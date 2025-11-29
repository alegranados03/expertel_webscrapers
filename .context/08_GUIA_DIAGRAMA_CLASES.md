# GUÍA DEL DIAGRAMA DE CLASES (PlantUML)

## Archivo
`07_DIAGRAMA_CLASES.puml`

---

## ¿Cómo usar este archivo?

### Opción 1: Visualizar en Línea (Recomendado)
1. Ve a https://www.plantuml.com/plantuml/uml/
2. Copia el contenido de `07_DIAGRAMA_CLASES.puml`
3. Pega en el editor
4. Verás el diagrama interactivo completo

### Opción 2: Generar Imagen Local
```bash
# Instalar PlantUML
brew install plantuml  # macOS
# o
apt install plantuml   # Linux

# Generar PNG
plantuml 07_DIAGRAMA_CLASES.puml

# Generar SVG (mejor para web)
plantuml -tsvg 07_DIAGRAMA_CLASES.puml
```

### Opción 3: En tu IDE
- **VS Code:** Instala extensión "PlantUML"
- **IntelliJ/PyCharm:** Soporta PlantUML nativamente
- **Otros:** Muchos editores tienen plugins

---

## ESTRUCTURA DEL DIAGRAMA

El diagrama está organizado en **5 capas** siguiendo Clean Architecture:

### 1. APPLICATION LAYER (Superior)
```
┌─────────────────────────────┐
│  ScraperJobProcessor        │ ← PUNTO DE ENTRADA (main.py)
│  ├─ log_statistics()        │
│  ├─ process_scraper_job()   │
│  └─ execute_available_scrapers()
└────────┬────────────────────┘
         │
         ├─→ SessionManager
         ├─→ SafeScraperJobService
         └─→ ScraperStrategyFactory
```

**Responsabilidad:** Orquestación principal del flujo de ejecución

---

### 2. DOMAIN LAYER (Centro)
Contiene **interfaces abstractas** y **entidades Pydantic**:

#### Interfaces (ABC - Abstract Base Classes)
```
AuthBaseStrategy (ABC)
├─ BellAuthStrategy ✓
├─ TelusAuthStrategy ✓
├─ RogersAuthStrategy ✓
├─ ATTAuthStrategy ✓
├─ TMobileAuthStrategy ✓
└─ VerizonAuthStrategy ✓

BrowserWrapper (ABC)
└─ PlaywrightWrapper (en Infrastructure)

ScraperBaseStrategy (ABC)
├─ MonthlyReportsScraperStrategy (ABC)
│  ├─ BellMonthlyReportsScraperStrategy ✓
│  ├─ TelusMonthlyReportsScraperStrategy ✓
│  └─ ... (6 carriers total)
├─ DailyUsageScraperStrategy (ABC)
│  ├─ BellDailyUsageScraperStrategy ✓
│  └─ ... (6 carriers total)
└─ PDFInvoiceScraperStrategy (ABC)
   ├─ BellPDFInvoiceScraperStrategy ✓
   └─ ... (6 carriers total)
```

#### Entidades (Pydantic Models)
```
Credentials
├─ id
├─ username
├─ password
└─ carrier

SessionState
├─ status
├─ carrier
├─ credentials
└─ error_message

ScraperResult
├─ success
├─ message
├─ files
├─ error
└─ timestamp

FileDownloadInfo
├─ file_id
├─ file_name
├─ download_url
├─ file_path
└─ [mapping files]

ScraperJobCompleteContext
├─ scraper_job
├─ scraper_config
├─ billing_cycle
├─ credential
├─ account
├─ carrier
├─ workspace
└─ client
```

#### Factory Pattern
```
ScraperStrategyFactory
└─ create_scraper(carrier, scraper_type, browser_wrapper)
   └─ Retorna: 18 combinaciones posibles
```

**Responsabilidad:** Lógica de negocio pura, sin dependencias de frameworks

---

### 3. INFRASTRUCTURE LAYER - PLAYWRIGHT

#### Browser Management
```
BrowserManager (Singleton)
└─ get_browser(browser_type)
   └─ BrowserDriverFactory
      ├─ create_browser(type)
      ├─ create_context(browser)
      ├─ create_page(context)
      └─ create_full_setup(type)
         └─ Retorna: (Browser, BrowserContext)
```

#### Browser Wrapper
```
BrowserWrapper (ABC) ← Interface
└─ PlaywrightWrapper ✓ (Implementación)
   ├─ Métodos de navegación (10)
   ├─ Métodos de interacción (14)
   ├─ Métodos de datos (4)
   ├─ Métodos de pestañas (8)
   └─ Métodos de utilidad (8)
   TOTAL: 30+ métodos implementados
```

#### Auth Strategies
```
AuthBaseStrategy (ABC) ← Interface
├─ BellAuthStrategy (+ SMS 2FA)
├─ TelusAuthStrategy
├─ RogersAuthStrategy
├─ ATTAuthStrategy
├─ TMobileAuthStrategy
└─ VerizonAuthStrategy
```

**Responsabilidad:** Implementación concreta de Playwright y autenticación

---

### 4. INFRASTRUCTURE LAYER - SCRAPERS

**18 Estrategias (6 carriers × 3 tipos):**

```
BELL:
├─ BellMonthlyReportsScraperStrategy (835 líneas, + 2FA SMS)
├─ BellDailyUsageScraperStrategy
└─ BellPDFInvoiceScraperStrategy

TELUS:
├─ TelusMonthlyReportsScraperStrategy (977 líneas, + generación dinámica)
├─ TelusDailyUsageScraperStrategy
└─ TelusPDFInvoiceScraperStrategy

ROGERS, AT&T, T-MOBILE, VERIZON:
└─ MonthlyReports / DailyUsage / PDFInvoice × 5 carriers
   TOTAL: 15 estrategias más
```

Cada estrategia:
1. Hereda de tipo específico (Monthly/Daily/PDF)
2. Implementa `_find_files_section()` (específico del portal)
3. Implementa `_download_files()` (específico del portal)
4. Hereda helpers: `_extract_zip_files()`, `_upload_files_to_endpoint()`, etc.

---

### 5. INFRASTRUCTURE LAYER - SERVICES

```
FileUploadService
├─ upload_files_batch(files, billing_cycle, upload_type)
├─ _get_headers(billing_cycle)
├─ _get_upload_config(upload_type, file_info, billing_cycle)
└─ _upload_single_file(file_info, billing_cycle, upload_type)
```

**Responsabilidad:** Carga universal a API externa con routing por tipo

---

## FLUJO DE INICIO (PUNTO DE ENTRADA)

```
┌─────────────────────────────────────────────────────────────┐
│ main.py                                                     │
│ ├─ ScraperJobProcessor.__init__()                          │
│ │  ├─ SessionManager(CHROME)                               │
│ │  ├─ SafeScraperJobService(ScraperJobService())           │
│ │  └─ ScraperStrategyFactory()                             │
│ │                                                           │
│ └─ processor.execute_available_scrapers()                  │
│    ├─ get_available_jobs_with_complete_context()          │
│    │  └─ Query BD para trabajos con status PENDING         │
│    │                                                        │
│    └─ Para cada trabajo:                                   │
│       ├─ process_scraper_job(context)                      │
│       │  ├─ SessionManager.login(credentials)              │
│       │  │  └─ Selecciona AuthStrategy según Carrier       │
│       │  │     └─ Ejecuta login (puede incluir 2FA)        │
│       │  │                                                  │
│       │  ├─ ScraperStrategyFactory.create_scraper()        │
│       │  │  └─ Retorna estrategia específica del carrier   │
│       │  │                                                  │
│       │  ├─ scraper.execute(config, billing_cycle, creds)  │
│       │  │  ├─ _find_files_section()                       │
│       │  │  ├─ _download_files()                           │
│       │  │  ├─ _extract_zip_files()                        │
│       │  │  ├─ _create_file_mapping()                      │
│       │  │  ├─ _upload_files_to_endpoint()                 │
│       │  │  └─ return ScraperResult                        │
│       │  │                                                  │
│       │  └─ update_scraper_job_status(result)              │
│       │                                                    │
│       └─ Reportar resultado
│
└─ Resumen final (exitosos/fallidos/total)
```

---

## RELACIONES DE HERENCIA

### Inheritance Chain (líneas `--|>`)

```
PlaywrightWrapper --|> BrowserWrapper
    └─ Implementa todos los 30+ métodos abstractos

BellAuthStrategy --|> AuthBaseStrategy
TelusAuthStrategy --|> AuthBaseStrategy
RogersAuthStrategy --|> AuthBaseStrategy
ATTAuthStrategy --|> AuthBaseStrategy
TMobileAuthStrategy --|> AuthBaseStrategy
VerizonAuthStrategy --|> AuthBaseStrategy
    └─ Cada una implementa login(), logout(), is_logged_in()

MonthlyReportsScraperStrategy --|> ScraperBaseStrategy
DailyUsageScraperStrategy --|> ScraperBaseStrategy
PDFInvoiceScraperStrategy --|> ScraperBaseStrategy
    └─ Intermediarias, también abstractas

BellMonthlyReportsScraperStrategy --|> MonthlyReportsScraperStrategy
BellDailyUsageScraperStrategy --|> DailyUsageScraperStrategy
BellPDFInvoiceScraperStrategy --|> PDFInvoiceScraperStrategy
    └─ Implementaciones concretas de Bell
    └─ Patrón se repite para Telus, Rogers, AT&T, etc.
```

---

## RELACIONES DE COMPOSICIÓN

### Composition (líneas `-->`)

```
ScraperJobProcessor --> SafeScraperJobService: wraps
    └─ ScraperJobProcessor tiene instancia de SafeScraperJobService

SafeScraperJobService --> ScraperJobService: wraps
    └─ SafeScraperJobService envuelve ScraperJobService (Decorator Pattern)

ScraperJobProcessor --> SessionManager: uses
    └─ ScraperJobProcessor instancia SessionManager en __init__

ScraperJobProcessor --> ScraperStrategyFactory: uses
    └─ ScraperJobProcessor instancia ScraperStrategyFactory

SessionManager --> BrowserManager: instantiates
    └─ SessionManager crea BrowserManager

SessionManager --> SessionState: manages
    └─ SessionManager mantiene estado de sesión

SessionManager --> Credentials: uses
    └─ SessionManager trabaja con Credentials

SessionManager --> AuthBaseStrategy: instantiates
    └─ SessionManager crea estrategia específica según Carrier

SessionManager --> PlaywrightWrapper: creates
    └─ SessionManager crea PlaywrightWrapper (a través de BrowserManager)

ScraperStrategyFactory --> BellMonthlyReportsScraperStrategy: creates
ScraperStrategyFactory --> TelusMonthlyReportsScraperStrategy: creates
    └─ Factory crea instancias específicas

ScraperBaseStrategy --> FileUploadService: uses
    └─ ScraperBaseStrategy llama upload_files_to_endpoint()

ScraperBaseStrategy --> FileDownloadInfo: returns
    └─ _download_files() retorna List[FileDownloadInfo]

ScraperBaseStrategy --> ScraperResult: returns
    └─ execute() retorna ScraperResult
```

---

## ENUMS USADOS

```
Carrier {BELL, TELUS, ROGERS, ATT, TMOBILE, VERIZON}
    └─ Identifica operador de telecomunicaciones

ScraperType {MONTHLY_REPORTS, DAILY_USAGE, PDF_INVOICE}
    └─ Tipo de scraping a realizar

ScraperJobStatus {PENDING, RUNNING, SUCCESS, ERROR}
    └─ Estado del trabajo en BD

SessionStatus {LOGGED_OUT, LOGGED_IN, ERROR}
    └─ Estado de la sesión actual

Navigators {CHROME, FIREFOX, EDGE, SAFARI}
    └─ Tipo de navegador a usar
```

---

## PATRONES DE DISEÑO VISIBLES

### 1. Strategy Pattern
```
AuthBaseStrategy ← interface
├─ BellAuthStrategy ✓
├─ TelusAuthStrategy ✓
└─ ... (6 implementaciones)

ScraperBaseStrategy ← interface
├─ MonthlyReportsScraperStrategy ✓
├─ DailyUsageScraperStrategy ✓
└─ PDFInvoiceScraperStrategy ✓
   └─ (18 implementaciones totales)
```

### 2. Factory Pattern
```
ScraperStrategyFactory
└─ create_scraper(carrier, type, browser)
   └─ Retorna instancia específica (una de 18)
```

### 3. Template Method Pattern
```
ScraperBaseStrategy.execute() {
    _find_files_section()  ← abstract (implementado por subclases)
    _download_files()      ← abstract (implementado por subclases)
    _extract_zip_files()   ← heredado (implementación base)
    _upload_files()        ← heredado (implementación base)
}
```

### 4. Singleton Pattern
```
BrowserManager
└─ _instance: BrowserManager (único)
└─ Una sola instancia durante la ejecución
```

### 5. Decorator Pattern
```
SafeScraperJobService
└─ wraps ScraperJobService
└─ Añade manejo de contexto async/sync
```

---

## CÓMO LEER EL DIAGRAMA

### Símbolos
- `--|>` = Herencia (A hereda de B)
- `-->` = Composición/Uso (A usa B)
- `--` = Separador de métodos (arriba: atributos, abajo: métodos)
- `{abstract}` = Método abstracto (debe implementarse en subclases)
- `+` = Public method
- `-` = Private attribute
- `#` = Protected (heredable)
- `<<property>>` = Property en Python

### Colores/Secciones
1. **APPLICATION:** Orquestación y punto de entrada
2. **DOMAIN.ENTITIES:** Interfaces y entidades (negocio puro)
3. **INFRASTRUCTURE.PLAYWRIGHT:** Implementación Playwright
4. **INFRASTRUCTURE.SCRAPERS:** Estrategias específicas por carrier
5. **INFRASTRUCTURE.SERVICES:** Servicios transversales
6. **ENUMS:** Enumeradores

---

## PREGUNTAS COMUNES

### P: ¿Cuál es el punto de entrada?
**R:** `ScraperJobProcessor` en `main.py`. Método `execute_available_scrapers()` inicia todo.

### P: ¿Cómo se elige la estrategia de scraper?
**R:** `ScraperStrategyFactory.create_scraper(carrier, scraper_type)` lo hace. Combina carrier + tipo para retornar la instancia correcta.

### P: ¿Dónde está la autenticación?
**R:** `SessionManager.login()` instancia la `AuthStrategy` correcta según el `Carrier`.

### P: ¿Cómo sé qué métodos tiene una clase?
**R:** Están todos en el diagrama. Métodos abstractos en interfaces, implementados en subclases.

### P: ¿Cuántas clases hay?
**R:** ~60 clases (4 interfaces + 6 auth strategies + 18 scraper strategies + utilities + services + enums)

### P: ¿Dónde se suben los archivos?
**R:** `FileUploadService.upload_files_batch()`. Llamado desde `ScraperBaseStrategy._upload_files_to_endpoint()`.

---

## ESTADÍSTICAS DEL DIAGRAMA

| Aspecto | Cantidad |
|---------|----------|
| **Clases** | ~60 |
| **Interfaces (ABC)** | 3 |
| **Estrategias de Auth** | 6 |
| **Estrategias de Scraper** | 18 |
| **Enums** | 5 |
| **Relaciones de herencia** | 27 |
| **Relaciones de composición** | 15+ |
| **Métodos abstractos** | 30+ (en BrowserWrapper) + más |

---

## NOTAS IMPORTANTES

1. **Clean Architecture:** El diagrama sigue claramente las capas de Clean Architecture
2. **Inyección de Dependencias:** Las clases reciben sus dependencias en constructores
3. **Desacoplamiento:** Las interfaces abstractas separan implementaciones
4. **Extensibilidad:** Agregar nuevo carrier = crear 3 estrategias nuevas
5. **Reutilización:** SessionManager reutiliza browser entre trabajos

---

**Creado:** 2025-11-29
**Status:** ✅ Diagrama completo y preciso
**Herramienta:** PlantUML