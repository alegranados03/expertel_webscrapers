import calendar
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    DailyUsageScraperStrategy,
    FileDownloadInfo,
    MonthlyReportsScraperStrategy,
    PDFInvoiceScraperStrategy,
)


class BellMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def get_carrier_name(self) -> str:
        return "BELL"

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos mensuales en el portal de Bell."""
        try:
            # Look for reports
            report_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[4]/a[1]"
            self.browser_wrapper.hover_element(report_xpath)

            # e-report (click)
            ereport_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[4]/div[1]/ul[1]/li[1]/a[1]/h3[1]"
            self.browser_wrapper.click_element(ereport_xpath)

            # change tab - wait for new tab and switch to it
            self.browser_wrapper.wait_for_page_load()

            # standard reports (click)
            standard_reports_xpath = "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/div[1]/div[1]/ul[1]/li[2]/div[1]/span[1]/a[1]"
            self.browser_wrapper.click_element(standard_reports_xpath)
            self.browser_wrapper.wait_for_page_load()

            # standard report dropdown (check if cost overview is selected)
            standard_report_dropdown_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/select[1]"
            # Get selected option text to check if cost overview is selected
            selected_option = self.browser_wrapper.get_text(standard_report_dropdown_xpath)
            if selected_option and "cost overview" not in selected_option.lower():
                self.browser_wrapper.select_dropdown_option(standard_report_dropdown_xpath, "Cost Overview")

            # select based on billing cycle date range
            # Format dates for dropdown selection
            start_date_text = billing_cycle.start_date.strftime('%B %Y')
            end_date_text = billing_cycle.end_date.strftime('%B %Y')

            # left date dropdown
            left_date_dropdown_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div[1]/div[7]/div[1]/div[2]/div[1]/select[1]"
            self.browser_wrapper.select_dropdown_option(left_date_dropdown_xpath, start_date_text)

            # right date dropdown
            right_date_dropdown_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div[1]/div[7]/div[1]/div[2]/div[1]/select[2]"
            self.browser_wrapper.select_dropdown_option(right_date_dropdown_xpath, end_date_text)

            # apply button (click)
            apply_button_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div[1]/div[11]/div[2]/button[1]"
            self.browser_wrapper.click_element(apply_button_xpath)
            self.browser_wrapper.wait_for_page_load()

            # excel image to generate report (click)
            excel_image_xpath = "/html[1]/body[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/img[2]"
            self.browser_wrapper.click_element(excel_image_xpath)
            self.browser_wrapper.wait_for_page_load()

            # My documents window - iterate my documents window (here starts the real download)
            my_documents_xpath = "/html[1]/body[1]/div[4]"
            self.browser_wrapper.hover_element(my_documents_xpath)

            return {"section": "monthly_reports", "ready_for_download": True}

        except Exception as e:
            # log exception e
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos mensuales de Bell."""
        downloaded_files = []
        try:
            # TODO: Implement actual download logic for My Documents window
            # This would involve iterating through the documents in the window
            # and downloading each one that matches the billing cycle criteria

            # Placeholder for now - simulate download
            file_info = FileDownloadInfo(
                file_id=1,  # Placeholder
                file_name=f"bell_monthly_report_{billing_cycle.start_date.strftime('%Y-%m-%d')}_{billing_cycle.end_date.strftime('%Y-%m-%d')}.xlsx",
                download_url="N/A",
                file_path=f"/tmp/bell_monthly_{billing_cycle.id}.xlsx",
                file_size=1024000,  # Placeholder
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
                # requests.post(endpoint_url, files={'file': open(file_info.file_path, 'rb')})

            return True

        except Exception as e:
            return False


class BellDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def get_carrier_name(self) -> str:
        return "BELL"

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos de uso diario en el portal de Bell."""
        try:
            # Flujo 1: Suscriber account usage details
            # usage: (hover)
            usage_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[2]/a[1]"
            self.browser_wrapper.hover_element(usage_xpath)

            # suscriber account usage details: (click)
            suscriber_details_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[2]/div[1]/ul[1]/li[2]/ul[1]/li[1]/a[1]/span[1]"
            self.browser_wrapper.click_element(suscriber_details_xpath)
            self.browser_wrapper.wait_for_page_load()

            # put a comment, there's other logic that needs to be solved
            # TODO: Another logic needs to be solved here.

            # Flujo 2: Billing account usage details
            # usage: (hover)
            self.browser_wrapper.hover_element(usage_xpath)  # Re-hover if necessary

            # billing account usage details: (click)
            billing_details_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[2]/div[1]/ul[1]/li[1]/ul[1]/li[1]/a[1]/span[1]"
            self.browser_wrapper.click_element(billing_details_xpath)
            self.browser_wrapper.wait_for_page_load()

            # Select Corp Data Share option
            dropdown_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/div[2]/account-details[1]/div[1]/div[2]/account-shared-data[1]/div[2]/category-usage-details[1]/div[1]/div[2]/div[4]/div[1]/subscriber-usage-details[1]/div[1]/div[2]/filter-selection[1]/div[1]/select[1]"
            self.browser_wrapper.select_dropdown_option(dropdown_xpath, "Corp Data Share")
            self.browser_wrapper.wait_for_page_load()  # after loaded

            return {"section": "daily_usage", "ready_for_download": True}

        except Exception as e:
            # log exception e
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de Bell."""
        downloaded_files = []
        try:
            # download tab: (click)
            download_tab_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/div[2]/account-details[1]/div[1]/div[2]/account-shared-data[1]/div[2]/category-usage-details[1]/div[1]/div[2]/div[4]/div[1]/subscriber-usage-details[1]/div[1]/div[3]/div[1]/search[1]/nav[1]/ul[1]/li[3]/a[1]/i[2]"
            self.browser_wrapper.click_element(download_tab_xpath)
            self.browser_wrapper.wait_for_page_load()

            # download all pages: (click)
            download_all_pages_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/div[2]/account-details[1]/div[1]/div[2]/account-shared-data[1]/div[2]/category-usage-details[1]/div[1]/div[2]/div[4]/div[1]/subscriber-usage-details[1]/div[1]/div[3]/div[1]/search[1]/nav[1]/ul[1]/li[3]/ul[1]/li[1]/a[1]"
            self.browser_wrapper.click_element(download_all_pages_xpath)
            self.browser_wrapper.wait_for_page_load()

            # TODO: Handle actual file download
            file_info = FileDownloadInfo(
                file_id=1,  # Placeholder
                file_name=f"bell_daily_usage_{billing_cycle.start_date.strftime('%Y-%m-%d')}_{billing_cycle.end_date.strftime('%Y-%m-%d')}.csv",
                download_url="N/A",
                file_path=f"/tmp/bell_daily_{billing_cycle.id}.csv",
                file_size=512000,  # Placeholder
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
                endpoint_url = f"https://api.expertel.com/daily_usage_files/{file_info.file_id}/upload"
                # Aquí iría la lógica real de envío

            return True

        except Exception as e:
            return False


class BellPDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def get_carrier_name(self) -> str:
        return "BELL"

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de facturas PDF en el portal de Bell."""
        try:
            # hover on billing
            billing_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[3]/a[1]"
            self.browser_wrapper.hover_element(billing_xpath)

            # click on download_pdf
            download_pdf_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[3]/div[1]/ul[1]/li[1]/ul[1]/li[3]/a[1]"
            self.browser_wrapper.click_element(download_pdf_xpath)
            self.browser_wrapper.wait_for_page_load()

            # account selection (optional, can be skipped)
            select_button_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[2]/section[1]/section[1]/div[3]/div[1]/div[3]/button[1]"
            if self.browser_wrapper.find_element_by_xpath(select_button_xpath, timeout=5000):  # 5 seconds timeout
                self.browser_wrapper.click_element(select_button_xpath)

                specific_account_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[2]/section[1]/section[1]/div[2]/div[3]/search[1]/div[2]/div[1]/div[2]/table[1]/tbody[1]/tr[1]/td[10]/button[1]"
                self.browser_wrapper.click_element(specific_account_xpath)

                continue_button_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[2]/account-selection[1]/div[9]/selection-dock[1]/div[1]/div[1]/div[1]/div[4]/button[1]"
                self.browser_wrapper.click_element(continue_button_xpath)
                self.browser_wrapper.wait_for_page_load()

            # complete invoice radio button
            complete_invoice_radio_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[3]/download-options[1]/div[1]/div[1]/section[1]/div[1]/label[2]/span[1]"
            self.browser_wrapper.click_element(complete_invoice_radio_xpath)

            # checkbox logic for specific period (e.g., "June 2025")
            # Using calendar to get locale-independent English month name.
            month_name = calendar.month_name[billing_cycle.start_date.month]
            period_text = f"{month_name} {billing_cycle.start_date.year}"

            # This XPath assumes the label containing the checkbox also contains the period text.
            checkbox_period_xpath = f'//label[contains(., "{period_text}")]/span[1]'
            self.browser_wrapper.click_element(checkbox_period_xpath)

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

            # wait up to three minutes for generation for the "download now" button to appear
            download_button_2_xpath = "/html[1]/body[1]/div[1]/main[1]/div[1]/uxp-flow[1]/div[4]/confirmation[1]/div[1]/div[1]/section[1]/button[1]"
            self.browser_wrapper.wait_for_element(download_button_2_xpath, timeout=180000)  # 3 minutes in ms

            # Click second download button to trigger download
            self.browser_wrapper.click_element(download_button_2_xpath)
            self.browser_wrapper.wait_for_page_load()

            # TODO: Handle actual file download
            file_info = FileDownloadInfo(
                file_id=1,  # Placeholder
                file_name=f"bell_invoice_{billing_cycle.start_date.strftime('%Y-%m-%d')}.pdf",
                download_url="N/A",
                file_path=f"/tmp/bell_invoice_{billing_cycle.id}.pdf",
                file_size=2048000,  # Placeholder
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
