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


class TelusMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para Telus."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de reportes mensuales de Telus."""
        try:
            print("Navegando a reportes mensuales de Telus...")

            # 1. Navegar a My Telus
            print("Navegando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            print("Navegacion inicial completada - listo para descarga de archivos")
            return {"section": "monthly_reports", "ready_for_download": True}

        except Exception as e:
            print(f"Error navegando a reportes mensuales: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de reportes mensuales de Telus."""
        downloaded_files = []

        # Mapear BillingCycleFiles por slug
        billing_cycle_file_map = {}
        if billing_cycle.billing_cycle_files:
            for bcf in billing_cycle.billing_cycle_files:
                if bcf.carrier_report and bcf.carrier_report.slug:
                    billing_cycle_file_map[bcf.carrier_report.slug] = bcf
                    print(f"Mapeando BillingCycleFile ID {bcf.id} -> Slug: '{bcf.carrier_report.slug}'")

        try:
            # === PARTE 1: DESCARGAR ZIP DESDE BILLS SECTION ===
            print("=== PARTE 1: DESCARGANDO ZIP DESDE BILLS SECTION ===")

            # 1. Click en bill options button
            bill_options_xpath = (
                "/html/body/div[5]/div/div/div/div[1]/div/div[3]/div/div/div/div/div/div/div[3]/div/div/div/div"
            )
            print("Click en bill options...")
            self.browser_wrapper.click_element(bill_options_xpath)
            time.sleep(3)

            # 2. Click en download bills section
            download_bills_xpath = "/html[1]/body[1]/div[5]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[1]/a[2]"
            print("Click en download bills section...")
            self.browser_wrapper.click_element(download_bills_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # 3. Buscar y click en el mes correcto basado en end_date
            target_month = billing_cycle.end_date.strftime("%B")
            target_year = billing_cycle.end_date.year

            print(f"Buscando mes: {target_month} {target_year}")
            month_clicked = self._find_and_click_target_month(target_month, target_year)

            if month_clicked:
                # 4. Descargar ZIP y procesar archivos extraidos
                zip_files = self._download_and_process_zip(billing_cycle, billing_cycle_file_map)
                downloaded_files.extend(zip_files)
                print(f"Parte 1 completada: {len(zip_files)} archivos del ZIP")
            else:
                print("No se pudo encontrar el mes objetivo, continuando sin ZIP")

            # === PARTE 2: DESCARGAR ARCHIVOS INDIVIDUALES DESDE REPORTS SECTION ===
            print("=== PARTE 2: DESCARGANDO ARCHIVOS INDIVIDUALES ===")

            # 1. Navegar a billing header
            billing_header_xpath = "/html[1]/body[1]/div[1]/div[1]/ul[1]/li[2]/a[1]/span[1]"
            print("Click en billing header...")
            self.browser_wrapper.click_element(billing_header_xpath)
            self.browser_wrapper.wait_for_page_load()
            print("Esperando 1 minuto...")
            time.sleep(60)

            # 2. Click en reports header
            reports_header_xpath = "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[3]/a[1]"
            print("Click en reports header...")
            self.browser_wrapper.click_element(reports_header_xpath)
            time.sleep(2)

            # 3. Click en detail reports
            detail_reports_xpath = (
                "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[3]/ul[1]/li[2]/a[1]/span[1]"
            )
            print("Click en detail reports...")
            self.browser_wrapper.click_element(detail_reports_xpath)
            self.browser_wrapper.wait_for_page_load()
            print("Esperando 1 minuto...")
            time.sleep(60)

            # 4. Configurar fecha
            self._configure_date_selection(billing_cycle)

            # 5. Descargar reportes individuales
            individual_files = self._download_individual_reports(billing_cycle, billing_cycle_file_map)
            downloaded_files.extend(individual_files)
            print(f"Parte 2 completada: {len(individual_files)} archivos individuales")

            # 6. Reset a pantalla principal
            self._reset_to_main_screen()

            print(f"DESCARGA TOTAL COMPLETADA: {len(downloaded_files)} archivos")
            return downloaded_files

        except Exception as e:
            print(f"Error en descarga de archivos: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _find_and_click_target_month(self, target_month: str, target_year: int) -> bool:
        """Busca y hace click en el mes objetivo dentro de la estructura de anos."""
        try:
            # Buscar el contenedor de bills section
            bills_container_xpath = "/html/body/div[1]/main/div/div[2]/div/div[2]"

            # Buscar el ano objetivo primero
            year_xpath = f"//h2[contains(text(), '{target_year}')]"
            if not self.browser_wrapper.find_element_by_xpath(year_xpath):
                print(f"No se encontro el ano {target_year}")
                return False

            print(f"Encontrado ano {target_year}")

            # Buscar el enlace del mes objetivo
            month_link_xpath = f"//div[contains(@class, 'css-146c3p1') and contains(text(), '{target_month}')]"

            if self.browser_wrapper.find_element_by_xpath(month_link_xpath):
                print(f"Encontrado mes {target_month}, haciendo click...")
                # Hacer click en el div parent que contiene el enlace
                parent_link_xpath = f"//div[contains(@class, 'css-146c3p1') and contains(text(), '{target_month}')]/parent::div/parent::div"
                self.browser_wrapper.click_element(parent_link_xpath)
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)
                return True
            else:
                print(f"No se encontro el mes {target_month} en el ano {target_year}")
                return False

        except Exception as e:
            print(f"Error buscando mes objetivo: {str(e)}")
            return False

    def _download_and_process_zip(self, billing_cycle: BillingCycle, file_map: dict) -> List[FileDownloadInfo]:
        """Descarga y procesa el ZIP con los archivos del mes."""
        downloaded_files = []

        try:
            # El click en el mes deberia llevarnos a una pagina con un enlace de descarga ZIP
            # Intentar encontrar el enlace de descarga (puede variar segun la estructura)

            # Posibles XPaths para el enlace de descarga ZIP
            zip_download_xpaths = [
                "//a[contains(@href, '.zip') or contains(text(), 'download') or contains(text(), 'Download')]",
                "//button[contains(text(), 'download') or contains(text(), 'Download')]",
                "//div[contains(@class, 'download')]//a",
            ]

            zip_file_path = None
            for xpath in zip_download_xpaths:
                try:
                    if self.browser_wrapper.find_element_by_xpath(xpath):
                        print(f"Intentando descargar ZIP con xpath: {xpath}")
                        zip_file_path = self.browser_wrapper.expect_download_and_click(
                            xpath, timeout=30000, downloads_dir=self.job_downloads_dir
                        )
                        if zip_file_path:
                            break
                except:
                    continue

            if not zip_file_path:
                print("No se pudo descargar ZIP")
                return downloaded_files

            print(f"ZIP descargado: {os.path.basename(zip_file_path)}")

            # Extraer archivos del ZIP
            extracted_files = self._extract_zip_files(zip_file_path)
            if not extracted_files:
                print("No se pudieron extraer archivos del ZIP")
                return downloaded_files

            print(f"Extraidos {len(extracted_files)} archivos del ZIP")

            # Procesar archivos extraidos y mapearlos
            for i, file_path in enumerate(extracted_files):
                original_filename = os.path.basename(file_path)
                print(f"Procesando archivo: {original_filename}")

                # Buscar el BillingCycleFile correspondiente
                corresponding_bcf = self._find_matching_billing_cycle_file(original_filename, file_map)

                if corresponding_bcf:
                    print(f"Mapeando {original_filename} -> BillingCycleFile ID {corresponding_bcf.id}")
                else:
                    print(f"No se encontro mapeo para {original_filename}")

                file_info = FileDownloadInfo(
                    file_id=corresponding_bcf.id if corresponding_bcf else (i + 1000),  # Offset para ZIP files
                    file_name=original_filename,
                    download_url="N/A",
                    file_path=file_path,
                    billing_cycle_file=corresponding_bcf,
                )
                downloaded_files.append(file_info)

            return downloaded_files

        except Exception as e:
            print(f"Error procesando ZIP: {str(e)}")
            return downloaded_files

    def _find_matching_billing_cycle_file(self, filename: str, file_map: dict) -> Optional[Any]:
        """Encuentra el BillingCycleFile que corresponde al nombre de archivo."""
        filename_lower = filename.lower()

        # Mapeo de patrones de nombres de archivos ZIP a slugs de Telus
        pattern_to_slug = {
            "account_detail": "invoice_detail",
            "airtime_detail": "airtime_detail",
            "dew_report": "wireless_data",
            "group_summary": "group_summary",
            "individual_detail": "individual_detail",
            "invoice_summary": "wireless_subscriber_charges",
            # Patrones adicionales para archivos individuales
            "wireless_subscriber_charges": "wireless_subscriber_charges",
            "wireless_subscriber_usage": "wireless_subscriber_usage",
            "mobility_device": "mobility_device",
            "wireless_voice": "wireless_voice",
            "wireless_data": "wireless_data",
        }

        for pattern, slug in pattern_to_slug.items():
            if pattern in filename_lower:
                bcf = file_map.get(slug)
                if bcf:
                    return bcf

        return None

    def _configure_date_selection(self, billing_cycle: BillingCycle):
        """Configura la seleccion de fecha para los reportes individuales."""
        try:
            # 1. Click en date selection
            date_selection_xpath = (
                "/html[1]/body[1]/div[2]/form[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/button[1]"
            )
            print("Click en date selection...")
            self.browser_wrapper.click_element(date_selection_xpath)
            time.sleep(2)

            # 2. Configurar dropdown de fecha
            target_period = billing_cycle.end_date.strftime("%B %Y") + " statements"
            select_date_dropdown_xpath = "/html[1]/body[1]/div[2]/form[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/select[1]"
            print(f"Seleccionando periodo: {target_period}")

            try:
                self.browser_wrapper.select_dropdown_option(select_date_dropdown_xpath, target_period)
            except:
                # Fallback: buscar solo por mes y ano sin "statements"
                fallback_period = billing_cycle.end_date.strftime("%B %Y")
                print(f"Fallback - Seleccionando: {fallback_period}")
                self.browser_wrapper.select_dropdown_option(select_date_dropdown_xpath, fallback_period)

            time.sleep(2)

            # 3. Click en confirm button
            confirm_button_xpath = "/html[1]/body[1]/div[2]/form[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[5]/button[1]"
            print("Click en confirm button...")
            self.browser_wrapper.click_element(confirm_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

        except Exception as e:
            print(f"Error configurando fecha: {str(e)}")
            raise

    def _download_individual_reports(self, billing_cycle: BillingCycle, file_map: dict) -> List[FileDownloadInfo]:
        """Descarga reportes individuales con verificacion de nombres exactos."""
        downloaded_files = []

        # Lista de reportes con nombres exactos a verificar
        individual_reports = [
            (
                "wireless_subscriber_charges",
                "Wireless Subscriber Charges",
                "/html[1]/body[1]/div[2]/form[1]/div[1]/div[3]/div[1]/div[1]/div[2]/ul[1]/li[4]/button[1]",
            ),
            (
                "wireless_subscriber_usage",
                "Wireless Subscriber Usage",
                "/html[1]/body[1]/div[2]/form[1]/div[1]/div[3]/div[1]/div[1]/div[2]/ul[1]/li[5]/button[1]",
            ),
            (
                "invoice_detail",
                "Invoice Detail Report",
                "/html[1]/body[1]/div[2]/form[1]/div[1]/div[3]/div[2]/div[1]/div[2]/ul[1]/li[1]/button[1]",
            ),
            (
                "mobility_device",
                "Wireless Data Usage Detail",
                "/html[1]/body[1]/div[2]/form[1]/div[1]/div[3]/div[11]/div[1]/div[2]/ul[1]/li[1]/button[1]",
            ),
            (
                "wireless_data",
                "Wireless Data Usage Detail",
                "/html[1]/body[1]/div[2]/form[1]/div[1]/div[3]/div[21]/div[1]/div[2]/ul[1]/li[1]/button[1]",
            ),
        ]

        for report_slug, expected_name, report_xpath in individual_reports:
            try:
                print(f"Procesando reporte: {expected_name}")

                # Verificar que el boton existe y tiene el nombre correcto
                if not self.browser_wrapper.find_element_by_xpath(report_xpath):
                    print(f"Boton no encontrado para {expected_name}, saltando...")
                    continue

                # Verificar el texto del boton
                button_text = self.browser_wrapper.get_text(report_xpath)
                if expected_name not in button_text:
                    print(
                        f"Nombre incorrecto. Esperado: '{expected_name}', Encontrado: '{button_text}', saltando..."
                    )
                    continue

                print(f"Nombre verificado: {expected_name}")
                corresponding_bcf = file_map.get(report_slug)
                if corresponding_bcf:
                    print(f"Usando BillingCycleFile ID {corresponding_bcf.id} para {report_slug}")

                # Click en el reporte y esperar 30 segundos
                self.browser_wrapper.click_element(report_xpath)
                print("Esperando 30 segundos...")
                time.sleep(30)

                # Click en download button
                download_xpath = "/html[1]/body[1]/div[3]/form[1]/div[2]/div[2]/div[1]/div[1]/button[1]"
                self.browser_wrapper.click_element(download_xpath)
                time.sleep(2)

                # Click en CSV radio label
                csv_xpath = "/html/body/div[7]/div/div/div[2]/form/div[1]/div/div/fieldset/label[2]"
                try:
                    self.browser_wrapper.click_element(csv_xpath)
                    time.sleep(1)
                except:
                    print("No se pudo seleccionar CSV, continuando...")

                # Click en confirm download button y esperar 30 segundos
                confirm_download_xpath = "/html/body/div[7]/div/div/div[3]/button[1]"
                downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                    confirm_download_xpath, timeout=30000, downloads_dir=self.job_downloads_dir
                )

                if downloaded_file_path:
                    actual_filename = os.path.basename(downloaded_file_path)
                    print(f"Descargado: {actual_filename}")

                    file_info = FileDownloadInfo(
                        file_id=corresponding_bcf.id if corresponding_bcf else len(downloaded_files) + 1,
                        file_name=actual_filename,
                        download_url="N/A",
                        file_path=downloaded_file_path,
                        billing_cycle_file=corresponding_bcf,
                    )
                    downloaded_files.append(file_info)

                    if corresponding_bcf:
                        print(f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id}")
                else:
                    print(f"No se pudo descargar {expected_name}")

                print("Esperando 30 segundos...")
                time.sleep(30)

                # Volver al menu anterior
                back_xpath = "/html[1]/body[1]/div[3]/form[1]/div[1]/div[1]/a[1]"
                self.browser_wrapper.click_element(back_xpath)
                time.sleep(2)

            except Exception as e:
                print(f"Error descargando {expected_name}: {str(e)}")
                try:
                    # Intentar volver al menu
                    back_xpath = "/html[1]/body[1]/div[3]/form[1]/div[1]/div[1]/a[1]"
                    self.browser_wrapper.click_element(back_xpath)
                    time.sleep(2)
                except:
                    pass
                continue

        # Descargar el ultimo reporte desde summary reports
        try:
            print("=== DESCARGANDO ULTIMO REPORTE: WIRELESS VOICE USAGE ===")

            # Click en reports header
            reports_header_xpath = (
                "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[3]/a[1]/span[1]"
            )
            self.browser_wrapper.click_element(reports_header_xpath)
            time.sleep(2)

            # Click en summary reports section y esperar 10 segundos
            summary_reports_xpath = (
                "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[3]/ul[1]/li[1]/a[1]/span[1]"
            )
            self.browser_wrapper.click_element(summary_reports_xpath)
            print("Esperando 10 segundos...")
            time.sleep(10)

            # Wireless voice usage report y esperar 1 minuto
            voice_report_xpath = (
                "/html[1]/body[1]/form[1]/div[2]/div[3]/div[3]/div[18]/div[1]/div[2]/ul[1]/li[1]/button[1]"
            )

            # Verificar nombre
            if self.browser_wrapper.find_element_by_xpath(voice_report_xpath):
                button_text = self.browser_wrapper.get_text(voice_report_xpath)
                if "Wireless Voice Usage per account and services" in button_text or "Wireless Voice" in button_text:
                    print("Wireless Voice Usage encontrado")

                    self.browser_wrapper.click_element(voice_report_xpath)
                    print("Esperando 1 minuto...")
                    time.sleep(60)

                    # Download button
                    voice_download_xpath = "/html/body/div[2]/form/div[2]/div[2]/div/div/button[3]"
                    self.browser_wrapper.click_element(voice_download_xpath)
                    time.sleep(2)

                    # CSV radio label
                    voice_csv_xpath = "/html/body/div[8]/div/div/div[2]/form/div[1]/div/div/fieldset/label[2]"
                    try:
                        self.browser_wrapper.click_element(voice_csv_xpath)
                        time.sleep(1)
                    except:
                        pass

                    # Confirm download button y esperar 30 segundos
                    voice_confirm_xpath = "/html/body/div[8]/div/div/div[3]/button[1]"
                    downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                        voice_confirm_xpath, timeout=30000, downloads_dir=self.job_downloads_dir
                    )

                    if downloaded_file_path:
                        corresponding_bcf = file_map.get("wireless_voice")
                        actual_filename = os.path.basename(downloaded_file_path)
                        print(f"Wireless Voice descargado: {actual_filename}")

                        file_info = FileDownloadInfo(
                            file_id=corresponding_bcf.id if corresponding_bcf else len(downloaded_files) + 1,
                            file_name=actual_filename,
                            download_url="N/A",
                            file_path=downloaded_file_path,
                            billing_cycle_file=corresponding_bcf,
                        )
                        downloaded_files.append(file_info)

                        if corresponding_bcf:
                            print(
                                f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id}"
                            )

                    print("Esperando 30 segundos...")
                    time.sleep(30)

                    # Back to previous menu
                    voice_back_xpath = "/html/body/div[2]/form/div[1]/div[1]/a"
                    self.browser_wrapper.click_element(voice_back_xpath)
                    time.sleep(2)
                else:
                    print(f"Nombre incorrecto para Wireless Voice. Encontrado: {button_text}")
            else:
                print("Wireless Voice Usage report no encontrado")

        except Exception as e:
            print(f"Error descargando Wireless Voice Usage: {str(e)}")

        return downloaded_files

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Telus usando My Telus."""
        try:
            print("Reseteando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("Reset completado")
        except Exception as e:
            print(f"Error en reset: {str(e)}")