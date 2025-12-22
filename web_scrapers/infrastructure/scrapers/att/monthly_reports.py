import calendar
import os
import time
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
    """Scraper de reportes mensuales para AT&T con 5 reportes específicos."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)
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
                print(f"Buscando seccion de archivos AT&T (intento {attempt + 1}/{max_retries + 1})")

                # 1. Click en billing header y esperar 2 minutos
                billing_header_xpath = "/html/body/div[1]/div/ul/li[3]/a"
                print("Haciendo clic en Billing header...")
                self.browser_wrapper.click_element(billing_header_xpath)
                time.sleep(120)  # Esperar 2 minutos como especificado

                # 2. Click en reports tab
                reports_tab_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[4]/a/span"
                print("Haciendo clic en Reports tab...")
                self.browser_wrapper.click_element(reports_tab_xpath)
                time.sleep(3)

                # 3. Click en detail option
                detail_option_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[4]/ul/li[3]/a"
                print("Haciendo clic en Detail option...")
                self.browser_wrapper.click_element(detail_option_xpath)
                time.sleep(5)

                # 4. Verificar que encontramos la sección correcta
                charges_tab_section_xpath = "/html/body/div[1]/main/div[2]/form/div/div[1]/ul/li[1]/a/span"
                if self.browser_wrapper.is_element_visible(charges_tab_section_xpath, timeout=10000):
                    # Verificar que el texto sea "Charges and usage"
                    section_text = self.browser_wrapper.get_text(charges_tab_section_xpath)
                    if section_text and "Charges and usage" in section_text:
                        print("Seccion de reportes encontrada exitosamente")
                        return {"section": "monthly_reports", "ready_for_download": True}
                    else:
                        print(f"Texto de seccion no coincide: {section_text}")
                        continue
                else:
                    print("No se encontro la seccion de reportes")
                    continue

            except Exception as e:
                print(f"Error en intento {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    continue

        print("No se pudo encontrar la seccion de archivos despues de todos los intentos")
        return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los 5 archivos mensuales de AT&T."""
        downloaded_files = []

        # Mapeo de slugs a nombres de reportes y configuraciones
        # Slugs activos: wireless_charges, usage_details, monthly_charges, device_installment, upgrade_and_inventory
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

        # Mapear BillingCycleFiles por slug del carrier_report para asociación exacta
        billing_cycle_file_map = {}
        if billing_cycle.billing_cycle_files:
            for bcf in billing_cycle.billing_cycle_files:
                if bcf.carrier_report and bcf.carrier_report.slug:
                    slug = bcf.carrier_report.slug
                    billing_cycle_file_map[slug] = bcf
                    print(f"Mapeado BillingCycleFile: {slug} -> ID {bcf.id}")

        try:
            # 1. Click en charges tab
            charges_tab_xpath = "/html/body/div[1]/main/div[2]/form/div/div[1]/ul/li[1]/a"
            print("Haciendo clic en Charges tab...")
            self.browser_wrapper.click_element(charges_tab_xpath)
            time.sleep(3)

            # 2. Configurar fecha
            self._configure_date_range(billing_cycle)

            # 3. Procesar reportes de la pestaña Charges
            charges_reports = [slug for slug, config in slug_to_report_config.items() if config["tab"] == "charges"]
            for slug in charges_reports:
                self._download_single_report(
                    slug, slug_to_report_config[slug], billing_cycle_file_map, downloaded_files
                )

            # 4. Cambiar a pestaña Unbilled Usage
            print("\nCambiando a pestana Unbilled Usage...")
            unbilled_tab_xpath = "/html/body/div[1]/main/div[2]/form/div/div[1]/ul/li[3]/a"
            self.browser_wrapper.click_element(unbilled_tab_xpath)
            time.sleep(3)

            # 5. Procesar reportes de la pestaña Unbilled
            unbilled_reports = [slug for slug, config in slug_to_report_config.items() if config["tab"] == "unbilled"]
            for slug in unbilled_reports:
                self._download_single_report(
                    slug, slug_to_report_config[slug], billing_cycle_file_map, downloaded_files
                )

            # 6. Reset a pantalla principal
            self._reset_to_main_screen()

            print(f"\nDescarga completada. Total archivos: {len(downloaded_files)}")
            return downloaded_files

        except Exception as e:
            print(f"Error durante descarga de archivos: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _configure_date_range(self, billing_cycle: BillingCycle):
        """Configura el rango de fechas basado en el billing cycle."""
        try:
            print(f"Configurando fecha para periodo: {billing_cycle.end_date}")

            # 1. Click en date dropdown
            date_dropdown_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/button"
            self.browser_wrapper.click_element(date_dropdown_xpath)
            time.sleep(2)

            # 2. Click en option dropdown
            option_dropdown_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/div/div/div[2]/div/div[1]/select"
            self.browser_wrapper.click_element(option_dropdown_xpath)
            time.sleep(1)

            # 3. Determinar la opción correcta basada en end_date
            end_date = billing_cycle.end_date
            month_name = calendar.month_name[end_date.month]
            year = end_date.year
            option_text = f"{month_name} {year} bills"

            print(f"Buscando opcion: {option_text}")

            # 4. Seleccionar la opción correcta
            select_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/div/div/div[2]/div/div[1]/select"
            self.browser_wrapper.select_dropdown_option(select_xpath, option_text)
            time.sleep(1)

            # 5. Apply date changes
            apply_button_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/div/div/div[2]/div/div[5]/button"
            print("Aplicando cambios de fecha...")
            self.browser_wrapper.click_element(apply_button_xpath)
            time.sleep(5)

        except Exception as e:
            print(f"Error configurando fecha: {str(e)}")

    def _download_single_report(
        self, slug: str, report_config: dict, billing_cycle_file_map: dict, downloaded_files: list
    ):
        """Descarga un reporte individual."""
        try:
            print(f"\nProcesando reporte: {report_config['name']} (slug: {slug})")

            # 1. Click en la sección del reporte
            section_xpath = report_config["section_xpath"]

            # Verificar que el texto del botón coincida
            if self.browser_wrapper.is_element_visible(section_xpath, timeout=5000):
                button_text = self.browser_wrapper.get_text(section_xpath)
                if button_text and report_config["text_to_verify"] in button_text:
                    print(f"Texto verificado: '{button_text}'")
                    self.browser_wrapper.click_element(section_xpath)
                    time.sleep(3)
                else:
                    print(
                        f"Texto no coincide para {slug}. Esperado: '{report_config['text_to_verify']}', Encontrado: '{button_text}'. Saltando..."
                    )
                    return
            else:
                print(f"Seccion no encontrada para {slug}. Saltando...")
                return

            # 2. Click en download report
            download_button_xpath = "/html/body/div[1]/main/div[2]/form/div[2]/div[2]/div/div/button[2]"
            print("Haciendo clic en Download Report...")
            self.browser_wrapper.click_element(download_button_xpath)
            time.sleep(2)

            # 3. Click en CSV option
            csv_option_xpath = "/html/body/div[1]/div[3]/div/div/div[2]/form/div[1]/div/div/fieldset/label[2]"
            print("Seleccionando opcion CSV...")
            self.browser_wrapper.click_element(csv_option_xpath)
            time.sleep(1)

            # 4. Click en OK button y esperar descarga
            ok_button_xpath = "/html/body/div[1]/div[3]/div/div/div[3]/button[1]"
            print("Haciendo clic en OK...")

            file_path = self.browser_wrapper.expect_download_and_click(
                ok_button_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                print(f"Archivo descargado: {actual_filename}")

                # Buscar BillingCycleFile correspondiente
                corresponding_bcf = billing_cycle_file_map.get(slug)

                # Crear FileDownloadInfo
                file_download_info = FileDownloadInfo(
                    file_id=corresponding_bcf.id if corresponding_bcf else len(downloaded_files) + 1,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    billing_cycle_file=corresponding_bcf,
                )
                downloaded_files.append(file_download_info)

                if corresponding_bcf:
                    print(
                        f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id} (Slug: '{slug}')"
                    )
                else:
                    print(f"Archivo descargado sin mapeo especifico de BillingCycleFile")
            else:
                print(f"No se pudo descargar el archivo para {slug}")

            # 5. Go back
            go_back_xpath = "/html/body/div[1]/main/div[2]/form/div[1]/div[1]/a"
            print("Regresando...")
            self.browser_wrapper.click_element(go_back_xpath)
            time.sleep(3)

        except Exception as e:
            print(f"Error descargando reporte {slug}: {str(e)}")
            # Intentar volver
            try:
                go_back_xpath = "/html/body/div[1]/main/div[2]/form/div[1]/div[1]/a"
                self.browser_wrapper.click_element(go_back_xpath)
                time.sleep(2)
            except:
                pass

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de AT&T."""
        try:
            print("Reseteando a pantalla inicial de AT&T...")
            self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("Reset a AT&T completado")
        except Exception as e:
            print(f"Error en reset de AT&T: {str(e)}")