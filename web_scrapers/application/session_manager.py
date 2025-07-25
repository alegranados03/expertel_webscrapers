import time
from datetime import datetime
from typing import Dict, Optional, Type

from web_scrapers.domain.entities.auth_strategies import AuthBaseStrategy
from web_scrapers.domain.entities.session import Carrier, Credentials, SessionState, SessionStatus
from web_scrapers.domain.enums import Navigators
from web_scrapers.infrastructure.playwright.auth_strategies import (
    ATTAuthStrategy,
    BellAuthStrategy,
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

        self._auth_strategies: Dict[Carrier, Type[AuthBaseStrategy]] = {
            Carrier.BELL: BellAuthStrategy,
            Carrier.TELUS: TelusAuthStrategy,
            Carrier.ROGERS: RogersAuthStrategy,
            Carrier.ATT: ATTAuthStrategy,
            Carrier.TMOBILE: TMobileAuthStrategy,
            Carrier.VERIZON: VerizonAuthStrategy,
        }

        self._current_auth_strategy: Optional[AuthBaseStrategy] = None
        self._browser_wrapper: Optional[BrowserWrapper] = None
        self._browser = None
        self._context = None
        self._page = None

    def is_logged_in(self) -> bool:
        # Usar la lógica mejorada de refresh_session_status
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
                return False

            return is_active

        except Exception as e:
            error_msg = f"Error al verificar el estado de la sesión: {str(e)}"
            self.session_state.set_error(error_msg)
            return False

    def force_logout(self) -> None:
        self.session_state.set_logged_out()
        self._current_auth_strategy = None

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

    def login(self, credentials: Credentials) -> bool:
        try:
            if self.session_state.is_logged_in():
                if (
                    self.session_state.carrier == credentials.carrier
                    and self.session_state.credentials
                    and self.session_state.credentials.id == credentials.id
                ):
                    return True
                self.logout()

            auth_strategy_class = self._auth_strategies.get(credentials.carrier)
            if not auth_strategy_class:
                error_msg = f"No auth strategy for carrier: {credentials.carrier}"
                self.session_state.set_error(error_msg)
                return False
            browser_wrapper = self._initialize_browser()
            self._current_auth_strategy = auth_strategy_class(browser_wrapper)
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
