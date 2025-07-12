from django.db import models


class FileStatusChoices(models.TextChoices):
    TO_BE_FETCHED = "to_be_fetched", "To be fetched"
    READY = "ready", "Ready"
    READING = "reading", "Reading"
    SUCCESS = "success", "Success"
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
