# BELL SESSION MANAGEMENT - FLUJO COMPLETO CON 3 SCRAPERS

Este documento describe el comportamiento específico del SessionManager y los scrapers de Bell cuando se ejecutan los 3 tipos de scrapers uno detrás del otro, incluyendo casos de error y recuperación.

## ESCENARIO: EJECUCIÓN SECUENCIAL DE BELL SCRAPERS

### Configuración Inicial
```python
scraper_types = [
    ScraperType.MONTHLY_REPORTS,
    ScraperType.DAILY_USAGE, 
    ScraperType.PDF_INVOICE
]
credentials = Credentials(id=1, username="taqa-notifications@expertel.ca", password="...", carrier=CarrierEnum.BELL)
session_manager = SessionManager(browser_type=Navigators.CHROME)
```

---

## SCRAPER 1: MONTHLY_REPORTS

### 1.1 Primera Ejecución - Estado Inicial del Sistema

**Estado Inicial**:
- `session_manager.session_state.status = SessionStatus.LOGGED_OUT`
- `session_manager._current_auth_strategy = None`
- `session_manager._browser_wrapper = None`
- No hay navegador iniciado

**Flujo de Verificación de Sesión**:
```
1. session_manager.is_logged_in()
   ↓
2. refresh_session_status() 
   ↓ 
3. self._current_auth_strategy is None → return False
   ↓
4. Resultado: False (no hay sesión activa)
```

**Decisión de Autenticación**:
```python
if not session_manager.is_logged_in():  # False
    print("   → No hay sesión activa, haciendo login")
    login_success = session_manager.login(credentials)
```

### 1.2 Proceso de Login Inicial

**SessionManager.login(credentials)**:
```
1. session_state.is_logged_in() → False, continuar
2. auth_strategy_class = BellAuthStrategy (desde _auth_strategies dict)
3. browser_wrapper = _initialize_browser() → Crea navegador Chrome
   - self._browser, self._context = browser_manager.get_browser(CHROME)
   - self._page = self._context.new_page()
   - self._browser_wrapper = PlaywrightWrapper(self._page)
4. self._current_auth_strategy = BellAuthStrategy(browser_wrapper)
5. login_success = bell_auth_strategy.login(credentials)
```

**BellAuthStrategy.login(credentials)**:
```
1. browser_wrapper.goto("https://business.bell.ca/web/login")
2. Ingresar email: "taqa-notifications@expertel.ca"
3. Ingresar password
4. Click en botón login
5. _handle_2fa_if_present() → Manejo automático de 2FA si aparece
6. return is_logged_in() → Verificar botón de usuario visible
```

**Resultado del Login**:
```
✅ login_success = True
📊 session_state.status = SessionStatus.LOGGED_IN
📊 session_state.carrier = Carrier.BELL
📊 session_state.credentials = credentials
📊 _current_auth_strategy = BellAuthStrategy instance
```

### 1.3 Ejecución de BellMonthlyReportsScraperStrategy

**Creación de Scraper**:
```python
browser_wrapper = session_manager.get_browser_wrapper()  # Retorna existente
scraper_strategy = scraper_factory.create_scraper(
    carrier=Carrier.BELL, 
    scraper_type=ScraperType.MONTHLY_REPORTS, 
    browser_wrapper=browser_wrapper
)
# Resultado: BellMonthlyReportsScraperStrategy instance
```

**Ejecución del Scraper**:
```python
result = scraper_strategy.execute(scraper_config, billing_cycle, credentials)
```

**Flujo Detallado de Monthly Reports**:
```
1. _find_files_section_with_retry(max_retries=1)
   ↓
2. Attempt 1:
   a. Hover "Reports" → OK
   b. Click "e-report" → Nueva pestaña abierta
   c. wait_for_new_tab() → Cambio exitoso
   d. switch_to_new_tab() → En pestaña e-report
   e. _verify_ereport_header_available() → ✅ Header visible (primera vez)
   f. Click "standard reports" → OK
   g. return {"section": "monthly_reports", "ready_for_download": True}

3. _download_files():
   a. Para cada reporte: "Cost Overview", "Enhanced User Profile Report", "Usage Overview"
      - Seleccionar en dropdown
      - Configurar fechas del billing_cycle
      - Click Apply + Excel icon
   b. Esperar tabla de status (120s timeout)
   c. Descargar 3 archivos usando page.expect_download()
   d. close_current_tab() → Cerrar pestaña e-report
   e. switch_to_previous_tab() → Regresar a pestaña principal
   f. _reset_to_main_screen() → Click en logo Bell

4. return ScraperResult(success=True, files=[3 archivos])
```

**Estado al Final del Scraper 1**:
```
✅ Scraper exitoso - 3 archivos descargados
📊 Sesión activa mantenida
📊 Navegador abierto en pestaña principal de Bell
📊 session_state.status = SessionStatus.LOGGED_IN
🗂️ Una sola pestaña activa (pestaña principal)
```

---

## SCRAPER 2: DAILY_USAGE

### 2.1 Verificación de Sesión Existente

**Estado al Inicio**:
- `session_manager.session_state.status = SessionStatus.LOGGED_IN`
- `session_manager._current_auth_strategy = BellAuthStrategy instance`
- `session_manager._browser_wrapper = PlaywrightWrapper instance`
- Navegador activo con sesión de Bell

**Flujo de Verificación**:
```
1. session_manager.is_logged_in()
   ↓
2. refresh_session_status()
   ↓
3. self._current_auth_strategy.is_logged_in()
   ↓
4. BellAuthStrategy verifica botón de usuario visible → ✅ True
   ↓
5. return True
```

**Decisión de Autenticación**:
```python
if session_manager.is_logged_in():  # True
    current_carrier = session_manager.get_current_carrier()  # Carrier.BELL
    current_credentials = session_manager.get_current_credentials()  # credentials id=1
    
    if (current_carrier == credentials.carrier and     # BELL == BELL ✅
        current_credentials and 
        current_credentials.id == credentials.id):     # 1 == 1 ✅
        print("   → Usando sesión existente")
        login_success = True  # 🚀 NO RE-LOGIN NECESARIO
```

### 2.2 Ejecución de BellDailyUsageScraperStrategy

**Reutilización de Recursos**:
```python
browser_wrapper = session_manager.get_browser_wrapper()  # Misma instancia
scraper_strategy = scraper_factory.create_scraper(BELL, DAILY_USAGE, browser_wrapper)
# Nueva instancia de BellDailyUsageScraperStrategy
```

**Flujo de Daily Usage**:
```
1. _find_files_section():
   a. Hover "Usage" → OK
   b. Click "Subscriber account usage details" → OK
   c. Buscar cuenta "502462125" → OK
   d. Click "View subscribers" → OK
   e. Re-hover "Usage" → OK
   f. Click "Billing account usage details" → OK
   g. Select "All usage" dropdown → OK
   h. return {"section": "daily_usage", "ready_for_download": True}

2. _download_files():
   a. Click "Download" tab → OK
   b. Click "Download all pages" → OK
   c. page.expect_download() → 1 archivo descargado
   d. _reset_to_main_screen() → Click en logo Bell

3. return ScraperResult(success=True, files=[1 archivo])
```

**Estado al Final del Scraper 2**:
```
✅ Scraper exitoso - 1 archivo descargado
📊 Sesión activa mantenida (sin re-login)
📊 Navegador abierto en pestaña principal de Bell
📊 session_state.status = SessionStatus.LOGGED_IN
⚡ Ejecución más rápida (sin autenticación)
```

---

## SCRAPER 3: PDF_INVOICE

### 3.1 Verificación de Sesión (Tercera Vez)

**Mismo Flujo de Verificación**:
```
session_manager.is_logged_in() → refresh_session_status() → True
Mismas credenciales detectadas → login_success = True (sin re-login)
```

### 3.2 Ejecución de BellPDFInvoiceScraperStrategy

**Flujo de PDF Invoice**:
```
1. _find_files_section():
   a. Hover "Billing" → OK
   b. Click "Download PDF" → OK
   c. Selección de cuenta (opcional) → OK
   d. Click "Complete invoice" radio → OK
   e. Selección de período usando billing_cycle.start_date → OK
   f. return {"section": "pdf_invoices", "ready_for_download": True}

2. _download_files():
   a. Click primer botón "Download" → OK
   b. Esperar hasta 3 minutos por "Download now" button → OK
   c. Click segundo botón "Download now" → OK
   d. _reset_to_main_screen() → Click en logo Bell

3. return ScraperResult(success=True, files=[1 archivo PDF])
```

**Estado al Final del Scraper 3**:
```
✅ Scraper exitoso - 1 archivo PDF descargado
📊 Sesión activa mantenida
📊 Navegador abierto en pestaña principal de Bell
📊 Total: 5 archivos descargados (3 + 1 + 1)
```

---

## CASOS DE ERROR Y RECUPERACIÓN

### Caso 1: Error de Caché en MONTHLY_REPORTS (Segunda Ejecución)

**Escenario**: Si ejecutamos MONTHLY_REPORTS por segunda vez consecutiva

**Flujo con Error de Caché**:
```
1. _find_files_section_with_retry(max_retries=1)
   ↓
2. Attempt 1:
   a. Hover "Reports" → OK
   b. Click "e-report" → Nueva pestaña abierta
   c. switch_to_new_tab() → En pestaña e-report
   d. _verify_ereport_header_available() → ❌ Header NO visible (caché corrupto)
   e. Error detectado: "⚠️ Error de caché detectado en e-reports"
   f. _handle_cache_recovery():
      - close_all_tabs_except_main() → Cerrar pestaña e-report
      - clear_browser_data(cookies=True, storage=True, cache=True)
      - Sesión perdida automáticamente
   g. continue → Reintentar

3. Attempt 2:
   a. Hover "Reports" → Sesión perdida → Error de navegación
   b. Exception capturada → _handle_cache_recovery() nuevamente
   c. continue → Reintentar
   
4. Max retries alcanzado → return None
```

**Impacto en SessionManager**:
```
📊 session_state sigue siendo LOGGED_IN (aún no detectado)
🧹 Datos del navegador limpiados → cookies/storage/cache eliminados
🔍 Próxima llamada a refresh_session_status() detectará sesión perdida
```

**Próximo Scraper (DAILY_USAGE) después del Error**:
```
1. session_manager.is_logged_in()
   ↓
2. refresh_session_status()
   ↓
3. bell_auth_strategy.is_logged_in() → ❌ False (sesión perdida por cache clearing)
   ↓
4. session_state.set_logged_out() → Estado actualizado
   ↓
5. return False

Resultado: login_success = session_manager.login(credentials) → RE-LOGIN AUTOMÁTICO
```

### Caso 2: Pérdida de Sesión por Timeout

**Escenario**: Sesión expira entre scrapers

**Detección**:
```
1. session_manager.is_logged_in() en scraper N+1
   ↓
2. refresh_session_status()
   ↓
3. bell_auth_strategy.is_logged_in() → Botón usuario no visible → False
   ↓
4. session_state.set_logged_out()
   ↓
5. return False
```

**Recuperación Automática**:
```
1. Detección: session_manager.is_logged_in() → False
2. Acción: session_manager.login(credentials) → Re-login automático
3. Continuación: Scraper ejecuta normalmente
```

### Caso 3: Error Fatal de Navegador

**Escenario**: Navegador crash durante ejecución

**Manejo**:
```
1. Exception en scraper.execute()
   ↓
2. try/catch en bucle principal captura error
   ↓
3. print("   ✗ Error inesperado: {str(e)}")
   ↓
4. continue → Próximo scraper
   ↓
5. session_manager.is_logged_in() → Error o False
   ↓
6. Re-inicialización completa del navegador en login()
```

---

## OPTIMIZACIONES DE RENDIMIENTO

### Reutilización de Recursos

**Navegador**:
- 1 instancia Chrome para toda la sesión
- 1 contexto Playwright reutilizado
- Páginas cerradas/abiertas según necesidad

**Sesión de Autenticación**:
- 1 login por sesión (no por scraper)
- Verificación rápida de estado antes de cada scraper
- Re-autenticación solo cuando es necesario

**Tiempo de Ejecución Estimado**:
```
MONTHLY_REPORTS (primera vez): ~60-90 segundos (incluye login)
DAILY_USAGE (reutiliza sesión): ~30-45 segundos  
PDF_INVOICE (reutiliza sesión): ~45-60 segundos
Total sin errores: ~135-195 segundos

Con error de caché:
MONTHLY_REPORTS (con recovery): ~120-150 segundos
DAILY_USAGE (re-login): ~60-75 segundos
PDF_INVOICE (reutiliza nueva sesión): ~45-60 segundos
Total con 1 recovery: ~225-285 segundos
```

---

## LIMPIEZA FINAL

### Proceso de Cleanup

**Al Final de Todos los Scrapers**:
```
1. session_manager.is_logged_in() → True (si todo salió bien)
2. session_manager.logout():
   a. bell_auth_strategy.logout() → Click en user button → logout button
   b. session_state.set_logged_out()
   c. _current_auth_strategy = None
3. session_manager.cleanup():
   a. force_logout() si aún hay sesión
   b. _page.close()
   c. _context.close() 
   d. _browser.close()
   e. Limpiar todas las referencias
```

**Garantías de Limpieza**:
- Logout explícito del portal Bell
- Cierre de todas las pestañas y contextos
- Liberación de recursos del navegador
- Limpieza de referencias en memoria

---

## MONITOREO Y LOGGING

### Mensajes Clave de Estado

**Sesión Existente**:
```
"   → Sesión activa para Bell con usuario taqa-notifications@expertel.ca"
"   → Usando sesión existente"
```

**Nueva Autenticación**:
```
"   → No hay sesión activa, haciendo login"
"   ✓ Login exitoso"
```

**Error de Caché**:
```
"⚠️ Error de caché detectado en e-reports"
"🧹 Iniciando limpieza de datos del navegador..."
"🔄 Datos limpiados - la sesión se perdió y se requiere re-login automático"
```

**Resultados**:
```
"   ✓ Scraper ejecutado exitosamente"
"   ✓ Archivos procesados: 3"
```

Este flujo garantiza máxima eficiencia con sesiones reutilizadas y recuperación automática ante errores específicos de Bell.