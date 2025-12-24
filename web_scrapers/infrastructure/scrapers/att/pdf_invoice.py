import calendar
import logging
import os
import time
import traceback
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    FileDownloadInfo,
    PDFInvoiceScraperStrategy,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class ATTPDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para AT&T.

    Navega a Billing > Bills, configura filtros de cuenta y mes,
    y descarga el PDF de factura desde la tabla de resultados.
    """

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la seccion de facturas PDF en el portal de AT&T."""
        return self._find_files_section_with_retry(config, billing_cycle, max_retries=1)

    def _find_files_section_with_retry(
        self, config: ScraperConfig, billing_cycle: BillingCycle, max_retries: int = 1
    ) -> Optional[Any]:
        """Busca la seccion de facturas PDF con reintento automatico."""
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"Searching for AT&T PDF invoices section (attempt {attempt + 1}/{max_retries + 1})")

                # 1. Click en Billing tab (igual que monthly)
                billing_tab_xpath = "//*[@id='primaryNav']/li[3]/a"
                self.logger.info("Clicking Billing tab...")

                if self.browser_wrapper.is_element_visible(billing_tab_xpath, timeout=10000):
                    billing_text = self.browser_wrapper.get_text(billing_tab_xpath)
                    if billing_text and "BILLING" in billing_text.upper():
                        self.logger.info(f"Billing tab verified: '{billing_text}'")
                        self.browser_wrapper.click_element(billing_tab_xpath)
                        time.sleep(60)  # Esperar 1 minuto
                    else:
                        self.logger.warning(f"Billing tab text mismatch: '{billing_text}'")
                        continue
                else:
                    self.logger.warning("Billing tab not found")
                    continue

                # 2. Click en Bills tab
                bills_tab_xpath = '//*[@id="navMenuItem14"]'
                self.logger.info("Clicking Bills tab...")

                if self.browser_wrapper.is_element_visible(bills_tab_xpath, timeout=10000):
                    self.browser_wrapper.click_element(bills_tab_xpath)
                    time.sleep(5)
                else:
                    self.logger.warning("Bills tab not found")
                    continue

                # 3. Verificar que llegamos a la seccion correcta (filtros visibles)
                filters_xpath = '//*[@id="_globysForm_"]/div/div/div[1]/div'
                if self.browser_wrapper.is_element_visible(filters_xpath, timeout=10000):
                    self.logger.info("Bills section found successfully - filters visible")
                    return {"section": "pdf_invoices", "ready_for_download": True}
                else:
                    self.logger.warning("Filters section not found")
                    continue

            except Exception as e:
                self.logger.error(f"Error on attempt {attempt + 1}: {str(e)}\n{traceback.format_exc()}")
                if attempt < max_retries:
                    continue

        self.logger.error("Could not find PDF invoices section after all attempts")
        return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de AT&T."""
        downloaded_files = []

        # Mapear BillingCyclePDFFile
        pdf_file = None
        if billing_cycle.pdf_files:
            pdf_file = billing_cycle.pdf_files[0]
            self.logger.info(f"PDF file found: ID {pdf_file.id}")

        try:
            self.logger.info("Downloading PDF invoice...")

            # 1. Configurar filtro de cuenta
            self._configure_account_filter(billing_cycle)

            # 2. Configurar filtro de mes
            self._configure_month_filter(billing_cycle)

            # 3. Click en View button para aplicar filtros
            view_button_xpath = '//*[@id="btnViewList"]'
            self.logger.info("Clicking View button to apply filters...")
            if self.browser_wrapper.is_element_visible(view_button_xpath, timeout=5000):
                self.browser_wrapper.click_element(view_button_xpath)
                time.sleep(15)  # Esperar 15 segundos para que se apliquen los filtros
            else:
                self.logger.error("View button not found")
                return downloaded_files

            # 4. Verificar que la tabla de resultados está visible
            table_wrapper_xpath = '//*[@id="DataTable_wrapper"]'
            if not self.browser_wrapper.is_element_visible(table_wrapper_xpath, timeout=15000):
                self.logger.error("Results table not found")
                self._reset_to_main_screen()
                return downloaded_files

            # 5. Buscar y hacer click en "Bill PDF" en la tabla
            if not self._click_bill_pdf_button():
                self.logger.error("Could not find Bill PDF button")
                self._reset_to_main_screen()
                return downloaded_files

            # 6. En el modal, seleccionar "Standard bill only" y descargar
            file_path = self._download_from_modal()

            if file_path:
                actual_filename = os.path.basename(file_path)
                self.logger.info(f"PDF downloaded: {actual_filename}")

                # Crear FileDownloadInfo
                file_download_info = FileDownloadInfo(
                    file_id=pdf_file.id if pdf_file else 1,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    pdf_file=pdf_file,
                )
                downloaded_files.append(file_download_info)

                if pdf_file:
                    self.logger.info(f"MAPPING CONFIRMED: {actual_filename} -> BillingCyclePDFFile ID {pdf_file.id}")
                else:
                    self.logger.warning("PDF file downloaded without specific BillingCyclePDFFile mapping")
            else:
                self.logger.error("Could not download PDF invoice")

            # 7. Reset a pantalla principal
            self._reset_to_main_screen()

            self.logger.info(f"PDF invoice download completed: {len(downloaded_files)} file(s)")
            return downloaded_files

        except Exception as e:
            self.logger.error(f"Error downloading PDF invoice: {str(e)}\n{traceback.format_exc()}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _configure_account_filter(self, billing_cycle: BillingCycle):
        """Configura el filtro de cuenta basado en el billing cycle."""
        try:
            account_number = billing_cycle.account.number
            self.logger.info(f"Configuring account filter for: {account_number}")

            # 1. Click en View by dropdown button
            view_by_button_xpath = '//*[@id="LevelDataDropdownButton"]'
            self.logger.info("Clicking View by dropdown...")
            self.browser_wrapper.click_element(view_by_button_xpath)
            time.sleep(2)

            # 2. Seleccionar opción "Accounts"
            accounts_option_xpath = '//*[@id="LevelDataDropdownList_multipleaccounts"]'
            self.logger.info("Selecting Accounts option...")
            self.browser_wrapper.click_element(accounts_option_xpath)
            time.sleep(2)

            # 3. Escribir número de cuenta en el input
            account_input_xpath = "//*[@id='scopeExpandedAccountMenu']/div[1]/div/div[2]/input"
            self.logger.info(f"Entering account number: {account_number}")
            self.browser_wrapper.clear_and_type(account_input_xpath, account_number)
            time.sleep(3)

            # 4. Seleccionar la primera opción del listado
            first_option_xpath = "//*[@id='scopeExpandedAccountMenu']/div[3]/ul/li[1]"
            if self.browser_wrapper.is_element_visible(first_option_xpath, timeout=5000):
                self.logger.info("Selecting first account option...")
                checkbox_xpath = f"{first_option_xpath}/input"
                if self.browser_wrapper.is_element_visible(checkbox_xpath, timeout=2000):
                    self.browser_wrapper.click_element(checkbox_xpath)
                else:
                    self.browser_wrapper.click_element(first_option_xpath)
                time.sleep(1)
            else:
                self.logger.warning("Account option not found in list")

            # 5. Click en OK button
            ok_button_xpath = "//*[@id='scopeExpandedAccountMenu']/div[4]/button"
            self.logger.info("Clicking OK button...")
            self.browser_wrapper.click_element(ok_button_xpath)
            time.sleep(3)

            self.logger.info("Account filter configured successfully")

        except Exception as e:
            self.logger.error(f"Error configuring account filter: {str(e)}\n{traceback.format_exc()}")

    def _configure_month_filter(self, billing_cycle: BillingCycle):
        """Configura el filtro de mes basado en el billing cycle."""
        try:
            end_date = billing_cycle.end_date
            month_name = calendar.month_name[end_date.month]
            year = end_date.year
            target_option = f"{month_name} {year}"

            self.logger.info(f"Configuring month filter for: {target_option}")

            # 1. Click en Month dropdown button
            month_button_xpath = '//*[@id="BilledMonthYearPendingDataDropdownButton"]'
            self.logger.info("Clicking Month dropdown...")
            self.browser_wrapper.click_element(month_button_xpath)
            time.sleep(2)

            # 2. Buscar y seleccionar la opción correcta en la lista
            month_list_xpath = '//*[@id="BilledMonthYearPendingDataDropdownList"]'
            if self.browser_wrapper.is_element_visible(month_list_xpath, timeout=5000):
                page = self.browser_wrapper.page
                options = page.query_selector_all(f"xpath={month_list_xpath}//li")

                for option in options:
                    option_text = option.inner_text().strip()
                    if target_option in option_text:
                        self.logger.info(f"Found month option: {option_text}")
                        option.click()
                        time.sleep(2)
                        return

                self.logger.warning(f"Month option '{target_option}' not found, using current selection")
            else:
                self.logger.warning("Month dropdown list not found")

        except Exception as e:
            self.logger.error(f"Error configuring month filter: {str(e)}\n{traceback.format_exc()}")

    def _click_bill_pdf_button(self) -> bool:
        """Busca y hace click en el botón 'Bill PDF' en la tabla de resultados."""
        try:
            self.logger.info("Searching for Bill PDF button in table...")

            # La tabla tiene una columna con el botón "Bill PDF"
            # El botón tiene la clase 'stmtListTableLinkDocument'
            page = self.browser_wrapper.page

            # Buscar el botón de Bill PDF en la primera fila (debería haber solo una después del filtro)
            bill_pdf_button = page.query_selector("button.stmtListTableLinkDocument")

            if bill_pdf_button:
                self.logger.info("Bill PDF button found, clicking...")
                bill_pdf_button.click()
                time.sleep(3)  # Esperar a que se abra el modal
                return True
            else:
                self.logger.warning("Bill PDF button not found in table")
                return False

        except Exception as e:
            self.logger.error(f"Error clicking Bill PDF button: {str(e)}\n{traceback.format_exc()}")
            return False

    def _download_from_modal(self) -> Optional[str]:
        """Descarga el PDF desde el modal seleccionando 'Standard bill only'."""
        try:
            # 1. Esperar a que el modal esté visible
            modal_content_xpath = '//*[@id="acctContent"]/div'
            if not self.browser_wrapper.is_element_visible(modal_content_xpath, timeout=10000):
                self.logger.error("Modal content not found")
                return None

            self.logger.info("Modal opened, selecting Standard bill only...")

            # 2. Click en "Standard bill only" - esto dispara la descarga automáticamente
            standard_bill_button_xpath = '//*[@id="billDocType_1"]'

            file_path = self.browser_wrapper.expect_download_and_click(
                standard_bill_button_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            # 3. Cerrar el modal
            self._close_modal()

            return file_path

        except Exception as e:
            self.logger.error(f"Error downloading from modal: {str(e)}\n{traceback.format_exc()}")
            self._close_modal()
            return None

    def _close_modal(self):
        """Cierra el modal de descarga de PDF."""
        try:
            close_button_xpath = '//*[@id="bdfModal"]/div/div/div[3]/button'
            self.logger.info("Closing modal...")

            if self.browser_wrapper.is_element_visible(close_button_xpath, timeout=5000):
                self.browser_wrapper.click_element(close_button_xpath)
                time.sleep(2)
                self.logger.info("Modal closed")
            else:
                # Intentar con Escape
                self.logger.info("Close button not found, trying Escape key...")
                self.browser_wrapper.page.keyboard.press("Escape")
                time.sleep(1)

        except Exception as e:
            self.logger.debug(f"Error closing modal: {str(e)}")

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de AT&T."""
        try:
            self.logger.info("Resetting to AT&T initial screen...")
            self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
            time.sleep(10)
            self.logger.info("Reset to AT&T completed")
        except Exception as e:
            self.logger.error(f"Error in AT&T reset: {str(e)}")