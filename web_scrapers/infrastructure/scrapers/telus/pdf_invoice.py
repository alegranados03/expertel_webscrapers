import logging
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
    """Scraper de facturas PDF para Telus.

    Este scraper:
    1. Navega a Bill Analyzer via My Telus
    2. Configura filtros de Scope (cuenta) y Month (mes)
    3. Descarga el PDF de la factura correspondiente
    """

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de facturas PDF de Telus y configura filtros."""
        try:
            self.logger.info("=== INICIANDO TELUS PDF INVOICE SCRAPER ===")

            # 1. Verificar que estamos en My Telus
            current_url = self.browser_wrapper.get_current_url()
            if "my-telus" not in current_url:
                self.logger.info("Navegando a My Telus...")
                self.browser_wrapper.goto("https://www.telus.com/my-telus")
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)

            # 2. Click en bill options dropdown
            bill_options_xpath = (
                "/html/body/div[5]/div/div/div/div[1]/div/div[3]/div/div/div/div/div/div/div[3]/div/div/div/div"
            )
            self.logger.info("Click en bill options dropdown...")
            self.browser_wrapper.click_element(bill_options_xpath)
            time.sleep(2)

            # 3. Click en "View bill" option
            view_bill_xpath = "//div[@class='generic_dropdownContainer__h39SV']//a[1]"
            self.logger.info("Click en 'View bill' option...")
            self.browser_wrapper.click_element(view_bill_xpath)
            self.logger.info("Esperando 30 segundos para cargar Bill Analyzer...")
            time.sleep(30)

            # 4. Manejar modal de Bill Analyzer si aparece
            self._dismiss_bill_analyzer_modal()

            # 5. Click en Statements tab
            statements_xpath = '//*[@id="navMenuItem14"]'
            self.logger.info("Click en Statements tab...")
            self.browser_wrapper.click_element(statements_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # 5. Configurar filtro de Scope (cuenta)
            if not self._configure_scope_filter(billing_cycle):
                self.logger.error("Fallo al configurar filtro de Scope - abortando scraper")
                return None

            # 6. Configurar filtro de Month
            if not self._configure_month_filter(billing_cycle):
                self.logger.error("Fallo al configurar filtro de Month - abortando scraper")
                return None

            # 7. Click en Apply
            apply_button_xpath = '//*[@id="btnViewList"]'
            self.logger.info("Click en Apply button...")
            self.browser_wrapper.click_element(apply_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(10)

            self.logger.info("Navegacion a seccion de facturas PDF completada")
            return {"section": "pdf_invoices", "ready_for_download": True}

        except Exception as e:
            self.logger.error(f"Error navegando a facturas PDF: {str(e)}")
            return None

    def _dismiss_bill_analyzer_modal(self) -> bool:
        """
        Detecta y cierra el modal de Bill Analyzer si aparece.
        Este modal puede aparecer al navegar a la seccion de reportes.
        Retorna True si se cerro el modal o si no aparecio.
        """
        try:
            modal_button_xpath = "//*[@id='tandc-content']/div[3]/button"

            # Verificar si el modal esta presente (con timeout corto)
            if self.browser_wrapper.is_element_visible(modal_button_xpath, timeout=3000):
                self.logger.info("Modal Bill Analyzer detectado, cerrando...")
                self.browser_wrapper.click_element(modal_button_xpath)
                time.sleep(2)
                self.logger.info("Modal Bill Analyzer cerrado")
                return True
            else:
                self.logger.info("Modal Bill Analyzer no detectado, continuando...")
                return True

        except Exception as e:
            self.logger.warning(f"Error manejando modal Bill Analyzer: {str(e)}")
            return True  # Continuar de todos modos

    def _configure_scope_filter(self, billing_cycle: BillingCycle) -> bool:
        """Configura el filtro de Scope para seleccionar la cuenta correcta."""
        try:
            target_account = billing_cycle.account.number
            self.logger.info(f"Configurando Scope filter para cuenta: {target_account}")

            # 1. Click en Scope dropdown button
            scope_dropdown_xpath = '//*[@id="LevelDataDropdownButton"]'
            self.logger.info("Click en Scope dropdown...")
            self.browser_wrapper.click_element(scope_dropdown_xpath)
            time.sleep(2)

            # 2. Click en "Accounts" option
            accounts_option_xpath = '//*[@id="LevelDataDropdownList_multipleaccounts"]'
            self.logger.info("Click en 'Accounts' option...")
            self.browser_wrapper.click_element(accounts_option_xpath)
            time.sleep(3)

            # 3. Escribir el numero de cuenta en el input de busqueda
            search_input_xpath = '//*[@id="scopeExpandedAccountMenu"]/div[1]/div/div[2]/input'
            self.logger.info(f"Escribiendo numero de cuenta '{target_account}' en el input de busqueda...")
            self.browser_wrapper.clear_and_type(search_input_xpath, target_account)
            time.sleep(2)

            # 4. Seleccionar la cuenta de la lista de resultados
            # La lista esta en: //*[@id="scopeExpandedAccountMenu"]/div[3]/ul
            # El li contiene el numero de cuenta
            account_list_item_xpath = f'//*[@id="scopeExpandedAccountMenu"]/div[3]/ul//li[contains(., "{target_account}")]'

            if self.browser_wrapper.find_element_by_xpath(account_list_item_xpath, timeout=5000):
                self.logger.info(f"Cuenta {target_account} encontrada en la lista, seleccionando...")
                self.browser_wrapper.click_element(account_list_item_xpath)
                time.sleep(1)
            else:
                self.logger.error(f"Cuenta {target_account} NO encontrada en la lista de resultados")
                return False

            # 5. Click en OK button para confirmar
            ok_button_xpath = '//*[@id="scopeExpandedAccountMenu"]/div[4]/button'
            self.logger.info("Click en OK button para confirmar cuenta...")
            self.browser_wrapper.click_element(ok_button_xpath)

            time.sleep(2)
            self.logger.info(f"Scope filter configurado para cuenta: {target_account}")
            return True

        except Exception as e:
            self.logger.error(f"Error configurando Scope filter: {str(e)}")
            return False

    def _configure_month_filter(self, billing_cycle: BillingCycle) -> bool:
        """Configura el filtro de Month basado en el end_date del billing cycle."""
        try:
            target_month = billing_cycle.end_date.month
            target_year = billing_cycle.end_date.year

            # Mapeo de numero de mes a nombre en ingles
            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            month_name = month_names[target_month]

            self.logger.info(f"Configurando Month filter para: {month_name} {target_year}")

            # 1. Click en Month dropdown button
            month_dropdown_xpath = '//*[@id="BilledMonthYearPendingDataDropdownButton"]'
            self.logger.info("Click en Month dropdown...")
            self.browser_wrapper.click_element(month_dropdown_xpath)
            time.sleep(2)

            # 2. Buscar y seleccionar el mes correcto
            # Formato de las opciones: "December 2025", "November 2025", etc.
            target_text = f"{month_name} {target_year}"

            # Buscar en la lista de opciones
            month_option_xpath = f"//li[@role='option'][contains(text(), '{target_text}')]"

            if self.browser_wrapper.find_element_by_xpath(month_option_xpath, timeout=5000):
                self.logger.info(f"Mes '{target_text}' encontrado, seleccionando...")
                self.browser_wrapper.click_element(month_option_xpath)
                time.sleep(2)
                self.logger.info(f"Month filter configurado: {target_text}")
                return True
            else:
                self.logger.error(f"Mes '{target_text}' NO encontrado en la lista")
                return False

        except Exception as e:
            self.logger.error(f"Error configurando Month filter: {str(e)}")
            return False

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de Telus."""
        downloaded_files = []

        # Obtener el BillingCyclePDFFile del billing_cycle
        pdf_file = billing_cycle.pdf_files[0] if billing_cycle.pdf_files else None
        if pdf_file:
            self.logger.info(f"Mapeando archivo PDF -> BillingCyclePDFFile ID {pdf_file.id}")

        target_account = billing_cycle.account.number

        try:
            self.logger.info("=== INICIANDO PROCESO DE DESCARGA DE PDF ===")

            # 1. Buscar en la tabla DataTable el primer row con la cuenta correcta
            data_table_xpath = '//*[@id="DataTable"]'

            if not self.browser_wrapper.find_element_by_xpath(data_table_xpath, timeout=10000):
                self.logger.error("Tabla de statements no encontrada")
                return downloaded_files

            self.logger.info("Tabla de statements encontrada")

            # 2. Buscar el boton "PDF Bill" en la fila de la cuenta correcta
            # El boton tiene aria-label que contiene el numero de cuenta
            pdf_button_xpath = f"//button[contains(@aria-label, 'PDF Bill')][contains(@aria-label, '{target_account}')]"

            # Alternativa: buscar en el primer row
            pdf_button_alt_xpath = "//tbody/tr[1]//button[contains(@aria-label, 'PDF Bill')]"

            if self.browser_wrapper.find_element_by_xpath(pdf_button_xpath, timeout=5000):
                self.logger.info(f"Boton PDF Bill encontrado para cuenta {target_account}")
                self.browser_wrapper.click_element(pdf_button_xpath)
            elif self.browser_wrapper.find_element_by_xpath(pdf_button_alt_xpath, timeout=3000):
                self.logger.info("Boton PDF Bill encontrado en primer row")
                self.browser_wrapper.click_element(pdf_button_alt_xpath)
            else:
                self.logger.error("Boton PDF Bill no encontrado")
                return downloaded_files

            time.sleep(3)

            # 3. Verificar que la cuenta en el modal sea la correcta
            modal_header_xpath = '//*[@id="bdfModalHeaderText"]'

            if self.browser_wrapper.find_element_by_xpath(modal_header_xpath, timeout=5000):
                modal_text = self.browser_wrapper.get_text(modal_header_xpath)
                self.logger.info(f"Modal header: '{modal_text}'")

                if target_account not in modal_text:
                    self.logger.error(f"Cuenta en modal '{modal_text}' no coincide con '{target_account}'")
                    self._close_modal_and_reset()
                    return downloaded_files

                self.logger.info(f"Cuenta verificada en modal: {target_account}")
            else:
                self.logger.warning("No se pudo verificar cuenta en modal header")

            # 4. Click en "PDF copy of your print bill" para expandir la lista
            pdf_copy_xpath = "//a[contains(@class, 'bdfDocType')][contains(., 'PDF copy of your print bill')]"

            if self.browser_wrapper.find_element_by_xpath(pdf_copy_xpath, timeout=5000):
                self.logger.info("Click en 'PDF copy of your print bill'...")
                self.browser_wrapper.click_element(pdf_copy_xpath)
                time.sleep(2)
            else:
                self.logger.error("Opcion 'PDF copy of your print bill' no encontrada")
                self._close_modal_and_reset()
                return downloaded_files

            # 5. Seleccionar la fecha correcta basada en end_date
            # Formato de las opciones: "YYYY/MM/DD" (ej: "2025/11/21")
            target_year = billing_cycle.end_date.year
            target_month = billing_cycle.end_date.month

            # Buscar la opcion con el ano y mes correctos
            date_pattern = f"{target_year}/{target_month:02d}"
            date_button_xpath = f"//button[contains(@class, 'bdf-doc-item')][contains(text(), '{date_pattern}')]"

            if self.browser_wrapper.find_element_by_xpath(date_button_xpath, timeout=5000):
                button_text = self.browser_wrapper.get_text(date_button_xpath)
                self.logger.info(f"Fecha encontrada: '{button_text}', descargando PDF...")

                # Click dispara la descarga automaticamente
                downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                    date_button_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
                )

                if downloaded_file_path:
                    actual_filename = os.path.basename(downloaded_file_path)
                    self.logger.info(f"PDF descargado: {actual_filename}")

                    file_info = FileDownloadInfo(
                        file_id=pdf_file.id if pdf_file else 1,
                        file_name=actual_filename,
                        download_url="N/A",
                        file_path=downloaded_file_path,
                        pdf_file=pdf_file,
                    )
                    downloaded_files.append(file_info)

                    if pdf_file:
                        self.logger.info(
                            f"MAPEO CONFIRMADO: {actual_filename} -> BillingCyclePDFFile ID {pdf_file.id}"
                        )
                else:
                    self.logger.error("Error en descarga del PDF")
            else:
                self.logger.error(f"No se encontro PDF para fecha {date_pattern}")
                # Listar opciones disponibles para debug
                self._list_available_pdf_dates()

            # 6. Cerrar modal y reset
            self._close_modal_and_reset()

            return downloaded_files

        except Exception as e:
            self.logger.error(f"Error en descarga de PDF: {str(e)}")
            try:
                self._close_modal_and_reset()
            except:
                pass
            return downloaded_files

    def _list_available_pdf_dates(self):
        """Lista las fechas de PDF disponibles para debug."""
        try:
            self.logger.info("Listando fechas de PDF disponibles:")

            # Buscar todos los botones de fecha
            for i in range(1, 20):
                button_xpath = f"(//button[contains(@class, 'bdf-doc-item')])[{i}]"
                if self.browser_wrapper.find_element_by_xpath(button_xpath, timeout=1000):
                    text = self.browser_wrapper.get_text(button_xpath)
                    self.logger.info(f"  - {text}")
                else:
                    break

        except Exception as e:
            self.logger.warning(f"Error listando fechas: {str(e)}")

    def _close_modal_and_reset(self):
        """Cierra el modal de PDF y resetea a la pantalla principal."""
        try:
            # Cerrar modal
            close_button_xpath = '//*[@id="bdfModal"]/div/div/div[1]/button'
            if self.browser_wrapper.find_element_by_xpath(close_button_xpath, timeout=3000):
                self.logger.info("Cerrando modal de PDF...")
                self.browser_wrapper.click_element(close_button_xpath)
                time.sleep(2)

            # Reset a My Telus
            self._reset_to_main_screen()

        except Exception as e:
            self.logger.warning(f"Error cerrando modal: {str(e)}")
            self._reset_to_main_screen()

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Telus."""
        try:
            self.logger.info("Reseteando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            self.logger.info("Reset completado")
        except Exception as e:
            self.logger.error(f"Error en reset: {str(e)}")