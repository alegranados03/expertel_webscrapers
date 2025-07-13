import os
from typing import Any, Dict, Optional, Type

from playwright.sync_api import Browser, BrowserContext, Page, Playwright as SyncPlaywright, sync_playwright

from web_scrapers.domain.entities.ports import NavigatorDriverBuilder
from web_scrapers.domain.enums import Navigators
from web_scrapers.infrastructure.playwright.drivers import (
    ChromeDriverBuilder,
    EdgeDriverBuilder,
    FirefoxDriverBuilder,
    SafariDriverBuilder,
)


class BrowserDriverFactory:

    def __init__(self):
        self._driver_builders: Dict[Navigators, Type[NavigatorDriverBuilder]] = {
            Navigators.CHROME: ChromeDriverBuilder,
            Navigators.EDGE: EdgeDriverBuilder,
            Navigators.FIREFOX: FirefoxDriverBuilder,
            Navigators.SAFARI: SafariDriverBuilder,
        }
        self._playwright: Optional[SyncPlaywright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def get_default_browser_type(self) -> Navigators:
        browser_type: str = os.getenv("BROWSER_TYPE", "chrome").lower()
        try:
            return Navigators(browser_type)
        except ValueError:
            return Navigators.CHROME

    def get_browser_options(self) -> Dict[str, Any]:
        return {
            "headless": os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
            "slow_mo": int(os.getenv("BROWSER_SLOW_MO", "1000")),
            "timeout": int(os.getenv("BROWSER_TIMEOUT", "30000")),
            "viewport_width": int(os.getenv("BROWSER_VIEWPORT_WIDTH", "1920")),
            "viewport_height": int(os.getenv("BROWSER_VIEWPORT_HEIGHT", "1080")),
            "devtools": os.getenv("BROWSER_DEVTOOLS", "false").lower() == "true",
            "no_sandbox": os.getenv("BROWSER_NO_SANDBOX", "false").lower() == "true",
            "disable_web_security": os.getenv("BROWSER_DISABLE_WEB_SECURITY", "false").lower() == "true",
        }

    def create_browser(self, browser_type: Optional[Navigators] = None, **kwargs) -> Browser:
        if not browser_type:
            browser_type = self.get_default_browser_type()

        default_options = self.get_browser_options()
        default_options.update(kwargs)

        driver_class: Type[NavigatorDriverBuilder] = self._driver_builders.get(browser_type)
        if not driver_class:
            raise ValueError(f"Navegador no soportado: {browser_type}")

        if not self._playwright:
            self._playwright = sync_playwright().start()

        driver_builder = driver_class(self._playwright)
        driver_builder.set_driver_options(**default_options)
        self._browser = driver_builder.get_browser()
        return self._browser

    def create_context(self, browser: Optional[Browser] = None, **kwargs) -> BrowserContext:
        if not browser:
            browser = self.create_browser()

        context_options = {
            "viewport": {
                "width": int(os.getenv("BROWSER_VIEWPORT_WIDTH", "1920")),
                "height": int(os.getenv("BROWSER_VIEWPORT_HEIGHT", "1080")),
            },
            "user_agent": os.getenv("BROWSER_USER_AGENT", None),
            "locale": os.getenv("BROWSER_LOCALE", "en-US"),
            "timezone_id": os.getenv("BROWSER_TIMEZONE", "America/New_York"),
            "ignore_https_errors": os.getenv("BROWSER_IGNORE_HTTPS_ERRORS", "false").lower() == "true",
        }

        context_options = {k: v for k, v in context_options.items() if v is not None}
        context_options.update(kwargs)

        self._context = browser.new_context(**context_options)
        return self._context

    def create_page(self, context: Optional[BrowserContext] = None) -> Page:
        if not context:
            context = self.create_context()

        self._page = context.new_page()

        default_timeout = int(os.getenv("BROWSER_DEFAULT_TIMEOUT", "30000"))
        navigation_timeout = int(os.getenv("BROWSER_NAVIGATION_TIMEOUT", "30000"))

        self._page.set_default_timeout(default_timeout)
        self._page.set_default_navigation_timeout(navigation_timeout)

        return self._page

    def create_full_setup(self, browser_type: Optional[Navigators] = None, **kwargs) -> tuple[Browser, BrowserContext]:
        self.create_browser(browser_type)
        self.create_context()
        return self._browser, self._context

    def get_available_browsers(self) -> list[Navigators]:
        return list(self._driver_builders.keys())

    def is_browser_available(self, browser_type: Navigators) -> bool:
        return browser_type in self._driver_builders

    def cleanup(self) -> None:
        if self._page:
            self._page.close()
            self._page = None

        if self._context:
            self._context.close()
            self._context = None

        if self._browser:
            self._browser.close()
            self._browser = None

        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


class BrowserManager:

    _instance: Optional["BrowserManager"] = None
    _factory: Optional[BrowserDriverFactory] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._factory is None:
            self._factory = BrowserDriverFactory()

    @property
    def factory(self) -> BrowserDriverFactory:
        return self._factory

    def get_browser(self, browser_type: Optional[Navigators] = None) -> tuple[Browser, BrowserContext]:
        return self._factory.create_full_setup(browser_type)

    def cleanup_all(self) -> None:
        if self._factory:
            self._factory.cleanup()
            self._factory = None
        BrowserManager._instance = None
