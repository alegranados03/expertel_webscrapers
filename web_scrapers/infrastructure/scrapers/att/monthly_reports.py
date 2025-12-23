import calendar
import logging
import os
import time
import traceback
from datetime import datetime
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    FileDownloadInfo,
    MonthlyReportsScraperStrategy,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class ATTMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para AT&T con 6 reportes específicos."""

    # Configuración de reportes por slug
    REPORT_CONFIG = {
        "all_billing_cycle_charges": {
            "tab": "charges_and_usage",
            "section": "Bill summary",
            "report_names": ["All charges"],
            "needs_date_filter": True,
        },
        "wireless_charges": {
            "tab": "charges_and_usage",
            "section": "Wireless number summary",
            "report_names": ["All wireless charges and usage (GB usage)", "All wireless charges and usage"],
            "needs_date_filter": True,
        },
        "usage_details": {
            "tab": "charges_and_usage",
            "section": "Billed usage",
            "report_names": ["All data export - usage details (GB usage)", "All data export - usage details"],
            "needs_date_filter": True,
        },
        "monthly_charges": {
            "tab": "charges_and_usage",
            "section": "Bill summary",
            "report_names": ["Monthly charges"],
            "needs_date_filter": True,
        },
        "device_installment": {
            "tab": "charges_and_usage",
            "section": "Equipment installment",
            "report_names": ["Device installment details"],
            "needs_date_filter": True,
        },
        "upgrade_and_inventory": {
            "tab": "inventory",
            "section": "Inventory",
            "report_names": ["Upgrade eligibility and inventory"],
            "needs_date_filter": False,
        },
    }

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.report_dictionary = {
            "wireless_charges": None,
            "usage_details": None,
            "monthly_charges": None,
            "device_installment": None,
            "upgrade_and_inventory": None,
            "all_billing_cycle_charges": None,
        }
        self._filters_configured = False

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos mensuales en el portal de AT&T."""
        return self._find_files_section_with_retry(config, billing_cycle, max_retries=1)

    def _find_files_section_with_retry(
        self, config: ScraperConfig, billing_cycle: BillingCycle, max_retries: int = 1
    ) -> Optional[Any]:
        """Busca la sección de archivos con reintento automático en caso de error."""
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"Searching for AT&T files section (attempt {attempt + 1}/{max_retries + 1})")

                # 1. Click en Billing tab
                billing_tab_xpath = "//*[@id='primaryNav']/li[3]/a"
                self.logger.info("Clicking Billing tab...")

                if self.browser_wrapper.is_element_visible(billing_tab_xpath, timeout=10000):
                    billing_text = self.browser_wrapper.get_text(billing_tab_xpath)
                    if billing_text and "BILLING" in billing_text.upper():
                        self.logger.info(f"Billing tab verified: '{billing_text}'")
                        self.browser_wrapper.click_element(billing_tab_xpath)
                        time.sleep(15)  # Esperar 15 segundos después de redirección
                    else:
                        self.logger.warning(f"Billing tab text mismatch: '{billing_text}'")
                        continue
                else:
                    self.logger.warning("Billing tab not found")
                    continue

                # 2. Click en Reports dropdown
                reports_dropdown_xpath = "//*[@id='navMenuGroupReports']"
                self.logger.info("Clicking Reports dropdown...")

                if self.browser_wrapper.is_element_visible(reports_dropdown_xpath, timeout=10000):
                    reports_text = self.browser_wrapper.get_text(reports_dropdown_xpath)
                    if reports_text and "Reports" in reports_text:
                        self.logger.info(f"Reports dropdown verified: '{reports_text}'")
                        self.browser_wrapper.click_element(reports_dropdown_xpath)
                        time.sleep(2)
                    else:
                        self.logger.warning(f"Reports dropdown text mismatch: '{reports_text}'")
                        continue
                else:
                    self.logger.warning("Reports dropdown not found")
                    continue

                # 3. Click en Detail option dentro del dropdown
                detail_option_xpath = "//*[@id='mainNavMenu']/ul[1]/li[4]/ul/li[3]/a"
                self.logger.info("Clicking Detail option...")

                if self.browser_wrapper.is_element_visible(detail_option_xpath, timeout=5000):
                    detail_text = self.browser_wrapper.get_text(detail_option_xpath)
                    if detail_text and "Detail" in detail_text:
                        self.logger.info(f"Detail option verified: '{detail_text}'")
                        self.browser_wrapper.click_element(detail_option_xpath)
                        time.sleep(10)  # Esperar 10 segundos
                    else:
                        self.logger.warning(f"Detail option text mismatch: '{detail_text}'")
                        continue
                else:
                    self.logger.warning("Detail option not found")
                    continue

                # 4. Verificar que estamos en la zona de reportes
                tabs_xpath = "//*[@id='thisForm']/div/div[1]/ul"
                if self.browser_wrapper.is_element_visible(tabs_xpath, timeout=10000):
                    tabs_text = self.browser_wrapper.get_text(tabs_xpath)
                    if tabs_text and ("Charges and usage" in tabs_text or "Unbilled usage" in tabs_text):
                        self.logger.info("Reports section found successfully")
                        return {"section": "monthly_reports", "ready_for_download": True}
                    else:
                        self.logger.warning(f"Tabs text does not match expected: '{tabs_text}'")
                        continue
                else:
                    self.logger.warning("Reports tabs not found")
                    continue

            except Exception as e:
                self.logger.error(f"Error on attempt {attempt + 1}: {str(e)}\n{traceback.format_exc()}")
                if attempt < max_retries:
                    continue

        self.logger.error("Could not find files section after all attempts")
        return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los 6 archivos mensuales de AT&T."""
        downloaded_files = []

        # Mapear BillingCycleFiles por slug del carrier_report para asociación exacta
        billing_cycle_file_map = {}
        if billing_cycle.billing_cycle_files:
            for bcf in billing_cycle.billing_cycle_files:
                if bcf.carrier_report and bcf.carrier_report.slug:
                    slug = bcf.carrier_report.slug
                    billing_cycle_file_map[slug] = bcf
                    self.logger.info(f"Mapping BillingCycleFile ID {bcf.id} -> Slug: '{slug}'")

        try:
            # Orden de descarga: primero todos los de "Charges and usage", luego "Inventory"
            charges_reports = [
                "all_billing_cycle_charges",
                "wireless_charges",
                "usage_details",
                "monthly_charges",
                "device_installment",
            ]
            inventory_reports = ["upgrade_and_inventory"]

            # 1. Procesar reportes de "Charges and usage"
            self.logger.info("Processing Charges and usage reports...")
            self._click_tab("Charges and usage")
            time.sleep(3)

            # Verificar y configurar filtros (cuenta + fecha)
            self._ensure_filters_configured(billing_cycle, needs_date_filter=True)

            for slug in charges_reports:
                report_config = self.REPORT_CONFIG.get(slug)
                if report_config:
                    file_info = self._download_single_report(
                        slug, report_config, billing_cycle_file_map, billing_cycle
                    )
                    if file_info:
                        downloaded_files.append(file_info)

            # 2. Procesar reportes de "Inventory"
            self.logger.info("Processing Inventory reports...")
            self._click_tab("Inventory")
            time.sleep(5)

            # Verificar y configurar solo filtro de cuenta (no hay filtro de fecha en Inventory)
            self._ensure_filters_configured(billing_cycle, needs_date_filter=False)

            for slug in inventory_reports:
                report_config = self.REPORT_CONFIG.get(slug)
                if report_config:
                    file_info = self._download_single_report(
                        slug, report_config, billing_cycle_file_map, billing_cycle
                    )
                    if file_info:
                        downloaded_files.append(file_info)

            # 3. Reset a pantalla principal
            self._reset_to_main_screen()

            self.logger.info(f"Download completed. Total files: {len(downloaded_files)}")
            return downloaded_files

        except Exception as e:
            self.logger.error(f"Error during file download: {str(e)}\n{traceback.format_exc()}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _ensure_filters_configured(self, billing_cycle: BillingCycle, needs_date_filter: bool = True):
        """Verifica que los filtros estén configurados correctamente, si no, los configura."""
        self.logger.info("Verifying filters configuration...")

        # Verificar filtro de cuenta
        if not self._is_account_filter_configured(billing_cycle):
            self.logger.info("Account filter not configured, configuring now...")
            self._configure_account_filter(billing_cycle)
        else:
            self.logger.info("Account filter already configured correctly")

        # Verificar filtro de fecha (solo si es necesario)
        if needs_date_filter:
            if not self._is_date_filter_configured(billing_cycle):
                self.logger.info("Date filter not configured, configuring now...")
                self._configure_date_range(billing_cycle)
            else:
                self.logger.info("Date filter already configured correctly")

    def _is_account_filter_configured(self, billing_cycle: BillingCycle) -> bool:
        """Verifica si el filtro de cuenta está configurado correctamente."""
        try:
            account_number = billing_cycle.account.number
            view_by_xpath = "//*[@id='thisForm']/div/div[2]/div[1]/div[1]"

            if self.browser_wrapper.is_element_visible(view_by_xpath, timeout=5000):
                current_text = self.browser_wrapper.get_text(view_by_xpath)
                if current_text and account_number in current_text:
                    self.logger.debug(f"Account filter shows: '{current_text}'")
                    return True

            return False
        except Exception as e:
            self.logger.debug(f"Error checking account filter: {str(e)}")
            return False

    def _is_date_filter_configured(self, billing_cycle: BillingCycle) -> bool:
        """Verifica si el filtro de fecha está configurado correctamente."""
        try:
            end_date = billing_cycle.end_date
            month_name = calendar.month_name[end_date.month]
            year = end_date.year
            expected_text = f"{month_name} {year}"

            date_range_xpath = "//*[@id='thisForm']/div/div[2]/div[1]/div[2]"

            if self.browser_wrapper.is_element_visible(date_range_xpath, timeout=5000):
                current_text = self.browser_wrapper.get_text(date_range_xpath)
                if current_text and expected_text in current_text:
                    self.logger.debug(f"Date filter shows: '{current_text}'")
                    return True

            return False
        except Exception as e:
            self.logger.debug(f"Error checking date filter: {str(e)}")
            return False

    def _click_tab(self, tab_name: str):
        """Hace click en una pestaña específica del listado de reportes."""
        try:
            tabs_xpath = "//*[@id='thisForm']/div/div[1]/ul"
            self.logger.info(f"Clicking tab: {tab_name}")

            # Buscar el tab por texto usando xpath con contains
            if tab_name == "Charges and usage":
                tab_xpath = f"{tabs_xpath}/li[1]/a"
            elif tab_name == "Inventory":
                tab_xpath = f"{tabs_xpath}/li[3]/a"
            else:
                # Fallback genérico
                tab_xpath = f"{tabs_xpath}//a[contains(., '{tab_name}')]"

            if self.browser_wrapper.is_element_visible(tab_xpath, timeout=5000):
                self.browser_wrapper.click_element(tab_xpath)
                time.sleep(3)
                self.logger.info(f"Tab '{tab_name}' clicked successfully")
            else:
                self.logger.warning(f"Tab '{tab_name}' not found")

        except Exception as e:
            self.logger.error(f"Error clicking tab '{tab_name}': {str(e)}\n{traceback.format_exc()}")

    def _download_single_report(
        self, slug: str, report_config: dict, billing_cycle_file_map: dict, billing_cycle: BillingCycle
    ) -> Optional[FileDownloadInfo]:
        """Descarga un reporte individual y retorna FileDownloadInfo."""
        try:
            report_names = report_config["report_names"]
            section_name = report_config["section"]
            needs_date_filter = report_config.get("needs_date_filter", True)

            self.logger.info(f"Processing report: {slug} (section: {section_name})")

            # 1. Buscar y hacer click en el reporte dentro del accordion
            if not self._find_and_click_report(section_name, report_names):
                self.logger.warning(f"Report not found for {slug}. Skipping...")
                return None

            # 2. Esperar 1 minuto después de entrar al reporte
            self.logger.info("Waiting 60 seconds for report to load...")
            time.sleep(60)

            # 3. Click en Export button
            export_button_xpath = "//*[@id='export']"
            if not self.browser_wrapper.is_element_visible(export_button_xpath, timeout=10000):
                self.logger.error(f"Export button not found for {slug}")
                self._go_back_to_reports()
                # Verificar filtros después de regresar
                self._ensure_filters_configured(billing_cycle, needs_date_filter=needs_date_filter)
                return None

            self.logger.info("Clicking Export button...")
            self.browser_wrapper.click_element(export_button_xpath)
            time.sleep(2)

            # 4. Seleccionar CSV en el modal
            csv_option_xpath = "//*[@id='radCsvLabel']"
            if self.browser_wrapper.is_element_visible(csv_option_xpath, timeout=5000):
                self.logger.info("Selecting CSV option...")
                self.browser_wrapper.click_element(csv_option_xpath)
                time.sleep(1)
            else:
                self.logger.warning("CSV option not found in modal")
                # Intentar cerrar el modal si no encontramos la opción
                self._close_export_modal_if_open()
                self._go_back_to_reports()
                self._ensure_filters_configured(billing_cycle, needs_date_filter=needs_date_filter)
                return None

            # 5. Click en OK y esperar descarga
            ok_button_xpath = "//*[@id='hrefOK']"
            self.logger.info("Clicking OK to download...")

            file_path = self.browser_wrapper.expect_download_and_click(
                ok_button_xpath, timeout=120000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                self.logger.info(f"File downloaded: {actual_filename}")

                corresponding_bcf = billing_cycle_file_map.get(slug)

                file_download_info = FileDownloadInfo(
                    file_id=corresponding_bcf.id if corresponding_bcf else 0,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    billing_cycle_file=corresponding_bcf,
                )

                if corresponding_bcf:
                    self.logger.info(
                        f"MAPPING CONFIRMED: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id} (Slug: '{slug}')"
                    )
                else:
                    self.logger.warning(f"File downloaded without specific BillingCycleFile mapping")

                # 6. Regresar a la sección de reportes
                self._go_back_to_reports()

                # 7. Verificar filtros después de regresar
                self._ensure_filters_configured(billing_cycle, needs_date_filter=needs_date_filter)

                return file_download_info
            else:
                self.logger.error(f"Could not download file for {slug}")
                self._go_back_to_reports()
                # Verificar filtros después de regresar
                self._ensure_filters_configured(billing_cycle, needs_date_filter=needs_date_filter)
                return None

        except Exception as e:
            self.logger.error(f"Error downloading report {slug}: {str(e)}\n{traceback.format_exc()}")
            try:
                self._go_back_to_reports()
                self._ensure_filters_configured(billing_cycle, needs_date_filter=report_config.get("needs_date_filter", True))
            except:
                pass
            return None

    def _find_and_click_report(self, section_name: str, report_names: List[str]) -> bool:
        """Busca y hace click en un reporte dentro del accordion."""
        try:
            accordion_xpath = "//*[@id='accordion']"

            if not self.browser_wrapper.is_element_visible(accordion_xpath, timeout=10000):
                self.logger.error("Accordion not found")
                return False

            # Usar page directamente para buscar elementos
            page = self.browser_wrapper.page

            # Buscar todos los paneles del accordion
            panels = page.query_selector_all(f"xpath={accordion_xpath}//div[contains(@class, 'panel-reports')]")

            for panel in panels:
                # Obtener el título del panel
                try:
                    panel_title_element = panel.query_selector(".panel-title span")
                    if panel_title_element:
                        panel_title = panel_title_element.inner_text().strip()

                        if section_name.lower() in panel_title.lower():
                            self.logger.info(f"Found section: {panel_title}")

                            # Buscar los reportes dentro de este panel
                            report_buttons = panel.query_selector_all("button[name='ViewReport']")

                            for button in report_buttons:
                                button_text = button.inner_text().strip()

                                for report_name in report_names:
                                    if report_name.lower() in button_text.lower():
                                        self.logger.info(f"Found report: {button_text}")
                                        button.click()
                                        time.sleep(3)
                                        return True

                except Exception as inner_e:
                    self.logger.debug(f"Error checking panel: {str(inner_e)}")
                    continue

            self.logger.warning(f"Report not found in section '{section_name}' with names: {report_names}")
            return False

        except Exception as e:
            self.logger.error(f"Error finding report: {str(e)}\n{traceback.format_exc()}")
            return False

    def _close_export_modal_if_open(self):
        """Cierra el modal de export si está abierto."""
        try:
            # Buscar botón de cerrar/cancelar en el modal de export
            close_button_xpath = "//*[@id='exportModal']//button[@class='close']"
            cancel_button_xpath = "//*[@id='exportModal']//button[contains(text(), 'Cancel')]"

            if self.browser_wrapper.is_element_visible(close_button_xpath, timeout=2000):
                self.logger.info("Closing export modal via close button...")
                self.browser_wrapper.click_element(close_button_xpath)
                time.sleep(1)
            elif self.browser_wrapper.is_element_visible(cancel_button_xpath, timeout=2000):
                self.logger.info("Closing export modal via cancel button...")
                self.browser_wrapper.click_element(cancel_button_xpath)
                time.sleep(1)
            else:
                # Intentar presionar Escape para cerrar el modal
                self.logger.info("Attempting to close modal with Escape key...")
                self.browser_wrapper.page.keyboard.press("Escape")
                time.sleep(1)

        except Exception as e:
            self.logger.debug(f"Error closing export modal: {str(e)}")

    def _go_back_to_reports(self):
        """Regresa a la sección de reportes."""
        try:
            # Primero intentar cerrar cualquier modal abierto
            self._close_export_modal_if_open()

            back_button_xpath = "//*[@id='thisForm']/div[1]/div[1]/a"
            self.logger.info("Going back to reports section...")

            if self.browser_wrapper.is_element_visible(back_button_xpath, timeout=5000):
                self.browser_wrapper.click_element(back_button_xpath)
                time.sleep(5)
                self.logger.info("Back to reports section")
            else:
                self.logger.warning("Back button not found")

        except Exception as e:
            self.logger.error(f"Error going back to reports: {str(e)}\n{traceback.format_exc()}")

    def _configure_account_filter(self, billing_cycle: BillingCycle):
        """Configura el filtro de cuenta basado en el billing cycle."""
        try:
            account_number = billing_cycle.account.number
            self.logger.info(f"Configuring account filter for: {account_number}")

            # 1. Click en View by dropdown
            view_by_xpath = "//*[@id='thisForm']/div/div[2]/div[1]/div[1]"
            self.logger.info("Clicking View by dropdown...")
            self.browser_wrapper.click_element(view_by_xpath)
            time.sleep(2)

            # 2. Seleccionar opción "Accounts"
            accounts_option_xpath = "//*[@id='LevelDataDropdownList_multipleaccounts']"
            self.logger.info("Selecting Accounts option...")
            self.browser_wrapper.click_element(accounts_option_xpath)
            time.sleep(2)

            # 3. Escribir número de cuenta en el input
            account_input_xpath = "//*[@id='scopeExpandedAccountMenu']/div[1]/div/div[2]/input"
            self.logger.info(f"Entering account number: {account_number}")
            self.browser_wrapper.clear_and_type(account_input_xpath, account_number)
            time.sleep(3)  # Esperar que se actualice el listado

            # 4. Seleccionar la primera opción del listado
            first_option_xpath = "//*[@id='scopeExpandedAccountMenu']/div[3]/ul/li[1]"
            if self.browser_wrapper.is_element_visible(first_option_xpath, timeout=5000):
                self.logger.info("Selecting first account option...")
                # Click en el checkbox dentro del li
                checkbox_xpath = f"{first_option_xpath}/input"
                if self.browser_wrapper.is_element_visible(checkbox_xpath, timeout=2000):
                    self.browser_wrapper.click_element(checkbox_xpath)
                else:
                    self.browser_wrapper.click_element(first_option_xpath)
                time.sleep(1)
            else:
                self.logger.warning("Account option not found in list")

            # 5. Click en OK button
            ok_button_xpath = "//*[@id='scopeExpandedAccountMenu']/div[4]/button"
            self.logger.info("Clicking OK button...")
            self.browser_wrapper.click_element(ok_button_xpath)
            time.sleep(3)

            self.logger.info("Account filter configured successfully")

        except Exception as e:
            self.logger.error(f"Error configuring account filter: {str(e)}\n{traceback.format_exc()}")

    def _configure_date_range(self, billing_cycle: BillingCycle):
        """Configura el rango de fechas basado en el billing cycle."""
        try:
            end_date = billing_cycle.end_date
            month_name = calendar.month_name[end_date.month]
            year = end_date.year
            target_option = f"{month_name} {year}"

            self.logger.info(f"Configuring date range for: {target_option}")

            # 1. Click en Date range dropdown
            date_range_xpath = "//*[@id='thisForm']/div/div[2]/div[1]/div[2]"
            self.logger.info("Clicking Date range dropdown...")
            self.browser_wrapper.click_element(date_range_xpath)
            time.sleep(2)

            # 2. Seleccionar "Billed date" si no está seleccionado
            billed_date_xpath = "//*[@id='CIDPendingDataDropdownList_billed']"
            if self.browser_wrapper.is_element_visible(billed_date_xpath, timeout=5000):
                self.logger.info("Selecting Billed date option...")
                self.browser_wrapper.click_element(billed_date_xpath)
                time.sleep(2)

            # 3. Seleccionar el mes/año correcto del select
            # El select tiene opciones con formato "November 2025 bills" o "November 2025"
            select_xpath = "//*[@id='CIDPending']"
            option_text_bills = f"{month_name} {year} bills"
            option_text_simple = f"{month_name} {year}"

            self.logger.info(f"Searching for date option: '{option_text_bills}' or '{option_text_simple}'")

            # Intentar seleccionar con "bills" primero, luego sin
            try:
                self.browser_wrapper.select_dropdown_option(select_xpath, option_text_bills)
                self.logger.info(f"Selected: {option_text_bills}")
            except Exception:
                try:
                    self.browser_wrapper.select_dropdown_option(select_xpath, option_text_simple)
                    self.logger.info(f"Selected: {option_text_simple}")
                except Exception as e:
                    self.logger.warning(f"Could not select date option: {str(e)}")

            # 4. Click en Apply button para aplicar los cambios
            apply_button_xpath = "//*[@id='btnApply']"
            if self.browser_wrapper.is_element_visible(apply_button_xpath, timeout=5000):
                self.logger.info("Clicking Apply button...")
                self.browser_wrapper.click_element(apply_button_xpath)
                time.sleep(5)  # Esperar que se apliquen los cambios
            else:
                self.logger.warning("Apply button not found")

            self.logger.info("Date range configured successfully")

        except Exception as e:
            self.logger.error(f"Error configuring date range: {str(e)}\n{traceback.format_exc()}")

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de AT&T."""
        try:
            self.logger.info("Resetting to AT&T initial screen...")
            self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
            time.sleep(10)
            self.logger.info("Reset to AT&T completed")
        except Exception as e:
            self.logger.error(f"Error in AT&T reset: {str(e)}\n{traceback.format_exc()}")


# =============================================================================
# LEGACY CLASS - DEPRECATED
# =============================================================================


class ATTMonthlyReportsScraperStrategyLegacy(MonthlyReportsScraperStrategy):
    """LEGACY: Scraper de reportes mensuales para AT&T - DEPRECATED.

    Esta clase está deprecada. Usar ATTMonthlyReportsScraperStrategy en su lugar.
    Se mantiene para compatibilidad con implementaciones anteriores.
    """

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.report_dictionary = {
            "wireless_charges": None,
            "usage_details": None,
            "monthly_charges": None,
            "device_installment": None,
            "upgrade_and_inventory": None,
        }

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos mensuales en el portal de AT&T."""
        return self._find_files_section_with_retry(config, billing_cycle, max_retries=1)

    def _find_files_section_with_retry(
        self, config: ScraperConfig, billing_cycle: BillingCycle, max_retries: int = 1
    ) -> Optional[Any]:
        """Busca la sección de archivos con reintento automático en caso de error."""
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"[LEGACY] Searching for AT&T files section (attempt {attempt + 1}/{max_retries + 1})")

                # 1. Click en billing header y esperar 2 minutos
                billing_header_xpath = "/html/body/div[1]/div/ul/li[3]/a"
                self.logger.info("[LEGACY] Clicking Billing header...")
                self.browser_wrapper.click_element(billing_header_xpath)
                time.sleep(120)  # Esperar 2 minutos como especificado

                # 2. Click en reports tab
                reports_tab_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[4]/a/span"
                self.logger.info("[LEGACY] Clicking Reports tab...")
                self.browser_wrapper.click_element(reports_tab_xpath)
                time.sleep(3)

                # 3. Click en detail option
                detail_option_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[4]/ul/li[3]/a"
                self.logger.info("[LEGACY] Clicking Detail option...")
                self.browser_wrapper.click_element(detail_option_xpath)
                time.sleep(5)

                # 4. Verificar que encontramos la sección correcta
                charges_tab_section_xpath = "/html/body/div[1]/main/div[2]/form/div/div[1]/ul/li[1]/a/span"
                if self.browser_wrapper.is_element_visible(charges_tab_section_xpath, timeout=10000):
                    section_text = self.browser_wrapper.get_text(charges_tab_section_xpath)
                    if section_text and "Charges and usage" in section_text:
                        self.logger.info("[LEGACY] Reports section found successfully")
                        return {"section": "monthly_reports", "ready_for_download": True}
                    else:
                        self.logger.warning(f"[LEGACY] Section text does not match: {section_text}")
                        continue
                else:
                    self.logger.warning("[LEGACY] Reports section not found")
                    continue

            except Exception as e:
                self.logger.error(f"[LEGACY] Error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    continue

        self.logger.error("[LEGACY] Could not find files section after all attempts")
        return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los 5 archivos mensuales de AT&T."""
        downloaded_files = []

        slug_to_report_config = {
            "wireless_charges": {
                "name": "All wireless charges and usage",
                "text_to_verify": "All wireless charges and usage",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div[3]/div/div[2]/ul/li[1]/button",
                "tab": "charges",
            },
            "usage_details": {
                "name": "All data export - usage details",
                "text_to_verify": "All data export - usage details",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div[2]/div/div[2]/ul/li[1]/button",
                "tab": "charges",
            },
            "monthly_charges": {
                "name": "Monthly charges",
                "text_to_verify": "Monthly charges",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div[1]/div/div[2]/ul/li[8]/button",
                "tab": "charges",
            },
            "device_installment": {
                "name": "Device installment details",
                "text_to_verify": "Device installment details",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div[1]/div/div[2]/ul/li[8]/button",
                "tab": "charges",
            },
            "upgrade_and_inventory": {
                "name": "Upgrade eligibility and inventory",
                "text_to_verify": "Upgrade eligibility and inventory",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div/div/div[2]/ul/li[3]/button",
                "tab": "unbilled",
            },
        }

        billing_cycle_file_map = {}
        if billing_cycle.billing_cycle_files:
            for bcf in billing_cycle.billing_cycle_files:
                if bcf.carrier_report and bcf.carrier_report.slug:
                    slug = bcf.carrier_report.slug
                    billing_cycle_file_map[slug] = bcf
                    self.logger.info(f"[LEGACY] Mapping BillingCycleFile ID {bcf.id} -> Slug: '{slug}'")

        try:
            charges_tab_xpath = "/html/body/div[1]/main/div[2]/form/div/div[1]/ul/li[1]/a"
            self.logger.info("[LEGACY] Clicking Charges tab...")
            self.browser_wrapper.click_element(charges_tab_xpath)
            time.sleep(3)

            self._configure_date_range(billing_cycle)

            charges_reports = [slug for slug, cfg in slug_to_report_config.items() if cfg["tab"] == "charges"]
            for slug in charges_reports:
                self._download_single_report(slug, slug_to_report_config[slug], billing_cycle_file_map, downloaded_files)

            self.logger.info("[LEGACY] Switching to Unbilled Usage tab...")
            unbilled_tab_xpath = "/html/body/div[1]/main/div[2]/form/div/div[1]/ul/li[3]/a"
            self.browser_wrapper.click_element(unbilled_tab_xpath)
            time.sleep(3)

            unbilled_reports = [slug for slug, cfg in slug_to_report_config.items() if cfg["tab"] == "unbilled"]
            for slug in unbilled_reports:
                self._download_single_report(slug, slug_to_report_config[slug], billing_cycle_file_map, downloaded_files)

            self._reset_to_main_screen()

            self.logger.info(f"[LEGACY] Download completed. Total files: {len(downloaded_files)}")
            return downloaded_files

        except Exception as e:
            self.logger.error(f"[LEGACY] Error during file download: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _configure_date_range(self, billing_cycle: BillingCycle):
        """Configura el rango de fechas basado en el billing cycle."""
        try:
            self.logger.info(f"[LEGACY] Configuring date for period: {billing_cycle.end_date}")

            date_dropdown_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/button"
            self.browser_wrapper.click_element(date_dropdown_xpath)
            time.sleep(2)

            option_dropdown_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/div/div/div[2]/div/div[1]/select"
            self.browser_wrapper.click_element(option_dropdown_xpath)
            time.sleep(1)

            end_date = billing_cycle.end_date
            month_name = calendar.month_name[end_date.month]
            year = end_date.year
            option_text = f"{month_name} {year} bills"

            self.logger.debug(f"[LEGACY] Searching for option: {option_text}")

            select_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/div/div/div[2]/div/div[1]/select"
            self.browser_wrapper.select_dropdown_option(select_xpath, option_text)
            time.sleep(1)

            apply_button_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/div/div/div[2]/div/div[5]/button"
            self.logger.info("[LEGACY] Applying date changes...")
            self.browser_wrapper.click_element(apply_button_xpath)
            time.sleep(5)

        except Exception as e:
            self.logger.error(f"[LEGACY] Error configuring date: {str(e)}")

    def _download_single_report(
        self, slug: str, report_config: dict, billing_cycle_file_map: dict, downloaded_files: list
    ):
        """Descarga un reporte individual."""
        try:
            self.logger.info(f"[LEGACY] Processing report: {report_config['name']} (slug: {slug})")

            section_xpath = report_config["section_xpath"]

            if self.browser_wrapper.is_element_visible(section_xpath, timeout=5000):
                button_text = self.browser_wrapper.get_text(section_xpath)
                if button_text and report_config["text_to_verify"] in button_text:
                    self.logger.debug(f"[LEGACY] Text verified: '{button_text}'")
                    self.browser_wrapper.click_element(section_xpath)
                    time.sleep(3)
                else:
                    self.logger.warning(
                        f"[LEGACY] Text mismatch for {slug}. Expected: '{report_config['text_to_verify']}', Found: '{button_text}'. Skipping..."
                    )
                    return
            else:
                self.logger.warning(f"[LEGACY] Section not found for {slug}. Skipping...")
                return

            download_button_xpath = "/html/body/div[1]/main/div[2]/form/div[2]/div[2]/div/div/button[2]"
            self.logger.info("[LEGACY] Clicking Download Report...")
            self.browser_wrapper.click_element(download_button_xpath)
            time.sleep(2)

            csv_option_xpath = "/html/body/div[1]/div[3]/div/div/div[2]/form/div[1]/div/div/fieldset/label[2]"
            self.logger.info("[LEGACY] Selecting CSV option...")
            self.browser_wrapper.click_element(csv_option_xpath)
            time.sleep(1)

            ok_button_xpath = "/html/body/div[1]/div[3]/div/div/div[3]/button[1]"
            self.logger.info("[LEGACY] Clicking OK...")

            file_path = self.browser_wrapper.expect_download_and_click(
                ok_button_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                self.logger.info(f"[LEGACY] File downloaded: {actual_filename}")

                corresponding_bcf = billing_cycle_file_map.get(slug)

                file_download_info = FileDownloadInfo(
                    file_id=corresponding_bcf.id if corresponding_bcf else len(downloaded_files) + 1,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    billing_cycle_file=corresponding_bcf,
                )
                downloaded_files.append(file_download_info)

                if corresponding_bcf:
                    self.logger.info(
                        f"[LEGACY] MAPPING CONFIRMED: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id} (Slug: '{slug}')"
                    )
                else:
                    self.logger.warning(f"[LEGACY] File downloaded without specific BillingCycleFile mapping")
            else:
                self.logger.error(f"[LEGACY] Could not download file for {slug}")

            go_back_xpath = "/html/body/div[1]/main/div[2]/form/div[1]/div[1]/a"
            self.logger.info("[LEGACY] Going back...")
            self.browser_wrapper.click_element(go_back_xpath)
            time.sleep(3)

        except Exception as e:
            self.logger.error(f"[LEGACY] Error downloading report {slug}: {str(e)}")
            try:
                go_back_xpath = "/html/body/div[1]/main/div[2]/form/div[1]/div[1]/a"
                self.browser_wrapper.click_element(go_back_xpath)
                time.sleep(2)
            except:
                pass

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de AT&T."""
        try:
            self.logger.info("[LEGACY] Resetting to AT&T initial screen...")
            self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
            time.sleep(10)
            self.logger.info("[LEGACY] Reset to AT&T completed")
        except Exception as e:
            self.logger.error(f"[LEGACY] Error in AT&T reset: {str(e)}")