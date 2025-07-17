from abc import ABC, abstractmethod
from typing import Any, List, Optional


class BrowserWrapper(ABC):
    # CURRENT SCRAPER NAVIGATOR (PAGE)

    @abstractmethod
    def goto(self, url: str, wait_until: str = "load") -> None:
        """Navega a una URL específica."""
        raise NotImplementedError()

    @abstractmethod
    def find_element_by_xpath(self, xpath: str, timeout: int = 10000) -> bool:
        """Encuentra un elemento por XPath."""
        raise NotImplementedError()

    @abstractmethod
    def click_element(self, xpath: str, timeout: int = 10000) -> None:
        """Hace clic en un elemento identificado por XPath."""
        raise NotImplementedError()

    @abstractmethod
    def type_text(self, xpath: str, text: str, timeout: int = 10000) -> None:
        """Escribe texto en un campo identificado por XPath."""
        raise NotImplementedError()

    @abstractmethod
    def clear_and_type(self, xpath: str, text: str, timeout: int = 10000) -> None:
        """Limpia un campo y escribe texto nuevo."""
        raise NotImplementedError()

    @abstractmethod
    def select_dropdown_option(self, xpath: str, option_text: str, timeout: int = 10000) -> None:
        """Selecciona una opción de un dropdown por texto."""
        raise NotImplementedError()

    @abstractmethod
    def select_dropdown_by_value(self, xpath: str, value: str, timeout: int = 10000) -> None:
        """Selecciona una opción de un dropdown por valor."""
        raise NotImplementedError()

    @abstractmethod
    def get_text(self, xpath: str, timeout: int = 10000) -> str:
        """Obtiene el texto de un elemento."""
        raise NotImplementedError()

    @abstractmethod
    def get_attribute(self, xpath: str, attribute: str, timeout: int = 10000) -> str:
        """Obtiene un atributo de un elemento."""
        raise NotImplementedError()

    @abstractmethod
    def wait_for_element(self, xpath: str, timeout: int = 10000) -> None:
        """Espera a que un elemento esté visible."""
        raise NotImplementedError()

    @abstractmethod
    def wait_for_page_load(self, timeout: int = 30000) -> None:
        """Espera a que la página cargue completamente."""
        raise NotImplementedError()

    @abstractmethod
    def is_element_visible(self, xpath: str, timeout: int = 5000) -> bool:
        """Verifica si un elemento está visible."""
        raise NotImplementedError()

    @abstractmethod
    def get_current_url(self) -> str:
        """Obtiene la URL actual."""
        raise NotImplementedError()

    @abstractmethod
    def take_screenshot(self, path: str) -> None:
        """Toma una captura de pantalla."""
        raise NotImplementedError()

    @abstractmethod
    def wait_for_navigation(self, timeout: int = 30000) -> None:
        """Espera a que la navegación se complete."""
        raise NotImplementedError()

    @abstractmethod
    def press_key(self, xpath: str, key: str, timeout: int = 10000) -> None:
        """Presiona una tecla en un elemento específico."""
        raise NotImplementedError()

    @abstractmethod
    def hover_element(self, xpath: str, timeout: int = 10000) -> None:
        """Hace hover sobre un elemento."""
        raise NotImplementedError()

    @abstractmethod
    def scroll_to_element(self, xpath: str, timeout: int = 10000) -> None:
        """Hace scroll hasta un elemento específico."""
        raise NotImplementedError()

    @abstractmethod
    def get_page_title(self) -> str:
        """Obtiene el título de la página actual."""
        raise NotImplementedError()

    @abstractmethod
    def reload_page(self) -> None:
        """Recarga la página actual."""
        raise NotImplementedError()

    @abstractmethod
    def go_back(self) -> None:
        """Navega hacia atrás en el historial."""
        raise NotImplementedError()

    @abstractmethod
    def go_forward(self) -> None:
        """Navega hacia adelante en el historial."""
        raise NotImplementedError()
