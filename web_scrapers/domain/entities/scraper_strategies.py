from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import (
    BillingCycle,
    BillingCycleDailyUsageFile,
    BillingCycleFile,
    FileDownloadInfo,
    ScraperConfig,
)
from web_scrapers.domain.entities.session import Credentials


class ScraperResult:
    def __init__(
        self,
        success: bool,
        message: str = "",
        files: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.message = message
        self.files = files or []
        self.error = error
        self.timestamp = datetime.now()


class ScraperBaseStrategy(ABC):
    def __init__(self, browser_wrapper: BrowserWrapper):
        self.browser_wrapper = browser_wrapper

    @abstractmethod
    def execute(self, config: ScraperConfig, billing_cycle: BillingCycle, credentials: Credentials) -> ScraperResult:
        raise NotImplementedError()

    def _create_file_mapping(self, downloaded_files: List[FileDownloadInfo]) -> List[Dict[str, Any]]:
        """Convierte FileDownloadInfo a formato de mapeo requerido para endpoints."""
        return [
            {
                "file_id": file_info.file_id,
                "file_name": file_info.file_name,
                "file_path": file_info.file_path,
                "download_url": file_info.download_url,
                "download_timestamp": file_info.download_timestamp.isoformat(),
            }
            for file_info in downloaded_files
        ]


class MonthlyReportsScraperStrategy(ScraperBaseStrategy):

    def execute(self, config: ScraperConfig, billing_cycle: BillingCycle, credentials: Credentials) -> ScraperResult:
        try:
            files_section = self._find_files_section(config, billing_cycle)
            if not files_section:
                return ScraperResult(False, error="No se pudo encontrar la sección de archivos")

            downloaded_files = self._download_files(files_section, config, billing_cycle)
            if not downloaded_files:
                return ScraperResult(False, error="No se pudieron descargar los archivos")

            # upload_result = self._upload_files_to_endpoint(downloaded_files, config, billing_cycle)
            # if not upload_result:
            #     return ScraperResult(False, error="Error al enviar archivos al endpoint externo")

            return ScraperResult(
                True, f"Procesados {len(downloaded_files)} archivos", self._create_file_mapping(downloaded_files)
            )

        except Exception as e:
            return ScraperResult(False, error=str(e))

    @abstractmethod
    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        raise NotImplementedError()

    @abstractmethod
    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        raise NotImplementedError()

    @abstractmethod
    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        raise NotImplementedError()


class DailyUsageScraperStrategy(ScraperBaseStrategy):

    def execute(self, config: ScraperConfig, billing_cycle: BillingCycle, credentials: Credentials) -> ScraperResult:
        try:
            files_section = self._find_files_section(config, billing_cycle)
            if not files_section:
                return ScraperResult(False, error="No se pudo encontrar la sección de archivos")

            downloaded_files = self._download_files(files_section, config, billing_cycle)
            if not downloaded_files:
                return ScraperResult(False, error="No se pudieron descargar los archivos")

            upload_result = self._upload_files_to_endpoint(downloaded_files, config, billing_cycle)
            if not upload_result:
                return ScraperResult(False, error="Error al enviar archivos al endpoint externo")

            return ScraperResult(
                True, f"Procesados {len(downloaded_files)} archivos", self._create_file_mapping(downloaded_files)
            )

        except Exception as e:
            return ScraperResult(False, error=str(e))

    @abstractmethod
    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        raise NotImplementedError()

    @abstractmethod
    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        raise NotImplementedError()

    @abstractmethod
    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        raise NotImplementedError()


class PDFInvoiceScraperStrategy(ScraperBaseStrategy):

    def execute(self, config: ScraperConfig, billing_cycle: BillingCycle, credentials: Credentials) -> ScraperResult:
        try:
            files_section = self._find_files_section(config, billing_cycle)
            if not files_section:
                return ScraperResult(False, error="No se pudo encontrar la sección de archivos")

            downloaded_files = self._download_files(files_section, config, billing_cycle)
            if not downloaded_files:
                return ScraperResult(False, error="No se pudieron descargar los archivos")

            upload_result = self._upload_files_to_endpoint(downloaded_files, config, billing_cycle)
            if not upload_result:
                return ScraperResult(False, error="Error al enviar archivos al endpoint externo")

            return ScraperResult(
                True, f"Procesados {len(downloaded_files)} archivos", self._create_file_mapping(downloaded_files)
            )

        except Exception as e:
            return ScraperResult(False, error=str(e))

    @abstractmethod
    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        raise NotImplementedError()

    @abstractmethod
    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        raise NotImplementedError()

    @abstractmethod
    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        raise NotImplementedError()
