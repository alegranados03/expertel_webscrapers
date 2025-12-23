import calendar
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


class ATTPDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para AT&T."""

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

                # 1. Click en billing tab y esperar 1 minuto
                billing_tab_xpath = "/html/body/div[1]/div/ul/li[3]/a"
                self.logger.info("Clicking Billing tab...")
                self.browser_wrapper.click_element(billing_tab_xpath)
                time.sleep(60)  # Esperar 1 minuto como especificado

                # 2. Click en bills tab y esperar 30 segundos
                bills_tab_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[3]/a"
                self.logger.info("Clicking Bills tab...")
                self.browser_wrapper.click_element(bills_tab_xpath)
                time.sleep(30)  # Esperar 30 segundos como especificado

                # 3. Verificar que llegamos a la seccion correcta buscando la tabla de resultados
                results_table_xpath = "/html/body/div[1]/main/div[2]/div[3]/div[2]/div/div/div/div[2]/div/table"
                if self.browser_wrapper.is_element_visible(results_table_xpath, timeout=15000):
                    self.logger.info("Invoices table found successfully")
                    return {"section": "pdf_invoices", "ready_for_download": True}
                else:
                    self.logger.warning("Invoices table not found")
                    continue

            except Exception as e:
                self.logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
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

            # 1. Configurar periodo de facturacion con calendario
            self._configure_billing_period(billing_cycle)

            # 2. Buscar fila especifica por account number
            account_number = billing_cycle.account.number
            pdf_row_found = self._find_pdf_row_by_account(account_number)

            if not pdf_row_found:
                self.logger.warning(f"Row not found for account number: {account_number}")
                return downloaded_files

            # 3. Click en standard bill only button para disparar descarga
            standard_bill_button_xpath = (
                "/html/body/div[1]/main/div[2]/div[3]/div[3]/div/div/div[2]/div[1]/div/div/button[1]"
            )
            self.logger.info("Clicking Standard Bill Only...")

            file_path = self.browser_wrapper.expect_download_and_click(
                standard_bill_button_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

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

            # Reset a pantalla principal
            self._reset_to_main_screen()

            self.logger.info(f"PDF invoice download completed: {len(downloaded_files)} file(s)")
            return downloaded_files

        except Exception as e:
            self.logger.error(f"Error downloading PDF invoice: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _configure_billing_period(self, billing_cycle: BillingCycle):
        """Configura el periodo de facturacion usando el calendario desplegable."""
        try:
            self.logger.info(f"Configuring billing period for: {billing_cycle.end_date}")

            # 1. Click en calendar button
            calendar_button_xpath = (
                "/html/body/div[1]/main/div[2]/div[3]/form[2]/div/div/div[1]/div/div[2]/div/div/div/button"
            )
            self.logger.info("Clicking Calendar button...")
            self.browser_wrapper.click_element(calendar_button_xpath)
            time.sleep(2)

            # 2. Buscar la opcion mas cercana basada en end_date
            end_date = billing_cycle.end_date
            month_name = calendar.month_name[end_date.month]
            year = end_date.year
            target_option = f"{month_name} {year}"

            self.logger.debug(f"Searching for calendar option: {target_option}")

            # 3. Buscar dentro de la UL desplegada
            ul_xpath = "/html/body/div[1]/main/div[2]/div[3]/form[2]/div/div/div[1]/div/div[2]/div/div/div/div/ul"
            if self.browser_wrapper.is_element_visible(ul_xpath, timeout=10000):
                # Buscar todas las opciones li dentro de la ul
                li_elements = self.browser_wrapper.page.query_selector_all(f"{ul_xpath}/li")

                for li in li_elements:
                    li_text = li.text_content() or ""
                    if target_option in li_text:
                        self.logger.info(f"Option found: {li_text}")
                        li.click()
                        time.sleep(2)
                        break
                else:
                    self.logger.warning(f"Exact option not found for {target_option}, using first available option")
                    if li_elements:
                        li_elements[0].click()
                        time.sleep(2)

                # 4. Click en apply button y esperar 1 minuto
                apply_button_xpath = "/html/body/div[1]/main/div[2]/div[3]/form[2]/div/div/div[1]/div/div[3]/button"
                self.logger.info("Clicking Apply button...")
                self.browser_wrapper.click_element(apply_button_xpath)
                time.sleep(60)  # Esperar 1 minuto como especificado

            else:
                self.logger.warning("Could not find calendar dropdown")

        except Exception as e:
            self.logger.error(f"Error configuring billing period: {str(e)}")

    def _find_pdf_row_by_account(self, account_number: str) -> bool:
        """Busca una fila especifica por account number y hace click en ella."""
        try:
            self.logger.info(f"Searching for row with account: {account_number}")

            # Buscar en la tabla de resultados
            table_xpath = "/html/body/div[1]/main/div[2]/div[3]/div[2]/div/div/div/div[2]/div/table"
            if not self.browser_wrapper.is_element_visible(table_xpath, timeout=10000):
                self.logger.warning("Invoices table not visible")
                return False

            # Buscar todas las filas de la tabla
            rows = self.browser_wrapper.page.query_selector_all(f"{table_xpath}/tbody/tr")

            for row in rows:
                row_text = row.text_content() or ""
                if account_number in row_text:
                    self.logger.info(f"Row found for account: {account_number}")
                    # Click en la fila para seleccionarla
                    row.click()
                    time.sleep(2)
                    return True

            self.logger.warning(f"Row not found with account number: {account_number}")
            return False

        except Exception as e:
            self.logger.error(f"Error searching for row by account: {str(e)}")
            return False

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de AT&T."""
        try:
            self.logger.info("Resetting to AT&T initial screen...")
            self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
            time.sleep(3)
            self.logger.info("Reset to AT&T completed")
        except Exception as e:
            self.logger.error(f"Error in AT&T reset: {str(e)}")