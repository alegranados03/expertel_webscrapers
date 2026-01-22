"""
ScraperJobService - Service for managing ScraperJobs with available_at support
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import Case, Q, Value, When
from django.utils import timezone

from web_scrapers.domain.entities.models import (
    Account,
    BillingCycle,
    BillingCycleDailyUsageFile,
    BillingCycleFile,
    BillingCyclePDFFile,
    Carrier,
    CarrierPortalCredential,
    CarrierReport,
    Client,
    ScraperConfig,
    ScraperJob,
    ScraperJobCompleteContext,
    ScraperStatistics,
    Workspace,
)
from web_scrapers.domain.enums import FileStatus, ScraperJobStatus
from web_scrapers.infrastructure.django.models import ScraperJob as DjangoScraperJob
from web_scrapers.infrastructure.django.repositories import (
    AccountRepository,
    BillingCycleDailyUsageFileRepository,
    BillingCycleFileRepository,
    BillingCyclePDFFileRepository,
    BillingCycleRepository,
    CarrierPortalCredentialRepository,
    CarrierReportRepository,
    CarrierRepository,
    ClientRepository,
    ScraperConfigRepository,
    ScraperJobRepository,
    WorkspaceRepository,
)


class ScraperJobService:
    """Service for managing ScraperJobs with intelligent fetch based on available_at"""

    def __init__(self):
        # Initialize all repositories needed to build complete structures
        self.scraper_job_repo = ScraperJobRepository()
        self.scraper_config_repo = ScraperConfigRepository()
        self.billing_cycle_repo = BillingCycleRepository()
        self.credential_repo = CarrierPortalCredentialRepository()
        self.account_repo = AccountRepository()
        self.carrier_repo = CarrierRepository()
        self.workspace_repo = WorkspaceRepository()
        self.client_repo = ClientRepository()
        self.billing_cycle_file_repo = BillingCycleFileRepository()
        self.daily_usage_file_repo = BillingCycleDailyUsageFileRepository()
        self.pdf_file_repo = BillingCyclePDFFileRepository()
        self.carrier_report_repo = CarrierReportRepository()

    def get_available_scraper_jobs(self, include_null_available_at: bool = True) -> List[ScraperJob]:
        """
        Get and claim scraper jobs for execution, limited to a single scraper_config.

        This method:
        1. Finds the first PENDING job
        2. Gets all PENDING jobs with the same scraper_config
        3. Marks them as IN_PROGRESS atomically
        4. Returns those jobs (main.py will mark them as RUNNING when executing)

        Args:
            include_null_available_at: Whether to include jobs with available_at=NULL for compatibility

        Returns:
            List of ScraperJob Pydantic entities for execution (from single scraper_config)
        """
        current_time = timezone.now()

        # Build base query filter for PENDING jobs
        query_filter = Q(status=ScraperJobStatus.PENDING)

        if include_null_available_at:
            query_filter &= Q(available_at__lte=current_time) | Q(available_at__isnull=True)
        else:
            query_filter &= Q(available_at__lte=current_time)

        # Custom ordering for scraper type: monthly_reports -> daily_usage -> pdf_invoice
        type_order = Case(
            When(type="monthly_reports", then=Value(1)),
            When(type="daily_usage", then=Value(2)),
            When(type="pdf_invoice", then=Value(3)),
            default=Value(99),
        )

        # 1. Find the first available PENDING job
        first_job = (
            DjangoScraperJob.objects.filter(query_filter)
            .annotate(type_order=type_order)
            .order_by("scraper_config__credential_id", "scraper_config__account_id", "type_order", "available_at")
            .first()
        )

        if not first_job:
            return []

        target_scraper_config_id = first_job.scraper_config_id

        # 2. Get the specific IDs we want to claim (must be done before UPDATE)
        # This ensures we only process jobs WE claimed, not jobs from failed previous runs
        target_job_ids = list(
            DjangoScraperJob.objects.filter(
                query_filter,
                scraper_config_id=target_scraper_config_id,
            ).values_list("id", flat=True)
        )

        if not target_job_ids:
            return []

        # 3. Atomically mark these specific PENDING jobs as IN_PROGRESS
        # The status=PENDING filter prevents race conditions - only PENDING jobs are updated
        updated_count = DjangoScraperJob.objects.filter(
            id__in=target_job_ids,
            status=ScraperJobStatus.PENDING,  # Extra safety: only update if still PENDING
        ).update(status=ScraperJobStatus.IN_PROGRESS)

        if updated_count == 0:
            # Another instance already claimed these jobs
            return []

        # 4. Fetch only the jobs we successfully claimed
        # Use the specific IDs AND verify they are IN_PROGRESS (our update succeeded)
        django_jobs = (
            DjangoScraperJob.objects.filter(
                id__in=target_job_ids,
                status=ScraperJobStatus.IN_PROGRESS,
            )
            .annotate(type_order=type_order)
            .order_by("type_order", "available_at")
        )

        return [self.scraper_job_repo.to_entity(job) for job in django_jobs]

    def get_scraper_job_with_complete_context(self, scraper_job_id: int) -> ScraperJobCompleteContext:
        """
        Get a scraper job with all its related context, building complete Pydantic structures
        similar to scraper_system_example.py

        Args:
            scraper_job_id: ID of the scraper job

        Returns:
            ScraperJobCompleteContext with complete assembled Pydantic structures for scraper execution
        """
        # Get Django models with all relations
        django_job = DjangoScraperJob.objects.select_related(
            "billing_cycle",
            "scraper_config",
            "scraper_config__account",
            "scraper_config__credential",
            "scraper_config__carrier",
            "billing_cycle__account",
            "billing_cycle__account__workspace",
            "billing_cycle__account__workspace__client",
            "billing_cycle__account__carrier",
        ).get(id=scraper_job_id)

        # Convert base entities using repositories (Django → Pydantic)
        scraper_job = self.scraper_job_repo.to_entity(django_job)
        scraper_config = self.scraper_config_repo.to_entity(django_job.scraper_config)
        billing_cycle = self.billing_cycle_repo.to_entity(django_job.billing_cycle)
        credential = self.credential_repo.to_entity(django_job.scraper_config.credential)
        account = self.account_repo.to_entity(django_job.billing_cycle.account)
        carrier = self.carrier_repo.to_entity(django_job.scraper_config.carrier)
        workspace = self.workspace_repo.to_entity(django_job.billing_cycle.account.workspace)
        client = self.client_repo.to_entity(django_job.billing_cycle.account.workspace.client)

        # Get related files for billing cycle and convert to Pydantic
        billing_cycle_files_django = django_job.billing_cycle.billing_cycle_files.select_related(
            "carrier_report"
        ).all()

        # Convert file collections to Pydantic
        billing_cycle_files = []
        for file_django in billing_cycle_files_django:
            file_pydantic = self.billing_cycle_file_repo.to_entity(file_django)
            # Add carrier report if exists
            if hasattr(file_django, "carrier_report") and file_django.carrier_report:
                file_pydantic.carrier_report = self.carrier_report_repo.to_entity(file_django.carrier_report)
            billing_cycle_files.append(file_pydantic)

        # Create placeholder arrays with single objects for daily and PDF files
        # These are created as placeholders since actual files don't exist until scraper execution
        daily_usage_files = [
            BillingCycleDailyUsageFile(
                id=1, billing_cycle_id=billing_cycle.id, status=FileStatus.TO_BE_FETCHED, s3_key=None
            )
        ]

        pdf_files = [
            BillingCyclePDFFile(
                id=1,
                billing_cycle_id=billing_cycle.id,
                status=FileStatus.TO_BE_FETCHED,
                status_comment="Waiting for PDF scraper execution",
                s3_key=None,
                pdf_type="invoice",
            )
        ]

        # Populate relationships
        workspace.client = client
        account.workspace = workspace

        billing_cycle.account = account
        billing_cycle.billing_cycle_files = billing_cycle_files
        billing_cycle.daily_usage_files = daily_usage_files
        billing_cycle.pdf_files = pdf_files

        # Return complete context structure as Pydantic model
        return ScraperJobCompleteContext(
            scraper_job=scraper_job,
            scraper_config=scraper_config,
            billing_cycle=billing_cycle,  # Complete with all files
            credential=credential,
            account=account,
            carrier=carrier,
            workspace=workspace,
            client=client,
        )

    def get_available_jobs_with_complete_context(
        self, include_null_available_at: bool = True
    ) -> List[ScraperJobCompleteContext]:
        """
        Get all available scraper jobs with their complete context, ready for scraper execution.
        Each job will have complete Pydantic structures like in scraper_system_example.py

        Args:
            include_null_available_at: Whether to include jobs with available_at=NULL

        Returns:
            List of ScraperJobCompleteContext with complete assembled Pydantic structures for each scraper job
        """
        available_jobs = self.get_available_scraper_jobs(include_null_available_at)

        return [self.get_scraper_job_with_complete_context(job.id) for job in available_jobs]

    def get_scraper_statistics(self) -> ScraperStatistics:
        """
        Get scraper statistics for logging.

        Returns:
            ScraperStatistics model with detailed statistics
        """
        current_time = timezone.now()

        total_pending = DjangoScraperJob.objects.filter(status=ScraperJobStatus.PENDING).count()

        available_now = DjangoScraperJob.objects.filter(
            status=ScraperJobStatus.PENDING, available_at__lte=current_time
        ).count()

        future_scheduled = DjangoScraperJob.objects.filter(
            status=ScraperJobStatus.PENDING, available_at__gt=current_time
        ).count()

        null_available = DjangoScraperJob.objects.filter(
            status=ScraperJobStatus.PENDING, available_at__isnull=True
        ).count()

        in_progress = DjangoScraperJob.objects.filter(status=ScraperJobStatus.IN_PROGRESS).count()

        running = DjangoScraperJob.objects.filter(status=ScraperJobStatus.RUNNING).count()

        return ScraperStatistics(
            timestamp=current_time,
            total_pending=total_pending,
            available_now=available_now,
            future_scheduled=future_scheduled,
            null_available_at=null_available,
            in_progress=in_progress,
            running=running,
        )

    def update_scraper_job_status(
        self, scraper_job_id: int, status: ScraperJobStatus, log_message: Optional[str] = None
    ) -> None:
        """
        Update the status of a scraper job.

        Args:
            scraper_job_id: ID of the scraper job
            status: New status
            log_message: Optional log message
        """
        django_job = DjangoScraperJob.objects.get(id=scraper_job_id)
        django_job.status = status

        if log_message:
            current_log = django_job.log or ""
            django_job.log = f"{current_log}\n{timezone.now()}: {log_message}".strip()

        if status in [ScraperJobStatus.SUCCESS, ScraperJobStatus.ERROR]:
            django_job.completed_at = timezone.now()

        django_job.save()
