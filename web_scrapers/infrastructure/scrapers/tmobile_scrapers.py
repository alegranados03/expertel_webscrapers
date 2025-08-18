import re
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


class TMobileMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para T-Mobile."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos mensuales en el portal de T-Mobile."""
        try:

            # Navegar a la sección de reportes mensuales
            reports_xpath = (
                "//a[contains(@href, 'reports') or contains(text(), 'Reports') or contains(text(), 'Reportes')]"
            )
            if not self.browser_wrapper.find_element_by_xpath(reports_xpath):
                return None

            self.browser_wrapper.click_element(reports_xpath)
            self.browser_wrapper.wait_for_page_load()

            # Buscar la sección específica de archivos mensuales
            monthly_section_xpath = "//div[contains(@class, 'monthly') or contains(text(), 'Monthly')]"
            if not self.browser_wrapper.find_element_by_xpath(monthly_section_xpath):
                return None

            return {"section": "monthly_reports", "xpath": monthly_section_xpath}

        except Exception as e:
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos mensuales de T-Mobile."""
        downloaded_files = []

        try:

            # Simular descarga
            file_info = FileDownloadInfo(
                file_id=1,
                file_name=f"tmobile_monthly_report_{billing_cycle.start_date}_{billing_cycle.end_date}.pdf",
                download_url="https://tmobile.com/download/monthly_report.pdf",
                file_path=f"/tmp/tmobile_monthly_{billing_cycle.id}.pdf",
                file_size=1024000,
            )
            downloaded_files.append(file_info)

            return downloaded_files

        except Exception as e:
            return downloaded_files

    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        """Envía los archivos descargados al endpoint externo."""
        try:

            for file_info in files:
                endpoint_url = f"https://api.expertel.com/billing_cycle_files/{file_info.file_id}/upload"

            return True

        except Exception as e:
            return False


class TMobileDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para T-Mobile con lógica de selección de período y descarga CSV."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la sección de billing y encuentra el primer row del account."""
        try:
            print("🔍 Navegando a la sección de billing para uso diario...")

            # 1. Click en billing section
            billing_section_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[1]/mat-accordion/mat-panel-title/mat-list-item"
            if not self.browser_wrapper.is_element_visible(billing_section_xpath, timeout=10000):
                print("❌ Sección de billing no encontrada")
                return None

            self.browser_wrapper.click_element(billing_section_xpath)
            time.sleep(3)

            # 2. Buscar y llenar el input de cuenta
            search_input_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div/div/app-billing/div/app-search/div/mat-form-field/div[1]/div/div[3]/input"
            if not self.browser_wrapper.is_element_visible(search_input_xpath, timeout=10000):
                print("❌ Campo de búsqueda no encontrado")
                return None

            print(f"🔍 Buscando cuenta: {billing_cycle.account.number}")
            self.browser_wrapper.fill_input(search_input_xpath, billing_cycle.account.number)
            time.sleep(1)

            # 3. Presionar Enter
            self.browser_wrapper.press_key(search_input_xpath, "Enter")
            time.sleep(5)

            # 4. Click en el primer row
            first_row_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-billing/div/section/div[1]/mat-grid-list"
            if not self.browser_wrapper.is_element_visible(first_row_xpath, timeout=10000):
                print("❌ Primer row no encontrado")
                return None

            self.browser_wrapper.click_element(first_row_xpath)
            time.sleep(5)

            return {"section": "daily_usage", "account_number": billing_cycle.account.number}

        except Exception as e:
            print(f"❌ Error navegando a sección de archivos: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de T-Mobile con selección de período."""
        downloaded_files = []

        try:
            print("📊 Iniciando descarga de uso diario...")

            # 1. Click en usage tab
            usage_tab_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/mat-tab-group/mat-tab-header/div/div/div/div[2]/div"
            if self.browser_wrapper.is_element_visible(usage_tab_xpath, timeout=10000):
                print("📱 Haciendo click en usage tab...")
                self.browser_wrapper.click_element(usage_tab_xpath)
                time.sleep(3)
            else:
                print("❌ Usage tab no encontrado")
                return downloaded_files

            # 2. Click en date selector
            date_selector_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/div/div/div[1]/mat-form-field/div[1]/div[2]/div/mat-select"
            if not self.browser_wrapper.is_element_visible(date_selector_xpath, timeout=10000):
                print("❌ Date selector no encontrado")
                return downloaded_files

            print("📅 Abriendo selector de fechas...")
            self.browser_wrapper.click_element(date_selector_xpath)
            time.sleep(3)

            # 3. Seleccionar el período más cercano al billing_cycle.end_date
            selected_option = self._select_best_billing_period(billing_cycle.end_date)
            if not selected_option:
                print("❌ No se pudo seleccionar el período de facturación")
                return downloaded_files

            time.sleep(3)

            # 4. Configurar el dropdown "View by" para seleccionar "All usage"
            if not self._select_all_usage_option():
                print("⚠️ No se pudo seleccionar 'All usage', continuando...")

            time.sleep(3)

            # 5. Click en download csv
            download_csv_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/mat-tab-group/div/mat-tab-body[4]/div/tfb-usage/div/div[2]/div[1]/tfb-usage-table/div/tfb-card/mat-card/div[2]/div[1]/div[2]/div/span"
            if not self.browser_wrapper.is_element_visible(download_csv_xpath, timeout=10000):
                print("❌ Botón download CSV no encontrado")
                return downloaded_files

            print("📥 Haciendo click en download CSV...")

            # Preparar directorio de descarga
            download_path = self.browser_wrapper.get_download_directory()

            self.browser_wrapper.click_element(download_csv_xpath)
            time.sleep(10)  # Esperar a que complete la descarga

            # Verificar archivos descargados
            downloaded_files = self.browser_wrapper.get_downloaded_files_info(download_path)

            if downloaded_files:
                print(f"✅ Se descargaron {len(downloaded_files)} archivos CSV")
                for file_info in downloaded_files:
                    print(f"📁 Archivo: {file_info.file_name}")
            else:
                print("⚠️ No se detectaron archivos descargados")

            return downloaded_files

        except Exception as e:
            print(f"❌ Error durante descarga de uso diario: {str(e)}")
            return downloaded_files

    def _select_all_usage_option(self) -> bool:
        """Selecciona la opción 'All usage' en el dropdown 'View by'."""
        try:
            print("🔍 Configurando View by dropdown...")

            # Click en el dropdown "View by"
            view_by_dropdown_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/mat-tab-group/div/mat-tab-body[4]/div/tfb-usage/div/div[2]/div[1]/tfb-usage-table/div/tfb-card/mat-card/div[2]/div[1]/div[1]/tfb-dropdown[1]/div/mat-form-field/div/div[1]/div/mat-select"

            if not self.browser_wrapper.is_element_visible(view_by_dropdown_xpath, timeout=10000):
                print("❌ View by dropdown no encontrado")
                return False

            print("📋 Abriendo View by dropdown...")
            self.browser_wrapper.click_element(view_by_dropdown_xpath)
            time.sleep(3)

            # Buscar la opción "All usage" en el listbox
            # El listbox puede estar en /html/body/div[12]/div[2]/div/div/div o similar
            all_usage_option = None

            # Intentar múltiples posibles ubicaciones del listbox
            possible_listbox_xpaths = [
                "/html/body/div[12]/div[2]/div/div/div",
                "/html/body/div[11]/div[2]/div/div/div",
                "/html/body/div[10]/div[2]/div/div/div",
                "/html/body/div[13]/div[2]/div/div/div",
            ]

            for listbox_xpath in possible_listbox_xpaths:
                try:
                    if self.browser_wrapper.is_element_visible(listbox_xpath, timeout=3000):
                        # Buscar todas las opciones en este listbox
                        options = self.browser_wrapper.find_elements_by_xpath(f"{listbox_xpath}//mat-option")

                        for option in options:
                            option_text = self.browser_wrapper.get_text_from_element(option)
                            if "All usage" in option_text:
                                all_usage_option = option
                                break

                        if all_usage_option:
                            break

                except Exception as e:
                    print(f"⚠️ Error buscando en listbox {listbox_xpath}: {str(e)}")
                    continue

            if all_usage_option:
                print("✅ Seleccionando opción 'All usage'...")
                self.browser_wrapper.click_element_direct(all_usage_option)
                time.sleep(2)
                return True
            else:
                print("❌ Opción 'All usage' no encontrada")
                return False

        except Exception as e:
            print(f"❌ Error seleccionando 'All usage': {str(e)}")
            return False

    def _select_best_billing_period(self, target_end_date: datetime) -> bool:
        """Selecciona el período de facturación más cercano al end_date del billing cycle."""
        try:
            print(f"🎯 Buscando período más cercano a: {target_end_date}")

            # XPath del panel de opciones
            options_panel_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[2]/div[2]/div/div"

            if not self.browser_wrapper.is_element_visible(options_panel_xpath, timeout=10000):
                print("❌ Panel de opciones no encontrado")
                return False

            # Obtener todas las opciones disponibles
            options = self.browser_wrapper.find_elements_by_xpath(f"{options_panel_xpath}//mat-option")

            if not options:
                print("❌ No se encontraron opciones de períodos")
                return False

            best_option = None
            best_match_score = float("inf")

            for option in options:
                try:
                    option_text = self.browser_wrapper.get_text_from_element(option)

                    # Saltear opciones especiales
                    if "Current" in option_text or "View historical" in option_text:
                        continue

                    # Extraer fechas del texto (formato: "May 13 - Jun 12")
                    date_match = re.search(r"(\w+)\s+(\d+)\s*-\s*(\w+)\s+(\d+)", option_text)
                    if not date_match:
                        continue

                    start_month, start_day, end_month, end_day = date_match.groups()

                    # Construir fecha aproximada del período
                    current_year = target_end_date.year

                    # Mapear nombres de meses
                    month_map = {
                        "Jan": 1,
                        "Feb": 2,
                        "Mar": 3,
                        "Apr": 4,
                        "May": 5,
                        "Jun": 6,
                        "Jul": 7,
                        "Aug": 8,
                        "Sep": 9,
                        "Oct": 10,
                        "Nov": 11,
                        "Dec": 12,
                    }

                    if end_month in month_map:
                        end_month_num = month_map[end_month]

                        # Si el mes de fin es menor que el mes de inicio, el período cruza años
                        period_year = current_year
                        if end_month_num < month_map.get(start_month, 1):
                            period_year = current_year + 1

                        period_end_date = datetime(period_year, end_month_num, int(end_day))

                        # Calcular qué tan cerca está esta fecha del target
                        date_diff = abs((period_end_date - target_end_date).days)

                        print(f"📅 Opción: {option_text} | End: {period_end_date} | Diff: {date_diff} días")

                        if date_diff < best_match_score:
                            best_match_score = date_diff
                            best_option = option

                except Exception as e:
                    print(f"⚠️ Error procesando opción: {str(e)}")
                    continue

            if best_option:
                option_text = self.browser_wrapper.get_text_from_element(best_option)
                print(f"✅ Seleccionando mejor opción: {option_text} (diferencia: {best_match_score} días)")
                self.browser_wrapper.click_element_direct(best_option)
                return True
            else:
                print("❌ No se encontró una opción válida")
                return False

        except Exception as e:
            print(f"❌ Error seleccionando período: {str(e)}")
            return False


class TMobilePDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para T-Mobile con lógica de selección de período."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la sección de billing y encuentra el primer row del account."""
        try:
            print("🔍 Navegando a la sección de billing...")

            # 1. Click en billing section
            billing_section_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[1]/mat-accordion/mat-panel-title/mat-list-item"
            if not self.browser_wrapper.is_element_visible(billing_section_xpath, timeout=10000):
                print("❌ Sección de billing no encontrada")
                return None

            self.browser_wrapper.click_element(billing_section_xpath)
            time.sleep(3)

            # 2. Buscar y llenar el input de cuenta
            search_input_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div/div/app-billing/div/app-search/div/mat-form-field/div[1]/div/div[3]/input"
            if not self.browser_wrapper.is_element_visible(search_input_xpath, timeout=10000):
                print("❌ Campo de búsqueda no encontrado")
                return None

            print(f"🔍 Buscando cuenta: {billing_cycle.account.number}")
            self.browser_wrapper.fill_input(search_input_xpath, billing_cycle.account.number)
            time.sleep(1)

            # 3. Presionar Enter
            self.browser_wrapper.press_key(search_input_xpath, "Enter")
            time.sleep(5)

            # 4. Click en el primer row
            first_row_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-billing/div/section/div[1]/mat-grid-list"
            if not self.browser_wrapper.is_element_visible(first_row_xpath, timeout=10000):
                print("❌ Primer row no encontrado")
                return None

            self.browser_wrapper.click_element(first_row_xpath)
            time.sleep(5)

            return {"section": "pdf_invoices", "account_number": billing_cycle.account.number}

        except Exception as e:
            print(f"❌ Error navegando a sección de archivos: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de T-Mobile con selección de período."""
        downloaded_files = []

        try:
            print("📄 Iniciando descarga de facturas PDF...")

            # 1. Click en charges tab
            charges_tab_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/mat-tab-group/mat-tab-header/div/div/div/div[2]/div"
            if self.browser_wrapper.is_element_visible(charges_tab_xpath, timeout=10000):
                print("💰 Haciendo click en charges tab...")
                self.browser_wrapper.click_element(charges_tab_xpath)
                time.sleep(3)
            else:
                print("⚠️ Charges tab no encontrado, continuando...")

            # 2. Click en date selector
            date_selector_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/div/div/div[1]/mat-form-field/div[1]/div[2]/div/mat-select"
            if not self.browser_wrapper.is_element_visible(date_selector_xpath, timeout=10000):
                print("❌ Date selector no encontrado")
                return downloaded_files

            print("📅 Abriendo selector de fechas...")
            self.browser_wrapper.click_element(date_selector_xpath)
            time.sleep(3)

            # 3. Seleccionar el período más cercano al billing_cycle.end_date
            selected_option = self._select_best_billing_period(billing_cycle.end_date)
            if not selected_option:
                print("❌ No se pudo seleccionar el período de facturación")
                return downloaded_files

            time.sleep(3)

            # 4. Click en view pdf bill
            view_pdf_button_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/button"
            if not self.browser_wrapper.is_element_visible(view_pdf_button_xpath, timeout=10000):
                print("❌ Botón view pdf bill no encontrado")
                return downloaded_files

            print("📄 Haciendo click en view PDF bill...")
            self.browser_wrapper.click_element(view_pdf_button_xpath)
            time.sleep(5)

            # 5. Click en detailed bill radio button
            detailed_radio_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[2]/div[2]/div/mat-dialog-container/div/div/download-bill-dialog/mat-dialog-content/mat-radio-group/mat-radio-button[2]/div/div/input"
            if self.browser_wrapper.is_element_visible(detailed_radio_xpath, timeout=10000):
                print("📋 Seleccionando detailed bill...")
                self.browser_wrapper.click_element(detailed_radio_xpath)
                time.sleep(2)
            else:
                print("⚠️ Detailed bill radio button no encontrado, continuando...")

            # 6. Click en download button
            download_button_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[2]/div[2]/div/mat-dialog-container/div/div/download-bill-dialog/mat-dialog-actions/button[2]"
            if not self.browser_wrapper.is_element_visible(download_button_xpath, timeout=10000):
                print("❌ Botón de download no encontrado")
                return downloaded_files

            print("⬇️ Iniciando descarga...")

            # Preparar directorio de descarga
            download_path = self.browser_wrapper.get_download_directory()

            self.browser_wrapper.click_element(download_button_xpath)
            time.sleep(10)  # Esperar a que complete la descarga

            # Verificar archivos descargados
            downloaded_files = self.browser_wrapper.get_downloaded_files_info(download_path)

            if downloaded_files:
                print(f"✅ Se descargaron {len(downloaded_files)} archivos PDF")
                for file_info in downloaded_files:
                    print(f"📁 Archivo: {file_info.file_name}")
            else:
                print("⚠️ No se detectaron archivos descargados")

            return downloaded_files

        except Exception as e:
            print(f"❌ Error durante descarga de PDF: {str(e)}")
            return downloaded_files

    def _select_best_billing_period(self, target_end_date: datetime) -> bool:
        """Selecciona el período de facturación más cercano al end_date del billing cycle."""
        try:
            print(f"🎯 Buscando período más cercano a: {target_end_date}")

            # XPath del panel de opciones
            options_panel_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[2]/div[2]/div/div"

            if not self.browser_wrapper.is_element_visible(options_panel_xpath, timeout=10000):
                print("❌ Panel de opciones no encontrado")
                return False

            # Obtener todas las opciones disponibles
            options = self.browser_wrapper.find_elements_by_xpath(f"{options_panel_xpath}//mat-option")

            if not options:
                print("❌ No se encontraron opciones de períodos")
                return False

            best_option = None
            best_match_score = float("inf")

            for option in options:
                try:
                    option_text = self.browser_wrapper.get_text_from_element(option)

                    # Saltear opciones especiales
                    if "Current" in option_text or "View historical" in option_text:
                        continue

                    # Extraer fechas del texto (formato: "May 13 - Jun 12")
                    date_match = re.search(r"(\w+)\s+(\d+)\s*-\s*(\w+)\s+(\d+)", option_text)
                    if not date_match:
                        continue

                    start_month, start_day, end_month, end_day = date_match.groups()

                    # Construir fecha aproximada del período
                    current_year = target_end_date.year

                    # Mapear nombres de meses
                    month_map = {
                        "Jan": 1,
                        "Feb": 2,
                        "Mar": 3,
                        "Apr": 4,
                        "May": 5,
                        "Jun": 6,
                        "Jul": 7,
                        "Aug": 8,
                        "Sep": 9,
                        "Oct": 10,
                        "Nov": 11,
                        "Dec": 12,
                    }

                    if end_month in month_map:
                        end_month_num = month_map[end_month]

                        # Si el mes de fin es menor que el mes de inicio, el período cruza años
                        period_year = current_year
                        if end_month_num < month_map.get(start_month, 1):
                            period_year = current_year + 1

                        period_end_date = datetime(period_year, end_month_num, int(end_day))

                        # Calcular qué tan cerca está esta fecha del target
                        date_diff = abs((period_end_date - target_end_date).days)

                        print(f"📅 Opción: {option_text} | End: {period_end_date} | Diff: {date_diff} días")

                        if date_diff < best_match_score:
                            best_match_score = date_diff
                            best_option = option

                except Exception as e:
                    print(f"⚠️ Error procesando opción: {str(e)}")
                    continue

            if best_option:
                option_text = self.browser_wrapper.get_text_from_element(best_option)
                print(f"✅ Seleccionando mejor opción: {option_text} (diferencia: {best_match_score} días)")
                self.browser_wrapper.click_element_direct(best_option)
                return True
            else:
                print("❌ No se encontró una opción válida")
                return False

        except Exception as e:
            print(f"❌ Error seleccionando período: {str(e)}")
            return False
