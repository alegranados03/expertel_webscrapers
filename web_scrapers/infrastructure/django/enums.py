from django.db import models


class FileStatusChoices(models.TextChoices):
    TO_BE_FETCHED = "to_be_fetched", "To be fetched"
    READY = "ready", "Ready"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    ERROR = "error", "Error"


class AccountTypeChoices(models.TextChoices):
    CORPORATE = "corporate", "Corporate"


class BillingCycleStatusChoices(models.TextChoices):
    OPEN = "open", "Open"
    READY_TO_PROCESS = "ready_to_process", "Ready to Process"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    ERROR = "error", "Error"


class PhoneNumberChoices(models.TextChoices):
    ACTIVE = "active", "Active"
    UNUSED = "unused", "Unused"
    SUSPENDED = "suspended", "Suspended"
    CANCELLED = "cancelled", "Cancelled"
    UNKNOWN = "unknown", "Unknown"


class ScraperJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    ERROR = "error", "Error"


class ScraperType(models.TextChoices):
    DAILY_USAGE = "daily_usage", "Daily Usage"
    MONTHLY_REPORTS = "monthly_reports", "Monthly Reports"
    PDF_INVOICE = "pdf_invoice", "PDF Invoice"
