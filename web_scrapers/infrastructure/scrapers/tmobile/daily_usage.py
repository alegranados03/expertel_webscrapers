import os
import re
import time
from datetime import datetime
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    DailyUsageScraperStrategy,
    FileDownloadInfo,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class TMobileDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para T-Mobile con logica de seleccion de periodo y descarga CSV."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de billing y encuentra el primer row del account."""
        try:
            print("Navegando a la seccion de billing para uso diario...")

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

            print("Seccion de uso diario encontrada")
            return {"section": "daily_usage", "account_number": billing_cycle.account.number}

        except Exception as e:
            print(f"Error navegando a seccion de archivos: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de T-Mobile con seleccion de periodo."""
        downloaded_files = []

        # Mapear BillingCycleDailyUsageFile
        daily_usage_file = None
        if billing_cycle.daily_usage_files:
            daily_usage_file = billing_cycle.daily_usage_files[0]
            print(f"Archivo de uso diario encontrado: ID {daily_usage_file.id}")

        try:
            print("Iniciando descarga de uso diario...")

            # 1. Click en usage tab
            usage_tab_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/mat-tab-group/mat-tab-header/div/div/div/div[2]/div"
            if self.browser_wrapper.is_element_visible(usage_tab_xpath, timeout=10000):
                print("Haciendo click en usage tab...")
                self.browser_wrapper.click_element(usage_tab_xpath)
                time.sleep(3)
            else:
                print("Usage tab no encontrado")
                return downloaded_files

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

            # 4. Configurar el dropdown "View by" para seleccionar "All usage"
            if not self._select_all_usage_option():
                print("No se pudo seleccionar 'All usage', continuando...")

            time.sleep(3)

            # 5. Click en download csv
            download_csv_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/mat-tab-group/div/mat-tab-body[4]/div/tfb-usage/div/div[2]/div[1]/tfb-usage-table/div/tfb-card/mat-card/div[2]/div[1]/div[2]/div/span"
            if not self.browser_wrapper.is_element_visible(download_csv_xpath, timeout=10000):
                print("Boton download CSV no encontrado")
                return downloaded_files

            print("Haciendo click en download CSV...")

            file_path = self.browser_wrapper.expect_download_and_click(
                download_csv_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                print(f"Archivo descargado: {actual_filename}")

                file_info = FileDownloadInfo(
                    file_id=daily_usage_file.id if daily_usage_file else 1,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    daily_usage_file=daily_usage_file,
                )
                downloaded_files.append(file_info)

                if daily_usage_file:
                    print(f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleDailyUsageFile ID {daily_usage_file.id}")
            else:
                print("No se pudo descargar el archivo CSV")

            # Reset a pantalla principal
            self._reset_to_main_screen()

            print(f"Descarga de uso diario completada: {len(downloaded_files)} archivo(s)")
            return downloaded_files

        except Exception as e:
            print(f"Error durante descarga de uso diario: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _select_all_usage_option(self) -> bool:
        """Selecciona la opcion 'All usage' en el dropdown 'View by'."""
        try:
            print("Configurando View by dropdown...")

            # Click en el dropdown "View by"
            view_by_dropdown_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/mat-tab-group/div/mat-tab-body[4]/div/tfb-usage/div/div[2]/div[1]/tfb-usage-table/div/tfb-card/mat-card/div[2]/div[1]/div[1]/tfb-dropdown[1]/div/mat-form-field/div/div[1]/div/mat-select"

            if not self.browser_wrapper.is_element_visible(view_by_dropdown_xpath, timeout=10000):
                print("View by dropdown no encontrado")
                return False

            print("Abriendo View by dropdown...")
            self.browser_wrapper.click_element(view_by_dropdown_xpath)
            time.sleep(3)

            # Buscar la opcion "All usage" en el listbox
            all_usage_option = None

            # Intentar multiples posibles ubicaciones del listbox
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
                    print(f"Error buscando en listbox {listbox_xpath}: {str(e)}")
                    continue

            if all_usage_option:
                print("Seleccionando opcion 'All usage'...")
                self.browser_wrapper.click_element_direct(all_usage_option)
                time.sleep(2)
                return True
            else:
                print("Opcion 'All usage' no encontrada")
                return False

        except Exception as e:
            print(f"Error seleccionando 'All usage': {str(e)}")
            return False

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
                        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
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