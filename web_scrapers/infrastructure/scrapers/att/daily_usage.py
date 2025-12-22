import os
import time
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    DailyUsageScraperStrategy,
    FileDownloadInfo,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class ATTDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para AT&T."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la seccion de archivos de uso diario en el portal de AT&T."""
        return self._find_files_section_with_retry(config, billing_cycle, max_retries=1)

    def _find_files_section_with_retry(
        self, config: ScraperConfig, billing_cycle: BillingCycle, max_retries: int = 1
    ) -> Optional[Any]:
        """Busca la seccion de archivos de uso diario con reintento automatico."""
        for attempt in range(max_retries + 1):
            try:
                print(f"Buscando seccion de uso diario AT&T (intento {attempt + 1}/{max_retries + 1})")

                # 1. Click en reports tab y esperar 1 minuto
                reports_tab_xpath = "/html/body/div[1]/div/ul/li[4]/a"
                print("Haciendo clic en Reports tab...")
                self.browser_wrapper.click_element(reports_tab_xpath)
                time.sleep(60)  # Esperar 1 minuto como especificado

                # 2. Click en reports section y esperar 1 minuto
                reports_section_xpath = "/html/body/div[1]/div/div[17]/div/div[2]/div[1]"
                print("Haciendo clic en Reports section...")
                self.browser_wrapper.click_element(reports_section_xpath)
                time.sleep(60)  # Esperar 1 minuto como especificado

                # 3. Click en internal reports tab
                internal_reports_tab_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[4]/a"
                print("Haciendo clic en Internal reports tab...")
                self.browser_wrapper.click_element(internal_reports_tab_xpath)
                time.sleep(3)

                # 4. Click en summary option
                summary_option_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[4]/ul/li[2]/a"
                print("Haciendo clic en Summary option...")
                self.browser_wrapper.click_element(summary_option_xpath)
                time.sleep(5)

                # 5. Verificar que encontramos la seccion correcta
                charges_tab_section_xpath = "/html/body/div[1]/main/form/div[2]/div[3]/div[1]/ul/li[1]/a/span"
                if self.browser_wrapper.is_element_visible(charges_tab_section_xpath, timeout=10000):
                    # Verificar que el texto sea "Charges and usage"
                    section_text = self.browser_wrapper.get_text(charges_tab_section_xpath)
                    if section_text and "Charges and usage" in section_text:
                        print("Seccion de uso diario encontrada exitosamente")
                        return {"section": "daily_usage", "ready_for_download": True}
                    else:
                        print(f"Texto de seccion no coincide: {section_text}")
                        continue
                else:
                    print("No se encontro la seccion de uso diario")
                    continue

            except Exception as e:
                print(f"Error en intento {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    continue

        print("No se pudo encontrar la seccion de uso diario despues de todos los intentos")
        return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de AT&T."""
        downloaded_files = []

        # Mapear BillingCycleDailyUsageFile
        daily_usage_file = None
        if billing_cycle.daily_usage_files:
            daily_usage_file = billing_cycle.daily_usage_files[0]
            print(f"Archivo de uso diario encontrado: ID {daily_usage_file.id}")

        try:
            print("Descargando archivo de uso diario...")

            # 1. Click en unbilled usage tab
            unbilled_tab_xpath = "/html/body/div[1]/main/form/div[2]/div[3]/div[1]/ul/li[2]/a"
            print("Haciendo clic en Unbilled usage tab...")
            self.browser_wrapper.click_element(unbilled_tab_xpath)
            time.sleep(3)

            # 2. Click en unbilled usage report section y esperar 1 minuto
            unbilled_report_xpath = (
                "/html/body/div[1]/main/form/div[2]/div[3]/div[2]/div[3]/div/div/div[2]/ul/li/button"
            )
            print("Haciendo clic en Unbilled usage report section...")
            self.browser_wrapper.click_element(unbilled_report_xpath)
            time.sleep(60)  # Esperar 1 minuto como especificado

            # 3. Click en download
            download_button_xpath = "/html/body/div[1]/main/div[2]/form/div[2]/div[2]/div/div/button[4]"
            print("Haciendo clic en Download...")
            self.browser_wrapper.click_element(download_button_xpath)
            time.sleep(2)

            # 4. Click en csv option
            csv_option_xpath = "/html/body/div[1]/div[1]/div/div/div[2]/form/div[1]/div/div/fieldset/label[2]"
            print("Seleccionando opcion CSV...")
            self.browser_wrapper.click_element(csv_option_xpath)
            time.sleep(1)

            # 5. Click en OK button y esperar descarga
            ok_button_xpath = "/html/body/div[1]/div[1]/div/div/div[3]/button[1]"
            print("Haciendo clic en OK...")

            file_path = self.browser_wrapper.expect_download_and_click(
                ok_button_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                print(f"Archivo descargado: {actual_filename}")

                # Crear FileDownloadInfo
                file_download_info = FileDownloadInfo(
                    file_id=daily_usage_file.id if daily_usage_file else 1,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    daily_usage_file=daily_usage_file,
                )
                downloaded_files.append(file_download_info)

                if daily_usage_file:
                    print(
                        f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleDailyUsageFile ID {daily_usage_file.id}"
                    )
                else:
                    print("Archivo descargado sin mapeo especifico de BillingCycleDailyUsageFile")
            else:
                print("No se pudo descargar el archivo de uso diario")

            # 6. Reset a pantalla principal
            self._reset_to_main_screen()

            print(f"Descarga de uso diario completada: {len(downloaded_files)} archivo(s)")
            return downloaded_files

        except Exception as e:
            print(f"Error descargando archivos de uso diario: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

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