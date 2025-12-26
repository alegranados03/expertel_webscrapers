import os
import time
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    FileDownloadInfo,
    MonthlyReportsScraperStrategy,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class TMobileMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para T-Mobile."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la seccion de archivos mensuales en el portal de T-Mobile."""
        try:
            print("Navegando a reportes mensuales de T-Mobile...")

            # Navegar a la seccion de reportes mensuales
            reports_xpath = (
                "//a[contains(@href, 'reports') or contains(text(), 'Reports') or contains(text(), 'Reportes')]"
            )
            if not self.browser_wrapper.find_element_by_xpath(reports_xpath):
                print("Seccion de reportes no encontrada")
                return None

            self.browser_wrapper.click_element(reports_xpath)
            self.browser_wrapper.wait_for_page_load()

            # Buscar la seccion especifica de archivos mensuales
            monthly_section_xpath = "//div[contains(@class, 'monthly') or contains(text(), 'Monthly')]"
            if not self.browser_wrapper.find_element_by_xpath(monthly_section_xpath):
                print("Seccion monthly no encontrada")
                return None

            print("Seccion de reportes mensuales encontrada")
            return {"section": "monthly_reports", "xpath": monthly_section_xpath}

        except Exception as e:
            print(f"Error navegando a reportes mensuales: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos mensuales de T-Mobile."""
        downloaded_files = []

        # Mapear BillingCycleFiles por slug
        billing_cycle_file_map = {}
        if billing_cycle.billing_cycle_files:
            for bcf in billing_cycle.billing_cycle_files:
                if bcf.carrier_report and bcf.carrier_report.slug:
                    billing_cycle_file_map[bcf.carrier_report.slug] = bcf
                    print(f"Mapeando BillingCycleFile ID {bcf.id} -> Slug: '{bcf.carrier_report.slug}'")

        try:
            print("Descargando archivos de reportes mensuales...")

            # TODO: Implementar logica de descarga especifica de T-Mobile
            # La implementacion original simulaba la descarga

            # Reset a pantalla principal
            self._reset_to_main_screen()

            print(f"Descarga completada: {len(downloaded_files)} archivos")
            return downloaded_files

        except Exception as e:
            print(f"Error en descarga de archivos: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de T-Mobile."""
        try:
            print("Reseteando a T-Mobile...")
            self.browser_wrapper.goto("https://b2b.t-mobile.com/")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("Reset completado")
        except Exception as e:
            print(f"Error en reset: {str(e)}")
