# ARQUITECTURA COMPLETA DEL SISTEMA

## Resumen Ejecutivo

**Expertel Web Scrapers** es un sistema empresarial de **Clean Architecture** que automatiza el scraping de portales de telecomunicaciones (6 operadores × 3 tipos de reportes = 18 estrategias).

- **Rama activa:** `feature/session-manager-and-strategies`
- **Total código:** ~10,386 líneas en 89 archivos Python
- **Framework:** Django 5.1.4 + Playwright 1.53.0
- **Patrones:** Strategy, Factory, Repository, Template Method, CQRS, Decorator, Singleton

---

## 1. ARQUITECTURA EN CAPAS (CLEAN ARCHITECTURE)

### Estructura Jerárquica

```
┌─────────────────────────────────────────────────────────────────┐
│                     PUNTO DE ENTRADA                            │
│  main.py (ScraperJobProcessor) / manage.py (Django CLI)        │
│  authenticator_webhook/sms2fa.py (Flask 2FA Service)           │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│           APPLICATION LAYER (casos de uso)                      │
│  • session_manager.py (Orquestación de sesiones)               │
│  • scraper_job_service.py (Gestión de trabajos)                │
│  • safe_scraper_job_service.py (Wrapper async-safe)            │
│  • cqrs/commands/ (Comandos de negocio)                         │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│           DOMAIN LAYER (lógica de negocio pura)                │
│  • entities/models.py (Entidades Pydantic: Client, Account...)  │
│  • entities/auth_strategies.py (Interfaz base de autenticación) │
│  • entities/scraper_strategies.py (Interfaz base de scrapers)   │
│  • entities/browser_wrapper.py (Interfaz abstracta de browser)  │
│  • entities/session.py (Estado de sesión)                       │
│  • entities/scraper_factory.py (Factory pattern)                │
│  • enums.py (Enums de negocio)                                  │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│        INFRASTRUCTURE LAYER (implementación concreta)           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Django Infrastructure                                     │  │
│  │ • models.py (ORM Models)                                  │  │
│  │ • repositories.py (Repository Pattern)                    │  │
│  │ • admin.py (Django Admin Interface)                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Playwright Infrastructure                                 │  │
│  │ • browser_factory.py (Factory para browsers)              │  │
│  │ • browser_wrapper.py (PlaywrightWrapper - 278 líneas)     │  │
│  │ • auth_strategies.py (Impl. de auth por carrier)          │  │
│  │ • drivers.py (Builder pattern)                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Scrapers Infrastructure                                   │  │
│  │ • bell_scrapers.py (835 líneas - avanzado)                │  │
│  │ • telus_scrapers.py (977 líneas - generación compleja)    │  │
│  │ • rogers_scrapers.py, att_scrapers.py, etc.               │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Servicios Transversales                                   │  │
│  │ • file_upload_service.py (Carga a API externa)            │  │
│  │ • logging_config.py (Sistema de logging)                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. CAPAS DETALLADAS

### 2.1 DOMAIN LAYER (web_scrapers/domain/)

**Responsabilidad:** Lógica de negocio pura, independiente de frameworks.

#### 2.1.1 Entidades Pydantic (entities/models.py)

```python
Client
  ├─ id: UUID
  ├─ name: str
  └─ workspaces: List[Workspace]
      ├─ id: UUID
      ├─ name: str
      ├─ accounts: List[Account]
      │   ├─ id: UUID
      │   ├─ number: str
      │   ├─ account_type: AccountType (Corporate/Individual)
      │   ├─ carrier: Carrier (Bell/Telus/Rogers/AT&T/T-Mobile/Verizon)
      │   ├─ is_active: bool
      │   └─ billing_cycles: List[BillingCycle]
      │       ├─ id: UUID
      │       ├─ start_date: datetime
      │       ├─ end_date: datetime
      │       ├─ status: BillingCycleStatus
      │       ├─ billing_cycle_files: List[BillingCycleFile]
      │       ├─ daily_usage_files: List[BillingCycleDailyUsageFile]
      │       └─ pdf_files: List[BillingCyclePDFFile]

ScraperConfig
  ├─ account: Account
  ├─ carrier: Carrier
  ├─ scraper_type: ScraperType (MONTHLY_REPORTS/DAILY_USAGE/PDF_INVOICE)
  └─ additional_config: Dict[str, Any]

FileDownloadInfo
  ├─ file_id: str
  ├─ file_name: str
  ├─ file_path: str
  ├─ download_url: str
  ├─ download_timestamp: datetime
  ├─ billing_cycle_file: BillingCycleFile (opcional)
  ├─ daily_usage_file: BillingCycleDailyUsageFile (opcional)
  └─ pdf_file: BillingCyclePDFFile (opcional)

Credentials
  ├─ id: UUID
  ├─ username: str
  ├─ password: str (encriptada)
  └─ carrier: Carrier

SessionState
  ├─ status: SessionStatus (LOGGED_IN/LOGGED_OUT/ERROR)
  ├─ carrier: Optional[Carrier]
  ├─ credentials: Optional[Credentials]
  ├─ created_at: datetime
  ├─ last_activity: datetime
  └─ error_message: Optional[str]
```

#### 2.1.2 Abstracciones (Interfaces)

**AuthBaseStrategy** (entities/auth_strategies.py)
```python
class AuthBaseStrategy(ABC):
    @abstractmethod
    def login(self, credentials: Credentials) -> bool

    @abstractmethod
    def logout(self) -> bool

    @abstractmethod
    def is_logged_in(self) -> bool
```

**BrowserWrapper** (entities/browser_wrapper.py)
```python
class BrowserWrapper(ABC):
    # 30+ métodos abstractos para:
    # - Navegación (goto, back, forward, reload)
    # - Interacción (click, fill, select, hover)
    # - Esperas (wait_for_selector, wait_for_page_load, wait_for_navigation)
    # - Obtención de datos (get_text, get_attribute, get_current_url)
    # - Gestión de pestañas (switch_to_tab, close_tab, get_tab_count)
    # - Descargas (download_file, get_downloads)
    # - Gestión de caché (clear_cache, clear_cookies)
    # - Screenshots y debugging
```

**ScraperBaseStrategy** (entities/scraper_strategies.py)
```python
class ScraperBaseStrategy(ABC):
    def __init__(self, browser_wrapper: BrowserWrapper)

    @abstractmethod
    def execute(
        self,
        config: ScraperConfig,
        billing_cycle: BillingCycle,
        credentials: Credentials
    ) -> ScraperResult

    # Métodos helper utilizados por estrategias concretas:
    def _create_file_mapping(files: List[FileDownloadInfo]) -> List[FileMappingInfo]
    def _extract_zip_files(zip_path: str) -> List[str]
    def _upload_files_to_endpoint(files: List[FileDownloadInfo])
```

#### 2.1.3 Enums de Negocio (enums.py)

- **Navigators:** CHROME, FIREFOX, EDGE, SAFARI
- **CarrierPortalUrls:** URLs por operador
- **FileStatus:** to_be_fetched, ready, processing, completed, error
- **AccountType:** CORPORATE, INDIVIDUAL
- **BillingCycleStatus:** ACTIVE, COMPLETED, CANCELLED
- **ScraperType:** DAILY_USAGE, MONTHLY_REPORTS, PDF_INVOICE
- **ScraperJobStatus:** PENDING, RUNNING, SUCCESS, ERROR, SCHEDULED
- **Slugs específicos:** BellFileSlug, TelusFileSlug, RogersFileSlug, VerizonFileSlug, ATTFileSlug, TMobileFileSlug

#### 2.1.4 Factory Pattern (entities/scraper_factory.py)

```python
class ScraperStrategyFactory:
    def create_scraper(
        carrier: Carrier,
        scraper_type: ScraperType,
        browser_wrapper: BrowserWrapper
    ) -> ScraperBaseStrategy

    # Mapeo dinámico a 18 estrategias:
    # Bell: MonthlyReports, DailyUsage, PDFInvoice
    # Telus: MonthlyReports, DailyUsage, PDFInvoice
    # Rogers: MonthlyReports, DailyUsage, PDFInvoice
    # AT&T: MonthlyReports, DailyUsage, PDFInvoice
    # T-Mobile: MonthlyReports, DailyUsage, PDFInvoice
    # Verizon: MonthlyReports, DailyUsage, PDFInvoice
```

---

### 2.2 APPLICATION LAYER (web_scrapers/application/)

**Responsabilidad:** Casos de uso y orquestación de dominio.

#### 2.2.1 Session Manager (session_manager.py - ~200 líneas)

**Flujo de Sesión Inteligente:**

```
┌─ Usuario A / Carrier Bell / Credenciales X
│  └─ Session creada
│
├─ Mismo usuario / Mismo carrier / Mismas creds
│  └─ ✅ Reutilizar sesión (eficiencia)
│
├─ Mismo usuario / Mismo carrier / Creds diferentes
│  └─ Logout previo → Re-login con nuevas creds
│
├─ Usuario A / Carrier Telus
│  └─ Logout de Bell → Login en Telus
│
└─ Sesión perdida (página de login visible)
   └─ Detección automática → Re-autenticación
```

**Métodos principales:**
- `login(credentials) -> bool`: Inicia sesión inteligente
- `logout() -> bool`: Cierra sesión segura
- `is_logged_in() -> bool`: Verifica estado actual
- `get_browser_wrapper() -> BrowserWrapper`: Obtiene browser activo
- `refresh_session_status() -> bool`: Verifica si sesión aún es válida
- `get_current_carrier()`: Operador actual
- `get_current_credentials()`: Credenciales actuales

#### 2.2.2 Scraper Job Service (scraper_job_service.py - ~150 líneas)

**Responsabilidades:**
- Obtener trabajos disponibles desde BD
- Construir contexto completo del trabajo (ScraperJobCompleteContext)
- Actualizar estado de trabajo en BD
- Obtener estadísticas (available_now, future_scheduled, total_pending)

**Métodos principales:**
- `get_available_jobs_with_complete_context() -> List[ScraperJobCompleteContext]`
- `update_scraper_job_status(job_id, status, message)`
- `get_scraper_statistics() -> ScraperStatistics`

#### 2.2.3 Safe Scraper Job Service (safe_scraper_job_service.py - ~100 líneas)

**Propósito:** Wrapper que maneja el contexto async después de ejecutar Playwright.

```python
class SafeScraperJobService:
    def __init__(self, original_service: ScraperJobService)
    # Delega a original_service pero maneja contexto de forma segura
```

#### 2.2.4 CQRS Commands (cqrs/commands/)

**Patrón Command-Query Responsibility Segregation:**
- `get_monthly_reports.py`: Comando para reportes mensuales
- `get_daily_usage.py`: Comando para uso diario
- `get_pdf_invoice.py`: Comando para facturas PDF

Cada comando contiene la lógica de su caso de uso específico.

---

### 2.3 INFRASTRUCTURE LAYER (web_scrapers/infrastructure/)

#### 2.3.1 Django Infrastructure (django/)

**Models (models.py)**
- Equivalentes ORM de todas las entidades Pydantic
- Soporte para Foreign Keys, Many-to-Many
- Django Choices para enums
- JSON Fields para metadata flexible

**Repositories (repositories.py)**
- Pattern Repository: abstracción de acceso a datos
- Métodos: create, update, delete, get_by_id, filter_by, get_all
- Desacoplamiento entre lógica de negocio y BD

**Admin Interface (admin.py)**
- Django Admin para gestión de:
  - Clients, Workspaces, Accounts
  - BillingCycles y archivos
  - Credentials (con encriptación)
  - ScraperJobs y estadísticas

#### 2.3.2 Playwright Infrastructure (playwright/)

**Browser Factory (browser_factory.py - 207 líneas)**
```python
class BrowserManager:
    def get_browser(browser_type: Navigators) -> Tuple[Browser, BrowserContext]

    # Soporta:
    # - Chrome, Firefox, Edge, Safari
    # - Stealth plugin (anti-detección)
    # - Inyección de scripts
    # - Singleton pattern (reutilización)
```

**Browser Wrapper (browser_wrapper.py - 278 líneas)**

Implementación concreta de BrowserWrapper usando Playwright Sync API:

```
Métodos de Navegación:
├─ goto(url, wait_until)
├─ back(), forward(), reload()
├─ wait_for_page_load()
├─ wait_for_selector(selector, timeout)
├─ wait_for_navigation()
└─ get_current_url()

Métodos de Interacción:
├─ click(selector/xpath)
├─ click_and_switch_to_new_tab(selector, timeout)
├─ fill(selector, text)
├─ select(selector, value)
├─ hover(selector)
├─ type(text)
└─ keyboard_press(key)

Métodos de Obtención de Datos:
├─ get_text(selector)
├─ get_attribute(selector, attr)
├─ get_page_content()
└─ evaluate(script)

Métodos de Gestión de Pestañas:
├─ switch_to_tab(index)
├─ switch_to_previous_tab()
├─ close_current_tab()
└─ get_tab_count()

Métodos de Descarga:
├─ download_file(selector, timeout)
├─ get_downloads()
└─ wait_for_download(timeout)

Métodos de Limpieza:
├─ clear_cache()
├─ clear_cookies()
└─ clear_local_storage()

Métodos de Debugging:
├─ take_screenshot(name)
├─ pause()
└─ get_console_messages()
```

**Auth Strategies (auth_strategies.py - 43,650 líneas)**

Implementaciones concretas de AuthBaseStrategy por operador:

```
BellAuthStrategy (avanzada)
├─ Soporte SMS 2FA
├─ Detección de errores de caché
├─ Manejo de radio buttons
├─ Integración con webhook SMS
└─ Re-autenticación automática

TelusAuthStrategy
├─ Autenticación My Telus
├─ Manejo de sesiones
└─ Recuperación de errores

RogersAuthStrategy, ATTAuthStrategy, TMobileAuthStrategy, VerizonAuthStrategy
└─ Autenticación estándar con carrier-specific tweaks
```

**Drivers (drivers.py)**
- Builder pattern para diferentes navegadores
- Configuración específica por browser type
- Creación de opciones de lanzamiento

#### 2.3.3 Scrapers Infrastructure (scrapers/)

**Estructura de cada scraper por operador:**

```
BellScrapers:
├─ BellMonthlyReportsScraperStrategy (835 líneas)
├─ BellDailyUsageScraperStrategy
└─ BellPDFInvoiceScraperStrategy

TelusScrapers:
├─ TelusMonthlyReportsScraperStrategy (977 líneas - compleja)
├─ TelusDailyUsageScraperStrategy
└─ TelusPDFInvoiceScraperStrategy

Rogers, AT&T, T-Mobile, Verizon:
├─ [Carrier]MonthlyReportsScraperStrategy
├─ [Carrier]DailyUsageScraperStrategy
└─ [Carrier]PDFInvoiceScraperStrategy
```

**Patrones Comunes:**

```python
class [Carrier][Type]ScraperStrategy([Type]ScraperStrategy):
    """Implementación específica de carrier."""

    def execute(config, billing_cycle, credentials) -> ScraperResult:
        1. Navegar a sección de archivos (_find_files_section)
        2. Descargar archivos (_download_files)
        3. Extraer ZIPs si aplica (_extract_zip_files)
        4. Mapear archivos a BD (_create_file_mapping)
        5. Cargar a API externa (_upload_files_to_endpoint)
        6. Retornar resultado con estado
```

#### 2.3.4 File Upload Service (services/file_upload_service.py - 150 líneas)

**Responsabilidad:** Carga universal de archivos a API externa.

```python
class FileUploadService:
    def upload_files_batch(
        files: List[FileDownloadInfo],
        billing_cycle: BillingCycle,
        upload_type: str  # 'monthly', 'daily_usage', 'pdf_invoice'
    ) -> bool

    # Endpoints por tipo:
    # Monthly: /api/v1/accounts/billing-cycles/{cycle_id}/files/{file_id}/upload-file/
    # Daily Usage: /api/v1/accounts/billing-cycles/{cycle_id}/daily-usage/
    # PDF Invoice: /api/v1/accounts/billing-cycles/{cycle_id}/pdf-invoice/

    # Features:
    # - Headers con x-api-key, x-workspace-id, x-client-id
    # - Manejo de errores granular (por archivo)
    # - Logging detallado
    # - Timeout configurable (300s)
```

#### 2.3.5 Logging Service (logging_config.py - 62 líneas)

- Configuración centralizada de logging
- Console + File handlers
- Log levels por módulo
- Integración con todos los servicios

---

## 3. PUNTO DE ENTRADA PRINCIPAL (main.py)

**ScraperJobProcessor** - Orquestador maestro

```
main()
  └─ ScraperJobProcessor.__init__()
      ├─ SessionManager (gestión de sesiones)
      ├─ ScraperJobService (obtención de trabajos)
      └─ ScraperStrategyFactory (creación de scrapers)

  └─ execute_available_scrapers()
      ├─ log_statistics() (mostrar métricas)
      └─ get_available_jobs_with_complete_context()
          └─ Para cada trabajo:
              └─ process_scraper_job()
                  ├─ Verificar/actualizar sesión
                  ├─ Crear scraper con factory
                  ├─ Ejecutar scraper
                  ├─ Actualizar estado en BD
                  └─ Reportar resultado
```

**Ejemplo de Ejecución:**
1. Obtener trabajos disponibles del scheduler
2. Para cada trabajo:
   - Extraer contexto completo (Pydantic models)
   - Inteligencia de sesión: ¿reutilizar sesión?
   - Login/logout inteligente
   - Crear scraper adecuado
   - Ejecutar con parámetros completos
   - Capturar resultado
   - Actualizar estado en BD
3. Reportar resumen (exitosos/fallidos/totales)

---

## 4. SERVICIO SMS 2FA (authenticator_webhook/sms2fa.py)

**Tecnología:** Flask + Thread-safe storage

**Endpoints:**
```
POST /sms                    - Recibir código SMS general
POST /verizon/sms           - Código Verizon
POST /att/sms               - Código AT&T
POST /tmobile/sms           - Código T-Mobile
GET /code                   - Obtener código disponible
POST /code/consume          - Marcar como usado
GET /status                 - Estado del webhook
GET /health                 - Health check
```

**Features:**
- Almacenamiento thread-safe de códigos
- Expiración automática (5 minutos)
- Pattern matching para 6-8 dígitos
- Soporte para múltiples operadores
- Tracking de consumo (una sola vez)

---

## 5. PATRONES DE DISEÑO

### 5.1 Strategy Pattern
- Diferentes estrategias de autenticación por operador
- Diferentes estrategias de scraping por carrier + tipo
- Fácil agregar nuevos operadores sin modificar código existente

### 5.2 Factory Pattern
- `ScraperStrategyFactory`: Crea scraper correcto basado en (Carrier, ScraperType)
- `BrowserManager`: Factory para instancias de browser
- Mapeo dinámico de 18 combinaciones

### 5.3 Template Method Pattern
- `ScraperBaseStrategy` define flujo: _find_files → _download → _extract → _upload
- Clases concretas implementan métodos específicos por carrier
- Reutilización de código, extensibilidad

### 5.4 Repository Pattern
- `Repository` abstrae acceso a datos
- Desacoplamiento entre lógica de negocio y ORM
- Facilita testing y cambios de BD

### 5.5 Decorator Pattern
- `SafeScraperJobService`: Envuelve `ScraperJobService`
- Añade manejo de contexto async sin modificar original

### 5.6 Singleton Pattern
- `BrowserManager`: Una sola instancia de browser
- Optimiza recursos, reutiliza contexto

### 5.7 CQRS
- `Commands`: operaciones que escriben (scraping, upload)
- `Queries`: operaciones que leen (obtener trabajos, estadísticas)
- Separación de responsabilidades

---

## 6. FLUJO DE EJECUCIÓN COMPLETO

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INICIALIZACIÓN (main.py)                                     │
│    └─ Setup Django, logging                                    │
│    └─ Crear SessionManager, ScraperJobService, Factory          │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. OBTENCIÓN DE TRABAJOS                                        │
│    └─ query: ScraperJobs disponibles ahora                      │
│    └─ Construir contexto completo (Pydantic models)            │
│    └─ Incluir BillingCycle con todos los archivos              │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. PROCESAMIENTO POR TRABAJO                                    │
│    ├─ 3a. SESIÓN INTELIGENTE                                    │
│    │     ├─ ¿Hay sesión activa?                               │
│    │     │  └─ Si: ¿Credenciales coinciden?                   │
│    │     │     ├─ Si: Reutilizar sesión ✅                    │
│    │     │     └─ No: Logout → Re-login                       │
│    │     └─ No: Login nuevo                                    │
│    │                                                           │
│    ├─ 3b. OBTENER BROWSER                                       │
│    │     └─ PlaywrightWrapper con API de 30+ métodos           │
│    │                                                           │
│    ├─ 3c. CREAR SCRAPER                                         │
│    │     └─ Factory.create_scraper(carrier, type, browser)     │
│    │     └─ Retorna estrategia específica (ej: BellMonthly)    │
│    │                                                           │
│    ├─ 3d. EJECUTAR SCRAPER                                      │
│    │     └─ scraper.execute(config, billing_cycle, creds)      │
│    │                                                           │
│    ├─ 3e. PROCESAR RESULTADO                                    │
│    │     ├─ Extraer ZIPs (_extract_zip_files)                 │
│    │     ├─ Mapear archivos (_create_file_mapping)            │
│    │     ├─ Cargar a API (_upload_files_to_endpoint)          │
│    │     └─ Retornar ScraperResult                            │
│    │                                                           │
│    └─ 3f. ACTUALIZAR ESTADO EN BD                              │
│         └─ update_scraper_job_status(job_id, status, msg)     │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. RESUMEN FINAL                                                │
│    └─ Reportar: [exitosos] / [fallidos] / [total]              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. DEPENDENCIAS PRINCIPALES

### Core
- **Django 5.1.4**: Web framework y ORM
- **Pydantic 2.10.3**: Validación y modelos
- **Playwright 1.53.0**: Automatización de navegador
- **Requests 2.32.0**: Cliente HTTP

### Data Processing
- **pandas 2.2.3**: Análisis de datos
- **openpyxl 3.1.5**: Lectura/escritura Excel

### Security
- **cryptography 44.0.2**: Encriptación de credenciales
- **djangorestframework-simplejwt 5.3.1**: JWT tokens

### Code Quality
- **Black 24.10.0**: Formatting (línea 119)
- **isort 6.0.1**: Sorting de imports
- **MyPy 1.13.0**: Type checking

---

## 8. CONFIGURACIÓN

### Variables de Entorno Clave

```env
# API Externa
EIQ_BACKEND_API_BASE_URL=https://api.expertel.com
EIQ_BACKEND_API_KEY=bearer_token_aqui

# Base de Datos
DB_HOST=localhost
DB_NAME=expertel_dev
DB_USERNAME=expertel
DB_PASSWORD=password

# Django
DJANGO_SECRET_KEY=secret_key_aqui
DJANGO_DEBUG_MODE=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Security
CRYPTOGRAPHY_KEY=encryption_key_aqui

# Browser (Opcional)
BROWSER_TYPE=chrome
BROWSER_HEADLESS=false
BROWSER_SLOW_MO=1000
```

### Herramientas de Código

**Black** (line-length: 119, excluye migrations)
**isort** (profile: black, compatible)
**MyPy** (Django plugin, excluye migrations)
**pre-commit** (hooks automáticos)

---

## 9. RESUMEN DE CAPACIDADES

| Aspecto | Detalles |
|---------|----------|
| **Operadores** | Bell, Telus, Rogers, AT&T, T-Mobile, Verizon (6) |
| **Tipos de Scraper** | Monthly Reports, Daily Usage, PDF Invoice (3) |
| **Total Estrategias** | 6 × 3 = 18 |
| **Métodos Browser** | 30+ (navegación, interacción, gestión) |
| **Patrones de Diseño** | 7 patrones (Strategy, Factory, Template, etc.) |
| **Capas Arquitectónicas** | 3 (Domain, Application, Infrastructure) |
| **Servicios Principales** | SessionManager, ScraperJobService, FileUploadService |
| **Formato de Respuesta** | Pydantic models (tipado, validado) |
| **Autenticación 2FA** | SMS webhook para Bell, Verizon, AT&T, T-Mobile |
| **Carga de Archivos** | API universal con routing por tipo |
| **Logging** | Centralizado, múltiples handlers |
| **Type Checking** | MyPy strict mode |

---

## 10. PUNTOS CLAVE

✅ **Arquitectura Limpia:** Domain, Application, Infrastructure separadas
✅ **Type-Safe:** Pydantic + MyPy para validación en tiempo de compilación
✅ **Extensible:** Strategy pattern para nuevos carriers fácilmente
✅ **Robusto:** Manejo de errores, recuperación automática, logging detallado
✅ **Eficiente:** Reutilización de sesiones browser, singleton pattern
✅ **Seguro:** Encriptación de credenciales, JWT tokens, API key management
✅ **Testeable:** Desacoplamiento via interfaces, inyección de dependencias
✅ **Production-Ready:** Migraciones, admin interface, CQRS, repository pattern

---

**Creado:** 2025-11-28
**Versión:** 1.0
**Rama:** feature/session-manager-and-strategies