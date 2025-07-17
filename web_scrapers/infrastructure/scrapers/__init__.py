"""
Módulo de scrapers para todos los carriers.

Este módulo contiene las implementaciones concretas de scrapers para cada carrier,
siguiendo el patrón template definido en las clases base.
"""

from .att_scrapers import (
    ATTDailyUsageScraperStrategy,
    ATTMonthlyReportsScraperStrategy,
    ATTPDFInvoiceScraperStrategy,
)

# Importar todas las implementaciones de scrapers
from .bell_scrapers import (
    BellDailyUsageScraperStrategy,
    BellMonthlyReportsScraperStrategy,
    BellPDFInvoiceScraperStrategy,
)
from .rogers_scrapers import (
    RogersDailyUsageScraperStrategy,
    RogersMonthlyReportsScraperStrategy,
    RogersPDFInvoiceScraperStrategy,
)
from .telus_scrapers import (
    TelusDailyUsageScraperStrategy,
    TelusMonthlyReportsScraperStrategy,
    TelusPDFInvoiceScraperStrategy,
)
from .tmobile_scrapers import (
    TMobileDailyUsageScraperStrategy,
    TMobileMonthlyReportsScraperStrategy,
    TMobilePDFInvoiceScraperStrategy,
)
from .verizon_scrapers import (
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
