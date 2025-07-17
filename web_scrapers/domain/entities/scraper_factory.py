from typing import Dict, Optional, Type

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.scraper_strategies import ScraperBaseStrategy
from web_scrapers.domain.entities.session import Carrier
from web_scrapers.domain.enums import ScraperType
from web_scrapers.infrastructure.scrapers.att_scrapers import (
    ATTDailyUsageScraperStrategy,
    ATTMonthlyReportsScraperStrategy,
    ATTPDFInvoiceScraperStrategy,
)
from web_scrapers.infrastructure.scrapers.bell_scrapers import (
    BellDailyUsageScraperStrategy,
    BellMonthlyReportsScraperStrategy,
    BellPDFInvoiceScraperStrategy,
)
from web_scrapers.infrastructure.scrapers.rogers_scrapers import (
    RogersDailyUsageScraperStrategy,
    RogersMonthlyReportsScraperStrategy,
    RogersPDFInvoiceScraperStrategy,
)
from web_scrapers.infrastructure.scrapers.telus_scrapers import (
    TelusDailyUsageScraperStrategy,
    TelusMonthlyReportsScraperStrategy,
    TelusPDFInvoiceScraperStrategy,
)
from web_scrapers.infrastructure.scrapers.tmobile_scrapers import (
    TMobileDailyUsageScraperStrategy,
    TMobileMonthlyReportsScraperStrategy,
    TMobilePDFInvoiceScraperStrategy,
)
from web_scrapers.infrastructure.scrapers.verizon_scrapers import (
    VerizonDailyUsageScraperStrategy,
    VerizonMonthlyReportsScraperStrategy,
    VerizonPDFInvoiceScraperStrategy,
)


class ScraperStrategyFactory:

    def __init__(self):
        self._strategies: Dict[tuple[Carrier, ScraperType], Type[ScraperBaseStrategy]] = {
            # Bell
            (Carrier.BELL, ScraperType.MONTHLY_REPORTS): BellMonthlyReportsScraperStrategy,
            (Carrier.BELL, ScraperType.DAILY_USAGE): BellDailyUsageScraperStrategy,
            (Carrier.BELL, ScraperType.PDF_INVOICE): BellPDFInvoiceScraperStrategy,
            # Telus
            (Carrier.TELUS, ScraperType.MONTHLY_REPORTS): TelusMonthlyReportsScraperStrategy,
            (Carrier.TELUS, ScraperType.DAILY_USAGE): TelusDailyUsageScraperStrategy,
            (Carrier.TELUS, ScraperType.PDF_INVOICE): TelusPDFInvoiceScraperStrategy,
            # Rogers
            (Carrier.ROGERS, ScraperType.MONTHLY_REPORTS): RogersMonthlyReportsScraperStrategy,
            (Carrier.ROGERS, ScraperType.DAILY_USAGE): RogersDailyUsageScraperStrategy,
            (Carrier.ROGERS, ScraperType.PDF_INVOICE): RogersPDFInvoiceScraperStrategy,
            # ATT
            (Carrier.ATT, ScraperType.MONTHLY_REPORTS): ATTMonthlyReportsScraperStrategy,
            (Carrier.ATT, ScraperType.DAILY_USAGE): ATTDailyUsageScraperStrategy,
            (Carrier.ATT, ScraperType.PDF_INVOICE): ATTPDFInvoiceScraperStrategy,
            # T-Mobile
            (Carrier.TMOBILE, ScraperType.MONTHLY_REPORTS): TMobileMonthlyReportsScraperStrategy,
            (Carrier.TMOBILE, ScraperType.DAILY_USAGE): TMobileDailyUsageScraperStrategy,
            (Carrier.TMOBILE, ScraperType.PDF_INVOICE): TMobilePDFInvoiceScraperStrategy,
            # Verizon
            (Carrier.VERIZON, ScraperType.MONTHLY_REPORTS): VerizonMonthlyReportsScraperStrategy,
            (Carrier.VERIZON, ScraperType.DAILY_USAGE): VerizonDailyUsageScraperStrategy,
            (Carrier.VERIZON, ScraperType.PDF_INVOICE): VerizonPDFInvoiceScraperStrategy,
        }

    def create_scraper(
        self, carrier: Carrier, scraper_type: ScraperType, browser_wrapper: BrowserWrapper
    ) -> Optional[ScraperBaseStrategy]:
        strategy_class = self._strategies.get((carrier, scraper_type))

        if not strategy_class:
            raise ValueError(f"No strategy for carrier {carrier} and type {scraper_type}")

        return strategy_class(browser_wrapper)
