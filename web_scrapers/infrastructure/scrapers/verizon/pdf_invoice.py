import os
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


class VerizonPDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para Verizon."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de facturas PDF de Verizon."""
        try:
            print("Navegando a facturas PDF de Verizon...")

            # 1. Click en billing tab
            billing_tab_xpath = "/html/body/app-root/app-secure-layout/div/div[1]/app-header/header/div[2]/div/div/div[1]/div[2]/header/div/div/div[2]/nav/ul/li[3]/a"
            print("Haciendo clic en billing tab...")
            self.browser_wrapper.click_element(billing_tab_xpath)
            time.sleep(2)

            # 2. Click en bill view details
            bill_view_details_xpath = "/html/body/app-root/app-secure-layout/div/div[1]/app-header/header/div[2]/div/div/div[1]/div[2]/header/div/div/div[2]/nav/ul/li[3]/div/div/div[1]/div/ul/li[2]/a"
            print("Haciendo clic en bill view details...")
            self.browser_wrapper.click_element(bill_view_details_xpath)
            time.sleep(2)

            # 3. Click en recent bills
            recent_bills_xpath = "/html/body/app-root/app-secure-layout/div/div[1]/app-header/header/div[2]/div/div/div[1]/div[2]/header/div/div/div[2]/nav/ul/li[3]/div/div/div[2]/div/div[1]/div/ul/li[1]/a"
            print("Haciendo clic en recent bills...")
            self.browser_wrapper.click_element(recent_bills_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            print("Navegacion a facturas PDF completada")
            return {"section": "pdf_invoices", "ready_for_download": True}

        except Exception as e:
            print(f"Error navegando a facturas PDF: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de Verizon."""
        downloaded_files = []

        # Obtener el BillingCyclePDFFile del billing_cycle
        pdf_file = billing_cycle.pdf_files[0] if billing_cycle.pdf_files else None
        if pdf_file:
            print(f"Mapeando archivo PDF -> BillingCyclePDFFile ID {pdf_file.id}")

        try:
            print("Descargando facturas PDF...")

            # 4. Configurar date dropdown
            target_date_option = self._find_closest_date_option(billing_cycle)
            if target_date_option:
                print(f"Seleccionando periodo: {target_date_option}")
                self._select_date_option(target_date_option)
            else:
                print("No se pudo encontrar periodo apropiado")
                return downloaded_files

            # 5. Download PDF
            download_pdf_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-view-invoice/div/div[1]/div[1]/div[1]/div/div[2]/app-export-invoice/div/div[1]/div"
            print("Descargando PDF...")

            file_path = self.browser_wrapper.expect_download_and_click(
                download_pdf_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                print(f"PDF descargado: {actual_filename}")

                file_info = FileDownloadInfo(
                    file_id=pdf_file.id,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    pdf_file=pdf_file,
                )
                downloaded_files.append(file_info)

                # Confirmar mapeo
                if pdf_file:
                    print(f"MAPEO CONFIRMADO: {actual_filename} -> BillingCyclePDFFile ID {pdf_file.id}")
            else:
                print("No se pudo descargar PDF")

            # Reset a pantalla principal
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

    def _find_closest_date_option(self, billing_cycle: BillingCycle) -> Optional[str]:
        """Encuentra la opcion de fecha mas cercana al rango del billing cycle."""
        try:
            # Obtener las fechas objetivo del billing cycle
            start_date = billing_cycle.start_date
            end_date = billing_cycle.end_date

            print(f"Buscando periodo mas cercano a: {start_date} - {end_date}")

            # Obtener todas las opciones disponibles en el dropdown
            dropdown_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-view-invoice/div/div[1]/div[1]/div[1]/div/div[2]/div/app-dropdown"
            self.browser_wrapper.click_element(dropdown_xpath)
            time.sleep(1)

            list_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-view-invoice/div/div[1]/div[1]/div[1]/div/div[2]/div/app-dropdown/div[1]/div/div[2]/ul"

            # Usar JavaScript para obtener todas las opciones
            options_text = self.browser_wrapper.page.evaluate(
                f"""
                () => {{
                    const list = document.evaluate("{list_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (list) {{
                        const items = list.querySelectorAll('li');
                        return Array.from(items).map(item => item.textContent.trim());
                    }}
                    return [];
                }}
            """
            )

            if not options_text:
                print("No se pudieron obtener las opciones del dropdown")
                return None

            print(f"Opciones disponibles: {options_text}")

            # Buscar la opcion mas cercana basada en las fechas del billing cycle
            closest_option = None
            min_diff = float("inf")

            for option in options_text:
                try:
                    # Ignorar "Request older bills here"
                    if "request older" in option.lower():
                        continue

                    # Parsear fechas del formato "Jun 27, 2025 - Jul 26, 2025"
                    if " - " in option:
                        date_parts = option.split(" - ")
                        if len(date_parts) == 2:
                            # Comparar con end_date del billing cycle
                            option_end_str = date_parts[1].strip()
                            try:
                                option_end_date = datetime.strptime(option_end_str, "%b %d, %Y")
                                diff = abs((option_end_date - end_date).days)
                                if diff < min_diff:
                                    min_diff = diff
                                    closest_option = option
                            except:
                                continue
                except:
                    continue

            if closest_option:
                print(f"Opcion mas cercana encontrada: {closest_option}")
                return closest_option

            print("No se pudo encontrar una opcion adecuada")
            return None

        except Exception as e:
            print(f"Error buscando opcion de fecha: {str(e)}")
            return None

    def _select_date_option(self, target_option: str) -> bool:
        """Selecciona la opcion de fecha especifica en el dropdown."""
        try:
            # Buscar y hacer clic en la opcion especifica
            list_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-view-invoice/div/div[1]/div[1]/div[1]/div/div[2]/div/app-dropdown/div[1]/div/div[2]/ul"

            # Usar JavaScript para encontrar y hacer clic en la opcion
            success = self.browser_wrapper.page.evaluate(
                f"""
                () => {{
                    const list = document.evaluate("{list_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (list) {{
                        const items = list.querySelectorAll('li');
                        for (let item of items) {{
                            if (item.textContent.trim() === "{target_option}") {{
                                item.click();
                                return true;
                            }}
                        }}
                    }}
                    return false;
                }}
            """
            )

            if success:
                print(f"Seleccionado: {target_option}")
                time.sleep(2)
                return True
            else:
                print(f"No se pudo seleccionar: {target_option}")
                return False

        except Exception as e:
            print(f"Error seleccionando opcion de fecha: {str(e)}")
            return False

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Verizon."""
        try:
            print("Reseteando a dashboard de Verizon...")
            dashboard_url = "https://mb.verizonwireless.com/mbt/secure/index?appName=esm#/esm/dashboard"
            self.browser_wrapper.goto(dashboard_url)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("Reset completado")
        except Exception as e:
            print(f"Error en reset: {str(e)}")