# COMPONENTES CLAVE Y CONFIGURACIÓN

## Tabla de Contenidos

1. [SessionManager - Orquestador de Sesiones](#1-sessionmanager---orquestador-de-sesiones)
2. [Browser Wrapper - Abstracción de Navegador](#2-browser-wrapper---abstracción-de-navegador)
3. [Scraper Strategies - Implementaciones por Carrier](#3-scraper-strategies---implementaciones-por-carrier)
4. [File Upload Service - Carga Universal](#4-file-upload-service---carga-universal)
5. [Configuración y Variables de Entorno](#5-configuración-y-variables-de-entorno)
6. [Entidades Pydantic](#6-entidades-pydantic)

---

## 1. SessionManager - Orquestador de Sesiones

### Ubicación
`web_scrapers/application/session_manager.py` (~200 líneas)

### Responsabilidad
Gestionar el ciclo de vida completo de sesiones de navegador, incluyendo:
- Login/logout inteligente
- Reutilización de sesiones
- Cambios de carrier
- Detección de sesión perdida
- Manejo de errores

### Atributos Principales

```python
class SessionManager:
    browser_manager: BrowserManager          # Factory de browsers
    browser_type: Optional[Navigators]       # Chrome, Firefox, Edge, Safari
    session_state: SessionState              # Estado actual

    _auth_strategies: Dict[Carrier, Type]    # Mapeo de estrategias
    _current_auth_strategy: Optional[AuthBaseStrategy]
    _browser_wrapper: Optional[BrowserWrapper]
    _browser: Optional[Browser]
    _context: Optional[BrowserContext]
    _page: Optional[Page]
```

### Métodos Principales

#### login(credentials: Credentials) -> bool
```python
"""
Inicia sesión con lógica inteligente:
1. Si ya hay sesión con mismas credenciales → reutilizar
2. Si hay sesión con credenciales diferentes → logout + login
3. Si no hay sesión → login nuevo

Args:
    credentials: Credenciales con usuario, pwd, carrier

Returns:
    True si login exitoso, False si falló
"""
```

**Uso:**
```python
session_manager = SessionManager(browser_type=Navigators.CHROME)
credentials = Credentials(
    id=uuid4(),
    username="user@bell.ca",
    password="encrypted_pwd",
    carrier=Carrier.BELL
)
success = session_manager.login(credentials)
```

#### logout() -> bool
```python
"""
Cierra sesión actual de forma segura.
- Ejecuta logout en estrategia
- Limpia estado
- Mantiene browser abierto para posible reutilización

Returns:
    True si logout exitoso
"""
```

#### is_logged_in() -> bool
```python
"""
Verifica si hay sesión activa llamando a refresh_session_status().

Returns:
    True si está logueado
"""
```

#### get_browser_wrapper() -> Optional[BrowserWrapper]
```python
"""
Retorna el wrapper del navegador para el scraper.
Es el que se pasa a ScraperStrategy.

Returns:
    PlaywrightWrapper para usar en scraping
"""
```

#### refresh_session_status() -> bool
```python
"""
Verifica si la sesión actual sigue siendo válida.
- Busca elementos de login en página
- Si aparecen → sesión perdida
- Actualiza session_state

Returns:
    True si sesión sigue válida
"""
```

#### get_current_carrier() -> Optional[Carrier]
```python
"""Retorna el carrier de la sesión actual (BELL, TELUS, etc)"""
```

#### get_current_credentials() -> Optional[Credentials]
```python
"""Retorna las credenciales de la sesión actual"""
```

#### clear_error() -> None
```python
"""
Limpia estado de error y vuelve a estado correcto
basado en auth actual.
"""
```

#### cleanup() -> None
```python
"""
Limpieza completa:
- Force logout
- Cerrar todas las páginas
- Cerrar contexto
- Cerrar browser
- Liberar memoria

IMPORTANTE: Llamar al final de cada ciclo de trabajo
"""
```

### Ejemplo de Uso Completo

```python
with SessionManager(browser_type=Navigators.CHROME) as sm:
    # Login
    creds_bell = Credentials(..., carrier=Carrier.BELL)
    sm.login(creds_bell)  # Loguea en Bell

    # Usar browser para scraping
    browser = sm.get_browser_wrapper()
    scraper1 = BellMonthlyScraperStrategy(browser)
    result1 = scraper1.execute(config1, billing1, creds_bell)

    # Cambiar carrier
    creds_telus = Credentials(..., carrier=Carrier.TELUS)
    sm.login(creds_telus)  # Logout Bell + Login Telus automáticamente

    # Usar mismo browser para otro carrier
    scraper2 = TelusDailyScraperStrategy(browser)
    result2 = scraper2.execute(config2, billing2, creds_telus)

    # Context manager: cleanup automático al salir
```

---

## 2. Browser Wrapper - Abstracción de Navegador

### Arquitectura

```
BrowserWrapper (Interfaz Abstracta)
   ↓
PlaywrightWrapper (Implementación)
   ↓
Playwright Sync API (libreply.sync)
   ↓
Chromium/Firefox/Safari
```

### Ubicación
- Interfaz: `web_scrapers/domain/entities/browser_wrapper.py`
- Implementación: `web_scrapers/infrastructure/playwright/browser_wrapper.py` (278 líneas)

### Métodos (30+)

#### Navegación
```python
goto(url: str, wait_until: str = "networkidle") -> Page
    """Navega a URL"""

back() -> Page
forward() -> Page
reload(wait_until: str = "networkidle") -> Page
    """Navegación histórica y recarga"""

get_current_url() -> str
    """Obtiene URL actual"""
```

#### Esperas
```python
wait_for_page_load(timeout: int = 30000) -> bool
    """Espera a que la página cargue"""

wait_for_selector(selector: str, timeout: int = 30000) -> bool
    """Espera a que elemento esté presente"""

wait_for_navigation(timeout: int = 30000) -> None
    """Espera a que página navegue"""

wait_for_timeout(timeout: int) -> None
    """Espera X milisegundos"""
```

#### Interacción

```python
click(selector: str) -> None
fill(selector: str, text: str) -> None
select(selector: str, value: str) -> None
    """Llena select dropdown"""

hover(selector: str) -> None
type(text: str) -> None
    """Escribe texto sin limpiar primero"""

keyboard_press(key: str) -> None
    """Presiona tecla (Enter, Tab, etc)"""
```

#### Obtención de Datos

```python
get_text(selector: str) -> str
    """Obtiene texto de elemento"""

get_attribute(selector: str, attr: str) -> Optional[str]
    """Obtiene atributo HTML (href, data-*, etc)"""

get_page_content() -> str
    """Obtiene HTML completo"""

evaluate(script: str) -> Any
    """Ejecuta JavaScript arbitrario"""
```

#### Gestión de Pestañas

```python
get_tab_count() -> int
    """Cuántas pestañas abiertas"""

switch_to_tab(index: int) -> None
    """Cambia a pestaña N"""

switch_to_previous_tab() -> None
close_current_tab() -> None
    """Cierra pestaña actual"""

click_and_switch_to_new_tab(selector: str, timeout: int) -> None
    """Clickea elemento que abre nueva tab, y cambia a ella"""
```

#### Descargas

```python
download_file(selector: str, timeout: int = 30000) -> str
    """
    Clickea selector que inicia descarga y espera a que termine.
    Retorna path del archivo descargado.
    """

get_downloads() -> List[str]
    """Obtiene lista de descargas"""

wait_for_download(timeout: int = 30000) -> str
    """Espera a descarga sin necesidad de click previo"""
```

#### Limpieza

```python
clear_cache() -> None
    """Limpia cache de navegador"""

clear_cookies() -> None
    """Borra todas las cookies"""

clear_local_storage() -> None
    """Borra localStorage"""
```

#### Debugging

```python
take_screenshot(name: str) -> str
    """Captura screenshot y lo guarda"""

pause() -> None
    """Pausa ejecución (útil para debugging)"""

get_console_messages() -> List[str]
    """Obtiene mensajes de consola del navegador"""
```

### Implementación PlaywrightWrapper

```python
class PlaywrightWrapper(BrowserWrapper):
    def __init__(self, page: Page):
        self.page = page  # Página Playwright actual
        self.downloads_dir = None

    def goto(self, url: str, wait_until: str = "networkidle"):
        return self.page.goto(url, wait_until=wait_until)

    def click(self, selector: str):
        self.page.click(selector)

    # ... resto de métodos ...
```

### Ejemplo de Uso

```python
# Inicializado automáticamente por SessionManager
browser_wrapper = session_manager.get_browser_wrapper()

# Navegación
browser_wrapper.goto("https://www.bell.ca")
browser_wrapper.wait_for_page_load()

# Interacción
browser_wrapper.fill("input[name=email]", "user@example.com")
browser_wrapper.fill("input[name=password]", "pwd123")
browser_wrapper.click("button[type=submit]")

# Espera
browser_wrapper.wait_for_selector(".dashboard", timeout=10000)

# Obtención de datos
title = browser_wrapper.get_text(".page-title")

# Descarga
file_path = browser_wrapper.download_file("a.download-btn")

# Screenshot
browser_wrapper.take_screenshot("login_success")
```

---

## 3. Scraper Strategies - Implementaciones por Carrier

### Estructura de Herencia

```
ScraperBaseStrategy (Abstracto)
   ├─ MonthlyReportsScraperStrategy (Abstract)
   ├─ DailyUsageScraperStrategy (Abstract)
   └─ PDFInvoiceScraperStrategy (Abstract)
      │
      ├─ BellMonthlyReportsScraperStrategy ✓
      ├─ BellDailyUsageScraperStrategy ✓
      ├─ BellPDFInvoiceScraperStrategy ✓
      │
      ├─ TelusMonthlyReportsScraperStrategy ✓
      ├─ TelusDailyUsageScraperStrategy ✓
      ├─ TelusPDFInvoiceScraperStrategy ✓
      │
      ├─ RogersMonthlyReportsScraperStrategy ✓
      │ ... (etc para todos los carriers)
```

### Interfaz Base - ScraperBaseStrategy

```python
class ScraperBaseStrategy(ABC):
    def __init__(self, browser_wrapper: BrowserWrapper):
        self.browser_wrapper = browser_wrapper
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def execute(
        self,
        config: ScraperConfig,
        billing_cycle: BillingCycle,
        credentials: Credentials
    ) -> ScraperResult:
        """Punto de entrada principal del scraper"""
        raise NotImplementedError()

    def _create_file_mapping(
        self,
        downloaded_files: List[FileDownloadInfo]
    ) -> List[FileMappingInfo]:
        """Helper: convierte FileDownloadInfo → FileMappingInfo"""

    def _extract_zip_files(
        self,
        zip_file_path: str,
        extract_to_dir: Optional[str] = None
    ) -> List[str]:
        """Helper: extrae ZIP con flattening"""

    def _upload_files_to_endpoint(
        self,
        files: List[FileDownloadInfo],
        billing_cycle: BillingCycle,
        upload_type: str
    ) -> bool:
        """Helper: carga archivos a API externa"""
```

### Métodos Abstractos a Implementar

```python
# En cada estrategia concreta:

def _find_files_section(
    self,
    config: ScraperConfig,
    billing_cycle: BillingCycle
) -> Optional[Any]:
    """
    Navega a la sección de archivos del portal.
    Cada carrier tiene su propia estructura.

    Returns:
        Dict con metadata de la sección (ej: {"section": "monthly", "ready": True})
        None si no encuentra
    """

def _download_files(
    self,
    files_section: Any,
    config: ScraperConfig,
    billing_cycle: BillingCycle
) -> List[FileDownloadInfo]:
    """
    Descarga archivos del portal.

    Returns:
        Lista de FileDownloadInfo con paths de archivos descargados
    """
```

### Ejemplo: BellMonthlyReportsScraperStrategy

```python
class BellMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para Bell Canada"""

    def __init__(self, browser_wrapper: BrowserWrapper):
        super().__init__(browser_wrapper)
        self.report_dictionary = {
            "cost_overview": None,
            "enhanced_user_profile_report": None,
            "usage_overview": None,
        }

    def _find_files_section(self, config, billing_cycle):
        """
        Navegar:
        1. Hover en Reports menu
        2. Click e-reports
        3. Switch a nueva tab
        4. Click standard reports
        5. Esperar carga
        """
        return self._find_files_section_with_retry(
            config,
            billing_cycle,
            max_retries=1
        )

    def _download_files(self, files_section, config, billing_cycle):
        """
        Descargar:
        1. Crear dict de BillingCycleFiles
        2. Para cada archivo:
           - Buscar en página
           - Click descargar
           - Esperar descarga
           - Crear FileDownloadInfo
        3. Retornar lista
        """
        # Implementación específica de Bell
        pass

    def execute(self, config, billing_cycle, credentials):
        """Implementa el template method"""
        # Llama a _find_files_section
        # Llama a _download_files
        # Llama a _extract_zip_files (si aplica)
        # Llama a _create_file_mapping
        # Llama a _upload_files_to_endpoint
        # Retorna ScraperResult
```

### Características Específicas por Carrier

#### Bell (Más Avanzada - 835 líneas)
- SMS 2FA integration
- Detección de errores de cache
- Navegación de e-reports compleja
- Manejo de múltiples formatos
- Retry automático

#### Telus (Generación Compleja - 977 líneas)
- Generación dinámica de reportes
- Monitoreo de cola ("In Queue" → "Ready")
- Múltiples formatos (CSV, Excel)
- Selección de período dinámico
- Esperas largas (1 minuto para actualización)

#### Rogers, AT&T, T-Mobile, Verizon
- Implementaciones más simples
- Autenticación estándar
- Descarga directa de archivos
- Menos validaciones carrier-específicas

---

## 4. File Upload Service - Carga Universal

### Ubicación
`web_scrapers/infrastructure/services/file_upload_service.py` (150 líneas)

### Responsabilidad
Carga universal de archivos descargados a API externa, con routing automático por tipo.

### Atributos

```python
class FileUploadService:
    api_base_url: str        # https://api.expertel.com
    api_key: str            # Bearer token de API
    logger: Logger
```

### Métodos Principales

#### upload_files_batch()

```python
def upload_files_batch(
    self,
    files: List[FileDownloadInfo],
    billing_cycle: BillingCycle,
    upload_type: str,  # 'monthly', 'daily_usage', 'pdf_invoice'
    additional_data: Optional[Dict] = None
) -> bool:
    """
    Carga múltiples archivos a API externa.

    Args:
        files: Archivos a cargar
        billing_cycle: Ciclo de facturación con IDs
        upload_type: Tipo de upload (determina endpoint)
        additional_data: Datos extra (no usado actualmente)

    Returns:
        True si todos los archivos se cargaron exitosamente
        False si al menos uno falló
    """
```

**Lógica:**
```python
success_count = 0
for i, file_info in enumerate(files, 1):
    if self._upload_single_file(file_info, billing_cycle, upload_type):
        success_count += 1

return success_count == len(files)
```

#### _upload_single_file()

```python
def _upload_single_file(
    self,
    file_info: FileDownloadInfo,
    billing_cycle: BillingCycle,
    upload_type: str
) -> bool:
    """
    Carga un archivo individual.

    Steps:
    1. Obtener config del tipo (URL template, content-type)
    2. Verificar que archivo tiene mapping en BD
    3. Construir URL final
    4. POST con headers y file multipart
    5. Verificar respuesta 200/201

    Returns:
        True si exitoso
    """
```

#### _get_upload_config()

```python
def _get_upload_config(
    self,
    upload_type: str,
    file_info: FileDownloadInfo,
    billing_cycle: BillingCycle
) -> Optional[Dict[str, Any]]:
    """
    Obtiene configuración para cada tipo de upload.

    Tipos soportados:
    - 'monthly': /api/v1/accounts/billing-cycles/{cycle_id}/files/{file_id}/upload-file/
    - 'daily_usage': /api/v1/accounts/billing-cycles/{cycle_id}/daily-usage/
    - 'pdf_invoice': /api/v1/accounts/billing-cycles/{cycle_id}/pdf-invoice/

    Returns:
        {
            'url_template': '...',
            'file_id_attr': 'billing_cycle_file',
            'content_type': 'application/pdf',
            'description': 'monthly report'
        }
    """
```

#### _get_headers()

```python
def _get_headers(self, billing_cycle: BillingCycle) -> Dict[str, str]:
    """
    Construye headers de request incluyendo:
    - x-api-key: Token de autorización
    - x-workspace-id: ID del workspace
    - x-client-id: ID del cliente
    - Accept: application/json

    Returns:
        Headers dict para requests.post()
    """
```

### Flujo de Upload Completo

```
upload_files_batch([file1, file2, file3], billing_cycle, 'monthly')
│
├─ for each file:
│  │
│  ├─ _get_upload_config('monthly', file1)
│  │  └─ url = "/api/v1/accounts/bc-123/files/f-456/upload-file/"
│  │
│  ├─ _get_headers(billing_cycle)
│  │  └─ {x-api-key, x-workspace-id, x-client-id}
│  │
│  ├─ Validar que file1.billing_cycle_file existe
│  │
│  ├─ POST https://api.expertel.com/api/v1/.../upload-file/
│  │  ├─ Headers
│  │  ├─ File multipart
│  │  └─ Timeout: 300s
│  │
│  ├─ Response 200/201? success_count++
│  │
│  └─ else: log error
│
├─ Log summary
└─ return success_count == total_count
```

### Ejemplo de Uso

```python
from web_scrapers.infrastructure.services.file_upload_service import FileUploadService

# Dentro de ScraperBaseStrategy._upload_files_to_endpoint()
upload_service = FileUploadService()

success = upload_service.upload_files_batch(
    files=downloaded_files,  # [FileDownloadInfo, ...]
    billing_cycle=billing_cycle,  # BillingCycle con IDs
    upload_type='monthly'
)

if success:
    self.logger.info("All files uploaded successfully")
else:
    self.logger.error("Some files failed to upload")
```

---

## 5. Configuración y Variables de Entorno

### Ubicación
`.env.example` (plantilla) → `.env` (producción)

### Variables Requeridas

#### API Externa

```env
# URL base de API externa para uploads
EIQ_BACKEND_API_BASE_URL=https://api.expertel.com

# Bearer token para autorización
EIQ_BACKEND_API_KEY=your_bearer_token_here
```

**Uso en Código:**
```python
self.api_base_url = os.getenv("EIQ_BACKEND_API_BASE_URL", "https://api.expertel.com")
self.api_key = os.getenv("EIQ_BACKEND_API_KEY", "")
```

#### Base de Datos

```env
# PostgreSQL (recomendado)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=expertel_dev
DB_USERNAME=expertel
DB_PASSWORD=your_password

# O SQLite para desarrollo
DATABASE_URL=sqlite:///db.sqlite3
```

#### Django

```env
# Secret key para session signing
DJANGO_SECRET_KEY=your_very_secret_key_here

# Debug mode (False en producción)
DJANGO_DEBUG_MODE=True

# Hosts permitidos
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,*.example.com

# CORS
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000,https://app.example.com
```

#### Seguridad

```env
# Clave para encriptación de credenciales (Fernet)
CRYPTOGRAPHY_KEY=your_base64_encoded_key_here

# Usado por django-allauth y DRF
SECURE_SSL_REDIRECT=False  # True en producción
SESSION_COOKIE_SECURE=False  # True en producción
```

#### Browser (Opcional)

```env
# Tipo de navegador: chrome, firefox, edge, safari
BROWSER_TYPE=chrome

# Headless mode
BROWSER_HEADLESS=false

# Retraso en milisegundos entre comandos (debugging)
BROWSER_SLOW_MO=0

# Timeout global en milisegundos
BROWSER_TIMEOUT=30000

# Viewport
BROWSER_VIEWPORT_WIDTH=1920
BROWSER_VIEWPORT_HEIGHT=1080
```

### Uso en Código

#### En Services
```python
import os

class FileUploadService:
    def __init__(self):
        self.api_base_url = os.getenv("EIQ_BACKEND_API_BASE_URL", "default")
        self.api_key = os.getenv("EIQ_BACKEND_API_KEY", "")
```

#### En Django Settings
```python
# config/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv("DJANGO_DEBUG_MODE", "True") == "True"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure")
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'NAME': os.getenv('DB_NAME', 'expertel_dev'),
        'USER': os.getenv('DB_USERNAME', 'expertel'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'password'),
    }
}
```

### Setup Inicial

```bash
# 1. Copiar template
cp .env.example .env

# 2. Editar .env con valores reales
nano .env

# 3. Generar CRYPTOGRAPHY_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copiar output a CRYPTOGRAPHY_KEY en .env

# 4. Migrar BD
python manage.py makemigrations
python manage.py migrate

# 5. Crear superuser
python manage.py createsuperuser

# 6. Testear
python main.py
```

---

## 6. Entidades Pydantic

### Ubicación
`web_scrapers/domain/entities/models.py`

### Características
- Validación automática
- Type hints completos
- Serialización JSON
- Conversión a BD fácil

### Jerarquía Completa

```python
# CLIENTE Y WORKSPACE
class Client(BaseModel):
    id: UUID
    name: str
    workspaces: List['Workspace'] = []

class Workspace(BaseModel):
    id: UUID
    name: str
    client: Optional[Client] = None
    accounts: List['Account'] = []

# CUENTA Y CICLOS
class Account(BaseModel):
    id: UUID
    number: str
    account_type: AccountType  # CORPORATE, INDIVIDUAL
    carrier: Carrier  # BELL, TELUS, etc
    is_active: bool = True
    workspace: Optional[Workspace] = None
    billing_cycles: List['BillingCycle'] = []

class BillingCycle(BaseModel):
    id: UUID
    account: Optional[Account] = None
    start_date: datetime
    end_date: datetime
    status: BillingCycleStatus  # ACTIVE, COMPLETED, CANCELLED
    billing_cycle_files: List['BillingCycleFile'] = []
    daily_usage_files: List['BillingCycleDailyUsageFile'] = []
    pdf_files: List['BillingCyclePDFFile'] = []

# ARCHIVOS POR TIPO
class BillingCycleFile(BaseModel):
    id: UUID
    billing_cycle: Optional[BillingCycle] = None
    carrier_report: Optional['CarrierReport'] = None
    status: FileStatus  # to_be_fetched, ready, processing, etc
    download_url: Optional[str] = None

class BillingCycleDailyUsageFile(BaseModel):
    id: UUID
    billing_cycle: Optional[BillingCycle] = None
    status: FileStatus

class BillingCyclePDFFile(BaseModel):
    id: UUID
    billing_cycle: Optional[BillingCycle] = None
    status: FileStatus

# CONFIGURACIÓN
class ScraperConfig(BaseModel):
    account: Account
    carrier: Carrier
    scraper_type: ScraperType  # MONTHLY_REPORTS, DAILY_USAGE, PDF_INVOICE
    additional_config: Dict[str, Any] = {}

class Credentials(BaseModel):
    id: UUID
    username: str
    password: str  # Almacenado encriptado en BD
    carrier: Carrier

# DESCARGAS
class FileDownloadInfo(BaseModel):
    file_id: str
    file_name: str
    file_path: str
    download_url: str
    download_timestamp: datetime
    billing_cycle_file: Optional[BillingCycleFile] = None
    daily_usage_file: Optional[BillingCycleDailyUsageFile] = None
    pdf_file: Optional[BillingCyclePDFFile] = None

class FileMappingInfo(BaseModel):
    file_id: str
    file_name: str
    file_path: str
    download_url: str
    billing_cycle_file_id: Optional[UUID] = None
    carrier_report_name: Optional[str] = None
    daily_usage_file_id: Optional[UUID] = None
    pdf_file_id: Optional[UUID] = None

# RESULTADO
class ScraperResult(BaseModel):
    success: bool
    message: str = ""
    files: List[FileMappingInfo] = []
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# SESIÓN
class SessionState(BaseModel):
    status: SessionStatus  # LOGGED_IN, LOGGED_OUT, ERROR
    carrier: Optional[Carrier] = None
    credentials: Optional[Credentials] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None

# TRABAJO
class ScraperJob(BaseModel):
    id: UUID
    type: ScraperType
    status: ScraperJobStatus  # PENDING, RUNNING, SUCCESS, ERROR, SCHEDULED
    available_at: datetime
    created_at: datetime
    updated_at: datetime
    message: Optional[str] = None
    error_details: Optional[str] = None

class ScraperJobCompleteContext(BaseModel):
    """Contexto completo de un trabajo para procesamiento"""
    scraper_job: ScraperJob
    scraper_config: ScraperConfig
    billing_cycle: BillingCycle
    credential: Credentials  # Relacionada a Account
    account: Account
    carrier: Carrier
```

### Validación Automática

```python
# Estos fallan automáticamente si datos inválidos
config = ScraperConfig(
    account=account,
    carrier=Carrier.BELL,  # Validado contra enum
    scraper_type=ScraperType.MONTHLY_REPORTS,  # Validado contra enum
)

# Conversión automática
billing_cycle = BillingCycle(
    start_date="2024-11-01",  # String → datetime
    end_date="2024-11-30",
    status="active"  # String → BillingCycleStatus enum
)

# Serialización a JSON
json_str = config.model_dump_json()

# Serialización a dict
dict_data = config.model_dump()
```

---

## Resumen de Componentes

| Componente | Líneas | Responsabilidad | Complejidad |
|-----------|--------|-----------------|-------------|
| SessionManager | 200 | Orquestación de sesiones | Alta |
| BrowserWrapper | 278 | Abstracción de Playwright | Alta |
| ScraperBaseStrategy | 300 | Template method base | Media |
| BellScraper | 835 | Scraping Bell con 2FA | Muy Alta |
| TelusScraper | 977 | Scraping Telus con queue | Muy Alta |
| FileUploadService | 150 | Carga universal | Media |
| Entidades Pydantic | 400 | Validación y mapping | Media |

**Total: ~4,000+ líneas de código principal**

---

**Creado:** 2025-11-28
**Versión:** 1.0