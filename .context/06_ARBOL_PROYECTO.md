# ÁRBOL DEL PROYECTO - Estructura Completa

**Generado:** 2025-11-28
**Rama:** `feature/session-manager-and-strategies`

---

## ESTRUCTURA COMPLETA

```
expertel_webscrapers/
│
├── 📂 config/                              # Configuración Django
│   ├── __init__.py
│   ├── settings.py                         # ⭐ Configuración principal (4,339 líneas)
│   ├── urls.py                            # URLs y routing
│   ├── asgi.py                            # ASGI (async)
│   └── wsgi.py                            # WSGI (producción)
│
├── 📂 web_scrapers/                        # 🎯 MÓDULO PRINCIPAL
│   │
│   ├── 📂 domain/                          # 🏛️ DOMAIN LAYER (lógica pura)
│   │   ├── 📂 entities/
│   │   │   ├── __init__.py
│   │   │   ├── models.py                   # ⭐ Entidades Pydantic (Client, Account, BillingCycle...)
│   │   │   ├── auth_strategies.py          # ⭐ Interfaz base de autenticación
│   │   │   ├── scraper_strategies.py       # ⭐ Clase base de scrapers + helpers
│   │   │   ├── browser_wrapper.py          # ⭐ Interfaz abstracta de browser (30+ métodos)
│   │   │   ├── session.py                  # ⭐ Entidades de sesión (SessionState, Credentials)
│   │   │   ├── scraper_factory.py          # ⭐ Factory pattern (18 combinaciones)
│   │   │   └── ports.py                    # Interfaces/puertos
│   │   ├── enums.py                        # ⭐ Enums (Carriers, FileStatus, ScraperType...)
│   │   └── __init__.py
│   │
│   ├── 📂 application/                     # 🚀 APPLICATION LAYER (casos de uso)
│   │   ├── 📂 cqrs/
│   │   │   ├── 📂 commands/
│   │   │   │   ├── get_monthly_reports.py  # Comando: obtener reportes mensuales
│   │   │   │   ├── get_daily_usage.py      # Comando: obtener uso diario
│   │   │   │   ├── get_pdf_invoice.py      # Comando: obtener facturas PDF
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   ├── session_manager.py              # ⭐ Orquestador de sesiones (200 líneas)
│   │   ├── scraper_job_service.py          # ⭐ Servicio de trabajos (~150 líneas)
│   │   ├── safe_scraper_job_service.py     # Wrapper async-safe (~100 líneas)
│   │   └── __init__.py
│   │
│   ├── 📂 infrastructure/                  # ⚙️ INFRASTRUCTURE LAYER (implementaciones)
│   │   ├── 📂 django/                      # Django ORM
│   │   │   ├── 📂 migrations/
│   │   │   │   └── __init__.py
│   │   │   ├── models.py                   # ORM models (equivalentes Pydantic)
│   │   │   ├── repositories.py             # Repository pattern (acceso datos)
│   │   │   ├── admin.py                    # Django admin interface
│   │   │   ├── apps.py                     # App config
│   │   │   ├── enums.py                    # Django choices
│   │   │   ├── views.py
│   │   │   ├── tests.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── 📂 playwright/                  # Automatización con Playwright
│   │   │   ├── browser_factory.py          # ⭐ Factory de browsers (207 líneas)
│   │   │   ├── browser_wrapper.py          # ⭐ PlaywrightWrapper impl. (278 líneas)
│   │   │   ├── auth_strategies.py          # ⭐ Autenticación por carrier (43,650 líneas)
│   │   │   ├── drivers.py                  # Builder pattern para browsers
│   │   │   └── __init__.py
│   │   │
│   │   ├── 📂 scrapers/                    # Implementación por carrier
│   │   │   ├── bell_scrapers.py            # ⭐ Bell (835 líneas - 2FA SMS)
│   │   │   ├── telus_scrapers.py           # ⭐ Telus (977 líneas - generación dinámca)
│   │   │   ├── rogers_scrapers.py          # Rogers (~200 líneas)
│   │   │   ├── att_scrapers.py             # AT&T (~800 líneas)
│   │   │   ├── tmobile_scrapers.py         # T-Mobile (~200 líneas)
│   │   │   ├── verizon_scrapers.py         # Verizon (~200 líneas)
│   │   │   └── __init__.py
│   │   │
│   │   ├── 📂 services/                    # Servicios transversales
│   │   │   ├── file_upload_service.py      # ⭐ Carga universal a API (150 líneas)
│   │   │   └── __init__.py
│   │   │
│   │   ├── logging_config.py               # ⭐ Configuración de logging (62 líneas)
│   │   └── __init__.py
│   │
│   ├── 📂 examples/                        # Ejemplos de uso
│   │   ├── session_manager_example.py      # Demo de SessionManager
│   │   ├── env_example.txt                 # Variables de entorno ejemplo
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── 📂 shared/                              # Código compartido
│   ├── 📂 domain/
│   │   ├── 📂 entities/
│   │   │   ├── cqrs.py                    # Clases base Command/Query
│   │   │   ├── repositories.py            # Interfaces Repository
│   │   │   ├── pagination.py              # QuerySet, paginación
│   │   │   ├── specifications.py          # Pattern Specifications
│   │   │   ├── annotations.py
│   │   │   └── __init__.py
│   │   ├── enums.py
│   │   ├── annotations.py
│   │   └── __init__.py
│   ├── 📂 infrastructure/
│   │   ├── 📂 django/
│   │   │   ├── models.py
│   │   │   ├── repositories.py
│   │   │   ├── specifications.py
│   │   │   ├── annotations.py
│   │   │   ├── buiders.py                 # [nota: typo en nombre]
│   │   │   └── __init__.py
│   │   ├── utils.py
│   │   └── __init__.py
│   └── __init__.py
│
├── 📂 authenticator_webhook/               # 🔐 Servicio SMS 2FA (Flask)
│   ├── sms2fa.py                           # ⭐ Webhook Flask (thread-safe)
│   └── __init__.py (implícito)
│
├── 📂 .context/                            # 📚 DOCUMENTACIÓN (TÚ ESTÁS AQUÍ)
│   ├── 00_README.md                        # Índice y guía
│   ├── 01_ARQUITECTURA_COMPLETA.md         # Arquitectura global
│   ├── 02_ESCENARIOS_EJEMPLO.md            # 8 casos de uso
│   ├── 03_FLUJOS_TECNICOS.md               # Detalles técnicos
│   ├── 04_COMPONENTES_CLAVE.md             # Referencia
│   ├── 05_RESUMEN_EJECUTIVO.md             # Resumen ejecutivo
│   └── 06_ARBOL_PROYECTO.md                # Este archivo
│
├── 🔧 ARCHIVOS RAÍZ
│   ├── main.py                             # ⭐ PUNTO DE ENTRADA (210 líneas)
│   ├── manage.py                           # Django CLI
│   ├── scraperpoc.py                       # POC / experimental
│   │
│   ├── 📋 CONFIGURACIÓN
│   ├── pyproject.toml                      # Poetry + herramientas (Black, isort, mypy)
│   ├── .env.example                        # Variables de entorno (plantilla)
│   │
│   ├── 📖 DOCUMENTACIÓN
│   ├── CLAUDE.md                           # Guía para Claude Code (existente)
│   │
│   └── 🐙 VERSION CONTROL
│       └── .git/                           # Historial (rama: feature/session-manager-and-strategies)
│
└── 📂 (Otros directorios no documentados)
    ├── __pycache__/
    ├── .idea/
    ├── node_modules/
    └── ...
```

---

## MAPA DE RESPONSABILIDADES

### Domain Layer (Lógica Pura)

```
domain/entities/
├── models.py
│   ├── Client               → Info de cliente
│   ├── Workspace            → Espacio de trabajo
│   ├── Account              → Cuenta del cliente
│   ├── BillingCycle         → Ciclo de facturación
│   ├── BillingCycleFile     → Archivo mensual
│   ├── BillingCycleDailyUsageFile
│   ├── BillingCyclePDFFile
│   ├── ScraperConfig        → Config de scraper
│   ├── FileDownloadInfo     → Info de descarga
│   ├── FileMappingInfo      → Info para upload
│   ├── Credentials          → Usuario/pwd
│   ├── SessionState         → Estado sesión
│   └── ScraperResult        → Resultado ejecución
│
├── auth_strategies.py
│   └── AuthBaseStrategy (ABC)
│       └── Métodos: login(), logout(), is_logged_in()
│
├── scraper_strategies.py
│   ├── ScraperBaseStrategy (ABC)
│   │   ├── Métodos base: _extract_zip_files(), _create_file_mapping()
│   │   └── Métodos abstractos: _find_files_section(), _download_files()
│   ├── MonthlyReportsScraperStrategy (Abstract)
│   ├── DailyUsageScraperStrategy (Abstract)
│   └── PDFInvoiceScraperStrategy (Abstract)
│
├── browser_wrapper.py
│   └── BrowserWrapper (ABC)
│       ├── 30+ métodos abstractos
│       └── Navegación, interacción, datos, tabs, descargas, limpieza
│
├── session.py
│   ├── SessionStatus (LOGGED_IN, LOGGED_OUT, ERROR)
│   ├── Carrier (BELL, TELUS, ROGERS, ATT, TMOBILE, VERIZON)
│   ├── Credentials
│   └── SessionState
│
├── scraper_factory.py
│   └── ScraperStrategyFactory
│       └── create_scraper(carrier, type, browser) → Strategy específica
│
└── enums.py
    ├── Navigators (CHROME, FIREFOX, EDGE, SAFARI)
    ├── CarrierPortalUrls
    ├── FileStatus
    ├── AccountType
    ├── BillingCycleStatus
    ├── ScraperType
    ├── ScraperJobStatus
    └── CarrierFileSlug... (por carrier)
```

### Application Layer (Orquestación)

```
application/
├── session_manager.py (200 líneas)
│   └── SessionManager
│       ├── Método login: lógica inteligente (reutilizar/logout+login/nuevo)
│       ├── Método logout: logout seguro
│       ├── Método is_logged_in: verificación
│       ├── Método get_browser_wrapper: obtener browser
│       ├── Método refresh_session_status: verificar si sigue válida
│       └── Método cleanup: liberar recursos
│
├── scraper_job_service.py (~150 líneas)
│   └── ScraperJobService
│       ├── get_available_jobs_with_complete_context()
│       ├── update_scraper_job_status()
│       └── get_scraper_statistics()
│
├── safe_scraper_job_service.py (~100 líneas)
│   └── SafeScraperJobService (decorator)
│       └── Envuelve ScraperJobService para manejo async-safe
│
└── cqrs/commands/
    ├── get_monthly_reports.py
    ├── get_daily_usage.py
    └── get_pdf_invoice.py
```

### Infrastructure Layer (Implementaciones)

```
infrastructure/
├── django/
│   ├── models.py           → ORM (mapeo Pydantic ↔ BD)
│   ├── repositories.py     → Repository pattern (acceso datos)
│   ├── admin.py            → Django admin
│   ├── enums.py            → Choices para ORM
│   └── views.py
│
├── playwright/
│   ├── browser_factory.py (207 líneas)
│   │   └── BrowserManager
│   │       └── get_browser(type) → Browser + Context
│   │
│   ├── browser_wrapper.py (278 líneas)
│   │   └── PlaywrightWrapper(BrowserWrapper)
│   │       ├── 30+ métodos
│   │       └── Implementa interface abstracta
│   │
│   ├── auth_strategies.py (43,650 líneas)
│   │   ├── BellAuthStrategy (+ 2FA SMS, cache recovery)
│   │   ├── TelusAuthStrategy
│   │   ├── RogersAuthStrategy
│   │   ├── ATTAuthStrategy
│   │   ├── TMobileAuthStrategy
│   │   └── VerizonAuthStrategy
│   │
│   └── drivers.py
│       └── Builder pattern para browsers
│
├── scrapers/
│   ├── bell_scrapers.py (835 líneas)
│   │   ├── BellMonthlyReportsScraperStrategy (compleja)
│   │   ├── BellDailyUsageScraperStrategy
│   │   └── BellPDFInvoiceScraperStrategy
│   │
│   ├── telus_scrapers.py (977 líneas)
│   │   ├── TelusMonthlyReportsScraperStrategy (generación dinámica + queue)
│   │   ├── TelusDailyUsageScraperStrategy
│   │   └── TelusPDFInvoiceScraperStrategy
│   │
│   ├── rogers_scrapers.py (~200 líneas)
│   ├── att_scrapers.py (~800 líneas)
│   ├── tmobile_scrapers.py (~200 líneas)
│   └── verizon_scrapers.py (~200 líneas)
│
├── services/
│   ├── file_upload_service.py (150 líneas)
│   │   └── FileUploadService
│   │       ├── upload_files_batch()
│   │       ├── _upload_single_file()
│   │       ├── _get_upload_config()
│   │       └── _get_headers()
│   │
│   └── [otros servicios]
│
└── logging_config.py (62 líneas)
    └── setup_logging() → logging centralizado
```

---

## FLUJO DE DATOS

```
┌─ main.py (ScraperJobProcessor)
│  └─ execute_available_scrapers()
│
└─ ScraperJobService
   └─ get_available_jobs_with_complete_context()
      └─ Query: ScraperJob.objects.filter(status=PENDING, available_at <= now)
         └─ Para cada job:
            ├─ Scraper Job
            ├─ Scraper Config
            ├─ Billing Cycle
            ├─ Credential (encriptada)
            ├─ Account
            └─ Carrier

         └─ Retorna: [ScraperJobCompleteContext, ...]

└─ SessionManager
   └─ login(credentials)
      └─ _auth_strategies[carrier]
         └─ AuthStrategy
            └─ browser_wrapper (PlaywrightWrapper)
               └─ Playwright Page

└─ ScraperStrategyFactory
   └─ create_scraper(carrier, type, browser)
      └─ [Carrier][Type]ScraperStrategy

└─ Scraper.execute(config, billing_cycle, credentials)
   ├─ _find_files_section()
   ├─ _download_files()
   │  └─ browser.download_file(selector)
   │     └─ FileDownloadInfo []
   │
   ├─ _extract_zip_files(zip_path)
   │  └─ string[] (paths extraídos)
   │
   ├─ _create_file_mapping()
   │  └─ FileMappingInfo[]
   │
   ├─ _upload_files_to_endpoint()
   │  └─ FileUploadService.upload_files_batch()
   │     ├─ _get_upload_config(type)
   │     ├─ _get_headers()
   │     └─ requests.post() → API externa
   │
   └─ return ScraperResult(success, message, files, error)

└─ ScraperJobService.update_scraper_job_status(job_id, status, msg)
   └─ ScraperJob.objects.filter(id=job_id).update(status=status, message=msg)
```

---

## PATRONES DE DISEÑO IMPLEMENTADOS

```
1. STRATEGY PATTERN
   ├─ AuthBaseStrategy (6 implementaciones)
   │  ├─ BellAuthStrategy
   │  ├─ TelusAuthStrategy
   │  ├─ RogersAuthStrategy
   │  └─ ... (ATT, TMobile, Verizon)
   │
   └─ ScraperBaseStrategy (18 implementaciones)
      ├─ MonthlyReports (6 carriers)
      ├─ DailyUsage (6 carriers)
      └─ PDFInvoice (6 carriers)

2. FACTORY PATTERN
   ├─ BrowserManager
   │  └─ get_browser(type) → Browser específico
   │
   └─ ScraperStrategyFactory
      └─ create_scraper(carrier, type) → Strategy específica

3. TEMPLATE METHOD PATTERN
   └─ ScraperBaseStrategy.execute()
      ├─ _find_files_section() (abstract)
      ├─ _download_files() (abstract)
      ├─ _extract_zip_files() (heredado)
      ├─ _create_file_mapping() (heredado)
      ├─ _upload_files_to_endpoint() (heredado)
      └─ Flujo: find → download → extract → map → upload

4. REPOSITORY PATTERN
   └─ Repository
      ├─ create(), update(), delete()
      ├─ get_by_id()
      ├─ filter_by()
      └─ Abstracción de Django ORM

5. DECORATOR PATTERN
   └─ SafeScraperJobService
      ├─ Envuelve ScraperJobService
      └─ Añade manejo async-safe

6. SINGLETON PATTERN
   └─ BrowserManager
      └─ Una sola instancia de browser

7. CQRS PATTERN
   ├─ Commands (cqrs/commands/)
   │  ├─ get_monthly_reports.py
   │  ├─ get_daily_usage.py
   │  └─ get_pdf_invoice.py
   │
   └─ Queries (service methods)
      └─ get_available_jobs()
```

---

## TAMAÑO Y COMPLEJIDAD

```
Componente                          Líneas      Complejidad
─────────────────────────────────────────────────────────────
config/settings.py                  4,339       Alta (muchas apps, config)
bell_scrapers.py                      835       Muy Alta (2FA + cache recovery)
telus_scrapers.py                     977       Muy Alta (generación dinámica)
att_scrapers.py                       ~800      Alta
auth_strategies.py                 43,650       Extremadamente Alta (6 carriers)
session_manager.py                    200       Media-Alta
browser_wrapper.py                    278       Media-Alta (30+ métodos)
file_upload_service.py                150       Media
browser_factory.py                    207       Media
scraper_job_service.py                150       Media
─────────────────────────────────────────────────────────────
TOTAL APROXIMADO                  ~10,386

Métricas:
- Archivos Python: 89
- Métodos/Funciones: 200+
- Clases: 50+
- Interfaces abstratas: 4
- Implementaciones concretas: 18+ (scrapers)
```

---

## DEPENDENCIAS PRINCIPALES

```
CORE
├─ Django 5.1.4              (Web framework + ORM)
├─ Pydantic 2.10.3           (Validación y modelos)
├─ Playwright 1.53.0         (Automatización browser)
└─ Requests 2.32.0           (Cliente HTTP)

DATA PROCESSING
├─ pandas 2.2.3              (Análisis datos)
├─ openpyxl 3.1.5            (Excel lectura)
├─ xlsxwriter 3.2.3           (Excel escritura)
└─ boto3 1.37.16             (AWS S3)

SECURITY
├─ cryptography 44.0.2       (Encriptación)
├─ djangorestframework-simplejwt (JWT)
└─ django-allauth 65.3.1     (Autenticación social)

DEVELOPMENT
├─ Black 24.10.0             (Formateador)
├─ isort 6.0.1               (Ordenador imports)
├─ MyPy 1.13.0               (Type checking)
├─ django-stubs 5.1.1        (Stubs para Django)
└─ pre-commit 4.0.1          (Git hooks)

UTILS
├─ python-dotenv 1.0.1       (Env variables)
├─ chardet 5.2.0             (Charset detection)
└─ pymongo 4.11.1            (MongoDB - opcional)
```

---

## ENDPOINTS API EXTERNA

```
MonthlyReports:
  POST /api/v1/accounts/billing-cycles/{cycle_id}/files/{file_id}/upload-file/
  Headers: x-api-key, x-workspace-id, x-client-id
  Body: file (multipart)
  Response: 200/201 OK

DailyUsage:
  POST /api/v1/accounts/billing-cycles/{cycle_id}/daily-usage/
  Headers: x-api-key, x-workspace-id, x-client-id
  Body: file (multipart)
  Response: 200/201 OK

PDFInvoice:
  POST /api/v1/accounts/billing-cycles/{cycle_id}/pdf-invoice/
  Headers: x-api-key, x-workspace-id, x-client-id
  Body: file (multipart, application/pdf)
  Response: 200/201 OK
```

---

## RESUMEN RÁPIDO

| Aspecto | Detalles |
|---------|----------|
| **Tipo de Proyecto** | Django + Playwright, scraping automático |
| **Arquitectura** | Clean Architecture (Domain, Application, Infrastructure) |
| **Patrones** | Strategy, Factory, Template Method, Repository, Decorator, Singleton, CQRS |
| **Carriers** | 6 (Bell, Telus, Rogers, AT&T, T-Mobile, Verizon) |
| **Estrategias** | 18 (6 carriers × 3 tipos) |
| **Características** | Session reuse, 2FA SMS, ZIP extraction, Universal upload |
| **Líneas de Código** | ~10,386 en 89 archivos |
| **Estado** | ✅ Production-ready |
| **Documentación** | ✅ Completa en `.context/` |

---

**Generado:** 2025-11-28
**Status:** ✅ Completo