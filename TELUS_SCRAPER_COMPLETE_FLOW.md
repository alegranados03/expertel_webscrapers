# TELUS SCRAPER - FLUJO COMPLETO CON MAPEO AVANZADO DE ARCHIVOS

Este documento describe el comportamiento completo del sistema de scrapers Telus con el nuevo sistema de mapeo avanzado de archivos, integración universal de uploads y funcionalidades de procesamiento de ZIP, incluyendo casos de error y recuperación específicos para el ecosistema Telus.

## ARQUITECTURA DEL SISTEMA TELUS

### Configuración Avanzada del Sistema
```python
from web_scrapers.infrastructure.scrapers.telus_scrapers import TelusFileMapperConfig
from web_scrapers.domain.enums import TelusFileSlug

scraper_types = [
    ScraperType.MONTHLY_REPORTS,
    ScraperType.DAILY_USAGE, 
    ScraperType.PDF_INVOICE
]
credentials = Credentials(id=1, username="usuario@telus.com", password="...", carrier=Carrier.TELUS)
session_manager = SessionManager(browser_type=Navigators.CHROME)
```

### Sistema de Mapeo de Archivos Telus

**TelusFileMapperConfig - Configuración Centralizada**:
```python
class TelusFileMapperConfig:
    # Mapeo de archivos individuales descargados a slugs
    INDIVIDUAL_FILE_MAPPING = {
        "wireless_subscriber_charges": TelusFileSlug.WIRELESS_SUBSCRIBER_CHARGES,
        "wireless_subscriber_usage": TelusFileSlug.WIRELESS_SUBSCRIBER_USAGE,
        "invoice_detail": TelusFileSlug.INVOICE_DETAIL,
        "mobility_device_summary": TelusFileSlug.MOBILITY_DEVICE,
        "wireless_data_usage": TelusFileSlug.WIRELESS_DATA,
        "wireless_usage_voice_per_account": TelusFileSlug.WIRELESS_VOICE,
    }
    
    # Mapeo de archivos dentro del ZIP (configurables)
    ZIP_FILE_MAPPING = {
        "airtime_detail": TelusFileSlug.AIRTIME_DETAIL,
        "individual_detail": TelusFileSlug.INDIVIDUAL_DETAIL,
        "group_summary": TelusFileSlug.GROUP_SUMMARY,
        "summary_of_renewal": TelusFileSlug.SUMMARY_OF_RENEWAL,
    }
    
    # Archivos que se obtienen individualmente (no del ZIP)
    INDIVIDUAL_DOWNLOADS = {
        WIRELESS_SUBSCRIBER_CHARGES, WIRELESS_SUBSCRIBER_USAGE,
        INVOICE_DETAIL, MOBILITY_DEVICE, WIRELESS_DATA, WIRELESS_VOICE
    }
    
    # Archivos que se obtienen del ZIP del details report
    ZIP_EXTRACTIONS = {
        AIRTIME_DETAIL, INDIVIDUAL_DETAIL, GROUP_SUMMARY, SUMMARY_OF_RENEWAL
    }
```

**Ejemplos de Renombrado Automático**:
```
Original: "wireless_subscriber_charges_20241201.csv"
→ Renamed: "telus_wireless_subscriber_charges_20241201.csv"

Original: "airtime_detail_report.csv" (del ZIP)
→ Renamed: "telus_airtime_detail_20241201.csv"

Original: "invoice_detail.xlsx"
→ Renamed: "telus_invoice_detail_20241201.xlsx"
```

---

## AUTENTICACIÓN TELUS - FLUJO COMPLEJO

### 1.1 TelusAuthStrategy - Proceso de Login

**Diferencias Clave con Bell**:
- Multi-step navigation through Telus.com
- Specific "My Telus" portal access required
- Complex XPath selectors for Telus-specific UI elements

**Flujo de Autenticación**:
```
1. Navegar a https://www.telus.com/en
   ↓
2. Click en botón "My Telus" en header
   → XPath: /html[1]/body[1]/div[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[1]/button[1]/span[1]/span[1]
   ↓
3. Click en "My Telus Web" del dropdown
   → XPath: /html[1]/body[1]/div[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[1]/nav[1]/div[1]/ul[1]/li[1]/a[1]
   ↓
4. Llenar campo de email
   → XPath: /html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[1]/div[1]/div[3]/input[1]
   ↓
5. Llenar campo de contraseña
   → XPath: /html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[2]/div[3]/input[1]
   ↓
6. Click en botón de login
   → XPath: /html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[4]/div[1]
   ↓
7. Verificación con avatar menu visible
   → XPath: /html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[3]/button[1]
```

**Proceso de Logout**:
```
1. Click en avatar menu
   → XPath: /html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[3]/button[1]
   ↓
2. Click en logout button del dropdown
   → XPath: /html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[3]/nav[1]/div[1]/ul[1]/li[5]/a[1]
```

---

## SCRAPER 1: TELUS MONTHLY REPORTS CON MAPEO AVANZADO

### 1.1 TelusMonthlyReportsScraperStrategy - Implementación Completa

**Características Avanzadas**:
- **Procesamiento Dual**: ZIP completo + descargas individuales
- **Mapeo Automático**: Asociación con BillingCycleFile
- **Renombrado Inteligente**: Nombres estandarizados automáticos
- **Upload Universal**: Integración con FileUploadService
- **Filtrado Inteligente**: Evita duplicados entre ZIP e individuales

### 1.2 Flujo de `_download_files()` - Proceso Completo

**Navegación y Configuración**:
```
1. Click en billing header
   → XPath: /html[1]/body[1]/div[1]/div[1]/ul[1]/li[2]/a[1]/span[1]
   ↓
2. Click en reports header
   → XPath: /html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[3]/a[1]
   ↓
3. Click en details report
   → XPath: /html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[3]/ul[1]/li[2]/a[1]/span[1]
   ↓
4. Configurar período de facturación
   → _configure_billing_period(billing_cycle)
```

### 1.3 NUEVO: Procesamiento de ZIP del Details Report

**Flujo de Descarga del ZIP**:
```python
def _download_details_report_zip(self, billing_cycle: BillingCycle) -> List[FileDownloadInfo]:
    # 1. Descargar ZIP completo del details report
    download_all_xpath = "/html[1]/body[1]/div[2]/form[1]/div[1]/div[2]/div[1]/button[1]"
    zip_file_path = self.browser_wrapper.expect_download_and_click(download_all_xpath, timeout=30000)
    
    # 2. Extraer archivos del ZIP
    extracted_files = self._extract_zip_files(zip_file_path)
    
    # 3. Procesar archivos extraídos con mapeo
    processed_files = self._process_zip_extracted_files(extracted_files, billing_cycle, base_file_id=1000)
    
    return processed_files
```

**Procesamiento de Archivos ZIP**:
```python
def _process_zip_extracted_files(self, extracted_files: List[str], billing_cycle: BillingCycle, base_file_id: int):
    for file_path in extracted_files:
        original_filename = os.path.basename(file_path)
        
        # Obtener slug basado en el nombre del archivo
        slug = self.file_mapper.get_slug_from_zip_filename(original_filename)
        
        # Solo procesar archivos que necesitamos (no los que se obtienen individualmente)
        if slug in self.file_mapper.INDIVIDUAL_DOWNLOADS:
            continue  # Saltar - se obtiene individualmente
        
        # Generar nombre estandarizado
        new_filename = self.file_mapper.generate_renamed_filename(original_filename, slug, billing_cycle)
        
        # Renombrar archivo
        os.rename(file_path, new_file_path)
        
        # Crear FileDownloadInfo y mapear con BillingCycleFile
        file_info = FileDownloadInfo(...)
        file_info = self._create_billing_cycle_file_mapping(file_info, slug, billing_cycle)
        
        processed_files.append(file_info)
```

### 1.4 Descargas Individuales con Renombrado Automático

**Tipos de Reportes Descargados Individualmente**:
```python
report_types = [
    ("wireless_subscriber_charges", "/html[1]/body[1]/div[2]/form[1]/div[1]/div[3]/div[1]/div[1]/div[2]/ul[1]/li[4]/button[1]"),
    ("wireless_subscriber_usage", "/html[1]/body[1]/div[2]/form[1]/div[1]/div[3]/div[1]/div[1]/div[2]/ul[1]/li[5]/button[1]"),
    ("invoice_detail", "/html[1]/body[1]/div[2]/form[1]/div[1]/div[3]/div[2]/div[1]/div[2]/ul[1]/li[1]/button[1]"),
    ("mobility_device_summary", "/html[1]/body[1]/div[2]/form[1]/div[1]/div[3]/div[11]/div[1]/div[2]/ul[1]/li[1]/button[1]"),
    ("wireless_data_usage", "/html[1]/body[1]/div[2]/form[1]/div[1]/div[3]/div[21]/div[1]/div[2]/ul[1]/li[1]/button[1]"),
]
```

**Proceso de Descarga Individual con Mapeo**:
```python
def _download_single_report(self, report_name: str, report_xpath: str, billing_cycle: BillingCycle, file_id: int):
    # 1. Descargar archivo
    downloaded_file_path = browser_wrapper.expect_download_and_click(ok_xpath, timeout=30000)
    
    # 2. === RENOMBRADO AUTOMÁTICO Y MAPEO ===
    # Obtener slug basado en el nombre del reporte
    slug = self.file_mapper.get_slug_from_individual_name(report_name)
    
    # Generar nombre estandarizado
    original_name = os.path.basename(downloaded_file_path)
    new_filename = self.file_mapper.generate_renamed_filename(original_name, slug, billing_cycle)
    new_file_path = os.path.join(os.path.dirname(downloaded_file_path), new_filename)
    
    # Renombrar archivo
    os.rename(downloaded_file_path, new_file_path)
    
    # Crear FileDownloadInfo
    file_info = FileDownloadInfo(file_name=new_filename, file_path=new_file_path, ...)
    
    # Mapear con BillingCycleFile
    file_info = self._create_billing_cycle_file_mapping(file_info, slug, billing_cycle)
    
    return file_info
```

### 1.5 Mapeo con BillingCycleFile

**Creación de Asociaciones**:
```python
def _create_billing_cycle_file_mapping(self, file_info: FileDownloadInfo, slug: str, billing_cycle: BillingCycle):
    # Crear CarrierReport basado en el slug
    carrier_report = CarrierReport(
        id=hash(slug) % 1000000,
        name=slug.replace("_", " ").title(),
        slug=slug,
        carrier="telus",
        description=f"Telus {slug.replace('_', ' ').title()} Report",
        active=True
    )
    
    # Crear BillingCycleFile
    billing_cycle_file = BillingCycleFile(
        id=file_info.file_id,
        billing_cycle=billing_cycle,
        carrier_report=carrier_report,
        file_name=file_info.file_name,
        file_path=file_info.file_path,
        file_size=file_info.file_size,
        download_url=file_info.download_url,
        status="ready"
    )
    
    # Actualizar FileDownloadInfo con el mapeo
    file_info.billing_cycle_file = billing_cycle_file
    
    return file_info
```

### 1.6 Summary Reports - Sección Adicional

**Navegación a Summary Reports**:
```
1. Volver a reports header
2. Click en summary reports
   → XPath: /html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[3]/ul[1]/li[1]/a[1]/span[1]
3. Descargar wireless usage voice per account report
   → XPath: /html[1]/body[1]/form[1]/div[2]/div[3]/div[3]/div[18]/div[1]/div[2]/ul[1]/li[1]/button[1]
```

**Estado Final del Scraper 1**:
```
✅ Archivos procesados (ZIP + Individuales):
   📦 Del ZIP: airtime_detail, individual_detail, group_summary, summary_of_renewal
   📄 Individuales: wireless_subscriber_charges, wireless_subscriber_usage, invoice_detail, mobility_device_summary, wireless_data_usage, wireless_usage_voice_per_account
📝 Todos renombrados automáticamente: telus_{slug}_{timestamp}.{ext}
🔗 Todos mapeados con BillingCycleFile
🌐 Upload automático a API externa completado
📊 Reset a My Telus dashboard
📊 Sesión activa mantenida
```

---

## SCRAPER 2: TELUS DAILY USAGE CON MAPEO

### 2.1 TelusDailyUsageScraperStrategy - Sistema Telus IQ Avanzado

**Nuevas Características**:
- **Mapeo con BillingCycleDailyUsageFile**: Asociación específica para uso diario
- **Renombrado Automático**: Nombres estandarizados con timestamps
- **Upload Universal**: Integración con FileUploadService para daily_usage

### 2.2 Flujo de `_download_files()` - Sistema de Cola con Mapeo

**Export Process con Mapeo**:
```python
def _download_files(self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle):
    # Navegación estándar a Telus IQ...
    
    downloaded_file_path = self.browser_wrapper.expect_download_and_click(download_link_xpath, timeout=30000)
    
    if downloaded_file_path:
        # === RENOMBRADO Y MAPEO PARA DAILY USAGE ===
        original_name = os.path.basename(downloaded_file_path)
        slug = "daily_usage"  # Slug fijo para uso diario
        new_filename = self.file_mapper.generate_renamed_filename(original_name, slug, billing_cycle)
        new_file_path = os.path.join(os.path.dirname(downloaded_file_path), new_filename)
        
        # Renombrar archivo
        os.rename(downloaded_file_path, new_file_path)
        
        # Crear FileDownloadInfo
        file_info = FileDownloadInfo(file_name=new_filename, file_path=new_file_path, ...)
        
        # Mapear con BillingCycleDailyUsageFile
        file_info = self._create_daily_usage_file_mapping(file_info, slug, billing_cycle)
        
        return [file_info]
```

### 2.3 Mapeo con BillingCycleDailyUsageFile

**Creación de Daily Usage Mapping**:
```python
def _create_daily_usage_file_mapping(self, file_info: FileDownloadInfo, slug: str, billing_cycle: BillingCycle):
    # Crear BillingCycleDailyUsageFile
    daily_usage_file = BillingCycleDailyUsageFile(
        id=file_info.file_id,
        billing_cycle=billing_cycle,
        file_name=file_info.file_name,
        file_path=file_info.file_path,
        file_size=file_info.file_size,
        download_url=file_info.download_url,
        status="ready",
        report_type=slug
    )
    
    # Actualizar FileDownloadInfo con el mapeo
    file_info.daily_usage_file = daily_usage_file
    
    return file_info
```

**Estado Final del Scraper 2**:
```
✅ 1 archivo descargado y mapeado:
   📄 telus_daily_usage_20241201.csv
🔗 Mapeado con BillingCycleDailyUsageFile
🌐 Upload automático a endpoint daily_usage
📊 Tiempo típico: 2-8 minutos (incluyendo generación)
```

---

## SCRAPER 3: TELUS PDF INVOICE CON MAPEO

### 3.1 TelusPDFInvoiceScraperStrategy - PDF Processing Avanzado

**Nuevas Características**:
- **Mapeo con BillingCyclePDFFile**: Asociación específica para PDFs
- **Renombrado Inteligente**: Nombres basados en fechas de facturación
- **Upload Universal**: Integración con FileUploadService para pdf_invoice

### 3.2 Flujo de `_download_files()` - PDF con Mapeo

**Descarga y Mapeo de PDF**:
```python
def _download_files(self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle):
    # Navegación y configuración estándar...
    
    downloaded_file_path = browser_wrapper.expect_download_and_click(pdf_button_xpath, timeout=30000)
    
    if downloaded_file_path:
        # === RENOMBRADO Y MAPEO PARA PDF ===
        original_name = os.path.basename(downloaded_file_path)
        slug = "pdf_invoice"  # Slug fijo para PDF
        new_filename = self.file_mapper.generate_renamed_filename(original_name, slug, billing_cycle)
        new_file_path = os.path.join(os.path.dirname(downloaded_file_path), new_filename)
        
        # Renombrar archivo
        os.rename(downloaded_file_path, new_file_path)
        
        # Crear FileDownloadInfo
        file_info = FileDownloadInfo(file_name=new_filename, file_path=new_file_path, ...)
        
        # Mapear con BillingCyclePDFFile
        file_info = self._create_pdf_file_mapping(file_info, slug, billing_cycle)
        
        return [file_info]
```

### 3.3 Mapeo con BillingCyclePDFFile

**Creación de PDF Mapping**:
```python
def _create_pdf_file_mapping(self, file_info: FileDownloadInfo, slug: str, billing_cycle: BillingCycle):
    # Crear BillingCyclePDFFile
    pdf_file = BillingCyclePDFFile(
        id=file_info.file_id,
        billing_cycle=billing_cycle,
        file_name=file_info.file_name,
        file_path=file_info.file_path,
        file_size=file_info.file_size,
        download_url=file_info.download_url,
        status="ready",
        invoice_type=slug
    )
    
    # Actualizar FileDownloadInfo con el mapeo
    file_info.pdf_file = pdf_file
    
    return file_info
```

**Estado Final del Scraper 3**:
```
✅ 1 archivo PDF descargado y mapeado:
   📄 telus_pdf_invoice_20241201.pdf
🔗 Mapeado con BillingCyclePDFFile
🌐 Upload automático a endpoint pdf_invoice
📊 Selección automática del PDF más cercano
📊 Tiempo típico: 5-8 minutos
```

---

## INTEGRACIÓN UNIVERSAL DE UPLOADS

### Configuración de API Externa

**Variables de Entorno Requeridas**:
```env
API_BASE_URL=https://api.expertel.com
API_TOKEN=your_api_bearer_token
```

**Endpoints Utilizados por Telus**:
```
Monthly Reports: /api/v1/accounts/billing-cycles/{cycle_id}/files/{file_id}/upload-file/
Daily Usage: /api/v1/accounts/billing-cycles/{cycle_id}/daily-usage/
PDF Invoice: /api/v1/accounts/billing-cycles/{cycle_id}/pdf-invoice/
```

### Upload Automático

**Proceso de Upload Universal**:
```python
# Todos los scrapers Telus heredan este método
def _upload_files_to_endpoint(self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle):
    upload_service = FileUploadService()
    
    # Determinar tipo de upload basado en la clase
    upload_type = self._get_upload_type()  # 'monthly', 'daily_usage', 'pdf_invoice'
    
    return upload_service.upload_files_batch(
        files=files,
        billing_cycle=billing_cycle,
        upload_type=upload_type,
        additional_data=None  # Solo enviamos el archivo
    )
```

**Logs de Upload**:
```
📤 Enviando 8 archivo(s) de tipo: monthly
📁 Archivo 1/8: telus_wireless_subscriber_charges_20241201.csv
📤 Enviando archivo reporte mensual: telus_wireless_subscriber_charges_20241201.csv
🔗 URL: https://api.expertel.com/api/v1/accounts/billing-cycles/123/files/456/upload-file/
✅ Archivo telus_wireless_subscriber_charges_20241201.csv enviado exitosamente
📊 RESUMEN DE ENVÍO:
   ✅ Exitosos: 8/8
   ❌ Fallidos: 0/8
```

---

## CASOS DE ERROR Y RECUPERACIÓN AVANZADOS

### Caso 1: Error en Procesamiento de ZIP

**Escenario**: ZIP corrupto o archivos no extraíbles

**Detección y Recuperación**:
```python
def _download_details_report_zip(self, billing_cycle: BillingCycle):
    try:
        # Extraer archivos del ZIP
        extracted_files = self._extract_zip_files(zip_file_path)
        if not extracted_files:
            print("❌ No se pudieron extraer archivos del ZIP")
            return []
        
        # Procesar archivos extraídos
        processed_files = self._process_zip_extracted_files(extracted_files, billing_cycle, base_file_id=1000)
        
    except Exception as e:
        print(f"❌ Error descargando ZIP del details report: {str(e)}")
        # Continuar con descargas individuales solamente
        return []
```

### Caso 2: Error en Mapeo de Archivos

**Escenario**: Archivo no mapeado o slug no encontrado

**Manejo**:
```python
def _process_zip_extracted_files(self, extracted_files: List[str], billing_cycle: BillingCycle, base_file_id: int):
    for file_path in extracted_files:
        slug = self.file_mapper.get_slug_from_zip_filename(original_filename)
        
        if not slug:
            print(f"⚠️ No se encontró mapeo para archivo ZIP: {original_filename}")
            continue  # Saltar archivo no mapeado
        
        # Continuar procesamiento...
```

### Caso 3: Error en Upload de Archivos

**Escenario**: Falla en upload a API externa

**Recuperación**:
```python
def upload_files_batch(self, files: List[FileDownloadInfo], billing_cycle: BillingCycle, upload_type: str):
    success_count = 0
    total_files = len(files)
    
    for file_info in files:
        if self._upload_single_file(file_info, billing_cycle, upload_type):
            success_count += 1
        # Continuar con siguientes archivos aunque fallen algunos
    
    print(f"📊 RESUMEN DE ENVÍO:")
    print(f"   ✅ Exitosos: {success_count}/{total_files}")
    print(f"   ❌ Fallidos: {total_files - success_count}/{total_files}")
    
    return success_count == total_files
```

---

## MONITOREO Y LOGGING AVANZADO

### Mensajes de Estado de Mapeo

**Renombrado de Archivos**:
```
"📝 Archivo renombrado: wireless_subscriber_charges_20241201.csv -> telus_wireless_subscriber_charges_20241201.csv"
"📝 Archivo ZIP renombrado: airtime_detail_report.csv -> telus_airtime_detail_20241201.csv"
```

**Mapeo de Entidades**:
```
"🔗 Archivo mapeado: telus_wireless_subscriber_charges_20241201.csv -> wireless_subscriber_charges"
"🔗 Archivo de uso diario mapeado: telus_daily_usage_20241201.csv -> daily_usage"
"🔗 Archivo PDF mapeado: telus_pdf_invoice_20241201.pdf -> pdf_invoice"
```

**Procesamiento de ZIP**:
```
"📦 Iniciando descarga del ZIP completo del details report..."
"📦 ZIP descargado: details_report_20241201.zip"
"📁 Extraídos 10 archivos del ZIP"
"📁 Procesando archivo extraído: airtime_detail_report.csv"
"⏭️ Saltando wireless_subscriber_charges.csv - se obtiene individualmente"
"✅ Procesamiento del ZIP completado: 4 archivos mapeados"
```

**Upload Universal**:
```
"📤 Enviando 8 archivo(s) de tipo: monthly"
"📤 Enviando archivo reporte mensual: telus_wireless_subscriber_charges_20241201.csv"
"🔗 URL: https://api.expertel.com/api/v1/accounts/billing-cycles/123/files/456/upload-file/"
"✅ Archivo telus_wireless_subscriber_charges_20241201.csv enviado exitosamente"
```

---

## EJEMPLO DE USO COMPLETO

### Ejecución del Sistema Completo

**Ver archivo**: `examples/telus_system_example.py`

**Ejemplo de Uso**:
```python
from examples.telus_system_example import main

# Configurar variables de entorno
os.environ["TELUS_USERNAME"] = "usuario@telus.com"
os.environ["TELUS_PASSWORD"] = "password"
os.environ["API_BASE_URL"] = "https://api.expertel.com"
os.environ["API_TOKEN"] = "your_api_token"

# Ejecutar demostración completa
main()
```

**Salida Esperada**:
```
🍁 EXPERTEL WEB SCRAPERS - SISTEMA TELUS
📋 Demostración completa del sistema de scrapers Telus
🔗 Con mapeo avanzado de archivos y integración API

📊 EJECUCIÓN DE SCRAPER - REPORTES MENSUALES
📦 Descargando ZIP del details report...
📄 Descargando archivos individuales...
🔄 Procesando y mapeando archivos...
✅ Scraper ejecutado exitosamente!
   📁 Archivos procesados: 8
   🌐 Upload automático completado

📱 EJECUCIÓN DE SCRAPER - USO DIARIO
⏳ Generando reporte (puede tomar varios minutos)...
📊 Monitoreando cola de generación...
✅ Scraper de uso diario completado!
   📁 Archivos descargados: 1

📄 EJECUCIÓN DE SCRAPER - FACTURAS PDF
🔍 Buscando facturas disponibles...
📅 Seleccionando período más cercano...
✅ Scraper de PDF completado!
   📄 PDFs descargados: 1

📊 RESUMEN DE EJECUCIÓN
   • Scrapers ejecutados: 3
   • Exitosos: 3
   • Fallidos: 0
   • Tasa de éxito: 100.0%
```

---

## INTEGRACIÓN CON SISTEMA PRINCIPAL

### Compatibilidad Total con Arquitectura

**Factory Pattern Integration**:
```python
(Carrier.TELUS, ScraperType.MONTHLY_REPORTS): TelusMonthlyReportsScraperStrategy,
(Carrier.TELUS, ScraperType.DAILY_USAGE): TelusDailyUsageScraperStrategy,
(Carrier.TELUS, ScraperType.PDF_INVOICE): TelusPDFInvoiceScraperStrategy,
```

**Template Method Pattern Compliance**:
- `execute()` - Flujo principal común con upload automático
- `_find_files_section()` - Implementación específica Telus
- `_download_files()` - Lógica de descarga con mapeo avanzado
- `_upload_files_to_endpoint()` - Hereda método universal de base class

**Universal Upload Integration**:
- Todas las estrategias Telus heredan `_upload_files_to_endpoint()` de `ScraperBaseStrategy`
- Detección automática de tipo de upload basada en clase
- Integración perfecta con `FileUploadService`

---

Este documento refleja el estado actual del sistema Telus con todas las funcionalidades avanzadas implementadas: mapeo de archivos, renombrado automático, procesamiento de ZIP, asociaciones de entidades, upload universal y manejo robusto de errores.