import logging
import os
import re
import time
from datetime import datetime
from typing import Any, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    FileDownloadInfo,
    PDFInvoiceScraperStrategy,
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class TMobilePDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para T-Mobile con logica de seleccion de periodo."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de billing y encuentra el primer row del account."""
        try:
            self.logger.info("=" * 70)
            self.logger.info("T-MOBILE PDF INVOICE - NAVEGACION A SECCION DE ARCHIVOS")
            self.logger.info("=" * 70)
            self.logger.info(f"Account: {billing_cycle.account.number if billing_cycle.account else 'N/A'}")
            self.logger.info(f"Billing Period: {billing_cycle.end_date.strftime('%B %Y')}")
            self.logger.info("-" * 70)

            self.logger.info("[Step 1/4] Navegando a la seccion de billing...")

            # 1. Click en billing section
            billing_section_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[1]/mat-accordion/mat-panel-title/mat-list-item"
            if not self.browser_wrapper.is_element_visible(billing_section_xpath, timeout=10000):
                error_msg = "FAILED at Step 1: Seccion de billing no encontrada"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

            self.browser_wrapper.click_element(billing_section_xpath)
            time.sleep(3)
            self.logger.info("[Step 1/4] OK - Seccion de billing encontrada")

            # 2. Buscar y llenar el input de cuenta
            self.logger.info("[Step 2/4] Buscando campo de busqueda de cuenta...")
            search_input_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div/div/app-billing/div/app-search/div/mat-form-field/div[1]/div/div[3]/input"
            if not self.browser_wrapper.is_element_visible(search_input_xpath, timeout=10000):
                error_msg = "FAILED at Step 2: Campo de busqueda no encontrado"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

            self.logger.info(f"[Step 2/4] Buscando cuenta: {billing_cycle.account.number}")
            self.browser_wrapper.type_text(search_input_xpath, billing_cycle.account.number)
            time.sleep(1)

            # 3. Presionar Enter
            self.logger.info("[Step 3/4] Ejecutando busqueda...")
            self.browser_wrapper.press_key(search_input_xpath, "Enter")
            time.sleep(5)
            self.logger.info("[Step 3/4] OK - Busqueda ejecutada")

            # 4. Click en el primer row
            self.logger.info("[Step 4/4] Buscando primer row de cuenta...")
            first_row_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-billing/div/section/div[1]/mat-grid-list"
            if not self.browser_wrapper.is_element_visible(first_row_xpath, timeout=10000):
                error_msg = "FAILED at Step 4: Primer row no encontrado"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

            self.browser_wrapper.click_element(first_row_xpath)
            time.sleep(5)
            self.logger.info("[Step 4/4] OK - Primer row seleccionado")

            self.logger.info("-" * 70)
            self.logger.info("SUCCESS: Seccion de facturas PDF encontrada")
            self.logger.info("=" * 70)
            return {"section": "pdf_invoices", "account_number": billing_cycle.account.number}

        except RuntimeError:
            # Reset antes de re-raise para dejar UI limpia para siguiente job
            try:
                self._reset_to_main_screen()
            except:
                pass
            raise
        except Exception as e:
            # Reset antes de raise para dejar UI limpia para siguiente job
            try:
                self._reset_to_main_screen()
            except:
                pass
            error_msg = f"EXCEPTION en _find_files_section: {str(e)}"
            self.logger.error(error_msg)
            import traceback
            self.logger.error(traceback.format_exc())
            raise RuntimeError(error_msg)

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de T-Mobile con seleccion de periodo."""
        downloaded_files = []

        # Mapear BillingCyclePDFFile
        pdf_file = None
        if billing_cycle.pdf_files:
            pdf_file = billing_cycle.pdf_files[0]
            self.logger.info(f"Archivo PDF encontrado: ID {pdf_file.id}")

        try:
            self.logger.info("=== INICIANDO DESCARGA DE FACTURAS PDF T-MOBILE ===")

            # Verificar y cerrar cualquier modal bloqueante
            self._dismiss_blocking_modal()

            # 1. Click en charges tab
            self.logger.info("[Step 1/6] Buscando charges tab...")
            charges_tab_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/mat-tab-group/mat-tab-header/div/div/div/div[2]/div"
            if self.browser_wrapper.is_element_visible(charges_tab_xpath, timeout=10000):
                self.logger.info("[Step 1/6] Haciendo click en charges tab...")
                self.browser_wrapper.click_element(charges_tab_xpath)
                time.sleep(3)
            else:
                self.logger.info("[Step 1/6] Charges tab no encontrado, continuando...")

            # 2. Click en date selector
            self.logger.info("[Step 2/6] Buscando date selector...")
            date_selector_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/div/div/div[1]/mat-form-field/div[1]/div[2]/div/mat-select"
            if not self.browser_wrapper.is_element_visible(date_selector_xpath, timeout=10000):
                self.logger.error("[Step 2/6] FAILED: Date selector no encontrado")
                return downloaded_files

            self.logger.info("[Step 2/6] Abriendo selector de fechas...")
            self.browser_wrapper.click_element(date_selector_xpath)
            time.sleep(3)

            # 3. Seleccionar el periodo mas cercano al billing_cycle.end_date
            self.logger.info("[Step 3/6] Seleccionando periodo de facturacion...")
            selected_option = self._select_best_billing_period(billing_cycle.end_date)
            if not selected_option:
                self.logger.error("[Step 3/6] FAILED: No se pudo seleccionar el periodo de facturacion")
                return downloaded_files
            self.logger.info("[Step 3/6] OK - Periodo seleccionado")

            time.sleep(3)

            # 4. Click en view pdf bill
            self.logger.info("[Step 4/6] Buscando boton view PDF bill...")
            view_pdf_button_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[1]/div/app-digital-billing/div/app-digital-billing-tabs/div/div[2]/button"
            if not self.browser_wrapper.is_element_visible(view_pdf_button_xpath, timeout=10000):
                self.logger.error("[Step 4/6] FAILED: Boton view pdf bill no encontrado")
                return downloaded_files

            self.logger.info("[Step 4/6] Haciendo click en view PDF bill...")
            self.browser_wrapper.click_element(view_pdf_button_xpath)
            time.sleep(5)

            # 5. Click en detailed bill radio button
            self.logger.info("[Step 5/6] Buscando detailed bill radio button...")
            detailed_radio_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[2]/div[2]/div/mat-dialog-container/div/div/download-bill-dialog/mat-dialog-content/mat-radio-group/mat-radio-button[2]/div/div/input"
            if self.browser_wrapper.is_element_visible(detailed_radio_xpath, timeout=10000):
                self.logger.info("[Step 5/6] Seleccionando detailed bill...")
                self.browser_wrapper.click_element(detailed_radio_xpath)
                time.sleep(2)
            else:
                self.logger.info("[Step 5/6] Detailed bill radio button no encontrado, continuando...")

            # 6. Click en download button
            self.logger.info("[Step 6/6] Buscando boton de descarga...")
            download_button_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[2]/div[2]/div/mat-dialog-container/div/div/download-bill-dialog/mat-dialog-actions/button[2]"
            if not self.browser_wrapper.is_element_visible(download_button_xpath, timeout=10000):
                self.logger.error("[Step 6/6] FAILED: Boton de download no encontrado")
                return downloaded_files

            self.logger.info("[Step 6/6] Iniciando descarga...")

            file_path = self.browser_wrapper.expect_download_and_click(
                download_button_xpath, timeout=60000, downloads_dir=self.job_downloads_dir
            )

            if file_path:
                actual_filename = os.path.basename(file_path)
                self.logger.info(f"PDF descargado: {actual_filename}")

                file_info = FileDownloadInfo(
                    file_id=pdf_file.id if pdf_file else 1,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    pdf_file=pdf_file,
                )
                downloaded_files.append(file_info)

                if pdf_file:
                    self.logger.info(f"MAPEO CONFIRMADO: {actual_filename} -> BillingCyclePDFFile ID {pdf_file.id}")
            else:
                self.logger.error("No se pudo descargar el PDF")

            # Reset a pantalla principal
            self._reset_to_main_screen()

            self.logger.info(f"Descarga de PDF completada: {len(downloaded_files)} archivo(s)")
            return downloaded_files

        except Exception as e:
            self.logger.error(f"Error durante descarga de PDF: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _select_best_billing_period(self, target_end_date: datetime) -> bool:
        """Selecciona el periodo de facturacion mas cercano al end_date del billing cycle."""
        try:
            self.logger.info(f"Buscando periodo mas cercano a: {target_end_date}")

            # XPath del panel de opciones
            options_panel_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav-content/div[3]/navapp-microapp-page/div/tfb-billing-root/div/div[2]/div[2]/div/div"

            if not self.browser_wrapper.is_element_visible(options_panel_xpath, timeout=10000):
                self.logger.error("Panel de opciones no encontrado")
                return False

            # Obtener todas las opciones disponibles usando page.query_selector_all
            options = self.browser_wrapper.page.query_selector_all("mat-option")

            if not options:
                self.logger.error("No se encontraron opciones de periodos")
                return False

            best_option = None
            best_match_score = float("inf")

            for option in options:
                try:
                    option_text = option.inner_text().strip()

                    # Saltear opciones especiales
                    if "Current" in option_text or "View historical" in option_text:
                        continue

                    # Extraer fechas del texto (formato: "May 13 - Jun 12")
                    date_match = re.search(r"(\w+)\s+(\d+)\s*-\s*(\w+)\s+(\d+)", option_text)
                    if not date_match:
                        continue

                    start_month, start_day, end_month, end_day = date_match.groups()

                    # Construir fecha aproximada del periodo
                    current_year = target_end_date.year

                    # Mapear nombres de meses
                    month_map = {
                        "Jan": 1,
                        "Feb": 2,
                        "Mar": 3,
                        "Apr": 4,
                        "May": 5,
                        "Jun": 6,
                        "Jul": 7,
                        "Aug": 8,
                        "Sep": 9,
                        "Oct": 10,
                        "Nov": 11,
                        "Dec": 12,
                    }

                    if end_month in month_map:
                        end_month_num = month_map[end_month]

                        # Si el mes de fin es menor que el mes de inicio, el periodo cruza anos
                        period_year = current_year
                        if end_month_num < month_map.get(start_month, 1):
                            period_year = current_year + 1

                        period_end_date = datetime(period_year, end_month_num, int(end_day))

                        # Calcular que tan cerca esta esta fecha del target
                        date_diff = abs((period_end_date - target_end_date).days)

                        self.logger.info(f"Opcion: {option_text} | End: {period_end_date} | Diff: {date_diff} dias")

                        if date_diff < best_match_score:
                            best_match_score = date_diff
                            best_option = option

                except Exception as e:
                    self.logger.debug(f"Error procesando opcion: {str(e)}")
                    continue

            if best_option:
                option_text = best_option.inner_text().strip()
                self.logger.info(f"Seleccionando mejor opcion: {option_text} (diferencia: {best_match_score} dias)")
                best_option.click()
                return True
            else:
                self.logger.error("No se encontro una opcion valida")
                return False

        except Exception as e:
            self.logger.error(f"Error seleccionando periodo: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def _dismiss_blocking_modal(self) -> bool:
        """Detecta y cierra cualquier modal bloqueante (error o confirmación)."""
        try:
            modal_xpath = "//mat-dialog-container"
            backdrop_xpath = "//div[contains(@class, 'cdk-overlay-backdrop-showing')]"

            # Verificar si hay un modal bloqueante
            if not self.browser_wrapper.is_element_visible(backdrop_xpath, timeout=1000):
                return True  # No hay modal bloqueante

            self.logger.warning("[MODAL] Detectado modal bloqueante, intentando cerrar...")

            # Detectar si es un modal de error "Something went wrong"
            error_modal_xpath = "//mat-dialog-container//span[contains(text(), 'Something went wrong')]"
            reload_button_xpath = "//mat-dialog-container//button[contains(., 'Reload reports')]"
            close_button_xpath = "//mat-dialog-container//button[contains(@class, 'close')]"
            close_icon_xpath = "//mat-dialog-container//mat-icon[contains(text(), 'close')]"

            # Si es un modal de error, hacer click en "Reload reports" o cerrar
            if self.browser_wrapper.is_element_visible(error_modal_xpath, timeout=2000):
                self.logger.warning("[MODAL] Modal de error 'Something went wrong' detectado")

                # Intentar click en "Reload reports"
                if self.browser_wrapper.is_element_visible(reload_button_xpath, timeout=2000):
                    self.logger.info("[MODAL] Clickeando 'Reload reports'...")
                    self.browser_wrapper.click_element(reload_button_xpath)
                    time.sleep(3)

                    # Esperar a que la página recargue
                    self.logger.info("[MODAL] Esperando recarga de página (30s)...")
                    time.sleep(30)
                    return True

            # Intentar cerrar con botón close
            if self.browser_wrapper.is_element_visible(close_button_xpath, timeout=1000):
                self.logger.info("[MODAL] Cerrando con botón close...")
                self.browser_wrapper.click_element(close_button_xpath)
                time.sleep(2)
                if not self.browser_wrapper.is_element_visible(backdrop_xpath, timeout=1000):
                    return True

            # Intentar cerrar con icono close
            if self.browser_wrapper.is_element_visible(close_icon_xpath, timeout=1000):
                self.logger.info("[MODAL] Cerrando con icono close...")
                self.browser_wrapper.click_element(close_icon_xpath)
                time.sleep(2)
                if not self.browser_wrapper.is_element_visible(backdrop_xpath, timeout=1000):
                    return True

            # Intentar con ESC
            self.logger.info("[MODAL] Intentando cerrar con ESC...")
            for _ in range(5):
                self.browser_wrapper.page.keyboard.press("Escape")
                time.sleep(0.5)

            time.sleep(2)
            if not self.browser_wrapper.is_element_visible(backdrop_xpath, timeout=1000):
                return True

            # Último recurso: refrescar la página
            self.logger.warning("[MODAL] No se pudo cerrar modal, refrescando página...")
            self.browser_wrapper.page.reload()
            time.sleep(10)
            return True

        except Exception as e:
            self.logger.error(f"[MODAL] Error manejando modal bloqueante: {str(e)}")
            return False

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de T-Mobile dashboard."""
        try:
            self.logger.info("Reseteando a T-Mobile dashboard...")
            self.browser_wrapper.goto("https://tfb.t-mobile.com/apps/tfb_billing/dashboard")
            time.sleep(5)
            self.logger.info("Reset completado")
        except Exception as e:
            self.logger.error(f"Error en reset: {str(e)}")
