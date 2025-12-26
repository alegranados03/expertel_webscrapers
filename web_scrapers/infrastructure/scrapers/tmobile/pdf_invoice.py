import os
import re
import time
from datetime import datetime
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    FileDownloadInfo,
    PDFInvoiceScraperStrategy,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class TMobilePDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para T-Mobile con logica de seleccion de periodo."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de billing y encuentra el primer row del account."""
        try:
            print("Navegando a la seccion de billing...")

            # 1. Click en billing section
            billing_section_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[1]/mat-accordion/mat-panel-title/mat-list-item"
            if not self.browser_wrapper.is_element_visible(billing_section_xpath, timeout=10000):
                print("Seccion de billing no encontrada")
                return None

            self.browser_wrapper.click_element(billing_section_xpath)
            time.sleep(3)

            # 2. Buscar y llenar el input de cuenta
            search_input_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div/div/app-billing/div/app-search/div/mat-form-field/div[1]/div/div[3]/input"
            if not self.browser_wrapper.is_element_visible(search_input_xpath, timeout=10000):
                print("Campo de busqueda no encontrado")
                return None

            print(f"Buscando cuenta: {billing_cycle.account.number}")
            self.browser_wrapper.fill_input(search_input_xpath, billing_cycle.account.number)
            time.sleep(1)

            # 3. Presionar Enter
            self.browser_wrapper.press_key(search_input_xpath, "Enter")
            time.sleep(5)

            # 4. Click en el primer row
            first_row_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-billing/div/section/div[1]/mat-grid-list"
            if not self.browser_wrapper.is_element_visible(first_row_xpath, timeout=10000):
                print("Primer row no encontrado")
                return None

            self.browser_wrapper.click_element(first_row_xpath)
            time.sleep(5)

            print("Seccion de facturas PDF encontrada")
            return {"section": "pdf_invoices", "account_number": billing_cycle.account.number}

        except Exception as e:
            print(f"Error navegando a seccion de archivos: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de T-Mobile con seleccion de periodo."""
        downloaded_files = []

        # Mapear BillingCyclePDFFile
        pdf_file = None
        if billing_cycle.pdf_files:
            pdf_file = billing_cycle.pdf_files[0]
            print(f"Archivo PDF encontrado: ID {pdf_file.id}")

        try:
            print("Iniciando descarga de facturas PDF...")

            # 1. Click en charges tab
            charges_tab_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/mat-tab-group/mat-tab-header/div/div/div/div[2]/div"
            if self.browser_wrapper.is_element_visible(charges_tab_xpath, timeout=10000):
                print("Haciendo click en charges tab...")
                self.browser_wrapper.click_element(charges_tab_xpath)
                time.sleep(3)
            else:
                print("Charges tab no encontrado, continuando...")

            # 2. Click en date selector
            date_selector_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/div/div/div[1]/mat-form-field/div[1]/div[2]/div/mat-select"
            if not self.browser_wrapper.is_element_visible(date_selector_xpath, timeout=10000):
                print("Date selector no encontrado")
                return downloaded_files

            print("Abriendo selector de fechas...")
            self.browser_wrapper.click_element(date_selector_xpath)
            time.sleep(3)

            # 3. Seleccionar el periodo mas cercano al billing_cycle.end_date
            selected_option = self._select_best_billing_period(billing_cycle.end_date)
            if not selected_option:
                print("No se pudo seleccionar el periodo de facturacion")
                return downloaded_files

            time.sleep(3)

            # 4. Click en view pdf bill
            view_pdf_button_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/button"
            if not self.browser_wrapper.is_element_visible(view_pdf_button_xpath, timeout=10000):
                print("Boton view pdf bill no encontrado")
                return downloaded_files

            print("Haciendo click en view PDF bill...")
            self.browser_wrapper.click_element(view_pdf_button_xpath)
            time.sleep(5)

            # 5. Click en detailed bill radio button
            detailed_radio_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[2]/div[2]/div/mat-dialog-container/div/div/download-bill-dialog/mat-dialog-content/mat-radio-group/mat-radio-button[2]/div/div/input"
            if self.browser_wrapper.is_element_visible(detailed_radio_xpath, timeout=10000):
                print("Seleccionando detailed bill...")
                self.browser_wrapper.click_element(detailed_radio_xpath)
                time.sleep(2)
            else:
                print("Detailed bill radio button no encontrado, continuando...")

            # 6. Click en download button
            download_button_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[2]/div[2]/div/mat-dialog-container/div/div/download-bill-dialog/mat-dialog-actions/button[2]"
            if not self.browser_wrapper.is_element_visible(download_button_xpath, timeout=10000):
                print("Boton de download no encontrado")
                return downloaded_files

            print("Iniciando descarga...")

            file_path = self.browser_wrapper.expect_download_and_click(
                download_button_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                print(f"PDF descargado: {actual_filename}")

                file_info = FileDownloadInfo(
                    file_id=pdf_file.id if pdf_file else 1,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    pdf_file=pdf_file,
                )
                downloaded_files.append(file_info)

                if pdf_file:
                    print(f"MAPEO CONFIRMADO: {actual_filename} -> BillingCyclePDFFile ID {pdf_file.id}")
            else:
                print("No se pudo descargar el PDF")

            # Reset a pantalla principal
            self._reset_to_main_screen()

            print(f"Descarga de PDF completada: {len(downloaded_files)} archivo(s)")
            return downloaded_files

        except Exception as e:
            print(f"Error durante descarga de PDF: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _select_best_billing_period(self, target_end_date: datetime) -> bool:
        """Selecciona el periodo de facturacion mas cercano al end_date del billing cycle."""
        try:
            print(f"Buscando periodo mas cercano a: {target_end_date}")

            # XPath del panel de opciones
            options_panel_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[2]/div[2]/div/div"

            if not self.browser_wrapper.is_element_visible(options_panel_xpath, timeout=10000):
                print("Panel de opciones no encontrado")
                return False

            # Obtener todas las opciones disponibles
            options = self.browser_wrapper.find_elements_by_xpath(f"{options_panel_xpath}//mat-option")

            if not options:
                print("No se encontraron opciones de periodos")
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

                    # Construir fecha aproximada del periodo
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

                        # Si el mes de fin es menor que el mes de inicio, el periodo cruza anos
                        period_year = current_year
                        if end_month_num < month_map.get(start_month, 1):
                            period_year = current_year + 1

                        period_end_date = datetime(period_year, end_month_num, int(end_day))

                        # Calcular que tan cerca esta esta fecha del target
                        date_diff = abs((period_end_date - target_end_date).days)

                        print(f"Opcion: {option_text} | End: {period_end_date} | Diff: {date_diff} dias")

                        if date_diff < best_match_score:
                            best_match_score = date_diff
                            best_option = option

                except Exception as e:
                    print(f"Error procesando opcion: {str(e)}")
                    continue

            if best_option:
                option_text = self.browser_wrapper.get_text_from_element(best_option)
                print(f"Seleccionando mejor opcion: {option_text} (diferencia: {best_match_score} dias)")
                self.browser_wrapper.click_element_direct(best_option)
                return True
            else:
                print("No se encontro una opcion valida")
                return False

        except Exception as e:
            print(f"Error seleccionando periodo: {str(e)}")
            return False

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de T-Mobile."""
        try:
            print("Reseteando a T-Mobile...")
            self.browser_wrapper.goto("https://b2b.t-mobile.com/")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("Reset completado")
        except Exception as e:
            print(f"Error en reset: {str(e)}")
