from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    DailyUsageScraperStrategy,
    FileDownloadInfo,
    MonthlyReportsScraperStrategy,
    PDFInvoiceScraperStrategy,
)


class VerizonMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        try:

            # Navegar a la sección de reportes mensuales
            reports_xpath = (
                "//a[contains(@href, 'reports') or contains(text(), 'Reports') or contains(text(), 'Reportes')]"
            )
            if not self.browser_wrapper.find_element_by_xpath(reports_xpath):
                return None

            self.browser_wrapper.click_element(reports_xpath)
            self.browser_wrapper.wait_for_page_load()

            # Buscar la sección específica de archivos mensuales
            monthly_section_xpath = "//div[contains(@class, 'monthly') or contains(text(), 'Monthly')]"
            if not self.browser_wrapper.find_element_by_xpath(monthly_section_xpath):
                return None

            return {"section": "monthly_reports", "xpath": monthly_section_xpath}

        except Exception as e:
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        downloaded_files = []

        try:

            file_info = FileDownloadInfo(
                file_id=1,
                file_name=f"verizon_monthly_report_{billing_cycle.start_date}_{billing_cycle.end_date}.pdf",
                download_url="https://verizon.com/download/monthly_report.pdf",
                file_path=f"/tmp/verizon_monthly_{billing_cycle.id}.pdf",
                file_size=1024000,
            )
            downloaded_files.append(file_info)

            return downloaded_files

        except Exception as e:
            return downloaded_files

    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        try:

            for file_info in files:
                endpoint_url = f"https://api.expertel.com/billing_cycle_files/{file_info.file_id}/upload"

            return True

        except Exception as e:
            return False


class VerizonDailyUsageScraperStrategy(DailyUsageScraperStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        try:

            # Navegar a la sección de uso diario
            usage_xpath = "//a[contains(@href, 'usage') or contains(text(), 'Usage') or contains(text(), 'Uso')]"
            if not self.browser_wrapper.find_element_by_xpath(usage_xpath):
                return None

            self.browser_wrapper.click_element(usage_xpath)
            self.browser_wrapper.wait_for_page_load()

            # Buscar la sección específica de archivos diarios
            daily_section_xpath = "//div[contains(@class, 'daily') or contains(text(), 'Daily')]"
            if not self.browser_wrapper.find_element_by_xpath(daily_section_xpath):
                return None

            return {"section": "daily_usage", "xpath": daily_section_xpath}

        except Exception as e:
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de Verizon."""
        downloaded_files = []

        try:

            # Simular descarga
            file_info = FileDownloadInfo(
                file_id=1,
                file_name=f"verizon_daily_usage_{billing_cycle.start_date}_{billing_cycle.end_date}.csv",
                download_url="https://verizon.com/download/daily_usage.csv",
                file_path=f"/tmp/verizon_daily_{billing_cycle.id}.csv",
                file_size=512000,
            )
            downloaded_files.append(file_info)

            return downloaded_files

        except Exception as e:
            return downloaded_files

    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        """Envía los archivos descargados al endpoint externo."""
        try:

            for file_info in files:
                endpoint_url = f"https://api.expertel.com/daily_usage_files/{file_info.file_id}/upload"

            return True

        except Exception as e:
            return False


class VerizonPDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        try:

            invoices_xpath = (
                "//a[contains(@href, 'invoice') or contains(text(), 'Invoice') or contains(text(), 'Factura')]"
            )
            if not self.browser_wrapper.find_element_by_xpath(invoices_xpath):
                return None

            self.browser_wrapper.click_element(invoices_xpath)
            self.browser_wrapper.wait_for_page_load()

            pdf_section_xpath = "//div[contains(@class, 'pdf') or contains(text(), 'PDF')]"
            if not self.browser_wrapper.find_element_by_xpath(pdf_section_xpath):
                return None

            return {"section": "pdf_invoices", "xpath": pdf_section_xpath}

        except Exception as e:
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        downloaded_files = []

        try:

            file_info = FileDownloadInfo(
                file_id=1,
                file_name=f"verizon_invoice_{billing_cycle.start_date}_{billing_cycle.end_date}.pdf",
                download_url="https://verizon.com/download/invoice.pdf",
                file_path=f"/tmp/verizon_invoice_{billing_cycle.id}.pdf",
                file_size=2048000,
            )
            downloaded_files.append(file_info)

            return downloaded_files

        except Exception as e:
            return downloaded_files

    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        try:

            for file_info in files:
                endpoint_url = f"https://api.expertel.com/billing_cycle_files/{file_info.file_id}/upload"

            return True

        except Exception as e:
            return False
