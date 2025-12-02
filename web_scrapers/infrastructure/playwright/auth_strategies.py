import time
from typing import Optional

import requests

from web_scrapers.domain.entities.auth_strategies import AuthBaseStrategy
from web_scrapers.domain.entities.session import Credentials
from web_scrapers.domain.enums import CarrierPortalUrls
from web_scrapers.infrastructure.playwright.browser_wrapper import BrowserWrapper


class BellEnterpriseAuthStrategy(AuthBaseStrategy):
    """Authentication strategy for Bell Enterprise Centre (https://enterprisecentre.bell.ca) - for monthly reports."""

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = "http://localhost:8000"):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url

    def login(self, credentials: Credentials) -> bool:
        try:
            # Navigate to the Enterprise Centre login URL
            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_page_load(60000)
            time.sleep(3)  # Wait for page stabilization

            # Fill username field
            username_xpath = "//*[@id='Username']"
            self.browser_wrapper.type_text(username_xpath, credentials.username)
            time.sleep(1)

            # Fill password field
            password_xpath = "//*[@id='Password']"
            self.browser_wrapper.type_text(password_xpath, credentials.password)
            time.sleep(1)

            # Click login button
            login_button_xpath = "//*[@id='loginBtn']"
            self.browser_wrapper.click_element(login_button_xpath)

            # Wait for page to load
            self.browser_wrapper.wait_for_page_load()
            time.sleep(10)  # Wait for page stabilization

            # Verify login was successful
            return self.is_logged_in()

        except Exception as e:
            print(f"❌ Error during Enterprise Centre login: {str(e)}")
            return False

    def logout(self) -> bool:
        try:
            # Click on the logout link in the sidebar
            logout_xpath = "nav:nth-child(4) > div:nth-child(1) > div:nth-child(1) > div:nth-child(3) > ul:nth-child(2) > li:nth-child(4) > a:nth-child(1) > span:nth-child(1)"
            self.browser_wrapper.click_element(logout_xpath, selector_type="css")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            print("✅ Logout successful in Bell Enterprise Centre")
            return not self.is_logged_in()

        except Exception as e:
            print(f"❌ Error during logout: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        try:
            login_form_xpath = "//*[@id='loginBtn']"
            # If login button is still visible, we're not logged in
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


class BellAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = "http://localhost:8000"):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url

    def login(self, credentials: Credentials) -> bool:
        try:
            # Navegar a la URL de login
            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_page_load(60000)
            time.sleep(3)  # Esperar 3 segundos adicionales para estabilización

            # Ingresar email
            email_xpath = (
                "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/div[1]/div[2]/input[1]"
            )
            self.browser_wrapper.type_text(email_xpath, credentials.username)
            time.sleep(1)  # Pequeña pausa entre campos

            # Ingresar password
            password_xpath = (
                "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/div[2]/div[2]/input[1]"
            )
            self.browser_wrapper.type_text(password_xpath, credentials.password)
            time.sleep(1)  # Pequeña pausa antes del clic

            # Hacer clic en el botón de login
            login_button_xpath = "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/button[1]"
            self.browser_wrapper.click_element(login_button_xpath)

            # Esperar tiempo suficiente para que la página cargue completamente
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)  # Esperar 5 segundos para que la página se estabilice

            # Verificar si aparece el formulario de 2FA
            if self._handle_2fa_if_present():
                print("✅ 2FA completado exitosamente")
            else:
                print("ℹ️ No se detectó 2FA o no fue necesario")

            # Verificar si el login fue exitoso
            return self.is_logged_in()

        except Exception as e:
            print(f"❌ Error durante el login: {str(e)}")
            return False

    def logout(self) -> bool:
        try:
            # Bell logo to reset navigation (click)
            bell_logo_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/a[1]"
            self.browser_wrapper.click_element(bell_logo_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)  # Esperar 3 segundos

            # user button (click)
            user_button_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/logout[1]/div[1]/button[1]"
            self.browser_wrapper.click_element(user_button_xpath)
            time.sleep(2)  # Esperar 2 segundos

            # logout button (click)
            logout_button_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/logout[1]/div[1]/div[1]/div[2]/div[1]/button[1]"
            self.browser_wrapper.click_element(logout_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)  # Esperar 3 segundos

            return not self.is_logged_in()

        except Exception as e:
            # log exception e
            return False

    def is_logged_in(self) -> bool:
        try:
            user_button_xpath = "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/logout[1]/div[1]/button[1]"
            return self.browser_wrapper.is_element_visible(
                user_button_xpath, timeout=10000
            )  # Aumentar timeout a 10 segundos
        except Exception:
            return False

    def get_login_url(self) -> str:
        return CarrierPortalUrls.BELL.value

    def get_logout_xpath(self) -> str:
        """Retorna el XPath del botón de logout específico de Bell."""
        return "/html[1]/body[1]/div[1]/header[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/logout[1]/div[1]/div[1]/div[2]/div[1]/button[1]"

    def get_username_xpath(self) -> str:
        """Retorna el XPath del campo de email específico de Bell."""
        return "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/div[1]/div[2]/input[1]"

    def get_password_xpath(self) -> str:
        """Retorna el XPath del campo de password específico de Bell."""
        return "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/div[2]/div[2]/input[1]"

    def get_login_button_xpath(self) -> str:
        """Retorna el XPath del botón de login específico de Bell."""
        return "/html[1]/body[1]/main[1]/div[4]/div[1]/div[1]/div[2]/div[2]/div[2]/form[1]/button[1]"

    def _handle_2fa_if_present(self) -> bool:
        """Detecta y maneja el proceso de 2FA si está presente."""
        try:
            # XPath del campo de verificación de 2FA
            verification_input_xpath = "/html/body/main/div/div[1]/div/div[2]/uxp-flow/div/identity-verification/div/div[1]/form/div[2]/div[2]/div[3]/div[2]/div[1]/input"
            radio_button = "/html/body/main/div/div[1]/div/div[2]/uxp-flow/div/identity-verification/div/div[1]/form/div[1]/section/div[2]/div/label[1]/input"
            # Verificar si existe el campo de 2FA
            if self.browser_wrapper.is_element_visible(radio_button, timeout=40000):
                print("🔐 Campo de 2FA detectado. Iniciando proceso de verificación...")
                return self._process_2fa(verification_input_xpath)
            else:
                print("ℹ️ No se detectó campo de 2FA")
                time.sleep(10)
                return True

        except Exception as e:
            print(f"⚠️ Error verificando 2FA: {str(e)}")
            return True  # Continuar si hay error

    def _process_2fa(self, verification_input_xpath: str) -> bool:
        """Procesa el flujo completo de 2FA."""
        try:
            # XPaths para los elementos de 2FA
            text_message_radio_xpath = "/html/body/main/div/div[1]/div/div[2]/uxp-flow/div/identity-verification/div/div[1]/form/div[1]/section/div[2]/div/label[2]"
            send_button_xpath = "/html/body/main/div/div[1]/div/div[2]/uxp-flow/div/identity-verification/div/div[1]/form/div[2]/div[2]/div[2]/div[2]/button"
            continue_button_xpath = (
                "/html/body/main/div/div[1]/div/div[2]/uxp-flow/div/identity-verification/div/div[2]/div/button[1]"
            )

            # 1. Seleccionar radio button de "Text Message"
            print("📱 Seleccionando opción de mensaje de texto...")
            self.browser_wrapper.click_element(text_message_radio_xpath)
            time.sleep(1)

            # 2. Hacer clic en el botón "Send"
            print("📤 Enviando solicitud de código SMS...")
            self.browser_wrapper.click_element(send_button_xpath)
            time.sleep(2)

            # 3. Esperar y obtener el código SMS del webhook
            print("⏳ Esperando código SMS del webhook...")
            sms_code = self._wait_for_sms_code(timeout=120)
            if not sms_code:
                print("❌ No se recibió código SMS en el tiempo esperado")
                return False

            # 4. Ingresar el código en el campo de verificación
            print(f"🔢 Ingresando código: {sms_code}")
            self.browser_wrapper.click_element(verification_input_xpath)
            self.browser_wrapper.clear_and_type(verification_input_xpath, sms_code)
            time.sleep(1)

            # 5. Hacer clic en Continue
            print("➡️ Haciendo clic en Continue...")
            self.browser_wrapper.change_button_attribute(continue_button_xpath, "disabled", "false")
            self.browser_wrapper.click_element(continue_button_xpath)

            # 6. Esperar que la página se procese
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # 7. Verificar que la validación fue exitosa
            # Si seguimos viendo el campo de 2FA, significa que falló
            if self.browser_wrapper.is_element_visible(verification_input_xpath, timeout=3000):
                print("❌ La validación 2FA falló - el campo sigue visible")
                return False

            print("✅ Validación 2FA exitosa")
            return True

        except Exception as e:
            print(f"❌ Error durante el proceso 2FA: {str(e)}")
            return False

    def _wait_for_sms_code(self, timeout: int = 120) -> str:
        """Espera a que llegue un código SMS del webhook."""
        start_time = time.time()
        check_interval = 3  # Verificar cada 3 segundos

        print(f"⏳ Esperando código SMS por hasta {timeout} segundos...")

        while time.time() - start_time < timeout:
            try:
                # Hacer request al webhook para obtener el código
                response = requests.get(f"{self.webhook_url}/code", timeout=5)

                if response.status_code == 200:
                    data = response.json()

                    if data.get("code") and data.get("status") == "available":
                        # Consumir el código para marcarlo como usado
                        consume_response = requests.post(f"{self.webhook_url}/code/consume", timeout=5)

                        if consume_response.status_code == 200:
                            consume_data = consume_response.json()
                            if consume_data.get("status") == "consumed":
                                print(f"✅ Código SMS recibido: {data['code']}")
                                return data["code"]

                # Si no hay código disponible, esperar antes del siguiente intento
                print(f"⏳ Esperando código... ({int(time.time() - start_time)}s/{timeout}s)")
                time.sleep(check_interval)

            except requests.RequestException as e:
                print(f"⚠️ Error conectando con webhook: {str(e)}")
                time.sleep(check_interval)
            except Exception as e:
                print(f"⚠️ Error inesperado: {str(e)}")
                time.sleep(check_interval)

        print("❌ Timeout esperando código SMS")
        return None


class TelusAuthStrategy(AuthBaseStrategy):

    def login(self, credentials: Credentials) -> bool:
        """Implementa el flujo de login específico para Telus con XPaths reales."""
        try:
            print("🔐 Iniciando login en Telus...")

            # 1. Navegar a la URL de login
            login_url = self.get_login_url()
            self.browser_wrapper.goto(login_url)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            # 2. Click en el botón "My Telus"
            my_telus_button_xpath = (
                "/html[1]/body[1]/div[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[1]/button[1]/span[1]/span[1]"
            )
            print("📱 Haciendo clic en My Telus...")
            self.browser_wrapper.click_element(my_telus_button_xpath)
            time.sleep(2)

            # 3. Click en "My Telus Web"
            my_telus_web_button_xpath = "/html[1]/body[1]/div[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[1]/nav[1]/div[1]/ul[1]/li[1]/a[1]"
            print("🌐 Haciendo clic en My Telus Web...")
            self.browser_wrapper.click_element(my_telus_web_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            # 4. Llenar campo de email
            email_field_xpath = (
                "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[1]/div[1]/div[3]/input[1]"
            )
            print(f"📧 Ingresando email: {credentials.username}")
            self.browser_wrapper.clear_and_type(email_field_xpath, credentials.username)
            time.sleep(1)

            # 5. Llenar campo de contraseña
            password_field_xpath = (
                "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[2]/div[3]/input[1]"
            )
            print("🔒 Ingresando contraseña...")
            self.browser_wrapper.clear_and_type(password_field_xpath, credentials.password)
            time.sleep(1)

            # 6. Click en botón de login
            login_button_xpath = "/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/form[1]/div[4]/div[1]"
            print("🚀 Haciendo clic en Login...")
            self.browser_wrapper.click_element(login_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # 7. Verificar si el login fue exitoso
            if self.is_logged_in():
                print("✅ Login exitoso en Telus")
                return True
            else:
                print("❌ Login falló en Telus")
                return False

        except Exception as e:
            print(f"❌ Error durante login en Telus: {str(e)}")
            return False

    def logout(self) -> bool:
        """Implementa el flujo de logout específico para Telus."""
        try:
            print("🚪 Iniciando logout en Telus...")
            self.browser_wrapper.goto("https://www.telus.com/my-telus")
            # 1. Click en avatar menu
            avatar_menu_xpath = "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[3]/button[1]"
            print("👤 Haciendo clic en avatar menu...")
            self.browser_wrapper.click_element(avatar_menu_xpath)
            time.sleep(2)

            # 2. Click en logout button
            logout_button_xpath = (
                "/html[1]/body[1]/header[1]/div[1]/div[2]/div[1]/nav[1]/ul[2]/li[3]/nav[1]/div[1]/ul[1]/li[5]/a[1]"
            )
            print("🚪 Haciendo clic en Logout...")
            self.browser_wrapper.click_element(logout_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            print("✅ Logout exitoso en Telus")
            return True

        except Exception as e:
            print(f"❌ Error durante logout en Telus: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        """Verifica si el usuario está logueado verificando la presencia del avatar menu."""
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


class RogersAuthStrategy(AuthBaseStrategy):

    def login(self, credentials: Credentials) -> bool:
        return self._perform_generic_login(credentials)

    def logout(self) -> bool:
        return self._perform_generic_logout()

    def is_logged_in(self) -> bool:
        return self.browser_wrapper.is_element_visible(
            self.get_logout_xpath(), timeout=10000
        )  # Aumentar timeout a 10 segundos

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


class ATTAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = "http://localhost:8000"):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url

    def login(self, credentials: Credentials) -> bool:
        try:
            print("🔐 Iniciando login en AT&T...")

            # Navegar a la URL de login
            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_page_load(60000)
            time.sleep(3)  # Esperar 3 segundos adicionales para estabilización

            # Ingresar username
            username_xpath = (
                "/html/body/app-root/div/div/div/div/app-login-general/app-card/div/div/div/form/div[1]/input"
            )
            print(f"👤 Ingresando username: {credentials.username}")
            self.browser_wrapper.type_text(username_xpath, credentials.username)
            time.sleep(1)  # Pequeña pausa entre campos

            # Click en continue button
            continue_button_xpath = (
                "/html/body/app-root/div/div/div/div/app-login-general/app-card/div/div/div/form/div[3]/button"
            )
            print("➡️ Haciendo clic en Continue...")
            self.browser_wrapper.click_element(continue_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            # Ingresar password
            password_xpath = (
                "/html/body/app-root/div/div/div/div/app-login-password/app-card/div/div/div/form/div[2]/input"
            )
            print("🔒 Ingresando contraseña...")
            self.browser_wrapper.type_text(password_xpath, credentials.password)
            time.sleep(1)  # Pequeña pausa antes del clic

            # Hacer clic en el botón de sign in
            signin_button_xpath = (
                "/html/body/app-root/div/div/div/div/app-login-password/app-card/div/div/div/form/div[3]/button"
            )
            print("🚀 Haciendo clic en Sign In...")
            self.browser_wrapper.click_element(signin_button_xpath)

            # Esperar tiempo suficiente para que la página cargue completamente
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)  # Esperar 5 segundos para que la página se estabilice

            # Verificar si aparece el formulario de 2FA
            if self._handle_2fa_if_present():
                print("✅ 2FA completado exitosamente")
            else:
                print("ℹ️ No se detectó 2FA o no fue necesario")

            # Verificar si el login fue exitoso
            return self.is_logged_in()

        except Exception as e:
            print(f"❌ Error durante el login en AT&T: {str(e)}")
            return False

    def logout(self) -> bool:
        """Implementa el flujo de logout específico para AT&T."""
        try:
            print("🚪 Iniciando logout en AT&T...")

            # Navegar a la página principal
            self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            # Revisar si está loggeado antes de intentar logout
            if not self.is_logged_in():
                print("ℹ️ Usuario ya desloggeado")
                return True

            # Hacer clic en logout button
            logout_button_xpath = "/html/body/div[1]/div/div[1]/ul/li[4]/a"
            print("🚪 Haciendo clic en Logout...")
            self.browser_wrapper.click_element(logout_button_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            print("✅ Logout exitoso en AT&T")
            return True

        except Exception as e:
            print(f"❌ Error durante logout en AT&T: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        """Verifica si el usuario está logueado verificando la presencia de 'My Profile'."""
        try:
            # Asegurar que estamos en la página principal
            current_url = self.browser_wrapper.get_current_url()
            if "premiercare" not in current_url.lower():
                self.browser_wrapper.goto("https://www.wireless.att.com/premiercare/")
                self.browser_wrapper.wait_for_page_load()
                time.sleep(2)

            # Verificar que exista el elemento y que tenga texto 'My Profile'
            my_profile_xpath = "/html/body/div[1]/div/div[2]/p/a"
            if self.browser_wrapper.is_element_visible(my_profile_xpath, timeout=10000):
                element_text = self.browser_wrapper.get_text(my_profile_xpath)
                if element_text and "My Profile" in element_text:
                    return True

            return False

        except Exception as e:
            print(f"❌ Error verificando login status: {str(e)}")
            return False

    def get_login_url(self) -> str:
        return CarrierPortalUrls.ATT.value

    def get_logout_xpath(self) -> str:
        """Retorna el XPath del botón de logout específico de AT&T."""
        # TODO: Definir XPath correcto cuando se especifique el logout
        return ""

    def get_username_xpath(self) -> str:
        """Retorna el XPath del campo de username específico de AT&T."""
        return "/html/body/app-root/div/div/div/div/app-login-general/app-card/div/div/div/form/div[1]/input"

    def get_password_xpath(self) -> str:
        """Retorna el XPath del campo de password específico de AT&T."""
        return "/html/body/app-root/div/div/div/div/app-login-password/app-card/div/div/div/form/div[2]/input"

    def get_login_button_xpath(self) -> str:
        """Retorna el XPath del botón de sign in específico de AT&T."""
        return "/html/body/app-root/div/div/div/div/app-login-password/app-card/div/div/div/form/div[3]/button"

    def _handle_2fa_if_present(self) -> bool:
        """
        Maneja el flujo de 2FA si está presente.
        Devuelve True si el 2FA fue exitoso, False si no fue necesario o falló.
        """
        try:
            print("🔍 Verificando si se requiere 2FA...")

            # Verificar si hay elementos de 2FA presentes con timeout corto
            sms_label_xpath = "/html/body/div[2]/div/form[1]/fieldset/div[1]/fieldset/div[1]/label"
            if not self.browser_wrapper.is_element_visible(sms_label_xpath, timeout=10000):
                print("ℹ️ No se detectaron elementos de 2FA")
                return True  # No hay 2FA, continuar normalmente

            print("📱 Detectado flujo de 2FA, procediendo...")

            # Hacer clic en el label de SMS
            print("📱 Seleccionando opción de SMS...")
            self.browser_wrapper.click_element(sms_label_xpath)
            time.sleep(2)

            # Hacer clic en el botón para enviar el código SMS
            send_code_button_xpath = "/html/body/div[2]/div/form[1]/fieldset/div[4]/input[3]"
            print("📤 Solicitando código SMS...")
            self.browser_wrapper.click_element(send_code_button_xpath)
            time.sleep(3)

            # Obtener el código del webhook
            print("🔄 Esperando código SMS del webhook...")
            code = self._get_2fa_code_from_webhook()

            if not code:
                print("❌ No se pudo obtener el código 2FA")
                return False

            print(f"📥 Código recibido: {code}")

            # Ingresar el código en el campo de input
            code_input_xpath = "/html/body/div[2]/div/form[1]/fieldset/div[1]/input[1]"
            print("⌨️ Ingresando código 2FA...")
            self.browser_wrapper.type_text(code_input_xpath, code)
            time.sleep(1)

            # Hacer clic en continuar
            continue_button_xpath = "/html/body/div[2]/div/form[1]/fieldset/div[4]/input[3]"
            print("➡️ Enviando código 2FA...")
            self.browser_wrapper.click_element(continue_button_xpath)

            # Marcar código como consumido en el webhook
            self._consume_2fa_code()

            # Esperar a que la página cargue después del 2FA
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            print("✅ 2FA procesado exitosamente")
            return True

        except Exception as e:
            print(f"❌ Error durante el manejo de 2FA: {str(e)}")
            return False

    def _get_2fa_code_from_webhook(self, max_retries: int = 30, retry_interval: int = 10) -> Optional[str]:
        """Obtiene el código 2FA desde el webhook de AT&T con reintentos."""
        for attempt in range(max_retries):
            try:
                print(f"🔄 Intento {attempt + 1}/{max_retries} para obtener código SMS...")
                response = requests.get(f"{self.webhook_url}/att/code", timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    code = data.get("code")

                    if code:
                        print(f"✅ Código SMS obtenido del webhook: {code}")
                        return code
                    else:
                        status = data.get("status", "unknown")
                        print(f"⏳ Sin código disponible (status: {status}), esperando...")
                else:
                    print(f"⚠️ Error HTTP {response.status_code} del webhook")

            except requests.exceptions.RequestException as e:
                print(f"❌ Error conectando al webhook: {e}")

            if attempt < max_retries - 1:  # No esperar en el último intento
                time.sleep(retry_interval)

        print(f"❌ No se pudo obtener código SMS después de {max_retries} intentos")
        return None

    def _consume_2fa_code(self) -> bool:
        """Marca el código 2FA como consumido en el webhook de AT&T."""
        try:
            response = requests.post(f"{self.webhook_url}/att/code/consume", timeout=5)
            if response.status_code == 200:
                print("✅ Código 2FA marcado como consumido")
                return True
            else:
                print(f"⚠️ Error al consumir código: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Error consumiendo código: {e}")
            return False


class TMobileAuthStrategy(AuthBaseStrategy):
    """Estrategia de autenticación específica para T-Mobile con manejo de 2FA."""

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = "http://localhost:8000"):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url

    def login(self, credentials: Credentials) -> bool:
        """Realiza el login en el portal de T-Mobile con soporte para 2FA."""
        try:
            print(f"🔐 Iniciando login en T-Mobile...")

            # 1. Navegar a la página de login
            self.browser_wrapper.goto(self.get_login_url())
            time.sleep(3)

            # 2. Verificar si está presente el botón opcional y hacer click si existe
            optional_button_xpath = "/html/body/div/div/div[3]/ul/li[2]/button"
            if self.browser_wrapper.is_element_visible(optional_button_xpath, timeout=5000):
                print("🔘 Botón opcional detectado, haciendo click...")
                self.browser_wrapper.click_element(optional_button_xpath)
                time.sleep(2)
            else:
                print("ℹ️ Botón opcional no encontrado, continuando...")

            # 3. Introducir username
            user_input_xpath = "/html/body/app-initiation/div/app-root/div/div[3]/div/div/div/div[2]/app-login/div[2]/div/div/div/div/div/form/div/div[1]/div/input"
            print(f"📧 Introduciendo username: {credentials.username}")
            self.browser_wrapper.fill_input(user_input_xpath, credentials.username)
            time.sleep(1)

            # 4. Click en next button
            next_button_xpath = "/html/body/app-initiation/div/app-root/div/div[3]/div/div/div/div[2]/app-login/div[2]/div/div/div/div/div/form/div/div[2]/button"
            print("➡️ Haciendo click en Next...")
            self.browser_wrapper.click_element(next_button_xpath)
            time.sleep(3)

            # 5. Introducir password
            password_input_xpath = "/html/body/app-initiation/div/app-root/div/div[2]/div/div/div/div[2]/app-login/div[2]/div/div/div/div[1]/div/form/div/div[1]/div/input"
            print("🔒 Introduciendo password...")
            self.browser_wrapper.fill_input(password_input_xpath, credentials.password)
            time.sleep(1)

            # 6. Click en log in button
            login_button_xpath = "/html/body/app-initiation/div/app-root/div/div[2]/div/div/div/div[2]/app-login/div[2]/div/div/div/div[1]/div/form/div/button"
            print("🔑 Haciendo click en Log In...")
            self.browser_wrapper.click_element(login_button_xpath)
            time.sleep(5)

            # 7. Verificar si hay 2FA presente
            if not self._handle_2fa_if_present():
                print("❌ Error en proceso de 2FA")
                return False

            # 8. Verificar que el login fue exitoso
            if self.is_logged_in():
                print("✅ Login exitoso en T-Mobile")
                return True
            else:
                print("❌ Login falló en T-Mobile")
                return False

        except Exception as e:
            print(f"❌ Error durante login en T-Mobile: {str(e)}")
            return False

    def logout(self) -> bool:
        """Realiza logout del portal T-Mobile."""
        try:
            print("🚪 Realizando logout de T-Mobile...")

            # Verificar si ya estamos en estado de logout
            if not self.is_logged_in():
                print("ℹ️ Ya estamos en estado de logout")
                return True

            # Hacer click en el elemento del sidebar para logout/reset
            logout_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[1]/mat-panel-title/mat-list-item"
            if self.browser_wrapper.is_element_visible(logout_xpath, timeout=5000):
                self.browser_wrapper.click_element(logout_xpath)
                time.sleep(2)
                print("✅ Logout exitoso en T-Mobile")
                return True
            else:
                print("⚠️ Elemento de logout no encontrado")
                return False

        except Exception as e:
            print(f"❌ Error durante logout en T-Mobile: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        """Verifica si el usuario está logueado en T-Mobile."""
        try:
            # Verificar que existe el path del sidebar que indica que está loggeado
            logged_in_xpath = "/html/body/globalnav-root/globalnav-nav/mat-sidenav-container/mat-sidenav/div/mat-nav-list[1]/mat-panel-title/mat-list-item"
            return self.browser_wrapper.is_element_visible(logged_in_xpath, timeout=5000)
        except Exception:
            return False

    def get_login_url(self) -> str:
        return CarrierPortalUrls.TMOBILE.value

    def _handle_2fa_if_present(self) -> bool:
        """Detecta y maneja el proceso de 2FA si está presente siguiendo el patrón de Bell."""
        try:
            # TODO: Implementar detección y manejo de 2FA para T-Mobile
            # Debe seguir el patrón de Bell con webhook SMS
            print("ℹ️ Verificación de 2FA para T-Mobile - implementar siguiendo patrón de Bell")
            time.sleep(5)
            return True

        except Exception as e:
            print(f"❌ Error en proceso de 2FA en T-Mobile: {str(e)}")
            return False


class VerizonAuthStrategy(AuthBaseStrategy):

    def __init__(self, browser_wrapper: BrowserWrapper, webhook_url: str = "http://localhost:8000"):
        super().__init__(browser_wrapper)
        self.webhook_url = webhook_url

    def login(self, credentials: Credentials) -> bool:
        try:
            print("🔐 Iniciando login en Verizon...")

            # Navegar a la URL de login
            self.browser_wrapper.goto(self.get_login_url())
            self.browser_wrapper.wait_for_page_load(60000)
            time.sleep(3)  # Esperar 3 segundos adicionales para estabilización

            # Ingresar email
            username_xpath = (
                "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[1]/input[1]"
            )
            print(f"📧 Ingresando email: {credentials.username}")
            self.browser_wrapper.type_text(username_xpath, credentials.username)
            time.sleep(1)  # Pequeña pausa entre campos

            # Ingresar password
            password_xpath = (
                "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[2]/input[1]"
            )
            print("🔒 Ingresando contraseña...")
            self.browser_wrapper.type_text(password_xpath, credentials.password)
            time.sleep(1)  # Pequeña pausa antes del clic

            # Hacer clic en el botón de login
            login_button_xpath = (
                "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[4]/button[1]"
            )
            print("🚀 Haciendo clic en Login...")
            self.browser_wrapper.click_element(login_button_xpath)

            # Esperar tiempo suficiente para que la página cargue completamente
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)  # Esperar 5 segundos para que la página se estabilice

            # Verificar si aparece el formulario de 2FA
            if self._handle_2fa_if_present():
                print("✅ 2FA completado exitosamente")
            else:
                print("ℹ️ No se detectó 2FA o no fue necesario")

            # Verificar si el login fue exitoso
            if self.is_logged_in():
                print("✅ Login exitoso en Verizon")
                return True
            else:
                print("❌ Login falló en Verizon")
                return False

        except Exception as e:
            print(f"❌ Error durante el login en Verizon: {str(e)}")
            return False

    def logout(self) -> bool:
        try:
            print("🚪 Iniciando logout en Verizon...")

            # Click en el icono del usuario
            user_icon_xpath = "/html/body/app-root/app-secure-layout/app-header/div/div[1]/div/div/div[1]/div[2]/header/div/div/div[3]/nav/ul/li/div[1]"
            print("👤 Haciendo clic en icono de usuario...")
            self.browser_wrapper.click_element(user_icon_xpath)
            time.sleep(2)

            # Click en sign out
            sign_out_xpath = "/html/body/app-root/app-secure-layout/app-header/div/div[1]/div/div/div[1]/div[2]/header/div/div/div[3]/nav/ul/li/div[2]/ul/li[6]/a"
            print("🚪 Haciendo clic en Sign Out...")
            self.browser_wrapper.click_element(sign_out_xpath)
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)

            print("✅ Logout exitoso en Verizon")
            return not self.is_logged_in()

        except Exception as e:
            print(f"❌ Error durante logout en Verizon: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        try:
            # Verificar la presencia del icono de usuario que indica que estamos logueados
            user_icon_xpath = "/html/body/app-root/app-secure-layout/app-header/div/div[1]/div/div/div[1]/div[2]/header/div/div/div[3]/nav/ul/li/div[1]"
            return self.browser_wrapper.is_element_visible(user_icon_xpath, timeout=10000)
        except Exception:
            return False

    def get_login_url(self) -> str:
        return CarrierPortalUrls.VERIZON.value

    def get_logout_xpath(self) -> str:
        """Retorna el XPath del botón de logout específico de Verizon."""
        return "/html/body/app-root/app-secure-layout/app-header/div/div[1]/div/div/div[1]/div[2]/header/div/div/div[3]/nav/ul/li/div[2]/ul/li[6]/a"

    def get_username_xpath(self) -> str:
        """Retorna el XPath del campo de email específico de Verizon."""
        return "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[1]/input[1]"

    def get_password_xpath(self) -> str:
        """Retorna el XPath del campo de password específico de Verizon."""
        return "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[2]/input[1]"

    def get_login_button_xpath(self) -> str:
        """Retorna el XPath del botón de login específico de Verizon."""
        return "/html[1]/body[1]/v-app[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/form[1]/div[4]/button[1]"

    def _handle_2fa_if_present(self) -> bool:
        """Detecta y maneja el proceso de 2FA si está presente."""
        try:
            # XPath del botón de opción de texto SMS
            text_option_xpath = "/html/body/v-app/div/div/div/div[2]/div/div/div/div/div[2]/li/div[1]/div"

            # Verificar si existe la opción de 2FA por SMS
            if self.browser_wrapper.is_element_visible(text_option_xpath, timeout=40000):
                print("🔐 Campo de 2FA detectado. Iniciando proceso de verificación...")
                return self._process_2fa()
            else:
                print("ℹ️ No se detectó campo de 2FA")
                time.sleep(10)
                return True

        except Exception as e:
            print(f"⚠️ Error verificando 2FA: {str(e)}")
            return True  # Continuar si hay error

    def _process_2fa(self) -> bool:
        """Procesa el flujo completo de 2FA."""
        try:
            # XPaths para los elementos de 2FA
            text_option_xpath = "/html/body/v-app/div/div/div/div[2]/div/div/div/div/div[2]/li/div[1]/div"
            code_input_xpath = "/html/body/v-app/div/div/div/div/div[2]/div[1]/div/div/div/div[2]/form/div[2]/input"
            continue_button_xpath = (
                "/html/body/v-app/div/div/div/div/div[2]/div[1]/div/div/div/div[2]/form/div[3]/button"
            )

            # 1. Seleccionar opción de texto SMS
            print("📱 Seleccionando opción de mensaje de texto...")
            self.browser_wrapper.click_element(text_option_xpath)
            time.sleep(2)

            # 2. Esperar y obtener el código SMS del webhook
            print("⏳ Esperando código SMS del webhook...")
            sms_code = self._wait_for_sms_code(timeout=120)
            if not sms_code:
                print("❌ No se recibió código SMS en el tiempo esperado")
                return False

            # 3. Ingresar el código en el campo de verificación
            print(f"🔢 Ingresando código: {sms_code}")
            self.browser_wrapper.click_element(code_input_xpath)
            self.browser_wrapper.clear_and_type(code_input_xpath, sms_code)
            time.sleep(1)

            # 4. Hacer clic en Continue
            print("➡️ Haciendo clic en Continue...")
            self.browser_wrapper.click_element(continue_button_xpath)

            # 5. Esperar que la página se procese
            self.browser_wrapper.wait_for_page_load()
            time.sleep(5)

            # 6. Verificar que la validación fue exitosa
            # Si seguimos viendo el campo de 2FA, significa que falló
            if self.browser_wrapper.is_element_visible(code_input_xpath, timeout=3000):
                print("❌ La validación 2FA falló - el campo sigue visible")
                return False

            print("✅ Validación 2FA exitosa")
            return True

        except Exception as e:
            print(f"❌ Error durante el proceso 2FA: {str(e)}")
            return False

    def _wait_for_sms_code(self, timeout: int = 120) -> str:
        """Espera a que llegue un código SMS del webhook de Verizon."""
        start_time = time.time()
        check_interval = 3  # Verificar cada 3 segundos

        print(f"⏳ Esperando código SMS de Verizon por hasta {timeout} segundos...")

        while time.time() - start_time < timeout:
            try:
                # Hacer request al webhook de Verizon para obtener el código
                response = requests.get(f"{self.webhook_url}/verizon/code", timeout=5)

                if response.status_code == 200:
                    data = response.json()

                    if data.get("code") and data.get("status") == "available":
                        # Consumir el código para marcarlo como usado
                        consume_response = requests.post(f"{self.webhook_url}/verizon/code/consume", timeout=5)

                        if consume_response.status_code == 200:
                            consume_data = consume_response.json()
                            if consume_data.get("status") == "consumed":
                                print(f"✅ Código SMS de Verizon recibido: {data['code']}")
                                return data["code"]

                # Si no hay código disponible, esperar antes del siguiente intento
                print(f"⏳ Esperando código de Verizon... ({int(time.time() - start_time)}s/{timeout}s)")
                time.sleep(check_interval)

            except requests.RequestException as e:
                print(f"⚠️ Error conectando con webhook de Verizon: {str(e)}")
                time.sleep(check_interval)
            except Exception as e:
                print(f"⚠️ Error inesperado: {str(e)}")
                time.sleep(check_interval)

        print("❌ Timeout esperando código SMS de Verizon")
        return None
