import time

import requests

from web_scrapers.domain.entities.auth_strategies import AuthBaseStrategy
from web_scrapers.domain.entities.session import Credentials
from web_scrapers.domain.enums import CarrierPortalUrls
from web_scrapers.infrastructure.playwright.browser_wrapper import BrowserWrapper


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

    def login(self, credentials: Credentials) -> bool:
        return self._perform_generic_login(credentials)

    def logout(self) -> bool:
        return self._perform_generic_logout()

    def is_logged_in(self) -> bool:
        return self.browser_wrapper.is_element_visible(
            self.get_logout_xpath(), timeout=10000
        )  # Aumentar timeout a 10 segundos

    def get_login_url(self) -> str:
        return CarrierPortalUrls.ATT.value

    def get_logout_xpath(self) -> str:
        return "//a[contains(@href, 'logout') or contains(text(), 'Logout') or contains(text(), 'Sign Out') or contains(text(), 'Cerrar Sesión')]"

    def get_username_xpath(self) -> str:
        return "//input[@type='text' and (@name='username' or @name='email' or @id='username' or @id='email' or @name='user')]"

    def get_password_xpath(self) -> str:
        return "//input[@type='password' and (@name='password' or @id='password' or @name='pass')]"

    def get_login_button_xpath(self) -> str:
        return "//button[@type='submit' or contains(text(), 'Login') or contains(text(), 'Sign In') or contains(text(), 'Iniciar') or contains(@value, 'Login')]"


class TMobileAuthStrategy(AuthBaseStrategy):

    def login(self, credentials: Credentials) -> bool:
        return self._perform_generic_login(credentials)

    def logout(self) -> bool:
        return self._perform_generic_logout()

    def is_logged_in(self) -> bool:
        return self.browser_wrapper.is_element_visible(
            self.get_logout_xpath(), timeout=10000
        )  # Aumentar timeout a 10 segundos

    def get_login_url(self) -> str:
        return CarrierPortalUrls.TMOBILE.value

    def get_logout_xpath(self) -> str:
        return "//a[contains(@href, 'logout') or contains(text(), 'Logout') or contains(text(), 'Sign Out') or contains(text(), 'Cerrar Sesión')]"

    def get_username_xpath(self) -> str:
        return "//input[@type='text' and (@name='username' or @name='email' or @id='username' or @id='email' or @name='user')]"

    def get_password_xpath(self) -> str:
        return "//input[@type='password' and (@name='password' or @id='password' or @name='pass')]"

    def get_login_button_xpath(self) -> str:
        return "//button[@type='submit' or contains(text(), 'Login') or contains(text(), 'Sign In') or contains(text(), 'Iniciar') or contains(@value, 'Login')]"


class VerizonAuthStrategy(AuthBaseStrategy):

    def login(self, credentials: Credentials) -> bool:
        return self._perform_generic_login(credentials)

    def logout(self) -> bool:
        return self._perform_generic_logout()

    def is_logged_in(self) -> bool:
        return self.browser_wrapper.is_element_visible(
            self.get_logout_xpath(), timeout=10000
        )  # Aumentar timeout a 10 segundos

    def get_login_url(self) -> str:
        return CarrierPortalUrls.VERIZON.value

    def get_logout_xpath(self) -> str:
        return "//a[contains(@href, 'logout') or contains(text(), 'Logout') or contains(text(), 'Sign Out') or contains(text(), 'Cerrar Sesión')]"

    def get_username_xpath(self) -> str:
        return "//input[@type='text' and (@name='username' or @name='email' or @id='username' or @id='email' or @name='user')]"

    def get_password_xpath(self) -> str:
        return "//input[@type='password' and (@name='password' or @id='password' or @name='pass')]"

    def get_login_button_xpath(self) -> str:
        return "//button[@type='submit' or contains(text(), 'Login') or contains(text(), 'Sign In') or contains(text(), 'Iniciar') or contains(@value, 'Login')]"
