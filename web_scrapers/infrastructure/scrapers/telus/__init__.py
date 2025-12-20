from web_scrapers.infrastructure.scrapers.telus.daily_usage import TelusDailyUsageScraperStrategy
from web_scrapers.infrastructure.scrapers.telus.monthly_reports import TelusMonthlyReportsScraperStrategy
from web_scrapers.infrastructure.scrapers.telus.pdf_invoice import TelusPDFInvoiceScraperStrategy

__all__ = [
    "TelusMonthlyReportsScraperStrategy",
    "TelusDailyUsageScraperStrategy",
    "TelusPDFInvoiceScraperStrategy",
]