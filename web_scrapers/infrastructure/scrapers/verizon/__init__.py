from web_scrapers.infrastructure.scrapers.verizon.daily_usage import VerizonDailyUsageScraperStrategy
from web_scrapers.infrastructure.scrapers.verizon.monthly_reports import VerizonMonthlyReportsScraperStrategy
from web_scrapers.infrastructure.scrapers.verizon.pdf_invoice import VerizonPDFInvoiceScraperStrategy

__all__ = [
    "VerizonMonthlyReportsScraperStrategy",
    "VerizonDailyUsageScraperStrategy",
    "VerizonPDFInvoiceScraperStrategy",
]
