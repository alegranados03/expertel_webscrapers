import logging
import os
import re
import shutil
import time
import zipfile
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from web_scrapers.domain.entities.browser_wrapper import BrowserWrapper
from web_scrapers.domain.entities.models import BillingCycle, BillingCycleFile, ScraperConfig
from web_scrapers.domain.entities.scraper_strategies import (
    FileDownloadInfo,
    MonthlyReportsScraperStrategy,
)
from web_scrapers.domain.enums import RogersFileSlug

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Report configurations: (category_text, report_type_text, slug)
# Note: BCR (Hardware Upgrade Eligibility Report) is handled separately via My Requests tab
ROGERS_REPORTS_CONFIG: List[Tuple[str, str, str]] = [
    ("Cost Centre Detail", "Monthly Charges Breakdown", RogersFileSlug.MONTHLY_CHARGES_BREAKDOWN.value),
    ("Cost Centre Detail", "Monthly Usage Breakdown", RogersFileSlug.MONTHLY_USAGE_BREAKDOWN.value),
    ("Current Charges and Credits", "Current Charges - Subscriber Level", RogersFileSlug.CURRENT_CHARGES_SUBSCRIBER.value),
    ("Current Charges and Credits", "Credit - Subscriber Level", RogersFileSlug.CREDITS_SUBSCRIBER.value),
]

# BCR report configuration (handled via My Requests flow)
BCR_REPORT_CATEGORY = "Wireless Eligibility Check"
BCR_REPORT_TYPE = "Hardware Upgrade Eligibility Report"
BCR_WAIT_TIME_SECONDS = 600  # 10 minutes


class RogersMonthlyReportsScraperStrategy(MonthlyReportsScraperStrategy):
    """Scraper de reportes mensuales para Rogers.

    Downloads 5 files:
    - CCD_MONTHLY: Cost Centre Detail / Monthly Charges Breakdown
    - DATA: Cost Centre Detail / Monthly Usage Breakdown
    - CCC_CHG: Current Charges and Credits / Current Charges - Subscriber Level
    - CCC_CRE: Current Charges and Credits / Credit - Subscriber Level
    - BCR: Hardware Upgrade Eligibility Report (via My Requests tab, ZIP processing)

    Special BCR flow:
    - If all 4 non-BCR files already have s3_key, skip directly to BCR download
    - BCR is obtained via "Wireless Eligibility Check" > "Hardware Upgrade Eligibility Report"
    - Goes to My Requests tab to find existing completed reports
    - If pending, waits 10 minutes and checks again
    - If not found, generates new report, waits 10 minutes, then downloads
    - Downloads ZIP, extracts TXT (headers) + Excel (data), combines into final XLSX
    """

    def __init__(self, browser_wrapper: BrowserWrapper, job_id: int):
        super().__init__(browser_wrapper, job_id=job_id)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _find_files_section(self, config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]:
        """Navega a la seccion de reportes de Rogers."""
        try:
            self.logger.info("Navigating to Rogers reports section...")

            # Click on Reports in the header menu
            reports_link_xpath = '//*[@id="header_menu"]/table/tbody/tr[2]/td/table/tbody/tr/td[3]/a'
            self.logger.info("Clicking on Reports link...")

            if self.browser_wrapper.is_element_visible(reports_link_xpath, timeout=10000):
                self.browser_wrapper.click_element(reports_link_xpath)
                time.sleep(3)
            else:
                self.logger.error("Reports link not found")
                return None

            self.logger.info("Navigation completed - ready for file download")
            return {"section": "monthly_reports", "ready_for_download": True}

        except Exception as e:
            self.logger.error(f"Error navigating to monthly reports: {str(e)}")
            return None

    def _download_files(
        self, files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle
    ) -> List[FileDownloadInfo]:
        """Descarga los archivos de reportes mensuales de Rogers."""
        downloaded_files = []

        # Map BillingCycleFiles by slug
        billing_cycle_file_map: Dict[str, BillingCycleFile] = {}
        if billing_cycle.billing_cycle_files:
            for bcf in billing_cycle.billing_cycle_files:
                if bcf.carrier_report and bcf.carrier_report.slug:
                    billing_cycle_file_map[bcf.carrier_report.slug] = bcf
                    self.logger.info(f"Mapping BillingCycleFile ID {bcf.id} -> Slug: '{bcf.carrier_report.slug}'")

        try:
            account_number = billing_cycle.account.number

            # Check if all 4 non-BCR files already have s3_key
            non_bcr_slugs = [
                RogersFileSlug.MONTHLY_CHARGES_BREAKDOWN.value,
                RogersFileSlug.MONTHLY_USAGE_BREAKDOWN.value,
                RogersFileSlug.CURRENT_CHARGES_SUBSCRIBER.value,
                RogersFileSlug.CREDITS_SUBSCRIBER.value,
            ]
            all_non_bcr_have_s3_key = self._check_all_files_have_s3_key(billing_cycle_file_map, non_bcr_slugs)

            if all_non_bcr_have_s3_key:
                self.logger.info("=== ALL 4 NON-BCR FILES ALREADY HAVE S3_KEY - SKIPPING TO BCR ===")
                # Go directly to BCR download
                bcr_file_info = self._download_bcr_report(
                    account_number=account_number,
                    billing_cycle=billing_cycle,
                    file_map=billing_cycle_file_map,
                    only_bcr_mode=True,
                )
                if bcr_file_info:
                    downloaded_files.append(bcr_file_info)
                    self.logger.info("BCR report downloaded successfully")
                else:
                    self.logger.warning("4 Files already loaded Hardware Upgrade Eligibility Report still not available")

                self._reset_to_main_screen()
                return downloaded_files

            # Download the 4 regular reports
            total_reports = len(ROGERS_REPORTS_CONFIG)
            for idx, (category_text, report_type_text, slug) in enumerate(ROGERS_REPORTS_CONFIG, 1):
                self.logger.info(f"=== DOWNLOADING REPORT {idx}/{total_reports}: {slug} ===")
                self.logger.info(f"Category: {category_text}")
                self.logger.info(f"Report Type: {report_type_text}")

                file_info = self._download_single_report(
                    category_text=category_text,
                    report_type_text=report_type_text,
                    slug=slug,
                    account_number=account_number,
                    billing_cycle=billing_cycle,
                    file_map=billing_cycle_file_map,
                )

                if file_info:
                    downloaded_files.append(file_info)
                    self.logger.info(f"Report {slug} downloaded successfully")
                else:
                    self.logger.error(f"Failed to download report {slug}")

                # Navigate back to reports section for next iteration
                if idx < len(ROGERS_REPORTS_CONFIG):
                    self.logger.info("Navigating back to reports section for next report...")
                    self._navigate_to_reports_section()

            # Now download BCR report via My Requests flow
            self.logger.info("=== DOWNLOADING BCR REPORT (Hardware Upgrade Eligibility Report) ===")
            self._navigate_to_reports_section()

            bcr_file_info = self._download_bcr_report(
                account_number=account_number,
                billing_cycle=billing_cycle,
                file_map=billing_cycle_file_map,
                only_bcr_mode=False,
            )
            if bcr_file_info:
                downloaded_files.append(bcr_file_info)
                self.logger.info("BCR report downloaded successfully")
            else:
                self.logger.warning("BCR report (Hardware Upgrade Eligibility Report) not available")

            # Reset to main screen after all downloads
            self._reset_to_main_screen()

            self.logger.info(f"TOTAL DOWNLOAD COMPLETED: {len(downloaded_files)} files")
            return downloaded_files

        except Exception as e:
            self.logger.error(f"Error downloading files: {str(e)}")
            try:
                self._reset_to_main_screen()
            except:
                pass
            return downloaded_files

    def _check_all_files_have_s3_key(
        self, file_map: Dict[str, BillingCycleFile], slugs: List[str]
    ) -> bool:
        """Check if all files for the given slugs have s3_key assigned."""
        for slug in slugs:
            bcf = file_map.get(slug)
            if not bcf or not bcf.s3_key:
                self.logger.info(f"File with slug '{slug}' does not have s3_key")
                return False
            self.logger.info(f"File with slug '{slug}' has s3_key: {bcf.s3_key}")
        return True

    def _download_single_report(
        self,
        category_text: str,
        report_type_text: str,
        slug: str,
        account_number: str,
        billing_cycle: BillingCycle,
        file_map: Dict[str, BillingCycleFile],
    ) -> Optional[FileDownloadInfo]:
        """Downloads a single report from Rogers portal."""
        try:
            # Step 1: Select category dropdown
            self.logger.info(f"Selecting category: {category_text}")
            if not self._select_category_dropdown(category_text):
                self.logger.error(f"Failed to select category: {category_text}")
                return None
            time.sleep(2)

            # Step 2: Select report type dropdown
            self.logger.info(f"Selecting report type: {report_type_text}")
            if not self._select_report_type_dropdown(report_type_text):
                self.logger.error(f"Failed to select report type: {report_type_text}")
                return None
            time.sleep(2)

            # Step 3: Select account number via iframe
            self.logger.info(f"Selecting account number: {account_number}")
            if not self._select_account_number_via_iframe(account_number):
                self.logger.error(f"Failed to select account number: {account_number}")
                return None
            time.sleep(2)

            # Step 4: Click Run Report button
            self.logger.info("Clicking Run Report...")
            if not self._click_run_report():
                self.logger.error("Failed to click Run Report")
                return None
            time.sleep(5)

            # Step 5: Change bill cycle date via iframe
            self.logger.info("Changing bill cycle date...")
            if not self._change_bill_cycle_date(billing_cycle.end_date):
                self.logger.error(f"Could not change bill cycle date to {billing_cycle.end_date}, aborting report download")
                return None
            time.sleep(2)

            # Step 6: Apply date filter
            self.logger.info("Applying date filter...")
            self._click_go_button()
            time.sleep(5)

            # Step 7: Download as Text with Double Quote qualifier
            self.logger.info("Downloading report as Text...")
            file_path = self._download_as_text()

            if file_path:
                actual_filename = os.path.basename(file_path)
                self.logger.info(f"Report downloaded: {actual_filename}")

                corresponding_bcf = file_map.get(slug)

                file_info = FileDownloadInfo(
                    file_id=corresponding_bcf.id if corresponding_bcf else 0,
                    file_name=actual_filename,
                    download_url="N/A",
                    file_path=file_path,
                    billing_cycle_file=corresponding_bcf,
                )

                if corresponding_bcf:
                    self.logger.info(f"MAPPING CONFIRMED: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id}")

                return file_info

            self.logger.error(f"Could not download report: {slug}")
            return None

        except Exception as e:
            self.logger.error(f"Error downloading report {slug}: {str(e)}")
            return None

    def _select_category_dropdown(self, category_text: str) -> bool:
        """Selects an option from the category dropdown."""
        try:
            category_dropdown_xpath = '//*[@id="categIDSelect"]'

            if self.browser_wrapper.is_element_visible(category_dropdown_xpath, timeout=10000):
                # Use select_dropdown_option to select by visible text (partial match)
                self.browser_wrapper.page.wait_for_selector(f"xpath={category_dropdown_xpath}", timeout=10000)

                # Get all options and find the one containing the text
                options = self.browser_wrapper.page.locator(f"xpath={category_dropdown_xpath}//option").all()
                for option in options:
                    option_text = option.text_content()
                    if option_text and category_text.lower() in option_text.lower():
                        option_value = option.get_attribute("value")
                        self.browser_wrapper.select_dropdown_by_value(category_dropdown_xpath, option_value)
                        self.logger.info(f"Selected category: {option_text}")
                        return True

                self.logger.error(f"Category option not found: {category_text}")
                return False
            else:
                self.logger.error("Category dropdown not found")
                return False

        except Exception as e:
            self.logger.error(f"Error selecting category dropdown: {str(e)}")
            return False

    def _select_report_type_dropdown(self, report_type_text: str) -> bool:
        """Selects an option from the report type dropdown."""
        try:
            report_dropdown_xpath = '//*[@id="reportIDSelect"]'

            if self.browser_wrapper.is_element_visible(report_dropdown_xpath, timeout=10000):
                # Get all options and find the one containing the text
                options = self.browser_wrapper.page.locator(f"xpath={report_dropdown_xpath}//option").all()
                for option in options:
                    option_text = option.text_content()
                    if option_text and report_type_text.lower() in option_text.lower():
                        option_value = option.get_attribute("value")
                        self.browser_wrapper.select_dropdown_by_value(report_dropdown_xpath, option_value)
                        self.logger.info(f"Selected report type: {option_text}")
                        return True

                self.logger.error(f"Report type option not found: {report_type_text}")
                return False
            else:
                self.logger.error("Report type dropdown not found")
                return False

        except Exception as e:
            self.logger.error(f"Error selecting report type dropdown: {str(e)}")
            return False

    def _select_account_number_via_iframe(self, account_number: str) -> bool:
        """Opens account number iframe and selects the account."""
        iframe_selector = '#TB_iframeContent'
        page = self.browser_wrapper.page

        # Normalizar número de cuenta: remover guiones para búsqueda
        # Ejemplo: "8-7424-0153" -> "874240153"
        account_number_normalized = account_number.replace("-", "")
        self.logger.info(f"Account number normalized: '{account_number}' -> '{account_number_normalized}'")

        try:
            # Click on Account Numbers link to open iframe
            account_numbers_link_xpath = '//*[@id="accountNumbersLink"]'
            self.logger.info("Clicking Account Numbers link...")

            if not self.browser_wrapper.is_element_visible(account_numbers_link_xpath, timeout=5000):
                self.logger.error("Account Numbers link not found")
                return False

            self.browser_wrapper.click_element(account_numbers_link_xpath)
            time.sleep(3)

            self.logger.info("Switching to iframe context...")
            iframe_locator = page.locator(iframe_selector)

            if iframe_locator.count() == 0:
                self.logger.error("Iframe not found")
                return False

            frame = page.frame_locator(iframe_selector)

            # Click on radio button to enable search
            radio_button_xpath = '//*[@id="searchBox1"]/div[1]/div[1]/input'
            self.logger.info("Clicking search radio button...")
            radio_button = frame.locator(f"xpath={radio_button_xpath}")
            if radio_button.count() > 0:
                radio_button.click()
                time.sleep(1)
            else:
                self.logger.error("Search radio button not found in iframe")
                self._close_iframe_modal()
                return False

            # Enter account number (normalized, without hyphens) using keyboard.type() to trigger input events
            search_field_xpath = '//*[@id="searchField1"]'
            self.logger.info(f"Entering account number: {account_number_normalized}")
            search_field = frame.locator(f"xpath={search_field_xpath}")
            if search_field.count() > 0:
                search_field.click()
                time.sleep(0.3)
                search_field.fill("")  # Clear first
                search_field.type(account_number_normalized, delay=50)  # Type character by character
                time.sleep(0.5)
                # Trigger blur to activate Find button
                search_field.blur()
                time.sleep(1)
            else:
                self.logger.error("Search field not found in iframe")
                self._close_iframe_modal()
                return False

            # Click find button
            find_button_xpath = '//*[@id="findButton1"]'
            self.logger.info("Clicking Find button...")
            find_button = frame.locator(f"xpath={find_button_xpath}")
            if find_button.count() > 0:
                find_button.click()
                time.sleep(3)
            else:
                self.logger.error("Find button not found in iframe")
                self._close_iframe_modal()
                return False

            # Find and click the Select button for the account
            self.logger.info("Looking for account in results list...")

            # Find the list item containing the account number and click Select
            # The structure is: li > span.rowCTN > strong with account number, and span > a with "Select"
            # Use normalized account number for search (portal may display with or without hyphens)
            select_button = frame.locator(f"//li[.//strong[contains(text(), '{account_number_normalized}')]]//a[contains(@class, 'buttongray')]")

            if select_button.count() > 0:
                self.logger.info(f"Found account {account_number_normalized}, clicking Select...")
                select_button.click()
                time.sleep(2)
            else:
                # Try with original account number (with hyphens)
                select_button_original = frame.locator(f"//li[.//strong[contains(text(), '{account_number}')]]//a[contains(@class, 'buttongray')]")
                if select_button_original.count() > 0:
                    self.logger.info(f"Found account {account_number}, clicking Select...")
                    select_button_original.click()
                    time.sleep(2)
                else:
                    # Try alternative: click on any Select button if account is in the list
                    self.logger.info("Trying alternative selector for Select button...")
                    select_button_alt = frame.locator("//a[.//span[text()='Select']]")
                    if select_button_alt.count() > 0:
                        select_button_alt.first.click()
                        time.sleep(2)
                    else:
                        self.logger.error("Select button not found in iframe")
                        self._close_iframe_modal()
                        return False

            self.logger.info("Account number selected successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error selecting account number via iframe: {str(e)}")
            self._close_iframe_modal()
            return False

    def _close_iframe_modal(self) -> None:
        """Closes the iframe modal/overlay if it's open."""
        try:
            self.logger.info("Attempting to close iframe modal...")
            page = self.browser_wrapper.page

            # Try clicking the close button (TB_closeWindowButton is common for ThickBox modals)
            close_button_selectors = [
                '#TB_closeWindowButton',
                '.TB_closeWindowButton',
                '#TB_closeAjaxWindow',
                '//a[@id="TB_closeWindowButton"]',
                '//div[@id="TB_closeWindowButton"]',
            ]

            for selector in close_button_selectors:
                try:
                    if selector.startswith('//'):
                        locator = page.locator(f"xpath={selector}")
                    else:
                        locator = page.locator(selector)

                    if locator.count() > 0 and locator.is_visible():
                        locator.click()
                        time.sleep(1)
                        self.logger.info(f"Modal closed using selector: {selector}")
                        return
                except Exception:
                    continue

            # Fallback: try pressing Escape key
            self.logger.info("Trying Escape key to close modal...")
            page.keyboard.press("Escape")
            time.sleep(1)

        except Exception as e:
            self.logger.warning(f"Could not close modal: {str(e)}")

    def _click_run_report(self) -> bool:
        """Clicks the Run Report button."""
        try:
            run_report_xpath = '//*[@id="submitbutton"]'

            if self.browser_wrapper.is_element_visible(run_report_xpath, timeout=10000):
                self.browser_wrapper.click_element(run_report_xpath)
                self.logger.info("Run Report clicked, waiting for redirect...")
                time.sleep(5)
                return True
            else:
                self.logger.error("Run Report button not found")
                return False

        except Exception as e:
            self.logger.error(f"Error clicking Run Report: {str(e)}")
            return False

    def _change_bill_cycle_date(self, end_date: date) -> bool:
        """Opens bill cycle date iframe and selects the appropriate date."""
        try:
            # Click on Change Bill Cycle Date link
            change_date_xpath = '//*[@id="changeBillCycleDate"]'
            self.logger.info("Clicking Change Bill Cycle Date...")

            if not self.browser_wrapper.is_element_visible(change_date_xpath, timeout=10000):
                self.logger.warning("Change Bill Cycle Date link not found")
                return False

            self.browser_wrapper.click_element(change_date_xpath)
            time.sleep(3)

            # Switch to iframe
            iframe_selector = '#TB_iframeContent'
            page = self.browser_wrapper.page

            self.logger.info("Switching to date selection iframe...")
            iframe_locator = page.locator(iframe_selector)

            if iframe_locator.count() == 0:
                self.logger.warning("Date iframe not found")
                return False

            frame = page.frame_locator(iframe_selector)

            # Format target date: we need to find input with value matching month/year
            # The format in the value is "MM/DD/YYYY" like "07/08/2024"
            # But we need to match by month and year from billing_cycle.end_date
            target_month = end_date.month
            target_year = end_date.year

            self.logger.info(f"Looking for billing cycle date with month={target_month}, year={target_year}")

            # Find all radio buttons with billCycleDate name
            radio_buttons = frame.locator("//input[@name='billCycleDate']")
            count = radio_buttons.count()
            self.logger.info(f"Found {count} billing cycle date options")

            for i in range(count):
                radio = radio_buttons.nth(i)
                value = radio.get_attribute("value")

                if value:
                    # Parse value format: MM/DD/YYYY
                    try:
                        parts = value.split("/")
                        if len(parts) == 3:
                            month = int(parts[0])
                            year = int(parts[2])

                            if month == target_month and year == target_year:
                                self.logger.info(f"Found matching date: {value}")
                                radio.click()
                                time.sleep(1)

                                # Click submit button to confirm
                                submit_xpath = '//*[@id="submitNewBCD"]'
                                submit_button = frame.locator(f"xpath={submit_xpath}")
                                if submit_button.count() > 0:
                                    submit_button.click()
                                    time.sleep(2)
                                    self.logger.info("Bill cycle date changed successfully")
                                    return True

                    except (ValueError, IndexError):
                        continue

            self.logger.warning(f"No matching date found for month={target_month}, year={target_year}")
            # Close iframe without changes if no match found
            return False

        except Exception as e:
            self.logger.error(f"Error changing bill cycle date: {str(e)}")
            return False

    def _click_go_button(self) -> bool:
        """Clicks the Go button to apply date filter."""
        try:
            go_button_xpath = '//*[@id="goButton"]'

            if self.browser_wrapper.is_element_visible(go_button_xpath, timeout=5000):
                self.browser_wrapper.click_element(go_button_xpath)
                self.logger.info("Go button clicked")
                return True
            else:
                self.logger.warning("Go button not found")
                return False

        except Exception as e:
            self.logger.error(f"Error clicking Go button: {str(e)}")
            return False

    def _download_as_text(self) -> Optional[str]:
        """Downloads the report as Text file with Double Quote qualifier."""
        try:
            # Find and click the Text button in the export options div
            export_div_xpath = (
                "/html/body/div[1]/div[2]/table/tbody/tr/td/table/tbody/tr[3]/td/table/"
                "tbody/tr[7]/td/div[2]/div[2]/div"
            )

            self.logger.info("Looking for Text export button...")

            if self.browser_wrapper.is_element_visible(export_div_xpath, timeout=10000):
                # Find the Text button within the div
                text_button_xpath = f"{export_div_xpath}//a[contains(@class, 'buttontext') and contains(@href, 'exportText')]"

                if self.browser_wrapper.is_element_visible(text_button_xpath, timeout=5000):
                    self.logger.info("Clicking Text export button...")
                    self.browser_wrapper.click_element(text_button_xpath)
                    time.sleep(3)
                else:
                    # Try alternative: find by class and onclick
                    alt_text_xpath = "//a[@class='buttontext' and contains(@href, 'javascript:exportText')]"
                    if self.browser_wrapper.is_element_visible(alt_text_xpath, timeout=5000):
                        self.browser_wrapper.click_element(alt_text_xpath)
                        time.sleep(3)
                    else:
                        self.logger.error("Text button not found")
                        return None
            else:
                self.logger.error("Export options div not found")
                return None

            # Handle download options iframe
            iframe_selector = '#TB_iframeContent'
            page = self.browser_wrapper.page

            self.logger.info("Switching to download options iframe...")
            iframe_locator = page.locator(iframe_selector)

            if iframe_locator.count() == 0:
                self.logger.error("Download options iframe not found")
                return None

            frame = page.frame_locator(iframe_selector)

            # Select Double Quote radio button
            self.logger.info("Selecting Double Quote qualifier...")
            double_quote_xpath = "//input[@name='qualifier' and @value='D']"
            double_quote_radio = frame.locator(f"xpath={double_quote_xpath}")

            if double_quote_radio.count() > 0:
                double_quote_radio.click()
                time.sleep(1)
                self.logger.info("Double Quote selected")
            else:
                self.logger.warning("Double Quote radio button not found")

            # Click Download Now button and expect download
            download_now_xpath = '//*[@id="downloadNow"]'
            download_button = frame.locator(f"xpath={download_now_xpath}")

            if download_button.count() > 0:
                self.logger.info("Clicking Download Now...")

                # We need to handle the download from within the frame
                # First, get the main page to set up download handler
                with page.expect_download(timeout=60000) as download_info:
                    download_button.click()

                download = download_info.value
                suggested_filename = download.suggested_filename

                os.makedirs(self.job_downloads_dir, exist_ok=True)
                file_path = os.path.join(self.job_downloads_dir, suggested_filename)

                download.save_as(file_path)
                self.logger.info(f"File downloaded: {file_path}")
                time.sleep(2)

                return file_path
            else:
                self.logger.error("Download Now button not found")
                return None

        except Exception as e:
            self.logger.error(f"Error downloading as text: {str(e)}")
            return None

    def _navigate_to_reports_section(self):
        """Navigates back to the reports section."""
        try:
            reports_link_xpath = '//*[@id="header_menu"]/table/tbody/tr[2]/td/table/tbody/tr/td[3]/a'
            self.logger.info("Navigating back to reports section...")

            if self.browser_wrapper.is_element_visible(reports_link_xpath, timeout=10000):
                self.browser_wrapper.click_element(reports_link_xpath)
                time.sleep(3)

        except Exception as e:
            self.logger.error(f"Error navigating to reports section: {str(e)}")

    def _reset_to_main_screen(self):
        """Reset a la pantalla inicial de Rogers."""
        try:
            self.logger.info("Resetting to Rogers main screen...")
            self.browser_wrapper.goto("https://bss.rogers.com/bizonline/homePage.do")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            self.logger.info("Reset completed")
        except Exception as e:
            self.logger.error(f"Error resetting to main screen: {str(e)}")

    # ==================== BCR REPORT METHODS (Hardware Upgrade Eligibility Report) ====================

    def _download_bcr_report(
        self,
        account_number: str,
        billing_cycle: BillingCycle,
        file_map: Dict[str, BillingCycleFile],
        only_bcr_mode: bool = False,
    ) -> Optional[FileDownloadInfo]:
        """Downloads the BCR report (Hardware Upgrade Eligibility Report) via My Requests flow.

        Flow:
        1. Select category "Wireless Eligibility Check" and report type "Hardware Upgrade Eligibility Report"
        2. Go to My Requests tab
        3. Search for a valid report (Completed, not expired, matching account)
        4. If found: download it
        5. If Pending: wait 10 min, refresh, check again
        6. If not found: generate new report, wait 10 min, then try to download
        """
        try:
            self.logger.info("=== STARTING BCR REPORT DOWNLOAD FLOW ===")

            # Step 1: Select category and report type
            self.logger.info(f"Selecting category: {BCR_REPORT_CATEGORY}")
            if not self._select_category_dropdown(BCR_REPORT_CATEGORY):
                self.logger.error(f"Failed to select category: {BCR_REPORT_CATEGORY}")
                return None
            time.sleep(2)

            self.logger.info(f"Selecting report type: {BCR_REPORT_TYPE}")
            if not self._select_report_type_dropdown(BCR_REPORT_TYPE):
                self.logger.error(f"Failed to select report type: {BCR_REPORT_TYPE}")
                return None
            time.sleep(2)

            # Step 2: Go to My Requests tab
            if not self._navigate_to_my_requests_tab():
                self.logger.error("Failed to navigate to My Requests tab")
                return None

            # Step 3: Search for valid report in the list
            report_status = self._search_valid_bcr_report(account_number)

            if report_status["status"] == "completed":
                # Found a valid completed report - download it
                self.logger.info("Found valid completed BCR report, downloading...")
                return self._download_bcr_from_link(
                    report_status["download_element"],
                    billing_cycle,
                    file_map,
                )

            elif report_status["status"] == "pending":
                # Report is pending - wait and check again
                self.logger.info("BCR report is pending, waiting 10 minutes...")
                time.sleep(BCR_WAIT_TIME_SECONDS)

                # Refresh and check again
                self._refresh_reports_page()
                if not self._navigate_to_my_requests_tab():
                    return None

                report_status = self._search_valid_bcr_report(account_number)
                if report_status["status"] == "completed":
                    self.logger.info("BCR report completed after waiting, downloading...")
                    return self._download_bcr_from_link(
                        report_status["download_element"],
                        billing_cycle,
                        file_map,
                    )
                else:
                    self.logger.warning("BCR report still not completed after waiting")
                    return None

            else:
                # No valid report found - generate new one
                self.logger.info("No valid BCR report found, generating new one...")

                # Need to go back to report config to select account and run report
                self._navigate_to_reports_section()
                time.sleep(2)

                # Re-select category and report type
                if not self._select_category_dropdown(BCR_REPORT_CATEGORY):
                    return None
                time.sleep(2)

                if not self._select_report_type_dropdown(BCR_REPORT_TYPE):
                    return None
                time.sleep(2)

                # Generate new report
                if not self._generate_new_bcr_report(account_number):
                    self.logger.error("Failed to generate new BCR report")
                    return None

                # Wait 10 minutes for report to generate
                self.logger.info("Waiting 10 minutes for BCR report to generate...")
                time.sleep(BCR_WAIT_TIME_SECONDS)

                # Refresh and check for the report
                self._refresh_reports_page()

                # Re-select category and report type, then go to My Requests
                if not self._select_category_dropdown(BCR_REPORT_CATEGORY):
                    return None
                time.sleep(2)

                if not self._select_report_type_dropdown(BCR_REPORT_TYPE):
                    return None
                time.sleep(2)

                if not self._navigate_to_my_requests_tab():
                    return None

                report_status = self._search_valid_bcr_report(account_number)
                if report_status["status"] == "completed":
                    self.logger.info("BCR report generated and completed, downloading...")
                    return self._download_bcr_from_link(
                        report_status["download_element"],
                        billing_cycle,
                        file_map,
                    )
                else:
                    self.logger.warning("BCR report not completed after generation and waiting")
                    return None

        except Exception as e:
            self.logger.error(f"Error downloading BCR report: {str(e)}")
            return None

    def _navigate_to_my_requests_tab(self) -> bool:
        """Navigates to the My Requests tab."""
        try:
            self.logger.info("Clicking on My Requests tab...")
            my_requests_tab_xpath = '//*[@id="myRequests-tab"]'

            if not self.browser_wrapper.is_element_visible(my_requests_tab_xpath, timeout=10000):
                self.logger.error("My Requests tab not found")
                return False

            self.browser_wrapper.click_element(my_requests_tab_xpath)
            time.sleep(3)
            self.logger.info("Navigated to My Requests tab")
            return True

        except Exception as e:
            self.logger.error(f"Error navigating to My Requests tab: {str(e)}")
            return False

    def _search_valid_bcr_report(self, account_number: str) -> Dict[str, Any]:
        """Searches for a valid BCR report in the My Requests list.

        Returns a dict with:
        - status: "completed", "pending", or "not_found"
        - download_element: the element to click for download (if completed)
        """
        try:
            self.logger.info(f"Searching for valid BCR report for account: {account_number}")
            page = self.browser_wrapper.page

            # Wait for the list container to be visible
            list_container_xpath = '//*[@id="myRequests"]/div[2]'
            if not self.browser_wrapper.is_element_visible(list_container_xpath, timeout=10000):
                self.logger.warning("My Requests list container not found")
                return {"status": "not_found", "download_element": None}

            # Get all list items
            list_items = page.locator(f"xpath={list_container_xpath}//ol[@class='fav_items']//li")
            count = list_items.count()
            self.logger.info(f"Found {count} items in My Requests list")

            today = date.today()
            pending_found = False

            for i in range(count):
                try:
                    item = list_items.nth(i)

                    # Check if this is a Hardware Upgrade Eligibility Report
                    report_name_div = item.locator("xpath=.//div[@class='row_name' and text()='Report name:']/following-sibling::div[@class='row_value']")
                    if report_name_div.count() == 0:
                        continue

                    report_name = (report_name_div.first.text_content() or "").strip()
                    if "Hardware Upgrade Eligibility Report" not in report_name:
                        continue

                    self.logger.info(f"Found Hardware Upgrade Eligibility Report at index {i}")

                    # Check Show for (account number)
                    show_for_div = item.locator("xpath=.//div[@class='row_name' and text()='Show for:']/following-sibling::div[@class='row_value']")
                    if show_for_div.count() > 0:
                        show_for_text = (show_for_div.first.text_content() or "").strip()
                        # Normalize: extract digits only for comparison
                        show_for_digits = re.sub(r"[^0-9]", "", show_for_text)
                        account_digits = re.sub(r"[^0-9]", "", account_number)

                        if account_digits not in show_for_digits:
                            self.logger.info(f"Account mismatch: '{show_for_text}' does not contain '{account_number}'")
                            continue

                        self.logger.info(f"Account match: '{show_for_text}' contains '{account_number}'")

                    # Check Status
                    status_div = item.locator("xpath=.//div[@class='row_name' and text()='Status:']/following-sibling::div[@class='row_value']")
                    if status_div.count() == 0:
                        continue

                    status_text = (status_div.first.text_content() or "").strip()
                    self.logger.info(f"Report status: '{status_text}'")

                    if "Pending" in status_text:
                        pending_found = True
                        continue

                    if "Completed" not in status_text:
                        continue

                    # Check Expiry Date
                    expiry_div = item.locator("xpath=.//div[@class='row_name' and text()='Expiry Date:']/following-sibling::div[@class='row_value']")
                    if expiry_div.count() > 0:
                        expiry_text = (expiry_div.first.text_content() or "").strip()
                        if expiry_text:
                            try:
                                # Parse date in MM/DD/YYYY format
                                expiry_date = datetime.strptime(expiry_text, "%m/%d/%Y").date()
                                if expiry_date < today:
                                    self.logger.info(f"Report expired: {expiry_text}")
                                    continue
                                self.logger.info(f"Report not expired: {expiry_text}")
                            except ValueError:
                                self.logger.warning(f"Could not parse expiry date: {expiry_text}")

                    # Check for download link (the date should be a hyperlink)
                    download_link = item.locator("xpath=.//h3//a[contains(@href, 'downloadExtractFile')]")
                    if download_link.count() == 0:
                        self.logger.info("No download link found for this report")
                        continue

                    self.logger.info("Found valid completed BCR report with download link")
                    return {"status": "completed", "download_element": download_link.first}

                except Exception as item_error:
                    self.logger.warning(f"Error processing list item {i}: {str(item_error)}")
                    continue

            if pending_found:
                return {"status": "pending", "download_element": None}

            return {"status": "not_found", "download_element": None}

        except Exception as e:
            self.logger.error(f"Error searching for BCR report: {str(e)}")
            return {"status": "not_found", "download_element": None}

    def _generate_new_bcr_report(self, account_number: str) -> bool:
        """Generates a new BCR report by selecting account and clicking Run Report."""
        try:
            self.logger.info("Generating new BCR report...")

            # Select account number via iframe
            self.logger.info(f"Selecting account number: {account_number}")
            if not self._select_account_number_via_iframe(account_number):
                self.logger.error(f"Failed to select account number: {account_number}")
                return False
            time.sleep(2)

            # Click Run Report button
            self.logger.info("Clicking Run Report...")
            if not self._click_run_report():
                self.logger.error("Failed to click Run Report")
                return False
            time.sleep(3)

            # Close the modal that appears
            self._close_bcr_report_modal()
            time.sleep(2)

            self.logger.info("New BCR report generation initiated")
            return True

        except Exception as e:
            self.logger.error(f"Error generating new BCR report: {str(e)}")
            return False

    def _close_bcr_report_modal(self) -> None:
        """Closes the modal that appears after clicking Run Report for BCR."""
        try:
            self.logger.info("Attempting to close BCR report modal...")
            page = self.browser_wrapper.page

            # The modal is inside an iframe, try to close it
            iframe_selector = '#TB_iframeContent'
            iframe_locator = page.locator(iframe_selector)

            if iframe_locator.count() > 0:
                # Try to click close button inside iframe
                frame = page.frame_locator(iframe_selector)
                close_button = frame.locator("xpath=//*[@id='TB_closeWindowButton']")

                if close_button.count() > 0:
                    close_button.click()
                    time.sleep(1)
                    self.logger.info("Modal closed via iframe close button")
                    return

            # Try clicking close button in main page (outside iframe)
            close_selectors = [
                '//*[@id="TB_closeWindowButton"]',
                '//a[@id="TB_closeWindowButton"]',
                '#TB_closeWindowButton',
            ]

            for selector in close_selectors:
                try:
                    if selector.startswith('//') or selector.startswith('/'):
                        locator = page.locator(f"xpath={selector}")
                    else:
                        locator = page.locator(selector)

                    if locator.count() > 0 and locator.is_visible():
                        locator.click()
                        time.sleep(1)
                        self.logger.info(f"Modal closed using selector: {selector}")
                        return
                except Exception:
                    continue

            # Fallback: try pressing Escape key
            self.logger.info("Trying Escape key to close modal...")
            page.keyboard.press("Escape")
            time.sleep(1)

        except Exception as e:
            self.logger.warning(f"Could not close BCR modal: {str(e)}")

    def _download_bcr_from_link(
        self,
        download_element: Any,
        billing_cycle: BillingCycle,
        file_map: Dict[str, BillingCycleFile],
    ) -> Optional[FileDownloadInfo]:
        """Downloads the BCR report by clicking the download link and processing the ZIP."""
        try:
            self.logger.info("Downloading BCR report from link...")
            page = self.browser_wrapper.page

            # Click the download link and expect download
            with page.expect_download(timeout=120000) as download_info:
                download_element.click()

            download = download_info.value
            suggested_filename = download.suggested_filename

            os.makedirs(self.job_downloads_dir, exist_ok=True)
            zip_file_path = os.path.join(self.job_downloads_dir, suggested_filename)

            download.save_as(zip_file_path)
            self.logger.info(f"BCR ZIP downloaded: {zip_file_path}")
            time.sleep(2)

            # Process the ZIP file to create the final XLSX
            final_xlsx_path = self._process_bcr_zip(zip_file_path)

            if not final_xlsx_path:
                self.logger.error("Failed to process BCR ZIP file")
                return None

            actual_filename = os.path.basename(final_xlsx_path)
            corresponding_bcf = file_map.get(RogersFileSlug.BALANCE_REMAINING.value)

            file_info = FileDownloadInfo(
                file_id=corresponding_bcf.id if corresponding_bcf else 0,
                file_name=actual_filename,
                download_url="N/A",
                file_path=final_xlsx_path,
                billing_cycle_file=corresponding_bcf,
            )

            if corresponding_bcf:
                self.logger.info(f"MAPPING CONFIRMED: {actual_filename} -> BillingCycleFile ID {corresponding_bcf.id}")

            return file_info

        except Exception as e:
            self.logger.error(f"Error downloading BCR from link: {str(e)}")
            return None

    def _process_bcr_zip(self, zip_file_path: str) -> Optional[str]:
        """Processes the BCR ZIP file: extracts TXT headers and CSV data, combines into new XLSX.

        The ZIP contains:
        - Header-Wireless.txt: Line 1 = metadata (e.g. "Custom Type : 11/24/2025 - 12/23/2025"),
          Line 2 = empty, Lines 3+ = "HeaderName,width,type" (e.g. "Billing Account,9,Text")
        - Wireless.csv: Comma-separated data rows without headers

        Returns the path to the generated XLSX file.
        """
        try:
            self.logger.info(f"Processing BCR ZIP file: {zip_file_path}")

            # Create extraction directory
            extract_dir = os.path.join(self.job_downloads_dir, "bcr_extract")
            os.makedirs(extract_dir, exist_ok=True)

            # Extract ZIP
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find TXT (headers) and CSV (data) files
            txt_file = None
            csv_file = None

            for filename in os.listdir(extract_dir):
                file_path = os.path.join(extract_dir, filename)
                if filename.lower().endswith('.txt'):
                    txt_file = file_path
                    self.logger.info(f"Found TXT file: {filename}")
                elif filename.lower().endswith('.csv'):
                    csv_file = file_path
                    self.logger.info(f"Found CSV file: {filename}")

            if not txt_file or not csv_file:
                self.logger.error(f"Could not find both TXT and CSV files in ZIP. TXT: {txt_file}, CSV: {csv_file}")
                return None

            # Read headers from TXT file
            # Format: Line 1 = metadata (skip), Line 2 = empty (skip),
            # Lines 3+ = "HeaderName,width,type" → extract only HeaderName
            headers = []
            with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line in lines[2:]:  # Skip first 2 lines (metadata + empty)
                    line = line.strip()
                    if line:
                        # Extract header name (part before first comma)
                        header_name = line.split(',')[0].strip()
                        if header_name:
                            headers.append(header_name)

            self.logger.info(f"Headers from TXT ({len(headers)}): {headers}")

            # Read data from CSV file (no headers)
            df = pd.read_csv(csv_file, header=None, dtype=str)
            self.logger.info(f"Read {len(df)} rows from CSV")

            # Assign headers to dataframe
            if len(headers) == len(df.columns):
                df.columns = headers
            else:
                self.logger.warning(f"Header count ({len(headers)}) doesn't match column count ({len(df.columns)})")
                df.columns = headers[:len(df.columns)] if len(headers) > len(df.columns) else headers + [f"Column_{i}" for i in range(len(headers), len(df.columns))]

            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"rogers_bcr_hardware_upgrade_{timestamp}.xlsx"
            output_path = os.path.join(self.job_downloads_dir, output_filename)

            # Save to XLSX
            df.to_excel(output_path, index=False, engine='openpyxl')
            self.logger.info(f"BCR XLSX generated: {output_path}")

            # Cleanup: remove extracted files and original ZIP
            try:
                shutil.rmtree(extract_dir)
                os.remove(zip_file_path)
                self.logger.info("Cleaned up temporary files")
            except Exception as cleanup_error:
                self.logger.warning(f"Could not cleanup temp files: {str(cleanup_error)}")

            return output_path

        except Exception as e:
            self.logger.error(f"Error processing BCR ZIP: {str(e)}")
            return None

    def _refresh_reports_page(self) -> None:
        """Refreshes the reports page."""
        try:
            self.logger.info("Refreshing reports page...")
            self.browser_wrapper.goto("https://bss.rogers.com/bizonline/prm-reports.do")
            self.browser_wrapper.wait_for_page_load()
            time.sleep(3)
            self.logger.info("Reports page refreshed")
        except Exception as e:
            self.logger.error(f"Error refreshing reports page: {str(e)}")