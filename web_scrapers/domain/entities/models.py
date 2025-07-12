from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from web_scrapers.domain.enums import AccountType, BillingCycleStatus, FileStatus


class Client(BaseModel):
    id: Optional[int] = None
    name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: str
    phone_number: str
    related_collection: Optional[str] = None
    is_testing: bool = False
    trial_ends: Optional[datetime] = None
    active: bool = True
    managed_by_expertel: bool = True

    model_config = {"from_attributes": True}


class Workspace(BaseModel):
    id: Optional[int] = None
    name: str
    client_id: int

    model_config = {"from_attributes": True}


class Carrier(BaseModel):
    id: Optional[int] = None
    name: str
    logo: Optional[str] = None
    metadata: Optional[dict] = None

    model_config = {"from_attributes": True}


class Account(BaseModel):
    id: Optional[int] = None
    number: str
    nickname: Optional[str] = None
    workspace_id: int
    carrier_id: int
    account_type: AccountType = AccountType.CORPORATE
    billing_day: int = 15
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class BillingCycle(BaseModel):
    id: Optional[int] = None
    start_date: date
    end_date: date
    account_id: int
    status: BillingCycleStatus = BillingCycleStatus.OPEN

    model_config = {"from_attributes": True}


class CarrierReport(BaseModel):
    id: Optional[int] = None
    name: str
    carrier_id: int
    slug: Optional[str] = None
    details: Optional[dict] = None
    required: Optional[bool] = False

    model_config = {"from_attributes": True}


class BillingCycleFile(BaseModel):
    id: Optional[int] = None
    billing_cycle_id: int
    carrier_report_id: int
    status: FileStatus = FileStatus.TO_BE_FETCHED
    status_comment: Optional[str] = None
    s3_key: Optional[str] = None

    model_config = {"from_attributes": True}


class CarrierPortalCredential(BaseModel):
    id: Optional[int] = None
    username: str
    password: str
    client_id: int
    carrier_id: int
    nickname: Optional[str] = None

    model_config = {"from_attributes": True}


class BillingCycleDailyUsageFile(BaseModel):
    id: Optional[int] = None
    billing_cycle_id: int
    status: BillingCycleStatus = BillingCycleStatus.OPEN
    s3_key: Optional[str] = None

    model_config = {"from_attributes": True}


# Filters for each entity
class ClientFilter(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    contact_email: Optional[str] = None
    zip_code: Optional[str] = None
    phone_number: Optional[str] = None
    related_collection: Optional[str] = None
    is_testing: Optional[bool] = None
    trial_ends: Optional[datetime] = None
    active: Optional[bool] = None
    managed_by_expertel: Optional[bool] = None

    model_config = {"from_attributes": True}


class WorkspaceFilter(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    client_id: Optional[int] = None

    model_config = {"from_attributes": True}


class CarrierFilter(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    metadata: Optional[dict] = None

    model_config = {"from_attributes": True}


class AccountFilter(BaseModel):
    id: Optional[int] = None
    number: Optional[str] = None
    nickname: Optional[str] = None
    workspace_id: Optional[int] = None
    carrier_id: Optional[int] = None
    billing_day: Optional[int] = None
    description: Optional[str] = None
    ids: Optional[list[int]] = None

    model_config = {"from_attributes": True}


class BillingCycleFilter(BaseModel):
    id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    account_id: Optional[int] = None
    status: Optional[BillingCycleStatus] = None
    ids: Optional[list[int]] = None

    model_config = {"from_attributes": True}


class BillingCycleFileFilter(BaseModel):
    id: Optional[int] = None
    billing_cycle_id: Optional[int] = None
    carrier_report_id: Optional[int] = None
    status: Optional[FileStatus] = None
    status_comment: Optional[str] = None

    model_config = {"from_attributes": True}


class CarrierPortalCredentialFilter(BaseModel):
    id: Optional[int] = None
    client_id: Optional[int] = None
    carrier_id: Optional[int] = None

    model_config = {"from_attributes": True}


class BillingCycleDailyUsageFileFilter(BaseModel):
    id: Optional[int] = None
    billing_cycle_id: Optional[int] = None
    status: Optional[BillingCycleStatus] = None
    s3_key: Optional[str] = None

    model_config = {"from_attributes": True}
