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
