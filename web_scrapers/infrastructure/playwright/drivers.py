from playwright.sync_api._generated import Browser, Playwright as SyncPlaywright

from web_scrapers.domain.entities.ports import NavigatorDriverBuilder
from web_scrapers.domain.enums import Navigators


class BaseNavigatorDriverBuilder(NavigatorDriverBuilder):
    pw: SyncPlaywright | None = None

    def __init__(self, pw: SyncPlaywright) -> None:
        self.pw: SyncPlaywright = pw

    def set_driver_options(self, **kwargs) -> None:
        raise NotImplementedError

    def get_browser(self) -> Browser:
        raise NotImplementedError


class ChromeDriverBuilder(BaseNavigatorDriverBuilder):
    def __init__(self, pw: SyncPlaywright):
        super().__init__(pw)

    def set_driver_options(self, **kwargs):
        raise NotImplementedError

    def get_browser(self) -> Browser:
        return self.pw.chromium.launch(channel=Navigators.CHROME.value, headless=False, slow_mo=5000)


class EdgeDriverBuilder(BaseNavigatorDriverBuilder):

    def __init__(self, pw: SyncPlaywright):
        super().__init__(pw)

    def set_driver_options(self, **kwargs):
        raise NotImplementedError

    def get_browser(self) -> Browser:
        return self.pw.chromium.launch(channel=Navigators.EDGE.value, headless=False, slow_mo=5000)


class FirefoxDriverBuilder(BaseNavigatorDriverBuilder):

    def __init__(self, pw: SyncPlaywright):
        super().__init__(pw)

    def set_driver_options(self, **kwargs):
        raise NotImplementedError

    def get_browser(self) -> Browser:
        return self.pw.firefox.launch(channel=Navigators.FIREFOX.value, headless=False, slow_mo=5000)
