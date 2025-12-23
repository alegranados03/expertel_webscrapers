import logging
import os
import time
from typing import Optional

import requests

from web_scrapers.domain.entities.auth_strategies import AuthBaseStrategy, MFACodeError
from web_scrapers.domain.entities.session import Credentials
from web_scrapers.domain.enums import CarrierPortalUrls
from web_scrapers.infrastructure.playwright.browser_wrapper import BrowserWrapper

# Default MFA webhook URL - can be overridden via environment variable
DEFAULT_MFA_SERVICE_URL = os.getenv("MFA_SERVICE_URL", "http://localhost:8000")


class BellEnterpriseAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = None):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url or DEFAULT_MFA_SERVICE_URL

    def login(self, credentials: Credentials) -> bool:
        try:
            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_page_load(60000)
            time.sleep(3)

            username_xpath = "//*[@id='Username']"
            self.browser_wrapper.type_text(username_xpath, credentials.username)
            time.sleep(1)

            password_xpath = "//*[@id='Password']"
            self.browser_wrapper.type_text(password_xpath, credentials.password)
            time.sleep(1)

            login_button_xpath = "//*[@id='loginBtn']"
            self.browser_wrapper.click_element(login_button_xpath)

            self.browser_wrapper.wait_for_page_load()
            time.sleep(10)

            return self.is_logged_in()

        except Exception as e:
            print(f"Error during Enterprise Centre login: {str(e)}")
            return False

    def logout(self) -> bool:
        try:
            logout_xpath = "#ec-sidebar > div > div > div.ec-sidebar__container > ul:nth-child(2) > li:nth-child(4) > a"
            self.browser_wrapper.click_element(logout_xpath, selector_type="css")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            print("Logout successful in Bell Enterprise Centre")
            return not self.is_logged_in()

        except Exception as e:
            print(f"Error during logout: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        try:
            login_form_xpath = "//*[@id='loginBtn']"
            return not self.browser_wrapper.is_element_visible(login_form_xpath, timeout=5000)
        except Exception:
            return False

    def get_login_url(self) -> str:
        return "https://enterprisecentre.bell.ca"

    def get_logout_xpath(self) -> str:
        return "//*[@id='ec-sidebar']/div/div/div[3]/ul[2]/li[4]/a"

    def get_username_xpath(self) -> str:
        return "//*[@id='Username']"

    def get_password_xpath(self) -> str:
        return "//*[@id='Password']"

    def get_login_button_xpath(self) -> str:
        return "//*[@id='loginBtn']"

    # TODO: Implementar _handle_2fa_if_present si Bell Enterprise Centre requiere 2FA
    # Pasos pendientes:
    # 1. Identificar si el portal requiere 2FA y cómo detectarlo
    # 2. Identificar los XPaths de los elementos de 2FA
    # 3. Usar el método heredado _consume_mfa_sse_stream:
    #     endpoint_url = f"{self.webhook_url}/api/v1/bell"
    #     code = self._consume_mfa_sse_stream(endpoint_url, credentials.username)


class BellAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = None):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url or DEFAULT_MFA_SERVICE_URL

    def login(self, credentials: Credentials) -> bool:
        try:
            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_page_load(60000)
            time.sleep(3)

            email_xpath = (
                "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/div[1]/div[2]/input[1]"
            )
            self.browser_wrapper.type_text(email_xpath, credentials.username)
            time.sleep(1)

            password_xpath = (
                "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/div[2]/div[2]/input[1]"
            )
            self.browser_wrapper.type_text(password_xpath, credentials.password)
            time.sleep(1)

            login_button_xpath = "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/button[1]"
            self.browser_wrapper.click_element(login_button_xpath)

            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            if not self._handle_2fa_if_present(credentials):
                print("2FA failed - interrupting login")
                return False

            return self.is_logged_in()

        except MFACodeError as e:
            print(f"MFA error during login: {str(e)}")
            return False
        except Exception as e:
            print(f"Error during login: {str(e)}")
            return False

    def logout(self) -> bool:
        try:
            bell_logo_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/a[1]"
            self.browser_wrapper.click_element(bell_logo_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            user_button_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/logout[1]/div[1]/button[1]"
            self.browser_wrapper.click_element(user_button_xpath)
            time.sleep(2)

            logout_button_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/logout[1]/div[1]/div[1]/div[2]/div[1]/button[1]"
            self.browser_wrapper.click_element(logout_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            return not self.is_logged_in()

        except Exception as e:
            return False

    def is_logged_in(self) -> bool:
        try:
            user_button_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/logout[1]/div[1]/button[1]"
            return self.browser_wrapper.is_element_visible(user_button_xpath, timeout=10000)
        except Exception:
            return False

    def get_login_url(self) -> str:
        return CarrierPortalUrls.BELL.value

    def get_logout_xpath(self) -> str:
        return "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/logout[1]/div[1]/div[1]/div[2]/div[1]/button[1]"

    def get_username_xpath(self) -> str:
        return "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/div[1]/div[2]/input[1]"

    def get_password_xpath(self) -> str:
        return "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/div[2]/div[2]/input[1]"

    def get_login_button_xpath(self) -> str:
        return "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/button[1]"

    def _handle_2fa_if_present(self, credentials: Credentials) -> bool:
        try:
            verification_input_xpath = "/html/body/main/div/div[1]/div/div[2]/uxp-flow/div/identity-verification/div/div[1]/form/div[2]/div[2]/div[3]/div[2]/div[1]/input"
            radio_button = "/html/body/main/div/div[1]/div/div[2]/uxp-flow/div/identity-verification/div/div[1]/form/div[1]/section/div[2]/div/label[1]/input"
            if self.browser_wrapper.is_element_visible(radio_button, timeout=40000):
                print("2FA field detected. Starting verification process...")
                return self._process_2fa(verification_input_xpath, credentials)
            else:
                print("No 2FA field detected")
                time.sleep(10)
                return True

        except MFACodeError:
            raise
        except Exception as e:
            print(f"Error verifying 2FA: {str(e)}")
            return True

    def _process_2fa(self, verification_input_xpath: str, credentials: Credentials) -> bool:
        text_message_radio_xpath = "/html/body/main/div/div[1]/div/div[2]/uxp-flow/div/identity-verification/div/div[1]/form/div[1]/section/div[2]/div/label[1]"
        send_button_xpath = "/html/body/main/div/div[1]/div/div[2]/uxp-flow/div/identity-verification/div/div[1]/form/div[2]/div[2]/div[2]/div[2]/button"
        continue_button_xpath = (
            "/html/body/main/div/div[1]/div/div[2]/uxp-flow/div/identity-verification/div/div[2]/div/button[1]"
        )

        print("Selecting text message option...")
        self.browser_wrapper.click_element(text_message_radio_xpath)
        time.sleep(1)

        print("Sending SMS code request...")
        self.browser_wrapper.click_element(send_button_xpath)
        time.sleep(2)

        print("Waiting for MFA code from SSE endpoint...")
        endpoint_url = f"{self.webhook_url}/api/v1/bell"
        sms_code = self._consume_mfa_sse_stream(endpoint_url, credentials.username)

        print(f"Entering code: {sms_code}")
        self.browser_wrapper.click_element(verification_input_xpath)
        self.browser_wrapper.clear_and_type(verification_input_xpath, sms_code)
        time.sleep(1)

        print("Clicking Continue...")
        self.browser_wrapper.change_button_attribute(continue_button_xpath, "disabled", "false")
        self.browser_wrapper.click_element(continue_button_xpath)

        self.browser_wrapper.wait_for_page_load()
        time.sleep(5)

        if self.browser_wrapper.is_element_visible(verification_input_xpath, timeout=3000):
            print("2FA validation failed - field still visible")
            return False

        print("2FA validation successful")
        return True


class TelusAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = None):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url or DEFAULT_MFA_SERVICE_URL

    def login(self, credentials: Credentials) -> bool:
        try:
            print("Starting login in Telus...")

            login_url = self.get_login_url()
            self.browser_wrapper.goto(login_url)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            my_telus_button_xpath = (
                "/html[1]/body[1]/div[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[1]/button[1]/span[1]/span[1]"
            )
            print("Clicking My Telus...")
            self.browser_wrapper.click_element(my_telus_button_xpath)
            time.sleep(2)

            my_telus_web_button_xpath = "/html[1]/body[1]/div[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[1]/nav[1]/div[1]/ul[1]/li[1]/a[1]"
            print("Clicking My Telus Web...")
            self.browser_wrapper.click_element(my_telus_web_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            email_field_xpath = (
                "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[1]/div[1]/div[3]/input[1]"
            )
            print(f"Entering email: {credentials.username}")
            self.browser_wrapper.clear_and_type(email_field_xpath, credentials.username)
            time.sleep(1)

            password_field_xpath = (
                "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[2]/div[3]/input[1]"
            )
            print("Entering password...")
            self.browser_wrapper.clear_and_type(password_field_xpath, credentials.password)
            time.sleep(1)

            login_button_xpath = "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[4]/div[1]"
            print("Clicking Login...")
            self.browser_wrapper.click_element(login_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            if self.is_logged_in():
                print("Login successful in Telus")
                return True
            else:
                print("Login failed in Telus")
                return False

        except Exception as e:
            print(f"Error during login in Telus: {str(e)}")
            return False

    def logout(self) -> bool:
        try:
            print("Starting logout in Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")

            avatar_menu_xpath = "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[3]/button[1]"
            print("Clicking avatar menu...")
            self.browser_wrapper.click_element(avatar_menu_xpath)
            time.sleep(2)

            logout_button_xpath = (
                "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[3]/nav[1]/div[1]/ul[1]/li[5]/a[1]"
            )
            print("Clicking Logout...")
            self.browser_wrapper.click_element(logout_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            print("Logout successful in Telus")
            return True

        except Exception as e:
            print(f"Error during logout in Telus: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        avatar_menu_xpath = "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[3]/button[1]"
        return self.browser_wrapper.is_element_visible(avatar_menu_xpath, timeout=10000)

    def get_login_url(self) -> str:
        return CarrierPortalUrls.TELUS.value

    def get_logout_xpath(self) -> str:
        return "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[3]/nav[1]/div[1]/ul[1]/li[5]/a[1]"

    def get_username_xpath(self) -> str:
        return "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[1]/div[1]/div[3]/input[1]"

    def get_password_xpath(self) -> str:
        return "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[2]/div[3]/input[1]"

    def get_login_button_xpath(self) -> str:
        return "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[4]/div[1]"

    # TODO: Implementar _handle_2fa_if_present si Telus requiere 2FA
    # Pasos pendientes:
    # 1. Identificar si el portal requiere 2FA y cómo detectarlo
    # 2. Identificar los XPaths de los elementos de 2FA
    # 3. Usar el método heredado _consume_mfa_sse_stream:
    #     endpoint_url = f"{self.webhook_url}/api/v1/telus"
    #     code = self._consume_mfa_sse_stream(endpoint_url, credentials.username)


class RogersAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = None):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url or DEFAULT_MFA_SERVICE_URL

    def login(self, credentials: Credentials) -> bool:
        try:
            result = self._perform_generic_login(credentials)
            if result:
                if not self._handle_2fa_if_present(credentials):
                    print("2FA failed - interrupting login")
                    return False
            return result
        except MFACodeError as e:
            print(f"MFA error during login in Rogers: {str(e)}")
            return False

    def logout(self) -> bool:
        return self._perform_generic_logout()

    def is_logged_in(self) -> bool:
        return self.browser_wrapper.is_element_visible(self.get_logout_xpath(), timeout=10000)

    def get_login_url(self) -> str:
        return CarrierPortalUrls.ROGERS.value or "https://www.rogers.com/business/login"

    def get_logout_xpath(self) -> str:
        return "//a[contains(@href, 'logout') or contains(text(), 'Logout') or contains(text(), 'Sign Out') or contains(text(), 'Cerrar Sesión')]"

    def get_username_xpath(self) -> str:
        return "//input[@type='text' and (@name='username' or @name='email' or @id='username' or @id='email' or @name='user')]"

    def get_password_xpath(self) -> str:
        return "//input[@type='password' and (@name='password' or @id='password' or @name='pass')]"

    def get_login_button_xpath(self) -> str:
        return "//button[@type='submit' or contains(text(), 'Login') or contains(text(), 'Sign In') or contains(text(), 'Iniciar') or contains(@value, 'Login')]"

    def _handle_2fa_if_present(self, credentials: Credentials) -> bool:
        # TODO: Implementar deteccion de 2FA para Rogers.
        # Pasos pendientes:
        # 1. Identificar el XPath del elemento que indica presencia de 2FA
        # 2. Identificar los XPaths para seleccionar metodo SMS y enviar codigo
        # 3. Identificar el XPath del campo de input para el codigo
        # 4. Identificar el XPath del boton de continuar/verificar
        #
        # Una vez identificados los elementos, usar el metodo heredado:
        #     endpoint_url = f"{self.webhook_url}/api/v1/rogers"
        #     code = self._consume_mfa_sse_stream(endpoint_url, credentials.username)
        #
        # Este metodo lanzara MFACodeError si el stream falla, interrumpiendo el login.
        print("2FA verification for Rogers - pending implementation")
        time.sleep(5)
        return True


class ATTAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = None):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url or DEFAULT_MFA_SERVICE_URL
        self.logger = logging.getLogger(self.__class__.__name__)

    def login(self, credentials: Credentials) -> bool:
        try:
            self.logger.info("Starting login in AT&T...")

            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_page_load(60000)
            time.sleep(3)

            username_xpath = (
                "/html/body/app-root/div/div/div/div/app-login-general/app-card/div/div/div/form/div[1]/input"
            )
            self.logger.info(f"Entering username: {credentials.username}")
            self.browser_wrapper.type_text(username_xpath, credentials.username)
            time.sleep(1)

            continue_button_xpath = (
                "/html/body/app-root/div/div/div/div/app-login-general/app-card/div/div/div/form/div[3]/button"
            )
            self.logger.info("Clicking Continue...")
            self.browser_wrapper.click_element(continue_button_xpath)
            time.sleep(3)

            password_xpath = (
                "/html/body/app-root/div/div/div/div/app-login-password/app-card/div/div/div/form/div[2]/input"
            )
            self.logger.info("Entering password...")
            self.browser_wrapper.type_text(password_xpath, credentials.password)
            time.sleep(1)

            signin_button_xpath = (
                "/html/body/app-root/div/div/div/div/app-login-password/app-card/div/div/div/form/div[3]/button"
            )
            self.logger.info("Clicking Sign In...")
            self.browser_wrapper.click_element(signin_button_xpath)
            time.sleep(5)

            self.logger.info("Checking for 2FA...")
            if not self._handle_2fa_if_present(credentials):
                self.logger.warning("2FA failed - interrupting login")
                return False

            return self.is_logged_in()

        except MFACodeError as e:
            self.logger.error(f"MFA error during login in AT&T: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error during login in AT&T: {str(e)}")
            return False

    def logout(self) -> bool:
        try:
            self.logger.info("Starting logout in AT&T...")

            self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
            time.sleep(30)
            if not self.is_logged_in():
                self.logger.info("User already logged out")
                return True

            logout_button_xpath = "/html/body/div[1]/div/div[1]/ul/li[4]/a"
            self.logger.info("Clicking Logout...")
            self.browser_wrapper.click_element(logout_button_xpath)
            time.sleep(15)
            self.logger.info("Logout successful in AT&T")
            return True

        except Exception as e:
            self.logger.error(f"Error during logout in AT&T: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        try:
            current_url = self.browser_wrapper.get_current_url()
            if "premiercare" not in current_url.lower():
                self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
                time.sleep(2)

            my_profile_xpath = "/html/body/div[1]/div/div[2]/p/a"
            if self.browser_wrapper.is_element_visible(my_profile_xpath, timeout=10000):
                element_text = self.browser_wrapper.get_text(my_profile_xpath)
                if element_text and "My Profile" in element_text:
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error verifying login status: {str(e)}")
            return False

    def get_login_url(self) -> str:
        return CarrierPortalUrls.ATT.value

    def get_logout_xpath(self) -> str:
        return ""

    def get_username_xpath(self) -> str:
        return "/html/body/app-root/div/div/div/div/app-login-general/app-card/div/div/div/form/div[1]/input"

    def get_password_xpath(self) -> str:
        return "/html/body/app-root/div/div/div/div/app-login-password/app-card/div/div/div/form/div[2]/input"

    def get_login_button_xpath(self) -> str:
        return "/html/body/app-root/div/div/div/div/app-login-password/app-card/div/div/div/form/div[3]/button"

    def _handle_2fa_if_present(self, credentials: Credentials) -> bool:
        self.logger.info("Checking if 2FA is required...")

        email_option_xpath = "//*[@id='option_3']"
        if not self.browser_wrapper.is_element_visible(email_option_xpath, timeout=10000):
            self.logger.info("No 2FA elements detected")
            return True

        self.logger.info("2FA flow detected, proceeding...")

        self.logger.info("Selecting Email option...")
        self.browser_wrapper.click_element(email_option_xpath)
        time.sleep(2)

        send_code_button_xpath = "//*[@id='submitVerifyIdentity']"
        self.logger.info("Requesting Email code...")
        self.browser_wrapper.click_element(send_code_button_xpath)
        time.sleep(3)

        self.logger.info("Waiting for MFA code from SSE endpoint...")
        endpoint_url = f"{self.webhook_url}/api/v1/att"
        code = self._consume_mfa_sse_stream(endpoint_url, credentials.username)

        self.logger.info(f"Code received: {code}")

        code_input_xpath = "/html/body/div[2]/div/form[1]/fieldset/div[1]/input[1]"
        self.logger.info("Entering 2FA code...")
        self.browser_wrapper.type_text(code_input_xpath, code)
        time.sleep(1)

        continue_button_xpath = "/html/body/div[2]/div/form[1]/fieldset/div[4]/input[3]"
        self.logger.info("Submitting 2FA code...")
        self.browser_wrapper.click_element(continue_button_xpath)
        time.sleep(30)
        self._dismiss_modal_if_present()

        self.logger.info("2FA processed successfully")
        return True

    def _dismiss_modal_if_present(self) -> None:
        modal_close_xpath = "/html/body/uws-wrapper[2]/div[2]/div/div[4]/div[2]"
        if self.browser_wrapper.is_element_visible(modal_close_xpath, timeout=5000):
            self.logger.info("Modal detected, dismissing...")
            self.browser_wrapper.click_element(modal_close_xpath)
            time.sleep(2)
        else:
            self.logger.debug("No modal detected")


class TMobileAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = None):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url or DEFAULT_MFA_SERVICE_URL

    def login(self, credentials: Credentials) -> bool:
        try:
            print("Starting login in T-Mobile...")

            self.browser_wrapper.goto(self.get_login_url())
            time.sleep(3)

            optional_button_xpath = "/html/body/div/div/div[3]/ul/li[2]/button"
            if self.browser_wrapper.is_element_visible(optional_button_xpath, timeout=5000):
                print("Optional button detected, clicking...")
                self.browser_wrapper.click_element(optional_button_xpath)
                time.sleep(2)
            else:
                print("Optional button not found, continuing...")

            user_input_xpath = "/html/body/app-initiation/div/app-root/div/div[3]/div/div/div/div[2]/app-login/div[2]/div/div/div/div/div/form/div/div[1]/div/input"
            print(f"Entering username: {credentials.username}")
            self.browser_wrapper.clear_and_type(user_input_xpath, credentials.username)
            time.sleep(1)

            next_button_xpath = "/html/body/app-initiation/div/app-root/div/div[3]/div/div/div/div[2]/app-login/div[2]/div/div/div/div/div/form/div/div[2]/button"
            print("Clicking Next...")
            self.browser_wrapper.click_element(next_button_xpath)
            time.sleep(3)

            password_input_xpath = "/html/body/app-initiation/div/app-root/div/div[2]/div/div/div/div[2]/app-login/div[2]/div/div/div/div[1]/div/form/div/div[1]/div/input"
            print("Entering password...")
            self.browser_wrapper.clear_and_type(password_input_xpath, credentials.password)
            time.sleep(1)

            login_button_xpath = "/html/body/app-initiation/div/app-root/div/div[2]/div/div/div/div[2]/app-login/div[2]/div/div/div/div[1]/div/form/div/button"
            print("Clicking Log In...")
            self.browser_wrapper.click_element(login_button_xpath)
            time.sleep(5)

            if not self._handle_2fa_if_present(credentials):
                print("Error in 2FA process")
                return False

            if self.is_logged_in():
                print("Login successful in T-Mobile")
                return True
            else:
                print("Login failed in T-Mobile")
                return False

        except MFACodeError as e:
            print(f"MFA error during login in T-Mobile: {str(e)}")
            return False
        except Exception as e:
            print(f"Error during login in T-Mobile: {str(e)}")
            return False

    def logout(self) -> bool:
        try:
            print("Starting logout in T-Mobile...")

            if not self.is_logged_in():
                print("Already logged out")
                return True

            logout_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[1]/mat-panel-title/mat-list-item"
            if self.browser_wrapper.is_element_visible(logout_xpath, timeout=5000):
                self.browser_wrapper.click_element(logout_xpath)
                time.sleep(2)
                print("Logout successful in T-Mobile")
                return True
            else:
                print("Logout element not found")
                return False

        except Exception as e:
            print(f"Error during logout in T-Mobile: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        try:
            logged_in_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[1]/mat-panel-title/mat-list-item"
            return self.browser_wrapper.is_element_visible(logged_in_xpath, timeout=5000)
        except Exception:
            return False

    def get_login_url(self) -> str:
        return CarrierPortalUrls.TMOBILE.value

    def _handle_2fa_if_present(self, credentials: Credentials) -> bool:
        # TODO: Implementar detección de 2FA para T-Mobile.
        # Pasos pendientes:
        # 1. Identificar el XPath del elemento que indica presencia de 2FA
        # 2. Identificar los XPaths para seleccionar método SMS y enviar código
        # 3. Identificar el XPath del campo de input para el código
        # 4. Identificar el XPath del botón de continuar/verificar
        #
        # Una vez identificados los elementos, usar el método heredado:
        #     endpoint_url = f"{self.webhook_url}/api/v1/tmobile"
        #     code = self._consume_mfa_sse_stream(endpoint_url, credentials.username)
        #
        # Este método lanzará MFACodeError si el stream falla, interrumpiendo el login.
        print("2FA verification for T-Mobile - pending implementation")
        time.sleep(5)
        return True


class VerizonAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = None):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url or DEFAULT_MFA_SERVICE_URL

    def login(self, credentials: Credentials) -> bool:
        try:
            print("Starting login in Verizon...")

            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_page_load(60000)
            time.sleep(3)

            username_xpath = (
                "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[1]/input[1]"
            )
            print(f"Entering email: {credentials.username}")
            self.browser_wrapper.type_text(username_xpath, credentials.username)
            time.sleep(1)

            password_xpath = (
                "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[2]/input[1]"
            )
            print("Entering password...")
            self.browser_wrapper.type_text(password_xpath, credentials.password)
            time.sleep(1)

            login_button_xpath = (
                "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[4]/button[1]"
            )
            print("Clicking Login...")
            self.browser_wrapper.click_element(login_button_xpath)

            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            if not self._handle_2fa_if_present(credentials):
                print("2FA failed - interrupting login")
                return False

            if self.is_logged_in():
                print("Login successful in Verizon")
                return True
            else:
                print("Login failed in Verizon")
                return False

        except MFACodeError as e:
            print(f"MFA error during login in Verizon: {str(e)}")
            return False
        except Exception as e:
            print(f"Error during login in Verizon: {str(e)}")
            return False

    def logout(self) -> bool:
        try:
            print("Starting logout in Verizon...")

            user_icon_xpath = "/html/body/app-root/app-secure-layout/app-header/div/div[1]/div/div/div[1]/div[2]/header/div/div/div[3]/nav/ul/li/div[1]"
            print("Clicking user icon...")
            self.browser_wrapper.click_element(user_icon_xpath)
            time.sleep(2)

            sign_out_xpath = "/html/body/app-root/app-secure-layout/app-header/div/div[1]/div/div/div[1]/div[2]/header/div/div/div[3]/nav/ul/li/div[2]/ul/li[6]/a"
            print("Clicking Sign Out...")
            self.browser_wrapper.click_element(sign_out_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            print("Logout successful in Verizon")
            return not self.is_logged_in()

        except Exception as e:
            print(f"Error during logout in Verizon: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        try:
            user_icon_xpath = "/html/body/app-root/app-secure-layout/app-header/div/div[1]/div/div/div[1]/div[2]/header/div/div/div[3]/nav/ul/li/div[1]"
            return self.browser_wrapper.is_element_visible(user_icon_xpath, timeout=10000)
        except Exception:
            return False

    def get_login_url(self) -> str:
        return CarrierPortalUrls.VERIZON.value

    def get_logout_xpath(self) -> str:
        return "/html/body/app-root/app-secure-layout/app-header/div/div[1]/div/div/div[1]/div[2]/header/div/div/div[3]/nav/ul/li/div[2]/ul/li[6]/a"

    def get_username_xpath(self) -> str:
        return "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[1]/input[1]"

    def get_password_xpath(self) -> str:
        return "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[2]/input[1]"

    def get_login_button_xpath(self) -> str:
        return "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[4]/button[1]"

    def _handle_2fa_if_present(self, credentials: Credentials) -> bool:
        try:
            text_option_xpath = "/html/body/v-app/div/div/div/div[2]/div/div/div/div/div[2]/li/div[1]/div"

            if self.browser_wrapper.is_element_visible(text_option_xpath, timeout=40000):
                print("2FA field detected. Starting verification process...")
                return self._process_2fa(credentials)
            else:
                print("No 2FA field detected")
                time.sleep(10)
                return True

        except MFACodeError:
            raise
        except Exception as e:
            print(f"Error verifying 2FA: {str(e)}")
            return True

    def _process_2fa(self, credentials: Credentials) -> bool:
        text_option_xpath = "/html/body/v-app/div/div/div/div[2]/div/div/div/div/div[2]/li/div[1]/div"
        code_input_xpath = "/html/body/v-app/div/div/div/div/div[2]/div[1]/div/div/div/div[2]/form/div[2]/input"
        continue_button_xpath = (
            "/html/body/v-app/div/div/div/div/div[2]/div[1]/div/div/div/div[2]/form/div[3]/button"
        )

        print("Selecting text message option...")
        self.browser_wrapper.click_element(text_option_xpath)
        time.sleep(2)

        print("Waiting for MFA code from SSE endpoint...")
        endpoint_url = f"{self.webhook_url}/api/v1/verizon"
        sms_code = self._consume_mfa_sse_stream(endpoint_url, credentials.username)

        print(f"Entering code: {sms_code}")
        self.browser_wrapper.click_element(code_input_xpath)
        self.browser_wrapper.clear_and_type(code_input_xpath, sms_code)
        time.sleep(1)

        print("Clicking Continue...")
        self.browser_wrapper.click_element(continue_button_xpath)

        self.browser_wrapper.wait_for_page_load()
        time.sleep(5)

        if self.browser_wrapper.is_element_visible(code_input_xpath, timeout=3000):
            print("2FA validation failed - field still visible")
            return False

        print("2FA validation successful")
        return True
