from abc import ABC, abstractmethod
from typing import Optional

from web_scrapers.domain.entities.session import Credentials, SessionState
from web_scrapers.infrastructure.playwright.browser_wrapper import BrowserWrapper


class AuthBaseStrategy(ABC):
    """Estrategia base abstracta para autenticación."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        self.browser_wrapper = browser_wrapper

    @abstractmethod
    def login(self, credentials: Credentials) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def logout(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def is_logged_in(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def get_login_url(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_logout_xpath(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_username_xpath(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_password_xpath(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_login_button_xpath(self) -> str:
        raise NotImplementedError()

    def _perform_generic_login(self, credentials: Credentials) -> bool:
        try:
            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_element(self.get_username_xpath())
            self.browser_wrapper.clear_and_type(self.get_username_xpath(), credentials.username)
            self.browser_wrapper.wait_for_element(self.get_password_xpath())
            self.browser_wrapper.clear_and_type(self.get_password_xpath(), credentials.password)
            self.browser_wrapper.click_element(self.get_login_button_xpath())
            self.browser_wrapper.wait_for_page_load()
            return self.is_logged_in()

        except Exception as e:
            print(f"Error durante el login: {str(e)}")
            return False

    def _perform_generic_logout(self) -> bool:
        try:
            if not self.browser_wrapper.is_element_visible(self.get_logout_xpath()):
                return False
            self.browser_wrapper.click_element(self.get_logout_xpath())
            self.browser_wrapper.wait_for_page_load()
            return not self.is_logged_in()

        except Exception as e:
            print(f"Error durante el logout: {str(e)}")
            return False
