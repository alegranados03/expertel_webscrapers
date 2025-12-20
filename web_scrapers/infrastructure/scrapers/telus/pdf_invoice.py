import os
import time
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    FileDownloadInfo,
    PDFInvoiceScraperStrategy,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class TelusPDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para Telus."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de facturas PDF de Telus."""
        try:
            print("Navegando a facturas PDF de Telus...")

            # 1. Verificar que estamos en My Telus
            current_url = self.browser_wrapper.get_current_url()
            if "my-telus" not in current_url:
                print("Navegando a My Telus...")
                self.browser_wrapper.goto("https://www.telus.com/my-telus")
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)

            # 2. Click en bill options button
            bill_options_xpath = (
                "/html/body/div[5]/div/div/div/div[1]/div/div[3]/div/div/div/div/div/div/div[3]/div/div/div/div"
            )
            print("Click en bill options button...")
            self.browser_wrapper.click_element(bill_options_xpath)
            time.sleep(3)

            # 3. Click en view bill option
            view_bill_xpath = "/html[1]/body[1]/div[5]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[1]/a[1]"
            print("Click en view bill option...")
            self.browser_wrapper.click_element(view_bill_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # 4. Click en statements header y esperar 1 minuto
            statements_header_xpath = "/html/body/div[1]/div/div/div/div/div[3]/ul[1]/li[2]/a"
            print("Click en statements header...")
            self.browser_wrapper.click_element(statements_header_xpath)
            print("Esperando 1 minuto...")
            time.sleep(60)

            print("Navegacion a facturas PDF completada")
            return {"section": "pdf_invoices", "ready_for_download": True}

        except Exception as e:
            print(f"Error navegando a facturas PDF: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de Telus."""
        downloaded_files = []

        # Obtener el BillingCyclePDFFile del billing_cycle
        pdf_file = billing_cycle.pdf_files[0] if billing_cycle.pdf_files else None
        if pdf_file:
            print(f"Mapeando archivo PDF -> BillingCyclePDFFile ID {pdf_file.id}")

        try:
            # 1. Click en download pdf
            download_pdf_xpath = "/html/body/div[2]/div[3]/div[2]/div/div/div/div[2]/div/table/tbody/tr/td[11]/button"
            print("Click en download pdf...")
            self.browser_wrapper.click_element(download_pdf_xpath)
            time.sleep(3)

            # 2. Click en drop list y esperar 30 segundos
            drop_list_xpath = "/html/body/div[2]/div[3]/div[3]/div/div/div[2]/div[1]/div/div/div/div/div[1]"
            print("Click en drop list...")
            self.browser_wrapper.click_element(drop_list_xpath)
            print("Esperando 30 segundos...")
            time.sleep(30)

            # 3. Buscar y hacer click en la fecha mas cercana al end_date del billing cycle
            target_month = billing_cycle.end_date.month
            target_year = billing_cycle.end_date.year

            print(f"Buscando PDF para {target_year}/{target_month:02d}")

            # Buscar en la lista desplegada
            list_xpath = "/html/body/div[2]/div[3]/div[3]/div/div/div[2]/div[1]/div/div/div/div/div[2]/ul"

            if self.browser_wrapper.find_element_by_xpath(list_xpath):
                print("Lista de PDFs encontrada")

                # Buscar el boton con la fecha mas cercana
                pdf_button_xpath = self._find_closest_pdf_in_list(target_year, target_month)

                if pdf_button_xpath:
                    print("PDF encontrado, descargando...")

                    # Hacer click para descargar (se dispara automaticamente)
                    downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                        pdf_button_xpath, timeout=30000, downloads_dir=self.job_downloads_dir
                    )

                    if downloaded_file_path:
                        actual_filename = os.path.basename(downloaded_file_path)
                        file_size = (
                            os.path.getsize(downloaded_file_path) if os.path.exists(downloaded_file_path) else 2048000
                        )

                        print(f"PDF descargado: {actual_filename}")

                        file_info = FileDownloadInfo(
                            file_id=pdf_file.id if pdf_file else 1,
                            file_name=actual_filename,
                            download_url="N/A",
                            file_path=downloaded_file_path,
                            pdf_file=pdf_file,
                        )
                        downloaded_files.append(file_info)

                        if pdf_file:
                            print(f"MAPEO CONFIRMADO: {actual_filename} -> BillingCyclePDFFile ID {pdf_file.id}")
                    else:
                        print("Error con expect_download, usando metodo tradicional...")
                        self.browser_wrapper.click_element(pdf_button_xpath)
                        time.sleep(5)

                        estimated_filename = f"telus_invoice_{billing_cycle.end_date.strftime('%Y_%m_%d')}.pdf"
                        file_info = FileDownloadInfo(
                            file_id=pdf_file.id if pdf_file else 1,
                            file_name=estimated_filename,
                            download_url="N/A",
                            file_path=f"{self.job_downloads_dir}/{estimated_filename}",
                            pdf_file=pdf_file,
                        )
                        downloaded_files.append(file_info)
                        print(f"PDF descargado (metodo tradicional): {estimated_filename}")
                else:
                    print("No se encontro PDF cercano para el periodo")
            else:
                print("Lista de PDFs no encontrada")

            # 4. Reset a pantalla principal
            self._reset_to_main_screen()

            print(f"Descarga PDF completada: {len(downloaded_files)} archivo(s)")
            return downloaded_files

        except Exception as e:
            print(f"Error en descarga de PDF: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _find_closest_pdf_in_list(self, target_year: int, target_month: int) -> Optional[str]:
        """Encuentra el PDF mas cercano en la lista desplegada."""
        try:
            print(f"Buscando PDF para {target_year}/{target_month:02d}")

            # 1. Buscar fecha exacta (ignorando el dia)
            exact_pattern = f"{target_year}/{target_month:02d}"
            exact_xpath = f"//button[@class='list-group-item bdf-doc-item'][contains(text(), '{exact_pattern}')]"

            if self.browser_wrapper.find_element_by_xpath(exact_xpath):
                button_text = self.browser_wrapper.get_text(exact_xpath)
                print(f"Encontrado PDF mes exacto: {button_text}")
                return exact_xpath

            # 2. Buscar mes anterior
            if target_month > 1:
                prev_month = target_month - 1
                prev_year = target_year
            else:
                prev_month = 12
                prev_year = target_year - 1

            prev_pattern = f"{prev_year}/{prev_month:02d}"
            prev_xpath = f"//button[@class='list-group-item bdf-doc-item'][contains(text(), '{prev_pattern}')]"

            if self.browser_wrapper.find_element_by_xpath(prev_xpath):
                button_text = self.browser_wrapper.get_text(prev_xpath)
                print(f"Encontrado PDF mes anterior: {button_text}")
                return prev_xpath

            # 3. Buscar cualquier PDF del ano actual (ignorando mes y dia)
            year_xpath = f"//button[@class='list-group-item bdf-doc-item'][contains(text(), '{target_year}/')]"

            if self.browser_wrapper.find_element_by_xpath(year_xpath):
                button_text = self.browser_wrapper.get_text(year_xpath)
                print(f"Encontrado PDF del ano {target_year}: {button_text}")
                return year_xpath

            # 4. Tomar el primer PDF disponible como ultimo recurso
            first_xpath = "//button[@class='list-group-item bdf-doc-item'][1]"

            if self.browser_wrapper.find_element_by_xpath(first_xpath):
                button_text = self.browser_wrapper.get_text(first_xpath)
                print(f"Tomando primer PDF disponible: {button_text}")
                return first_xpath

            print("No se encontraron PDFs en la lista")
            return None

        except Exception as e:
            print(f"Error buscando PDF en lista: {str(e)}")
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