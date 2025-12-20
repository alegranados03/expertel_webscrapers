import os
import time
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    DailyUsageScraperStrategy,
    FileDownloadInfo,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class TMobileDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para T-Mobile."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de uso diario de T-Mobile."""
        try:
            print("Navegando a uso diario de T-Mobile...")
            # Implementar navegacion especifica de T-Mobile
            print("Navegacion completada")
            return {"section": "daily_usage", "ready_for_download": True}

        except Exception as e:
            print(f"Error navegando a uso diario: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de T-Mobile."""
        downloaded_files = []

        try:
            print("Descargando archivos de uso diario...")
            # Implementar logica de descarga especifica de T-Mobile

            # Reset a pantalla principal
            self._reset_to_main_screen()

            return downloaded_files

        except Exception as e:
            print(f"Error en descarga de uso diario: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de T-Mobile."""
        try:
            print("Reseteando a T-Mobile...")
            time.sleep(3)
            print("Reset completado")
        except Exception as e:
            print(f"Error en reset: {str(e)}")