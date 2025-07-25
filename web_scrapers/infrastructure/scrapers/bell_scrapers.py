import calendar
import os
import time
from datetime import datetime
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    DailyUsageScraperStrategy,
    FileDownloadInfo,
    MonthlyReportsScraperStrategy,
    PDFInvoiceScraperStrategy,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class BellMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)
        self.report_dictionary = {
            "cost_overview": None,
            "enhanced_user_profile_report": None,
            "usage_overview": None,
        }

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos mensuales en el portal de Bell."""
        try:
            # Look for reports
            report_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[4]/a[1]"
            self.browser_wrapper.hover_element(report_xpath)
            time.sleep(2)  # Esperar 2 segundos después del hover

            # e-report (click)
            ereport_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[4]/div[1]/ul[1]/li[1]/a[1]/h3[1]"
            self.browser_wrapper.click_element(ereport_xpath)

            # Esperar a que se abra la nueva pestaña y cambiar a ella
            self.browser_wrapper.wait_for_new_tab(timeout=10000)  # Esperar hasta 10 segundos
            self.browser_wrapper.switch_to_new_tab()
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # standard reports (click)
            standard_reports_xpath = (
                "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/div[1]/div[1]/ul[1]/li[2]/div[1]/span[1]/a[1]"
            )
            self.browser_wrapper.click_element(standard_reports_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            return {"section": "monthly_reports", "ready_for_download": True}

        except Exception as e:
            try:
                if self.browser_wrapper.get_tab_count() > 1:
                    self.browser_wrapper.close_current_tab()
                    self.browser_wrapper.switch_to_previous_tab()
            except:
                pass
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        downloaded_files = []
        report_types = ["Cost Overview", "Enhanced User Profile Report", "Usage Overview"]

        standard_report_dropdown_xpath = (
            "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/select[1]"
        )
        left_date_dropdown_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div[1]/div[7]/div[1]/div[2]/div[1]/select[1]"
        right_date_dropdown_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div[1]/div[7]/div[1]/div[2]/div[1]/select[2]"
        apply_button_xpath = (
            "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div[1]/div[11]/div[2]/button[1]"
        )
        excel_image_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/img[2]"

        start_date_text = billing_cycle.start_date.strftime("%b %Y")
        end_date_text = billing_cycle.end_date.strftime("%b %Y")
        for report_name in report_types:
            selected_option = self.browser_wrapper.get_text(standard_report_dropdown_xpath)
            if not selected_option or report_name.lower() not in selected_option.lower():
                self.browser_wrapper.select_dropdown_option(standard_report_dropdown_xpath, report_name)
                time.sleep(2)

            self.browser_wrapper.select_dropdown_option(left_date_dropdown_xpath, start_date_text)
            self.browser_wrapper.select_dropdown_option(right_date_dropdown_xpath, end_date_text)
            self.browser_wrapper.click_element(apply_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            self.browser_wrapper.click_element(excel_image_xpath)
            time.sleep(10)

        try:
            records = 3
            page = self.browser_wrapper.page
            status_board_locator = page.locator(
                "xpath=//body/div[@id='reportStatusBar']/div[@id='reportStatusBarContent']/div[@id='reportStatusBarRequests']/table[1]"
            )
            status_board_locator.wait_for(timeout=120_000)
            rows = status_board_locator.locator("tr").all()[:records]

            for i, row in enumerate(rows, start=1):
                try:
                    download_link = row.locator("td >> nth=0 >> a")

                    with page.expect_download() as download_info:
                        download_link.click()

                    download = download_info.value

                    suggested_filename = f"report_{i}_{datetime.now().timestamp()}_{download.suggested_filename}"
                    final_path = os.path.join(DOWNLOADS_DIR, suggested_filename)

                    # Guardar en disco
                    download.save_as(final_path)

                    downloaded_files.append(
                        FileDownloadInfo(
                            file_id=i, file_name=suggested_filename, download_url="N/A", file_path=final_path
                        )
                    )

                except Exception as e:
                    print(f"❌ Error al intentar descargar archivo #{i}: {e}")
                    continue

            self.browser_wrapper.close_current_tab()
            self.browser_wrapper.switch_to_previous_tab()
            time.sleep(2)

            return downloaded_files
        except Exception as e:
            print(f"❌ Error general al procesar la tabla de descargas: {e}")
            return downloaded_files

    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        """Envía los archivos descargados al endpoint externo."""
        try:
            for file_info in files:
                endpoint_url = f"https://api.expertel.com/billing_cycle_files/{file_info.file_id}/upload"
                # Aquí iría la lógica real de envío
                # requests.post(endpoint_url, files={'file': open(file_info.file_path, 'rb')})

            return True

        except Exception as e:
            return False


class BellDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos de uso diario en el portal de Bell."""
        try:
            # Flujo 1: Suscriber account usage details
            # usage: (hover)
            usage_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[2]/a[1]"
            self.browser_wrapper.hover_element(usage_xpath)
            time.sleep(2)  # Esperar 2 segundos

            # suscriber account usage details: (click)
            suscriber_details_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[2]/div[1]/ul[1]/li[2]/ul[1]/li[1]/a[1]/span[1]"
            self.browser_wrapper.click_element(suscriber_details_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)  # Esperar 5 segundos

            # put a comment, there's other logic that needs to be solved
            search_input_xpath = "/html/body/div[1]/main/div[1]/div/account-selection/div[2]/section/div/account-selection-global-search/div/div[2]/section[2]/div/div/account-search/div/div[1]/div[1]/input"
            self.browser_wrapper.type_text(search_input_xpath, "502462125")
            search_button = "/html/body/div[1]/main/div[1]/div/account-selection/div[2]/section/div/account-selection-global-search/div/div[2]/section[2]/div/div/account-search/div/div[1]/div[2]/button"
            self.browser_wrapper.click_element(search_button)
            view_subscribers_btn_xpath = "/html/body/div[1]/main/div[1]/div/account-selection/div[2]/section/div/account-selection-global-search/div/section/div/search/div[2]/div[1]/div[2]/table/tbody/tr/td[9]/button"
            self.browser_wrapper.click_element(view_subscribers_btn_xpath)

            # Flujo 2: Billing account usage details
            # usage: (hover)
            self.browser_wrapper.hover_element(usage_xpath)  # Re-hover if necessary
            time.sleep(10)

            # billing account usage details: (click)
            billing_details_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[2]/div[1]/ul[1]/li[1]/ul[1]/li[1]/a[1]/span[1]"
            self.browser_wrapper.click_element(billing_details_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)  # Esperar 5 segundos

            # Select Corp Data Share option
            dropdown_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/div[2]/account-details[1]/div[1]/div[2]/account-shared-data[1]/div[2]/category-usage-details[1]/div[1]/div[2]/div[4]/div[1]/subscriber-usage-details[1]/div[1]/div[2]/filter-selection[1]/div[1]/select[1]"
            self.browser_wrapper.select_dropdown_option(dropdown_xpath, "All usage")
            self.browser_wrapper.wait_for_page_load()  # after loaded
            time.sleep(5)  # Esperar 5 segundos

            return {"section": "daily_usage", "ready_for_download": True}

        except Exception as e:
            # log exception e
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> Optional[FileDownloadInfo]:
        """Descarga los archivos de uso diario de Bell."""
        try:
            # download tab: (click)
            download_tab_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/div[2]/account-details[1]/div[1]/div[2]/account-shared-data[1]/div[2]/category-usage-details[1]/div[1]/div[2]/div[4]/div[1]/subscriber-usage-details[1]/div[1]/div[3]/div[1]/search[1]/nav[1]/ul[1]/li[3]/a[1]/i[2]"
            self.browser_wrapper.click_element(download_tab_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)  # Esperar 5 segundos

            # download all pages: (click)
            download_all_pages_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/div[2]/account-details[1]/div[1]/div[2]/account-shared-data[1]/div[2]/category-usage-details[1]/div[1]/div[2]/div[4]/div[1]/subscriber-usage-details[1]/div[1]/div[3]/div[1]/search[1]/nav[1]/ul[1]/li[3]/ul[1]/li[1]/a[1]"
            page = self.browser_wrapper.page
            with page.expect_download() as download_info:
                self.browser_wrapper.click_element(download_all_pages_xpath)
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)

            download = download_info.value
            suggested_filename = f"report_{datetime.now().timestamp()}_{download.suggested_filename}"
            final_path = os.path.join(DOWNLOADS_DIR, suggested_filename)

            # Guardar en disco
            download.save_as(final_path)

            dowloaded_file = FileDownloadInfo(
                file_id=1, file_name=suggested_filename, download_url="N/A", file_path=final_path
            )
            return dowloaded_file
        except Exception as e:
            return None

    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        """Envía los archivos descargados al endpoint externo."""
        try:
            for file_info in files:
                endpoint_url = f"https://api.expertel.com/daily_usage_files/{file_info.file_id}/upload"
                # Aquí iría la lógica real de envío

            return True

        except Exception as e:
            return False


class BellPDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de facturas PDF en el portal de Bell."""
        try:
            # hover on billing
            billing_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[3]/a[1]"
            self.browser_wrapper.hover_element(billing_xpath)
            time.sleep(2)  # Esperar 2 segundos

            # click on download_pdf
            download_pdf_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[3]/div[1]/ul[1]/li[1]/ul[1]/li[3]/a[1]"
            self.browser_wrapper.click_element(download_pdf_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)  # Esperar 5 segundos

            # account selection (optional, can be skipped)
            select_button_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[2]/section[1]/section[1]/div[3]/div[1]/div[3]/button[1]"
            if self.browser_wrapper.find_element_by_xpath(select_button_xpath, timeout=5000):  # 5 seconds timeout
                self.browser_wrapper.click_element(select_button_xpath)
                time.sleep(2)  # Esperar 2 segundos

                specific_account_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[2]/section[1]/section[1]/div[2]/div[3]/search[1]/div[2]/div[1]/div[2]/table[1]/tbody[1]/tr[1]/td[10]/button[1]"
                self.browser_wrapper.click_element(specific_account_xpath)
                time.sleep(2)  # Esperar 2 segundos

                continue_button_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[9]/selection-dock[1]/div[1]/div[1]/div[1]/div[4]/button[1]"
                self.browser_wrapper.click_element(continue_button_xpath)
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)  # Esperar 5 segundos

            # complete invoice radio button
            complete_invoice_radio_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[3]/download-options[1]/div[1]/div[1]/section[1]/div[1]/label[2]/span[1]"
            self.browser_wrapper.click_element(complete_invoice_radio_xpath)
            time.sleep(2)  # Esperar 2 segundos

            # checkbox logic for specific period (e.g., "June 2025")
            # Using calendar to get locale-independent English month name.
            month_name = calendar.month_name[billing_cycle.start_date.month]
            period_text = f"{month_name} {billing_cycle.start_date.year}"

            # This XPath assumes the label containing the checkbox also contains the period text.
            checkbox_period_xpath = f'//label[contains(., "{period_text}")]/span[1]'
            self.browser_wrapper.click_element(checkbox_period_xpath)
            time.sleep(2)  # Esperar 2 segundos

            return {"section": "pdf_invoices", "ready_for_download": True}

        except Exception as e:
            # log exception e
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de Bell."""
        downloaded_files = []

        try:
            # Click first download button
            download_button_1_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[3]/download-options[1]/div[1]/div[1]/div[1]/div[1]/button[2]"
            self.browser_wrapper.click_element(download_button_1_xpath)
            time.sleep(5)  # Esperar 5 segundos

            # wait up to three minutes for generation for the "download now" button to appear
            download_button_2_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[4]/confirmation[1]/div[1]/div[1]/section[1]/button[1]"
            self.browser_wrapper.wait_for_element(download_button_2_xpath, timeout=180000)  # 3 minutes in ms
            time.sleep(10)  # Esperar 10 segundos

            # Click second download button to trigger download
            self.browser_wrapper.click_element(download_button_2_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)  # Esperar 5 segundos

            # TODO: Handle actual file download
            file_info = FileDownloadInfo(
                file_id=1,  # Placeholder
                file_name=f"bell_invoice_{billing_cycle.start_date.strftime('%Y-%m-%d')}.pdf",
                download_url="N/A",
                file_path=f"/tmp/bell_invoice_{billing_cycle.id}.pdf",
            )
            downloaded_files.append(file_info)

            return downloaded_files

        except Exception as e:
            # log exception e
            return downloaded_files

    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        """Envía los archivos descargados al endpoint externo."""
        try:
            for file_info in files:
                endpoint_url = f"https://api.expertel.com/billing_cycle_files/{file_info.file_id}/upload"
                # Aquí iría la lógica real de envío

            return True

        except Exception as e:
            return False
