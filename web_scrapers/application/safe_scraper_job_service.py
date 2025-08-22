"""
Safe wrapper for ScraperJobService that handles async context issues.

This wrapper detects when we're in an async context (after Playwright execution)
and automatically uses sync_to_async to make Django ORM calls work safely.
"""

import asyncio
import logging
from typing import Any, Callable, Optional, Union

from asgiref.sync import sync_to_async

from web_scrapers.domain.enums import ScraperJobStatus
from .scraper_job_service import ScraperJobService


class SafeScraperJobService:
    """
    Safe wrapper for ScraperJobService that handles both sync and async contexts.
    
    This solves the SynchronousOnlyOperation error that occurs when Django ORM
    is called after Playwright creates an async context.
    """
    
    def __init__(self, scraper_job_service: ScraperJobService):
        """
        Initialize with the original ScraperJobService.
        
        Args:
            scraper_job_service: The original ScraperJobService instance
        """
        self.scraper_job_service = scraper_job_service
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def update_scraper_job_status(
        self, scraper_job_id: int, status: ScraperJobStatus, log_message: Optional[str] = None
    ) -> Union[None, "asyncio.Task[None]"]:
        """
        Safe update that works in both sync and async contexts.
        
        Automatically detects the execution context and uses the appropriate method:
        - Sync context: Direct call to original service
        - Async context: Uses sync_to_async wrapper
        
        Args:
            scraper_job_id: ID of the scraper job to update
            status: New status to set
            log_message: Optional log message to append
        """
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            if loop and loop.is_running():
                self.logger.debug(f"Async context detected for job {scraper_job_id}, using sync_to_async")
                # We're in async context, use sync_to_async
                return asyncio.create_task(
                    sync_to_async(self.scraper_job_service.update_scraper_job_status)(
                        scraper_job_id, status, log_message
                    )
                )
        except RuntimeError:
            # No async context or no running loop, execute normally
            self.logger.debug(f"Sync context detected for job {scraper_job_id}, executing normally")
            pass
        
        # Execute normally in sync context
        return self.scraper_job_service.update_scraper_job_status(
            scraper_job_id, status, log_message
        )
    
    def __getattr__(self, name: str) -> Any:
        """
        Delegate all other methods to the original service.
        
        This ensures full compatibility - any method not explicitly overridden
        will be passed through to the original ScraperJobService.
        
        Args:
            name: Name of the attribute/method to delegate
            
        Returns:
            The attribute/method from the original service, wrapped if callable
        """
        attr = getattr(self.scraper_job_service, name)
        
        # If it's a method, wrap it to handle async context
        if callable(attr):
            def wrapped_method(*args: Any, **kwargs: Any) -> Any:
                try:
                    # Check if we're in an async context
                    loop = asyncio.get_running_loop()
                    if loop and loop.is_running():
                        self.logger.debug(f"Async context detected for method {name}, using sync_to_async")
                        # We're in async context, use sync_to_async
                        return asyncio.create_task(
                            sync_to_async(attr)(*args, **kwargs)
                        )
                except RuntimeError:
                    # No async context or no running loop, execute normally
                    self.logger.debug(f"Sync context detected for method {name}, executing normally")
                    pass
                
                # Execute normally in sync context
                return attr(*args, **kwargs)
            
            return wrapped_method
        
        # If it's not a method, return as-is
        return attr