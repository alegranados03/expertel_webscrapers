"""
Main ScraperJob processor with available_at support
"""

import os
import sys
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# Configure logging BEFORE Django setup and imports
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('main.log', mode='a')
    ]
)

import django

# Configure Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from web_scrapers.application.scraper_job_service import ScraperJobService
from web_scrapers.application.safe_scraper_job_service import SafeScraperJobService
from web_scrapers.application.session_manager import SessionManager
from web_scrapers.domain.entities.models import ScraperJobCompleteContext
from web_scrapers.domain.entities.scraper_factory import ScraperStrategyFactory
from web_scrapers.domain.entities.session import Carrier as CarrierEnum, Credentials
from web_scrapers.domain.enums import ScraperJobStatus, Navigators, ScraperType
from web_scrapers.infrastructure.logging_config import get_logger, setup_logging


class ScraperJobProcessor:
    """Main ScraperJob processor using clean architecture"""

    def __init__(self):
        self.logger = get_logger("scraper_job_processor")
        # Use SafeScraperJobService to handle async context after Playwright execution
        original_service = ScraperJobService()
        self.scraper_job_service = SafeScraperJobService(original_service)
        self.session_manager = SessionManager(browser_type=Navigators.CHROME)
        self.scraper_factory = ScraperStrategyFactory()

    def log_statistics(self) -> None:
        """Display available scraper statistics"""
        stats = self.scraper_job_service.get_scraper_statistics()
        self.logger.info(
            f"Scraper statistics: {stats.available_now} available now, "
            f"{stats.future_scheduled} scheduled for future, "
            f"{stats.total_pending} total pending"
        )

    def process_scraper_job(self, job_context: ScraperJobCompleteContext, job_number: int, total_jobs: int) -> bool:
        """
        Process a single scraper job.

        Args:
            job_context: Complete job context with Pydantic models
            job_number: Current job number
            total_jobs: Total jobs to process

        Returns:
            True if processing was successful, False otherwise
        """
        # Extract Pydantic entities from complete context model
        scraper_job = job_context.scraper_job
        scraper_config = job_context.scraper_config
        billing_cycle = job_context.billing_cycle  # Complete with files
        credential = job_context.credential
        account = job_context.account
        carrier = job_context.carrier

        self.logger.info(f"Processing job {job_number}/{total_jobs}")
        self.logger.info(f"Job ID: {scraper_job.id}")
        self.logger.info(f"Type: {scraper_job.type}")
        self.logger.info(f"Carrier: {carrier.name}")
        self.logger.info(f"Account: {account.number}")
        self.logger.info(f"Available at: {scraper_job.available_at}")

        try:
            # Update status to RUNNING
            self.scraper_job_service.update_scraper_job_status(
                scraper_job.id,
                ScraperJobStatus.RUNNING,
                f"Starting processing - Carrier: {carrier.name}, Type: {scraper_job.type}",
            )

            carrier_enum = CarrierEnum(carrier.name)
            credentials = Credentials(
                id=credential.id,
                username=credential.username,
                password=credential.get_decrypted_password(),
                carrier=carrier_enum,
            )

            scraper_type = ScraperType(scraper_job.type)

            # Intelligent session management and verification
            if self.session_manager.is_logged_in():
                current_carrier = self.session_manager.get_current_carrier()
                current_credentials = self.session_manager.get_current_credentials()
                self.logger.info(
                    f"Active session for {current_carrier.value if current_carrier else 'Unknown'} with user {current_credentials.username if current_credentials else 'N/A'}"
                )

                # Check if current session matches required credentials
                if (
                    current_carrier == credentials.carrier
                    and current_credentials
                    and current_credentials.id == credentials.id
                ):
                    self.logger.info("Using existing session - credentials match")
                    login_success = True
                else:
                    self.logger.info("Credentials differ from current session - logging out and re-authenticating")
                    self.session_manager.logout()
                    login_success = self.session_manager.login(credentials, scraper_type=scraper_type)
            else:
                self.logger.info("No active session - initiating login")
                login_success = self.session_manager.login(credentials, scraper_type=scraper_type)

            if not login_success:
                error_msg = "Authentication failed"
                if self.session_manager.has_error():
                    error_msg = f"Authentication failed: {self.session_manager.get_error_message()}"
                self.logger.error(error_msg)
                raise Exception(error_msg)

            self.logger.info("Authentication successful")

            # Get browser wrapper after successful authentication
            browser_wrapper = self.session_manager.get_browser_wrapper()
            if not browser_wrapper:
                raise Exception("Failed to get browser wrapper after successful authentication")

            # Create scraper using factory (like in example)
            scraper_strategy = self.scraper_factory.create_scraper(
                carrier=carrier_enum,
                scraper_type=scraper_job.type,
                browser_wrapper=browser_wrapper,
                job_id=scraper_job.id,
            )

            self.logger.info(f"Scraper created successfully: {scraper_strategy.__class__.__name__}")

            # Execute actual scraper with complete Pydantic structures
            result = scraper_strategy.execute(scraper_config, billing_cycle, credentials)

            if result.success:
                self.logger.info(f"Scraper executed successfully: {result.message}")
                self.logger.info(f"Files processed: {len(result.files)}")

                self.scraper_job_service.update_scraper_job_status(
                    scraper_job.id, ScraperJobStatus.SUCCESS, f"Scraper executed successfully: {result.message}"
                )
            else:
                self.logger.error(f"Scraper execution failed: {result.error}")
                self.scraper_job_service.update_scraper_job_status(
                    scraper_job.id, ScraperJobStatus.ERROR, f"Scraper execution failed: {result.error}"
                )
                return False

            return True

        except Exception as e:
            error_msg = f"Error processing scraper: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            # Update status to ERROR
            self.scraper_job_service.update_scraper_job_status(scraper_job.id, ScraperJobStatus.ERROR, error_msg)

            return False

    def execute_available_scrapers(self) -> None:
        """Main function that retrieves and executes available scrapers"""
        self.logger.info("Fetching available scraper jobs...")

        # Display statistics
        self.log_statistics()

        # Get available jobs with complete context (like scraper_system_example.py)
        available_jobs = self.scraper_job_service.get_available_jobs_with_complete_context()

        if not available_jobs:
            self.logger.info("No scraper jobs available for execution at this time")
            return

        self.logger.info(f"Found {len(available_jobs)} scraper jobs available for execution")

        # Process each job
        successful_jobs = 0
        failed_jobs = 0

        for i, job_context in enumerate(available_jobs, 1):
            success = self.process_scraper_job(job_context, i, len(available_jobs))
            if success:
                successful_jobs += 1
            else:
                failed_jobs += 1

        # Final summary
        self.logger.info("Execution summary:")
        self.logger.info(f"Successful: {successful_jobs}")
        self.logger.info(f"Failed: {failed_jobs}")
        self.logger.info(f"Total processed: {len(available_jobs)}")


def main():
    """Main processor function"""
    # Setup logging
    setup_logging(log_level="DEBUG")
    logger = get_logger("main")
    # logger.setLevel("DEBUG")

    try:
        logger.info("Starting ScraperJob processor")
        processor = ScraperJobProcessor()
        processor.execute_available_scrapers()
        logger.info("ScraperJob processor completed successfully")
    except Exception as e:
        logger.error(f"Error in main processor: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
