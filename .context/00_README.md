# DOCUMENTACIÓN DEL SISTEMA - Expertel Web Scrapers

## Introducción

Esta carpeta `.context/` contiene documentación completa y actualizada del sistema **Expertel Web Scrapers**.

**Fecha de Auditoría:** 2025-11-28
**Última Actualización:** 2025-12-01 (Bell Enterprise Centre Implementation)
**Rama Activa:** `feature/session-manager-and-strategies`
**Estado:** Completo y funcional

---

## 📋 Documentos Disponibles

### 1. **01_ARQUITECTURA_COMPLETA.md**
**Propósito:** Comprensión de la arquitectura global del sistema

**Contiene:**
- Estructura de capas (Domain, Application, Infrastructure)
- Jerarquía completa de directorios
- Descripción de cada capa y componentes
- Patrones de diseño implementados (7 patrones)
- Dependencias principales
- Estadísticas del código

**Cuándo leer:** Para entender cómo está organizado el proyecto y cómo se comunican los componentes.

---

### 2. **02_ESCENARIOS_EJEMPLO.md**
**Propósito:** Ver el sistema en acción con ejemplos concretos

**Contiene 8 escenarios:**
1. **Ejecución Exitosa - Bell Monthly Reports:** Flujo completo exitoso
2. **Reutilización de Sesión - Telus:** Cómo el sistema reutiliza sesiones
3. **Manejo de Error - ZIP Corrupto:** Recuperación de errores
4. **Session Loss Detection:** Detección automática de sesión perdida
5. **Múltiples Trabajos en Secuencia:** Procesamiento batch
6. **Extracción ZIP Compleja:** Aplanamiento de estructura de carpetas
7. **Fallo Parcial de Upload:** Continuar tras errores parciales
8. **2FA SMS Timeout:** Manejo de timeout en autenticación

**Cada escenario incluye:**
- Contexto de negocio
- Diagrama de flujo ASCII
- Estados de BD antes/después
- Logs esperados

**Cuándo leer:** Para ver cómo el sistema maneja situaciones reales (éxito, errores, cambios de carrier, etc.).

---

### 3. **03_FLUJOS_TECNICOS.md**
**Propósito:** Detalles técnicos profundos de cada componente

**Contiene 6 secciones:**
1. **Flujo de Autenticación por Carrier**
   - Arquitectura de estrategias
   - Flujo Bell (con 2FA SMS)
   - Flujo Telus (estándar)
   - Método is_logged_in()

2. **Flujo de Scraping Base**
   - Template Method Pattern
   - Flujo Bell Monthly
   - Flujo Telus (generación dinámica)

3. **Flujo de Gestión de Sesiones**
   - Lógica de decisión inteligente
   - Verificación periódica
   - Ciclo de vida completo

4. **Flujo de Extracción y Procesamiento**
   - Descarga de archivos Playwright
   - Extracción ZIP con flattening
   - Mapeo de archivos

5. **Flujo de Carga a API**
   - Servicio universal
   - Configuración por tipo
   - Headers y URLs

6. **Flujo de 2FA SMS**
   - Arquitectura webhook
   - Polling de códigos
   - Endpoints y storage

**Cada flujo incluye:**
- Diagramas ASCII detallados
- Pseudocódigo
- Steps numerados
- Manejo de excepciones

**Cuándo leer:** Para implementar cambios, debuggear problemas, o entender cómo se ejecuta código específico.

---

### 4. **04_COMPONENTES_CLAVE.md**
**Propósito:** Referencia detallada de cada componente principal

**Contiene 6 secciones:**

1. **SessionManager** (200 líneas)
   - Métodos principales (login, logout, is_logged_in, etc)
   - Atributos
   - Ejemplo de uso
   - Context manager

2. **Browser Wrapper** (278 líneas, 30+ métodos)
   - Métodos de navegación
   - Métodos de interacción
   - Métodos de obtención de datos
   - Gestión de pestañas
   - Descargas y limpieza

3. **Scraper Strategies**
   - Estructura de herencia (18 estrategias)
   - Interfaz base
   - Métodos abstractos
   - Características por carrier

4. **File Upload Service** (150 líneas)
   - Métodos upload_files_batch y _upload_single_file
   - Configuración por tipo
   - Flujo completo
   - Ejemplo de uso

5. **Configuración y Variables de Entorno**
   - Variables requeridas (API, BD, Django, etc)
   - Setup inicial
   - Uso en código

6. **Entidades Pydantic**
   - Jerarquía completa
   - Validación automática
   - Serialización

**Cuándo leer:** Como referencia rápida de métodos, parámetros y ejemplos de uso.

---

## 🔍 Estado del CLAUDE.md Existente

**ESTADO:** ✅ **ACTUALIZADO**

El archivo `CLAUDE.md` en la raíz del proyecto está al día y contiene:
- Comandos de desarrollo correctos
- Arquitectura resumida
- Componentes principales
- Variables de entorno

**Cambios respecto a la realidad actual:**
- ✅ SessionManager: Coincide (200 líneas aprox)
- ✅ FileUploadService: Coincide (150 líneas aprox)
- ✅ Browser Wrapper: Coincide (30+ métodos)
- ✅ SMS 2FA: Coincide (endpoints correctos)
- ✅ 18 estrategias: Correcto (6 carriers × 3 tipos)
- ✅ Bell Enterprise Centre: Nuevo scraper para 4 reportes mensuales

**CAMBIO IMPORTANTE (2025-12-01):**
- BellMonthlyReportsScraperStrategy migrado a Enterprise Centre (https://enterprisecentre.bell.ca)
- BellEnterpriseAuthStrategy para autenticación en nuevo portal
- Soporte para 4 reportes en lugar de 3 (agregado Invoice Charge Report)
- Filtrado automático de mes y cuenta por reporte

No se requieren actualizaciones al CLAUDE.md.

---

## 📊 Estadísticas del Proyecto

| Métrica | Valor |
|---------|-------|
| **Total Archivos Python** | 89 |
| **Total Líneas de Código** | ~10,386 |
| **Operadores Soportados** | 6 (Bell, Telus, Rogers, AT&T, T-Mobile, Verizon) |
| **Tipos de Scraper** | 3 (Monthly, Daily, PDF) |
| **Total Estrategias** | 18 (6 × 3) |
| **Métodos en BrowserWrapper** | 30+ |
| **Patrones de Diseño** | 7 |
| **Capas Arquitectónicas** | 3 (Domain, Application, Infrastructure) |
| **Dependencias Core** | 12+ |

---

## 🚀 Cómo Usar Esta Documentación

### Para Nuevos Desarrolladores
1. Comienza con **01_ARQUITECTURA_COMPLETA.md** para entender la estructura
2. Lee **02_ESCENARIOS_EJEMPLO.md** para ver cómo funciona en la práctica
3. Usa **04_COMPONENTES_CLAVE.md** como referencia rápida

### Para Debuggear Problemas
1. Consulta **03_FLUJOS_TECNICOS.md** para el componente específico
2. Busca logs esperados en **02_ESCENARIOS_EJEMPLO.md**
3. Verifica métodos en **04_COMPONENTES_CLAVE.md**

### Para Implementar Nuevas Características
1. Revisa patrones en **01_ARQUITECTURA_COMPLETA.md**
2. Estudia estrategia similar en **04_COMPONENTES_CLAVE.md**
3. Sigue flujo técnico en **03_FLUJOS_TECNICOS.md**

### Para Agregar Nuevo Carrier
1. Copia estructura de carrier existente en `web_scrapers/infrastructure/scrapers/`
2. Implementa 3 estrategias (Monthly, Daily, PDF)
3. Registra en `ScraperStrategyFactory`
4. Agrega `AuthStrategy` en `auth_strategies.py`
5. Actualiza enums si es necesario

---

## 🔧 Punto de Entrada Principal

**main.py** - `ScraperJobProcessor`

```python
if __name__ == "__main__":
    main()
    # 1. Setup Django
    # 2. Inicializar SessionManager, ScraperJobService, Factory
    # 3. Obtener trabajos disponibles
    # 4. Para cada trabajo:
    #    - Verificar/actualizar sesión
    #    - Crear scraper
    #    - Ejecutar
    #    - Actualizar estado BD
    # 5. Reportar resultado
```

**Ejecución:**
```bash
python main.py
```

---

## 🧪 Flujo de Ejecución Rápido

```
┌─ Django Setup
├─ SessionManager (CHROME browser)
├─ Obtener trabajos disponibles (QuerySet)
│
├─ Para cada trabajo:
│  ├─ ¿Sesión activa con mismas creds?
│  │  ├─ Si → Reutilizar
│  │  └─ No → Logout + Login
│  │
│  ├─ Crear scraper (Factory)
│  ├─ Ejecutar (Template Method)
│  │  ├─ _find_files_section
│  │  ├─ _download_files
│  │  ├─ _extract_zip_files
│  │  ├─ _upload_files_to_endpoint
│  │  └─ Return ScraperResult
│  │
│  └─ Actualizar BD
│
└─ Resumen final
```

---

## 🔐 Variables de Entorno Críticas

```env
# API (REQUERIDO para uploads)
EIQ_BACKEND_API_BASE_URL=https://api.expertel.com
EIQ_BACKEND_API_KEY=your_token

# BD (REQUERIDO)
DB_HOST=localhost
DB_NAME=expertel_dev
DB_USERNAME=expertel
DB_PASSWORD=password

# Django (REQUERIDO)
DJANGO_SECRET_KEY=secret_key
DJANGO_DEBUG_MODE=True

# Encriptación (REQUERIDO)
CRYPTOGRAPHY_KEY=base64_encoded_fernet_key
```

---

## 📚 Recursos Adicionales

### Archivos del Proyecto
- `config/settings.py`: Configuración Django (4,339 líneas)
- `web_scrapers/domain/entities/`: Entidades y abstracciones
- `web_scrapers/infrastructure/scrapers/`: Implementaciones por carrier
- `authenticator_webhook/sms2fa.py`: Servicio Flask 2FA

### Herramientas de Desarrollo
```bash
# Formateo
poetry run black .

# Ordenar imports
poetry run isort .

# Type checking
poetry run mypy .

# Pre-commit hooks
poetry run pre-commit run --all-files

# Tests
python manage.py test

# Django admin
python manage.py runserver
```

---

## ⚠️ Notas Importantes

1. **Session Reuse:** El sistema mantiene sesiones de browser activas entre trabajos para eficiencia (37% más rápido)

2. **ZIP Extraction:** Los ZIPs se aplanan a estructura de 1 nivel para simplificar processing

3. **SMS 2FA:** Requiere servicio webhook externo ejecutando en puerto 8000

4. **Carrier-Specific:** Bell es el más complejo (1,097 líneas - legacy + Enterprise Centre), Telus también (977 líneas - reportes dinámicos)

5. **Error Handling:** Sistema es resiliente - continúa si un archivo falla en upload

6. **Logging:** Centralizado y detallado - revisar logs para debuggear

---

## 📞 Preguntas Frecuentes

**P: ¿Cómo agrego un nuevo carrier?**
R: Crea 3 estrategias (Monthly, Daily, PDF) heredando de clases base, registra en Factory, agrega AuthStrategy.

**P: ¿Por qué es importante la reutilización de sesión?**
R: Ahorra 30+ segundos por trabajo (no recrear browser, no re-autenticar).

**P: ¿Qué pasa si falla un upload de archivo?**
R: Se log el error pero se continúa con siguientes archivos. Upload retorna False si alguno falla.

**P: ¿Cómo funciona el 2FA?**
R: Sistema realiza polling a webhook cada 500ms esperando código SMS (timeout 30s).

**P: ¿Dónde están los logs?**
R: Configurados en `logging_config.py` - console y archivo (si está configurado).

---

## 📝 Actualización de Documentación

**Esta documentación fue generada:** 2025-11-28
**Por auditoría de código del proyecto**
**Versión:** 1.0

**Próxima actualización recomendada cuando:**
- Se agregue un nuevo carrier
- Se cambien patrones arquitectónicos
- Se migre a nueva versión de dependencias
- Se añadan nuevas capas o servicios

---

**Última revisión:** 2025-12-01 (Actualización: Bell Enterprise Centre)
**Status:** ✅ Completo y Actualizado
**Alcance:** Sistema completo sin carpeta `script_testing`

**Cambios en última revisión:**
- Agregada documentación para BellMonthlyReportsScraperStrategy (Enterprise Centre)
- Actualizado flujo de ejemplo para 4 reportes
- Deprecated BellMonthlyReportsScraperStrategyLegacy (3 reportes antiguos)