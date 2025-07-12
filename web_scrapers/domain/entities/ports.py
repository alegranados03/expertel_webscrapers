from abc import ABC, abstractmethod
from typing import Optional


class NavigatorDriverBuilder(ABC):
    @abstractmethod
    def set_driver_options(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_browser(self):
        raise NotImplementedError


class ContextManager(ABC):
    logged_in: bool = False

    @abstractmethod
    def get_credentials(self):
        raise NotImplementedError

    @abstractmethod
    def is_logged_in(self):
        raise NotImplementedError

    @abstractmethod
    def current_carrier(self):
        raise NotImplementedError

    @abstractmethod
    def set_credentials(self, credentials):
        raise NotImplementedError

    @abstractmethod
    def set_carrier(self, carrier):
        raise NotImplementedError

    @abstractmethod
    def get_carrier(self, carrier):
        raise NotImplementedError


class MonthlyReportsScraper(ABC):
    pass

class DailyUsagesScraper(ABC):
    pass

class PDFInvoiceScraper(ABC):
    pass

