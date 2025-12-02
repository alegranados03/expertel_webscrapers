import time
from datetime import datetime
from typing import Dict, Optional, Type

from web_scrapers.domain.entities.auth_strategies import AuthBaseStrategy
from web_scrapers.domain.entities.session import Carrier, Credentials, SessionState, SessionStatus
from web_scrapers.domain.enums import Navigators, ScraperType
from web_scrapers.infrastructure.playwright.auth_strategies import (
    ATTAuthStrategy,
    BellAuthStrategy,
    BellEnterpriseAuthStrategy,
    RogersAuthStrategy,
    TelusAuthStrategy,
    TMobileAuthStrategy,
    VerizonAuthStrategy,
)
from web_scrapers.infrastructure.playwright.browser_factory import BrowserManager
from web_scrapers.infrastructure.playwright.browser_wrapper import BrowserWrapper, PlaywrightWrapper


class SessionManager:

    def __init__(self, browser_type: Optional[Navigators] = None):

        self.browser_manager = BrowserManager()
        self.browser_type = browser_type
        self.session_state = SessionState()

        self._auth_strategies: dict[tuple[Carrier, ScraperType], Type[AuthBaseStrategy]] = {
            (Carrier.BELL, ScraperType.MONTHLY_REPORTS): BellEnterpriseAuthStrategy,
            (Carrier.BELL, ScraperType.DAILY_USAGE): BellAuthStrategy,
            (Carrier.BELL, ScraperType.PDF_INVOICE): BellAuthStrategy,
            (Carrier.TELUS, ScraperType.MONTHLY_REPORTS): TelusAuthStrategy,
            (Carrier.TELUS, ScraperType.DAILY_USAGE): TelusAuthStrategy,
            (Carrier.TELUS, ScraperType.PDF_INVOICE): TelusAuthStrategy,
            (Carrier.ROGERS, ScraperType.MONTHLY_REPORTS): RogersAuthStrategy,
            (Carrier.ROGERS, ScraperType.DAILY_USAGE): RogersAuthStrategy,
            (Carrier.ROGERS, ScraperType.PDF_INVOICE): RogersAuthStrategy,
            (Carrier.ATT, ScraperType.MONTHLY_REPORTS): ATTAuthStrategy,
            (Carrier.ATT, ScraperType.DAILY_USAGE): ATTAuthStrategy,
            (Carrier.ATT, ScraperType.PDF_INVOICE): ATTAuthStrategy,
            (Carrier.TMOBILE, ScraperType.MONTHLY_REPORTS): TMobileAuthStrategy,
            (Carrier.TMOBILE, ScraperType.DAILY_USAGE): TMobileAuthStrategy,
            (Carrier.TMOBILE, ScraperType.PDF_INVOICE): TMobileAuthStrategy,
            (Carrier.VERIZON, ScraperType.MONTHLY_REPORTS): VerizonAuthStrategy,
            (Carrier.VERIZON, ScraperType.DAILY_USAGE): VerizonAuthStrategy,
            (Carrier.VERIZON, ScraperType.PDF_INVOICE): VerizonAuthStrategy,
        }

        self._current_auth_strategy: Optional[AuthBaseStrategy] = None
        self._scraper_type: Optional[ScraperType] = None
        self._current_login_url: Optional[str] = None  # ← NUEVO: guardar URL de login actual
        self._browser_wrapper: Optional[BrowserWrapper] = None
        self._browser = None
        self._context = None
        self._page = None

    def is_logged_in(self) -> bool:
        return self.refresh_session_status()

    def get_current_carrier(self) -> Optional[Carrier]:
        return self.session_state.carrier

    def get_current_credentials(self) -> Optional[Credentials]:
        return self.session_state.credentials

    def get_session_state(self) -> SessionState:
        return self.session_state

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
                    self._scraper_type = None
                    self._current_login_url = None
                return False

            return is_active

        except Exception as e:
            error_msg = f"Error al verificar el estado de la sesión: {str(e)}"
            self.session_state.set_error(error_msg)
            return False

    def force_logout(self) -> None:
        self.session_state.set_logged_out()
        self._current_auth_strategy = None
        self._scraper_type = None
        self._current_login_url = None

    def has_error(self) -> bool:
        return self.session_state.is_error()

    def get_error_message(self) -> Optional[str]:
        return self.session_state.error_message

    def _initialize_browser(self) -> BrowserWrapper:

        if not self._browser_wrapper:
            self._browser, self._context = self.browser_manager.get_browser(self.browser_type)
            self._page = self._context.new_page()
            self._browser_wrapper = PlaywrightWrapper(self._page)

        return self._browser_wrapper

    def get_new_browser_wrapper(self) -> BrowserWrapper:
        if self._context:
            self._page = self._context.new_page()
            self._browser_wrapper = PlaywrightWrapper(self._page)
        return self._browser_wrapper

    def get_browser_wrapper(self) -> Optional[BrowserWrapper]:
        return self._browser_wrapper

    def login(self, credentials: Credentials, scraper_type: ScraperType) -> bool:
        try:
            if self.session_state.is_logged_in():
                if (
                    self.session_state.carrier == credentials.carrier
                    and self.session_state.credentials
                    and self.session_state.credentials.id == credentials.id
                    and self._scraper_type == scraper_type
                ):
                    return True

                # Si cambió el scraper_type, verificar si la URL de login también cambió
                if self._scraper_type != scraper_type:
                    auth_strategy_class = self._auth_strategies.get((credentials.carrier, scraper_type))
                    if auth_strategy_class:
                        # Crear instancia temporal para obtener la URL sin afectar la actual
                        temp_strategy = auth_strategy_class(self._browser_wrapper)
                        new_login_url = temp_strategy.get_login_url()

                        # Solo hacer logout si la URL de login cambió
                        if new_login_url != self._current_login_url:
                            self.logout()
                        else:
                            # La URL es la misma, solo actualizar scraper_type y reutilizar sesión
                            self._scraper_type = scraper_type
                            return True
                    else:
                        self.logout()
                else:
                    self.logout()

            # CAMBIO CLAVE: Búsqueda con tupla (carrier, scraper_type)
            auth_strategy_class = self._auth_strategies.get((credentials.carrier, scraper_type))

            if not auth_strategy_class:
                error_msg = f"No auth strategy for carrier: {credentials.carrier}, scraper_type: {scraper_type}"
                self.session_state.set_error(error_msg)
                return False
            browser_wrapper = self._initialize_browser()
            self._current_auth_strategy = auth_strategy_class(browser_wrapper)
            self._scraper_type = scraper_type
            self._current_login_url = self._current_auth_strategy.get_login_url()  # ← CAMBIO: guardar URL de login

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
                self._scraper_type = None
                self._current_login_url = None  # ← CAMBIO: limpiar URL de login
                return True
            else:
                error_msg = "Error al hacer logout"
                self.session_state.set_error(error_msg)
                return False

        except Exception as e:
            error_msg = f"Error durante el proceso de logout: {str(e)}"
            self.session_state.set_error(error_msg)
            return False

    def cleanup(self) -> None:
        if self.session_state.is_logged_in():
            self.force_logout()

        self._current_auth_strategy = None
        self._scraper_type = None
        self._current_login_url = None
        self._browser_wrapper = None

        if self._page:
            self._page.close()
            self._page = None

        if self._context:
            self._context.close()
            self._context = None

        if self._browser:
            self._browser.close()
            self._browser = None

    def clear_error(self) -> None:
        """Clears error state and returns to appropriate status based on current auth state."""
        if self.session_state.is_error():
            self.session_state.error_message = None
            # Determine correct status based on actual authentication state
            if self._current_auth_strategy and self._current_auth_strategy.is_logged_in():
                self.session_state.status = SessionStatus.LOGGED_IN
            else:
                self.session_state.status = SessionStatus.LOGGED_OUT

    def close_all_pages_and_open_new(self):
        if self._context:
            for page in self._context.pages:
                page.close()
            self._page = self._context.new_page()
            self._browser_wrapper = PlaywrightWrapper(self._page)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
