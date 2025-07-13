from django.db import models

from web_scrapers.infrastructure.django.enums import *


class Client(models.Model):
    name = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=300, null=True)
    contact_email = models.CharField(max_length=300, null=True)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    zip_code = models.CharField(max_length=10)
    phone_number = models.CharField(max_length=20)
    related_collection = models.CharField(max_length=100, null=True, unique=True)
    is_testing = models.BooleanField(default=False)
    trial_ends = models.DateTimeField(null=True)
    active = models.BooleanField(default=True)
    managed_by_expertel = models.BooleanField(default=True)

    class Meta:
        db_table = "clients"
        managed = False

    def __str__(self):
        return self.name


class Workspace(models.Model):
    name = models.CharField(max_length=100)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="workspaces")

    class Meta:
        db_table = "workspaces"
        managed = False

    def __str__(self):
        return self.name


class Carrier(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, null=True)

    class Meta:
        db_table = "carriers"
        managed = False


class Account(models.Model):
    number = models.CharField(max_length=200, null=False)
    nickname = models.CharField(max_length=200, null=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="accounts")
    carrier = models.ForeignKey(Carrier, on_delete=models.PROTECT, related_name="accounts")
    account_type = models.CharField(choices=AccountTypeChoices.choices, default=AccountTypeChoices.CORPORATE)
    billing_day = models.IntegerField(default=15)
    description = models.CharField(max_length=500, null=True)

    class Meta:
        db_table = "accounts"
        managed = False


class BillingCycle(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="billing_cycles")
    status = models.CharField(choices=BillingCycleStatusChoices.choices, default=BillingCycleStatusChoices.OPEN)

    def __init__(self, *args, **kwargs):
        """Initializes the model, also saves the original values for name and
        folder in an extra attribute, to be able to identify from a signal if
        these attributes changed.
        """
        super().__init__(*args, **kwargs)
        self._status = self.status

    class Meta:
        db_table = "billing_cycles"
        managed = False


class CarrierReport(models.Model):
    name = models.CharField(max_length=200, unique=True)
    carrier = models.ForeignKey(Carrier, on_delete=models.RESTRICT)
    slug = models.CharField(max_length=200, null=True)
    details = models.JSONField(default=dict, null=True)
    required = models.BooleanField(default=False, null=True)

    class Meta:
        db_table = "carrier_reports"
        managed = False


class BillingCycleFile(models.Model):
    billing_cycle = models.ForeignKey(BillingCycle, on_delete=models.PROTECT, related_name="billing_cycle_files")
    carrier_report = models.ForeignKey(CarrierReport, on_delete=models.PROTECT, related_name="billing_cycle_files")
    status = models.CharField(choices=FileStatusChoices.choices, default=FileStatusChoices.TO_BE_FETCHED)
    status_comment = models.CharField(max_length=300, blank=True, null=True)
    s3_key = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        db_table = "billing_cycle_files"
        managed = False


class CarrierPortalCredential(models.Model):
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=150)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="portal_credentials")
    carrier = models.ForeignKey(Carrier, on_delete=models.PROTECT, related_name="client_credentials")
    nickname = models.CharField(max_length=150, null=True)

    class Meta:
        db_table = "carrier_portal_credentials"
        managed = False


class BillingCycleDailyUsageFile(models.Model):
    billing_cycle = models.ForeignKey(BillingCycle, on_delete=models.PROTECT, related_name="daily_usage_files")
    status = models.CharField(choices=BillingCycleStatusChoices.choices, default=BillingCycleStatusChoices.OPEN)
    s3_key = models.CharField(max_length=300, blank=True, null=True)

    def __init__(self, *args, **kwargs):
        """Initializes the model, also saves the original values for name and
        folder in an extra attribute, to be able to identify from a signal if
        these attributes changed.
        """
        super().__init__(*args, **kwargs)
        self._status = self.status

    class Meta:
        db_table = "daily_usage_files"
        managed = False


class ScraperConfig(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="scraper_config")
    credential = models.ForeignKey(
        CarrierPortalCredential, on_delete=models.PROTECT, related_name="scraper_configs"
    )
    carrier = models.ForeignKey(Carrier, on_delete=models.PROTECT, related_name="scraper_configs")
    parameters = models.JSONField(default=dict, blank=True)
    days_offset = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "scraper_configs"
        managed = False

class ScraperJob(models.Model):
    billing_cycle = models.ForeignKey(
        BillingCycle, on_delete=models.CASCADE, related_name="scraper_jobs"
    )
    scraper_config = models.ForeignKey(ScraperConfig, on_delete=models.PROTECT, related_name="scraper_jobs")
    status = models.CharField(
        max_length=50,
        choices=ScraperJobStatus.choices,
        default=ScraperJobStatus.PENDING,
    )
    type = models.CharField(
        max_length=50,
        choices=ScraperType.choices,
        default=ScraperType.DAILY_USAGE,
    )
    log = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "scraper_jobs"
        managed = False

