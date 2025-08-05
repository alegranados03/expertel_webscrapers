import time
import os
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
        locator = self.page.locator(f"xpath={xpath}")
        locator.focus()
        locator.dispatch_event("keydown", {"key": text[0]})
        locator.dispatch_event("keyup", {"key": text[0]})
        self.page.fill(f"xpath={xpath}", text)

    def select_dropdown_option(self, xpath: str, option_text: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        options = self.page.locator(f"xpath={xpath} >> option").all()
        print("Available options in dropdown:")
        for option in options:
            text = option.inner_text()
            val = option.get_attribute("value")
            print(f"  Texto: {text} | Valor: {val}")
        self.page.select_option(f"xpath={xpath}", label=option_text)

    def select_dropdown_by_value(self, xpath: str, value: str, timeout: int = 10000) -> None:
        self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        options = self.page.locator(f"xpath={xpath} >> option").all()
        print("Available options in dropdown:")
        for option in options:
            text = option.inner_text()
            val = option.get_attribute("value")
            print(f"  Texto: {text} | Valor: {val}")
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

    def refresh(self) -> None:
        """Refresh the current page - alias for reload_page."""
        self.page.reload()

    def go_back(self) -> None:
        self.page.go_back()

    def go_forward(self) -> None:
        self.page.go_forward()

    def wait_for_new_tab(self, timeout: int = 10000) -> None:
        raise NotImplementedError
        # initial_tab_count = len(self.page.context.pages)
        # print(f"[DETECT] tabulada: {initial_tab_count}")
        # start_time = time.time()
        # while len(self.page.context.pages) <= initial_tab_count:
        #     if time.time() - start_time > timeout / 1000:
        #         raise TimeoutError(f"No se abrió una nueva pestaña en {timeout}ms")
        #     time.sleep(0.1)

    def switch_to_new_tab(self) -> None:
        pages = self.page.context.pages
        print("las pages", pages)
        for page in reversed(pages):
            print("page", page.url, "is_closed", page.is_closed())
            if not page.is_closed():
                self.page = page
                self.page.bring_to_front()
                return
        raise RuntimeError("No hay pestaña nueva disponible o todas están cerradas.")

    def close_current_tab(self) -> None:
        self.page.close()

        remaining_pages = [p for p in self.page.context.pages if not p.is_closed()]
        if remaining_pages:
            self.page = remaining_pages[-1]  # o la que necesites
            self.page.bring_to_front()
        else:
            raise RuntimeError("Todas las pestañas han sido cerradas.")

    def switch_to_previous_tab(self) -> None:
        pages = self.page.context.pages
        current_index = self.get_current_tab_index()
        previous_index = current_index - 1
        print("current_index:", current_index, "previous_index:", previous_index, "pages:", len(pages))
        if 0 <= previous_index < len(pages):
            page = pages[previous_index]
            if not page.is_closed():
                self.page = page
                self.page.bring_to_front()
                return
        raise RuntimeError("No se pudo cambiar a la pestaña anterior.")

    def switch_to_tab_by_index(self, index: int) -> None:
        pages = self.page.context.pages
        if 0 <= index < len(pages):
            page = pages[index]
            if not page.is_closed():
                self.page = page
                self.page.bring_to_front()
                return
            else:
                raise RuntimeError(f"La pestaña en el índice {index} está cerrada.")
        raise ValueError(f"Índice de pestaña {index} fuera de rango. Hay {len(pages)} pestañas disponibles.")

    def get_tab_count(self) -> int:
        return len(self.page.context.pages)

    def clear_browser_data(
        self, clear_cookies: bool = True, clear_storage: bool = True, clear_cache: bool = True
    ) -> None:
        try:
            context = self.page.context
            if clear_cookies:
                context.clear_cookies()
            if clear_storage or clear_cache:
                self.page.evaluate(
                    """
                    () => {
                        if (typeof(Storage) !== "undefined" && localStorage) {
                            localStorage.clear();
                        }
                        if (typeof(Storage) !== "undefined" && sessionStorage) {
                            sessionStorage.clear();
                        }
                    }
                """
                )
            print("🧹 Datos del navegador limpiados exitosamente")
        except Exception as e:
            print(f"⚠️ Error al limpiar datos del navegador: {e}")

    def close_all_tabs_except_main(self) -> None:
        try:
            pages = self.page.context.pages
            main_page = pages[0] if pages else None
            for i in range(len(pages) - 1, 0, -1):
                try:
                    pages[i].close()
                except:
                    pass
            if main_page and not main_page.is_closed():
                self.page = main_page
                self.page.bring_to_front()
                print(f"🗂️ Cerradas {len(pages) - 1} pestañas, regresado a pestaña principal")
            else:
                print("⚠️ No se pudo regresar a la pestaña principal")
        except Exception as e:
            print(f"❌ Error al cerrar pestañas: {e}")

    def get_current_tab_index(self) -> int:
        try:
            pages = self.page.context.pages
            for i, page in enumerate(pages):
                if page == self.page:
                    return i
            return -1
        except:
            return -1

    def change_button_attribute(self, xpath: str, attribute: str, value: str) -> None:
        """Cambia cualquier atributo de un botón usando JavaScript."""
        self.page.evaluate(
            f"""
            () => {{
                const el = document.evaluate("{xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (el) {{
                    el.setAttribute("{attribute}", "{value}");
                    if ("{attribute}" === "disabled" && "{value}" === "false") {{
                        el.disabled = false;
                    }}
                }}
            }}
        """
        )

    def expect_download_and_click(self, xpath: str, timeout: int = 30000) -> str | None:
        """Hace clic en un elemento esperando una descarga y retorna la ruta del archivo descargado."""
        try:
            with self.page.expect_download(timeout=timeout) as download_info:
                self.page.click(f"xpath={xpath}")

            download = download_info.value
            # Obtener el path sugerido del archivo
            suggested_filename = download.suggested_filename

            # Guardar el archivo en el directorio de descargas

            downloads_dir = os.path.abspath("downloads")
            os.makedirs(downloads_dir, exist_ok=True)
            file_path = os.path.join(downloads_dir, suggested_filename)

            download.save_as(file_path)
            print(f"📥 Archivo descargado: {file_path}")
            return file_path

        except Exception as e:
            print(f"❌ Error en descarga: {str(e)}")
            return None

    def click_and_switch_to_new_tab(self, xpath: str, timeout: int = 10000) -> None:
        """Hace clic en un enlace que abre una nueva pestaña y cambia el foco automáticamente."""
        with self.page.context.expect_page(timeout=timeout) as new_page_info:
            self.page.click(f"xpath={xpath}")

        print(self.page.context.pages)
        new_tab = new_page_info.value
        new_tab.bring_to_front()
        self.page = new_tab
        self.page.wait_for_load_state("load")
