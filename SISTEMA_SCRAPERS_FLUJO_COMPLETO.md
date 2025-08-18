# SISTEMA DE SCRAPERS - FLUJO COMPLETO EXHAUSTIVO

Este documento describe paso a paso el flujo completo del sistema de scrapers, siguiendo el código desde `scraper_system_example.py` hasta la ejecución final, incluyendo todas las bifurcaciones y casos especiales.

## ÍNDICE
1. [Inicialización del Sistema](#1-inicialización-del-sistema)
2. [Configuración de Entidades](#2-configuración-de-entidades)
3. [Gestión de Sesiones](#3-gestión-de-sesiones)
4. [Ejecución de Scrapers](#4-ejecución-de-scrapers)
5. [Estrategias Específicas por Carrier](#5-estrategias-específicas-por-carrier)
6. [Manejo de Errores y Recuperación](#6-manejo-de-errores-y-recuperación)
7. [Limpieza y Finalización](#7-limpieza-y-finalización)

---

## 1. INICIALIZACIÓN DEL SISTEMA

### 1.1 Punto de Entrada - `scraper_system_example.py`
**Archivo**: `web_scrapers/examples/scraper_system_example.py`

```python
def simulate_scraper_execution():
```

**Flujo de Inicialización**:
1. **Configuración de PATH**: Se agrega el directorio padre al sys.path
2. **Importaciones**: Se cargan todas las dependencias necesarias
3. **Creación de Entidades**: Se instancian objetos de ejemplo (Cliente, Workspace, Carrier, etc.)

### 1.2 Creación de Entidades de Ejemplo

**Orden de Creación**:
1. **Client** - Información del cliente (Expertel Test Client)
2. **Workspace** - Espacio de trabajo vinculado al cliente
3. **Carrier** - Información del carrier (Bell Canada con metadata de 2FA)
4. **Account** - Cuenta corporativa vinculada al workspace y carrier
5. **CarrierReport** - Definición de reportes disponibles
6. **CarrierPortalCredential** - Credenciales de acceso al portal
7. **BillingCycle** - Período de facturación con Account integrado
8. **BillingCycleFile** - Archivos de ciclo de facturación
9. **BillingCycleDailyUsageFile** - Archivos de uso diario
10. **BillingCyclePDFFile** - Archivos PDF de facturas
11. **ScraperConfig** - Configuración del scraper
12. **ScraperJob** - Trabajo de scraper

### 1.3 Componentes Principales del Sistema

**SessionManager Initialization**:
```python
session_manager = SessionManager(browser_type=Navigators.CHROME)
```

**ScraperFactory Initialization**:
```python
scraper_factory = ScraperStrategyFactory()
```

**Credentials Setup**:
```python
credentials = Credentials(
    id=1, 
    username="taqa-notifications@expertel.ca", 
    password="password", 
    carrier=CarrierEnum.BELL
)
```

---

## 2. CONFIGURACIÓN DE ENTIDADES

### 2.1 Modelo de Datos Completo

**Client Entity**:
- Información básica del cliente (nombre, contacto, dirección)
- Flags de configuración (is_testing, active, managed_by_expertel)
- Información de facturación (zip_code, phone_number)

**Account Hierarchy**:
```
Client -> Workspace -> Account -> BillingCycle -> Files
```

**Carrier Configuration**:
- Metadata específica del carrier (país, soporte 2FA)
- Configuración de reportes disponibles
- Credenciales de acceso al portal

### 2.2 Configuración de Scraper

**ScraperConfig Components**:
- `account_id`: Vinculación con la cuenta
- `credential_id`: Credenciales a utilizar
- `carrier_id`: Carrier específico
- `parameters`: Parámetros personalizados (billing_period, format)
- `days_offset`: Offset de días para fechas

---

## 3. GESTIÓN DE SESIONES

### 3.1 SessionManager - Clase Principal
**Archivo**: `web_scrapers/application/session_manager.py`

**Componentes del SessionManager**:
```python
class SessionManager:
    - browser_manager: BrowserManager()
    - browser_type: Navigators
    - session_state: SessionState()
    - _auth_strategies: Dict[Carrier, AuthBaseStrategy]
    - _current_auth_strategy: AuthBaseStrategy
    - _browser_wrapper: BrowserWrapper
    - _browser: Browser
    - _context: BrowserContext
    - _page: Page
```

### 3.2 Verificación de Estado de Sesión

**Flujo de Verificación (`is_logged_in()`)**:
```
1. session_manager.is_logged_in()
   ↓
2. refresh_session_status()
   ↓
3. _current_auth_strategy.is_logged_in()
   ↓
4. Verifica elementos específicos del carrier en la página
   ↓
5. Actualiza session_state según el resultado
```

**Estados Posibles**:
- `LOGGED_IN`: Sesión activa y válida
- `LOGGED_OUT`: Sin sesión activa
- `ERROR`: Error en la verificación

### 3.3 Lógica de Decisión de Autenticación

**Caso A - No hay sesión activa**:
```python
if not session_manager.is_logged_in():
    print("   → No hay sesión activa, haciendo login")
    login_success = session_manager.login(credentials)
```

**Caso B - Sesión activa con mismas credenciales**:
```python
if (current_carrier == credentials.carrier and 
    current_credentials and 
    current_credentials.id == credentials.id):
    print("   → Usando sesión existente")
    login_success = True
```

**Caso C - Sesión activa con credenciales diferentes**:
```python
else:
    print("   → Credenciales diferentes, haciendo logout y login")
    session_manager.logout()
    login_success = session_manager.login(credentials)
```

### 3.4 Proceso de Login

**Flujo de Login (`session_manager.login(credentials)`)**:
```
1. Verificar si ya hay sesión activa con mismas credenciales
   ↓
2. Si hay sesión diferente, hacer logout primero
   ↓
3. Obtener estrategia de autenticación según carrier
   ↓
4. Inicializar navegador si no existe
   ↓
5. Crear instancia de auth strategy
   ↓
6. Ejecutar auth_strategy.login(credentials)
   ↓
7. Actualizar session_state según resultado
```

**Inicialización de Navegador**:
```python
def _initialize_browser(self) -> BrowserWrapper:
    if not self._browser_wrapper:
        self._browser, self._context = self.browser_manager.get_browser(self.browser_type)
        self._page = self._context.new_page()
        self._browser_wrapper = PlaywrightWrapper(self._page)
    return self._browser_wrapper
```

---

## 4. EJECUCIÓN DE SCRAPERS

### 4.1 Ciclo Principal de Ejecución

**Bucle de Scrapers**:
```python
for scraper_type in scraper_types:
    # 1. Verificación de sesión
    # 2. Autenticación si es necesario  
    # 3. Obtención de browser_wrapper
    # 4. Creación de scraper strategy
    # 5. Ejecución del scraper
    # 6. Procesamiento de resultados
```

### 4.2 Factory Pattern para Scrapers

**ScraperStrategyFactory**:
**Archivo**: `web_scrapers/domain/entities/scraper_factory.py`

**Mapeo de Estrategias**:
```python
self._strategies = {
    (Carrier.BELL, ScraperType.MONTHLY_REPORTS): BellMonthlyReportsScraperStrategy,
    (Carrier.BELL, ScraperType.DAILY_USAGE): BellDailyUsageScraperStrategy,
    (Carrier.BELL, ScraperType.PDF_INVOICE): BellPDFInvoiceScraperStrategy,
    # ... otros carriers
}
```

**Creación de Scraper**:
```python
scraper_strategy = scraper_factory.create_scraper(
    carrier=credentials.carrier, 
    scraper_type=scraper_type, 
    browser_wrapper=browser_wrapper
)
```

### 4.3 Ejecución de Strategy

**Template Method Pattern**:
```python
def execute(self, config: ScraperConfig, billing_cycle: BillingCycle, credentials: Credentials) -> ScraperResult:
    try:
        # 1. Buscar sección de archivos
        files_section = self._find_files_section(config, billing_cycle)
        
        # 2. Descargar archivos
        downloaded_files = self._download_files(files_section, config, billing_cycle)
        
        # 3. Subir archivos al endpoint (opcional)
        # upload_result = self._upload_files_to_endpoint(downloaded_files, config, billing_cycle)
        
        # 4. Retornar resultado
        return ScraperResult(True, f"Procesados {len(downloaded_files)} archivos", file_mapping)
    except Exception as e:
        return ScraperResult(False, error=str(e))
```

---

## 5. ESTRATEGIAS ESPECÍFICAS POR CARRIER

### 5.1 Bell Scrapers - Implementación Detallada

**Archivo**: `web_scrapers/infrastructure/scrapers/bell_scrapers.py`

#### 5.1.1 BellMonthlyReportsScraperStrategy

**Flujo de `_find_files_section()`**:
```
1. _find_files_section_with_retry(max_retries=1)
   ↓
2. Para cada intento:
   a. Hover sobre "Reports" en menú principal
   b. Click en "e-report" → Abre nueva pestaña
   c. wait_for_new_tab() → Espera apertura
   d. switch_to_new_tab() → Cambia a nueva pestaña
   e. _verify_ereport_header_available() → DETECCIÓN DE CACHÉ
   f. Si header OK: Click en "standard reports"
   g. Si header FAIL: _handle_cache_recovery() → RECUPERACIÓN
```

**Detección de Error de Caché**:
```python
def _verify_ereport_header_available(self) -> bool:
    header_xpath = "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/div[1]/div[1]/ul[1]/li[2]/div[1]/span[1]/a[1]"
    is_available = self.browser_wrapper.is_element_visible(header_xpath, timeout=5000)
    
    if is_available:
        print("✅ Header de e-reports disponible")
        return True
    else:
        print("⚠️ Header de e-reports no disponible - posible error de caché")
        return False
```

**Recuperación de Caché**:
```python
def _handle_cache_recovery(self) -> bool:
    # 1. Cerrar pestañas adicionales
    if self.browser_wrapper.get_tab_count() > 1:
        self.browser_wrapper.close_all_tabs_except_main()
    
    # 2. Limpiar datos del navegador (cookies, localStorage, sessionStorage)
    self.browser_wrapper.clear_browser_data(
        clear_cookies=True, 
        clear_storage=True, 
        clear_cache=True
    )
    
    # 3. La sesión se pierde automáticamente
    # 4. SessionManager detectará pérdida en próximo refresh_session_status()
    # 5. Re-login automático en siguiente iteración
    
    return True
```

**Flujo de `_download_files()`**:
```
1. Para cada tipo de reporte ["Cost Overview", "Enhanced User Profile Report", "Usage Overview"]:
   a. Seleccionar reporte en dropdown
   b. Configurar fechas (start_date, end_date del billing_cycle)
   c. Click en "Apply"
   d. Click en icono de Excel para generar reporte
   
2. Esperar tabla de status de reportes (120 segundos timeout)

3. Para cada fila de la tabla:
   a. Click en link de descarga
   b. Esperar descarga con page.expect_download()
   c. Guardar archivo con nombre único
   d. Crear FileDownloadInfo
   
4. Cerrar pestaña e-report
5. Regresar a pestaña principal
6. _reset_to_main_screen() → Click en logo de Bell
```

**Reset a Pantalla Principal**:
```python
def _reset_to_main_screen(self):
    logo_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/a[1]"
    self.browser_wrapper.click_element(logo_xpath)
    self.browser_wrapper.wait_for_page_load()
```

#### 5.1.2 BellDailyUsageScraperStrategy

**Flujo Específico**:
```
1. Hover sobre "Usage" en menú
2. Click en "Subscriber account usage details"
3. Búsqueda de cuenta específica (hardcoded: "502462125")
4. Click en "View subscribers"
5. Re-hover "Usage" 
6. Click en "Billing account usage details"
7. Seleccionar "All usage" en dropdown
8. Click en pestaña "Download"
9. Click en "Download all pages"
10. Manejar descarga directa
11. _reset_to_main_screen()
```

#### 5.1.3 BellPDFInvoiceScraperStrategy

**Flujo Específico**:
```
1. Hover sobre "Billing" en menú
2. Click en "Download PDF"
3. Selección de cuenta (opcional)
4. Click en radio button "Complete invoice"
5. Selección de período usando billing_cycle dates
6. Click en primer botón "Download"
7. Esperar hasta 3 minutos por generación
8. Click en segundo botón "Download now"
9. _reset_to_main_screen()
```

### 5.2 Auth Strategies por Carrier

**Bell Auth Strategy**:
**Archivo**: `web_scrapers/infrastructure/playwright/auth_strategies.py`

**Flujo de Login**:
```
1. Navegar a CarrierPortalUrls.BELL
2. Ingresar email en campo específico
3. Ingresar password
4. Click en botón login
5. Manejo de 2FA si aparece (_handle_2fa_if_present())
6. Verificación final con is_logged_in()
```

**Manejo de 2FA**:
- Detección automática de formulario 2FA
- Selección de opción SMS
- Polling de webhook para recibir código
- Ingreso automático del código
- Verificación de éxito

**Verificación de Sesión Activa**:
```python
def is_logged_in(self) -> bool:
    user_button_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/logout[1]/div[1]/button[1]"
    return self.browser_wrapper.is_element_visible(user_button_xpath, timeout=10000)
```

---

## 6. MANEJO DE ERRORES Y RECUPERACIÓN

### 6.1 Niveles de Manejo de Errores

**Nivel 1 - Scraper Strategy**:
- Try/catch en métodos individuales
- Retorno de `ScraperResult` con error
- Logging específico de errores

**Nivel 2 - Session Manager**:
- Verificación continua de estado de sesión
- Re-autenticación automática
- Manejo de errores de navegador

**Nivel 3 - Sistema Principal**:
- Try/catch en bucle principal
- Continuación con próximo scraper en caso de error
- Limpieza final garantizada

### 6.2 Casos Específicos de Error

**Error de Caché (Bell e-reports)**:
```
DETECCIÓN → LIMPIEZA → PÉRDIDA DE SESIÓN → RE-LOGIN → REINTENTO
```

**Error de Autenticación**:
```
DETECCIÓN → LOGOUT → LIMPIAR AUTH STRATEGY → RE-LOGIN
```

**Error de Navegador**:
```
DETECCIÓN → CERRAR PESTAÑAS → REINICIALIZAR BROWSER → CONTINUAR
```

**Error de Red/Timeout**:
```
DETECCIÓN → ESPERA → REINTENTO → FALL BACK A SIGUIENTE SCRAPER
```

### 6.3 Recuperación Automática

**SessionManager.refresh_session_status()**:
```python
def refresh_session_status(self) -> bool:
    try:
        if not self._current_auth_strategy:
            return False

        # Verificar si hay elementos de login visibles en la pantalla
        is_active = self._current_auth_strategy.is_logged_in()

        # Si no hay elementos visibles y hay sesión activa, cerrar sesión
        if not is_active:
            if self.session_state.is_logged_in():
                self.session_state.set_logged_out()
                self._current_auth_strategy = None
            return False

        return is_active

    except Exception as e:
        error_msg = f"Error al verificar el estado de la sesión: {str(e)}"
        self.session_state.set_error(error_msg)
        return False
```

---

## 7. LIMPIEZA Y FINALIZACIÓN

### 7.1 Flujo de Limpieza Final

**Después del bucle de scrapers**:
```python
print(f"\n5. Limpieza del sistema...")

if session_manager.is_logged_in():
    logout_success = session_manager.logout()
    if logout_success:
        print(f"   ✓ Logout exitoso")
    else:
        print(f"   ✗ Error en logout")

session_manager.cleanup()
print(f"   ✓ Limpieza completada")
```

### 7.2 SessionManager.cleanup()

**Proceso de Limpieza**:
```python
def cleanup(self) -> None:
    # 1. Forzar logout si hay sesión activa
    if self.session_state.is_logged_in():
        self.force_logout()

    # 2. Limpiar referencias
    self._current_auth_strategy = None
    self._browser_wrapper = None

    # 3. Cerrar recursos de Playwright
    if self._page:
        self._page.close()
        self._page = None

    if self._context:
        self._context.close()
        self._context = None

    if self._browser:
        self._browser.close()
        self._browser = None
```

### 7.3 Garantías del Sistema

**Recursos Garantizados de Limpieza**:
1. **Sesiones**: Logout automático
2. **Páginas**: Cierre de todas las pestañas
3. **Contextos**: Cierre de contexto de navegador
4. **Navegadores**: Cierre de instancia de navegador
5. **Referencias**: Limpieza de objetos en memoria

**Finally Blocks**:
- Cada scraper mantiene sesión abierta para siguiente tarea
- Solo al final se hace limpieza completa
- Garantiza recursos liberados incluso en caso de excepción

---

## BIFURCACIONES Y CASOS ESPECIALES

### Caso 1: Primera Ejecución
```
Sin sesión → Login requerido → Inicialización completa del navegador
```

### Caso 2: Sesión Existente con Mismas Credenciales
```
Sesión activa → Verificación exitosa → Uso directo
```

### Caso 3: Sesión Existente con Credenciales Diferentes
```
Sesión activa → Logout → Login con nuevas credenciales
```

### Caso 4: Pérdida de Sesión Durante Ejecución
```
Sesión perdida → Detección en refresh_session_status() → Re-login automático
```

### Caso 5: Error de Caché (Bell Specific)
```
Error detectado → Limpieza de datos → Pérdida de sesión → Re-login → Reintento
```

### Caso 6: Error Fatal de Navegador
```
Error crítico → Skip scraper actual → Continuar con siguiente → Limpieza al final
```

---

## FLUJO DE DATOS

### Entrada del Sistema
```
ScraperConfig + BillingCycle + Credentials → ScraperStrategy.execute()
```

### Procesamiento
```
Portal Navigation → File Download → FileDownloadInfo Creation
```

### Salida del Sistema
```
ScraperResult {
    success: bool,
    message: string,
    files: List[FileDownloadInfo],
    error: string
}
```

### Persistencia
```
Archivos descargados → DOWNLOADS_DIR → Procesamiento posterior opcional
```

---

Este flujo garantiza la robustez del sistema manteniendo sesiones activas para eficiencia, manejando errores específicos por carrier, y asegurando limpieza de recursos en todos los casos.