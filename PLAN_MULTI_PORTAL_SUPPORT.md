# PLAN: SOPORTE PARA MÚLTIPLES PORTALES POR CARRIER

## FASE 1: ANÁLISIS DEL PROBLEMA

### Limitación Actual
El sistema asume implícitamente **UN único portal por carrier** en todos los niveles:
- AuthBaseStrategy retorna URLs/XPaths fijos (no pueden variar)
- SessionManager mantiene UNA sola sesión activa
- Credentials no tiene campo para identificar portal
- ScraperStrategyFactory mapea solo (Carrier, ScraperType) → Strategy
- CarrierPortalUrls es enum con URLs únicas por carrier

### Casos de Uso Necesarios
1. Bell tiene "Business Portal" y "Enterprise Portal" con estructura diferente
2. Mismo usuario puede necesitar acceder a ambos portales en paralelo
3. Cada portal requiere distintos XPaths y flujos de autenticación
4. Diferentes portales pueden tener diferentes tipos de reportes disponibles

### Impacto de No Cambiar
- **Bloqueador**: No se puede soportar 2 portales Bell sin refactorización mayor
- **Mantenibilidad**: Código frágil con URLs hardcodeadas
- **Escalabilidad**: Agregar nuevo portal requiere cambios en múltiples capas

---

## CONCLUSIÓN FINAL

**Opción Recomendada**: OPCIÓN SIMPLIFICADA (SessionManager Storage)

Esta es la solución elegida y es **claramente la más pragmática**:

✅ **30 minutos** de implementación (vs 2-3 horas de alternatives)
✅ **20-30 líneas** de cambio totales
✅ **Zero impacto** en AuthBaseStrategy
✅ **Patrón ya existente** en ScraperStrategyFactory
✅ **Altamente mantenible**: agregar portal nuevo = crear nueva strategy + 1 línea en SessionManager
✅ **Backward compatible**: scraper_type=None sigue funcionando

---

## RECOMENDACIÓN FINAL: OPCIÓN SIMPLIFICADA (SessionManager Storage + Scraper Type Aware Mapping)

### Arquitectura Elegida

**Nombre**: "Scraper-Type Aware SessionManager Storage"

**Concepto Core**:
- SessionManager mantiene `self._scraper_type` como estado de sesión
- Mapeo de estrategias: `Dict[tuple[Carrier, ScraperType], Type[AuthBaseStrategy]]`
- Al logout(), se limpia `self._scraper_type = None`
- Sin cambios en AuthBaseStrategy ni auth strategies concretas

**Por qué es óptimo**:
1. **Minimalista**: Solo agregar variable de estado en SessionManager
2. **Patrón existente**: ScraperStrategyFactory ya usa `Dict[tuple[Carrier, ScraperType], Type]`
3. **Sin refactorización**: AuthStrategies quedan como están
4. **Limpieza automática**: logout() resetea scraper_type
5. **Escalable**: Soporta N portales por carrier sin cambios arquitectónicos

---

## PLAN DE IMPLEMENTACIÓN

### Archivos a Modificar (En Orden)

#### 1. **web_scrapers/application/session_manager.py**
**Cambios**: Agregar variable de estado y mapeo de estrategias

```python
from typing import Dict, Optional, Type
from web_scrapers.domain.enums import ScraperType
from web_scrapers.domain.entities.auth_strategies import AuthBaseStrategy
from web_scrapers.domain.entities.session import Carrier, Credentials, SessionState, SessionStatus

class SessionManager:

    def __init__(self, browser_type: Optional[Navigators] = None):
        self.browser_manager = BrowserManager()
        self.browser_type = browser_type
        self.session_state = SessionState()

        # CAMBIO 1: Mapeo actualizado con scraper_type
        self._auth_strategies: Dict[tuple[Carrier, Optional[ScraperType]], Type[AuthBaseStrategy]] = {
            # Sin scraper_type (backward compat) - usa default MONTHLY_REPORTS
            (Carrier.BELL, None): BellAuthStrategy,
            (Carrier.TELUS, None): TelusAuthStrategy,
            (Carrier.ROGERS, None): RogersAuthStrategy,
            (Carrier.ATT, None): ATTAuthStrategy,
            (Carrier.TMOBILE, None): TMobileAuthStrategy,
            (Carrier.VERIZON, None): VerizonAuthStrategy,

            # Con scraper_type específico - si el carrier/tipo tienen strategy diferente
            # (Carrier.BELL, ScraperType.DAILY_USAGE): BellDailyUsageAuthStrategy,  # ← Agregar si necesario
            # (Carrier.BELL, ScraperType.PDF_INVOICE): BellPDFInvoiceAuthStrategy,  # ← Agregar si necesario
        }

        self._current_auth_strategy: Optional[AuthBaseStrategy] = None
        self._scraper_type: Optional[ScraperType] = None  # ← NUEVO: guardar tipo de scraper
        self._browser_wrapper: Optional[BrowserWrapper] = None
        self._browser = None
        self._context = None
        self._page = None

    def login(self, credentials: Credentials, scraper_type: Optional[ScraperType] = None) -> bool:  # ← NUEVO parámetro
        try:
            if self.session_state.is_logged_in():
                if (
                    self.session_state.carrier == credentials.carrier
                    and self.session_state.credentials
                    and self.session_state.credentials.id == credentials.id
                    and self._scraper_type == scraper_type  # ← CAMBIO: verificar que scraper_type coincida
                ):
                    return True
                self.logout()

            # CAMBIO CLAVE: Búsqueda con tupla (carrier, scraper_type)
            auth_strategy_class = self._auth_strategies.get((credentials.carrier, scraper_type))

            if not auth_strategy_class:
                error_msg = f"No auth strategy for carrier: {credentials.carrier}, scraper_type: {scraper_type}"
                self.session_state.set_error(error_msg)
                return False

            browser_wrapper = self._initialize_browser()
            self._current_auth_strategy = auth_strategy_class(browser_wrapper)
            self._scraper_type = scraper_type  # ← CAMBIO: guardar scraper_type

            login_success = self._current_auth_strategy.login(credentials)
            if login_success:
                self.session_state.set_logged_in(carrier=credentials.carrier, credentials=credentials)
                return True
            else:
                error_msg = f"Error al hacer login con {credentials.carrier}"
                self.session_state.set_error(error_msg)
                return False

        except Exception as e:
            error_msg = f"Error durante el proceso de login: {str(e)}"
            self.session_state.set_error(error_msg)
            return False

    def logout(self) -> bool:
        try:
            if not self.session_state.is_logged_in():
                return True

            if not self._current_auth_strategy:
                self.session_state.set_logged_out()
                return True

            logout_success = self._current_auth_strategy.logout()

            if logout_success:
                self.session_state.set_logged_out()
                self._current_auth_strategy = None
                self._scraper_type = None  # ← CAMBIO: limpiar scraper_type
                return True
            else:
                error_msg = "Error al hacer logout"
                self.session_state.set_error(error_msg)
                return False

        except Exception as e:
            error_msg = f"Error durante el proceso de logout: {str(e)}"
            self.session_state.set_error(error_msg)
            return False

    def force_logout(self) -> None:
        self.session_state.set_logged_out()
        self._current_auth_strategy = None
        self._scraper_type = None  # ← CAMBIO: limpiar scraper_type

    # ... resto de métodos igual
```

**Líneas de cambio**: ~20 líneas totales

---

#### 2. **web_scrapers/infrastructure/playwright/auth_strategies.py**
**Cambios**: NINGUNO - Las estrategias quedan como están (por ahora)

Si un carrier necesita estrategias diferentes por scraper_type:
1. Crear nuevas clases: `BellDailyUsageAuthStrategy`, `BellPDFInvoiceAuthStrategy`, etc.
2. Registrar en SessionManager (ver Paso 3)

**Ejemplo**: Si Bell necesita DAILY_USAGE en portal diferente:
```python
class BellDailyUsageAuthStrategy(AuthBaseStrategy):
    """Auth strategy específica para Daily Usage de Bell"""

    def get_login_url(self) -> str:
        return "https://usage.bell.ca/login"  # ← Portal diferente

    # ... implementar otros métodos con XPaths del portal "usage"
```

**Líneas de cambio**: 0 para ahora (agregar solo cuando sea necesario)

---

#### 3. **main.py** (ScraperJobProcessor)
**Cambios**: Pasar scraper_type cuando llamas login

```python
# Línea ~78 (en process_scraper_job)
from web_scrapers.domain.enums import ScraperType as ScraperTypeEnum

scraper_type = ScraperTypeEnum(scraper_job.type)  # ← Convertir string a enum

# Línea ~105-115 (donde llamas login)
if not self.session_manager.login(credentials, scraper_type=scraper_type):  # ← CAMBIO: pasar scraper_type
    self.logger.error(f"Failed to login with carrier {carrier.name}")
    # ... error handling
```

**Líneas de cambio**: ~5 líneas

---

### Ejemplo: Agregar Soporte para Bell DAILY_USAGE (Portal Diferente)

**Paso 1**: Crear nueva AuthStrategy (solo si es necesario)
```python
# En auth_strategies.py
class BellDailyUsageAuthStrategy(AuthBaseStrategy):
    """Auth strategy para Bell Daily Usage (portal diferente)"""

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = "http://localhost:8000"):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url

    def login(self, credentials: Credentials) -> bool:
        # Implementar login en portal "usage.bell.ca"
        pass

    # ... rest of methods
```

**Paso 2**: Registrar en SessionManager
```python
# En session_manager.py _auth_strategies
(Carrier.BELL, ScraperType.DAILY_USAGE): BellDailyUsageAuthStrategy,  # ← Agregar
```

**Listo**. Sin cambios en main.py.

---

### Validación Post-Implementación

1. ✅ login(creds) sin scraper_type usa default None → busca (Carrier, None)
2. ✅ login(creds, ScraperType.MONTHLY_REPORTS) busca (Carrier, MONTHLY_REPORTS)
3. ✅ logout() limpia self._scraper_type automáticamente
4. ✅ Si cambias carrier → logout() automático
5. ✅ Si cambias scraper_type del mismo carrier → logout() automático
6. ✅ Agregar portal diferente = crear nueva AuthStrategy + registrar

---

## RESUMEN: Cambios Totales

| Archivo | Cambios | Complejidad |
|---------|---------|-------------|
| session_manager.py | +1 variable, +3 líneas en getters, +1 línea logout | Baja |
| auth_strategies.py (si aplica) | Nueva clase per portal diferente | Media |
| main.py | +5 líneas (pasar scraper_type) | Baja |
| **TOTAL** | **~20-30 líneas (sin nuevas strategies)** | **Baja** |

**Esfuerzo estimado**: 30 minutos (solo cambios SessionManager + main.py)
Agregar estrategia nueva si se necesita: +30 minutos por strategy

**Risk**: Muy bajo - cambios localizados, sin afectar interfaces

---

## Próximo Paso
**Aprobación para comenzar implementación**
