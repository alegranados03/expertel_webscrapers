import calendar
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
from web_scrapers.domain.entities.session import Credentials

class ATTMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para AT&T con 7 reportes específicos."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)
        self.report_dictionary = {
            "wireless_charges": None,
            "feature_report": None,
            "usage_details": None,
            "fees_and_taxes": None,
            "monthly_charges": None,
            "device_installment": None,
            "upgrade_and_inventory": None,
        }
        self._current_credentials: Optional[Credentials] = None

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos mensuales en el portal de AT&T."""
        return self._find_files_section_with_retry(config, billing_cycle, max_retries=1)

    def _find_files_section_with_retry(
        self, config: ScraperConfig, billing_cycle: BillingCycle, max_retries: int = 1
    ) -> Optional[Any]:
        """Busca la sección de archivos con reintento automático en caso de error."""
        for attempt in range(max_retries + 1):
            try:
                print(f"🔍 Buscando sección de archivos AT&T (intento {attempt + 1}/{max_retries + 1})")

                # 1. Click en billing header y esperar 2 minutos
                billing_header_xpath = "/html/body/div[1]/div/ul/li[3]/a"
                print("🏦 Haciendo clic en Billing header...")
                self.browser_wrapper.click_element(billing_header_xpath)
                time.sleep(120)  # Esperar 2 minutos como especificado

                # 2. Click en reports tab
                reports_tab_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[4]/a/span"
                print("📊 Haciendo clic en Reports tab...")
                self.browser_wrapper.click_element(reports_tab_xpath)
                time.sleep(3)

                # 3. Click en detail option
                detail_option_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[4]/ul/li[3]/a"
                print("📋 Haciendo clic en Detail option...")
                self.browser_wrapper.click_element(detail_option_xpath)
                time.sleep(5)

                # 4. Verificar que encontramos la sección correcta
                charges_tab_section_xpath = "/html/body/div[1]/main/div[2]/form/div/div[1]/ul/li[1]/a/span"
                if self.browser_wrapper.is_element_visible(charges_tab_section_xpath, timeout=10000):
                    # Verificar que el texto sea "Charges and usage"
                    section_text = self.browser_wrapper.get_text(charges_tab_section_xpath)
                    if section_text and "Charges and usage" in section_text:
                        print("✅ Sección de reportes encontrada exitosamente")
                        return {"section": "monthly_reports", "ready_for_download": True}
                    else:
                        print(f"⚠️ Texto de sección no coincide: {section_text}")
                        continue
                else:
                    print("❌ No se encontró la sección de reportes")
                    continue

            except Exception as e:
                print(f"❌ Error en intento {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    continue

        print("❌ No se pudo encontrar la sección de archivos después de todos los intentos")
        return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los 7 archivos mensuales de AT&T."""
        downloaded_files = []

        # Mapeo de slugs a nombres de reportes y configuraciones
        slug_to_report_config = {
            "wireless_charges": {
                "name": "All wireless charges and usage",
                "text_to_verify": "All wireless charges and usage",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div[3]/div/div[2]/ul/li[1]/button",
                "tab": "charges",
            },
            "feature_report": {
                "name": "Features",
                "text_to_verify": "Features",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div[1]/div/div[2]/ul/li[7]/button",
                "tab": "charges",
            },
            "usage_details": {
                "name": "All data export - usage details",
                "text_to_verify": "All data export - usage details",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div[2]/div/div[2]/ul/li[1]/button",
                "tab": "charges",
            },
            "fees_and_taxes": {
                "name": "Surcharges, fees and taxes",
                "text_to_verify": "Surcharges, fees and taxes",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div[1]/div/div[2]/ul/li[9]/button",
                "tab": "charges",
            },
            "monthly_charges": {
                "name": "Monthly charges",
                "text_to_verify": "Monthly charges",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div[1]/div/div[2]/ul/li[8]/button",
                "tab": "charges",
            },
            "device_installment": {
                "name": "Device installment details",
                "text_to_verify": "Device installment details",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div[1]/div/div[2]/ul/li[8]/button",
                "tab": "charges",
            },
            "upgrade_and_inventory": {
                "name": "Upgrade eligibility and inventory",
                "text_to_verify": "Upgrade eligibility and inventory",
                "section_xpath": "/html/body/div[1]/main/div[2]/form/div/div[2]/div[3]/div/div/div[2]/ul/li[3]/button",
                "tab": "unbilled",
            },
        }

        # Mapear BillingCycleFiles por slug del carrier_report para asociación exacta
        billing_cycle_file_map = {}
        if billing_cycle.billing_cycle_files:
            for bcf in billing_cycle.billing_cycle_files:
                if bcf.carrier_report and bcf.carrier_report.slug:
                    slug = bcf.carrier_report.slug
                    billing_cycle_file_map[slug] = bcf
                    print(f"📋 Mapeado BillingCycleFile: {slug} -> ID {bcf.id}")

        try:
            # 1. Click en charges tab
            charges_tab_xpath = "/html/body/div[1]/main/div[2]/form/div/div[1]/ul/li[1]/a"
            print("💰 Haciendo clic en Charges tab...")
            self.browser_wrapper.click_element(charges_tab_xpath)
            time.sleep(3)

            # 2. Configurar fecha
            self._configure_date_range(billing_cycle)

            # 3. Procesar reportes de la pestaña Charges
            charges_reports = [slug for slug, config in slug_to_report_config.items() if config["tab"] == "charges"]
            for slug in charges_reports:
                self._download_single_report(
                    slug, slug_to_report_config[slug], billing_cycle_file_map, downloaded_files
                )

            # 4. Cambiar a pestaña Unbilled Usage
            print("\n📱 Cambiando a pestaña Unbilled Usage...")
            unbilled_tab_xpath = "/html/body/div[1]/main/div[2]/form/div/div[1]/ul/li[3]/a"
            self.browser_wrapper.click_element(unbilled_tab_xpath)
            time.sleep(3)

            # 5. Procesar reportes de la pestaña Unbilled
            unbilled_reports = [slug for slug, config in slug_to_report_config.items() if config["tab"] == "unbilled"]
            for slug in unbilled_reports:
                self._download_single_report(
                    slug, slug_to_report_config[slug], billing_cycle_file_map, downloaded_files
                )

            print(f"\n✅ Descarga completada. Total archivos: {len(downloaded_files)}")
            return downloaded_files

        except Exception as e:
            print(f"❌ Error durante descarga de archivos: {str(e)}")
            return downloaded_files

    def _configure_date_range(self, billing_cycle: BillingCycle):
        """Configura el rango de fechas basado en el billing cycle."""
        try:
            print(f"📅 Configurando fecha para período: {billing_cycle.end_date}")

            # 1. Click en date dropdown
            date_dropdown_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/button"
            self.browser_wrapper.click_element(date_dropdown_xpath)
            time.sleep(2)

            # 2. Click en option dropdown
            option_dropdown_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/div/div/div[2]/div/div[1]/select"
            self.browser_wrapper.click_element(option_dropdown_xpath)
            time.sleep(1)

            # 3. Determinar la opción correcta basada en end_date
            end_date = billing_cycle.end_date
            month_name = calendar.month_name[end_date.month]
            year = end_date.year
            option_text = f"{month_name} {year} bills"

            print(f"🔍 Buscando opción: {option_text}")

            # 4. Seleccionar la opción correcta
            select_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/div/div/div[2]/div/div[1]/select"
            self.browser_wrapper.select_dropdown_option(select_xpath, option_text)
            time.sleep(1)

            # 5. Apply date changes
            apply_button_xpath = "/html/body/div[1]/main/div[2]/form/div/div[2]/div[1]/div[2]/div/div/div/div/div/div[2]/div/div[5]/button"
            print("✅ Aplicando cambios de fecha...")
            self.browser_wrapper.click_element(apply_button_xpath)
            time.sleep(5)

        except Exception as e:
            print(f"⚠️ Error configurando fecha: {str(e)}")

    def _download_single_report(
        self, slug: str, report_config: dict, billing_cycle_file_map: dict, downloaded_files: list
    ):
        """Descarga un reporte individual."""
        try:
            print(f"\n📊 Procesando reporte: {report_config['name']} (slug: {slug})")

            # 1. Click en la sección del reporte
            section_xpath = report_config["section_xpath"]

            # Verificar que el texto del botón coincida
            if self.browser_wrapper.is_element_visible(section_xpath, timeout=5000):
                button_text = self.browser_wrapper.get_text(section_xpath)
                if button_text and report_config["text_to_verify"] in button_text:
                    print(f"✅ Texto verificado: '{button_text}'")
                    self.browser_wrapper.click_element(section_xpath)
                    time.sleep(3)
                else:
                    print(
                        f"⚠️ Texto no coincide para {slug}. Esperado: '{report_config['text_to_verify']}', Encontrado: '{button_text}'. Saltando..."
                    )
                    return
            else:
                print(f"⚠️ Sección no encontrada para {slug}. Saltando...")
                return

            # 2. Click en download report
            download_button_xpath = "/html/body/div[1]/main/div[2]/form/div[2]/div[2]/div/div/button[2]"
            print("⬇️ Haciendo clic en Download Report...")
            self.browser_wrapper.click_element(download_button_xpath)
            time.sleep(2)

            # 3. Click en CSV option
            csv_option_xpath = "/html/body/div[1]/div[3]/div/div/div[2]/form/div[1]/div/div/fieldset/label[2]"
            print("📄 Seleccionando opción CSV...")
            self.browser_wrapper.click_element(csv_option_xpath)
            time.sleep(1)

            # 4. Click en OK button
            ok_button_xpath = "/html/body/div[1]/div[3]/div/div/div[3]/button[1]"
            print("✅ Haciendo clic en OK...")
            self.browser_wrapper.click_element(ok_button_xpath)

            # 5. Esperar descarga y aplicar renombre de archivo
            time.sleep(10)  # Esperar descarga

            # Generar nombre de archivo con fecha
            current_date = datetime.now().strftime("%Y-%m-%d")
            renamed_filename = f"{slug}_{current_date}.csv"

            # Buscar BillingCycleFile correspondiente
            corresponding_bcf = billing_cycle_file_map.get(slug)

            # Crear FileDownloadInfo
            file_download_info = FileDownloadInfo(
                file_id=corresponding_bcf.id if corresponding_bcf else len(downloaded_files) + 1,
                file_name=renamed_filename,
                download_url="N/A",
                file_path=f"{self.job_downloads_dir}/{renamed_filename}",
                billing_cycle_file=corresponding_bcf,
            )
            downloaded_files.append(file_download_info)

            if corresponding_bcf:
                print(
                    f"✅ MAPEO CONFIRMADO: {renamed_filename} -> BillingCycleFile ID {corresponding_bcf.id} (Slug: '{slug}')"
                )
            else:
                print(f"⚠️ Archivo descargado sin mapeo específico de BillingCycleFile")

            # 6. Go back
            go_back_xpath = "/html/body/div[1]/main/div[2]/form/div[1]/div[1]/a"
            print("🔙 Regresando...")
            self.browser_wrapper.click_element(go_back_xpath)
            time.sleep(3)

        except Exception as e:
            print(f"❌ Error descargando reporte {slug}: {str(e)}")

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de AT&T."""
        try:
            print("🔄 Reseteando a pantalla inicial de AT&T...")
            self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("✅ Reset a AT&T completado")
        except Exception as e:
            print(f"❌ Error en reset de AT&T: {str(e)}")


class ATTDailyUsageScraperStrategy(DailyUsageScraperStrategy):
    """Scraper de uso diario para AT&T."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de archivos de uso diario en el portal de AT&T."""
        return self._find_files_section_with_retry(config, billing_cycle, max_retries=1)

    def _find_files_section_with_retry(
        self, config: ScraperConfig, billing_cycle: BillingCycle, max_retries: int = 1
    ) -> Optional[Any]:
        """Busca la sección de archivos de uso diario con reintento automático."""
        for attempt in range(max_retries + 1):
            try:
                print(f"🔍 Buscando sección de uso diario AT&T (intento {attempt + 1}/{max_retries + 1})")

                # 1. Click en reports tab y esperar 1 minuto
                reports_tab_xpath = "/html/body/div[1]/div/ul/li[4]/a"
                print("📊 Haciendo clic en Reports tab...")
                self.browser_wrapper.click_element(reports_tab_xpath)
                time.sleep(60)  # Esperar 1 minuto como especificado

                # 2. Click en reports section y esperar 1 minuto
                reports_section_xpath = "/html/body/div[1]/div/div[17]/div/div[2]/div[1]"
                print("📋 Haciendo clic en Reports section...")
                self.browser_wrapper.click_element(reports_section_xpath)
                time.sleep(60)  # Esperar 1 minuto como especificado

                # 3. Click en internal reports tab
                internal_reports_tab_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[4]/a"
                print("📊 Haciendo clic en Internal reports tab...")
                self.browser_wrapper.click_element(internal_reports_tab_xpath)
                time.sleep(3)

                # 4. Click en summary option
                summary_option_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[4]/ul/li[2]/a"
                print("📋 Haciendo clic en Summary option...")
                self.browser_wrapper.click_element(summary_option_xpath)
                time.sleep(5)

                # 5. Verificar que encontramos la sección correcta
                charges_tab_section_xpath = "/html/body/div[1]/main/form/div[2]/div[3]/div[1]/ul/li[1]/a/span"
                if self.browser_wrapper.is_element_visible(charges_tab_section_xpath, timeout=10000):
                    # Verificar que el texto sea "Charges and usage"
                    section_text = self.browser_wrapper.get_text(charges_tab_section_xpath)
                    if section_text and "Charges and usage" in section_text:
                        print("✅ Sección de uso diario encontrada exitosamente")
                        return {"section": "daily_usage", "ready_for_download": True}
                    else:
                        print(f"⚠️ Texto de sección no coincide: {section_text}")
                        continue
                else:
                    print("❌ No se encontró la sección de uso diario")
                    continue

            except Exception as e:
                print(f"❌ Error en intento {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    continue

        print("❌ No se pudo encontrar la sección de uso diario después de todos los intentos")
        return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de uso diario de AT&T."""
        downloaded_files = []

        # Mapear BillingCycleDailyUsageFile
        daily_usage_file = None
        if billing_cycle.daily_usage_files:
            daily_usage_file = billing_cycle.daily_usage_files[0]
            print(f"📋 Archivo de uso diario encontrado: ID {daily_usage_file.id}")

        try:
            print("📱 Descargando archivo de uso diario...")

            # 1. Click en unbilled usage tab
            unbilled_tab_xpath = "/html/body/div[1]/main/form/div[2]/div[3]/div[1]/ul/li[2]/a"
            print("📱 Haciendo clic en Unbilled usage tab...")
            self.browser_wrapper.click_element(unbilled_tab_xpath)
            time.sleep(3)

            # 2. Click en unbilled usage report section y esperar 1 minuto
            unbilled_report_xpath = (
                "/html/body/div[1]/main/form/div[2]/div[3]/div[2]/div[3]/div/div/div[2]/ul/li/button"
            )
            print("📊 Haciendo clic en Unbilled usage report section...")
            self.browser_wrapper.click_element(unbilled_report_xpath)
            time.sleep(60)  # Esperar 1 minuto como especificado

            # 3. Click en download
            download_button_xpath = "/html/body/div[1]/main/div[2]/form/div[2]/div[2]/div/div/button[4]"
            print("⬇️ Haciendo clic en Download...")
            self.browser_wrapper.click_element(download_button_xpath)
            time.sleep(2)

            # 4. Click en csv option
            csv_option_xpath = "/html/body/div[1]/div[1]/div/div/div[2]/form/div[1]/div/div/fieldset/label[2]"
            print("📄 Seleccionando opción CSV...")
            self.browser_wrapper.click_element(csv_option_xpath)
            time.sleep(1)

            # 5. Click en OK button
            ok_button_xpath = "/html/body/div[1]/div[1]/div/div/div[3]/button[1]"
            print("✅ Haciendo clic en OK...")
            self.browser_wrapper.click_element(ok_button_xpath)
            time.sleep(2)

            # 6. Click en go back (este dispara la descarga)
            go_back_xpath = "/html/body/div[1]/main/div[2]/form/div[1]/div[1]/a"
            print("🔙 Haciendo clic en Go back (disparará descarga)...")
            self.browser_wrapper.click_element(go_back_xpath)

            # 7. Esperar descarga y aplicar renombre de archivo
            time.sleep(10)  # Esperar descarga

            # Generar nombre de archivo con fecha
            current_date = datetime.now().strftime("%Y-%m-%d")
            renamed_filename = f"daily_usage_{current_date}.csv"

            # Crear FileDownloadInfo
            file_download_info = FileDownloadInfo(
                file_id=daily_usage_file.id if daily_usage_file else 1,
                file_name=renamed_filename,
                download_url="N/A",
                file_path=f"{self.job_downloads_dir}/{renamed_filename}",
                billing_cycle_daily_usage_file=daily_usage_file,
            )
            downloaded_files.append(file_download_info)

            if daily_usage_file:
                print(
                    f"✅ MAPEO CONFIRMADO: {renamed_filename} -> BillingCycleDailyUsageFile ID {daily_usage_file.id}"
                )
            else:
                print(f"⚠️ Archivo descargado sin mapeo específico de BillingCycleDailyUsageFile")

            print(f"✅ Descarga de uso diario completada: {renamed_filename}")
            return downloaded_files

        except Exception as e:
            print(f"❌ Error descargando archivos de uso diario: {str(e)}")
            return downloaded_files

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de AT&T."""
        try:
            print("🔄 Reseteando a pantalla inicial de AT&T...")
            self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("✅ Reset a AT&T completado")
        except Exception as e:
            print(f"❌ Error en reset de AT&T: {str(e)}")


class ATTPDFInvoiceScraperStrategy(PDFInvoiceScraperStrategy):
    """Scraper de facturas PDF para AT&T."""

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Busca la sección de facturas PDF en el portal de AT&T."""
        return self._find_files_section_with_retry(config, billing_cycle, max_retries=1)

    def _find_files_section_with_retry(
        self, config: ScraperConfig, billing_cycle: BillingCycle, max_retries: int = 1
    ) -> Optional[Any]:
        """Busca la sección de facturas PDF con reintento automático."""
        for attempt in range(max_retries + 1):
            try:
                print(f"🔍 Buscando sección de facturas PDF AT&T (intento {attempt + 1}/{max_retries + 1})")

                # 1. Click en billing tab y esperar 1 minuto
                billing_tab_xpath = "/html/body/div[1]/div/ul/li[3]/a"
                print("🏦 Haciendo clic en Billing tab...")
                self.browser_wrapper.click_element(billing_tab_xpath)
                time.sleep(60)  # Esperar 1 minuto como especificado

                # 2. Click en bills tab y esperar 30 segundos
                bills_tab_xpath = "/html/body/div[1]/main/div[1]/div/div/div/div/div[3]/ul[1]/li[3]/a"
                print("💰 Haciendo clic en Bills tab...")
                self.browser_wrapper.click_element(bills_tab_xpath)
                time.sleep(30)  # Esperar 30 segundos como especificado

                # 3. Verificar que llegamos a la sección correcta buscando la tabla de resultados
                results_table_xpath = "/html/body/div[1]/main/div[2]/div[3]/div[2]/div/div/div/div[2]/div/table"
                if self.browser_wrapper.is_element_visible(results_table_xpath, timeout=15000):
                    print("✅ Tabla de facturas encontrada exitosamente")
                    return {"section": "pdf_invoices", "ready_for_download": True}
                else:
                    print("❌ No se encontró la tabla de facturas")
                    continue

            except Exception as e:
                print(f"❌ Error en intento {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    continue

        print("❌ No se pudo encontrar la sección de facturas PDF después de todos los intentos")
        return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga las facturas PDF de AT&T."""
        downloaded_files = []

        # Mapear BillingCyclePDFFile
        pdf_file = None
        if billing_cycle.pdf_files:
            pdf_file = billing_cycle.pdf_files[0]
            print(f"📋 Archivo PDF encontrado: ID {pdf_file.id}")

        try:
            print("📄 Descargando factura PDF...")

            # 1. Configurar período de facturación con calendario
            self._configure_billing_period(billing_cycle)

            # 2. Buscar fila específica por account number
            account_number = billing_cycle.account.number
            pdf_row_found = self._find_pdf_row_by_account(account_number)

            if not pdf_row_found:
                print(f"❌ No se encontró fila para account number: {account_number}")
                return downloaded_files

            # 3. Click en standard bill only button para disparar descarga
            standard_bill_button_xpath = (
                "/html/body/div[1]/main/div[2]/div[3]/div[3]/div/div/div[2]/div[1]/div/div/button[1]"
            )
            print("📄 Haciendo clic en Standard Bill Only...")
            self.browser_wrapper.click_element(standard_bill_button_xpath)

            # 4. Esperar descarga
            time.sleep(15)  # Esperar descarga de PDF

            # Generar nombre de archivo con fecha
            current_date = datetime.now().strftime("%Y-%m-%d")
            renamed_filename = f"invoice_{account_number}_{current_date}.pdf"

            # Crear FileDownloadInfo
            file_download_info = FileDownloadInfo(
                file_id=pdf_file.id if pdf_file else 1,
                file_name=renamed_filename,
                download_url="N/A",
                file_path=f"{self.job_downloads_dir}/{renamed_filename}",
                billing_cycle_pdf_file=pdf_file,
            )
            downloaded_files.append(file_download_info)

            if pdf_file:
                print(f"✅ MAPEO CONFIRMADO: {renamed_filename} -> BillingCyclePDFFile ID {pdf_file.id}")
            else:
                print(f"⚠️ Archivo PDF descargado sin mapeo específico de BillingCyclePDFFile")

            print(f"✅ Descarga de factura PDF completada: {renamed_filename}")
            return downloaded_files

        except Exception as e:
            print(f"❌ Error descargando factura PDF: {str(e)}")
            return downloaded_files

    def _configure_billing_period(self, billing_cycle: BillingCycle):
        """Configura el período de facturación usando el calendario desplegable."""
        try:
            print(f"📅 Configurando período de facturación para: {billing_cycle.end_date}")

            # 1. Click en calendar button
            calendar_button_xpath = (
                "/html/body/div[1]/main/div[2]/div[3]/form[2]/div/div/div[1]/div/div[2]/div/div/div/button"
            )
            print("📅 Haciendo clic en Calendar button...")
            self.browser_wrapper.click_element(calendar_button_xpath)
            time.sleep(2)

            # 2. Buscar la opción más cercana basada en end_date
            end_date = billing_cycle.end_date
            month_name = calendar.month_name[end_date.month]
            year = end_date.year
            target_option = f"{month_name} {year}"

            print(f"🔍 Buscando opción de calendario: {target_option}")

            # 3. Buscar dentro de la UL desplegada
            ul_xpath = "/html/body/div[1]/main/div[2]/div[3]/form[2]/div/div/div[1]/div/div[2]/div/div/div/div/ul"
            if self.browser_wrapper.is_element_visible(ul_xpath, timeout=10000):
                # Buscar todas las opciones li dentro de la ul
                li_elements = self.browser_wrapper.page.query_selector_all(f"{ul_xpath}/li")

                for li in li_elements:
                    li_text = li.text_content() or ""
                    if target_option in li_text:
                        print(f"✅ Opción encontrada: {li_text}")
                        li.click()
                        time.sleep(2)
                        break
                else:
                    print(f"⚠️ No se encontró opción exacta para {target_option}, usando primera opción disponible")
                    if li_elements:
                        li_elements[0].click()
                        time.sleep(2)

                # 4. Click en apply button y esperar 1 minuto
                apply_button_xpath = "/html/body/div[1]/main/div[2]/div[3]/form[2]/div/div/div[1]/div/div[3]/button"
                print("✅ Haciendo clic en Apply button...")
                self.browser_wrapper.click_element(apply_button_xpath)
                time.sleep(60)  # Esperar 1 minuto como especificado

            else:
                print("❌ No se pudo encontrar el dropdown de calendario")

        except Exception as e:
            print(f"⚠️ Error configurando período de facturación: {str(e)}")

    def _find_pdf_row_by_account(self, account_number: str) -> bool:
        """Busca una fila específica por account number y verifica que tenga Bill PDF disponible."""
        try:
            print(f"🔍 Buscando fila para account number: {account_number}")

            # Xpath base de la tabla de resultados
            results_table_xpath = "/html/body/div[1]/main/div[2]/div[3]/div[2]/div/div/div/div[2]/div/table"

            if not self.browser_wrapper.is_element_visible(results_table_xpath, timeout=10000):
                print("❌ Tabla de resultados no encontrada")
                return False

            # Buscar todas las filas en tbody
            tbody_rows = self.browser_wrapper.page.query_selector_all(f"{results_table_xpath}/tbody/tr")

            for row in tbody_rows:
                try:
                    # Buscar la columna de Account number (índice 2 basado en la estructura HTML)
                    account_cell = row.query_selector("td:nth-child(3)")  # Account number column
                    if account_cell:
                        cell_text = account_cell.text_content() or ""
                        if account_number in cell_text:
                            print(f"✅ Fila encontrada para account: {account_number}")

                            # Verificar que la columna Bill Documents tenga "Bill PDF"
                            bill_docs_cell = row.query_selector("td:nth-child(14)")  # Bill documents column
                            if bill_docs_cell:
                                bill_docs_text = bill_docs_cell.text_content() or ""
                                if "Bill PDF" in bill_docs_text:
                                    print("✅ Bill PDF disponible, haciendo clic...")

                                    # Buscar el span con "Bill PDF" dentro de la celda y hacer clic
                                    pdf_span = bill_docs_cell.query_selector("span:has-text('Bill PDF')")
                                    if pdf_span:
                                        pdf_span.click()
                                        time.sleep(2)
                                        return True
                                    else:
                                        # Si no hay span, buscar button con "Bill PDF"
                                        pdf_button = bill_docs_cell.query_selector("button")
                                        if pdf_button and "Bill PDF" in (pdf_button.text_content() or ""):
                                            pdf_button.click()
                                            time.sleep(2)
                                            return True
                                else:
                                    print(f"⚠️ Bill PDF no disponible para account {account_number}")
                                    return False
                except Exception as e:
                    print(f"⚠️ Error procesando fila: {str(e)}")
                    continue

            print(f"❌ No se encontró fila para account number: {account_number}")
            return False

        except Exception as e:
            print(f"❌ Error buscando fila por account number: {str(e)}")
            return False

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de AT&T."""
        try:
            print("🔄 Reseteando a pantalla inicial de AT&T...")
            self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            print("✅ Reset a AT&T completado")
        except Exception as e:
            print(f"❌ Error en reset de AT&T: {str(e)}")
