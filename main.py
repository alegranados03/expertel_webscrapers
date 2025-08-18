"""
Procesador principal de ScraperJobs con soporte para available_at
"""

import os

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from web_scrapers.application.scraper_job_service import ScraperJobService
from web_scrapers.application.session_manager import SessionManager
from web_scrapers.domain.entities.scraper_factory import ScraperStrategyFactory
from web_scrapers.domain.enums import ScraperJobStatus


class ScraperJobProcessor:
    """Procesador principal de ScraperJobs usando clean architecture"""

    def __init__(self):
        self.scraper_job_service = ScraperJobService()
        self.session_manager = SessionManager()
        self.scraper_factory = ScraperStrategyFactory()

    def log_statistics(self) -> None:
        """Muestra estadísticas de scrapers disponibles"""
        stats = self.scraper_job_service.get_scraper_statistics()
        print(
            f"📊 Stats: {stats['available_now']} disponibles ahora, "
            f"{stats['future_scheduled']} programados para el futuro, "
            f"{stats['total_pending']} total pending"
        )

    def process_scraper_job(self, job_context: dict, job_number: int, total_jobs: int) -> bool:
        """
        Procesa un único scraper job.

        Args:
            job_context: Contexto completo del job
            job_number: Número del job actual
            total_jobs: Total de jobs a procesar

        Returns:
            True si el procesamiento fue exitoso, False en caso contrario
        """
        scraper_job = job_context["scraper_job"]
        scraper_config = job_context["scraper_config"]
        billing_cycle = job_context["billing_cycle"]
        credential = job_context["credential"]
        account = job_context["account"]
        carrier = job_context["carrier"]

        print(f"\n🔄 Procesando job {job_number}/{total_jobs}")
        print(f"   Job ID: {scraper_job.id}")
        print(f"   Tipo: {scraper_job.type}")
        print(f"   Carrier: {carrier.name}")
        print(f"   Account: {account.number}")
        print(f"   Available at: {scraper_job.available_at}")

        try:
            # Actualizar estado a RUNNING
            self.scraper_job_service.update_scraper_job_status(
                scraper_job.id,
                ScraperJobStatus.RUNNING,
                f"Iniciando procesamiento - Carrier: {carrier.name}, Tipo: {scraper_job.type}",
            )

            # Crear el scraper usando la factory
            scraper_strategy = self.scraper_factory.create_scraper(
                carrier_name=carrier.name.lower(), scraper_type=scraper_job.type
            )

            print(f"   ✅ Scraper creado: {scraper_strategy.__class__.__name__}")

            # TODO: Ejecutar el scraper real
            # result = scraper_strategy.execute(scraper_config, billing_cycle, credential)

            # Por ahora simulamos éxito
            self.scraper_job_service.update_scraper_job_status(
                scraper_job.id, ScraperJobStatus.SUCCESS, "Scraper ejecutado exitosamente (simulado)"
            )

            return True

        except Exception as e:
            error_msg = f"Error procesando scraper: {str(e)}"
            print(f"   ❌ {error_msg}")

            # Actualizar estado a ERROR
            self.scraper_job_service.update_scraper_job_status(scraper_job.id, ScraperJobStatus.ERROR, error_msg)

            return False

    def execute_available_scrapers(self) -> None:
        """Función principal que obtiene y ejecuta los scrapers disponibles"""
        print("🔍 Obteniendo scraper jobs disponibles...")

        # Mostrar estadísticas
        self.log_statistics()

        # Obtener jobs disponibles con contexto completo
        available_jobs = self.scraper_job_service.get_available_jobs_with_context()

        if not available_jobs:
            print("✅ No hay scraper jobs disponibles para ejecutar en este momento.")
            return

        print(f"🚀 Encontrados {len(available_jobs)} scraper jobs disponibles para ejecutar")

        # Procesar cada job
        successful_jobs = 0
        failed_jobs = 0

        for i, job_context in enumerate(available_jobs, 1):
            success = self.process_scraper_job(job_context, i, len(available_jobs))
            if success:
                successful_jobs += 1
            else:
                failed_jobs += 1

        # Resumen final
        print(f"\n📈 Resumen de ejecución:")
        print(f"   ✅ Exitosos: {successful_jobs}")
        print(f"   ❌ Fallidos: {failed_jobs}")
        print(f"   📊 Total procesados: {len(available_jobs)}")


def main():
    """Función principal del procesador"""
    try:
        processor = ScraperJobProcessor()
        processor.execute_available_scrapers()
    except Exception as e:
        print(f"❌ Error en el procesador principal: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
