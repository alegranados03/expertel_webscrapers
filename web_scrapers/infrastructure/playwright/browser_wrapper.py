from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper


class PlaywrightWrapper(BrowserWrapper):

    def __init__(self, page: Page):
        self.page = page

    def goto(self, url: str, wait_until: str = "load") -> None:
        self.page.goto(url, wait_until=wait_until)

    def find_element_by_xpath(self, xpath: str, timeout: int = 10000) -> bool:
        try:
            self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    def click_element(self, xpath: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        self.page.click(f"xpath={xpath}")

    def type_text(self, xpath: str, text: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        self.page.type(f"xpath={xpath}", text)

    def clear_and_type(self, xpath: str, text: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        self.page.fill(f"xpath={xpath}", text)

    def select_dropdown_option(self, xpath: str, option_text: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        self.page.select_option(f"xpath={xpath}", label=option_text)

    def select_dropdown_by_value(self, xpath: str, value: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        self.page.select_option(f"xpath={xpath}", value=value)

    def get_text(self, xpath: str, timeout: int = 10000) -> str:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        return self.page.text_content(f"xpath={xpath}") or ""

    def get_attribute(self, xpath: str, attribute: str, timeout: int = 10000) -> str:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        return self.page.get_attribute(f"xpath={xpath}", attribute) or ""

    def wait_for_element(self, xpath: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)

    def wait_for_page_load(self, timeout: int = 30000) -> None:
        self.page.wait_for_load_state("networkidle", timeout=timeout)

    def is_element_visible(self, xpath: str, timeout: int = 5000) -> bool:
        try:
            self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
            return self.page.is_visible(f"xpath={xpath}")
        except PlaywrightTimeoutError:
            return False

    def get_current_url(self) -> str:
        return self.page.url

    def take_screenshot(self, path: str) -> None:
        self.page.screenshot(path=path)

    def wait_for_navigation(self, timeout: int = 30000) -> None:
        self.page.wait_for_load_state("networkidle", timeout=timeout)

    def press_key(self, xpath: str, key: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        self.page.press(f"xpath={xpath}", key)

    def hover_element(self, xpath: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        self.page.hover(f"xpath={xpath}")

    def scroll_to_element(self, xpath: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        self.page.locator(f"xpath={xpath}").scroll_into_view_if_needed()

    def get_page_title(self) -> str:
        return self.page.title()

    def reload_page(self) -> None:
        self.page.reload()

    def go_back(self) -> None:
        self.page.go_back()

    def go_forward(self) -> None:
        self.page.go_forward()
