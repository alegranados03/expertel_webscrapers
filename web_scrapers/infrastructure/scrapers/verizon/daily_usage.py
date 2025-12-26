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


class VerizonDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para Verizon."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de uso diario de Verizon."""
        try:
            print("Navegando a uso diario de Verizon...")

            # 1. Click en report tab
            report_tab_xpath = "/html/body/app-root/app-secure-layout/div/div[1]/app-header/header/div[2]/div/div/div[1]/div[2]/header/div/div/div[2]/nav/ul/li[4]/a"
            print("Haciendo clic en report tab...")
            self.browser_wrapper.click_element(report_tab_xpath)
            time.sleep(2)

            # 2. Click en reports home
            reports_home_xpath = "/html/body/app-root/app-secure-layout/div/div[1]/app-header/header/div[2]/div/div/div[1]/div[2]/header/div/div/div[2]/nav/ul/li[4]/div/div/div[1]/div/ul/li[1]/a"
            print("Haciendo clic en reports home...")
            self.browser_wrapper.click_element(reports_home_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            # 3. Click en usage tab
            usage_tab_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[2]/app-tab-click/div/div[1]/ul/li[3]"
            print("Haciendo clic en usage tab...")
            self.browser_wrapper.click_element(usage_tab_xpath)
            time.sleep(2)

            print("Navegacion a uso diario completada")
            return {"section": "daily_usage", "ready_for_download": True}

        except Exception as e:
            print(f"Error navegando a uso diario: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de Verizon."""
        downloaded_files = []

        # Obtener el BillingCycleDailyUsageFile del billing_cycle
        daily_usage_file = billing_cycle.daily_usage_files[0] if billing_cycle.daily_usage_files else None
        if daily_usage_file:
            print(f"Mapeando archivo Daily Usage -> BillingCycleDailyUsageFile ID {daily_usage_file.id}")

        try:
            print("Descargando archivos de uso diario...")

            # 4. Click en account unbilled usage block usando logica de busqueda inteligente
            account_unbilled_xpath = self._find_report_by_title_in_usage("Account unbilled usage")
            if account_unbilled_xpath:
                print("Haciendo clic en Account unbilled usage...")
                self.browser_wrapper.click_element(account_unbilled_xpath)
                time.sleep(2)

                # 5. Download full report
                download_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/div[1]/app-reporting-dashboard/div/div[2]/div/div[1]/div/div[1]/div[2]/div"
                print("Descargando Daily Usage report...")

                file_path = self.browser_wrapper.expect_download_and_click(
                    download_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
                )

                if file_path:
                    actual_filename = os.path.basename(file_path)
                    print(f"Daily Usage descargado: {actual_filename}")

                    file_info = FileDownloadInfo(
                        file_id=daily_usage_file.id,
                        file_name=actual_filename,
                        download_url="N/A",
                        file_path=file_path,
                        daily_usage_file=daily_usage_file,
                    )
                    downloaded_files.append(file_info)

                    # Confirmar mapeo
                    if daily_usage_file:
                        print(
                            f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleDailyUsageFile ID {daily_usage_file.id}"
                        )
                else:
                    print("No se pudo descargar Daily Usage report")
            else:
                print("No se encontro Account unbilled usage report")

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

    def _find_report_by_title_in_usage(self, title: str) -> Optional[str]:
        """Encuentra un reporte por su titulo dentro del componente app-reports-list de usage."""
        try:
            print(f"Buscando reporte: {title}")

            # Obtener el contenedor de reportes de usage
            container_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[4]/div[4]/div/app-reports-list"

            # Usar JavaScript para encontrar el reporte por titulo
            report_xpath = self.browser_wrapper.page.evaluate(
                f"""
                () => {{
                    const container = document.evaluate("{container_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (container) {{
                        const reportBlocks = container.querySelectorAll('div[role="link"][aria-label="Report"]');
                        for (let block of reportBlocks) {{
                            const titleElement = block.querySelector('h3 span[title]');

                            if (titleElement && titleElement.getAttribute('title').includes("{title}")) {{
                                // Construir el XPath del elemento
                                let xpath = '';
                                let element = block;
                                while (element && element.nodeType === Node.ELEMENT_NODE) {{
                                    let tagName = element.nodeName.toLowerCase();
                                    if (element.id) {{
                                        xpath = '//' + tagName + '[@id="' + element.id + '"]' + xpath;
                                        break;
                                    }} else {{
                                        let position = Array.from(element.parentNode.children).indexOf(element) + 1;
                                        xpath = '/' + tagName + '[' + position + ']' + xpath;
                                        element = element.parentElement;
                                    }}
                                }}
                                return '/html' + xpath;
                            }}
                        }}
                    }}
                    return null;
                }}
            """
            )

            if report_xpath:
                print(f"Reporte encontrado: {report_xpath}")
                return report_xpath
            else:
                print(f"No se encontro el reporte: {title}")
                return None

        except Exception as e:
            print(f"Error buscando reporte por titulo: {str(e)}")
            return None

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Verizon."""
        try:
            print("Reseteando a dashboard de Verizon...")
            dashboard_url = "https://mb.verizonwireless.com/mbt/secure/index?appName=esm#/esm/dashboard"
            self.browser_wrapper.goto(dashboard_url)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("Reset completado")
        except Exception as e:
            print(f"Error en reset: {str(e)}")
