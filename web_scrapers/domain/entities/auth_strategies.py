import json
import time
from abc import ABC, abstractmethod
from typing import Optional

import requests

from web_scrapers.domain.entities.session import Credentials, SessionState
from web_scrapers.infrastructure.playwright.browser_wrapper import BrowserWrapper


class MFACodeError(Exception):
    """Exception raised when MFA code retrieval fails from SSE endpoint."""

    pass


class AuthBaseStrategy(ABC):
    """Estrategia base abstracta para autenticación."""

    def __init__(self, browser_wrapper: BrowserWrapper):
        self.browser_wrapper = browser_wrapper

    def _consume_mfa_sse_stream(self, endpoint_url: str, email_alias: str, timeout: int = 310) -> str:
        """
        Consume the MFA SSE stream endpoint and return the code.

        Args:
            endpoint_url: The SSE endpoint URL (e.g., "http://localhost:8000/api/bell")
            email_alias: The email alias to use for filtering
            timeout: Request timeout in seconds (default 310 to account for 5-minute SSE timeout)

        Returns:
            The MFA code as a string

        Raises:
            MFACodeError: If the stream returns an error event or fails to get the code
        """
        url = f"{endpoint_url}?email_alias={email_alias}"
        print(f"🔗 Connecting to MFA SSE stream: {url}")

        try:
            with requests.get(url, stream=True, timeout=timeout) as response:
                response.raise_for_status()

                current_event = None
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue

                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if current_event == "endpoint_error":
                            error_msg = data.get("message", "Unknown error from MFA endpoint")
                            print(f"❌ MFA endpoint error: {error_msg}")
                            raise MFACodeError(error_msg)

                        if current_event == "code":
                            code = data.get("code")
                            if code:
                                print(f"✅ MFA code received: {code}")
                                return str(code)

                        if current_event == "done":
                            # Stream ended without code
                            raise MFACodeError("Stream ended without providing a code")

            raise MFACodeError("Stream closed unexpectedly without code or error")

        except requests.exceptions.Timeout:
            raise MFACodeError("Timeout connecting to MFA SSE endpoint")
        except requests.exceptions.RequestException as e:
            raise MFACodeError(f"Error connecting to MFA SSE endpoint: {str(e)}")

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
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)  # Esperar 3 segundos para estabilización

            self.browser_wrapper.wait_for_element(self.get_username_xpath())
            self.browser_wrapper.clear_and_type(self.get_username_xpath(), credentials.username)
            time.sleep(1)  # Pequeña pausa entre campos

            self.browser_wrapper.wait_for_element(self.get_password_xpath())
            self.browser_wrapper.clear_and_type(self.get_password_xpath(), credentials.password)
            time.sleep(1)  # Pequeña pausa antes del clic

            self.browser_wrapper.click_element(self.get_login_button_xpath())
            self.browser_wrapper.wait_for_page_load()
            time.sleep(10)  # Esperar 10 segundos para que la página se estabilice

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
            time.sleep(3)  # Esperar 3 segundos
            return not self.is_logged_in()

        except Exception as e:
            print(f"Error durante el logout: {str(e)}")
            return False
