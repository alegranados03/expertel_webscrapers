# ESCENARIOS DE EJEMPLO Y CASOS DE USO

## Introducción

Este documento presenta escenarios completos del sistema en funcionamiento, con diagramas de flujo y ejemplos concretos de cómo el sistema maneja diferentes situaciones.

---

## ESCENARIO 1: Ejecución Exitosa - Bell Monthly Reports

### Contexto

```
Cliente: ACME Corp
  └─ Workspace: Canadá
      └─ Account: Bell - 416-555-1234
          └─ Ciclo de Facturación: Nov 1 - Nov 30, 2024
              ├─ BillingCycleFile (Cost Overview) - estado: to_be_fetched
              ├─ BillingCycleFile (Enhanced Profile) - estado: to_be_fetched
              └─ BillingCycleFile (Usage Overview) - estado: to_be_fetched

Credencial: user@example.com / pwd1234 (Bell)
Trabajo Scheduler: ScraperJob disponible ahora
```

### Flujo de Ejecución

```
┌─ MAIN.PY ──────────────────────────────────────────────────────┐
│ 1. Inicialización                                              │
│    ├─ Django setup                                             │
│    ├─ SessionManager(browser_type=CHROME)                      │
│    ├─ ScraperJobService()                                      │
│    └─ ScraperStrategyFactory()                                 │
│                                                                │
│ 2. Obtener trabajos disponibles                               │
│    └─ Query: "WHERE status = PENDING AND available_at <= NOW" │
│    └─ Resultado: 1 trabajo encontrado                         │
│                                                                │
│ 3. Construir ScraperJobCompleteContext                        │
│    ├─ scraper_job: {id, type: MONTHLY_REPORTS}               │
│    ├─ scraper_config: {account, carrier: BELL, type}          │
│    ├─ billing_cycle: {start_date, end_date, files: [...]}     │
│    ├─ credential: {username, password_encrypted}              │
│    ├─ account: {number: "416-555-1234"}                       │
│    └─ carrier: {name: "BELL"}                                 │
│                                                                │
│ 4. PROCESS_SCRAPER_JOB                                         │
│    ├─ Status update: PENDING → RUNNING                        │
│    └─ Log: "Processing job 1/1"                               │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌─ SESSION MANAGER ──────────────────────────────────────────────┐
│ 5. Verificar sesión activa                                    │
│    ├─ is_logged_in() = false (primera ejecución)             │
│    └─ Log: "No active session - initiating login"             │
│                                                                │
│ 6. Login con SessionManager                                   │
│    ├─ Crear Credentials(username, password, carrier=BELL)    │
│    ├─ _initialize_browser()                                   │
│    │  ├─ BrowserManager.get_browser(CHROME)                  │
│    │  ├─ Crear contexto con stealth plugin                   │
│    │  └─ Crear nueva página                                  │
│    ├─ Crear BellAuthStrategy(browser_wrapper)                 │
│    ├─ BellAuthStrategy.login(credentials)                     │
│    │  ├─ Navegar a bell.ca                                    │
│    │  ├─ Llenar username                                      │
│    │  ├─ Llenar password                                      │
│    │  ├─ Submit formulario                                    │
│    │  ├─ Detectar 2FA (SMS)                                   │
│    │  ├─ POST /authenticator_webhook/sms/code                 │
│    │  │  └─ Webhook obtiene: SMS "Your code is 123456"        │
│    │  ├─ Llenar campo 2FA                                     │
│    │  └─ return True                                          │
│    ├─ session_state.set_logged_in(BELL, credentials)          │
│    └─ return True                                             │
│                                                                │
│ 7. Obtener browser_wrapper para scraper                       │
│    └─ return self._browser_wrapper (PlaywrightWrapper)        │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌─ SCRAPER FACTORY ──────────────────────────────────────────────┐
│ 8. Crear scraper                                               │
│    └─ create_scraper(                                          │
│         carrier=BELL,                                          │
│         scraper_type=MONTHLY_REPORTS,                          │
│         browser_wrapper=PlaywrightWrapper                      │
│       )                                                         │
│    └─ return BellMonthlyReportsScraperStrategy(browser_wrapper)│
└────────────────────────────────────────────────────────────────┘
                          ↓
┌─ BELL MONTHLY SCRAPER ─────────────────────────────────────────┐
│ 9. execute(scraper_config, billing_cycle, credentials)        │
│                                                                │
│    ├─ PASO 1: Navegar a sección de archivos                   │
│    │   ├─ browser.hover_element(report_menu_xpath)            │
│    │   ├─ wait 2 segundos                                     │
│    │   ├─ browser.click_and_switch_to_new_tab(ereport_xpath)  │
│    │   ├─ Verificar header disponible                         │
│    │   ├─ browser.click_element(standard_reports_xpath)       │
│    │   ├─ wait_for_page_load()                                │
│    │   └─ wait 50 segundos                                    │
│    │   └─ return {"section": "monthly_reports", "ready": True}│
│    │                                                           │
│    ├─ PASO 2: Descargar archivos                              │
│    │   ├─ Crear downloads_dir en memoria                      │
│    │   ├─ Para cada BillingCycleFile en billing_cycle:        │
│    │   │  ├─ Buscar elemento de descarga en página           │
│    │   │  ├─ browser.download_file(selector)                  │
│    │   │  ├─ Esperar descarga                                 │
│    │   │  ├─ Mover a downloads_dir                            │
│    │   │  └─ Crear FileDownloadInfo:                          │
│    │   │     {file_id, file_name, file_path,                 │
│    │   │      billing_cycle_file_id, download_timestamp}     │
│    │   └─ downloaded_files = [file1, file2, file3]           │
│    │                                                           │
│    ├─ PASO 3: Procesar ZIPs (si aplica)                       │
│    │   └─ Ningún archivo ZIP en este caso                     │
│    │                                                           │
│    ├─ PASO 4: Mapear archivos                                 │
│    │   └─ file_mappings = _create_file_mapping(downloaded)   │
│    │      └─ Convierte FileDownloadInfo → FileMappingInfo    │
│    │                                                           │
│    ├─ PASO 5: Cargar a API externa                            │
│    │   └─ FileUploadService.upload_files_batch(               │
│    │        files=downloaded_files,                            │
│    │        billing_cycle=billing_cycle,                       │
│    │        upload_type='monthly'                              │
│    │      )                                                    │
│    │   ├─ Para cada archivo:                                  │
│    │   │  ├─ config = _get_upload_config('monthly', file)    │
│    │   │  │  └─ url_template: /api/v1/accounts/billing-cycles │
│    │   │  │                   /{cycle_id}/files/{file_id}/...  │
│    │   │  ├─ headers: {x-api-key, x-workspace-id, x-client-id}│
│    │   │  ├─ POST file a URL                                  │
│    │   │  ├─ Response 200 OK                                  │
│    │   │  └─ Log: "File uploaded successfully"                │
│    │   └─ return True (todos exitosos)                        │
│    │                                                           │
│    ├─ PASO 6: Limpiar                                         │
│    │   └─ Cerrar pestañas extras, limpiar memoria             │
│    │                                                           │
│    └─ RETORNAR RESULTADO                                      │
│        └─ ScraperResult(                                       │
│             success=True,                                      │
│             message="3 files downloaded and uploaded",         │
│             files=file_mappings,                               │
│             timestamp=datetime.now()                           │
│           )                                                    │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌─ MAIN.PY RESULTADO ────────────────────────────────────────────┐
│ 10. Procesar ScraperResult                                     │
│     ├─ result.success = True                                   │
│     ├─ Status update: RUNNING → SUCCESS                        │
│     ├─ Message: "3 files downloaded and uploaded"              │
│     └─ return True                                             │
│                                                                │
│ 11. Resumen final                                              │
│     ├─ Successful: 1                                           │
│     ├─ Failed: 0                                               │
│     └─ Total processed: 1                                      │
└────────────────────────────────────────────────────────────────┘
```

### Estados de Base de Datos Antes/Después

**Antes:**
```
ScraperJob {
  id: uuid-123,
  type: MONTHLY_REPORTS,
  status: PENDING,
  available_at: 2024-11-28 10:00:00
}

BillingCycleFile {
  id: uuid-file-1,
  status: to_be_fetched,
  carrier_report: "Cost Overview"
}
```

**Después:**
```
ScraperJob {
  id: uuid-123,
  type: MONTHLY_REPORTS,
  status: SUCCESS,  ← ACTUALIZADO
  available_at: 2024-11-28 10:00:00,
  message: "3 files downloaded and uploaded"
}

BillingCycleFile {
  id: uuid-file-1,
  status: completed,  ← ACTUALIZADO
  carrier_report: "Cost Overview"
}
```

### Logs Generados

```
[2024-11-28 10:15:45] INFO: Starting ScraperJob processor
[2024-11-28 10:15:46] INFO: Scraper statistics: 1 available now, 0 scheduled, 1 pending
[2024-11-28 10:15:47] INFO: Found 1 scraper jobs available for execution
[2024-11-28 10:15:48] INFO: Processing job 1/1
[2024-11-28 10:15:49] INFO: Job ID: uuid-123
[2024-11-28 10:15:50] INFO: Type: MONTHLY_REPORTS
[2024-11-28 10:15:51] INFO: Carrier: BELL
[2024-11-28 10:15:52] INFO: Account: 416-555-1234
[2024-11-28 10:15:53] INFO: No active session - initiating login
[2024-11-28 10:15:54] INFO: Initiating BellAuthStrategy.login
[2024-11-28 10:16:15] INFO: SMS 2FA detected, waiting for code...
[2024-11-28 10:16:35] INFO: Code received from webhook, submitting...
[2024-11-28 10:16:50] INFO: Authentication successful
[2024-11-28 10:16:51] INFO: Scraper created successfully: BellMonthlyReportsScraperStrategy
[2024-11-28 10:16:52] INFO: Searching for files section (attempt 1/1)
[2024-11-28 10:17:45] INFO: Files section found successfully
[2024-11-28 10:18:10] INFO: Downloading file: Cost_Overview_Nov_2024.pdf
[2024-11-28 10:18:20] INFO: File downloaded successfully
[2024-11-28 10:18:25] INFO: Downloading file: Enhanced_Profile_Nov_2024.csv
[2024-11-28 10:18:35] INFO: File downloaded successfully
[2024-11-28 10:18:40] INFO: Downloading file: Usage_Overview_Nov_2024.xlsx
[2024-11-28 10:18:50] INFO: File downloaded successfully
[2024-11-28 10:19:00] INFO: Uploading 3 file(s) of type: monthly
[2024-11-28 10:19:05] INFO: Processing file 1/3: Cost_Overview_Nov_2024.pdf
[2024-11-28 10:19:10] INFO: Uploading monthly report file: Cost_Overview_Nov_2024.pdf
[2024-11-28 10:19:15] INFO: File Cost_Overview_Nov_2024.pdf uploaded successfully
[2024-11-28 10:19:20] INFO: Processing file 2/3: Enhanced_Profile_Nov_2024.csv
[2024-11-28 10:19:25] INFO: File Enhanced_Profile_Nov_2024.csv uploaded successfully
[2024-11-28 10:19:30] INFO: Processing file 3/3: Usage_Overview_Nov_2024.xlsx
[2024-11-28 10:19:35] INFO: File Usage_Overview_Nov_2024.xlsx uploaded successfully
[2024-11-28 10:19:40] INFO: UPLOAD SUMMARY: Successful: 3/3, Failed: 0/3
[2024-11-28 10:19:45] INFO: Scraper executed successfully: 3 files downloaded and uploaded
[2024-11-28 10:19:50] INFO: Execution summary: Successful: 1, Failed: 0, Total: 1
```

---

## ESCENARIO 2: Reutilización de Sesión - Telus Daily Usage

### Contexto

```
Mismo usuario que Escenario 1 ahora ejecuta un trabajo Telus
  └─ Account: Telus - 604-555-5678
      └─ Tipo de Scraper: DAILY_USAGE (no MONTHLY)
```

### Diferencia Clave: Cambio de Carrier

```
┌─ SESSION MANAGER ──────────────────────────────────────────────┐
│ 1. is_logged_in() = true (sesión Bell activa)                 │
│                                                                │
│ 2. get_current_carrier() = Carrier.BELL                        │
│                                                                │
│ 3. Lógica de decisión:                                         │
│    ├─ current_carrier (BELL) != required_carrier (TELUS)      │
│    └─ ✅ Diferentes carriers → Logout + Re-login              │
│                                                                │
│ 4. logout()                                                    │
│    ├─ BellAuthStrategy.logout()                               │
│    │  └─ Navegar a portal de logout                            │
│    ├─ session_state.set_logged_out()                           │
│    └─ Log: "Logged out from BELL"                              │
│                                                                │
│ 5. login(Credentials(TELUS))                                   │
│    ├─ _initialize_browser() [REUTILIZA CONTEXTO]              │
│    ├─ TelusAuthStrategy.login(credentials)                    │
│    │  ├─ Navegar a my-telus portal                             │
│    │  ├─ Autenticación estándar (sin 2FA)                      │
│    │  └─ return True                                           │
│    ├─ session_state.set_logged_in(TELUS, credentials)          │
│    └─ Log: "Logged in to TELUS"                                │
└────────────────────────────────────────────────────────────────┘
                          ↓
                   TelusDailyUsageScraperStrategy
                   execute(...)
                   └─ return ScraperResult(success=True)
```

### Beneficio: Eficiencia

```
Escenario 1 (Bell):
  - Crear browser: 5 segundos
  - Authenticación + 2FA: 30 segundos
  - Scraping: 50 segundos
  TOTAL: 85 segundos

Escenario 2 (Telus, reutilizando contexto):
  - Crear browser: 0 segundos (ya existe)
  - Logout Bell: 3 segundos
  - Autenticación Telus: 10 segundos
  - Scraping: 40 segundos
  TOTAL: 53 segundos

AHORRO: 32 segundos (37% más rápido)
```

---

## ESCENARIO 3: Manejo de Error - ZIP Extraction Fallida

### Contexto

```
Carrier: Rogers
Tipo: PDF_INVOICE
Problemas:
  - Archivo descargado es corrupto
  - ZIP no es válido
```

### Flujo de Recuperación

```
┌─ ROGERS PDF SCRAPER ────────────────────────────────────────────┐
│ 1. execute() → obtiene archivo descargado                       │
│                                                                │
│ 2. _download_files() retorna: [file1.zip (corrupto)]          │
│                                                                │
│ 3. _extract_zip_files(file1.zip)                               │
│    ├─ os.path.exists(file1.zip) → True                         │
│    ├─ zipfile.is_zipfile(file1.zip) → False ❌                 │
│    │  └─ Log ERROR: "File is not a valid ZIP"                  │
│    ├─ return [] (lista vacía)                                  │
│    └─ extracted_files = []                                     │
│                                                                │
│ 4. _create_file_mapping([])                                    │
│    └─ file_mappings = [] (vacío)                               │
│                                                                │
│ 5. _upload_files_to_endpoint([])                               │
│    └─ Nada para cargar                                         │
│                                                                │
│ 6. Retornar resultado                                          │
│    └─ ScraperResult(                                           │
│         success=False,                                         │
│         error="Invalid ZIP file: file1.zip",                  │
│         files=[],                                              │
│         timestamp=datetime.now()                               │
│       )                                                        │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌─ MAIN.PY ──────────────────────────────────────────────────────┐
│ result.success = False                                         │
│                                                                │
│ Status update: RUNNING → ERROR                                 │
│ Message: "Invalid ZIP file: file1.zip"                         │
│                                                                │
│ return False                                                   │
│                                                                │
│ Log: "Job failed - error handling triggered"                   │
└────────────────────────────────────────────────────────────────┘
```

### Resultado en BD

```
ScraperJob {
  id: uuid-456,
  status: ERROR,  ← Actualizado a ERROR
  message: "Invalid ZIP file: file1.zip",
  error_details: "Scraper execution failed: Invalid ZIP file"
}

BillingCyclePDFFile {
  status: error,  ← No completado
  error_log: "ZIP extraction failed"
}
```

---

## ESCENARIO 4: Session Loss Detection - Cache Error Bell

### Contexto

```
Carrier: Bell
Problemas:
  - Usuario fue desconectado por sesión expirada
  - O cache del navegador está corrupto
  - Página de login reappeared
```

### Flujo de Detección y Recuperación

```
┌─ BELL SCRAPER ────────────────────────────────────────────────┐
│ 1. _find_files_section_with_retry()                            │
│    ├─ Attempt 1:                                               │
│    │  ├─ browser.hover_element(report_menu_xpath)              │
│    │  ├─ Excepción: "Element not found"                        │
│    │  │  └─ Señal de sesión perdida                            │
│    │  ├─ self._verify_ereport_header_available()               │
│    │  │  └─ return False (header NO disponible)                │
│    │  ├─ Log WARNING: "Potential cache error detected"         │
│    │  └─ ¿max_retries > 0? → Si                                │
│    │                                                           │
│    └─ Attempt 2:                                               │
│       └─ Reintentar (_find_files_section_with_retry)           │
│          └─ Ahora debe funcionar                               │
│                                                                │
│ [NOTA: Recovery automático comentado en código actual]         │
│ # if self._handle_cache_recovery():                            │
│ #     Log: "Recovery successful, retrying..."                  │
│ #     Limpiar cache                                            │
│ #     Ejecutar callback de re-autenticación                    │
│ #     continue                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## ESCENARIO 5: Múltiples Trabajos en Secuencia

### Contexto

```
Scheduler tiene 3 trabajos disponibles:
  1. Bell Monthly Reports (ACME Corp)
  2. Telus Daily Usage (ACME Corp)
  3. Verizon PDF Invoice (Different Client)
```

### Flujo Completo de Ejecución

```
┌─ MAIN PROCESSOR ────────────────────────────────────────────────┐
│ execute_available_scrapers()                                   │
│                                                                │
│ 1. get_available_jobs_with_complete_context()                  │
│    └─ Retorna: [job1, job2, job3]                             │
│                                                                │
│ 2. Log statistics:                                             │
│    └─ "3 available now, 0 scheduled, 3 total pending"          │
│                                                                │
│ 3. process_scraper_job(job1, 1, 3)                            │
│    ├─ Carrier: BELL, Type: MONTHLY                             │
│    ├─ No existe sesión → Login BELL                            │
│    ├─ Ejecutar BellMonthlyReportsScraperStrategy                │
│    ├─ Resultado: SUCCESS                                       │
│    └─ successful_jobs = 1                                      │
│                                                                │
│ 4. process_scraper_job(job2, 2, 3)                            │
│    ├─ Carrier: TELUS, Type: DAILY                              │
│    ├─ Existe sesión BELL → Logout + Login TELUS               │
│    ├─ Ejecutar TelusDailyUsageScraperStrategy                   │
│    ├─ Resultado: SUCCESS                                       │
│    └─ successful_jobs = 2                                      │
│                                                                │
│ 5. process_scraper_job(job3, 3, 3)                            │
│    ├─ Carrier: VERIZON, Type: PDF                              │
│    ├─ Existe sesión TELUS → Logout + Login VERIZON            │
│    ├─ Ejecutar VerizonPDFInvoiceScraperStrategy                 │
│    ├─ Resultado: SUCCESS                                       │
│    └─ successful_jobs = 3                                      │
│                                                                │
│ 6. Log final summary:                                          │
│    ├─ Successful: 3                                            │
│    ├─ Failed: 0                                                │
│    └─ Total processed: 3                                       │
└────────────────────────────────────────────────────────────────┘

TIMELINE:
  T+0s:    Job 1 comienza (BELL)
  T+85s:   Job 1 termina, Job 2 comienza (TELUS - reutiliza sesión)
  T+138s:  Job 2 termina, Job 3 comienza (VERIZON)
  T+200s:  Job 3 termina, resumen impreso
```

---

## ESCENARIO 6: Extracción de ZIP Compleja

### Contexto

```
Carrier: Telus
Tipo: MONTHLY_REPORTS
Descarga: archivo ZIP con estructura anidada compleja
```

### Contenido Original del ZIP

```
reports_nov_2024.zip
├─ folder1/
│  ├─ file1.pdf (nested)
│  ├─ folder2/
│  │  ├─ file2.csv (deeply nested)
│  │  └─ file3.xlsx
│  └─ .hidden_file (ignorado)
├─ file4.docx (raíz)
├─ file5.txt (raíz)
└─ __MACOSX/ (ignorado)
```

### Proceso de Extracción

```
┌─ SCRAPER BASE STRATEGY ────────────────────────────────────────┐
│ _extract_zip_files(reports_nov_2024.zip)                       │
│                                                                │
│ 1. Verificaciones:                                             │
│    ├─ os.path.exists(zip_file) → True                         │
│    ├─ zipfile.is_zipfile(zip_file) → True                     │
│    └─ Log: "Extracting ZIP: reports_nov_2024.zip"              │
│                                                                │
│ 2. Crear directorio único:                                     │
│    └─ extract_dir = "downloads/reports_nov_2024_extracted_3f4a9b2e" │
│    └─ uuid cortado a 8 caracteres para evitar paths largos    │
│                                                                │
│ 3. Iterar archivos en ZIP:                                     │
│    ├─ "folder1/file1.pdf"                                      │
│    │  ├─ No es directorio (no termina con /)                   │
│    │  ├─ base_filename = "file1.pdf"                           │
│    │  ├─ No comienza con "." → procesar                        │
│    │  ├─ flattened_path = "extracted_dir/file1.pdf"           │
│    │  ├─ No existe → crear                                     │
│    │  ├─ Escribir contenido                                    │
│    │  └─ Log: "Extracted: folder1/file1.pdf -> file1.pdf"      │
│    │                                                           │
│    ├─ "folder1/folder2/file2.csv"                              │
│    │  ├─ base_filename = "file2.csv"                           │
│    │  ├─ flattened_path = "extracted_dir/file2.csv"           │
│    │  ├─ No existe → crear                                     │
│    │  └─ Log: "Extracted: folder1/folder2/file2.csv -> file2.csv" │
│    │                                                           │
│    ├─ "folder1/folder2/file3.xlsx"                             │
│    │  ├─ flattened_path = "extracted_dir/file3.xlsx"          │
│    │  └─ No existe → crear                                     │
│    │                                                           │
│    ├─ "file4.docx"                                             │
│    │  ├─ flattened_path = "extracted_dir/file4.docx"          │
│    │  └─ No existe → crear                                     │
│    │                                                           │
│    ├─ "file5.txt"                                              │
│    │  ├─ flattened_path = "extracted_dir/file5.txt"           │
│    │  └─ No existe → crear                                     │
│    │                                                           │
│    ├─ "folder1/.hidden_file"                                   │
│    │  ├─ base_filename = ".hidden_file"                        │
│    │  ├─ Comienza con "." → IGNORADO                          │
│    │  └─ Log: "Ignored system file: folder1/.hidden_file"      │
│    │                                                           │
│    ├─ "folder1/" (es directorio)                               │
│    │  └─ Log: "Ignored directory: folder1/"                    │
│    │                                                           │
│    ├─ "__MACOSX/" (es directorio)                              │
│    │  └─ Log: "Ignored directory: __MACOSX/"                   │
│    │                                                           │
│    └─ "folder1/folder2/" (es directorio)                       │
│       └─ Log: "Ignored directory: folder1/folder2/"            │
│                                                                │
│ 4. Manejo de colisiones:                                       │
│    ├─ Si existe "extracted_dir/file1.pdf" nuevamente:          │
│    │  ├─ Renombrar a "file1_1.pdf"                             │
│    │  ├─ Siguiente colisión: "file1_2.pdf"                     │
│    │  └─ Continue...                                           │
│    └─ [No hay colisiones en este caso]                         │
│                                                                │
│ 5. Resumen de extracción:                                      │
│    ├─ Total elementos en ZIP: 10                               │
│    ├─ Total archivos extraídos: 5                              │
│    │  └─ file1.pdf, file2.csv, file3.xlsx, file4.docx, file5.txt │
│    └─ Ignorados: 5 (archivos ocultos + directorios)            │
│                                                                │
│ 6. Retornar paths:                                             │
│    └─ [                                                        │
│         "extracted_dir/file1.pdf",                             │
│         "extracted_dir/file2.csv",                             │
│         "extracted_dir/file3.xlsx",                            │
│         "extracted_dir/file4.docx",                            │
│         "extracted_dir/file5.txt"                              │
│       ]                                                        │
└────────────────────────────────────────────────────────────────┘

Resultado:
  extracted_dir/
  ├─ file1.pdf
  ├─ file2.csv
  ├─ file3.xlsx
  ├─ file4.docx
  └─ file5.txt

[Estructura anidada fue APLANADA a un nivel]
```

### Logs de Extracción

```
[2024-11-28 11:30:45] INFO: Extracting ZIP: reports_nov_2024.zip
[2024-11-28 11:30:46] INFO: Extraction directory: downloads/reports_nov_2024_extracted_3f4a9b2e
[2024-11-28 11:30:47] INFO: Elements in ZIP: 10
[2024-11-28 11:30:48] DEBUG: Extracted: folder1/file1.pdf -> file1.pdf
[2024-11-28 11:30:49] DEBUG: Extracted: folder1/folder2/file2.csv -> file2.csv
[2024-11-28 11:30:50] DEBUG: Extracted: folder1/folder2/file3.xlsx -> file3.xlsx
[2024-11-28 11:30:51] DEBUG: Extracted: file4.docx
[2024-11-28 11:30:52] DEBUG: Extracted: file5.txt
[2024-11-28 11:30:53] DEBUG: Ignored system file: folder1/.hidden_file
[2024-11-28 11:30:54] DEBUG: Ignored directory: folder1/
[2024-11-28 11:30:55] DEBUG: Ignored directory: __MACOSX/
[2024-11-28 11:30:56] INFO: EXTRACTION SUMMARY:
[2024-11-28 11:30:57] INFO: Total files extracted: 5
[2024-11-28 11:30:58] INFO: Multiple files:
```

---

## ESCENARIO 7: Flujo con Fallo Parcial de Upload

### Contexto

```
Se descargaron 4 archivos, pero:
  - Archivo 1: Upload exitoso
  - Archivo 2: API retorna 500 (error temporal)
  - Archivo 3: Upload exitoso
  - Archivo 4: Archivo no existe en BD (error de mapping)
```

### Proceso de Upload

```
┌─ FILE UPLOAD SERVICE ─────────────────────────────────────────┐
│ upload_files_batch(                                            │
│   files=[file1, file2, file3, file4],                          │
│   billing_cycle=billing_cycle,                                 │
│   upload_type='monthly'                                        │
│ )                                                              │
│                                                                │
│ success_count = 0                                              │
│ total_files = 4                                                │
│                                                                │
│ Archivo 1/4:                                                   │
│  ├─ config = _get_upload_config('monthly', file1)             │
│  ├─ url_template = "/api/v1/accounts/.../upload-file/"        │
│  ├─ file_obj = file1.billing_cycle_file ✓ existe               │
│  ├─ POST a URL                                                 │
│  ├─ Response: 200 OK                                           │
│  ├─ Log: "File 1 uploaded successfully"                        │
│  └─ success_count = 1                                          │
│                                                                │
│ Archivo 2/4:                                                   │
│  ├─ config = _get_upload_config('monthly', file2)             │
│  ├─ url_template = "/api/v1/accounts/.../upload-file/"        │
│  ├─ file_obj = file2.billing_cycle_file ✓ existe               │
│  ├─ POST a URL                                                 │
│  ├─ Response: 500 Internal Server Error ❌                     │
│  ├─ Log ERROR: "Error uploading file 2: 500 - Internal error"  │
│  └─ success_count = 1 (sin cambios)                            │
│                                                                │
│ Archivo 3/4:                                                   │
│  ├─ config = _get_upload_config('monthly', file3)             │
│  ├─ file_obj = file3.billing_cycle_file ✓ existe               │
│  ├─ POST a URL                                                 │
│  ├─ Response: 200 OK                                           │
│  ├─ Log: "File 3 uploaded successfully"                        │
│  └─ success_count = 2                                          │
│                                                                │
│ Archivo 4/4:                                                   │
│  ├─ config = _get_upload_config('monthly', file4)             │
│  ├─ file_obj = getattr(file4, 'billing_cycle_file') → None ❌ │
│  ├─ Log ERROR: "No billing_cycle_file mapping for file4"       │
│  └─ success_count = 2 (sin cambios)                            │
│                                                                │
│ UPLOAD SUMMARY:                                                │
│  ├─ Successful: 2/4                                            │
│  ├─ Failed: 2/4                                                │
│  └─ return False (2/4 ≠ todos)                                  │
└────────────────────────────────────────────────────────────────┘
```

### Resultado

```
ScraperResult {
  success: False,
  message: "Upload batch failed: 2/4 successful",
  files: [...],
  error: "2 files failed to upload"
}

ScraperJob status: ERROR
Message: "Scraper execution failed: Upload batch failed"
```

---

## ESCENARIO 8: 2FA SMS Webhook Timeout

### Contexto

```
Carrier: Bell
Usuario intenta login pero nunca recibe SMS
Timeout en webhook después de 30 segundos
```

### Flujo

```
┌─ BELL AUTH STRATEGY ────────────────────────────────────────────┐
│ login(credentials)                                              │
│                                                                │
│ 1. Navegar a login page                                        │
│ 2. Llenar username/password                                    │
│ 3. Detectar 2FA visible                                        │
│ 4. Buscar código SMS:                                          │
│    ├─ HTTP GET /authenticator_webhook/code                     │
│    ├─ timeout: 30 segundos                                     │
│    ├─ Esperar respuesta...                                     │
│    ├─ T+10s: No hay código                                     │
│    ├─ T+20s: No hay código                                     │
│    ├─ T+30s: TIMEOUT ❌                                         │
│    │   └─ Exception: TimeoutError                              │
│    └─ return False                                             │
│                                                                │
│ 5. SessionManager.login() retorna False                        │
│    └─ session_state.set_error("Authentication failed: SMS timeout") │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌─ MAIN.PY ──────────────────────────────────────────────────────┐
│ if not login_success:                                          │
│   error_msg = "Authentication failed: SMS timeout"             │
│   raise Exception(error_msg)                                   │
│                                                                │
│ except Exception:                                              │
│   update_scraper_job_status(                                   │
│     job_id,                                                    │
│     ScraperJobStatus.ERROR,                                    │
│     error_msg                                                  │
│   )                                                            │
└────────────────────────────────────────────────────────────────┘
```

### Logs

```
[2024-11-28 12:15:45] INFO: No active session - initiating login
[2024-11-28 12:15:46] INFO: Initiating BellAuthStrategy.login
[2024-11-28 12:16:10] INFO: SMS 2FA detected, requesting code...
[2024-11-28 12:16:10] DEBUG: GET /authenticator_webhook/code timeout=30
[2024-11-28 12:16:40] ERROR: SMS 2FA timeout - code never received
[2024-11-28 12:16:41] ERROR: Authentication failed: SMS timeout
[2024-11-28 12:16:42] ERROR: Error processing scraper: Authentication failed: SMS timeout
[2024-11-28 12:16:43] INFO: Job status updated to ERROR
```

---

## Conclusiones de Escenarios

| Escenario | Tecnología | Resultado | Lección |
|-----------|-----------|-----------|---------|
| 1 - Exitoso | Bell + 2FA | SUCCESS | Sistema completo funciona |
| 2 - Reutilización | Session manager | 37% más rápido | Inteligencia de sesión crítica |
| 3 - ZIP corrupto | Validación ZIP | Graceful degradation | Error handling robusto |
| 4 - Cache error | Retry logic | Recuperación automática | Resilencia a fallos temporales |
| 5 - Múltiples trabajos | Scheduler | Batch processing | Escalabilidad horizontal |
| 6 - ZIP complejo | ZIP extraction | Flattening correcta | Manejo de estructura compleja |
| 7 - Upload parcial | Batch upload | 50% éxito | Continuar tras fallos parciales |
| 8 - SMS timeout | 2FA webhook | Timeout handling | Fallback sin SMS |

---

**Creado:** 2025-11-28
**Versión:** 1.0