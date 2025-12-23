from enum import Enum


class Navigators(str, Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    SAFARI = "safari"


class CarrierPortalUrls(str, Enum):
    ATT = "https://www.wireless.att.com/premiercare/"
    BELL = "https://business.bell.ca/corporateselfserve/Login"
    TELUS = "https://www.telus.com/en"
    ROGERS = ""
    TMOBILE = "https://account.t-mobile.com"
    # TMOBILE = "https://account.t-mobile.com/signin/v2/?redirect_uri=https:%2F%2Ftfb.t-mobile.com%2Fimplicit%2Fcallback&scope=TMO_ID_profile%20openid%20role%20extended_lines%20email&client_id=TFBBilling&access_type=ONLINE&response_type=code"
    VERIZON = "https://mblogin.verizonwireless.com/account/business/ilogin"


class FileStatus(str, Enum):
    TO_BE_FETCHED = "to_be_fetched"
    READY = "ready"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"


class AccountType(str, Enum):
    CORPORATE = "corporate"
    INDIVIDUAL = "individual"


class BillingCycleStatus(str, Enum):
    OPEN = "open"
    READY_TO_PROCESS = "ready_to_process"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"


class PhoneNumberStatus(str, Enum):
    ACTIVE = "active"
    UNUSED = "unused"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class ScraperJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class ScraperType(str, Enum):
    DAILY_USAGE = "daily_usage"
    MONTHLY_REPORTS = "monthly_reports"
    PDF_INVOICE = "pdf_invoice"


class BellFileSlug(str, Enum):
    COST_OVERVIEW = "cost_overview"
    ENHANCED_USER_PROFILE_REPORT = "enhanced_user_profile_report"
    USAGE_OVERVIEW = "usage_overview"


class TelusFileSlug(str, Enum):
    AIRTIME_DETAIL = "airtime_detail"
    INDIVIDUAL_DETAIL = "individual_detail"
    MOBILITY_DEVICE = "mobility_device"
    WIRELESS_VOICE = "wireless_voice"
    WIRELESS_DATA = "wireless_data"
    WIRELESS_SUBSCRIBER_CHARGES = "wireless_subscriber_charges"
    WIRELESS_SUBSCRIBER_USAGE = "wireless_subscriber_usage"
    GROUP_SUMMARY = "group_summary"
    SUMMARY_OF_RENEWAL = "summary_of_renewal"
    INVOICE_DETAIL = "invoice_detail"


class VerizonFileSlug(str, Enum):
    ACCOUNT_AND_WIRELESS = "account_wireless"
    WIRELESS_CHARGES_DETAIL = "wireless_charges_detail"
    DEVICE_REPORT = "device_report"
    SUSPENDED_WIRELESS_NUMBERS = "suspended_wireless_numbers"
    ACTIVATION_AND_DEACTIVATION = "activation_and_deactivation"


class ATTFileSlug(str, Enum):
    WIRELESS_CHARGES = "wireless_charges"
    USAGE_DETAILS = "usage_details"
    MONTHLY_CHARGES = "monthly_charges"
    DEVICE_INSTALLMENT = "device_installment"
    UPGRADE_AND_INVENTORY = "upgrade_and_inventory"
    ALL_BILLING_CYCLE_CHARGES = "all_billing_cycle_charges"


class TMobileFileSlug(str, Enum):
    CHARGES_AND_USAGE = "charges_and_usage"
    USAGE_DETAIL = "usage_detail"
    INVENTORY_REPORT = "inventory_report"
    EQUIPMENT_INSTALLMENT = "equipment_installment"
