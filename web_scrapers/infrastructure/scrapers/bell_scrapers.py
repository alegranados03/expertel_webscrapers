import calendar
import logging
import os
import time
from datetime import datetime
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    DailyUsageScraperStrategy,
    FileDownloadInfo,
    MonthlyReportsScraperStrategy,
    PDFInvoiceScraperStrategy,
)
from web_scrapers.domain.entities.session import Credentials

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class BellMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Monthly reports scraper for Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.report_dictionary = {
            "cost_overview": None,
            "enhanced_user_profile_report": None,
            "usage_overview": None,
        }
        self._current_credentials: Optional[Credentials] = None
        self._reauthentication_callback = None

    def set_reauthentication_callback(self, callback):
        """Establece el callback para re-autenticación después de limpieza de caché."""
        self._reauthentication_callback = callback

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos mensuales en el portal de Bell."""
        return self._find_files_section_with_retry(config, billing_cycle, max_retries=1)

    def _find_files_section_with_retry(
        self, config: ScraperConfig, billing_cycle: BillingCycle, max_retries: int = 1
    ) -> Optional[Any]:
        """Busca la sección de archivos con reintento automático en caso de error de caché."""
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"Searching for files section (attempt {attempt + 1}/{max_retries + 1})")

                # Look for reports
                report_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[4]/a[1]"
                self.browser_wrapper.hover_element(report_xpath)
                time.sleep(2)  # Esperar 2 segundos después del hover

                # e-report (click)
                ereport_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[4]/div[1]/ul[1]/li[1]/a[1]/h3[1]"
                current_url: str = self.browser_wrapper.get_current_url()
                self.logger.debug(f"Current url: {current_url}")
                self.browser_wrapper.click_and_switch_to_new_tab(ereport_xpath, 60000)

                # DETECTAR ERROR DE CACHÉ: Verificar que el header esté disponible
                if not self._verify_ereport_header_available():
                    self.logger.warning("Potential cache error detected in e-reports")
                    # if attempt > max_retries:
                    #     self.logger.info("Starting cache recovery...")
                    #     if self._handle_cache_recovery():
                    #         self.logger.info("Recovery successful, retrying...")
                    #         continue
                    #     else:
                    #         print("❌ Recuperación falló")
                    #         return None
                    # else:
                    #     print("❌ Máximo de reintentos alcanzado")
                    #     return None

                # standard reports (click)
                standard_reports_xpath = (
                    "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/div[1]/div[1]/ul[1]/li[2]/div[1]/span[1]/a[1]"
                )
                self.browser_wrapper.click_element(standard_reports_xpath)
                self.browser_wrapper.wait_for_page_load()
                time.sleep(30)

                self.logger.info("Files section found successfully")
                return {"section": "monthly_reports", "ready_for_download": True}

            except Exception as e:
                self.logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                try:
                    if self.browser_wrapper.get_tab_count() > 1:
                        self.browser_wrapper.close_current_tab()
                        self.browser_wrapper.switch_to_previous_tab()
                except:
                    self.logger.error("Could not close previous window and switch to previous tab")

                if attempt < max_retries:
                    # print("🔧 Iniciando recuperación por excepción...")
                    # if self._handle_cache_recovery():
                    #     print("✅ Recuperación exitosa, reintentando...")
                    continue
                    # else:
                    #     print("❌ Recuperación falló")
                    #     return None

        return None

    def _verify_ereport_header_available(self) -> bool:
        """Verifica que el header de e-reports esté disponible (no hay error de caché)."""
        try:
            # Verificar que el header de e-reports esté presente
            header_xpath = (
                "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/div[1]/div[1]/ul[1]/li[2]/div[1]/span[1]/a[1]"
            )
            is_available = self.browser_wrapper.is_element_visible(header_xpath, timeout=60000)

            if is_available:
                self.logger.info("E-reports header available")
                return True
            else:
                self.logger.warning("E-reports header not available - possible cache error")
                return False

        except Exception as e:
            self.logger.error(f"Error verifying header: {e}")
            return False

    def _handle_cache_recovery(self) -> bool:
        """Maneja la recuperación cuando se detecta error de caché."""
        try:
            self.logger.info("Starting browser data cleanup...")

            # Cerrar pestañas adicionales y regresar a main
            if self.browser_wrapper.get_tab_count() > 1:
                self.browser_wrapper.close_all_tabs_except_main()
                time.sleep(2)

            # Limpiar datos del navegador (esto invalidará la sesión)
            self.browser_wrapper.clear_browser_data(clear_cookies=True, clear_storage=True, clear_cache=True)
            time.sleep(3)

            # Notificar que necesitamos re-autenticación
            # La sesión se perdió automáticamente por la limpieza de datos
            self.logger.info("Data cleaned - session lost and automatic re-login required")

            # El SessionManager detectará automáticamente que la sesión no está activa
            # cuando se llame al siguiente método del scraper
            return True

        except Exception as e:
            self.logger.error(f"Error in cache recovery: {e}")
            return False

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        downloaded_files = []

        slug_to_report_name = {
            "cost_overview": "Cost Overview",
            "enhanced_user_profile": "Enhanced User Profile Report",
            "usage_overview": "Usage Overview",
        }

        # Mapeo de nombres de reportes a valores del dropdown
        report_types = {"Cost Overview": 2, "Enhanced User Profile Report": 7, "Usage Overview": 5}

        # Mapear BillingCycleFiles por slug del carrier_report para asociación exacta
        billing_cycle_file_map = {}
        slug_order = []  # Orden de slugs para mapeo posterior

        if billing_cycle.billing_cycle_files:
            for bcf in billing_cycle.billing_cycle_files:
                if bcf.carrier_report and bcf.carrier_report.slug:
                    slug = bcf.carrier_report.slug
                    billing_cycle_file_map[slug] = bcf
                    slug_order.append(slug)
                    report_name = slug_to_report_name.get(slug, slug)
                    self.logger.info(f"Mapping BillingCycleFile ID {bcf.id} -> Slug: '{slug}' -> Report: '{report_name}'")

        standard_report_dropdown_xpath = "/html/body/div[3]/div/div/div[1]/div[1]/div/div[1]/div[1]/div[1]/select"
        left_date_dropdown_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div[1]/div[7]/div[1]/div[2]/div[1]/select[1]"
        right_date_dropdown_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div[1]/div[7]/div[1]/div[2]/div[1]/select[2]"
        apply_button_xpath = (
            "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div[1]/div[11]/div[2]/button[1]"
        )
        excel_image_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/img[2]"

        start_date_text = billing_cycle.start_date.strftime("%b %Y")
        end_date_text = billing_cycle.end_date.strftime("%b %Y")

        generated_slugs_order = []
        for slug in slug_order:
            if slug in slug_to_report_name:
                report_name = slug_to_report_name[slug]
                if report_name in report_types:
                    report_value = report_types[report_name]
                    self.logger.info(f"Processing slug '{slug}' -> report: {report_name}")
                    selected_option = self.browser_wrapper.get_text(standard_report_dropdown_xpath)
                    if not selected_option or report_name.lower() != selected_option.lower():
                        self.browser_wrapper.select_dropdown_by_value(
                            standard_report_dropdown_xpath, str(report_value)
                        )
                    time.sleep(2)
                    self.logger.debug(f"Start date text to select: {start_date_text}, end date text to select: {end_date_text}")
                    self.browser_wrapper.select_dropdown_option(left_date_dropdown_xpath, start_date_text)
                    self.browser_wrapper.select_dropdown_option(right_date_dropdown_xpath, end_date_text)
                    self.logger.debug(f"Dates selected: from: {start_date_text}, to: {end_date_text}")
                    self.browser_wrapper.click_element(apply_button_xpath)
                    self.browser_wrapper.wait_for_page_load()
                    time.sleep(5)
                    self.browser_wrapper.click_element(excel_image_xpath)
                    time.sleep(10)
                    generated_slugs_order.append(slug)
                    self.logger.info(
                        f"Slug '{slug}' ({report_name}) requested (position {len(generated_slugs_order)} in queue)"
                    )
                else:
                    self.logger.warning(f"Report '{report_name}' for slug '{slug}' not found in report_types")
            else:
                self.logger.warning(f"Slug '{slug}' not found in slug_to_report_name mapping")

        self.logger.info(f"Order of generated slugs: {generated_slugs_order}")

        time.sleep(60 * 5)
        try:
            self.logger.info("Waiting for downloads table to appear...")
            table_xpath = "/html/body/div[4]/div[2]/div/table"
            self.browser_wrapper.wait_for_element(table_xpath, timeout=120000)
            time.sleep(5)

            self.logger.info("Downloads table found. Starting download of first 3 files...")

            records_to_download = len(generated_slugs_order)
            for i in range(records_to_download, 0, -1):
                try:
                    # Determinar qué slug corresponde a este archivo (orden inverso)
                    slug_index = records_to_download - i  # 0, 1, 2
                    current_slug = (
                        generated_slugs_order[slug_index] if slug_index < len(generated_slugs_order) else None
                    )
                    current_report_name = slug_to_report_name.get(current_slug) if current_slug else None

                    corresponding_bcf = billing_cycle_file_map.get(current_slug) if current_slug else None
                    self.logger.info(f"Downloading file #{i} -> Slug: '{current_slug}' -> Report: '{current_report_name}'")
                    if corresponding_bcf:
                        self.logger.info(f"    Associated with BillingCycleFile ID: {corresponding_bcf.id}")
                    else:
                        self.logger.warning(f"    BillingCycleFile not found for mapping")

                    # XPath específico para cada fila: /html/body/div[4]/div[2]/div/table/tbody/tr[i]/td[1]/a
                    download_link_xpath = f"/html/body/div[4]/div[2]/div/table/tbody/tr[{i}]/td[1]/a"

                    # Verificar que el enlace existe antes de hacer clic
                    if not self.browser_wrapper.find_element_by_xpath(download_link_xpath, timeout=5000):
                        self.logger.warning(f"Download link not found for file #{i}")
                        continue

                    # Obtener el texto del enlace para logging
                    try:
                        link_text = self.browser_wrapper.get_text(download_link_xpath)
                        self.logger.info(f"Downloading: {link_text}")
                    except:
                        self.logger.info(f"Downloading file in row #{i}")

                    downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                        download_link_xpath, timeout=30000
                    )
                    self.logger.debug(f"Downloaded file path: {downloaded_file_path}")

                    if downloaded_file_path:
                        actual_file_name = os.path.basename(downloaded_file_path)
                        self.logger.info(f"File downloaded successfully: {actual_file_name}")

                        # Crear FileDownloadInfo con mapeo al BillingCycleFile
                        file_download_info = FileDownloadInfo(
                            file_id=corresponding_bcf.id if corresponding_bcf else i,
                            file_name=actual_file_name,
                            download_url="N/A",
                            file_path=downloaded_file_path,
                            billing_cycle_file=corresponding_bcf,
                        )
                        downloaded_files.append(file_download_info)

                        # Imprimir confirmación del mapeo
                        if corresponding_bcf:
                            self.logger.info(
                                f"    MAPPING CONFIRMED: {actual_file_name} -> BillingCycleFile ID {corresponding_bcf.id} (Slug: '{current_slug}' -> {current_report_name})"
                            )
                        else:
                            self.logger.warning(f"    File downloaded without specific BillingCycleFile mapping")

                    else:
                        self.logger.warning(f"expect_download_and_click failed for file #{i}, trying traditional method...")
                        self.browser_wrapper.click_element(download_link_xpath)
                        time.sleep(5)
                        estimated_filename = (
                            f"bell_report_{current_slug}_{datetime.now().timestamp()}.xlsx"
                            if current_slug
                            else f"bell_report_{i}_{datetime.now().timestamp()}.xlsx"
                        )

                        file_download_info = FileDownloadInfo(
                            file_id=corresponding_bcf.id,
                            file_name=estimated_filename,
                            download_url="N/A",
                            file_path=f"{DOWNLOADS_DIR}/{estimated_filename}",
                            billing_cycle_file=corresponding_bcf,
                        )
                        downloaded_files.append(file_download_info)

                        self.logger.info(f"Download started (traditional method): {estimated_filename}")
                        if corresponding_bcf:
                            self.logger.info(
                                f"    MAPPING CONFIRMED: {estimated_filename} -> BillingCycleFile ID {corresponding_bcf.id} (Slug: '{current_slug}' -> {current_report_name})"
                            )

                    # Pequeña pausa entre descargas
                    time.sleep(5)
                except Exception as e:
                    self.logger.error(f"Error trying to download file #{i}: {str(e)}")
                    continue

            # Imprimir resumen final de mapeos
            self.logger.info(f"\nFINAL FILE MAPPING SUMMARY:")
            self.logger.info(f"   Total files downloaded: {len(downloaded_files)}")
            for idx, file_info in enumerate(downloaded_files, 1):
                if file_info.billing_cycle_file:
                    bcf = file_info.billing_cycle_file
                    slug = bcf.carrier_report.slug if hasattr(bcf, "carrier_report") and bcf.carrier_report else "N/A"
                    report_name = slug_to_report_name.get(slug, slug) if slug != "N/A" else "N/A"
                    self.logger.info(
                        f"   [{idx}] {file_info.file_name} -> BillingCycleFile ID {bcf.id} (Slug: '{slug}' -> {report_name})"
                    )
                else:
                    self.logger.info(f"   [{idx}] {file_info.file_name} -> NO MAPPING")
            self.logger.info(f"=====================================")

            self.browser_wrapper.close_current_tab()
            time.sleep(2)
            # Reset a pantalla inicial usando el logo
            self._reset_to_main_screen()
            return downloaded_files
        except Exception as e:
            self.logger.error(f"General error processing downloads table: {e}")
            return downloaded_files

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Bell usando el logo."""
        try:
            self.logger.info("Resetting to Bell initial screen...")
            logo_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/a[1]"
            self.browser_wrapper.click_element(logo_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            self.logger.info("Reset to Bell completed")
        except Exception as e:
            self.logger.error(f"Error in Bell reset: {str(e)}")


class BellDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Daily usage scraper for Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos de uso diario en el portal de Bell."""
        try:
            # Determine if account selection is needed (Version 1) or already preselected (Version 2)
            account_selection_header_xpath = (
                "/html/body/div[1]/main/div[1]/div/div/div/account-selection/div[2]/section/div[1]/header/div/h1"
            )

            # Check if account selection header appears
            account_selection_needed = self.browser_wrapper.find_element_by_xpath(
                account_selection_header_xpath, timeout=5000
            )

            if account_selection_needed:
                self.logger.info("Version 1: Account selection required")
                self._handle_account_selection(billing_cycle)
            else:
                self.logger.info("Version 2: Account already preselected, continuing direct")

            # Parte común: Navegar a usage details y configurar dropdown
            self._navigate_to_usage_details()

            return {"section": "daily_usage", "ready_for_download": True}

        except Exception as e:
            self.logger.error(f"Error in _find_files_section: {str(e)}")
            return None

    def _handle_account_selection(self, billing_cycle: BillingCycle):
        """Maneja la selección de cuenta cuando es necesaria (Version 1)."""
        self.logger.info("Executing account selection...")

        # Buscar cuenta por número
        search_input_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/div[1]/div[1]/div[1]/account-selection[1]/div[2]/section[1]/div[2]/global-search[1]/div[1]/section[2]/div[1]/div[1]/account-search[1]/div[1]/div[1]/div[1]/input[1]"
        self.browser_wrapper.type_text(search_input_xpath, billing_cycle.account.number)

        # Hacer clic en buscar
        search_button_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/div[1]/div[1]/div[1]/account-selection[1]/div[2]/section[1]/div[2]/global-search[1]/div[1]/section[2]/div[1]/div[1]/account-search[1]/div[1]/div[1]/div[2]/button[1]"
        self.browser_wrapper.click_element(search_button_xpath)
        time.sleep(3)

        # Seleccionar cuenta
        select_account_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/div[1]/div[1]/div[1]/account-selection[1]/div[2]/section[1]/div[2]/global-search[1]/div[1]/section[3]/div[1]/search[1]/div[2]/div[1]/div[2]/table[1]/tbody[1]/tr[1]/td[9]/button[1]"
        self.browser_wrapper.click_element(select_account_xpath)
        time.sleep(5)
        self.logger.info("Account selected successfully")

    def _navigate_to_usage_details(self):
        """Navega a usage details y configura el dropdown (parte común)."""
        self.logger.info("Navigating to usage details...")

        # usage header (hover)
        usage_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[2]/a[1]"
        self.browser_wrapper.hover_element(usage_xpath)
        time.sleep(2)

        # usage details: (click)
        usage_details_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[2]/div[1]/ul[1]/li[1]/ul[1]/li[1]/a[1]/span[1]"
        self.browser_wrapper.click_element(usage_details_xpath)
        self.browser_wrapper.wait_for_page_load()
        time.sleep(60)  # Esperar 60 segundos como especificado
        self.logger.info("Reports section found")

        # Configurar dropdown con lógica de fallback
        self._configure_data_share_dropdown()
        time.sleep(30)  # Esperar 30 segundos como especificado

    def _configure_data_share_dropdown(self):
        """Configura el dropdown con lógica de fallback entre Medium y Corp Business Data Share."""
        dropdown_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/div[2]/account-details[1]/div[1]/div[2]/account-shared-data[1]/div[2]/category-usage-details[1]/div[1]/div[2]/div[4]/div[1]/subscriber-usage-details[1]/div[1]/div[2]/filter-selection[1]/div[1]/select[1]"

        try:
            # Intentar primero con "Medium Business Data Share"
            self.logger.info("Trying to select 'Medium Business Data Share'...")
            self.browser_wrapper.select_dropdown_option(dropdown_xpath, "Medium Business Data Share")
            self.logger.info("'Medium Business Data Share' selected")
        except Exception as e:
            self.logger.warning("'Medium Business Data Share' not available, trying 'Corp Business Data Share'...")
            try:
                self.browser_wrapper.select_dropdown_option(dropdown_xpath, "Corp Business Data Share")
                self.logger.info("'Corp Business Data Share' selected")
            except Exception as e2:
                self.logger.error(f"Error configuring dropdown: {str(e2)}")
                raise e2

        self.browser_wrapper.wait_for_page_load()

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de Bell."""
        downloaded_files = []

        # Obtener el BillingCycleDailyUsageFile del billing_cycle
        daily_usage_file = billing_cycle.daily_usage_files[0] if billing_cycle.daily_usage_files else None
        if daily_usage_file:
            self.logger.info(f"Mapping Daily Usage file -> BillingCycleDailyUsageFile ID {daily_usage_file.id}")
        else:
            self.logger.warning("BillingCycleDailyUsageFile not found for mapping")

        try:
            # download tab: (click) - usando nuevos XPaths
            download_tab_xpath = "/html/body/div[1]/main/div[1]/div[2]/account-details/div/div[2]/account-shared-data/div[2]/category-usage-details/div/div[2]/div[4]/div/subscriber-usage-details/div/div[3]/div/search/nav/ul/li[3]/a"
            self.browser_wrapper.click_element(download_tab_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)  # Esperar 5 segundos

            # download all pages: (click) - usando nuevos XPaths
            download_all_pages_xpath = "/html/body/div[1]/main/div[1]/div[2]/account-details/div/div[2]/account-shared-data/div[2]/category-usage-details/div/div[2]/div[4]/div/subscriber-usage-details/div/div[3]/div/search/nav/ul/li[3]/ul/li/a"
            page = self.browser_wrapper.page
            with page.expect_download() as download_info:
                self.browser_wrapper.click_element(download_all_pages_xpath)
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)

            download = download_info.value
            suggested_filename = f"report_{datetime.now().timestamp()}_{download.suggested_filename}"
            final_path = os.path.join(DOWNLOADS_DIR, suggested_filename)

            # Guardar en disco
            download.save_as(final_path)

            # Crear FileDownloadInfo con mapeo al BillingCycleDailyUsageFile
            downloaded_file = FileDownloadInfo(
                file_id=daily_usage_file.id,
                file_name=suggested_filename,
                download_url="N/A",
                file_path=final_path,
                daily_usage_file=daily_usage_file,
            )
            downloaded_files.append(downloaded_file)

            # Confirmar mapeo
            if daily_usage_file:
                self.logger.info(
                    f"MAPPING CONFIRMED: {suggested_filename} -> BillingCycleDailyUsageFile ID {daily_usage_file.id}"
                )
            else:
                self.logger.warning(f"File downloaded without specific BillingCycleDailyUsageFile mapping")

            # Reset a pantalla inicial usando el logo
            self._reset_to_main_screen()

            return downloaded_files
        except Exception as e:
            self.logger.error(f"Error downloading Daily Usage file: {str(e)}")
            return downloaded_files

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Bell usando el logo."""
        try:
            self.logger.info("Resetting to Bell initial screen...")
            logo_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/a[1]"
            self.browser_wrapper.click_element(logo_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            self.logger.info("Reset to Bell completed")
        except Exception as e:
            self.logger.error(f"Error in Bell reset: {str(e)}")


class BellPDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """PDF invoice scraper for Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de facturas PDF en el portal de Bell."""
        try:
            # Navegar a la sección de billing y download PDF
            self._navigate_to_pdf_section()

            # Determine if account selection is needed (Version 1) or already preselected (Version 2)
            search_input_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[2]/section[1]/div[1]/account-selection-global-search[1]/div[1]/div[2]/section[2]/div[1]/div[1]/account-search[1]/div[1]/div[1]/div[1]/input[1]"
            account_selection_needed = self.browser_wrapper.find_element_by_xpath(search_input_xpath, timeout=10000)

            if account_selection_needed:
                self.logger.info("Version 1: Account selection required")
                self._handle_pdf_account_selection(billing_cycle)
            else:
                self.logger.info("Version 2: Account already preselected, continuing direct")

            # Parte común: Configurar opciones de descarga de PDF
            self._configure_pdf_download_options(billing_cycle)

            return {"section": "pdf_invoices", "ready_for_download": True}

        except Exception as e:
            self.logger.error(f"Error in _find_files_section: {str(e)}")
            return None

    def _navigate_to_pdf_section(self):
        """Navega a la sección de descarga de PDF (parte inicial común)."""
        self.logger.info("Navigating to PDF download section...")

        # billing tab (hover)
        billing_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[3]/a[1]"
        self.browser_wrapper.hover_element(billing_xpath)
        time.sleep(2)

        # download pdf section (click)
        download_pdf_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[3]/div[1]/ul[1]/li[1]/ul[1]/li[3]/a[1]"
        self.browser_wrapper.click_element(download_pdf_xpath)
        self.browser_wrapper.wait_for_page_load()
        time.sleep(5)
        self.logger.info("Navigation to PDF completed")

    def _handle_pdf_account_selection(self, billing_cycle: BillingCycle):
        """Maneja la selección de cuenta cuando es necesaria (Version 1)."""
        self.logger.info("Executing account selection for PDF...")

        # search input (enter billing_cycle.account.number)
        search_input_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[2]/section[1]/div[1]/account-selection-global-search[1]/div[1]/div[2]/section[2]/div[1]/div[1]/account-search[1]/div[1]/div[1]/div[1]/input[1]"
        self.browser_wrapper.type_text(search_input_xpath, billing_cycle.account.number)

        # search button (click)
        search_button_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[2]/section[1]/div[1]/account-selection-global-search[1]/div[1]/div[2]/section[2]/div[1]/div[1]/account-search[1]/div[1]/div[1]/div[2]/button[1]"
        self.browser_wrapper.click_element(search_button_xpath)
        time.sleep(3)

        # select account (click)
        select_account_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[2]/section[1]/div[1]/account-selection-global-search[1]/div[1]/section[1]/div[1]/search[1]/div[2]/div[1]/div[2]/table[1]/tbody[1]/tr[1]/td[1]/label[1]/span[1]"
        self.browser_wrapper.click_element(select_account_xpath)
        time.sleep(2)

        # continue (click)
        continue_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[9]/selection-dock[1]/div[1]/div[1]/div[1]/div[4]/button[1]"
        self.browser_wrapper.click_element(continue_xpath)
        self.browser_wrapper.wait_for_page_load()
        time.sleep(5)
        self.logger.info("Account selected successfully")

    def _configure_pdf_download_options(self, billing_cycle: BillingCycle):
        """Configura las opciones de descarga de PDF (parte común)."""
        self.logger.info("Configuring PDF download options...")

        # Verificar que estamos en la página correcta
        complete_invoice_radiobtn_xpath = (
            "/html/body/div[1]/main/div[1]/uxp-flow/div[2]/download-options/div/div/section[1]/div[1]/label[2]/input"
        )
        if not self.browser_wrapper.find_element_by_xpath(complete_invoice_radiobtn_xpath, timeout=5000):
            raise Exception("No se encontró el radio button de opciones de descarga")

        # complete invoice (click)
        complete_invoice_label_xpath = (
            "/html/body/div[1]/main/div[1]/uxp-flow/div[2]/download-options/div/div/section[1]/div[1]/label[2]/span[2]"
        )
        self.browser_wrapper.click_element(complete_invoice_label_xpath)
        time.sleep(5)
        self.logger.info("Complete invoice selected")

        # Seleccionar fecha más cercana al end_date del billing_cycle
        self._select_closest_date_checkbox(billing_cycle)

    def _select_closest_date_checkbox(self, billing_cycle: BillingCycle):
        """Selecciona el checkbox de fecha más cercano al end_date del billing_cycle."""
        self.logger.info("Selecting closest date...")

        target_month = billing_cycle.end_date.month
        target_year = billing_cycle.end_date.year
        target_month_name = calendar.month_name[target_month]
        target_period = f"{target_month_name} {target_year}"

        self.logger.info(f"Searching checkbox for: {target_period}")

        try:
            # Buscar por texto exacto en el label
            checkbox_xpath = f"//label[contains(., '{target_period}')]/span[1]"
            if self.browser_wrapper.find_element_by_xpath(checkbox_xpath, timeout=3000):
                self.browser_wrapper.click_element(checkbox_xpath)
                self.logger.info(f"Checkbox selected for: {target_period}")
                return
        except:
            self.logger.warning(f"Exact checkbox not found for {target_period}")

        try:
            self.logger.info("Searching for available checkboxes...")
            # Buscar todos los checkboxes disponibles en la sección
            checkboxes_section_xpath = (
                "/html/body/div[1]/main/div[1]/uxp-flow/div[3]/download-options/div/div/section[2]"
            )

            # Como fallback, usar el primer checkbox disponible
            fallback_checkbox_xpath = f"{checkboxes_section_xpath}//div[@class='grd-col-1-4'][1]//label/span[1]"
            self.browser_wrapper.click_element(fallback_checkbox_xpath)
            self.logger.info("Fallback checkbox selected (first available option)")
        except Exception as e:
            self.logger.error(f"Error selecting date checkbox: {str(e)}")
            raise e

        time.sleep(5)

    def _handle_pdf_exit_flow(self):
        """Maneja el flujo de salida específico para PDF downloads."""
        self.logger.info("Executing PDF exit flow...")

        try:
            # return to back to my account (click)
            back_to_account_xpath = "/html/body/div[1]/header/div/div/div/div[3]/div[1]/div/app-header/button[2]"
            self.browser_wrapper.click_element(back_to_account_xpath)
            self.logger.info("'Back to my account' button clicked")

            # wait 30 seconds
            self.logger.info("Waiting 30 seconds...")
            time.sleep(30)

            # click to leave page
            try:
                leave_page_xpath = (
                    "/html/body/div[1]/header/div/div/div/div[3]/div[1]/div/app-header/div/div/div/div/div/button[2]"
                )
                self.browser_wrapper.click_element(leave_page_xpath)
                self.logger.info("'Leave page' button clicked")
            except Exception as e:
                self.logger.info("Leave button didn't appear, you should see initial site")
            time.sleep(3)  # Pausa adicional antes del reset
            self.logger.info("PDF exit flow completed")

        except Exception as e:
            self.logger.warning(f"Error in PDF exit flow: {str(e)} - continuing with reset...")

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de Bell."""
        downloaded_files = []

        # Obtener el BillingCyclePDFFile del billing_cycle
        pdf_file = billing_cycle.pdf_files[0] if billing_cycle.pdf_files else None
        if pdf_file:
            self.logger.info(f"Mapping PDF Invoice file -> BillingCyclePDFFile ID {pdf_file.id}")
        else:
            self.logger.warning("BillingCyclePDFFile not found for mapping")

        try:
            # download button (click) - usando nuevos XPaths
            download_button_xpath = (
                "/html/body/div[1]/main/div[1]/uxp-flow/div[2]/download-options/div/div/div/div/button[2]"
            )
            self.browser_wrapper.click_element(download_button_xpath)
            self.logger.info("Initial download button clicked")

            # wait 2 minutes for button to appear then click - usando nuevos XPaths
            self.logger.info("Waiting 2 minutes for final download button to appear...")
            final_download_button_xpath = (
                "/html/body/div[1]/main/div[1]/uxp-flow/div[3]/confirmation/div/div/section[1]/button[1]"
            )
            self.browser_wrapper.wait_for_element(final_download_button_xpath, timeout=120000)  # 2 minutes in ms

            # Descargar archivo PDF usando expect_download_and_click
            downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                final_download_button_xpath, timeout=30000
            )
            self.logger.debug(f"Downloaded file path: {downloaded_file_path}")

            if downloaded_file_path:
                actual_file_name = os.path.basename(downloaded_file_path)
                self.logger.info(f"File downloaded successfully: {actual_file_name}")

                if actual_file_name.lower().endswith(".zip"):
                    self.logger.info("ZIP file detected, proceeding to extract...")
                    extracted_files = self._extract_zip_files(downloaded_file_path)
                    if extracted_files:
                        for i, extracted_file_path in enumerate(extracted_files):
                            extracted_file_name = os.path.basename(extracted_file_path)

                            # Crear FileDownloadInfo para cada archivo extraído
                            file_info = FileDownloadInfo(
                                file_id=pdf_file.id if pdf_file else (i + 1),
                                file_name=extracted_file_name,
                                download_url="N/A",
                                file_path=extracted_file_path,
                                pdf_file=pdf_file,
                            )
                            downloaded_files.append(file_info)

                            # Confirmar mapeo para cada archivo extraído
                            if pdf_file:
                                self.logger.info(
                                    f"MAPPING CONFIRMED: {extracted_file_name} -> BillingCyclePDFFile ID {pdf_file.id}"
                                )
                            else:
                                self.logger.warning(f"Extracted file without specific BillingCyclePDFFile mapping")
                    else:
                        self.logger.error("Could not extract files from ZIP")
                        # Usar el ZIP original como fallback
                        file_info = FileDownloadInfo(
                            file_id=pdf_file.id if pdf_file else 1,
                            file_name=actual_file_name,
                            download_url="N/A",
                            file_path=downloaded_file_path,
                            pdf_file=pdf_file,
                        )
                        downloaded_files.append(file_info)
                else:
                    self.logger.info("Regular file detected (not ZIP)")
                    file_info = FileDownloadInfo(
                        file_id=pdf_file.id if pdf_file else 1,
                        file_name=actual_file_name,
                        download_url="N/A",
                        file_path=downloaded_file_path,
                        pdf_file=pdf_file,
                    )
                    downloaded_files.append(file_info)

                    # Confirmar mapeo
                    if pdf_file:
                        self.logger.info(f"MAPPING CONFIRMED: {actual_file_name} -> BillingCyclePDFFile ID {pdf_file.id}")
                    else:
                        self.logger.warning(f"File downloaded without specific BillingCyclePDFFile mapping")
            else:
                self.logger.warning("expect_download_and_click failed for PDF, using fallback method...")
                self.browser_wrapper.click_element(final_download_button_xpath)
                time.sleep(5)

                # Considerar que podría ser ZIP o PDF
                estimated_filename = f"bell_invoice_{billing_cycle.end_date.strftime('%Y-%m-%d')}.zip"
                fallback_path = f"{DOWNLOADS_DIR}/{estimated_filename}"

                file_info = FileDownloadInfo(
                    file_id=pdf_file.id,
                    file_name=estimated_filename,
                    download_url="N/A",
                    file_path=fallback_path,
                    pdf_file=pdf_file,
                )
                downloaded_files.append(file_info)
                self.logger.info(f"Download started (traditional method): {estimated_filename}")
                self.logger.warning(
                    "Note: If downloaded file is ZIP, extract manually or use _extract_zip_files function"
                )

            # Flujo de salida específico para PDF
            self._handle_pdf_exit_flow()

            # Reset a pantalla inicial usando el logo
            self._reset_to_main_screen()

            return downloaded_files

        except Exception as e:
            self.logger.error(f"Error downloading PDF file: {str(e)}")
            return downloaded_files

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Bell usando el logo."""
        try:
            self.logger.info("Resetting to Bell initial screen...")
            logo_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/a[1]"
            self.browser_wrapper.click_element(logo_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            self.logger.info("Reset to Bell completed")
        except Exception as e:
            self.logger.error(f"Error in Bell reset: {str(e)}")
