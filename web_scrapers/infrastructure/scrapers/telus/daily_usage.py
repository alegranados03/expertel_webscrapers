import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    DailyUsageScraperStrategy,
    FileDownloadInfo,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class TelusDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para Telus.

    Este scraper:
    1. Navega a la tab de Usage para obtener pool_size y pool_used
    2. Navega a Telus IQ via Overview
    3. Genera y descarga el Daily Usage Report
    """

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pool_size: Optional[int] = None  # En bytes
        self.pool_used: Optional[int] = None  # En bytes

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de uso diario en Telus y obtiene datos del pool."""
        try:
            self.logger.info("=== INICIANDO TELUS DAILY USAGE SCRAPER ===")

            # 1. Verificar que estamos en My Telus
            current_url = self.browser_wrapper.get_current_url()
            if "my-telus" not in current_url:
                self.logger.info("Navegando a My Telus...")
                self.browser_wrapper.goto("https://www.telus.com/my-telus")
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)

            # 2. Click en la tab de Usage
            usage_tab_xpath = '//*[@id="navOpen"]/li[3]/a'
            self.logger.info("Click en tab de Usage...")
            self.browser_wrapper.click_element(usage_tab_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # 3. Manejar posible pantalla "Find your account"
            if not self._handle_account_selection(billing_cycle):
                self.logger.error("Fallo en seleccion de cuenta - abortando scraper")
                return None

            # 4. Verificar que la cuenta actual es la correcta
            if not self._verify_current_account(billing_cycle):
                self.logger.error("Fallo en verificacion de cuenta - abortando scraper")
                return None

            time.sleep(3)

            # 5. Extraer pool_size y pool_used
            pool_data = self._extract_pool_data()
            if pool_data:
                self.pool_used, self.pool_size = pool_data
                self.logger.info(f"Pool data extraido: used={self.pool_used} bytes, size={self.pool_size} bytes")
            else:
                self.logger.warning("No se pudo extraer pool data, continuando sin datos de pool...")

            # 6. Navegar a Overview tab
            overview_tab_xpath = '//*[@id="navOpen"]/li[1]/a'
            self.logger.info("Click en tab de Overview...")
            self.browser_wrapper.click_element(overview_tab_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # 7. Click en "Go to Telus IQ"
            telus_iq_button_xpath = (
                "/html/body/div[5]/div/div/div/div[1]/div/div[3]/div/div/div/div/div/div/div[3]/div/div/a"
            )
            self.logger.info("Click en 'Go to Telus IQ' button...")
            self.browser_wrapper.click_element(telus_iq_button_xpath)
            self.logger.info("Esperando 30 segundos para cargar Telus IQ...")
            time.sleep(30)

            # 8. Manejar modal de Bill Analyzer si aparece
            self._dismiss_bill_analyzer_modal()

            # 9. Click en Manage tab
            manage_tab_xpath = '//*[@id="site-header__root"]/div[1]/div/div/div/div/ul[1]/li[2]/a'
            self.logger.info("Click en Manage tab...")
            self.browser_wrapper.click_element(manage_tab_xpath)
            time.sleep(3)

            # 10. Click en Usage View option
            usage_view_xpath = '//*[@id="site-header__root"]/div[2]/div/div/div/div/div[2]/div[1]/div[3]/div/a'
            self.logger.info("Verificando opcion 'Usage view'...")

            # Validar que efectivamente diga "Usage view"
            if self.browser_wrapper.find_element_by_xpath(usage_view_xpath, timeout=5000):
                link_text = self.browser_wrapper.get_text(usage_view_xpath)
                if "Usage view" in link_text:
                    self.logger.info("Click en 'Usage view' option...")
                    self.browser_wrapper.click_element(usage_view_xpath)
                else:
                    self.logger.warning(f"Texto inesperado en enlace: '{link_text}', intentando click de todos modos...")
                    self.browser_wrapper.click_element(usage_view_xpath)
            else:
                self.logger.error("Opcion 'Usage view' no encontrada")
                return None

            self.logger.info("Esperando 15 segundos para cargar Usage View...")
            time.sleep(15)

            # 11. Configurar busqueda avanzada con el BAN
            if not self._configure_advanced_search(billing_cycle):
                self.logger.error("Fallo en configuracion de busqueda avanzada")
                return None

            self.logger.info("Navegacion a seccion de uso diario completada")
            return {
                "section": "daily_usage",
                "ready_for_export": True,
                "pool_size": self.pool_size,
                "pool_used": self.pool_used,
            }

        except Exception as e:
            self.logger.error(f"Error navegando a seccion de uso diario: {str(e)}")
            return None

    def _handle_account_selection(self, billing_cycle: BillingCycle) -> bool:
        """Maneja la pantalla de seleccion de cuenta si aparece."""
        try:
            # Verificar si estamos en la pantalla "Find your account"
            find_account_header_xpath = (
                "//*[@id='__next']/div/div[1]/div/div/div/div[1]/div/div[2]/div/div/div/div[1]/div/h1"
            )

            header_element = self.browser_wrapper.find_element_by_xpath(find_account_header_xpath, timeout=3000)
            if not header_element:
                self.logger.info("No se encontro pantalla de seleccion de cuenta, continuando...")
                return True

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
            account_number_xpath = (
                f"//div[@data-testid='account-card-north-star']//div[contains(text(), '{target_account_number}')]"
            )

            if self.browser_wrapper.find_element_by_xpath(account_number_xpath, timeout=5000):
                self.logger.info(f"Cuenta {target_account_number} encontrada, haciendo click...")
                target_card_xpath = (
                    f"//div[@data-testid='account-card-north-star'][.//div[contains(text(), '{target_account_number}')]]"
                )
                self.browser_wrapper.click_element(target_card_xpath)
                self.browser_wrapper.wait_for_page_load()
                time.sleep(3)
                self.logger.info(f"Cuenta {target_account_number} seleccionada exitosamente")
                return True
            else:
                self.logger.error(f"Cuenta {target_account_number} NO encontrada en la lista")
                return False

        except Exception as e:
            self.logger.error(f"Error seleccionando cuenta de la lista: {str(e)}")
            return False

    def _verify_current_account(self, billing_cycle: BillingCycle) -> bool:
        """Verifica que la cuenta actualmente seleccionada sea la correcta."""
        try:
            target_account_number = billing_cycle.account.number
            self.logger.info(f"Verificando cuenta actual vs objetivo: {target_account_number}")

            # Buscar el elemento que muestra el numero de cuenta actual
            account_number_xpath = '//*[@data-testid="accountNumber"]'

            if not self.browser_wrapper.find_element_by_xpath(account_number_xpath, timeout=5000):
                self.logger.info("No se encontro elemento de numero de cuenta, continuando...")
                return True

            current_account = self.browser_wrapper.get_text(account_number_xpath)
            self.logger.info(f"Cuenta actual: '{current_account}'")

            if target_account_number in current_account or current_account in target_account_number:
                self.logger.info(f"Cuenta correcta confirmada: {target_account_number}")
                return True

            # La cuenta no coincide, necesitamos cambiarla
            self.logger.info(f"Cuenta incorrecta. Esperado: {target_account_number}, Actual: {current_account}")
            self.logger.info("Buscando enlace 'Change account'...")

            # Buscar el enlace "Change account"
            change_account_xpath = '//*[@data-testid="link"]//div[contains(text(), "Change account")]'
            change_account_parent_xpath = '//*[@data-testid="link"]'

            if self.browser_wrapper.find_element_by_xpath(change_account_xpath, timeout=3000):
                self.logger.info("Click en 'Change account'...")
                self.browser_wrapper.click_element(change_account_parent_xpath)
                self.browser_wrapper.wait_for_page_load()
                time.sleep(5)
                return self._select_account_from_list(billing_cycle)
            else:
                self.logger.error("No se encontro enlace 'Change account'")
                return False

        except Exception as e:
            self.logger.error(f"Error verificando cuenta actual: {str(e)}")
            return True  # Continuar si hay error

    def _extract_pool_data(self) -> Optional[Tuple[int, int]]:
        """Extrae pool_used y pool_size del div de uso y los convierte a bytes."""
        try:
            self.logger.info("Extrayendo datos de pool...")

            # XPath del div que contiene los datos de uso
            usage_container_xpath = '//*[@id="app"]/div[2]/div/div/div/div[3]/div[7]/div/div[2]/div/div[3]/div/div/div[5]'

            if not self.browser_wrapper.find_element_by_xpath(usage_container_xpath, timeout=5000):
                self.logger.warning("Contenedor de uso no encontrado")
                return None

            # Extraer valores individuales usando data-testid
            usage_used_xpath = '//*[@data-testid="usage-used"]'
            usage_allowance_xpath = '//*[@data-testid="usage-allowance"]'

            pool_used_text = None
            pool_size_text = None

            if self.browser_wrapper.find_element_by_xpath(usage_used_xpath, timeout=3000):
                pool_used_text = self.browser_wrapper.get_text(usage_used_xpath)
                self.logger.info(f"Usage used raw: '{pool_used_text}'")

            if self.browser_wrapper.find_element_by_xpath(usage_allowance_xpath, timeout=3000):
                pool_size_text = self.browser_wrapper.get_text(usage_allowance_xpath)
                self.logger.info(f"Usage allowance raw: '{pool_size_text}'")

            if not pool_used_text or not pool_size_text:
                self.logger.warning("No se pudieron extraer valores de uso")
                return None

            # Parsear valores y convertir a bytes
            pool_used_bytes = self._parse_gb_to_bytes(pool_used_text)
            pool_size_bytes = self._parse_gb_to_bytes(pool_size_text)

            if pool_used_bytes is not None and pool_size_bytes is not None:
                self.logger.info(f"Pool used: {pool_used_bytes} bytes ({pool_used_text})")
                self.logger.info(f"Pool size: {pool_size_bytes} bytes ({pool_size_text})")
                return (pool_used_bytes, pool_size_bytes)
            else:
                self.logger.warning("Error parseando valores de pool")
                return None

        except Exception as e:
            self.logger.error(f"Error extrayendo datos de pool: {str(e)}")
            return None

    def _parse_gb_to_bytes(self, value_text: str) -> Optional[int]:
        """Parsea un valor de GB a bytes."""
        try:
            # Limpiar el texto y extraer el numero
            # Ejemplos: "47.13", "601 GB", "47.13 GB"
            cleaned = value_text.strip().replace(",", "")

            # Extraer solo el numero (puede tener decimales)
            match = re.search(r"([\d.]+)", cleaned)
            if not match:
                return None

            value = float(match.group(1))

            # Convertir GB a bytes (1 GB = 1024^3 bytes)
            bytes_value = int(value * (1024 ** 3))
            return bytes_value

        except Exception as e:
            self.logger.error(f"Error parseando '{value_text}' a bytes: {str(e)}")
            return None

    def _dismiss_bill_analyzer_modal(self) -> bool:
        """Detecta y cierra el modal de Bill Analyzer si aparece."""
        try:
            # Buscar el boton "don't show again" del modal de Bill Analyzer
            dont_show_again_xpath = (
                "/html/body/div[1]/html/body/div/div/div/div[2]/div/div[2]/div[2]/div[1]/div/div/div[3]/div/div[2]/p/div/a"
            )

            if self.browser_wrapper.find_element_by_xpath(dont_show_again_xpath, timeout=5000):
                self.logger.info("Modal Bill Analyzer detectado, cerrando...")
                self.browser_wrapper.click_element(dont_show_again_xpath)
                time.sleep(2)
                self.logger.info("Modal Bill Analyzer cerrado")
                return True
            else:
                self.logger.info("Modal Bill Analyzer no detectado, continuando...")
                return True

        except Exception as e:
            self.logger.warning(f"Error manejando modal Bill Analyzer: {str(e)}")
            return True  # Continuar de todos modos

    def _configure_advanced_search(self, billing_cycle: BillingCycle) -> bool:
        """Configura la busqueda avanzada con el BAN de la cuenta."""
        try:
            target_account = billing_cycle.account.number
            self.logger.info(f"Configurando busqueda avanzada para cuenta: {target_account}")

            # 1. Click en Advanced search toggle
            advanced_toggle_xpath = '//*[@id="advanced__search__toggle"]'
            self.logger.info("Click en Advanced search toggle...")
            self.browser_wrapper.click_element(advanced_toggle_xpath)
            time.sleep(2)

            # 2. Verificar que el panel de busqueda avanzada esta abierto
            advanced_panel_xpath = '//*[@id="advanced__search"]'
            if not self.browser_wrapper.find_element_by_xpath(advanced_panel_xpath, timeout=5000):
                self.logger.error("Panel de busqueda avanzada no se abrio")
                return False

            self.logger.info("Panel de busqueda avanzada abierto")

            # 3. Seleccionar "Account number (BAN)" en el primer dropdown
            filter_select_xpath = '//*[@id="advancedsearchselect"]'
            self.logger.info("Seleccionando 'Account number (BAN)' en dropdown de filtro...")
            self.browser_wrapper.select_dropdown_by_value(filter_select_xpath, "accountnum")
            time.sleep(2)

            # 4. Seleccionar el numero de cuenta en el segundo dropdown
            account_input_xpath = '//*[@id="advancedsearchinput"]'
            self.logger.info(f"Seleccionando cuenta {target_account} en dropdown de valor...")
            self.browser_wrapper.select_dropdown_by_value(account_input_xpath, target_account)
            time.sleep(2)

            # 5. Click en boton Add
            add_button_xpath = "//a[contains(@class, 'advanced__search__button')]"
            self.logger.info("Click en boton Add...")
            self.browser_wrapper.click_element(add_button_xpath)
            time.sleep(2)

            # 6. Click en boton Show results
            show_results_xpath = "//button[contains(@class, 'show__result__button')]"
            self.logger.info("Click en boton Show results...")

            # Verificar que el boton no esta deshabilitado
            if self.browser_wrapper.find_element_by_xpath(show_results_xpath, timeout=3000):
                # Verificar si tiene la clase 'disabled'
                button_class = self.browser_wrapper.get_attribute(show_results_xpath, "class")
                if "disabled" not in button_class:
                    self.browser_wrapper.click_element(show_results_xpath)
                    self.logger.info("Esperando resultados...")
                    time.sleep(10)
                else:
                    self.logger.warning("Boton Show results esta deshabilitado, continuando...")

            self.logger.info("Busqueda avanzada configurada exitosamente")
            return True

        except Exception as e:
            self.logger.error(f"Error configurando busqueda avanzada: {str(e)}")
            return False

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de Telus IQ."""
        downloaded_files = []

        # Obtener el BillingCycleDailyUsageFile del billing_cycle
        daily_usage_file = billing_cycle.daily_usage_files[0] if billing_cycle.daily_usage_files else None
        if daily_usage_file:
            self.logger.info(f"Mapeando archivo Daily Usage -> BillingCycleDailyUsageFile ID {daily_usage_file.id}")

        try:
            self.logger.info("=== INICIANDO PROCESO DE EXPORTACION ===")

            # 1. Click en Export View button
            export_view_xpath = (
                '//*[@id="app"]/html/body/div/div/div/div[2]/div[3]/div[1]/div[11]/div[2]/div/div[2]/div/div[2]'
            )
            # XPath alternativo mas especifico
            export_view_alt_xpath = "//div[contains(@class, 'export')]//div[contains(text(), 'Export')]"

            self.logger.info("Buscando boton Export View...")
            if self.browser_wrapper.find_element_by_xpath(export_view_xpath, timeout=5000):
                self.logger.info("Click en Export View button...")
                self.browser_wrapper.click_element(export_view_xpath)
            elif self.browser_wrapper.find_element_by_xpath(export_view_alt_xpath, timeout=3000):
                self.logger.info("Click en Export View button (alternativo)...")
                self.browser_wrapper.click_element(export_view_alt_xpath)
            else:
                self.logger.error("Boton Export View no encontrado")
                return downloaded_files

            time.sleep(3)

            # 2. Generar nombre del reporte: "Daily Usage Report" + fecha mm-dd-yyyy
            current_date = datetime.now()
            report_name = f"Daily Usage Report {current_date.strftime('%m-%d-%Y')}"
            self.logger.info(f"Nombre del reporte: {report_name}")

            # 3. Escribir en el input del modal
            report_input_xpath = '//*[@id="reportname"]'
            if self.browser_wrapper.find_element_by_xpath(report_input_xpath, timeout=5000):
                self.logger.info("Escribiendo nombre del reporte...")
                self.browser_wrapper.clear_and_type(report_input_xpath, report_name)
                time.sleep(1)
            else:
                self.logger.error("Input de nombre de reporte no encontrado")
                return downloaded_files

            # 4. Click en Continue button
            continue_button_xpath = '//*[@id="confirmation__dialog1"]/div/div[2]/a[2]'
            self.logger.info("Click en Continue button...")
            self.browser_wrapper.click_element(continue_button_xpath)
            self.logger.info("Esperando 3 minutos para generacion del reporte...")
            time.sleep(180)

            # 5. Monitorear tabla de resultados y descargar
            # Pasamos el account number para validar BAN en la tabla
            target_account = billing_cycle.account.number
            download_info = self._monitor_results_table_and_download(report_name, daily_usage_file, target_account)

            if download_info:
                downloaded_files.append(download_info)
                self.logger.info(f"Reporte descargado: {download_info.file_name}")
            else:
                self.logger.error("No se pudo descargar el reporte")

            # 6. Reset a pantalla principal
            self._reset_to_main_screen()

            return downloaded_files

        except Exception as e:
            self.logger.error(f"Error en descarga de uso diario: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _monitor_results_table_and_download(
        self, report_name: str, daily_usage_file, target_account: str
    ) -> Optional[FileDownloadInfo]:
        """Monitorea la tabla de resultados y descarga cuando este listo.

        Args:
            report_name: Nombre del reporte a buscar
            daily_usage_file: Archivo de daily usage para mapeo
            target_account: Numero de cuenta (BAN) para validar
        """
        max_attempts = 2  # Maximo 2 intentos (3 min + 3 min = 6 min total)
        attempt = 0

        while attempt < max_attempts:
            try:
                attempt += 1
                self.logger.info(f"Intento {attempt}/{max_attempts} - Verificando tabla de resultados...")

                # Verificar si existe la tabla dinamica
                dynamic_table_xpath = '//*[@id="dynamicTable"]'

                if not self.browser_wrapper.find_element_by_xpath(dynamic_table_xpath, timeout=10000):
                    self.logger.info("Tabla dinamica no encontrada, esperando 3 minutos mas...")
                    time.sleep(180)
                    continue

                self.logger.info("Tabla dinamica encontrada")

                # Buscar la fila correcta: nombre + BAN + fecha mas reciente
                report_row = self._find_best_report_row(report_name, target_account)

                if not report_row:
                    self.logger.info(f"Reporte '{report_name}' con BAN '{target_account}' no encontrado, esperando 3 minutos mas...")
                    time.sleep(180)
                    continue

                self.logger.info(f"Reporte '{report_name}' encontrado en fila {report_row}")

                # Verificar el estado (columna 3 - Status)
                download_link = self._get_download_link_for_report(report_row)

                if download_link:
                    link_text = self.browser_wrapper.get_text(download_link)
                    self.logger.info(f"Estado del reporte: {link_text}")

                    if "Download" in link_text:
                        self.logger.info("Reporte listo para descarga!")

                        # Descargar archivo
                        downloaded_file_path = self.browser_wrapper.expect_download_and_click(
                            download_link, timeout=60000, downloads_dir=self.job_downloads_dir
                        )

                        if downloaded_file_path:
                            actual_filename = os.path.basename(downloaded_file_path)
                            self.logger.info(f"Archivo descargado: {actual_filename}")

                            file_info = FileDownloadInfo(
                                file_id=daily_usage_file.id if daily_usage_file else 1,
                                file_name=actual_filename,
                                download_url="N/A",
                                file_path=downloaded_file_path,
                                daily_usage_file=daily_usage_file,
                            )

                            if daily_usage_file:
                                self.logger.info(
                                    f"MAPEO CONFIRMADO: {actual_filename} -> BillingCycleDailyUsageFile ID {daily_usage_file.id}"
                                )

                            return file_info
                        else:
                            self.logger.error("Error en descarga del archivo")
                            return None

                    elif "In Queue" in link_text or "queue" in link_text.lower():
                        self.logger.info("Reporte en cola, esperando 3 minutos mas...")
                        time.sleep(180)
                        continue
                    else:
                        self.logger.info(f"Estado desconocido: {link_text}, esperando 3 minutos mas...")
                        time.sleep(180)
                        continue
                else:
                    self.logger.info("Enlace de descarga no encontrado, esperando 3 minutos mas...")
                    time.sleep(180)
                    continue

            except Exception as e:
                self.logger.error(f"Error en intento {attempt}: {str(e)}")
                if attempt < max_attempts:
                    time.sleep(180)
                continue

        self.logger.error("Maximo de intentos alcanzado sin poder descargar el reporte")
        return None

    def _find_best_report_row(self, report_name: str, target_account: str) -> Optional[int]:
        """Busca la mejor fila que coincida con el reporte.

        Criterios:
        1. El nombre del reporte debe coincidir (columna 2)
        2. El BAN debe coincidir con target_account O decir "Multiple" (columna 5)
        3. De las coincidencias, elige la con Date generated mas reciente (columna 8)

        La tabla tiene estructura de columnas separadas:
        - Columna 1: vacia (firstColumnId)
        - Columna 2: Report name
        - Columna 3: Status (Download/In Queue)
        - Columna 4: Report type
        - Columna 5: BAN
        - Columna 6: Submitted by
        - Columna 7: Date submitted
        - Columna 8: Date generated
        - Columna 9: vacia (lastColumnId)

        Returns:
            int: Indice de la fila (1-based) o None si no se encuentra
        """
        try:
            self.logger.info(f"Buscando reporte '{report_name}' con BAN '{target_account}'...")

            candidates = []  # Lista de tuplas: (row_index, date_generated_text)

            # Escanear hasta 10 filas buscando coincidencias
            for i in range(1, 11):
                # Obtener nombre del reporte (columna 2)
                name_xpath = (
                    f"//div[contains(@class, 'new__dynamic__table__column')][2]"
                    f"//div[contains(@class, 'new-dynamic-table__table__cell')][{i}]//span"
                )

                if not self.browser_wrapper.find_element_by_xpath(name_xpath, timeout=1000):
                    break  # No hay mas filas

                name_text = self.browser_wrapper.get_text(name_xpath).strip()

                # Verificar si el nombre coincide
                if report_name not in name_text:
                    self.logger.debug(f"Fila {i}: nombre '{name_text}' no coincide")
                    continue

                self.logger.debug(f"Fila {i}: nombre coincide '{name_text}'")

                # Obtener BAN (columna 5)
                ban_xpath = (
                    f"//div[contains(@class, 'new__dynamic__table__column')][5]"
                    f"//div[contains(@class, 'new-dynamic-table__table__cell')][{i}]//span"
                )

                if self.browser_wrapper.find_element_by_xpath(ban_xpath, timeout=1000):
                    ban_text = self.browser_wrapper.get_text(ban_xpath).strip()
                    self.logger.debug(f"Fila {i}: BAN = '{ban_text}'")

                    # Validar BAN: debe ser el account number O "Multiple"
                    if target_account not in ban_text and "Multiple" not in ban_text:
                        self.logger.debug(f"Fila {i}: BAN no coincide (esperado: {target_account})")
                        continue
                else:
                    self.logger.debug(f"Fila {i}: no se pudo obtener BAN")
                    continue

                # Obtener Date generated (columna 8)
                date_xpath = (
                    f"//div[contains(@class, 'new__dynamic__table__column')][8]"
                    f"//div[contains(@class, 'new-dynamic-table__table__cell')][{i}]//span"
                )

                date_text = ""
                if self.browser_wrapper.find_element_by_xpath(date_xpath, timeout=1000):
                    date_text = self.browser_wrapper.get_text(date_xpath).strip()
                    self.logger.debug(f"Fila {i}: Date generated = '{date_text}'")

                # Esta fila es candidata
                candidates.append((i, date_text))
                self.logger.info(f"Fila {i} es candidata: nombre='{name_text}', BAN='{ban_text}', fecha='{date_text}'")

            if not candidates:
                self.logger.warning(f"No se encontraron filas con reporte '{report_name}' y BAN '{target_account}'")
                return None

            if len(candidates) == 1:
                self.logger.info(f"Una sola coincidencia encontrada: fila {candidates[0][0]}")
                return candidates[0][0]

            # Multiples candidatos: elegir el mas reciente por Date generated
            self.logger.info(f"Encontrados {len(candidates)} candidatos, seleccionando el mas reciente...")
            best_row = self._select_most_recent_row(candidates)
            self.logger.info(f"Fila seleccionada (mas reciente): {best_row}")
            return best_row

        except Exception as e:
            self.logger.error(f"Error buscando reporte en tabla: {str(e)}")
            return None

    def _select_most_recent_row(self, candidates: List[Tuple[int, str]]) -> int:
        """Selecciona la fila con la fecha mas reciente.

        Args:
            candidates: Lista de tuplas (row_index, date_text)
                       date_text formato: "Dec 25, 2025 17:37 CST"

        Returns:
            int: Indice de la fila mas reciente
        """
        try:
            parsed_candidates = []

            for row_index, date_text in candidates:
                try:
                    # Parsear fecha: "Dec 25, 2025 17:37 CST"
                    # Remover timezone para parsear
                    date_clean = date_text.replace(" CST", "").replace(" EST", "").replace(" PST", "").strip()
                    parsed_date = datetime.strptime(date_clean, "%b %d, %Y %H:%M")
                    parsed_candidates.append((row_index, parsed_date))
                except ValueError as e:
                    self.logger.warning(f"No se pudo parsear fecha '{date_text}': {e}")
                    # Usar fecha minima si no se puede parsear
                    parsed_candidates.append((row_index, datetime.min))

            # Ordenar por fecha descendente (mas reciente primero)
            parsed_candidates.sort(key=lambda x: x[1], reverse=True)

            # Retornar el indice de la fila mas reciente
            return parsed_candidates[0][0]

        except Exception as e:
            self.logger.error(f"Error seleccionando fila mas reciente: {e}")
            # Fallback: retornar el primer candidato
            return candidates[0][0]

    def _get_download_link_for_report(self, row_index: int) -> Optional[str]:
        """Obtiene el XPath del enlace de descarga para una fila especifica.

        Args:
            row_index: Indice de la fila (1-based)

        Returns:
            str: XPath del enlace de descarga o None si no existe
        """
        try:
            # La columna de status es la tercera columna
            download_link_xpath = (
                f"//div[contains(@class, 'new__dynamic__table__column')][3]"
                f"//div[contains(@class, 'new-dynamic-table__table__cell')][{row_index}]"
                f"//a[contains(@class, 'download-anchor')]"
            )

            if self.browser_wrapper.find_element_by_xpath(download_link_xpath, timeout=3000):
                return download_link_xpath

            # Alternativa: buscar enlace sin clase especifica
            alt_download_xpath = (
                f"//div[contains(@class, 'new__dynamic__table__column')][3]"
                f"//div[contains(@class, 'new-dynamic-table__table__cell')][{row_index}]"
                f"//a"
            )

            if self.browser_wrapper.find_element_by_xpath(alt_download_xpath, timeout=3000):
                return alt_download_xpath

            return None

        except Exception as e:
            self.logger.error(f"Error obteniendo enlace de descarga: {str(e)}")
            return None

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Telus."""
        try:
            self.logger.info("Reseteando a My Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            self.logger.info("Reset completado")
        except Exception as e:
            self.logger.error(f"Error en reset: {str(e)}")

    def get_pool_data(self) -> Dict[str, Optional[int]]:
        """Retorna los datos del pool extraidos durante la navegacion.

        Returns:
            Dict con pool_size y pool_used en bytes
        """
        return {
            "pool_size": self.pool_size,
            "pool_used": self.pool_used,
        }