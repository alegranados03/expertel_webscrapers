from enum import Enum


class Navigators(str, Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    SAFARI = "safari"


class CarrierPortalUrls(str, Enum):
    ATT = "https://www.business.att.com/login-portal.html"
    BELL = "https://business.bell.ca/corporateselfserve/Login"
    TELUS = "https://www.telus.com/en"
    ROGERS = ""
    TMOBILE = "https://account.t-mobile.com/signin/v2/?redirect_uri=https:%2F%2Ftfb.t-mobile.com%2Fimplicit%2Fcallback&scope=TMO_ID_profile%20openid%20role%20extended_lines%20email&client_id=TFBBilling&access_type=ONLINE&response_type=code"
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
