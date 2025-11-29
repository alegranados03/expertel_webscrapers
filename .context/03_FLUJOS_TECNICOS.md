# FLUJOS TÉCNICOS DETALLADOS

## Tabla de Contenidos

1. [Flujo de Autenticación por Carrier](#1-flujo-de-autenticación-por-carrier)
2. [Flujo de Scraping Base](#2-flujo-de-scraping-base)
3. [Flujo de Gestión de Sesiones](#3-flujo-de-gestión-de-sesiones)
4. [Flujo de Extracción y Procesamiento de Archivos](#4-flujo-de-extracción-y-procesamiento-de-archivos)
5. [Flujo de Carga de Archivos a API](#5-flujo-de-carga-de-archivos-a-api)
6. [Flujo de 2FA SMS](#6-flujo-de-2fa-sms)

---

## 1. FLUJO DE AUTENTICACIÓN POR CARRIER

### 1.1 Arquitectura de Autenticación

```
┌────────────────────────────────────────────────────────────────┐
│                     SessionManager                             │
│                   (Control Principal)                          │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                AuthBaseStrategy (Interfaz)                     │
│  abstract login(credentials) -> bool                           │
│  abstract logout() -> bool                                     │
│  abstract is_logged_in() -> bool                              │
└────────────────────────────────────────────────────────────────┘
                              ↓
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │BellAuth     │    │TelusAuth    │    │RogersAuth   │
    │Strategy     │    │Strategy     │    │Strategy     │
    │(2FA SMS)    │    │(Estándar)   │    │(Estándar)   │
    └─────────────┘    └─────────────┘    └─────────────┘
          +                   +                   +
        [... ATT, T-Mobile, Verizon ...]
```

### 1.2 Flujo Bell (con 2FA SMS)

**Más complejo:** Integración con webhook de SMS

```
SessionManager.login(credentials: Bell)
│
├─ 1. INICIALIZAR BROWSER
│  ├─ BrowserManager.get_browser(CHROME)
│  ├─ Crear contexto Playwright con stealth
│  └─ Crear nueva página
│
├─ 2. INSTANCIAR ESTRATEGIA
│  └─ BellAuthStrategy(browser_wrapper)
│
├─ 3. LLAMAR login()
│  └─ BellAuthStrategy.login(credentials)
│     │
│     ├─ STEP 1: Navegar a portal
│     │  └─ browser.goto("https://www.bell.ca/...")
│     │
│     ├─ STEP 2: Esperar página de login
│     │  └─ wait_for_selector("input[name=username]", timeout=10s)
│     │
│     ├─ STEP 3: Rellenar username
│     │  ├─ browser.fill("input[name=username]", "user@example.com")
│     │  └─ wait 1s
│     │
│     ├─ STEP 4: Rellenar password
│     │  ├─ browser.fill("input[name=password]", "pwd1234")
│     │  └─ wait 1s
│     │
│     ├─ STEP 5: Click submit
│     │  ├─ browser.click("button[type=submit]")
│     │  └─ wait_for_navigation(timeout=15s)
│     │
│     ├─ STEP 6: Verificar si hay 2FA
│     │  ├─ try:
│     │  │   ├─ browser.wait_for_selector(".otp-input", timeout=5s)
│     │  │   └─ 2FA DETECTED ✓
│     │  │
│     │  └─ except:
│     │      └─ NO 2FA - ir a STEP 10
│     │
│     ├─ STEP 7: Solicitar método 2FA
│     │  ├─ browser.find_element("radio[value=sms]")
│     │  ├─ browser.click("radio[value=sms]")
│     │  └─ Log: "SMS 2FA option selected"
│     │
│     ├─ STEP 8: Solicitar código SMS
│     │  ├─ browser.click("button#send-code")
│     │  ├─ wait 3s
│     │  └─ Log: "SMS code requested"
│     │
│     ├─ STEP 9: Esperar código del webhook
│     │  ├─ polling_start = time.time()
│     │  ├─ while timeout_not_exceeded:
│     │  │   ├─ HTTP GET /authenticator_webhook/code (timeout=30s)
│     │  │   ├─ Si response.code:
│     │  │   │   ├─ code_received = response.code
│     │  │   │   ├─ Log: "SMS code received: ****56"
│     │  │   │   ├─ break
│     │  │   │
│     │  │   └─ else:
│     │  │       ├─ wait 500ms
│     │  │       └─ retry
│     │  │
│     │  ├─ Si timeout:
│     │  │   └─ return False (error de 2FA)
│     │  │
│     │  └─ Log: "Code polling completed in Xs"
│     │
│     ├─ STEP 10: Rellenar 2FA en formulario
│     │  ├─ browser.fill("input.otp-input[0]", "1")
│     │  ├─ browser.fill("input.otp-input[1]", "2")
│     │  ├─ ... (6-8 dígitos)
│     │  └─ wait 1s
│     │
│     ├─ STEP 11: Submit 2FA
│     │  ├─ browser.click("button#verify-code")
│     │  ├─ wait_for_navigation(timeout=10s)
│     │  └─ Log: "2FA code submitted"
│     │
│     ├─ STEP 12: Marcar código como consumido
│     │  └─ HTTP POST /authenticator_webhook/code/consume
│     │
│     ├─ STEP 13: Verificar éxito
│     │  ├─ current_url = browser.get_current_url()
│     │  ├─ Si URL contiene "dashboard" o "home":
│     │  │   └─ return True ✓
│     │  │
│     │  └─ else:
│     │      └─ return False ❌
│     │
│     └─ Exception handling:
│         ├─ Retry automático en ciertos errores
│         ├─ Log detallado de excepción
│         └─ return False
│
└─ 4. ACTUALIZAR SESSION STATE
   ├─ session_state.set_logged_in(Carrier.BELL, credentials)
   ├─ session_state.status = SessionStatus.LOGGED_IN
   ├─ session_state.carrier = Carrier.BELL
   └─ session_state.credentials = credentials
```

### 1.3 Flujo Telus (Estándar sin 2FA)

```
BellAuthStrategy.login(credentials: Telus)
│
├─ STEP 1: Navegar a My Telus
│  └─ browser.goto("https://www.telus.com/my-telus")
│
├─ STEP 2: Esperar formulario login
│  └─ wait_for_selector("input[name=email]", timeout=10s)
│
├─ STEP 3-5: Rellenar email/password (igual que Bell)
│
├─ STEP 6: Click submit
│  └─ browser.click("button[type=submit]")
│
├─ STEP 7: Esperar dashboard
│  ├─ wait_for_selector(".dashboard-container", timeout=15s)
│  └─ wait_for_navigation()
│
├─ STEP 8: Verificar éxito
│  ├─ Si dashboard visible:
│  │   └─ return True ✓
│  │
│  └─ else:
│      └─ return False ❌
│
└─ Session state updated
   └─ carrier = Carrier.TELUS
```

### 1.4 Método is_logged_in() - Verificación de Estado

```
AuthStrategy.is_logged_in() -> bool
│
├─ Buscar elementos de login visibles
│  ├─ try:
│  │   browser.wait_for_selector("input[name=password]", timeout=2s)
│  │   └─ Si se encuentra: usuario NO está logueado ❌
│  │      return False
│  │
│  └─ except TimeoutError:
│      └─ Input no visible (timeout 2s)
│
├─ Verificar URL
│  ├─ current_url = browser.get_current_url()
│  ├─ Si URL contains "login" o "signin":
│  │   └─ return False ❌
│  │
│  └─ else:
│      └─ Probablemente logueado
│
├─ Búsqueda final de dashboard
│  ├─ try:
│  │   browser.wait_for_selector(".dashboard", timeout=1s)
│  │   └─ return True ✓
│  │
│  └─ except:
│      └─ return False (assumir not logged in)
│
└─ return overall_result
```

---

## 2. FLUJO DE SCRAPING BASE

### 2.1 Template Method Pattern - Estructura Base

```
ScraperBaseStrategy.execute() - Template Method
│
├─ FASE 1: ENCONTRAR SECCIÓN DE ARCHIVOS
│  │
│  └─ abstract _find_files_section(config, billing_cycle)
│     └─ Cada carrier implementa su navegación
│        ├─ Bell: hover menu → e-reports → standard reports
│        ├─ Telus: My Telus → Bills → Reports
│        ├─ Rogers: Account → Downloads
│        └─ ...
│
├─ FASE 2: DESCARGAR ARCHIVOS
│  │
│  └─ abstract _download_files(files_section, config, billing_cycle)
│     └─ Cada carrier implementa su descarga
│        ├─ Bell: Click en botones de descarga individuales
│        ├─ Telus: Seleccionar período → Generar reporte → Descargar
│        ├─ Rogers: Click en links de descarga
│        └─ ...
│     └─ Retorna: List[FileDownloadInfo]
│
├─ FASE 3: EXTRAER ZIPs (si aplica)
│  │
│  └─ _extract_zip_files(zip_path) - Heredado de base
│     ├─ Verificar ZIP válido
│     ├─ Crear directorio único (UUID)
│     ├─ Iterar archivos
│     │  ├─ Ignorar directorios
│     │  ├─ Ignorar archivos ocultos (.*)
│     │  └─ Aplanar estructura
│     └─ Retorna: List[str] (paths extraídos)
│
├─ FASE 4: MAPEAR ARCHIVOS
│  │
│  └─ _create_file_mapping(downloaded_files) - Heredado
│     ├─ Convertir FileDownloadInfo → FileMappingInfo
│     ├─ Incluir IDs de BD
│     └─ Retorna: List[FileMappingInfo]
│
├─ FASE 5: CARGAR A API EXTERNA
│  │
│  └─ _upload_files_to_endpoint(files, billing_cycle, type)
│     ├─ Crear FileUploadService
│     ├─ Llamar upload_files_batch()
│     ├─ Procesar resultado
│     └─ Retorna: bool (éxito/fallo)
│
└─ FASE 6: RETORNAR RESULTADO
   └─ ScraperResult(
      success=True/False,
      message="...",
      files=file_mappings,
      error=error_msg_if_any
    )
```

### 2.2 Flujo Específico: Bell Monthly Reports

```
BellMonthlyReportsScraperStrategy.execute()
│
├─ _find_files_section(config, billing_cycle)
│  │
│  └─ _find_files_section_with_retry(max_retries=1)
│     │
│     ├─ ATTEMPT 1:
│     │  ├─ hover element: Reports menu
│     │  ├─ wait 2s
│     │  ├─ click e-reports link
│     │  ├─ switch_to_new_tab (esperar 90s)
│     │  ├─ verify header disponible
│     │  ├─ click standard reports
│     │  ├─ wait_for_page_load()
│     │  ├─ wait 50s (cargar página)
│     │  │
│     │  └─ Success? return {"section": "monthly_reports"}
│     │     Or catch Exception:
│     │         └─ Log error, close tab, switch back
│     │         └─ Retry (attempt 2)?
│     │
│     └─ [Recovery automática comentada en código actual]
│        # if attempt < max_retries:
│        #     if self._handle_cache_recovery():
│        #         continue
│
├─ _download_files(files_section, config, billing_cycle)
│  │
│  ├─ Crear dict para mapear BillingCycleFiles por slug
│  │
│  ├─ Para cada BillingCycleFile:
│  │  ├─ Buscar slug en página
│  │  ├─ Encontrar elemento de descarga
│  │  ├─ browser.download_file(selector)
│  │  │  └─ Espera descarga, retorna path
│  │  │
│  │  ├─ Crear FileDownloadInfo:
│  │  │  {
│  │  │    file_id: uuid(),
│  │  │    file_name: "Cost_Overview_Nov_2024.pdf",
│  │  │    file_path: "/downloads/Cost_Overview_Nov_2024.pdf",
│  │  │    download_url: "https://bell.ca/...",
│  │  │    download_timestamp: datetime.now(),
│  │  │    billing_cycle_file: bcf_object
│  │  │  }
│  │  │
│  │  └─ Append a downloaded_files list
│  │
│  └─ return downloaded_files (list de 3 archivos típicamente)
│
├─ _extract_zip_files()
│  └─ Bell no genera ZIPs, retorna []
│
├─ _create_file_mapping(downloaded_files)
│  └─ Convertir a FileMappingInfo para BD
│
├─ _upload_files_to_endpoint(file_mappings, billing_cycle, 'monthly')
│  │
│  └─ FileUploadService.upload_files_batch()
│     ├─ Para cada archivo:
│     │  ├─ POST /api/v1/accounts/billing-cycles/{id}/files/{file_id}/upload-file/
│     │  ├─ Headers: x-api-key, x-workspace-id, x-client-id
│     │  ├─ File multipart
│     │  ├─ Respuesta 200/201? Éxito
│     │  └─ Otro? Error log
│     │
│     └─ return success_count == total_count
│
└─ return ScraperResult(success=True, message="3 files...", files=...) ✓
```

### 2.3 Flujo Específico: Telus Monthly Reports (Complejo)

**Particularidad:** Generación de reportes dinámicos con cola

```
TelusMonthlyReportsScraperStrategy.execute()
│
├─ PARTE 1: DESCARGAR ZIP DESDE BILLS
│  │
│  ├─ Navegar a My Telus
│  │
│  ├─ Click bill options dropdown
│  │
│  ├─ Click download bills
│  │
│  ├─ Buscar mes/año basado en billing_cycle.end_date
│  │  ├─ target_month = "November"
│  │  ├─ target_year = 2024
│  │  ├─ Iterar selectores de meses
│  │  │  ├─ Encontrar "November 2024"
│  │  │  ├─ browser.click()
│  │  │  └─ wait 5s
│  │  │
│  │  └─ Success? Proceder a descarga ZIP
│  │
│  ├─ Descargar ZIP
│  │  ├─ browser.download_file(zip_selector)
│  │  ├─ Esperar descarga completa
│  │  │
│  │  ├─ _extract_zip_files(zip_path)
│  │  │  ├─ Validar ZIP
│  │  │  ├─ Crear directorio único
│  │  │  ├─ Iterar contenido
│  │  │  ├─ Aplanar estructura
│  │  │  └─ return list[extracted_files]
│  │  │
│  │  └─ Mapear archivos extraídos
│  │
│  └─ Agregar al list de descargados
│
├─ PARTE 2: DESCARGAR ARCHIVOS INDIVIDUALES
│  │
│  ├─ Navegar a Reports section
│  │  ├─ Click billing header
│  │  ├─ wait_for_page_load()
│  │  ├─ wait 60s (un minuto!)
│  │  │
│  │  └─ Razón: Telus necesita tiempo para actualizar reportes
│  │
│  ├─ Para cada tipo de reporte:
│  │  ├─ Click para generar reporte
│  │  │
│  │  ├─ MONITOREAR COLA:
│  │  │  ├─ Estado inicial: "In Queue"
│  │  │  ├─ Polling cada 5s
│  │  │  ├─ Esperar hasta "Ready for Download"
│  │  │  ├─ Timeout: 5 minutos
│  │  │  │
│  │  │  └─ Cuando esté listo:
│  │  │     ├─ Click descargar
│  │  │     ├─ Esperar archivo
│  │  │     └─ Registrar en downloaded_files
│  │  │
│  │  └─ Si timeout:
│  │     ├─ Log warning
│  │     └─ Continuar con siguiente reporte
│  │
│  └─ Agregar todos al list
│
├─ _create_file_mapping()
│
├─ _upload_files_to_endpoint()
│  └─ Upload type: 'monthly' (múltiples archivos)
│
└─ return ScraperResult(success=True, message="...", files=...)
```

---

## 3. FLUJO DE GESTIÓN DE SESIONES

### 3.1 Lógica de Decisión Inteligente

```
SessionManager.login(credentials: Credentials) -> bool
│
├─ ¿Ya hay sesión?
│  │
│  └─ if session_state.is_logged_in():
│     │
│     ├─ ¿Credenciales coinciden?
│     │  │
│     │  └─ if current_carrier == credentials.carrier
│     │     AND current_credentials.id == credentials.id:
│     │
│     │     ├─ ✅ REUTILIZAR SESIÓN
│     │     ├─ Log: "Using existing session"
│     │     └─ return True (sin hacer nada)
│     │
│     │  └─ else (credenciales diferentes):
│     │
│     │     ├─ 🔄 LOGOUT PREVIO
│     │     ├─ self.logout()
│     │     │  ├─ auth_strategy.logout()
│     │     │  ├─ session_state.set_logged_out()
│     │     │  └─ _current_auth_strategy = None
│     │     │
│     │     ├─ 🆕 LOGIN NUEVO
│     │     │  ├─ Proceder a paso "No hay sesión"
│     │     │  └─ return resultado
│     │
│  └─ else (no hay sesión activa):
│
│     ├─ 🆕 LOGIN NUEVO
│     ├─ Obtener estrategia para carrier:
│     │  ├─ auth_strategy_class = self._auth_strategies[carrier]
│     │  │  └─ Mapeo: BELL → BellAuthStrategy, etc.
│     │  │
│     │  └─ Si no existe: return False (carrier no soportado)
│     │
│     ├─ Inicializar browser:
│     │  ├─ _initialize_browser()
│     │  ├─ BrowserManager.get_browser(browser_type)
│     │  ├─ Crear contexto (con stealth si es Chrome)
│     │  ├─ Crear nueva página
│     │  └─ Crear PlaywrightWrapper
│     │
│     ├─ Instanciar estrategia:
│     │  └─ auth_strategy = auth_strategy_class(browser_wrapper)
│     │
│     ├─ Ejecutar login:
│     │  └─ login_success = auth_strategy.login(credentials)
│     │
│     ├─ Si éxito:
│     │  ├─ session_state.set_logged_in(carrier, credentials)
│     │  ├─ _current_auth_strategy = auth_strategy
│     │  └─ return True
│     │
│     └─ Si fallo:
│        ├─ session_state.set_error(error_message)
│        └─ return False
│
└─ END
```

### 3.2 Refresh Session Status - Verificación Periódica

```
SessionManager.refresh_session_status() -> bool
│
├─ ¿Hay estrategia activa?
│  ├─ if not _current_auth_strategy:
│  │   └─ return False (no hay sesión)
│  │
│  └─ else: Proceder
│
├─ Verificar si aún logueado
│  ├─ is_active = _current_auth_strategy.is_logged_in()
│  │  └─ Este método:
│  │     ├─ Busca elementos login
│  │     ├─ Verifica URL
│  │     ├─ Busca dashboard
│  │     └─ return True/False
│  │
│  └─ if not is_active:
│     ├─ Sesión se perdió (logout forzado, timeout, etc)
│     ├─ session_state.set_logged_out()
│     ├─ _current_auth_strategy = None
│     └─ return False
│
└─ return is_active
```

### 3.3 Ciclo de Vida Completo de Sesión

```
                    ┌─────────────────┐
                    │  NO LOGUEADO    │
                    └────────┬────────┘
                             │ login()
                             ↓
                    ┌─────────────────┐
              ┌────→│  LOGUEADO       │◄──────────┐
              │     └────────┬────────┘           │
              │              │                   │ logout()
              │              │ is_logged_in()    │ fallido
              │              ├─ False ──────────→├────────┐
              │              │                   │        │
              │              └─ True ────────────┘        │
              │                                          │
              ├──────────────← Timeout/error ◄──────────┘
              │
         refresh_session_status()
         (verificación periódica)
         ├─ True: sesión válida
         └─ False: sesión perdida

Transiciones:
  - login(same_creds): LOGUEADO → LOGUEADO (no-op)
  - login(diff_creds): LOGUEADO → NO → LOGUEADO (logout + login)
  - logout(): LOGUEADO → NO LOGUEADO
  - timeout: LOGUEADO → NO LOGUEADO (detección)
  - refresh: LOGUEADO → LOGUEADO (si válida) o NO (si perdida)
```

---

## 4. FLUJO DE EXTRACCIÓN Y PROCESAMIENTO DE ARCHIVOS

### 4.1 Descarga de Archivos - Mecánica de Playwright

```
browser.download_file(selector: str, timeout: int) -> str
│
├─ INICIAR LISTENER
│  └─ Crear listener para eventos de descarga
│
├─ CLICKEAR SELECTOR
│  ├─ browser.click(selector)
│  └─ Esto dispara descarga en navegador
│
├─ ESPERAR DESCARGA
│  ├─ Esperar evento 'download' (timeout=30s por defecto)
│  │  ├─ Descarga en progreso
│  │  ├─ Monitorear estado
│  │  │  ├─ 0-5%: iniciando
│  │  │  ├─ 5-95%: transfiriendo
│  │  │  └─ 95-100%: finalizando
│  │  │
│  │  └─ Cuando completado:
│  │     ├─ download.path() retorna archivo temp
│  │     └─ Archivo está en memoria de Playwright
│  │
│  └─ Si timeout:
│     └─ raise TimeoutError
│
├─ GUARDAR ARCHIVO
│  ├─ path = download.path()
│  ├─ Crear downloads_dir si no existe
│  ├─ destiny = os.path.join(downloads_dir, filename)
│  ├─ shutil.move(path, destiny)
│  └─ Log: "File saved to {destiny}"
│
└─ return destiny (path absoluto)
```

### 4.2 Extracción de ZIP - Flattening

```
_extract_zip_files(zip_file_path: str) -> List[str]
│
├─ VALIDACIONES
│  ├─ os.path.exists(zip_file_path)? → False? return []
│  ├─ zipfile.is_zipfile(zip_file_path)? → False? return []
│  └─ OK: proceder
│
├─ CREAR DIRECTORIO EXTRACCIÓN
│  ├─ zip_basename = "mi_archivo"
│  ├─ unique_id = uuid4()[:8] = "3f4a9b2e"
│  ├─ extract_dir = f"{dirname}/mi_archivo_extracted_3f4a9b2e"
│  ├─ os.makedirs(extract_dir, exist_ok=True)
│  └─ Log: "Extraction directory: {extract_dir}"
│
├─ ITERAR ARCHIVOS EN ZIP
│  │
│  └─ with ZipFile(zip_path) as zf:
│     │
│     └─ for file_name in zf.namelist():  # ["folder/file1.pdf", "file2.csv", ...]
│        │
│        ├─ ¿Es directorio? (termina con /)
│        │  └─ Si: Skip (log "Ignored directory")
│        │
│        ├─ Obtener nombre base (sin carpetas)
│        │  ├─ base_filename = os.path.basename(file_name)
│        │  │  └─ "folder/file1.pdf" → "file1.pdf"
│        │  │
│        │  └─ ¿Comienza con "."? (archivo oculto)
│        │     └─ Si: Skip (log "Ignored system file")
│        │
│        ├─ APLANAR ESTRUCTURA
│        │  ├─ flattened_path = os.path.join(extract_dir, base_filename)
│        │  │  └─ Siempre en el nivel 1 de extract_dir
│        │  │
│        │  ├─ ¿Existe ya?
│        │  │  ├─ Si: Renombrar con contador
│        │  │  │   ├─ name = "file1", ext = ".pdf"
│        │  │  │   ├─ flattened_path = "extract_dir/file1_1.pdf"
│        │  │  │   ├─ ¿Existe? → "file1_2.pdf"
│        │  │  │   └─ Continuar hasta encontrar disponible
│        │  │  │
│        │  │  └─ No: usar path original
│        │  │
│        │  └─ Log: "Extracted: {original} → {base_filename}"
│        │
│        ├─ ESCRIBIR ARCHIVO
│        │  ├─ file_content = zf.read(file_name)
│        │  ├─ with open(flattened_path, "wb") as f:
│        │  │   f.write(file_content)
│        │  │
│        │  └─ Log: "Written to {flattened_path}"
│        │
│        └─ Agregar a extracted_files[]
│
├─ RESUMEN
│  ├─ Log total elementos: 10
│  ├─ Log total extraídos: 5
│  └─ Log ignorados: 5 (directorios + ocultos)
│
└─ return extracted_files
   └─ [
        "extracted_dir/file1.pdf",
        "extracted_dir/file2.csv",
        ...
      ]
```

### 4.3 Mapeo de Archivos

```
_create_file_mapping(downloaded_files: List[FileDownloadInfo])
   → List[FileMappingInfo]
│
├─ for file_info in downloaded_files:
│  │
│  └─ FileMappingInfo(
│       file_id = file_info.file_id,
│       file_name = file_info.file_name,
│       file_path = file_info.file_path,
│       download_url = file_info.download_url,
│       billing_cycle_file_id = file_info.billing_cycle_file.id,
│       carrier_report_name = file_info.billing_cycle_file.carrier_report.name,
│       daily_usage_file_id = file_info.daily_usage_file?.id,
│       pdf_file_id = file_info.pdf_file?.id
│     )
│
└─ return file_mappings
```

---

## 5. FLUJO DE CARGA DE ARCHIVOS A API

### 5.1 Servicio de Upload Universal

```
FileUploadService.upload_files_batch(
    files: List[FileDownloadInfo],
    billing_cycle: BillingCycle,
    upload_type: str  # 'monthly', 'daily_usage', 'pdf_invoice'
) -> bool
│
├─ INICIALIZACIÓN
│  ├─ self.api_base_url = "https://api.expertel.com"
│  ├─ self.api_key = "${EIQ_BACKEND_API_KEY}"
│  ├─ success_count = 0
│  ├─ total_files = len(files)
│  │
│  └─ Log: f"Uploading {total_files} file(s) of type: {upload_type}"
│
├─ LOOP ARCHIVOS
│  │
│  └─ for i, file_info in enumerate(files, 1):
│     │
│     └─ PASO 1: Obtener configuración
│        │
│        ├─ config = _get_upload_config(upload_type, file_info)
│        │  │
│        │  ├─ Si upload_type == 'monthly':
│        │  │   ├─ url_template = "/api/v1/accounts/billing-cycles/{cycle_id}/files/{file_id}/upload-file/"
│        │  │   ├─ file_id_attr = "billing_cycle_file"
│        │  │   ├─ content_type = "application/octet-stream"
│        │  │   └─ description = "monthly report"
│        │  │
│        │  ├─ Si upload_type == 'daily_usage':
│        │  │   ├─ url_template = "/api/v1/accounts/billing-cycles/{cycle_id}/daily-usage/"
│        │  │   ├─ file_id_attr = "daily_usage_file"
│        │  │   └─ No incluye {file_id} en template
│        │  │
│        │  ├─ Si upload_type == 'pdf_invoice':
│        │  │   ├─ url_template = "/api/v1/accounts/billing-cycles/{cycle_id}/pdf-invoice/"
│        │  │   ├─ file_id_attr = "pdf_file"
│        │  │   ├─ content_type = "application/pdf"
│        │  │   └─ No incluye {file_id} en template
│        │  │
│        │  └─ Si tipo desconocido:
│        │     ├─ Log error
│        │     └─ return False
│        │
│        └─ PASO 2: Verificar mapeo BD
│           │
│           ├─ file_obj = getattr(file_info, config['file_id_attr'])
│           │  └─ Obtiene el objeto de BD (ej: BillingCycleFile)
│           │
│           └─ Si no existe:
│              ├─ Log error: f"No {attr} mapping for {file_name}"
│              └─ continue (siguiente archivo)
│
│        └─ PASO 3: Construir URL
│           │
│           ├─ cycle_id = billing_cycle.id
│           │
│           └─ Si url_template contiene "{file_id}":
│              ├─ url = template.format(file_id=file_obj.id)
│              │  └─ "/api/v1/accounts/bc-123/files/f-456/upload-file/"
│              │
│              └─ else:
│                 ├─ url = template
│                 │  └─ "/api/v1/accounts/bc-123/daily-usage/"
│
│        └─ PASO 4: Preparar headers
│           │
│           ├─ headers = {
│           │    "x-api-key": self.api_key,
│           │    "Accept": "application/json",
│           │    "x-workspace-id": billing_cycle.account.workspace.id,
│           │    "x-client-id": billing_cycle.account.workspace.client.id
│           │  }
│           │
│           └─ Log debug: "Headers prepared"
│
│        └─ PASO 5: POST archivo
│           │
│           ├─ with open(file_info.file_path, "rb") as file:
│           │   │
│           │   ├─ files = {
│           │   │    "file": (
│           │   │      file_info.file_name,
│           │   │      file,
│           │   │      config["content_type"]  # application/pdf, etc
│           │   │    )
│           │   │  }
│           │   │
│           │   ├─ response = requests.post(
│           │   │    url=url,
│           │   │    headers=headers,
│           │   │    data={},  # Solo enviar file
│           │   │    files=files,
│           │   │    timeout=300  # 5 minutos
│           │   │  )
│           │   │
│           │   └─ Log: f"Uploaded to {url}"
│           │
│           └─ PASO 6: Verificar respuesta
│              │
│              ├─ if response.status_code in [200, 201]:
│              │   ├─ Log: "File uploaded successfully"
│              │   ├─ success_count += 1
│              │   └─ continue
│              │
│              └─ else:
│                 ├─ Log error: f"Error: {status} - {text}"
│                 └─ success_count sin cambios (fallo)
│
├─ RESULTADO FINAL
│  │
│  ├─ Log SUMMARY:
│  │  ├─ f"Successful: {success_count}/{total_files}"
│  │  └─ f"Failed: {total_files - success_count}/{total_files}"
│  │
│  └─ return success_count == total_files
│     ├─ True: Todos exitosos
│     └─ False: Al menos uno falló

Exception handling en cada POST:
  ├─ ConnectionError: Log error
  ├─ Timeout: Log error
  ├─ JSONDecodeError: Log error
  └─ Cualquier excepción: Continuar con siguiente
```

---

## 6. FLUJO DE 2FA SMS

### 6.1 Arquitectura SMS 2FA

```
┌─────────────────────────────────────────────────────────────────┐
│                    BELL AUTH STRATEGY                           │
│                  (Cliente HTTP)                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ GET /authenticator_webhook/code
                         │ (polling)
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              SMS 2FA WEBHOOK (Flask)                            │
│          (authenticator_webhook/sms2fa.py)                      │
└────────────────────────────────────────────────────────────────┘
                         ↑
                         │
                    SMS Gateway
                    (ext. service)
                         ↑
                         │
         User Teléfono recibe SMS
         "Your code is 123456"
```

### 6.2 Flujo Completo de 2FA

```
1. USUARIO INICIA LOGIN
   └─ Bell auth strategy entra en branch "Detectar 2FA"
      └─ wait_for_selector(".otp-input", timeout=5s)
      └─ 2FA DETECTADO ✓

2. USUARIO SELECCIONA MÉTODO SMS
   ├─ browser.find_element("radio[value=sms]")
   ├─ browser.click()
   └─ Log: "SMS method selected"

3. USUARIO SOLICITA CÓDIGO
   ├─ browser.click("button#send-code")
   ├─ wait 3s
   └─ Log: "SMS code requested"
   └─ Usuario recibe SMS: "Your code is 123456"

4. WEBHOOK RECIBE SMS (Ext. Sistema)
   │
   └─ POST /authenticator_webhook/sms
      │
      ├─ Body: {"message": "Your code is 123456"}
      │
      ├─ PROCESAR:
      │  ├─ regex pattern: \d{6,8}
      │  ├─ match = re.search(pattern, message)
      │  ├─ code = "123456"
      │  │
      │  ├─ Almacenar en thread-safe storage:
      │  │  ├─ sms_codes["latest"] = {
      │  │  │    "code": "123456",
      │  │  │    "timestamp": datetime.now(),
      │  │  │    "consumed": False
      │  │  │  }
      │  │  │
      │  │  └─ Expirar en 5 minutos:
      │  │     └─ background thread: monitorear y limpiar
      │  │
      │  └─ return {"status": "received", "code_stored": True}
      │
      └─ Log: "SMS code 123456 received and stored"

5. AUTH STRATEGY REALIZA POLLING
   │
   └─ while time.time() - polling_start < TIMEOUT (30s):
      │
      ├─ HTTP GET /authenticator_webhook/code
      │  │
      │  ├─ Webhook responde:
      │  │  ├─ Si hay código disponible:
      │  │  │   ├─ {"code": "123456", "timestamp": "..."}
      │  │  │   └─ Código está en storage
      │  │  │
      │  │  └─ Si no hay código:
      │  │      ├─ {"error": "No code available"}
      │  │      └─ Esperar siguiente intento
      │  │
      │  └─ response.code?
      │     ├─ Si: code_received = response.code
      │     │   └─ break (salir loop)
      │     │
      │     └─ No: wait 500ms, retry
      │
      └─ Si timeout (30s):
         ├─ Log error: "SMS 2FA timeout"
         └─ return False

6. LLENAR CÓDIGO EN FORMULARIO
   │
   ├─ code = "123456"
   ├─ for i, digit in enumerate(code):
   │   └─ browser.fill(f"input.otp-input[{i}]", digit)
   │
   └─ Log: "OTP code filled (****56)"

7. SUBMIT 2FA
   │
   ├─ browser.click("button#verify-code")
   ├─ wait_for_navigation(timeout=10s)
   └─ Log: "2FA code submitted"

8. MARCAR COMO CONSUMIDO
   │
   └─ HTTP POST /authenticator_webhook/code/consume
      │
      ├─ Webhook actualiza storage:
      │  └─ sms_codes["latest"]["consumed"] = True
      │
      └─ Prevenir reutilización de código

9. VERIFICAR ÉXITO
   │
   ├─ current_url = browser.get_current_url()
   ├─ Si contains "dashboard" or "home":
   │   └─ return True ✓
   │
   └─ else:
       └─ return False ❌

10. SESSION STATE ACTUALIZA
    └─ session_state.set_logged_in(Carrier.BELL, credentials)
```

### 6.3 Endpoints del Webhook

```
POST /sms
  └─ Recibir SMS general
  └─ Body: {"message": "Your code is 123456"}
  └─ Response: {"status": "received"}

POST /verizon/sms
  └─ Recibir SMS Verizon específico
  └─ Misma lógica

POST /att/sms
  └─ Recibir SMS AT&T específico

POST /tmobile/sms
  └─ Recibir SMS T-Mobile específico

GET /code
  └─ Obtener último código disponible
  └─ Response:
     ├─ {"code": "123456", "timestamp": "2024-11-28T10:15:45"}
     └─ {"error": "No code available"}

POST /code/consume
  └─ Marcar código como consumido
  └─ Response: {"status": "consumed"}

GET /status
  └─ Estado del webhook
  └─ Response: {
      "status": "running",
      "codes_stored": 1,
      "last_received": "2024-11-28T10:15:45"
    }

GET /health
  └─ Health check
  └─ Response: {"status": "healthy"}
```

### 6.4 Storage Thread-Safe

```
sms_codes = {
    "latest": {
        "code": "123456",
        "timestamp": datetime.now(),
        "consumed": False,
        "carrier": "BELL"
    }
}

Lock: threading.Lock()
  ├─ with lock:
  │   ├─ Lectura/escritura de sms_codes
  │   └─ Evitar race conditions
  │
  └─ Cleanup thread:
     ├─ Cada 10s: verificar expiración
     ├─ Si time.time() - timestamp > 300 (5 min):
     │   └─ Borrar código expirado
     └─ Mantener storage limpio
```

---

**Creado:** 2025-11-28
**Versión:** 1.0
**Diagramas:** ASCII art para facilitar lectura en terminal