# PROJECT TECHNICAL REFERENCE

This document provides a comprehensive technical reference for the Web Scrapers project, documenting all available models, entities, repositories, factories, enums, and services that actually exist in the codebase.

## 1. DOMAIN ENTITIES

### Core Business Models

#### Client
```python
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
```

#### Account
```python
class Account(BaseModel):
    id: Optional[int] = None
    number: str
    nickname: Optional[str] = None
    workspace_id: int
    carrier_id: int
    account_type: AccountType = AccountType.CORPORATE
    billing_day: int = 15
    description: Optional[str] = None
```

#### BillingCycle
```python
class BillingCycle(BaseModel):
    id: Optional[int] = None
    start_date: date
    end_date: date
    account_id: int
    status: BillingCycleStatus = BillingCycleStatus.OPEN
    account: Optional["Account"] = None
```

#### ScraperJob
```python
class ScraperJob(BaseModel):
    id: Optional[int] = None
    billing_cycle_id: int
    scraper_config_id: int
    status: ScraperJobStatus = ScraperJobStatus.PENDING
    type: ScraperType = ScraperType.DAILY_USAGE
    log: Optional[str] = None
    completed_at: Optional[datetime] = None
```

### Session Management

#### Credentials
```python
class Credentials(BaseModel):
    id: Optional[int] = None
    username: str
    password: str
    carrier: Carrier
```

#### SessionState
```python
class SessionState(BaseModel):
    status: SessionStatus = SessionStatus.LOGGED_OUT
    carrier: Optional[Carrier] = None
    credentials: Optional[Credentials] = None
    error_message: Optional[str] = None
```

## 2. ENUMS

### Domain Enums
- **Navigators**: CHROME, FIREFOX, EDGE, SAFARI
- **FileStatus**: TO_BE_FETCHED, READY, PROCESSING, PROCESSED, ERROR
- **AccountType**: CORPORATE, INDIVIDUAL
- **BillingCycleStatus**: OPEN, READY_TO_PROCESS, PROCESSING, PROCESSED, ERROR
- **ScraperJobStatus**: PENDING, RUNNING, SUCCESS, ERROR
- **ScraperType**: DAILY_USAGE, MONTHLY_REPORTS, PDF_INVOICE

### Session Enums
- **SessionStatus**: LOGGED_OUT, LOGGED_IN, ERROR
- **Carrier**: BELL, TELUS, ROGERS, ATT, TMOBILE, VERIZON

### Carrier Portal URLs
- **ATT**: https://www.business.att.com/login-portal.html
- **BELL**: https://business.bell.ca/corporateselfserve/Login
- **TELUS**: https://www.telus.com/en
- **TMOBILE**: https://account.t-mobile.com/signin/v2/...
- **VERIZON**: https://mblogin.verizonwireless.com/account/business/ilogin

## 3. REPOSITORY CLASSES

### Base Repository Classes
All repositories extend `DjangoFullRepository[EntityType, ModelType]` with these methods:
- `to_entity(model)` - Convert ORM model to domain entity
- `to_orm_model(entity)` - Convert domain entity to ORM model
- `get()`, `find()`, `filter()`, `all()` - Read operations
- `save()`, `update()`, `delete()` - Write operations
- `bulk_create()`, `bulk_update()`, `bulk_delete()` - Bulk operations

### Available Repositories
- `ClientRepository`
- `WorkspaceRepository`
- `CarrierRepository`
- `AccountRepository`
- `BillingCycleRepository`
- `CarrierReportRepository`
- `BillingCycleFileRepository`
- `CarrierPortalCredentialRepository`
- `ScraperConfigRepository`
- `ScraperJobRepository`

## 4. FACTORY CLASSES

### BrowserDriverFactory
```python
# Methods:
def create_browser(browser_type: Navigators) -> Browser
def create_context(browser: Browser) -> BrowserContext
def create_page(context: BrowserContext) -> Page
def create_full_setup(browser_type: Navigators) -> tuple[Browser, BrowserContext]
```

### ScraperStrategyFactory
```python
def create_scraper(carrier: Carrier, scraper_type: ScraperType, browser_wrapper: BrowserWrapper) -> ScraperBaseStrategy
```

**Supported Strategy Combinations:**
- **Bell**: MonthlyReports, DailyUsage, PDFInvoice
- **Telus**: MonthlyReports, DailyUsage, PDFInvoice
- **Rogers**: MonthlyReports, DailyUsage, PDFInvoice
- **ATT**: MonthlyReports, DailyUsage, PDFInvoice
- **T-Mobile**: MonthlyReports, DailyUsage, PDFInvoice
- **Verizon**: MonthlyReports, DailyUsage, PDFInvoice

## 5. ABSTRACT BASE STRATEGIES

### AuthBaseStrategy
```python
# Abstract methods:
def login(credentials: Credentials) -> bool
def logout() -> bool
def is_logged_in() -> bool
def get_login_url() -> str
def get_logout_xpath() -> str
def get_username_xpath() -> str
def get_password_xpath() -> str
def get_login_button_xpath() -> str
```

### ScraperBaseStrategy
```python
# Abstract methods:
def execute(config: ScraperConfig, billing_cycle: BillingCycle, credentials: Credentials) -> ScraperResult

# Implemented helper methods:
def _create_file_mapping(downloaded_files: List[FileDownloadInfo]) -> List[Dict[str, Any]]
```

### MonthlyReportsScraperStrategy
```python
# Abstract methods (in addition to ScraperBaseStrategy):
def _find_files_section(config: ScraperConfig, billing_cycle: BillingCycle) -> Optional[Any]
def _download_files(files_section: Any, config: ScraperConfig, billing_cycle: BillingCycle) -> List[FileDownloadInfo]
def _upload_files_to_endpoint(files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle) -> bool
```

### BrowserWrapper
Abstract interface with 35+ methods for browser automation:

**Core Navigation:**
- `goto(url, wait_until)` - Navigate to URL
- `find_element_by_xpath(xpath, timeout)` - Find element
- `click_element(xpath, timeout)` - Click element
- `type_text(xpath, text, timeout)` - Type text
- `clear_and_type(xpath, text, timeout)` - Clear and type

**Element Interaction:**
- `select_dropdown_option(xpath, option_text, timeout)` - Select dropdown option
- `get_text(xpath, timeout)` - Get element text
- `get_attribute(xpath, attribute, timeout)` - Get attribute value
- `wait_for_element(xpath, timeout)` - Wait for element
- `is_element_visible(xpath, timeout)` - Check visibility

**Page Management:**
- `wait_for_page_load(timeout)` - Wait for page load
- `get_current_url()` - Get current URL
- `take_screenshot(path)` - Take screenshot
- `reload_page()` - Reload page
- `go_back()`, `go_forward()` - Navigation

**Tab Management:**
- `wait_for_new_tab(timeout)` - Wait for new tab
- `switch_to_new_tab()` - Switch to new tab
- `close_current_tab()` - Close current tab
- `switch_to_previous_tab()` - Switch to previous tab
- `get_tab_count()` - Get tab count

**Cache and Error Recovery:**
- `clear_browser_data(clear_cookies, clear_storage, clear_cache)` - Clear browser data
- `close_all_tabs_except_main()` - Close all tabs except main
- `get_current_tab_index()` - Get current tab index

**Advanced Operations:**
- `expect_download_and_click(xpath, timeout)` - Click element and handle download
- `click_and_switch_to_new_tab(xpath, timeout)` - Click link that opens new tab and switch focus
- `change_button_attribute(xpath, attribute, value)` - Modify element attributes via JavaScript

## 6. APPLICATION SERVICES

### SessionManager
Main orchestration service for browser sessions and authentication:

**Session State:**
- `is_logged_in()` - Check if logged in
- `get_current_carrier()` - Get current carrier
- `get_current_credentials()` - Get current credentials
- `refresh_session_status()` - Refresh session status
- `force_logout()` - Force logout

**Browser Management:**
- `get_browser_wrapper()` - Get browser wrapper
- `get_new_browser_wrapper()` - Create new browser wrapper

**Authentication:**
- `login(credentials)` - Login with credentials
- `logout()` - Logout from current session

**Cleanup:**
- `cleanup()` - Clean up all resources

**Supported Auth Strategies:**
- Bell: `BellAuthStrategy`
- Telus: `TelusAuthStrategy`
- Rogers: `RogersAuthStrategy`
- ATT: `ATTAuthStrategy`
- T-Mobile: `TMobileAuthStrategy`
- Verizon: `VerizonAuthStrategy`

## 7. INFRASTRUCTURE IMPLEMENTATIONS

### PlaywrightWrapper
Concrete implementation of BrowserWrapper using Playwright.
Implements all 35+ BrowserWrapper abstract methods with Playwright-specific logic.

### Auth Strategy Implementations
Located in `web_scrapers/infrastructure/playwright/auth_strategies.py`:
- Each carrier has specific XPath selectors and login flows
- Bell includes 2FA SMS integration via webhook system
- All strategies implement the AuthBaseStrategy interface

### Scraper Strategy Implementations
Located in `web_scrapers/infrastructure/scrapers/`:
- **Bell Scrapers** (`bell_scrapers.py`): Includes cache error recovery
- **Other Carriers**: ATT, Telus, Rogers, T-Mobile, Verizon
- Each carrier has 3 scraper types: MonthlyReports, DailyUsage, PDFInvoice

## 8. 2FA SMS INTEGRATION

### Bell Carrier 2FA Support
**Webhook System** (`authenticator_webhook/sms2fa.py`):
- Automatic SMS code reception
- Code extraction via regex
- Integration with Bell auth strategy
- Polling mechanism with timeout

**Endpoints:**
- `POST /sms` - Receive SMS messages
- `GET /code` - Get available code
- `POST /code/consume` - Mark code as used
- `GET /status` - Webhook status
- `GET /health` - Health check

## 9. ERROR HANDLING AND RECOVERY

### Cache Error Recovery (Bell Specific)
- Detection via header verification in e-reports
- Browser data clearing (cookies, localStorage, sessionStorage)
- Automatic session loss and re-authentication
- Retry mechanism with limited attempts

### Session Management
- Continuous session state verification
- Automatic re-authentication on session loss
- Proper browser resource cleanup
- Error state management with detailed messages

### Browser Management
- Tab management and cleanup
- Context and browser instance lifecycle
- Resource cleanup on errors
- Graceful degradation

## 10. KEY FILE PATHS

### Domain Layer
- `web_scrapers/domain/entities/models.py` - Core business entities
- `web_scrapers/domain/entities/auth_strategies.py` - Abstract auth base
- `web_scrapers/domain/entities/scraper_strategies.py` - Abstract scraper bases
- `web_scrapers/domain/entities/browser_wrapper.py` - Browser abstraction
- `web_scrapers/domain/entities/session.py` - Session management
- `web_scrapers/domain/entities/scraper_factory.py` - Scraper factory
- `web_scrapers/domain/enums.py` - Business enums

### Application Layer
- `web_scrapers/application/session_manager.py` - Session orchestration

### Infrastructure Layer
- `web_scrapers/infrastructure/playwright/browser_factory.py` - Browser factory
- `web_scrapers/infrastructure/playwright/browser_wrapper.py` - Playwright implementation
- `web_scrapers/infrastructure/playwright/auth_strategies.py` - Auth implementations
- `web_scrapers/infrastructure/scrapers/` - Scraper implementations

### External Components
- `authenticator_webhook/sms2fa.py` - SMS 2FA webhook system

## USAGE PATTERNS

### Basic Scraper Execution
```python
# 1. Initialize components
session_manager = SessionManager(browser_type=Navigators.CHROME)
scraper_factory = ScraperStrategyFactory()
credentials = Credentials(username="user", password="pass", carrier=Carrier.BELL)

# 2. Handle session
if not session_manager.is_logged_in():
    session_manager.login(credentials)

# 3. Create and execute scraper
browser_wrapper = session_manager.get_browser_wrapper()
scraper = scraper_factory.create_scraper(Carrier.BELL, ScraperType.MONTHLY_REPORTS, browser_wrapper)
result = scraper.execute(config, billing_cycle, credentials)

# 4. Cleanup
session_manager.logout()
session_manager.cleanup()
```

### Error Handling Pattern
```python
try:
    result = scraper.execute(config, billing_cycle, credentials)
    if result.success:
        # Process files
        for file_info in result.files:
            print(f"Downloaded: {file_info['file_name']}")
    else:
        print(f"Scraper error: {result.error}")
except Exception as e:
    print(f"Unexpected error: {str(e)}")
```

---

**Last Updated:** Based on codebase analysis including cache recovery improvements
**Version:** Clean Architecture Django Web Scrapers Project with Bell 2FA Support