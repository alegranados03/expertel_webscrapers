"""
ScraperJobService - Servicio para gestión de ScraperJobs con soporte para available_at
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db.models import Q
from django.utils import timezone

from web_scrapers.domain.entities.models import ScraperJob
from web_scrapers.domain.enums import ScraperJobStatus
from web_scrapers.infrastructure.django.models import ScraperJob as DjangoScraperJob
from web_scrapers.infrastructure.django.repositories import (
    AccountRepository,
    BillingCycleRepository,
    CarrierPortalCredentialRepository,
    CarrierRepository,
    ScraperConfigRepository,
    ScraperJobRepository,
)


class ScraperJobService:
    """Servicio para gestión de ScraperJobs con fetch inteligente basado en available_at"""

    def __init__(self):
        self.scraper_job_repo = ScraperJobRepository()
        self.scraper_config_repo = ScraperConfigRepository()
        self.billing_cycle_repo = BillingCycleRepository()
        self.credential_repo = CarrierPortalCredentialRepository()
        self.account_repo = AccountRepository()
        self.carrier_repo = CarrierRepository()

    def get_available_scraper_jobs(self, include_null_available_at: bool = True) -> List[ScraperJob]:
        """
        Obtiene todos los scraper jobs que están disponibles para ejecución.

        Args:
            include_null_available_at: Si incluir jobs con available_at=NULL para compatibilidad

        Returns:
            Lista de ScraperJob entities disponibles para ejecución
        """
        current_time = timezone.now()

        # Query con NULL safety para transición
        query_filter = Q(status=ScraperJobStatus.PENDING)

        if include_null_available_at:
            query_filter &= Q(available_at__lte=current_time) | Q(available_at__isnull=True)
        else:
            query_filter &= Q(available_at__lte=current_time)

        django_jobs = DjangoScraperJob.objects.filter(query_filter).order_by("available_at")

        return [self.scraper_job_repo.to_entity(job) for job in django_jobs]

    def get_scraper_job_with_context(self, scraper_job_id: int) -> Dict[str, Any]:
        """
        Obtiene un scraper job con todo su contexto relacionado.

        Args:
            scraper_job_id: ID del scraper job

        Returns:
            Diccionario con toda la información necesaria para ejecutar el scraper
        """
        django_job = DjangoScraperJob.objects.select_related(
            "billing_cycle",
            "scraper_config",
            "scraper_config__account",
            "scraper_config__credential",
            "scraper_config__carrier",
            "billing_cycle__account",
            "billing_cycle__account__workspace",
            "billing_cycle__account__carrier",
        ).get(id=scraper_job_id)

        return {
            "scraper_job": self.scraper_job_repo.to_entity(django_job),
            "scraper_config": self.scraper_config_repo.to_entity(django_job.scraper_config),
            "billing_cycle": self.billing_cycle_repo.to_entity(django_job.billing_cycle),
            "credential": self.credential_repo.to_entity(django_job.scraper_config.credential),
            "account": self.account_repo.to_entity(django_job.billing_cycle.account),
            "carrier": self.carrier_repo.to_entity(django_job.scraper_config.carrier),
        }

    def get_available_jobs_with_context(self, include_null_available_at: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene todos los scraper jobs disponibles con su contexto completo.

        Args:
            include_null_available_at: Si incluir jobs con available_at=NULL

        Returns:
            Lista de diccionarios con información completa de cada scraper job
        """
        available_jobs = self.get_available_scraper_jobs(include_null_available_at)

        return [self.get_scraper_job_with_context(job.id) for job in available_jobs]

    def get_scraper_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de los scrapers para logging.

        Returns:
            Diccionario con estadísticas detalladas
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

        return {
            "timestamp": current_time,
            "total_pending": total_pending,
            "available_now": available_now,
            "future_scheduled": future_scheduled,
            "null_available_at": null_available,
        }

    def update_scraper_job_status(
        self, scraper_job_id: int, status: ScraperJobStatus, log_message: Optional[str] = None
    ) -> None:
        """
        Actualiza el estado de un scraper job.

        Args:
            scraper_job_id: ID del scraper job
            status: Nuevo estado
            log_message: Mensaje de log opcional
        """
        django_job = DjangoScraperJob.objects.get(id=scraper_job_id)
        django_job.status = status

        if log_message:
            current_log = django_job.log or ""
            django_job.log = f"{current_log}\n{timezone.now()}: {log_message}".strip()

        if status in [ScraperJobStatus.SUCCESS, ScraperJobStatus.ERROR]:
            django_job.completed_at = timezone.now()

        django_job.save()
