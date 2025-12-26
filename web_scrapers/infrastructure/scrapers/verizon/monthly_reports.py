import calendar
import os
import time
from datetime import datetime
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    FileDownloadInfo,
    MonthlyReportsScraperStrategy,
)
from web_scrapers.domain.enums import VerizonFileSlug

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class VerizonMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para Verizon: 2 archivos del ZIP + 3 reportes individuales."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de reportes mensuales de Verizon."""
        try:
            print("Navegando a reportes mensuales de Verizon...")

            # 1. Click en report header
            report_header_xpath = "/html[1]/body[1]/app-root[1]/app-secure-layout[1]/app-header[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/header[1]/div[1]/div[1]/div[2]/nav[1]/ul[1]/li[4]/a[1]"
            print("Haciendo clic en header de reportes...")
            self.browser_wrapper.click_element(report_header_xpath)
            time.sleep(2)

            # 2. Click en raw data download section
            raw_data_section_xpath = "/html/body/app-root/app-secure-layout/app-header/div/div[1]/div/div/div[1]/div[2]/header/div/div/div[2]/nav/ul/li[4]/div/div/div[1]/div/ul/li[4]/a"
            print("Haciendo clic en Raw Data Download section...")
            self.browser_wrapper.click_element(raw_data_section_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            print("Navegacion completada - listo para descarga de archivos")
            return {"section": "monthly_reports", "ready_for_download": True}

        except Exception as e:
            print(f"Error navegando a reportes mensuales: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los 5 archivos de reportes mensuales de Verizon: 2 del ZIP + 3 individuales."""
        downloaded_files = []

        # Mapear BillingCycleFiles por slug si estan disponibles
        billing_cycle_file_map = {}
        if billing_cycle.billing_cycle_files:
            for bcf in billing_cycle.billing_cycle_files:
                if bcf.carrier_report and bcf.carrier_report.slug:
                    billing_cycle_file_map[bcf.carrier_report.slug] = bcf
                    print(f"Mapeando BillingCycleFile ID {bcf.id} -> Slug: '{bcf.carrier_report.slug}'")

        try:
            print("Iniciando descarga de 5 archivos mensuales de Verizon...")

            # === PARTE 1: RAW DATA DOWNLOAD (ZIP con 2 archivos relevantes) ===
            print("=== PARTE 1: DESCARGANDO ZIP DESDE RAW DATA DOWNLOAD (2 archivos) ===")
            zip_files = self._download_raw_data_zip(billing_cycle, billing_cycle_file_map)
            downloaded_files.extend(zip_files)
            print(f"Parte 1 completada: {len(zip_files)} archivos del ZIP")

            # === PARTE 2: DEVICE PAYMENT REPORT ===
            print("=== PARTE 2: DESCARGANDO DEVICE PAYMENT REPORT ===")
            device_file = self._download_device_payment_report(billing_cycle, billing_cycle_file_map)
            if device_file:
                downloaded_files.append(device_file)
                print("Device Payment Report descargado")

            # === PARTE 3: ACTIVATION & DEACTIVATION REPORT ===
            print("=== PARTE 3: DESCARGANDO ACTIVATION & DEACTIVATION REPORT ===")
            activation_file = self._download_activation_deactivation_report(billing_cycle, billing_cycle_file_map)
            if activation_file:
                downloaded_files.append(activation_file)
                print("Activation & Deactivation Report descargado")

            # === PARTE 4: SUSPENDED WIRELESS NUMBERS REPORT ===
            print("=== PARTE 4: DESCARGANDO SUSPENDED WIRELESS NUMBERS REPORT ===")
            suspended_file = self._download_suspended_lines_report(billing_cycle, billing_cycle_file_map)
            if suspended_file:
                downloaded_files.append(suspended_file)
                print("Suspended Lines Report descargado")

            # Reset a pantalla principal
            self._reset_to_main_screen()

            print(f"DESCARGA TOTAL COMPLETADA: {len(downloaded_files)} archivos (2 ZIP + 3 individuales)")
            return downloaded_files

        except Exception as e:
            print(f"Error en descarga de archivos: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _download_raw_data_zip(self, billing_cycle: BillingCycle, file_map: dict) -> List[FileDownloadInfo]:
        """Descarga el ZIP del Raw Data report y extrae solo los 2 archivos relevantes."""
        downloaded_files = []

        try:
            print("Descargando Raw Data ZIP...")

            # 1. Click en dropdown
            dropdown_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[4]/div[3]/div/app-reports-list/app-raw-data-download/app-form-modal/div/div[2]/div[2]/div[2]/div/app-dropdown"
            self.browser_wrapper.click_element(dropdown_xpath)
            time.sleep(1)

            # 2. Click dentro del div para desplegar la lista
            dropdown_trigger_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[4]/div[3]/div/app-reports-list/app-raw-data-download/app-form-modal/div/div[2]/div[2]/div[2]/div/app-dropdown/div/div/div"
            self.browser_wrapper.click_element(dropdown_trigger_xpath)
            time.sleep(2)

            # 3. Seleccionar la fecha mas cercana basada en end_date del billing cycle
            target_month_year = self._find_closest_month_option(billing_cycle)
            if target_month_year:
                print(f"Seleccionando mes: {target_month_year}")
                self._select_month_option(target_month_year)
            else:
                print("No se pudo encontrar fecha apropiada")
                return downloaded_files

            # 4. Click en download button y esperar 1 minuto
            download_button_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[4]/div[3]/div/app-reports-list/app-raw-data-download/app-form-modal/div/div[2]/div[2]/div[5]/button"
            print("Haciendo clic en Download y esperando 1 minuto...")
            zip_file_path = self.browser_wrapper.expect_download_and_click(
                download_button_xpath, timeout=120000, downloads_dir=self.job_downloads_dir
            )
            time.sleep(60)  # Esperar 1 minuto adicional

            if zip_file_path:
                print(f"ZIP descargado: {os.path.basename(zip_file_path)}")

                # Extraer archivos del ZIP
                extracted_files = self._extract_zip_files(zip_file_path)
                if not extracted_files:
                    print("No se pudieron extraer archivos del ZIP")
                    return downloaded_files

                print(f"Extraidos {len(extracted_files)} archivos del ZIP")

                # Procesar solo los archivos relevantes del ZIP
                for file_path in extracted_files:
                    original_filename = os.path.basename(file_path)
                    print(f"Procesando archivo: {original_filename}")

                    # Buscar el BillingCycleFile correspondiente para archivos relevantes del ZIP
                    corresponding_bcf = self._find_matching_zip_file(original_filename, file_map)

                    if corresponding_bcf:
                        print(
                            f"Archivo relevante - Mapeando {original_filename} -> BillingCycleFile ID {corresponding_bcf.id}"
                        )

                        file_info = FileDownloadInfo(
                            file_id=corresponding_bcf.id,
                            file_name=original_filename,
                            download_url="N/A",
                            file_path=file_path,
                            billing_cycle_file=corresponding_bcf,
                        )
                        downloaded_files.append(file_info)
                    else:
                        print(f"Archivo ignorado (no relevante): {original_filename}")

                print(f"Procesados {len(downloaded_files)} archivos relevantes del ZIP")
                return downloaded_files
            else:
                print("No se pudo descargar el ZIP")
                return downloaded_files

        except Exception as e:
            print(f"Error descargando Raw Data ZIP: {str(e)}")
            return downloaded_files

    def _find_matching_zip_file(self, filename: str, file_map: dict) -> Optional[Any]:
        """Encuentra el BillingCycleFile que corresponde solo a los 2 archivos relevantes del ZIP."""
        filename_lower = filename.lower()

        # Solo mapear los 2 archivos que nos interesan del ZIP
        zip_pattern_to_slug = {
            "account & wireless summary": VerizonFileSlug.ACCOUNT_AND_WIRELESS.value,
            "accountsummary": VerizonFileSlug.ACCOUNT_AND_WIRELESS.value,
            "acct & wireless charges detail": VerizonFileSlug.WIRELESS_CHARGES_DETAIL.value,
        }

        for pattern, slug in zip_pattern_to_slug.items():
            if pattern in filename_lower:
                bcf = file_map.get(slug)
                if bcf:
                    return bcf

        # Si no coincide con ningun patron relevante, devolver None (se ignora)
        return None

    def _download_device_payment_report(
        self, billing_cycle: BillingCycle, file_map: dict
    ) -> Optional[FileDownloadInfo]:
        """Descarga el reporte de Device Payment usando deteccion inteligente."""
        try:
            print("Descargando Device Payment report...")

            # 1. Click en device tab
            device_tab_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[2]/app-tab-click/div/div[1]/ul/li[4]"
            print("Haciendo clic en Device tab...")
            self.browser_wrapper.click_element(device_tab_xpath)
            time.sleep(2)

            # 2. Buscar Device Payment report por titulo usando logica inteligente
            device_payment_xpath = self._find_report_by_title_in_device_tab("Device Payment")
            if not device_payment_xpath:
                print("No se encontro Device Payment report")
                return None

            print("Haciendo clic en Device Payment report...")
            self.browser_wrapper.click_element(device_payment_xpath)
            time.sleep(2)

            # 3. Click en "I understand" button si aparece
            i_understand_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/div[1]/app-reporting-dashboard/div/div[2]/div/app-reporting-header/app-form-modal/div/div[2]/div[2]/div/div[2]/button"
            try:
                if self.browser_wrapper.find_element_by_xpath(i_understand_xpath, timeout=5000):
                    print("Haciendo clic en 'I understand'...")
                    self.browser_wrapper.click_element(i_understand_xpath)
                    time.sleep(2)
                else:
                    print("Boton 'I understand' no aparecio, continuando...")
            except:
                print("Boton 'I understand' no encontrado, continuando...")

            # 4. Download full report
            download_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/div[1]/app-reporting-dashboard/div/div[2]/div/div[1]/div/div[1]/div[2]"
            print("Descargando Device Payment report...")

            corresponding_bcf = file_map.get(VerizonFileSlug.DEVICE_REPORT.value)
            file_path = self.browser_wrapper.expect_download_and_click(
                download_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                print(f"Device Payment descargado: {actual_filename}")

                file_info = FileDownloadInfo(
                    file_id=corresponding_bcf.id,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    billing_cycle_file=corresponding_bcf,
                )

                if corresponding_bcf:
                    print(f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id}")

                # 5. Click en reports breadcrumb para regresar
                breadcrumb_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/div[1]/app-reporting-dashboard/div/div[1]/a"
                print("Regresando con breadcrumbs...")
                self.browser_wrapper.click_element(breadcrumb_xpath)
                time.sleep(30)

                return file_info
            else:
                print("No se pudo descargar Device Payment report")
                return None

        except Exception as e:
            print(f"Error descargando Device Payment report: {str(e)}")
            return None

    def _download_activation_deactivation_report(
        self, billing_cycle: BillingCycle, file_map: dict
    ) -> Optional[FileDownloadInfo]:
        """Descarga el reporte de Activation & Deactivation usando deteccion inteligente."""
        try:
            print("Descargando Activation & Deactivation report...")

            # 1. Click en others tab
            others_tab_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[2]/app-tab-click/div/div[1]/ul/li[5]"
            print("Haciendo clic en Others tab...")
            self.browser_wrapper.click_element(others_tab_xpath)
            time.sleep(2)

            # 2. Buscar Activation & Deactivation report por titulo usando logica inteligente
            activation_xpath = self._find_report_by_title_in_others_tab("Activation & deactivation")
            if not activation_xpath:
                print("No se encontro Activation & deactivation report")
                return None

            print("Haciendo clic en Activation & deactivation report...")
            self.browser_wrapper.click_element(activation_xpath)
            time.sleep(60)  # Esperar 1 minuto como se especifica

            # 3. Download report
            download_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/div[1]/app-reporting-dashboard/div/div[2]/div/div[1]/div/div[1]/div[2]"
            print("Descargando Activation & Deactivation report...")

            corresponding_bcf = file_map.get(VerizonFileSlug.ACTIVATION_AND_DEACTIVATION.value)
            file_path = self.browser_wrapper.expect_download_and_click(
                download_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                print(f"Activation & Deactivation descargado: {actual_filename}")

                file_info = FileDownloadInfo(
                    file_id=corresponding_bcf.id,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    billing_cycle_file=corresponding_bcf,
                )

                if corresponding_bcf:
                    print(f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id}")

                # 4. Click en reports breadcrumb para regresar
                breadcrumb_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/div[1]/app-reporting-dashboard/div/div[1]/a"
                print("Regresando con breadcrumbs...")
                self.browser_wrapper.click_element(breadcrumb_xpath)
                time.sleep(30)

                return file_info
            else:
                print("No se pudo descargar Activation & Deactivation report")
                return None

        except Exception as e:
            print(f"Error descargando Activation & Deactivation report: {str(e)}")
            return None

    def _download_suspended_lines_report(
        self, billing_cycle: BillingCycle, file_map: dict
    ) -> Optional[FileDownloadInfo]:
        """Descarga el reporte de Suspended Lines usando deteccion inteligente."""
        try:
            print("Descargando Suspended Lines report...")

            # 1. Buscar Suspended wireless number report por titulo usando logica inteligente
            # (El others tab ya deberia estar activo desde el paso anterior)
            suspended_xpath = self._find_report_by_title_in_others_tab("Suspended wireless number")
            if not suspended_xpath:
                print("No se encontro Suspended wireless number report")
                return None

            print("Haciendo clic en Suspended wireless number report...")
            self.browser_wrapper.click_element(suspended_xpath)
            time.sleep(30)  # Esperar 30 segundos como se especifica

            # 2. Download report
            download_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/div[1]/app-reporting-dashboard/div/div[2]/div/div[1]/div/div[1]/div[2]/div"
            print("Descargando Suspended Lines report...")

            corresponding_bcf = file_map.get(VerizonFileSlug.SUSPENDED_WIRELESS_NUMBERS.value)
            file_path = self.browser_wrapper.expect_download_and_click(
                download_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                print(f"Suspended Lines descargado: {actual_filename}")

                file_info = FileDownloadInfo(
                    file_id=corresponding_bcf.id,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    billing_cycle_file=corresponding_bcf,
                )

                if corresponding_bcf:
                    print(f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id}")

                return file_info
            else:
                print("No se pudo descargar Suspended Lines report")
                return None

        except Exception as e:
            print(f"Error descargando Suspended Lines report: {str(e)}")
            return None

    def _find_report_by_title_in_device_tab(self, title: str) -> Optional[str]:
        """Encuentra un reporte por su titulo dentro del device tab usando deteccion inteligente."""
        try:
            print(f"Buscando reporte en Device tab: {title}")

            # Obtener el contenedor de reportes del device tab
            device_tab_container_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[4]/div[6]/div/app-reports-list"

            # Usar JavaScript para encontrar el reporte por titulo
            report_xpath = self.browser_wrapper.page.evaluate(
                f"""
                () => {{
                    const container = document.evaluate("{device_tab_container_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
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
                print(f"Reporte encontrado en Device tab: {report_xpath}")
                return report_xpath
            else:
                print(f"No se encontro el reporte en Device tab: {title}")
                return None

        except Exception as e:
            print(f"Error buscando reporte en Device tab: {str(e)}")
            return None

    def _find_report_by_title_in_others_tab(self, title: str) -> Optional[str]:
        """Encuentra un reporte por su titulo dentro del others tab usando deteccion inteligente."""
        try:
            print(f"Buscando reporte en Others tab: {title}")

            # Obtener el contenedor de reportes del others tab
            others_tab_container_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[4]/div[5]/div/app-reports-list"

            # Usar JavaScript para encontrar el reporte por titulo
            report_xpath = self.browser_wrapper.page.evaluate(
                f"""
                () => {{
                    const container = document.evaluate("{others_tab_container_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
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
                print(f"Reporte encontrado en Others tab: {report_xpath}")
                return report_xpath
            else:
                print(f"No se encontro el reporte en Others tab: {title}")
                return None

        except Exception as e:
            print(f"Error buscando reporte en Others tab: {str(e)}")
            return None

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Verizon usando el dashboard."""
        try:
            print("Reseteando a dashboard de Verizon...")
            dashboard_url = "https://mb.verizonwireless.com/mbt/secure/index?appName=esm#/esm/dashboard"
            self.browser_wrapper.goto(dashboard_url)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("Reset a Verizon completado")
        except Exception as e:
            print(f"Error en reset de Verizon: {str(e)}")

    def _find_closest_month_option(self, billing_cycle: BillingCycle) -> Optional[str]:
        """Encuentra la opcion de mes mas cercana al end_date del billing cycle."""
        try:
            # Obtener el mes y ano del end_date del billing cycle
            target_date = billing_cycle.end_date
            target_month_name = calendar.month_abbr[target_date.month]  # 'Jan', 'Feb', etc.
            target_year = target_date.year
            target_format = f"{target_month_name} {target_year}"  # 'Jul 2025'

            print(f"Buscando fecha mas cercana a: {target_format}")

            # Obtener todas las opciones disponibles en el dropdown
            list_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[4]/div[3]/div/app-reports-list/app-raw-data-download/app-form-modal/div/div[2]/div[2]/div[2]/div/app-dropdown/div/div/div[2]/ul"

            # Usar JavaScript para obtener todas las opciones
            options_text = self.browser_wrapper.page.evaluate(
                f"""
                () => {{
                    const list = document.evaluate("{list_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (list) {{
                        const items = list.querySelectorAll('li');
                        return Array.from(items).map(item => item.textContent.trim());
                    }}
                    return [];
                }}
            """
            )

            if not options_text:
                print("No se pudieron obtener las opciones del dropdown")
                return None

            print(f"Opciones disponibles: {options_text}")

            # Buscar coincidencia exacta primero
            if target_format in options_text:
                print(f"Coincidencia exacta encontrada: {target_format}")
                return target_format

            # Si no hay coincidencia exacta, buscar la mas cercana
            # Convertir opciones a fechas para comparar
            closest_option = None
            min_diff = float("inf")

            for option in options_text:
                try:
                    # Parsear "Jul 2025" -> datetime
                    parts = option.split()
                    if len(parts) == 2:
                        month_name = parts[0]
                        year = int(parts[1])
                        month_num = list(calendar.month_abbr).index(month_name)
                        option_date = datetime(year, month_num, 1)
                        target_datetime = datetime(target_year, target_date.month, 1)

                        diff = abs((option_date - target_datetime).days)
                        if diff < min_diff:
                            min_diff = diff
                            closest_option = option
                except:
                    continue

            if closest_option:
                print(f"Opcion mas cercana encontrada: {closest_option}")
                return closest_option

            print("No se pudo encontrar una opcion adecuada")
            return None

        except Exception as e:
            print(f"Error buscando opcion de mes: {str(e)}")
            return None

    def _select_month_option(self, target_month: str) -> bool:
        """Selecciona la opcion de mes especifica en el dropdown."""
        try:
            # Buscar y hacer clic en la opcion especifica
            list_xpath = "/html/body/app-root/app-secure-layout/div/main/div/app-reports-landing/main/div/div[2]/div[2]/div/div/div[2]/div[4]/div[3]/div/app-reports-list/app-raw-data-download/app-form-modal/div/div[2]/div[2]/div[2]/div/app-dropdown/div/div/div[2]/ul"

            # Usar JavaScript para encontrar y hacer clic en la opcion
            success = self.browser_wrapper.page.evaluate(
                f"""
                () => {{
                    const list = document.evaluate("{list_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (list) {{
                        const items = list.querySelectorAll('li');
                        for (let item of items) {{
                            if (item.textContent.trim() === "{target_month}") {{
                                item.click();
                                return true;
                            }}
                        }}
                    }}
                    return false;
                }}
            """
            )

            if success:
                print(f"Seleccionado: {target_month}")
                time.sleep(1)
                return True
            else:
                print(f"No se pudo seleccionar: {target_month}")
                return False

        except Exception as e:
            print(f"Error seleccionando opcion de mes: {str(e)}")
            return False
