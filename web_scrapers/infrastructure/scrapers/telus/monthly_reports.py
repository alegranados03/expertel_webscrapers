import logging
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
        self.logger = logging.getLogger(self.__class__.__name__)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de reportes mensuales de Telus."""
        try:
            self.logger.info("Navegando a reportes mensuales de Telus...")

            # 1. Navegar a My Telus
            self.logger.info("Navegando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            self.logger.info("Navegacion inicial completada - listo para descarga de archivos")
            return {"section": "monthly_reports", "ready_for_download": True}

        except Exception as e:
            self.logger.error(f"Error navegando a reportes mensuales: {str(e)}")
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
                    self.logger.info(f"Mapeando BillingCycleFile ID {bcf.id} -> Slug: '{bcf.carrier_report.slug}'")

        try:
            # === PARTE 1: DESCARGAR ZIP DESDE BILLS SECTION ===
            self.logger.info("=== PARTE 1: DESCARGANDO ZIP DESDE BILLS SECTION ===")

            # 1. Click en bill options button
            bill_options_xpath = (
                "/html/body/div[5]/div/div/div/div[1]/div/div[3]/div/div/div/div/div/div/div[3]/div/div/div/div"
            )
            self.logger.info("Click en bill options...")
            self.browser_wrapper.click_element(bill_options_xpath)

            # 2. Click inmediato en text-bill link (el menu aparece y desaparece del DOM)
            text_bill_xpath = "//a[@href='/my-telus/text-bill?intcmp=tcom_mt_overview_button_download-text-bill']"
            self.logger.info("Click en text-bill link...")
            time.sleep(0.5)  # Breve espera para que aparezca el menu
            self.browser_wrapper.click_element(text_bill_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            # 3. Manejar posible pantalla de seleccion de cuenta (primera vez)
            if not self._handle_account_selection(billing_cycle):
                self.logger.error("Fallo en seleccion de cuenta inicial - abortando scraper")
                return downloaded_files
            time.sleep(2)

            # 4. Verificar que la cuenta seleccionada sea la correcta (caso de sesion previa con cuenta diferente)
            if not self._verify_current_account(billing_cycle):
                self.logger.error("Fallo en verificacion de cuenta actual - abortando scraper")
                return downloaded_files
            time.sleep(2)

            # 5. Buscar y click en el mes correcto basado en end_date
            target_month = billing_cycle.end_date.strftime("%B")
            target_year = billing_cycle.end_date.year

            self.logger.info(f"Buscando mes: {target_month} {target_year}")

            # 6. Descargar ZIP haciendo click en el mes (el click descarga directamente el ZIP)
            zip_file_path = self._click_month_and_download_zip(target_month, target_year)

            if zip_file_path:
                # 7. Procesar archivos extraidos del ZIP
                zip_files = self._process_downloaded_zip(zip_file_path, billing_cycle_file_map)
                downloaded_files.extend(zip_files)
                self.logger.info(f"Parte 1 completada: {len(zip_files)} archivos del ZIP")
            else:
                self.logger.info("No se pudo descargar el ZIP del mes objetivo")

            # === PARTE 2: DESCARGAR MOBILITY DEVICE SUMMARY DESDE SUMMARY REPORTS ===
            # Los archivos del ZIP (group_summary, individual_detail) ya se obtuvieron en Parte 1.
            # Aqui descargamos mobility_device desde Summary Reports en Telus IQ.

            self.logger.info("=== PARTE 2: DESCARGANDO MOBILITY DEVICE DESDE SUMMARY REPORTS ===")

            # 1. Navegar a billing header (Telus IQ)
            billing_header_xpath = '//*[@id="navOpen"]/li[2]/a'
            self.logger.info("Click en billing header...")
            self.browser_wrapper.click_element(billing_header_xpath)
            self.logger.info("Waiting 30 seconds...")
            time.sleep(30)

            # 1.1. Detectar y cerrar modal Bill Analyzer si aparece
            self._dismiss_bill_analyzer_modal()

            # 2. Click en reports header
            reports_header_xpath = '//*[@id="navMenuGroupReports"]'
            self.logger.info("Click en reports header...")
            self.browser_wrapper.click_element(reports_header_xpath)
            time.sleep(2)

            # 3. Click en summary reports (NO detail reports)
            summary_reports_xpath = '//*[@id="navMenuItem5"]'
            self.logger.info("Click en summary reports...")
            self.browser_wrapper.click_element(summary_reports_xpath)
            self.browser_wrapper.wait_for_page_load()
            self.logger.info("Waitings 30 seconds...")
            time.sleep(30)

            # 4. Descargar Mobility Device Summary (incluye configuracion de filtros Scope y Date Range)
            individual_files = self._download_individual_reports(billing_cycle, billing_cycle_file_map)
            downloaded_files.extend(individual_files)
            self.logger.info(f"Parte 2 completada: {len(individual_files)} archivos individuales")

            #Reset a pantalla principal
            self._reset_to_main_screen()

            self.logger.info(f"DESCARGA TOTAL COMPLETADA: {len(downloaded_files)} archivos")
            return downloaded_files

        except Exception as e:
            self.logger.error(f"Error en descarga de archivos: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _handle_account_selection(self, billing_cycle: BillingCycle) -> bool:
        """Maneja la pantalla de seleccion de cuenta si aparece (para credenciales con multiples cuentas)."""
        try:
            # Verificar si estamos en la pantalla "Find your account"
            find_account_header_xpath = (
                "//*[@id='__next']/div/div[1]/div/div/div/div[1]/div/div[2]/div/div/div/div[1]/div/h1"
            )

            header_element = self.browser_wrapper.find_element_by_xpath(find_account_header_xpath)
            if not header_element:
                self.logger.info("No se encontro pantalla de seleccion de cuenta, continuando...")
                return True

            # Verificar el texto del header
            header_text = self.browser_wrapper.get_text(find_account_header_xpath)
            if "Find your account" not in header_text:
                self.logger.info(f"Header encontrado pero texto diferente: '{header_text}', continuando...")
                return True

            self.logger.info("Pantalla 'Find your account' detectada - seleccionando cuenta correcta...")
            return self._select_account_from_list(billing_cycle)

        except Exception as e:
            self.logger.error(f"Error manejando seleccion de cuenta: {str(e)}")
            return False

    def _select_account_from_list(self, billing_cycle: BillingCycle) -> bool:
        """Selecciona la cuenta correcta de la lista de cuentas disponibles."""
        try:

            target_account_number = billing_cycle.account.number
            self.logger.info(f"Buscando cuenta: {target_account_number}")

            # Buscar el div que contiene el numero de cuenta especifico
            account_number_xpath = f"//div[@data-testid='account-card-north-star']//div[contains(text(), '{target_account_number}')]"

            if self.browser_wrapper.find_element_by_xpath(account_number_xpath):
                self.logger.info(f"Cuenta {target_account_number} encontrada, haciendo click...")
                target_card_xpath = f"//div[@data-testid='account-card-north-star'][.//div[contains(text(), '{target_account_number}')]]"
                self.browser_wrapper.click_element(target_card_xpath)
                self.browser_wrapper.wait_for_page_load()
                time.sleep(3)
                self.logger.info(f"Cuenta {target_account_number} seleccionada exitosamente")
                return True
            else:
                self.logger.error(f"Cuenta {target_account_number} NO encontrada en la lista de cuentas disponibles")
                return False

        except Exception as e:
            self.logger.error(f"Error seleccionando cuenta de la lista: {str(e)}")
            return False

    def _verify_current_account(self, billing_cycle: BillingCycle) -> bool:
        """
        Verifica que la cuenta actualmente seleccionada sea la correcta.
        Este metodo se usa justo antes de descargar el ZIP, donde aparece el header con 'Account #XXXXXXXX'.
        Si la cuenta no coincide, hace click en 'Change' y selecciona la cuenta correcta.
        """
        try:
            target_account_number = billing_cycle.account.number
            self.logger.info(f"Verificando cuenta actual vs objetivo: {target_account_number}")

            # Buscar el elemento que muestra la cuenta actual
            # Estructura: <div>Account #42680715</div> seguido de <a>Change</a>
            account_header_xpath = "//*[@id='app']/div/div[2]/div/div[1]/div/div[2]"

            if not self.browser_wrapper.find_element_by_xpath(account_header_xpath):
                self.logger.info("No se encontro header de cuenta (credenciales con cuenta unica), continuando...")
                return True

            # Obtener el texto del header de cuenta
            account_header_text = self.browser_wrapper.get_text(account_header_xpath)
            self.logger.info(f"Header de cuenta encontrado: '{account_header_text}'")

            # Verificar si el numero de cuenta objetivo esta en el header
            if target_account_number in account_header_text:
                self.logger.info(f"Cuenta correcta confirmada: {target_account_number}")
                return True

            # La cuenta no coincide, necesitamos cambiarla
            self.logger.info(f"Cuenta incorrecta detectada. Esperado: {target_account_number}, Actual: {account_header_text}")
            self.logger.info("Haciendo click en 'Change' para cambiar de cuenta...")

            # Buscar y hacer click en el enlace "Change"
            change_link_xpath = "//*[@id='app']/div/div[2]/div/div[1]/div/div[2]//a[contains(text(), 'Change')]"
            # Alternativa mas especifica basada en la estructura proporcionada
            change_link_alt_xpath = "//a[.//div[contains(text(), 'Change')]]"

            if self.browser_wrapper.find_element_by_xpath(change_link_xpath):
                self.browser_wrapper.click_element(change_link_xpath)
            elif self.browser_wrapper.find_element_by_xpath(change_link_alt_xpath):
                self.browser_wrapper.click_element(change_link_alt_xpath)
            else:
                self.logger.error("No se encontro el enlace 'Change'")
                return False

            time.sleep(5)

            self.logger.info("Navegando a pantalla de seleccion de cuenta...")
            return self._select_account_from_list(billing_cycle)

        except Exception as e:
            self.logger.error(f"Error verificando cuenta actual: {str(e)}")
            return True

    def _click_month_and_download_zip(self, target_month: str, target_year: int) -> Optional[str]:
        """
        Busca el mes objetivo y descarga el ZIP haciendo click en el mes.
        El click en el mes descarga directamente el archivo ZIP.
        Retorna la ruta del archivo descargado o None si falla.
        """
        try:
            self.logger.info(f"Directorio de descarga configurado: {self.job_downloads_dir}")

            # Buscar el ano objetivo primero
            year_xpath = f"//h2[contains(text(), '{target_year}')]"
            if not self.browser_wrapper.find_element_by_xpath(year_xpath):
                self.logger.error(f"No se encontro el ano {target_year}")
                return None

            self.logger.info(f"Encontrado ano {target_year}")

            # Buscar el enlace del mes objetivo
            month_link_xpath = f"//div[contains(@class, 'css-146c3p1') and contains(text(), '{target_month}')]"

            if not self.browser_wrapper.find_element_by_xpath(month_link_xpath):
                self.logger.error(f"No se encontro el mes {target_month} en el ano {target_year}")
                return None

            self.logger.info(f"Encontrado mes {target_month}, descargando ZIP...")

            # El click en el mes descarga directamente el ZIP
            # Usar expect_download_and_click para capturar la descarga
            parent_link_xpath = f"//div[contains(@class, 'css-146c3p1') and contains(text(), '{target_month}')]/parent::div/parent::div"

            zip_file_path = self.browser_wrapper.expect_download_and_click(
                parent_link_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if zip_file_path:
                self.logger.info(f"ZIP descargado exitosamente: {zip_file_path}")
                return zip_file_path
            else:
                self.logger.error("expect_download_and_click retorno None")
                # Verificar si el archivo se descargo de todos modos
                if self.job_downloads_dir and os.path.exists(self.job_downloads_dir):
                    files_in_dir = os.listdir(self.job_downloads_dir)
                    self.logger.info(f"Archivos en directorio de descarga: {files_in_dir}")
                    # Buscar archivos ZIP
                    zip_files = [f for f in files_in_dir if f.endswith('.zip')]
                    if zip_files:
                        zip_file_path = os.path.join(self.job_downloads_dir, zip_files[0])
                        self.logger.info(f"ZIP encontrado manualmente: {zip_file_path}")
                        return zip_file_path
                return None

        except Exception as e:
            self.logger.error(f"Error descargando ZIP del mes: {str(e)}")
            return None

    def _process_downloaded_zip(self, zip_file_path: str, file_map: dict) -> List[FileDownloadInfo]:
        """
        Procesa el ZIP descargado, extrae archivos y los mapea a BillingCycleFiles.
        IMPORTANTE: Solo se agregan a downloaded_files los archivos que tienen mapeo valido.
        Del ZIP solo se necesitan: individual_detail, group_summary
        """
        downloaded_files = []

        try:
            self.logger.info(f"Procesando ZIP: {os.path.basename(zip_file_path)}")

            # Extraer archivos del ZIP
            extracted_files = self._extract_zip_files(zip_file_path)
            if not extracted_files:
                self.logger.error("No se pudieron extraer archivos del ZIP")
                return downloaded_files

            self.logger.info(f"Extraidos {len(extracted_files)} archivos del ZIP")

            # Procesar archivos extraidos y mapearlos
            # SOLO agregar archivos que tienen mapeo valido (individual_detail, group_summary)
            for file_path in extracted_files:
                original_filename = os.path.basename(file_path)
                self.logger.info(f"Procesando archivo: {original_filename}")

                # Buscar el BillingCycleFile correspondiente
                corresponding_bcf = self._find_matching_billing_cycle_file(original_filename, file_map)

                if corresponding_bcf:
                    self.logger.info(f"Mapeando {original_filename} -> BillingCycleFile ID {corresponding_bcf.id}")
                    file_info = FileDownloadInfo(
                        file_id=corresponding_bcf.id,
                        file_name=original_filename,
                        download_url="N/A",
                        file_path=file_path,
                        billing_cycle_file=corresponding_bcf,
                    )
                    downloaded_files.append(file_info)
                else:
                    self.logger.info(f"Archivo {original_filename} sin mapeo - NO se agregara a la lista de subida")

            self.logger.info(f"Total archivos del ZIP con mapeo valido: {len(downloaded_files)}")
            return downloaded_files

        except Exception as e:
            self.logger.error(f"Error procesando ZIP: {str(e)}")
            return downloaded_files

    def _download_and_process_zip(self, billing_cycle: BillingCycle, file_map: dict) -> List[FileDownloadInfo]:
        """Descarga y procesa el ZIP con los archivos del mes."""
        downloaded_files = []

        try:
            self.logger.info(f"Directorio de descarga configurado: {self.job_downloads_dir}")

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
                        self.logger.info(f"Elemento encontrado con xpath: {xpath}")
                        self.logger.info(f"Intentando descargar ZIP a: {self.job_downloads_dir}")
                        zip_file_path = self.browser_wrapper.expect_download_and_click(
                            xpath, timeout=60000, downloads_dir=self.job_downloads_dir
                        )
                        self.logger.info(f"Resultado de descarga: {zip_file_path}")
                        if zip_file_path:
                            break
                except Exception as e:
                    self.logger.error(f"Error con xpath {xpath}: {str(e)}")
                    continue

            if not zip_file_path:
                self.logger.error(f"No se pudo descargar ZIP. Verificando directorio: {self.job_downloads_dir}")
                # Listar archivos en el directorio de descarga para diagnóstico
                if self.job_downloads_dir and os.path.exists(self.job_downloads_dir):
                    files_in_dir = os.listdir(self.job_downloads_dir)
                    self.logger.info(f"Archivos en directorio de descarga: {files_in_dir}")
                return downloaded_files

            self.logger.info(f"ZIP descargado: {os.path.basename(zip_file_path)}")

            # Extraer archivos del ZIP
            extracted_files = self._extract_zip_files(zip_file_path)
            if not extracted_files:
                self.logger.info("No se pudieron extraer archivos del ZIP")
                return downloaded_files

            self.logger.info(f"Extraidos {len(extracted_files)} archivos del ZIP")

            # Procesar archivos extraidos y mapearlos
            for i, file_path in enumerate(extracted_files):
                original_filename = os.path.basename(file_path)
                self.logger.info(f"Procesando archivo: {original_filename}")

                # Buscar el BillingCycleFile correspondiente
                corresponding_bcf = self._find_matching_billing_cycle_file(original_filename, file_map)

                if corresponding_bcf:
                    self.logger.info(f"Mapeando {original_filename} -> BillingCycleFile ID {corresponding_bcf.id}")
                else:
                    self.logger.info(f"No se encontro mapeo para {original_filename}")

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
            self.logger.error(f"Error procesando ZIP: {str(e)}")
            return downloaded_files

    def _find_matching_billing_cycle_file(self, filename: str, file_map: dict) -> Optional[Any]:
        """
        Encuentra el BillingCycleFile que corresponde al nombre de archivo.
        NOTA: Solo mapea archivos del ZIP (individual_detail, group_summary).
        El mobility_device viene de los reportes individuales (Parte 2).
        """
        filename_lower = filename.lower()

        # Mapeo de patrones de nombres de archivos ZIP a slugs de Telus
        # Solo 2 slugs del ZIP: individual_detail, group_summary
        # mobility_device se obtiene de la Parte 2 (reportes individuales)
        pattern_to_slug = {
            "group_summary": "group_summary",
            "individual_detail": "individual_detail",
        }

        for pattern, slug in pattern_to_slug.items():
            if pattern in filename_lower:
                bcf = file_map.get(slug)
                if bcf:
                    return bcf

        return None

    def _dismiss_bill_analyzer_modal(self) -> bool:
        """
        Detecta y cierra el modal de Bill Analyzer si aparece.
        Este modal puede aparecer al navegar a la seccion de reportes.
        Retorna True si se cerro el modal o si no aparecio.
        """
        try:
            modal_button_xpath = "//*[@id='tandc-content']/div[3]/button"

            # Verificar si el modal esta presente (con timeout corto)
            if self.browser_wrapper.is_element_visible(modal_button_xpath, timeout=3000):
                self.logger.info("Modal Bill Analyzer detectado, cerrando...")
                self.browser_wrapper.click_element(modal_button_xpath)
                time.sleep(2)
                self.logger.info("Modal Bill Analyzer cerrado")
                return True
            else:
                self.logger.info("Modal Bill Analyzer no detectado, continuando...")
                return True

        except Exception as e:
            self.logger.warning(f"Error manejando modal Bill Analyzer: {str(e)}")
            return True  # Continuar de todos modos

    def _configure_date_selection(self, billing_cycle: BillingCycle):
        """Configura la seleccion de fecha para los reportes individuales."""
        try:
            # 1. Click en date selection
            date_selection_xpath = (
                "/html[1]/body[1]/div[2]/form[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/button[1]"
            )
            self.logger.info("Click en date selection...")
            self.browser_wrapper.click_element(date_selection_xpath)
            time.sleep(2)

            # 2. Configurar dropdown de fecha
            target_period = billing_cycle.end_date.strftime("%B %Y") + " statements"
            select_date_dropdown_xpath = "/html[1]/body[1]/div[2]/form[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/select[1]"
            self.logger.info(f"Seleccionando periodo: {target_period}")

            try:
                self.browser_wrapper.select_dropdown_option(select_date_dropdown_xpath, target_period)
            except:
                # Fallback: buscar solo por mes y ano sin "statements"
                fallback_period = billing_cycle.end_date.strftime("%B %Y")
                self.logger.info(f"Fallback - Seleccionando: {fallback_period}")
                self.browser_wrapper.select_dropdown_option(select_date_dropdown_xpath, fallback_period)

            time.sleep(2)

            # 3. Click en confirm button
            confirm_button_xpath = "/html[1]/body[1]/div[2]/form[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[5]/button[1]"
            self.logger.info("Click en confirm button...")
            self.browser_wrapper.click_element(confirm_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

        except Exception as e:
            self.logger.error(f"Error configurando fecha: {str(e)}")
            raise

    def _configure_scope_filter(self, billing_cycle: BillingCycle) -> bool:
        """
        Configura el filtro de Scope (cuenta) en Telus IQ.
        Flujo: abrir dropdown, seleccionar Accounts, buscar cuenta, confirmar con OK.
        """
        try:
            target_account = billing_cycle.account.number
            self.logger.info(f"Configurando Scope filter para cuenta: {target_account}")

            # 1. Click en Scope dropdown button
            scope_button_xpath = "//*[@id='LevelDataDropdownButton']"
            self.logger.info("Click en Scope dropdown button...")
            self.browser_wrapper.click_element(scope_button_xpath)
            time.sleep(2)

            # 2. Click en "Accounts" option para mostrar lista de cuentas
            accounts_option_xpath = "//*[@id='LevelDataDropdownList_multipleaccounts']"
            self.logger.info("Seleccionando opcion 'Accounts'...")
            self.browser_wrapper.click_element(accounts_option_xpath)
            time.sleep(3)

            # 3. Buscar la cuenta en el campo de busqueda o en la lista
            search_input_xpath = "//input[contains(@placeholder, 'Search') or contains(@class, 'search')]"
            if self.browser_wrapper.find_element_by_xpath(search_input_xpath, timeout=2000):
                self.logger.info(f"Buscando cuenta: {target_account}")
                self.browser_wrapper.clear_and_type(search_input_xpath, target_account)
                time.sleep(2)

            # 4. Buscar y seleccionar la cuenta en la lista
            account_option_xpath = f"//*[contains(text(), '{target_account}')]"
            if not self.browser_wrapper.find_element_by_xpath(account_option_xpath):
                self.logger.error(f"Cuenta {target_account} no encontrada en la lista")
                return False

            self.logger.info(f"Cuenta {target_account} encontrada, seleccionando...")
            self.browser_wrapper.click_element(account_option_xpath)
            time.sleep(2)

            # 5. Click en el checkbox si aparece
            first_item_xpath = "//div[contains(@class, 'checkbox')]//input | //li[contains(@class, 'list-group-item')]//input[@type='checkbox']"
            if self.browser_wrapper.find_element_by_xpath(first_item_xpath, timeout=2000):
                self.browser_wrapper.click_element(first_item_xpath)
                time.sleep(1)

            # 6. Click en boton OK para confirmar la seleccion de Scope
            scope_ok_button_xpath = "//*[@id='scopeExpandedAccountMenu']/div[4]/button"
            if not self.browser_wrapper.find_element_by_xpath(scope_ok_button_xpath, timeout=3000):
                self.logger.error("Boton OK de Scope no encontrado")
                return False

            self.logger.info("Click en boton OK para confirmar Scope...")
            self.browser_wrapper.click_element(scope_ok_button_xpath)
            time.sleep(3)

            self.logger.info(f"Scope configurado para cuenta: {target_account}")
            return True

        except Exception as e:
            self.logger.error(f"Error configurando Scope filter: {str(e)}")
            return False

    def _configure_date_range_filter(self, billing_cycle: BillingCycle) -> bool:
        """
        Configura el filtro de Date Range en Telus IQ.
        Flujo:
        1. Click en CIDPendingDataDropdownButton para abrir el menu
        2. Seleccionar directamente por value en bmtype_data (Select2)
        3. Click en btnApply para confirmar

        El value sigue el patron bYYYYMM21 (siempre dia 21)
        Ejemplo: para noviembre 2025 -> b20251121
        """
        try:
            target_month = billing_cycle.end_date.month
            target_year = billing_cycle.end_date.year
            # Construir el value directamente: bYYYYMM21 (siempre dia 21)
            target_value = f"b{target_year}{target_month:02d}21"
            target_date_text = f"{target_month:02d}-21-{target_year} statement"

            self.logger.info(f"Configurando Date Range filter para: {target_date_text} (value={target_value})")

            # 1. Click en Date Range dropdown button para abrir el menu
            date_button_xpath = "//*[@id='CIDPendingDataDropdownButton']"
            self.logger.info("Click en CIDPendingDataDropdownButton...")
            self.browser_wrapper.click_element(date_button_xpath)
            time.sleep(2)

            # 2. Seleccionar directamente por value (Select2 component)
            bmtype_select_xpath = "//*[@id='bmtype_data']"
            self.logger.info(f"Seleccionando por value: {target_value}")
            self.browser_wrapper.select_dropdown_by_value(bmtype_select_xpath, target_value)
            time.sleep(1)

            # 3. Click en OK para aplicar
            if not self._click_date_range_ok_button():
                self.logger.error("Error aplicando Date Range (boton OK)")
                return False

            self.logger.info(f"Date Range configurado exitosamente: {target_date_text}")
            return True

        except Exception as e:
            self.logger.error(f"Error configurando Date Range filter: {str(e)}")
            return False

    def _click_date_range_ok_button(self) -> bool:
        """Click en el boton OK/Apply para confirmar la seleccion de fecha."""
        try:
            ok_button_xpath = "//*[@id='btnApply']"
            if self.browser_wrapper.find_element_by_xpath(ok_button_xpath, timeout=2000):
                self.logger.info("Click en boton OK para aplicar Date Range...")
                self.browser_wrapper.click_element(ok_button_xpath)
                time.sleep(3)
                return True
            return False
        except Exception as e:
            self.logger.warning(f"Error clickeando boton OK: {str(e)}")
            return False

    def _download_individual_reports(self, billing_cycle: BillingCycle, file_map: dict) -> List[FileDownloadInfo]:
        """
        Descarga el reporte Mobility Device Summary desde Summary Reports.
        Flujo similar a ATT:
        1. Configurar Scope (cuenta) filter
        2. Configurar Date Range filter
        3. Buscar seccion "Mobility Device Summary" en el accordion
        4. Click en el reporte "Mobility Device Summary Report"
        5. Descargar el reporte
        """
        downloaded_files = []

        try:
            self.logger.info("=== DESCARGANDO MOBILITY DEVICE SUMMARY ===")

            # 1. Configurar Scope filter (cuenta)
            self.logger.info("Configurando filtro de Scope...")
            if not self._configure_scope_filter(billing_cycle):
                self.logger.error("No se pudo configurar Scope filter - archivo marcado como fallido")
                return downloaded_files
            time.sleep(3)

            # 2. Configurar Date Range filter (OBLIGATORIO - sin fallback)
            self.logger.info("Configurando filtro de Date Range...")
            if not self._configure_date_range_filter(billing_cycle):
                self.logger.error("No se pudo configurar Date Range filter - archivo marcado como fallido")
                return downloaded_files
            time.sleep(3)

            # 3. Buscar y expandir la seccion "Mobility Device Summary" en el accordion
            # El accordion tiene id="accordion" y la seccion Mobility Device Summary tiene id="collapse42"
            mobility_section_header_xpath = "//*[@id='heading42']"
            mobility_section_collapse_xpath = "//*[@id='collapse42']"

            # Verificar si la seccion existe
            if not self.browser_wrapper.find_element_by_xpath(mobility_section_header_xpath):
                self.logger.error("Seccion 'Mobility Device Summary' no encontrada en el accordion")
                return downloaded_files

            self.logger.info("Seccion 'Mobility Device Summary' encontrada")

            # Verificar si la seccion esta colapsada y expandirla si es necesario
            # Buscar el boton de toggle en el header
            toggle_button_xpath = "//*[@id='heading42']//button[@data-toggle='collapse']"
            if self.browser_wrapper.find_element_by_xpath(toggle_button_xpath):
                # Verificar si esta colapsada (aria-expanded="false")
                is_collapsed = self.browser_wrapper.get_attribute(toggle_button_xpath, "aria-expanded")
                if is_collapsed == "false":
                    self.logger.info("Expandiendo seccion 'Mobility Device Summary'...")
                    self.browser_wrapper.click_element(toggle_button_xpath)
                    time.sleep(2)

            # 4. Buscar el reporte "Mobility Device Summary Report" dentro de la seccion
            # Buscar cualquier boton con btnSelectSummaryReport que contenga "Mobility Device"
            mobility_report_xpath = "//*[@id='collapse42']//button[contains(@id, 'btnSelectSummaryReport')][contains(., 'Mobility Device')]"
            # Alternativa: buscar por texto parcial
            mobility_report_alt_xpath = "//*[@id='collapse42']//button[contains(text(), 'Mobility Device')]"

            report_found = False
            report_xpath_to_use = None

            if self.browser_wrapper.find_element_by_xpath(mobility_report_xpath):
                report_xpath_to_use = mobility_report_xpath
                report_found = True
            elif self.browser_wrapper.find_element_by_xpath(mobility_report_alt_xpath):
                report_xpath_to_use = mobility_report_alt_xpath
                report_found = True

            if not report_found:
                self.logger.error("Reporte 'Mobility Device Summary Report' no encontrado en Mobility Device Summary section")
                return downloaded_files

            # Verificar el texto del boton
            button_text = self.browser_wrapper.get_text(report_xpath_to_use)
            self.logger.info(f"Reporte encontrado: {button_text}")

            corresponding_bcf = file_map.get("mobility_device")
            if corresponding_bcf:
                self.logger.info(f"Usando BillingCycleFile ID {corresponding_bcf.id} para mobility_device")

            # 5. Click en el reporte para abrir la vista del reporte
            self.logger.info("Click en reporte 'Mobility Device Summary Report'...")
            self.browser_wrapper.click_element(report_xpath_to_use)
            self.logger.info("Esperando 1 minuto para que cargue el reporte...")
            time.sleep(60)

            # 6. Click en boton Export/Download
            export_button_xpath = "//*[@id='export']"
            if not self.browser_wrapper.find_element_by_xpath(export_button_xpath, timeout=10000):
                self.logger.error("Boton Export no encontrado")
                return downloaded_files

            self.logger.info("Click en boton Export...")
            self.browser_wrapper.click_element(export_button_xpath)
            time.sleep(3)

            # 7. Seleccionar formato CSV
            csv_label_xpath = "//*[@id='radCsvLabel']"
            if self.browser_wrapper.find_element_by_xpath(csv_label_xpath, timeout=5000):
                self.logger.info("Seleccionando formato CSV...")
                self.browser_wrapper.click_element(csv_label_xpath)
                time.sleep(1)
            else:
                self.logger.warning("Label CSV no encontrado, continuando...")

            # 8. Click en boton OK para descargar
            ok_button_xpath = "//*[@id='hrefOK']"
            if not self.browser_wrapper.find_element_by_xpath(ok_button_xpath, timeout=5000):
                self.logger.error("Boton OK no encontrado")
                return downloaded_files

            self.logger.info("Click en boton OK para descargar...")
            downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                ok_button_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if downloaded_file_path:
                actual_filename = os.path.basename(downloaded_file_path)
                self.logger.info(f"Mobility Device descargado: {actual_filename}")

                file_info = FileDownloadInfo(
                    file_id=corresponding_bcf.id if corresponding_bcf else len(downloaded_files) + 1,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=downloaded_file_path,
                    billing_cycle_file=corresponding_bcf,
                )
                downloaded_files.append(file_info)

                if corresponding_bcf:
                    self.logger.info(f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id}")
            else:
                self.logger.error("No se pudo descargar el reporte Mobility Device")

            time.sleep(5)

        except Exception as e:
            self.logger.error(f"Error descargando Mobility Device Summary: {str(e)}")

        return downloaded_files

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Telus usando My Telus."""
        try:
            self.logger.info("Reseteando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            self.logger.info("Reset completado")
        except Exception as e:
            self.logger.error(f"Error en reset: {str(e)}")