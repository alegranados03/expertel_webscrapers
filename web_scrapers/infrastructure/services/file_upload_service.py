"""
Servicio universal para upload de archivos a la API externa.
"""
import os
import requests
from typing import Dict, Any, Optional, List
from web_scrapers.domain.entities.models import FileDownloadInfo, BillingCycle


class FileUploadService:
    """Servicio para enviar archivos a la API externa."""
    
    def __init__(self):
        # Configuración desde variables de entorno
        self.api_base_url = os.getenv('API_BASE_URL', 'https://api.expertel.com')
        self.api_token = os.getenv('API_TOKEN', '')
        
        if not self.api_token:
            print("⚠️ API_TOKEN no configurado en variables de entorno")
    
    def _get_headers(self) -> Dict[str, str]:
        """Obtiene headers base para las requests."""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Accept': 'application/json'
        }
    
    def _get_upload_config(self, upload_type: str, file_info: FileDownloadInfo, billing_cycle: BillingCycle) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración específica para cada tipo de upload."""
        cycle_id = billing_cycle.id
        
        configs = {
            'monthly': {
                'url_template': f"{self.api_base_url}/api/v1/accounts/billing-cycles/{cycle_id}/files/{{file_id}}/upload-file/",
                'file_id_attr': 'billing_cycle_file',
                'content_type': 'application/octet-stream',
                'description': 'reporte mensual'
            },
            'daily_usage': {
                'url_template': f"{self.api_base_url}/api/v1/accounts/billing-cycles/{cycle_id}/daily-usage/",
                'file_id_attr': 'daily_usage_file',
                'content_type': 'application/octet-stream',
                'description': 'uso diario'
            },
            'pdf_invoice': {
                'url_template': f"{self.api_base_url}/api/v1/accounts/billing-cycles/{cycle_id}/pdf-invoice/",
                'file_id_attr': 'pdf_file',
                'content_type': 'application/pdf',
                'description': 'PDF factura'
            }
        }
        
        return configs.get(upload_type)
    
    def _upload_single_file(
        self, 
        file_info: FileDownloadInfo, 
        billing_cycle: BillingCycle, 
        upload_type: str
    ) -> bool:
        """Método unificado para enviar un archivo al endpoint correspondiente."""
        try:
            # Obtener configuración específica del tipo de upload
            config = self._get_upload_config(upload_type, file_info, billing_cycle)
            if not config:
                print(f"❌ Tipo de upload desconocido: {upload_type}")
                return False
            
            # Verificar que el archivo tenga el mapeo correspondiente
            file_obj = getattr(file_info, config['file_id_attr'], None)
            if not file_obj:
                print(f"❌ No hay {config['file_id_attr']} mapeado para {file_info.file_name}")
                return False
            
            # Construir URL
            if '{file_id}' in config['url_template']:
                url = config['url_template'].format(file_id=file_obj.id)
            else:
                url = config['url_template']
            
            print(f"📤 Enviando archivo {config['description']}: {file_info.file_name}")
            print(f"🔗 URL: {url}")
            
            # Preparar y enviar archivo
            with open(file_info.file_path, 'rb') as file:
                files = {'file': (file_info.file_name, file, config['content_type'])}
                
                response = requests.post(
                    url=url,
                    headers=self._get_headers(),
                    data={},  # Payload vacío, solo enviamos el archivo
                    files=files,
                    timeout=300
                )
            
            # Verificar respuesta
            if response.status_code in [200, 201]:
                print(f"✅ Archivo {file_info.file_name} enviado exitosamente")
                return True
            else:
                print(f"❌ Error al enviar {file_info.file_name}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error al enviar archivo {upload_type} {file_info.file_name}: {str(e)}")
            return False
    
    def upload_files_batch(
        self, 
        files: List[FileDownloadInfo], 
        billing_cycle: BillingCycle,
        upload_type: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envía múltiples archivos uno por uno según el tipo.
        
        Args:
            files: Lista de archivos a enviar
            billing_cycle: Ciclo de facturación
            upload_type: Tipo de upload ('monthly', 'daily_usage', 'pdf_invoice')
            additional_data: Datos adicionales (no usado, mantenido para compatibilidad)
        """
        success_count = 0
        total_files = len(files)
        
        print(f"📤 Enviando {total_files} archivo(s) de tipo: {upload_type}")
        
        for i, file_info in enumerate(files, 1):
            print(f"📁 Archivo {i}/{total_files}: {file_info.file_name}")
            
            if self._upload_single_file(file_info, billing_cycle, upload_type):
                success_count += 1
        
        print(f"📊 RESUMEN DE ENVÍO:")
        print(f"   ✅ Exitosos: {success_count}/{total_files}")
        print(f"   ❌ Fallidos: {total_files - success_count}/{total_files}")
        
        return success_count == total_files