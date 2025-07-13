from web_scrapers.domain.entities.auth_strategies import AuthBaseStrategy
from web_scrapers.domain.entities.session import Credentials
from web_scrapers.domain.enums import CarrierPortalUrls
from web_scrapers.infrastructure.playwright.browser_wrapper import BrowserWrapper


class BellAuthStrategy(AuthBaseStrategy):

    def login(self, credentials: Credentials) -> bool:
        return self._perform_generic_login(credentials)

    def logout(self) -> bool:
        return self._perform_generic_logout()

    def is_logged_in(self) -> bool:
        return self.browser_wrapper.is_element_visible(self.get_logout_xpath(), timeout=3000)

    def get_login_url(self) -> str:
        return CarrierPortalUrls.BELL.value

    def get_logout_xpath(self) -> str:
        return "//a[contains(@href, 'logout') or contains(text(), 'Logout') or contains(text(), 'Sign Out') or contains(text(), 'Cerrar Sesión')]"

    def get_username_xpath(self) -> str:
        return "//input[@type='text' and (@name='username' or @name='email' or @id='username' or @id='email' or @name='user')]"

    def get_password_xpath(self) -> str:
        return "//input[@type='password' and (@name='password' or @id='password' or @name='pass')]"

    def get_login_button_xpath(self) -> str:
        return "//button[@type='submit' or contains(text(), 'Login') or contains(text(), 'Sign In') or contains(text(), 'Iniciar') or contains(@value, 'Login')]"


class TelusAuthStrategy(AuthBaseStrategy):

    def login(self, credentials: Credentials) -> bool:
        return self._perform_generic_login(credentials)

    def logout(self) -> bool:
        return self._perform_generic_logout()

    def is_logged_in(self) -> bool:
        return self.browser_wrapper.is_element_visible(self.get_logout_xpath(), timeout=3000)

    def get_login_url(self) -> str:
        return CarrierPortalUrls.TELUS.value

    def get_logout_xpath(self) -> str:
        return "//a[contains(@href, 'logout') or contains(text(), 'Logout') or contains(text(), 'Sign Out') or contains(text(), 'Cerrar Sesión')]"

    def get_username_xpath(self) -> str:
        return "//input[@type='text' and (@name='username' or @name='email' or @id='username' or @id='email' or @name='user')]"

    def get_password_xpath(self) -> str:
        return "//input[@type='password' and (@name='password' or @id='password' or @name='pass')]"

    def get_login_button_xpath(self) -> str:
        return "//button[@type='submit' or contains(text(), 'Login') or contains(text(), 'Sign In') or contains(text(), 'Iniciar') or contains(@value, 'Login')]"


class RogersAuthStrategy(AuthBaseStrategy):

    def login(self, credentials: Credentials) -> bool:
        return self._perform_generic_login(credentials)

    def logout(self) -> bool:
        return self._perform_generic_logout()

    def is_logged_in(self) -> bool:
        return self.browser_wrapper.is_element_visible(self.get_logout_xpath(), timeout=3000)

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
        return self.browser_wrapper.is_element_visible(self.get_logout_xpath(), timeout=3000)

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
        return self.browser_wrapper.is_element_visible(self.get_logout_xpath(), timeout=3000)

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
        return self.browser_wrapper.is_element_visible(self.get_logout_xpath(), timeout=3000)

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
