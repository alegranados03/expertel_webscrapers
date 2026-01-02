import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests

from mfa.infrastructure.verizon_captcha_solver import extract_text_from_image
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
            logout_xpath = (
                "#ec-sidebar > div > div > div.ec-sidebar__container > ul:nth-child(2) > li:nth-child(4) > a"
            )
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
        self.logger = logging.getLogger(self.__class__.__name__)

    def login(self, credentials: Credentials) -> bool:
        try:
            print("Starting login in Telus...")

            login_url = self.get_login_url()
            self.browser_wrapper.goto(login_url)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            # Handle potential blocking popup with skip button
            self._try_skip_popup()

            my_telus_button_xpath = '//*[@id="ge-top-nav"]/ul[2]/li[3]/button'
            print("Clicking My Telus...")
            self.browser_wrapper.click_element(my_telus_button_xpath)
            time.sleep(2)

            my_telus_web_button_xpath = '//*[@id="ge-top-nav"]/ul[2]/li[3]/nav/div/ul/li[1]/a'
            print("Clicking My Telus Web...")
            self.browser_wrapper.click_element(my_telus_web_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            email_field_xpath = '//*[@id="idtoken1"]'
            print(f"Entering email: {credentials.username}")
            self.browser_wrapper.clear_and_type(email_field_xpath, credentials.username)
            time.sleep(1)

            password_field_xpath = '//*[@id="idtoken2"]'
            print("Entering password...")
            self.browser_wrapper.clear_and_type(password_field_xpath, credentials.password)
            time.sleep(1)

            login_button_xpath = '//*[@id="login-btn"]'
            print("Clicking Login...")
            self.browser_wrapper.click_element(login_button_xpath)
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
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            avatar_menu_xpath = '//*[@id="ge-top-nav"]/ul[2]/li[3]/button'
            print("Clicking avatar menu...")
            self.browser_wrapper.click_element(avatar_menu_xpath)
            time.sleep(2)

            logout_button_xpath = '//*[@id="ge-top-nav"]/ul[2]/li[3]/nav/div/ul/li[5]/a'
            print("Clicking Logout...")
            self.browser_wrapper.click_element(logout_button_xpath)
            time.sleep(3)

            print("Logout successful in Telus")
            return True

        except Exception as e:
            print(f"Error during logout in Telus: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        """Verifica si el usuario esta logueado en Telus usando multiples metodos."""
        try:
            current_url = self.browser_wrapper.get_current_url()
            self.logger.info(f"Verificando login en URL: {current_url}")

            # Metodo 1: Verificar si estamos en my-telus (indica login exitoso)
            if "my-telus" in current_url:
                self.logger.info("URL contiene 'my-telus' - probablemente logueado")

                # Verificar elementos que solo aparecen cuando esta logueado
                logged_in_indicators = [
                    # Avatar menu button (multiples variantes)
                    "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[3]/button[1]",
                    "//button[contains(@class, 'avatar') or contains(@aria-label, 'account')]",
                    "//nav//button[contains(@class, 'user') or contains(@class, 'profile')]",
                    # Elementos del dashboard de my-telus
                    "//div[contains(@class, 'account-overview')]",
                    "//*[@id='__next']//div[contains(@class, 'dashboard')]",
                    # Cualquier elemento que indique balance o cuenta
                    "//*[contains(text(), 'Your balance') or contains(text(), 'Account')]",
                ]

                for xpath in logged_in_indicators:
                    try:
                        if self.browser_wrapper.is_element_visible(xpath, timeout=3000):
                            self.logger.info(f"Login confirmado con elemento: {xpath[:50]}...")
                            return True
                    except Exception:
                        continue

                # Si estamos en my-telus pero no encontramos indicadores, asumir logueado
                self.logger.info("En my-telus sin indicadores visibles, asumiendo logueado")
                return True

            # Metodo 2: Verificar si estamos en pagina de login (indica NO logueado)
            login_page_indicators = [
                "//input[@id='idtoken1']",  # Campo de email en login
                "//input[@id='idtoken2']",  # Campo de password en login
                "//*[@id='login-btn']",  # Boton de login
            ]

            for xpath in login_page_indicators:
                try:
                    if self.browser_wrapper.is_element_visible(xpath, timeout=2000):
                        self.logger.info(f"Pagina de login detectada con: {xpath}")
                        return False
                except Exception:
                    continue

            # Metodo 3: Navegar a my-telus para verificar
            self.logger.info("Navegando a my-telus para verificar estado de login...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            # Verificar URL despues de navegar
            new_url = self.browser_wrapper.get_current_url()
            if "my-telus" in new_url and "login" not in new_url.lower():
                self.logger.info("Navegacion exitosa a my-telus - usuario logueado")
                return True

            self.logger.info("No se pudo confirmar login")
            return False

        except Exception as e:
            self.logger.error(f"Error verificando estado de login: {str(e)}")
            return False

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

    def _try_skip_popup(self) -> None:
        """Try to dismiss a blocking popup by clicking the skip button if present."""
        skip_button_xpath = "//*[@id='skip-button']"
        try:
            if self.browser_wrapper.is_element_visible(skip_button_xpath, timeout=3000):
                print("Blocking popup detected, clicking skip button...")
                self.browser_wrapper.click_element(skip_button_xpath)
                time.sleep(1)
                print("Popup dismissed")
            else:
                print("No blocking popup detected, continuing...")
        except Exception as e:
            print(f"Error handling popup (non-critical): {str(e)}")

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
        self.logger = logging.getLogger(self.__class__.__name__)

    def login(self, credentials: Credentials) -> bool:
        try:
            self.logger.info("Starting login in T-Mobile...")

            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_page_load(60000)
            time.sleep(3)

            # Handle language modal if present (select English)
            self._handle_language_modal()

            # Enter email/phone number
            email_xpath = '//*[@id="emailOrPhoneNumberTextBox"]'
            self.logger.info(f"Entering email/phone: {credentials.username}")
            self.browser_wrapper.clear_and_type(email_xpath, credentials.username)
            time.sleep(1)

            # Click Next button
            next_button_xpath = '//*[@id="lp1-next-btn"]'
            self.logger.info("Clicking Next...")
            self.browser_wrapper.click_element(next_button_xpath)
            time.sleep(3)

            # Enter password
            password_xpath = '//*[@id="passwordTextBox"]'
            self.logger.info("Entering password...")
            self.browser_wrapper.clear_and_type(password_xpath, credentials.password)
            time.sleep(1)

            # Click Login button
            login_button_xpath = '//*[@id="lp2-login-btn"]'
            self.logger.info("Clicking Log In...")
            self.browser_wrapper.click_element(login_button_xpath)
            time.sleep(5)

            # Handle 2FA if present
            if not self._handle_2fa_if_present(credentials):
                self.logger.error("Error in 2FA process")
                return False

            if self.is_logged_in():
                self.logger.info("Login successful in T-Mobile")
                return True
            else:
                self.logger.error("Login failed in T-Mobile")
                return False

        except MFACodeError as e:
            self.logger.error(f"MFA error during login in T-Mobile: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error during login in T-Mobile: {str(e)}")
            return False

    def logout(self) -> bool:
        try:
            self.logger.info("Starting logout in T-Mobile...")

            # First, go to the dashboard
            self.browser_wrapper.goto("https://tfb.t-mobile.com/apps/tfb_billing/dashboard")
            time.sleep(3)

            if not self.is_logged_in():
                self.logger.info("Already logged out")
                return True

            # Logout button is in the second nav-list, 7th panel-title
            logout_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[2]/mat-panel-title[7]/mat-list-item"
            logout_by_text_xpath = "//mat-list-item[.//span[contains(text(), 'Logout') or contains(text(), 'logout')]]"

            if self.browser_wrapper.is_element_visible(logout_xpath, timeout=5000):
                # Verify it says "Logout" before clicking
                # Use xpath= prefix for page.locator()
                logout_text = self.browser_wrapper.page.locator(f"xpath={logout_xpath}").inner_text()
                if "logout" in logout_text.lower():
                    self.logger.info(f"Logout button found: '{logout_text}'")
                    self.browser_wrapper.click_element(logout_xpath)
                    time.sleep(3)
                    self.logger.info("Logout successful in T-Mobile")
                    return True
                else:
                    self.logger.warning(f"Element found but not logout: '{logout_text}'")

            # Fallback: try by text
            if self.browser_wrapper.is_element_visible(logout_by_text_xpath, timeout=3000):
                self.logger.info("Logout button found (by text)")
                self.browser_wrapper.click_element(logout_by_text_xpath)
                time.sleep(3)
                self.logger.info("Logout successful in T-Mobile")
                return True

            self.logger.warning("Logout element not found")
            return False

        except Exception as e:
            self.logger.error(f"Error during logout in T-Mobile: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        try:
            logged_in_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[1]/mat-panel-title/mat-list-item"
            return self.browser_wrapper.is_element_visible(logged_in_xpath, timeout=5000)
        except Exception:
            return False

    def get_login_url(self) -> str:
        return CarrierPortalUrls.TMOBILE.value

    def get_logout_xpath(self) -> str:
        return "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[1]/mat-panel-title/mat-list-item"

    def get_username_xpath(self) -> str:
        return '//*[@id="emailOrPhoneNumberTextBox"]'

    def get_password_xpath(self) -> str:
        return '//*[@id="passwordTextBox"]'

    def get_login_button_xpath(self) -> str:
        return '//*[@id="lp2-login-btn"]'

    def _handle_language_modal(self) -> None:
        """Handle the language selection modal if present (select English).

        The language modal is inside an iframe, so we need to switch context.
        """
        iframe_selector = "#lightbox_pop"
        english_button_css = "#en"
        email_field_xpath = '//*[@id="emailOrPhoneNumberTextBox"]'

        try:
            # Esperar a que el iframe del modal tenga tiempo de aparecer
            self.logger.info("Waiting for language modal iframe to potentially appear...")
            time.sleep(5)

            # Verificar si el iframe existe
            page = self.browser_wrapper.page
            iframe_locator = page.locator(iframe_selector)

            if iframe_locator.count() > 0:
                self.logger.info("Language modal iframe detected, switching context...")

                # Obtener el frame y buscar el botón dentro
                frame = page.frame_locator(iframe_selector)
                english_button = frame.locator(english_button_css)

                if english_button.count() > 0:
                    self.logger.info("English button found inside iframe, clicking...")
                    english_button.click()
                    time.sleep(3)
                    self.logger.info("Language set to English")
                else:
                    self.logger.info("English button not found inside iframe")
            else:
                self.logger.info("No language modal iframe detected, continuing...")

            # Verificar que el campo de email esté visible después de manejar el modal
            if not self.browser_wrapper.is_element_visible(email_field_xpath, timeout=10000):
                self.logger.warning("Email field not visible after language modal handling")

        except Exception as e:
            self.logger.warning(f"Error handling language modal: {str(e)}")

    def _handle_2fa_if_present(self, credentials: Credentials) -> bool:
        """Detect and handle MFA if present. Similar to Bell implementation."""
        try:
            mfa_code_input_xpath = '//*[@id="code"]'

            if self.browser_wrapper.is_element_visible(mfa_code_input_xpath, timeout=10000):
                self.logger.info("2FA field detected. Starting verification process...")
                return self._process_2fa(mfa_code_input_xpath, credentials)
            else:
                self.logger.info("No 2FA field detected")
                time.sleep(5)
                return True

        except MFACodeError:
            raise
        except Exception as e:
            self.logger.error(f"Error verifying 2FA: {str(e)}")
            return True

    def _process_2fa(self, code_input_xpath: str, credentials: Credentials) -> bool:
        """Process 2FA by waiting for code from webhook and entering it."""
        continue_button_xpath = '//*[@id="main"]/div[1]/form/div/div/div[2]/div/div[2]/button'

        self.logger.info("Waiting for MFA code from SSE endpoint...")
        endpoint_url = f"{self.webhook_url}/api/v1/tmobile"
        sms_code = self._consume_mfa_sse_stream(endpoint_url, credentials.username)

        self.logger.info(f"Entering code: {sms_code}")
        self.browser_wrapper.click_element(code_input_xpath)
        self.browser_wrapper.clear_and_type(code_input_xpath, sms_code)
        time.sleep(1)

        self.logger.info("Clicking Continue...")
        self.browser_wrapper.click_element(continue_button_xpath)

        self.browser_wrapper.wait_for_page_load()
        time.sleep(5)

        # Check if MFA field is still visible (indicates failure)
        if self.browser_wrapper.is_element_visible(code_input_xpath, timeout=3000):
            self.logger.error("2FA validation failed - field still visible")
            return False

        self.logger.info("2FA validation successful")
        return True


class VerizonAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = None):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url or DEFAULT_MFA_SERVICE_URL
        self.logger = logging.getLogger(self.__class__.__name__)

    def login(self, credentials: Credentials) -> bool:
        try:
            self.logger.info("Starting login in Verizon...")

            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_page_load(60000)
            time.sleep(3)

            # First login attempt
            if not self._fill_login_form_and_submit(credentials):
                return False

            time.sleep(10)

            # Check for CAPTCHA after first login click
            captcha_img_xpath = '//*[@id="captchaImg"]'
            if self.browser_wrapper.is_element_visible(captcha_img_xpath, timeout=3000):
                self.logger.info("CAPTCHA detected after login attempt...")

                # First CAPTCHA attempt
                if not self._solve_captcha_and_submit():
                    return False

                time.sleep(10)

                # Check if CAPTCHA still exists (failed first attempt)
                if self.browser_wrapper.is_element_visible(captcha_img_xpath, timeout=3000):
                    self.logger.warning("CAPTCHA still present")

                    # Second attempt: refill entire form
                    if not self._fill_login_form_and_submit(credentials):
                        return False

                    if not self._solve_captcha_and_submit():
                        self.logger.error("CAPTCHA failed on second attempt")
                        return False

                    time.sleep(10)

                    # If CAPTCHA still exists after second attempt, fail
                    if self.browser_wrapper.is_element_visible(captcha_img_xpath, timeout=3000):
                        self.logger.error("CAPTCHA failed after two attempts")
                        return False

            # Wait a bit for page to settle
            time.sleep(5)

            # First check if already logged in (no MFA required)
            if self.is_logged_in():
                self.logger.info("Login successful in Verizon (no MFA required)")
                return True

            # Check for MFA
            if not self._handle_2fa_if_present(credentials):
                self.logger.error("2FA failed - interrupting login")
                return False

            if self.is_logged_in():
                self.logger.info("Login successful in Verizon")
                return True
            else:
                self.logger.error("Login failed in Verizon")
                return False

        except MFACodeError as e:
            self.logger.error(f"MFA error during login in Verizon: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error during login in Verizon: {str(e)}")
            return False

    def _fill_login_form_and_submit(self, credentials: Credentials) -> bool:
        """Fill the login form with username and password, then click login."""
        try:
            username_xpath = '//*[@id="ilogin_userid"]'
            password_xpath = '//*[@id="ilogin_password"]'
            login_button_xpath = '//*[@id="ilogin_login_button"]'

            self.logger.info(f"Entering email: {credentials.username}")
            self.browser_wrapper.clear_and_type(username_xpath, credentials.username)
            time.sleep(1)

            self.logger.info("Entering password...")
            self.browser_wrapper.clear_and_type(password_xpath, credentials.password)
            time.sleep(1)

            self.logger.info("Clicking Login...")
            self.browser_wrapper.click_element(login_button_xpath)
            time.sleep(3)
            return True
        except Exception as e:
            self.logger.error(f"Error filling login form: {str(e)}")
            return False

    def _solve_captcha_and_submit(self) -> bool:
        """Solve the CAPTCHA and click login."""
        try:
            captcha_input_xpath = '//*[@id="captchaInput"]'
            login_button_xpath = '//*[@id="ilogin_login_button"]'

            screenshot_path = self._take_captcha_screenshot()
            if not screenshot_path:
                self.logger.error("Failed to take CAPTCHA screenshot")
                return False

            captcha_solution = self.send_image_to_ia(screenshot_path)
            self.logger.info(f"CAPTCHA solution (raw): {captcha_solution}")

            if not captcha_solution:
                self.logger.error("Failed to get CAPTCHA solution from AI")
                return False

            # Remove any spaces from the CAPTCHA solution
            captcha_solution = captcha_solution.replace(" ", "")
            self.logger.info(f"CAPTCHA solution (cleaned): {captcha_solution}")

            self.logger.info("Entering CAPTCHA solution...")
            self.browser_wrapper.clear_and_type(captcha_input_xpath, captcha_solution)
            time.sleep(1)

            self.logger.info("Clicking Login after CAPTCHA...")
            self.browser_wrapper.click_element(login_button_xpath)
            return True
        except Exception as e:
            self.logger.error(f"Error solving CAPTCHA: {str(e)}")
            return False

    def _take_captcha_screenshot(self) -> Optional[str]:
        """Take a screenshot of the CAPTCHA element and save it to captcha_screenshots folder."""
        import os
        from datetime import datetime

        try:
            # Create captcha_screenshots folder if it doesn't exist
            screenshots_dir = os.path.join(os.getcwd(), "captcha_screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)

            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"captcha_{timestamp}.png"
            filepath = os.path.join(screenshots_dir, filename)

            # Take screenshot of the CAPTCHA element
            captcha_element = self.browser_wrapper.page.locator("#captchaImg")
            captcha_element.screenshot(path=filepath)

            self.logger.info(f"CAPTCHA screenshot saved to: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Error taking CAPTCHA screenshot: {str(e)}")
            return None

    def send_image_to_ia(self, image_path: str) -> Optional[str]:
        """Send CAPTCHA image to AI service for solving."""
        try:
            self.logger.info(f"Sending image to AI for CAPTCHA solving: {image_path}")
            result = extract_text_from_image(Path(image_path))
            self.logger.info(f"AI returned CAPTCHA text: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error solving CAPTCHA with AI: {str(e)}")
            return None
        finally:
            try:
                Path(image_path).unlink()
                self.logger.info(f"Deleted CAPTCHA image: {image_path}")
            except Exception as e:
                self.logger.warning(f"Could not delete CAPTCHA image: {str(e)}")

    def logout(self) -> bool:
        try:
            self.logger.info("Starting logout in Verizon...")

            # Click on user menu
            user_menu_xpath = '//*[@id="gNavHeader"]/div/div/div[1]/div[2]/header/div/div/div[3]/nav/ul/li/div[1]'
            self.logger.info("Clicking user menu...")

            if self.browser_wrapper.is_element_visible(user_menu_xpath, timeout=5000):
                self.browser_wrapper.click_element(user_menu_xpath)
                time.sleep(2)
            else:
                self.logger.error("User menu not found")
                return False

            # Click on logout
            logout_xpath = '//*[@id="gn-logout-li-item"]/a'
            self.logger.info("Clicking Logout...")

            if self.browser_wrapper.is_element_visible(logout_xpath, timeout=5000):
                self.browser_wrapper.click_element(logout_xpath)
                self.browser_wrapper.wait_for_page_load()
                time.sleep(3)
            else:
                self.logger.error("Logout button not found")
                return False

            self.logger.info("Logout successful in Verizon")
            return not self.is_logged_in()

        except Exception as e:
            self.logger.error(f"Error during logout in Verizon: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        """Check if logged in by looking for the Welcome label."""
        try:
            welcome_label_xpath = '//*[@id="searchContainer"]/div[2]/label'
            if self.browser_wrapper.is_element_visible(welcome_label_xpath, timeout=10000):
                label_text = self.browser_wrapper.page.locator(welcome_label_xpath).text_content()
                if label_text and "welcome" in label_text.lower():
                    self.logger.info(f"Welcome label found: {label_text.strip()}")
                    return True
            return False
        except Exception:
            return False

    def get_login_url(self) -> str:
        return CarrierPortalUrls.VERIZON.value

    def get_logout_xpath(self) -> str:
        return "/html/body/app-root/app-secure-layout/app-header/div/div[1]/div/div/div[1]/div[2]/header/div/div/div[3]/nav/ul/li/div[2]/ul/li[6]/a"

    def get_username_xpath(self) -> str:
        return '//*[@id="ilogin_userid"]'

    def get_password_xpath(self) -> str:
        return '//*[@id="ilogin_password"]'

    def get_login_button_xpath(self) -> str:
        return '//*[@id="ilogin_login_button"]'

    def _handle_2fa_if_present(self, credentials: Credentials) -> bool:
        """Detects and handles Verizon MFA by selecting the best Email option."""
        try:
            # Check if MFA options list is visible (short timeout since we already checked is_logged_in)
            mfa_list_xpath = '//*[@id="app"]/div/div/div/div[2]/div/div/div/div/div/div[2]/li'

            if self.browser_wrapper.is_element_visible(mfa_list_xpath, timeout=10000):
                self.logger.info("MFA options detected. Starting verification process...")
                return self._process_2fa(credentials)
            else:
                self.logger.info("No MFA options detected, checking if logged in...")
                return self.is_logged_in()

        except MFACodeError:
            raise
        except Exception as e:
            self.logger.error(f"Error verifying 2FA: {str(e)}")
            return self.is_logged_in()

    def _process_2fa(self, credentials: Credentials) -> bool:
        """Process 2FA by selecting the best Email option and confirming via link."""
        # Find and click the best Email option
        self.logger.info("Finding best Email option for MFA...")
        email_option = self._find_best_email_option(credentials.username)

        if email_option is None:
            self.logger.info("Manual MFA resolution completed")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)
            return True

        # Click the selected email option using its section ID
        section_id = email_option.get("sectionId")
        if section_id:
            self.logger.info(f"Selecting Email option with ID: {section_id}...")
            self.browser_wrapper.click_element(f'//*[@id="{section_id}"]')
        else:
            # Fallback: use index-based selector
            index = email_option.get("index", 1)
            self.logger.info(f"Selecting Email option at index {index}...")
            option_xpath = f'(//*[contains(@class, "pwdless_options_section")])[{index}]'
            self.browser_wrapper.click_element(option_xpath)
        time.sleep(2)

        self.logger.info("Waiting for MFA link from SSE endpoint...")
        endpoint_url = f"{self.webhook_url}/api/v1/verizon"
        mfa_link = self._consume_mfa_sse_stream(endpoint_url, credentials.username, event_type="link")

        self.logger.info(f"MFA link received: {mfa_link}")

        # Open link in new tab and confirm Allow
        if not self._confirm_mfa_in_new_tab(mfa_link):
            self.logger.error("Failed to confirm MFA in new tab")
            return False

        # Wait for main page to update after MFA confirmation
        self.logger.info("Waiting for main page to update after MFA confirmation...")
        time.sleep(10)
        self.browser_wrapper.wait_for_page_load()

        self.logger.info("2FA validation completed")
        return True

    def _confirm_mfa_in_new_tab(self, mfa_link: str) -> bool:
        """Open MFA link in new tab, click Allow and confirm, then return to original tab."""
        allow_label_xpath = '//*[@id="dvbtn"]/form/div[1]/label'
        confirm_button_xpath = '//*[@id="dvbtn"]/button'

        try:
            # Save reference to original page
            original_page = self.browser_wrapper.page

            # Open new tab with the MFA link
            self.logger.info("Opening MFA link in new tab...")
            new_page = self.browser_wrapper.context.new_page()
            self.browser_wrapper.page = new_page
            new_page.goto(mfa_link)
            new_page.wait_for_load_state("networkidle")
            time.sleep(3)

            # Click on Allow label
            self.logger.info("Looking for Allow option...")
            if self.browser_wrapper.is_element_visible(allow_label_xpath, timeout=10000):
                label_text = new_page.locator(allow_label_xpath).text_content()
                self.logger.info(f"Found label: {label_text}")
                if label_text and "allow" in label_text.lower():
                    self.logger.info("Clicking Allow option...")
                    self.browser_wrapper.click_element(allow_label_xpath)
                    time.sleep(2)
                else:
                    self.logger.warning(f"Label does not contain 'Allow': {label_text}")
            else:
                self.logger.error("Allow label not visible")
                self.browser_wrapper.close_current_tab()
                self.browser_wrapper.page = original_page
                return False

            # Click confirm button
            self.logger.info("Clicking confirm button...")
            if self.browser_wrapper.is_element_visible(confirm_button_xpath, timeout=5000):
                self.browser_wrapper.click_element(confirm_button_xpath)
                time.sleep(3)
            else:
                self.logger.error("Confirm button not visible")
                self.browser_wrapper.close_current_tab()
                self.browser_wrapper.page = original_page
                return False

            # Close the MFA tab and return to original
            self.logger.info("MFA confirmed, closing tab and returning to original...")
            self.browser_wrapper.close_current_tab()
            self.browser_wrapper.page = original_page
            original_page.bring_to_front()
            return True

        except Exception as e:
            self.logger.error(f"Error confirming MFA in new tab: {str(e)}")
            # Try to recover by returning to original page
            try:
                self.browser_wrapper.page = original_page
                original_page.bring_to_front()
            except:
                pass
            return False

    def _find_best_email_option(self, login_email: str) -> Optional[dict]:
        """
        Find the best Email option from the MFA options list.

        Logic:
        1. Get all MFA options from the list
        2. Filter only options with method="Email"
        3. If only one Email option, use it
        4. If two Email options, use the one that is NOT "s***n@e***.com"
        """
        try:
            # Get all MFA options using JavaScript
            mfa_options = self.browser_wrapper.page.evaluate(
                """
                () => {
                    const options = [];
                    const optionSections = document.querySelectorAll('#app li .pwdless_options_section');

                    optionSections.forEach((section, index) => {
                        const deliveryOption = section.querySelector('.delivery_option_with_msg a');
                        const contactEl = section.querySelector('.pwdless_delivery_link');

                        if (deliveryOption && contactEl) {
                            const fullText = deliveryOption.textContent;
                            const method = fullText.split('\\n')[0].trim();

                            options.push({
                                index: index + 1,
                                method: method,
                                contact: contactEl.textContent.trim(),
                                sectionId: section.id || null
                            });
                        }
                    });

                    return options;
                }
            """
            )

            self.logger.info(f"Found {len(mfa_options)} MFA options")

            # Print all options found
            print(f"\n{'='*60}")
            print("ALL MFA OPTIONS FOUND:")
            for opt in mfa_options:
                print(f"  [{opt['index']}] Method: {opt['method']}, Contact: {opt['contact']}, ID: {opt['sectionId']}")
            print(f"{'='*60}\n")

            # Filter only Email options (method starts with "Email")
            email_options = [opt for opt in mfa_options if opt["method"].lower().startswith("email")]

            if not email_options:
                self.logger.warning("No Email options found in MFA list")
                print("Waiting 120 seconds for manual MFA resolution...")
                time.sleep(120)
                return None

            self.logger.info(f"Found {len(email_options)} Email option(s)")

            # If only one Email option, return it
            if len(email_options) == 1:
                self.logger.info(f"Single Email option: {email_options[0]['contact']}")
                return email_options[0]

            # If two Email options, use the one that is NOT "s***n@e***"
            excluded_pattern = "s***n@e***"
            for opt in email_options:
                if opt["contact"].lower() != excluded_pattern.lower():
                    self.logger.info(f"Selected Email option: {opt['contact']} (excluded: {excluded_pattern})")
                    return opt

            # Fallback to first Email option if all match the excluded pattern
            self.logger.warning(f"All options match excluded pattern, using first: {email_options[0]['contact']}")
            return email_options[0]

        except Exception as e:
            self.logger.error(f"Error finding Email option: {str(e)}")
            return None
