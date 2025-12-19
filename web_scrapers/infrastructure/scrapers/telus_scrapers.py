import os
import time
from datetime import datetime
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    DailyUsageScraperStrategy,
    FileDownloadInfo,
    MonthlyReportsScraperStrategy,
    PDFInvoiceScraperStrategy,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class TelusMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para Telus siguiendo el patrón de Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la sección de reportes mensuales de Telus."""
        try:
            print("📋 Navegando a reportes mensuales de Telus...")

            # 1. Navegar a My Telus
            print("🏠 Navegando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            print("✅ Navegación inicial completada - listo para descarga de archivos")
            return {"section": "monthly_reports", "ready_for_download": True}

        except Exception as e:
            print(f"❌ Error navegando a reportes mensuales: {str(e)}")
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
                    print(f"📋 Mapeando BillingCycleFile ID {bcf.id} -> Slug: '{bcf.carrier_report.slug}'")

        try:
            # === PARTE 1: DESCARGAR ZIP DESDE BILLS SECTION ===
            print("📦 === PARTE 1: DESCARGANDO ZIP DESDE BILLS SECTION ===")

            # 1. Click en bill options button
            bill_options_xpath = (
                "/html/body/div[5]/div/div/div/div[1]/div/div[3]/div/div/div/div/div/div/div[3]/div/div/div/div"
            )
            print("💰 Click en bill options...")
            self.browser_wrapper.click_element(bill_options_xpath)
            time.sleep(3)

            # 2. Click en download bills section
            download_bills_xpath = "/html[1]/body[1]/div[5]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[1]/a[2]"
            print("📊 Click en download bills section...")
            self.browser_wrapper.click_element(download_bills_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # 3. Buscar y click en el mes correcto basado en end_date
            target_month = billing_cycle.end_date.strftime("%B")
            target_year = billing_cycle.end_date.year

            print(f"🔍 Buscando mes: {target_month} {target_year}")
            month_clicked = self._find_and_click_target_month(target_month, target_year)

            if month_clicked:
                # 4. Descargar ZIP y procesar archivos extraídos
                zip_files = self._download_and_process_zip(billing_cycle, billing_cycle_file_map)
                downloaded_files.extend(zip_files)
                print(f"✅ Parte 1 completada: {len(zip_files)} archivos del ZIP")
            else:
                print("⚠️ No se pudo encontrar el mes objetivo, continuando sin ZIP")

            # === PARTE 2: DESCARGAR ARCHIVOS INDIVIDUALES DESDE REPORTS SECTION ===
            print("📄 === PARTE 2: DESCARGANDO ARCHIVOS INDIVIDUALES ===")

            # 1. Navegar a billing header
            billing_header_xpath = "/html[1]/body[1]/div[1]/div[1]/ul[1]/li[2]/a[1]/span[1]"
            print("💳 Click en billing header...")
            self.browser_wrapper.click_element(billing_header_xpath)
            self.browser_wrapper.wait_for_page_load()
            print("⏳ Esperando 1 minuto...")
            time.sleep(60)

            # 2. Click en reports header
            reports_header_xpath = "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[3]/a[1]"
            print("📊 Click en reports header...")
            self.browser_wrapper.click_element(reports_header_xpath)
            time.sleep(2)

            # 3. Click en detail reports
            detail_reports_xpath = (
                "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[3]/ul[1]/li[2]/a[1]/span[1]"
            )
            print("📋 Click en detail reports...")
            self.browser_wrapper.click_element(detail_reports_xpath)
            self.browser_wrapper.wait_for_page_load()
            print("⏳ Esperando 1 minuto...")
            time.sleep(60)

            # 4. Configurar fecha
            self._configure_date_selection(billing_cycle)

            # 5. Descargar reportes individuales
            individual_files = self._download_individual_reports(billing_cycle, billing_cycle_file_map)
            downloaded_files.extend(individual_files)
            print(f"✅ Parte 2 completada: {len(individual_files)} archivos individuales")

            # 6. Reset a pantalla principal
            self._reset_to_main_screen()

            print(f"✅ DESCARGA TOTAL COMPLETADA: {len(downloaded_files)} archivos")
            return downloaded_files

        except Exception as e:
            print(f"❌ Error en descarga de archivos: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _find_and_click_target_month(self, target_month: str, target_year: int) -> bool:
        """Busca y hace click en el mes objetivo dentro de la estructura de años."""
        try:
            # Buscar el contenedor de bills section
            bills_container_xpath = "/html/body/div[1]/main/div/div[2]/div/div[2]"

            # Buscar el año objetivo primero
            year_xpath = f"//h2[contains(text(), '{target_year}')]"
            if not self.browser_wrapper.find_element_by_xpath(year_xpath):
                print(f"❌ No se encontró el año {target_year}")
                return False

            print(f"✅ Encontrado año {target_year}")

            # Buscar el enlace del mes objetivo
            month_link_xpath = f"//div[contains(@class, 'css-146c3p1') and contains(text(), '{target_month}')]"

            if self.browser_wrapper.find_element_by_xpath(month_link_xpath):
                print(f"✅ Encontrado mes {target_month}, haciendo click...")
                # Hacer click en el div parent que contiene el enlace
                parent_link_xpath = f"//div[contains(@class, 'css-146c3p1') and contains(text(), '{target_month}')]/parent::div/parent::div"
                self.browser_wrapper.click_element(parent_link_xpath)
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)
                return True
            else:
                print(f"❌ No se encontró el mes {target_month} en el año {target_year}")
                return False

        except Exception as e:
            print(f"❌ Error buscando mes objetivo: {str(e)}")
            return False

    def _download_and_process_zip(self, billing_cycle: BillingCycle, file_map: dict) -> List[FileDownloadInfo]:
        """Descarga y procesa el ZIP con los archivos del mes."""
        downloaded_files = []

        try:
            # El click en el mes debería llevarnos a una página con un enlace de descarga ZIP
            # Intentar encontrar el enlace de descarga (puede variar según la estructura)

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
                print("⚠️ No se pudo descargar ZIP")
                return downloaded_files

            print(f"📦 ZIP descargado: {os.path.basename(zip_file_path)}")

            # Extraer archivos del ZIP
            extracted_files = self._extract_zip_files(zip_file_path)
            if not extracted_files:
                print("❌ No se pudieron extraer archivos del ZIP")
                return downloaded_files

            print(f"📁 Extraídos {len(extracted_files)} archivos del ZIP")

            # Procesar archivos extraídos y mapearlos
            for i, file_path in enumerate(extracted_files):
                original_filename = os.path.basename(file_path)
                print(f"📄 Procesando archivo: {original_filename}")

                # Buscar el BillingCycleFile correspondiente
                corresponding_bcf = self._find_matching_billing_cycle_file(original_filename, file_map)

                if corresponding_bcf:
                    print(f"✅ Mapeando {original_filename} -> BillingCycleFile ID {corresponding_bcf.id}")
                else:
                    print(f"⚠️ No se encontró mapeo para {original_filename}")

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
            print(f"❌ Error procesando ZIP: {str(e)}")
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
        """Configura la selección de fecha para los reportes individuales."""
        try:
            # 1. Click en date selection
            date_selection_xpath = (
                "/html[1]/body[1]/div[2]/form[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/button[1]"
            )
            print("📅 Click en date selection...")
            self.browser_wrapper.click_element(date_selection_xpath)
            time.sleep(2)

            # 2. Configurar dropdown de fecha
            target_period = billing_cycle.end_date.strftime("%B %Y") + " statements"
            select_date_dropdown_xpath = "/html[1]/body[1]/div[2]/form[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/select[1]"
            print(f"📅 Seleccionando período: {target_period}")

            try:
                self.browser_wrapper.select_dropdown_option(select_date_dropdown_xpath, target_period)
            except:
                # Fallback: buscar solo por mes y año sin "statements"
                fallback_period = billing_cycle.end_date.strftime("%B %Y")
                print(f"📅 Fallback - Seleccionando: {fallback_period}")
                self.browser_wrapper.select_dropdown_option(select_date_dropdown_xpath, fallback_period)

            time.sleep(2)

            # 3. Click en confirm button
            confirm_button_xpath = "/html[1]/body[1]/div[2]/form[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[5]/button[1]"
            print("✅ Click en confirm button...")
            self.browser_wrapper.click_element(confirm_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

        except Exception as e:
            print(f"❌ Error configurando fecha: {str(e)}")
            raise

    def _download_individual_reports(self, billing_cycle: BillingCycle, file_map: dict) -> List[FileDownloadInfo]:
        """Descarga reportes individuales con verificación de nombres exactos."""
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
                print(f"📄 Procesando reporte: {expected_name}")

                # Verificar que el botón existe y tiene el nombre correcto
                if not self.browser_wrapper.find_element_by_xpath(report_xpath):
                    print(f"⚠️ Botón no encontrado para {expected_name}, saltando...")
                    continue

                # Verificar el texto del botón
                button_text = self.browser_wrapper.get_text(report_xpath)
                if expected_name not in button_text:
                    print(
                        f"⚠️ Nombre incorrecto. Esperado: '{expected_name}', Encontrado: '{button_text}', saltando..."
                    )
                    continue

                print(f"✅ Nombre verificado: {expected_name}")
                corresponding_bcf = file_map.get(report_slug)
                if corresponding_bcf:
                    print(f"📋 Usando BillingCycleFile ID {corresponding_bcf.id} para {report_slug}")

                # Click en el reporte y esperar 30 segundos
                self.browser_wrapper.click_element(report_xpath)
                print("⏳ Esperando 30 segundos...")
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
                    print("⚠️ No se pudo seleccionar CSV, continuando...")

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
                        print(f"✅ MAPEO CONFIRMADO: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id}")
                else:
                    print(f"⚠️ No se pudo descargar {expected_name}")

                print("⏳ Esperando 30 segundos...")
                time.sleep(30)

                # Volver al menú anterior
                back_xpath = "/html[1]/body[1]/div[3]/form[1]/div[1]/div[1]/a[1]"
                self.browser_wrapper.click_element(back_xpath)
                time.sleep(2)

            except Exception as e:
                print(f"❌ Error descargando {expected_name}: {str(e)}")
                try:
                    # Intentar volver al menú
                    back_xpath = "/html[1]/body[1]/div[3]/form[1]/div[1]/div[1]/a[1]"
                    self.browser_wrapper.click_element(back_xpath)
                    time.sleep(2)
                except:
                    pass
                continue

        # Descargar el último reporte desde summary reports
        try:
            print("📄 === DESCARGANDO ÚLTIMO REPORTE: WIRELESS VOICE USAGE ===")

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
            print("⏳ Esperando 10 segundos...")
            time.sleep(10)

            # Wireless voice usage report y esperar 1 minuto
            voice_report_xpath = (
                "/html[1]/body[1]/form[1]/div[2]/div[3]/div[3]/div[18]/div[1]/div[2]/ul[1]/li[1]/button[1]"
            )

            # Verificar nombre
            if self.browser_wrapper.find_element_by_xpath(voice_report_xpath):
                button_text = self.browser_wrapper.get_text(voice_report_xpath)
                if "Wireless Voice Usage per account and services" in button_text or "Wireless Voice" in button_text:
                    print("✅ Wireless Voice Usage encontrado")

                    self.browser_wrapper.click_element(voice_report_xpath)
                    print("⏳ Esperando 1 minuto...")
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
                                f"✅ MAPEO CONFIRMADO: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id}"
                            )

                    print("⏳ Esperando 30 segundos...")
                    time.sleep(30)

                    # Back to previous menu
                    voice_back_xpath = "/html/body/div[2]/form/div[1]/div[1]/a"
                    self.browser_wrapper.click_element(voice_back_xpath)
                    time.sleep(2)
                else:
                    print(f"⚠️ Nombre incorrecto para Wireless Voice. Encontrado: {button_text}")
            else:
                print("⚠️ Wireless Voice Usage report no encontrado")

        except Exception as e:
            print(f"❌ Error descargando Wireless Voice Usage: {str(e)}")

        return downloaded_files

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Telus usando My Telus."""
        try:
            print("🔄 Reseteando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("✅ Reset completado")
        except Exception as e:
            print(f"❌ Error en reset: {str(e)}")


class TelusDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para Telus siguiendo el patrón de Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la sección de uso diario en Telus IQ."""
        try:
            print("📊 Navegando a Telus IQ para uso diario...")

            # 1. Verificar que estamos en My Telus
            current_url = self.browser_wrapper.get_current_url()
            if "my-telus" not in current_url:
                print("🏠 Navegando a My Telus...")
                self.browser_wrapper.goto("https://www.telus.com/my-telus")
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)

            # 2. Click en Telus IQ button y esperar 30 segundos
            telus_iq_xpath = "/html/body/div[5]/div/div/div/div[1]/div/div[3]/div/div/div/div/div/div/div[3]/div/div/a"
            print("🔍 Click en Telus IQ button...")
            self.browser_wrapper.click_element(telus_iq_xpath)
            print("⏳ Esperando 30 segundos...")
            time.sleep(30)

            # 3. Verificar si aparece el botón "don't show again" y hacer click si existe
            dont_show_again_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div/div[2]/div[2]/div[1]/div/div/div[3]/div/div[2]/p/div/a"
            try:
                if self.browser_wrapper.find_element_by_xpath(dont_show_again_xpath, timeout=5000):
                    print("ℹ️ Click en don't show again button...")
                    self.browser_wrapper.click_element(dont_show_again_xpath)
                    time.sleep(2)
                else:
                    print("ℹ️ Don't show again button no apareció, continuando...")
            except:
                print("ℹ️ Don't show again button no encontrado, continuando...")

            # 4. Click en manage tab
            manage_tab_xpath = "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/ul[1]/li[2]/a[1]/span[1]/span[1]"
            print("⚙️ Click en manage tab...")
            self.browser_wrapper.click_element(manage_tab_xpath)
            time.sleep(3)

            # 5. Click en usage view option y esperar 30 segundos
            usage_view_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div/div[1]/div/div[2]/div/div/div/div/div[2]/div[1]/div[3]/div/a/span/span[1]/div/span"
            print("📊 Click en usage view option...")
            self.browser_wrapper.click_element(usage_view_xpath)
            print("⏳ Esperando 30 segundos...")
            time.sleep(30)

            print("✅ Navegación a Telus IQ completada")
            return {"section": "daily_usage", "ready_for_export": True}

        except Exception as e:
            print(f"❌ Error navegando a Telus IQ: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de Telus IQ."""
        downloaded_files = []

        # Obtener el BillingCycleDailyUsageFile del billing_cycle
        daily_usage_file = billing_cycle.daily_usage_files[0] if billing_cycle.daily_usage_files else None
        if daily_usage_file:
            print(f"📋 Mapeando archivo Daily Usage -> BillingCycleDailyUsageFile ID {daily_usage_file.id}")

        try:
            print("📤 Iniciando proceso de exportación...")

            # 1. Click en export view button
            export_view_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div[3]/div[1]/div[11]/div[2]/div/div[2]/div/div[2]/div/a"
            print("📤 Click en export view button...")
            self.browser_wrapper.click_element(export_view_xpath)
            time.sleep(3)

            # 2. Generar nombre del reporte con formato daily_usage_yyyy-mm-dd
            current_date = datetime.now()
            report_name = f"daily_usage_{current_date.strftime('%Y-%m-%d')}"
            print(f"📝 Nombre del reporte: {report_name}")

            # 3. Escribir en report view modal input
            report_input_xpath = "/html[1]/body[1]/div[1]/div[1]/div[1]/div[2]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/input[1]"
            self.browser_wrapper.clear_and_type(report_input_xpath, report_name)
            time.sleep(2)

            # 4. Click en continue button y esperar 2 minutos
            continue_button_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div[2]/div/div[2]/a[2]"
            print("➡️ Click en continue button...")
            self.browser_wrapper.click_element(continue_button_xpath)
            print("⏳ Esperando 2 minutos...")
            time.sleep(120)

            # 5. Verificar results table y monitorear descarga
            download_info = self._monitor_results_table_and_download(report_name, daily_usage_file)

            if download_info:
                downloaded_files.append(download_info)
                print(f"✅ Reporte descargado: {download_info.file_name}")
            else:
                print("❌ No se pudo descargar el reporte")

            # 6. Reset a pantalla principal
            self._reset_to_main_screen()

            return downloaded_files

        except Exception as e:
            print(f"❌ Error en descarga de uso diario: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _monitor_results_table_and_download(self, report_name: str, daily_usage_file) -> Optional[FileDownloadInfo]:
        """Monitorea la tabla de resultados y descarga cuando esté listo."""
        max_attempts = 10  # Máximo 10 reintentos
        attempt = 0

        while attempt < max_attempts:
            try:
                attempt += 1
                print(f"🔍 Intento {attempt}/{max_attempts} - Verificando results table...")

                # Verificar si existe la results table
                results_table_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div[2]/div/div[3]"

                if not self.browser_wrapper.find_element_by_xpath(results_table_xpath, timeout=10000):
                    print("⚠️ Results table no apareció, refrescando página...")
                    self.browser_wrapper.refresh()
                    print("⏳ Esperando 1 minuto después del refresh...")
                    time.sleep(60)
                    continue

                print("✅ Results table encontrada")

                # Buscar nuestro reporte en la primera fila por nombre
                first_row_name_xpath = "//div[@class='new__dynamic__table__column'][2]//div[@class='new-dynamic-table__table__cell'][1]//span"

                if not self.browser_wrapper.find_element_by_xpath(first_row_name_xpath):
                    print("⚠️ Primera fila no encontrada, esperando...")
                    time.sleep(60)
                    continue

                name_text = self.browser_wrapper.get_text(first_row_name_xpath)
                print(f"📝 Nombre en primera fila: {name_text}")

                if report_name not in name_text:
                    print(f"⚠️ Reporte '{report_name}' no encontrado en primera fila, esperando...")
                    time.sleep(60)
                    continue

                print(f"✅ Reporte '{report_name}' encontrado en primera fila")

                # Verificar el estado en la columna Status (columna 3)
                first_row_status_xpath = "//div[@class='new__dynamic__table__column'][3]//div[@class='new-dynamic-table__table__cell'][1]//span"

                if not self.browser_wrapper.find_element_by_xpath(first_row_status_xpath):
                    print("⚠️ Estado no encontrado, esperando...")
                    time.sleep(60)
                    continue

                status_element = self.browser_wrapper.get_text(first_row_status_xpath)
                print(f"📊 Estado del reporte: {status_element}")

                # Verificar si contiene enlace de descarga
                download_link_xpath = "/html/body/div[1]/html/body/div/div/div/div[2]/div[2]/div/div[3]/div[2]/div[1]/div[3]/div[1]//a[@class='new-dynamic-table__table__cell__download-anchor']"

                if self.browser_wrapper.find_element_by_xpath(download_link_xpath):
                    link_text = self.browser_wrapper.get_text(download_link_xpath)
                    print(f"🔗 Enlace encontrado: {link_text}")

                    if "Download" in link_text:
                        print("✅ Reporte listo para descarga!")

                        # Descargar archivo
                        downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                            download_link_xpath, timeout=30000, downloads_dir=self.job_downloads_dir
                        )

                        if downloaded_file_path:
                            actual_filename = os.path.basename(downloaded_file_path)
                            file_size = (
                                os.path.getsize(downloaded_file_path)
                                if os.path.exists(downloaded_file_path)
                                else 1024000
                            )

                            print(f"✅ Archivo descargado: {actual_filename}")

                            file_info = FileDownloadInfo(
                                file_id=daily_usage_file.id if daily_usage_file else 1,
                                file_name=actual_filename,
                                download_url="N/A",
                                file_path=downloaded_file_path,
                                daily_usage_file=daily_usage_file,
                            )

                            if daily_usage_file:
                                print(
                                    f"✅ MAPEO CONFIRMADO: {actual_filename} -> BillingCycleDailyUsageFile ID {daily_usage_file.id}"
                                )

                            return file_info
                        else:
                            print("❌ Error en descarga")
                            return None
                    elif "In Queue" in link_text:
                        print("⏳ Reporte en cola, esperando 1 minuto más...")
                        time.sleep(60)
                        continue
                    else:
                        print(f"⚠️ Estado desconocido en enlace: {link_text}")
                        time.sleep(60)
                        continue
                else:
                    print("⚠️ Enlace de descarga no encontrado, esperando...")
                    time.sleep(60)
                    continue

            except Exception as e:
                print(f"❌ Error en intento {attempt}: {str(e)}")
                time.sleep(60)
                continue

        print("⏰ Máximo de intentos alcanzado")
        return None

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Telus."""
        try:
            print("🔄 Reseteando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("✅ Reset completado")
        except Exception as e:
            print(f"❌ Error en reset: {str(e)}")


class TelusPDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para Telus siguiendo el patrón de Bell."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la sección de facturas PDF de Telus."""
        try:
            print("📄 Navegando a facturas PDF de Telus...")

            # 1. Verificar que estamos en My Telus
            current_url = self.browser_wrapper.get_current_url()
            if "my-telus" not in current_url:
                print("🏠 Navegando a My Telus...")
                self.browser_wrapper.goto("https://www.telus.com/my-telus")
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)

            # 2. Click en bill options button
            bill_options_xpath = (
                "/html/body/div[5]/div/div/div/div[1]/div/div[3]/div/div/div/div/div/div/div[3]/div/div/div/div"
            )
            print("💰 Click en bill options button...")
            self.browser_wrapper.click_element(bill_options_xpath)
            time.sleep(3)

            # 3. Click en view bill option
            view_bill_xpath = "/html[1]/body[1]/div[5]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[1]/a[1]"
            print("📋 Click en view bill option...")
            self.browser_wrapper.click_element(view_bill_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # 4. Click en statements header y esperar 1 minuto
            statements_header_xpath = "/html/body/div[1]/div/div/div/div/div[3]/ul[1]/li[2]/a"
            print("📊 Click en statements header...")
            self.browser_wrapper.click_element(statements_header_xpath)
            print("⏳ Esperando 1 minuto...")
            time.sleep(60)

            print("✅ Navegación a facturas PDF completada")
            return {"section": "pdf_invoices", "ready_for_download": True}

        except Exception as e:
            print(f"❌ Error navegando a facturas PDF: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de Telus."""
        downloaded_files = []

        # Obtener el BillingCyclePDFFile del billing_cycle
        pdf_file = billing_cycle.pdf_files[0] if billing_cycle.pdf_files else None
        if pdf_file:
            print(f"📋 Mapeando archivo PDF -> BillingCyclePDFFile ID {pdf_file.id}")

        try:
            # 1. Click en download pdf
            download_pdf_xpath = "/html/body/div[2]/div[3]/div[2]/div/div/div/div[2]/div/table/tbody/tr/td[11]/button"
            print("📥 Click en download pdf...")
            self.browser_wrapper.click_element(download_pdf_xpath)
            time.sleep(3)

            # 2. Click en drop list y esperar 30 segundos
            drop_list_xpath = "/html/body/div[2]/div[3]/div[3]/div/div/div[2]/div[1]/div/div/div/div/div[1]"
            print("📝 Click en drop list...")
            self.browser_wrapper.click_element(drop_list_xpath)
            print("⏳ Esperando 30 segundos...")
            time.sleep(30)

            # 3. Buscar y hacer click en la fecha más cercana al end_date del billing cycle
            target_month = billing_cycle.end_date.month
            target_year = billing_cycle.end_date.year

            print(f"🔍 Buscando PDF para {target_year}/{target_month:02d}")

            # Buscar en la lista desplegada
            list_xpath = "/html/body/div[2]/div[3]/div[3]/div/div/div[2]/div[1]/div/div/div/div/div[2]/ul"

            if self.browser_wrapper.find_element_by_xpath(list_xpath):
                print("✅ Lista de PDFs encontrada")

                # Buscar el botón con la fecha más cercana
                pdf_button_xpath = self._find_closest_pdf_in_list(target_year, target_month)

                if pdf_button_xpath:
                    print(f"✅ PDF encontrado, descargando...")

                    # Hacer click para descargar (se dispara automáticamente)
                    downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                        pdf_button_xpath, timeout=30000, downloads_dir=self.job_downloads_dir
                    )

                    if downloaded_file_path:
                        actual_filename = os.path.basename(downloaded_file_path)
                        file_size = (
                            os.path.getsize(downloaded_file_path) if os.path.exists(downloaded_file_path) else 2048000
                        )

                        print(f"✅ PDF descargado: {actual_filename}")

                        file_info = FileDownloadInfo(
                            file_id=pdf_file.id if pdf_file else 1,
                            file_name=actual_filename,
                            download_url="N/A",
                            file_path=downloaded_file_path,
                            pdf_file=pdf_file,
                        )
                        downloaded_files.append(file_info)

                        if pdf_file:
                            print(f"✅ MAPEO CONFIRMADO: {actual_filename} -> BillingCyclePDFFile ID {pdf_file.id}")
                    else:
                        print("⚠️ Error con expect_download, usando método tradicional...")
                        self.browser_wrapper.click_element(pdf_button_xpath)
                        time.sleep(5)

                        estimated_filename = f"telus_invoice_{billing_cycle.end_date.strftime('%Y_%m_%d')}.pdf"
                        file_info = FileDownloadInfo(
                            file_id=pdf_file.id if pdf_file else 1,
                            file_name=estimated_filename,
                            download_url="N/A",
                            file_path=f"{self.job_downloads_dir}/{estimated_filename}",
                            pdf_file=pdf_file,
                        )
                        downloaded_files.append(file_info)
                        print(f"✅ PDF descargado (método tradicional): {estimated_filename}")
                else:
                    print("❌ No se encontró PDF cercano para el período")
            else:
                print("❌ Lista de PDFs no encontrada")

            # 4. Reset a pantalla principal
            self._reset_to_main_screen()

            print(f"✅ Descarga PDF completada: {len(downloaded_files)} archivo(s)")
            return downloaded_files

        except Exception as e:
            print(f"❌ Error en descarga de PDF: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _find_closest_pdf_in_list(self, target_year: int, target_month: int) -> Optional[str]:
        """Encuentra el PDF más cercano en la lista desplegada."""
        try:
            print(f"🔍 Buscando PDF para {target_year}/{target_month:02d}")

            # 1. Buscar fecha exacta (ignorando el día)
            exact_pattern = f"{target_year}/{target_month:02d}"
            exact_xpath = f"//button[@class='list-group-item bdf-doc-item'][contains(text(), '{exact_pattern}')]"

            if self.browser_wrapper.find_element_by_xpath(exact_xpath):
                button_text = self.browser_wrapper.get_text(exact_xpath)
                print(f"✅ Encontrado PDF mes exacto: {button_text}")
                return exact_xpath

            # 2. Buscar mes anterior
            if target_month > 1:
                prev_month = target_month - 1
                prev_year = target_year
            else:
                prev_month = 12
                prev_year = target_year - 1

            prev_pattern = f"{prev_year}/{prev_month:02d}"
            prev_xpath = f"//button[@class='list-group-item bdf-doc-item'][contains(text(), '{prev_pattern}')]"

            if self.browser_wrapper.find_element_by_xpath(prev_xpath):
                button_text = self.browser_wrapper.get_text(prev_xpath)
                print(f"✅ Encontrado PDF mes anterior: {button_text}")
                return prev_xpath

            # 3. Buscar cualquier PDF del año actual (ignorando mes y día)
            year_xpath = f"//button[@class='list-group-item bdf-doc-item'][contains(text(), '{target_year}/')]"

            if self.browser_wrapper.find_element_by_xpath(year_xpath):
                button_text = self.browser_wrapper.get_text(year_xpath)
                print(f"✅ Encontrado PDF del año {target_year}: {button_text}")
                return year_xpath

            # 4. Tomar el primer PDF disponible como último recurso
            first_xpath = "//button[@class='list-group-item bdf-doc-item'][1]"

            if self.browser_wrapper.find_element_by_xpath(first_xpath):
                button_text = self.browser_wrapper.get_text(first_xpath)
                print(f"✅ Tomando primer PDF disponible: {button_text}")
                return first_xpath

            print("❌ No se encontraron PDFs en la lista")
            return None

        except Exception as e:
            print(f"❌ Error buscando PDF en lista: {str(e)}")
            return None

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Telus."""
        try:
            print("🔄 Reseteando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("✅ Reset completado")
        except Exception as e:
            print(f"❌ Error en reset: {str(e)}")
