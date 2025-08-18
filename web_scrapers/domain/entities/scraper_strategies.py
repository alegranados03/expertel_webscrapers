import os
import uuid
import zipfile
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
                "billing_cycle_file_id": file_info.billing_cycle_file.id if file_info.billing_cycle_file else None,
                "carrier_report_name": (
                    file_info.billing_cycle_file.carrier_report.name
                    if (file_info.billing_cycle_file and file_info.billing_cycle_file.carrier_report)
                    else None
                ),
                "daily_usage_file_id": file_info.daily_usage_file.id if file_info.daily_usage_file else None,
                "pdf_file_id": file_info.pdf_file.id if file_info.pdf_file else None,
            }
            for file_info in downloaded_files
        ]

    def _extract_zip_files(self, zip_file_path: str, extract_to_dir: Optional[str] = None) -> List[str]:
        """
        Extrae archivos de un ZIP y retorna las rutas de todos los archivos extraídos.

        Args:
            zip_file_path: Ruta del archivo ZIP a extraer
            extract_to_dir: Directorio donde extraer (si no se especifica, usa el directorio del ZIP)

        Returns:
            Lista de rutas de archivos extraídos
        """
        extracted_files = []
        try:
            # Verificar que el archivo existe y es un ZIP
            if not os.path.exists(zip_file_path):
                print(f"❌ Archivo ZIP no encontrado: {zip_file_path}")
                return extracted_files

            if not zipfile.is_zipfile(zip_file_path):
                print(f"❌ El archivo no es un ZIP válido: {zip_file_path}")
                return extracted_files

            # Determinar directorio de extracción con UUID único
            if extract_to_dir is None:
                zip_basename = os.path.splitext(os.path.basename(zip_file_path))[0]
                unique_id = str(uuid.uuid4())[:8]  # Usar solo primeros 8 caracteres del UUID
                extract_to_dir = os.path.join(os.path.dirname(zip_file_path), f"{zip_basename}_extracted_{unique_id}")

            # Crear directorio de extracción si no existe
            os.makedirs(extract_to_dir, exist_ok=True)

            print(f"📦 Extrayendo ZIP: {os.path.basename(zip_file_path)}")
            print(f"📁 Directorio de extracción: {extract_to_dir}")

            # Extraer archivos
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                file_list = zip_ref.namelist()
                print(f"📋 Elementos en ZIP: {len(file_list)}")

                for file_name in file_list:
                    # Solo procesar archivos, no directorios
                    if not file_name.endswith("/"):
                        # Obtener solo el nombre del archivo (sin ruta de carpetas)
                        base_filename = os.path.basename(file_name)

                        # Evitar archivos ocultos o del sistema
                        if base_filename and not base_filename.startswith("."):
                            # Leer el contenido del archivo del ZIP
                            file_content = zip_ref.read(file_name)

                            # Crear ruta de destino en el primer nivel
                            flattened_file_path = os.path.join(extract_to_dir, base_filename)

                            # Si ya existe un archivo con el mismo nombre, agregar un número
                            counter = 1
                            original_path = flattened_file_path
                            while os.path.exists(flattened_file_path):
                                name, ext = os.path.splitext(base_filename)
                                flattened_file_path = os.path.join(extract_to_dir, f"{name}_{counter}{ext}")
                                counter += 1

                            # Escribir el archivo al directorio de extracción (primer nivel)
                            with open(flattened_file_path, "wb") as output_file:
                                output_file.write(file_content)

                            extracted_files.append(flattened_file_path)

                            # Mostrar información de extracción
                            if file_name != base_filename:
                                print(f"   ✅ Extraído: {file_name} -> {base_filename}")
                            else:
                                print(f"   ✅ Extraído: {base_filename}")
                        else:
                            print(f"   ⏭️ Ignorado archivo del sistema: {file_name}")
                    else:
                        print(f"   📁 Ignorado directorio: {file_name}")

            # Resumen de extracción
            print(f"📊 RESUMEN DE EXTRACCIÓN:")
            print(f"   Total archivos extraídos: {len(extracted_files)}")

            if len(extracted_files) == 1:
                print(f"   📄 Archivo único: {os.path.basename(extracted_files[0])}")
            else:
                print(f"   📄 Múltiples archivos:")
                for i, file_path in enumerate(extracted_files, 1):
                    print(f"     [{i}] {os.path.basename(file_path)}")

            print(f"📦 ===============================")

            return extracted_files

        except Exception as e:
            print(f"❌ Error al extraer ZIP: {str(e)}")
            return extracted_files

    def _upload_files_to_endpoint(
        self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle
    ) -> bool:
        """Método base para enviar archivos al endpoint. Override si necesitas lógica específica."""
        try:
            from web_scrapers.infrastructure.services.file_upload_service import FileUploadService

            upload_service = FileUploadService()

            # Determinar tipo de upload basado en la clase
            upload_type = self._get_upload_type()

            return upload_service.upload_files_batch(
                files=files, billing_cycle=billing_cycle, upload_type=upload_type, additional_data=None
            )

        except Exception as e:
            print(f"❌ Error en upload de archivos: {str(e)}")
            return False

    def _get_upload_type(self) -> str:
        """Determina el tipo de upload basado en la clase de estrategia."""
        class_name = self.__class__.__name__.lower()
        if "monthly" in class_name:
            return "monthly"
        elif "daily" in class_name:
            return "daily_usage"
        elif "pdf" in class_name:
            return "pdf_invoice"
        else:
            return "unknown"


class MonthlyReportsScraperStrategy(ScraperBaseStrategy):

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
