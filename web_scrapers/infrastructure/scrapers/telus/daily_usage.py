import os
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


class TelusDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para Telus."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de uso diario en Telus IQ."""
        try:
            print("Navegando a Telus IQ para uso diario...")

            # 1. Verificar que estamos en My Telus
            current_url = self.browser_wrapper.get_current_url()
            if "my-telus" not in current_url:
                print("Navegando a My Telus...")
                self.browser_wrapper.goto("https://www.telus.com/my-telus")
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)

            # 2. Click en Telus IQ button y esperar 30 segundos
            telus_iq_xpath = "/html/body/div[5]/div/div/div/div[1]/div/div[3]/div/div/div/div/div/div/div[3]/div/div/a"
            print("Click en Telus IQ button...")
            self.browser_wrapper.click_element(telus_iq_xpath)
            print("Esperando 30 segundos...")
            time.sleep(30)

            # 3. Verificar si aparece el boton "don't show again" y hacer click si existe
            dont_show_again_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div/div[2]/div[2]/div[1]/div/div/div[3]/div/div[2]/p/div/a"
            try:
                if self.browser_wrapper.find_element_by_xpath(dont_show_again_xpath, timeout=5000):
                    print("Click en don't show again button...")
                    self.browser_wrapper.click_element(dont_show_again_xpath)
                    time.sleep(2)
                else:
                    print("Don't show again button no aparecio, continuando...")
            except:
                print("Don't show again button no encontrado, continuando...")

            # 4. Click en manage tab
            manage_tab_xpath = "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/ul[1]/li[2]/a[1]/span[1]/span[1]"
            print("Click en manage tab...")
            self.browser_wrapper.click_element(manage_tab_xpath)
            time.sleep(3)

            # 5. Click en usage view option y esperar 30 segundos
            usage_view_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div/div[1]/div/div[2]/div/div/div/div/div[2]/div[1]/div[3]/div/a/span/span[1]/div/span"
            print("Click en usage view option...")
            self.browser_wrapper.click_element(usage_view_xpath)
            print("Esperando 30 segundos...")
            time.sleep(30)

            print("Navegacion a Telus IQ completada")
            return {"section": "daily_usage", "ready_for_export": True}

        except Exception as e:
            print(f"Error navegando a Telus IQ: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de Telus IQ."""
        downloaded_files = []

        # Obtener el BillingCycleDailyUsageFile del billing_cycle
        daily_usage_file = billing_cycle.daily_usage_files[0] if billing_cycle.daily_usage_files else None
        if daily_usage_file:
            print(f"Mapeando archivo Daily Usage -> BillingCycleDailyUsageFile ID {daily_usage_file.id}")

        try:
            print("Iniciando proceso de exportacion...")

            # 1. Click en export view button
            export_view_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div[3]/div[1]/div[11]/div[2]/div/div[2]/div/div[2]/div/a"
            print("Click en export view button...")
            self.browser_wrapper.click_element(export_view_xpath)
            time.sleep(3)

            # 2. Generar nombre del reporte con formato daily_usage_yyyy-mm-dd
            current_date = datetime.now()
            report_name = f"daily_usage_{current_date.strftime('%Y-%m-%d')}"
            print(f"Nombre del reporte: {report_name}")

            # 3. Escribir en report view modal input
            report_input_xpath = "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/input[1]"
            self.browser_wrapper.clear_and_type(report_input_xpath, report_name)
            time.sleep(2)

            # 4. Click en continue button y esperar 2 minutos
            continue_button_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div[2]/div/div[2]/a[2]"
            print("Click en continue button...")
            self.browser_wrapper.click_element(continue_button_xpath)
            print("Esperando 2 minutos...")
            time.sleep(120)

            # 5. Verificar results table y monitorear descarga
            download_info = self._monitor_results_table_and_download(report_name, daily_usage_file)

            if download_info:
                downloaded_files.append(download_info)
                print(f"Reporte descargado: {download_info.file_name}")
            else:
                print("No se pudo descargar el reporte")

            # 6. Reset a pantalla principal
            self._reset_to_main_screen()

            return downloaded_files

        except Exception as e:
            print(f"Error en descarga de uso diario: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _monitor_results_table_and_download(self, report_name: str, daily_usage_file) -> Optional[FileDownloadInfo]:
        """Monitorea la tabla de resultados y descarga cuando este listo."""
        max_attempts = 10  # Maximo 10 reintentos
        attempt = 0

        while attempt < max_attempts:
            try:
                attempt += 1
                print(f"Intento {attempt}/{max_attempts} - Verificando results table...")

                # Verificar si existe la results table
                results_table_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div[2]/div/div[3]"

                if not self.browser_wrapper.find_element_by_xpath(results_table_xpath, timeout=10000):
                    print("Results table no aparecio, refrescando pagina...")
                    self.browser_wrapper.refresh()
                    print("Esperando 1 minuto despues del refresh...")
                    time.sleep(60)
                    continue

                print("Results table encontrada")

                # Buscar nuestro reporte en la primera fila por nombre
                first_row_name_xpath = "//div[@class='new__dynamic__table__column'][2]//div[@class='new-dynamic-table__table__cell'][1]//span"

                if not self.browser_wrapper.find_element_by_xpath(first_row_name_xpath):
                    print("Primera fila no encontrada, esperando...")
                    time.sleep(60)
                    continue

                name_text = self.browser_wrapper.get_text(first_row_name_xpath)
                print(f"Nombre en primera fila: {name_text}")

                if report_name not in name_text:
                    print(f"Reporte '{report_name}' no encontrado en primera fila, esperando...")
                    time.sleep(60)
                    continue

                print(f"Reporte '{report_name}' encontrado en primera fila")

                # Verificar el estado en la columna Status (columna 3)
                first_row_status_xpath = "//div[@class='new__dynamic__table__column'][3]//div[@class='new-dynamic-table__table__cell'][1]//span"

                if not self.browser_wrapper.find_element_by_xpath(first_row_status_xpath):
                    print("Estado no encontrado, esperando...")
                    time.sleep(60)
                    continue

                status_element = self.browser_wrapper.get_text(first_row_status_xpath)
                print(f"Estado del reporte: {status_element}")

                # Verificar si contiene enlace de descarga
                download_link_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div[2]/div/div[3]/div[2]/div[1]/div[3]/div[1]//a[@class='new-dynamic-table__table__cell__download-anchor']"

                if self.browser_wrapper.find_element_by_xpath(download_link_xpath):
                    link_text = self.browser_wrapper.get_text(download_link_xpath)
                    print(f"Enlace encontrado: {link_text}")

                    if "Download" in link_text:
                        print("Reporte listo para descarga!")

                        # Descargar archivo
                        downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                            download_link_xpath, timeout=30000, downloads_dir=self.job_downloads_dir
                        )

                        if downloaded_file_path:
                            actual_filename = os.path.basename(downloaded_file_path)
                            file_size = (
                                os.path.getsize(downloaded_file_path)
                                if os.path.exists(downloaded_file_path)
                                else 1024000
                            )

                            print(f"Archivo descargado: {actual_filename}")

                            file_info = FileDownloadInfo(
                                file_id=daily_usage_file.id if daily_usage_file else 1,
                                file_name=actual_filename,
                                download_url="N/A",
                                file_path=downloaded_file_path,
                                daily_usage_file=daily_usage_file,
                            )

                            if daily_usage_file:
                                print(
                                    f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleDailyUsageFile ID {daily_usage_file.id}"
                                )

                            return file_info
                        else:
                            print("Error en descarga")
                            return None
                    elif "In Queue" in link_text:
                        print("Reporte en cola, esperando 1 minuto mas...")
                        time.sleep(60)
                        continue
                    else:
                        print(f"Estado desconocido en enlace: {link_text}")
                        time.sleep(60)
                        continue
                else:
                    print("Enlace de descarga no encontrado, esperando...")
                    time.sleep(60)
                    continue

            except Exception as e:
                print(f"Error en intento {attempt}: {str(e)}")
                time.sleep(60)
                continue

        print("Maximo de intentos alcanzado")
        return None

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Telus."""
        try:
            print("Reseteando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("Reset completado")
        except Exception as e:
            print(f"Error en reset: {str(e)}")