"""
Universal file upload service for external API.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests

from web_scrapers.domain.entities.models import BillingCycle, FileDownloadInfo


class FileUploadService:
    """Service for uploading files to external API."""

    def __init__(self):
        # Configuration from environment variables
        self.api_base_url = os.getenv("EIQ_BACKEND_API_BASE_URL", "https://api.expertel.com")
        self.api_key = os.getenv("EIQ_BACKEND_API_KEY", "")
        self.logger = logging.getLogger(self.__class__.__name__)

        if not self.api_key:
            self.logger.warning("EIQ_BACKEND_API_KEY not configured in environment variables")

    def _get_headers(self, billing_cycle: BillingCycle) -> Dict[str, str]:
        """Gets headers for requests including client and workspace IDs."""
        headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json",
        }

        # Get client_id and workspace_id from billing_cycle relationships
        if billing_cycle.account and billing_cycle.account.workspace:
            headers["x-workspace-id"] = str(billing_cycle.account.workspace.id)
            if billing_cycle.account.workspace.client:
                headers["x-client-id"] = str(billing_cycle.account.workspace.client.id)

        return headers

    def _get_upload_config(
        self, upload_type: str, file_info: FileDownloadInfo, billing_cycle: BillingCycle
    ) -> Optional[Dict[str, Any]]:
        """Gets specific configuration for each upload type."""
        cycle_id = billing_cycle.id

        configs = {
            "monthly": {
                "url_template": f"{self.api_base_url}/api/v1/accounts/billing-cycles/{cycle_id}/files/{{file_id}}/upload-file/",
                "file_id_attr": "billing_cycle_file",
                "content_type": "application/octet-stream",
                "description": "monthly report",
            },
            "daily_usage": {
                "url_template": f"{self.api_base_url}/api/v1/accounts/billing-cycles/{cycle_id}/daily-usage/",
                "file_id_attr": "daily_usage_file",
                "content_type": "application/octet-stream",
                "description": "daily usage",
            },
            "pdf_invoice": {
                "url_template": f"{self.api_base_url}/api/v1/accounts/billing-cycles/{cycle_id}/pdf-invoice/",
                "file_id_attr": "pdf_file",
                "content_type": "application/pdf",
                "description": "PDF invoice",
            },
        }

        return configs.get(upload_type)

    def _upload_single_file(self, file_info: FileDownloadInfo, billing_cycle: BillingCycle, upload_type: str) -> bool:
        """Unified method for uploading a file to the corresponding endpoint."""
        try:
            # Get specific configuration for upload type
            config = self._get_upload_config(upload_type, file_info, billing_cycle)
            if not config:
                self.logger.error(f"Unknown upload type: {upload_type}")
                return False

            # Verify file has corresponding mapping
            file_obj = getattr(file_info, config["file_id_attr"], None)
            if not file_obj:
                self.logger.error(f"No {config['file_id_attr']} mapping for {file_info.file_name}")
                return False

            # Build URL
            if "{file_id}" in config["url_template"]:
                url = config["url_template"].format(file_id=file_obj.id)
            else:
                url = config["url_template"]

            self.logger.info(f"Uploading {config['description']} file: {file_info.file_name}")
            self.logger.debug(f"Upload URL: {url}")

            # Prepare and upload file
            with open(file_info.file_path, "rb") as file:
                files = {"file": (file_info.file_name, file, config["content_type"])}

                response = requests.post(
                    url=url,
                    headers=self._get_headers(billing_cycle),
                    data={},  # Empty payload, only send file
                    files=files,
                    timeout=300,
                )

            # Verify response
            if response.status_code in [200, 201]:
                self.logger.info(f"File {file_info.file_name} uploaded successfully")
                return True
            else:
                self.logger.error(f"Error uploading {file_info.file_name}: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Error uploading {upload_type} file {file_info.file_name}: {str(e)}")
            return False

    def upload_files_batch(
        self,
        files: List[FileDownloadInfo],
        billing_cycle: BillingCycle,
        upload_type: str,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Uploads multiple files one by one according to type.

        Args:
            files: List of files to upload
            billing_cycle: Billing cycle
            upload_type: Upload type ('monthly', 'daily_usage', 'pdf_invoice')
            additional_data: Additional data (unused, kept for compatibility)
        """
        success_count = 0
        total_files = len(files)

        self.logger.info(f"Uploading {total_files} file(s) of type: {upload_type}")

        for i, file_info in enumerate(files, 1):
            self.logger.info(f"Processing file {i}/{total_files}: {file_info.file_name}")

            if self._upload_single_file(file_info, billing_cycle, upload_type):
                success_count += 1

        self.logger.info(f"UPLOAD SUMMARY:")
        self.logger.info(f"   Successful: {success_count}/{total_files}")
        self.logger.info(f"   Failed: {total_files - success_count}/{total_files}")

        return success_count == total_files
