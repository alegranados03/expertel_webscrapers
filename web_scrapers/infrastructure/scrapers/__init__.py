"""
Módulo de scrapers para todos los carriers.

Este módulo contiene las implementaciones concretas de scrapers para cada carrier,
siguiendo el patrón template definido en las clases base.
"""

from web_scrapers.infrastructure.scrapers.att import (
    ATTDailyUsageScraperStrategy,
    ATTMonthlyReportsScraperStrategy,
    ATTPDFInvoiceScraperStrategy,
)
from web_scrapers.infrastructure.scrapers.bell import (
    BellDailyUsageScraperStrategy,
    BellMonthlyReportsScraperStrategy,
    BellMonthlyReportsScraperStrategyLegacy,
    BellPDFInvoiceScraperStrategy,
)
from web_scrapers.infrastructure.scrapers.rogers import (
    RogersDailyUsageScraperStrategy,
    RogersMonthlyReportsScraperStrategy,
    RogersPDFInvoiceScraperStrategy,
)
from web_scrapers.infrastructure.scrapers.telus import (
    TelusDailyUsageScraperStrategy,
    TelusMonthlyReportsScraperStrategy,
    TelusPDFInvoiceScraperStrategy,
)
from web_scrapers.infrastructure.scrapers.tmobile import (
    TMobileDailyUsageScraperStrategy,
    TMobileMonthlyReportsScraperStrategy,
    TMobilePDFInvoiceScraperStrategy,
)
from web_scrapers.infrastructure.scrapers.verizon import (
    VerizonDailyUsageScraperStrategy,
    VerizonMonthlyReportsScraperStrategy,
    VerizonPDFInvoiceScraperStrategy,
)

__all__ = [
    # Bell
    "BellMonthlyReportsScraperStrategy",
    "BellDailyUsageScraperStrategy",
    "BellPDFInvoiceScraperStrategy",
    # Telus
    "TelusMonthlyReportsScraperStrategy",
    "TelusDailyUsageScraperStrategy",
    "TelusPDFInvoiceScraperStrategy",
    # Rogers
    "RogersMonthlyReportsScraperStrategy",
    "RogersDailyUsageScraperStrategy",
    "RogersPDFInvoiceScraperStrategy",
    # ATT
    "ATTMonthlyReportsScraperStrategy",
    "ATTDailyUsageScraperStrategy",
    "ATTPDFInvoiceScraperStrategy",
    # T-Mobile
    "TMobileMonthlyReportsScraperStrategy",
    "TMobileDailyUsageScraperStrategy",
    "TMobilePDFInvoiceScraperStrategy",
    # Verizon
    "VerizonMonthlyReportsScraperStrategy",
    "VerizonDailyUsageScraperStrategy",
    "VerizonPDFInvoiceScraperStrategy",
]
