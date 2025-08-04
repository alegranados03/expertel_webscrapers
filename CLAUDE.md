# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
- **Poetry**: This project uses Poetry for dependency management
- Install dependencies: `poetry install`
- Activate virtual environment: `poetry shell`

### Django Management
- **Development server**: `python manage.py runserver`
- **Database migrations**: `python manage.py makemigrations` then `python manage.py migrate`
- **Django admin**: Access admin interface after creating superuser with `python manage.py createsuperuser`

### Code Quality
- **Black formatter**: `poetry run black .` (line length: 119, excludes migrations)
- **isort imports**: `poetry run isort .` (compatible with Black profile)
- **MyPy type checking**: `poetry run mypy .` (excludes migrations)
- **Pre-commit hooks**: `poetry run pre-commit run --all-files`

### Testing
- **Django tests**: `python manage.py test`
- **Specific app tests**: `python manage.py test web_scrapers`

## Architecture Overview

This is a **Clean Architecture** Django project for web scraping telecommunication carrier portals (Bell, Telus, Rogers, AT&T, T-Mobile, Verizon).

### Core Structure

**Domain Layer** (`web_scrapers/domain/`):
- `entities/models.py`: Pydantic models for business entities (Client, Account, BillingCycle, ScraperJob, etc.)
- `entities/auth_strategies.py`: Abstract base strategy for carrier authentication
- `entities/scraper_strategies.py`: Abstract base strategies for different scraping tasks (MonthlyReports, DailyUsage, PDFInvoice)
- `entities/browser_wrapper.py`: Browser abstraction interface with tab management and cache clearing
- `entities/session.py`: Session state management entities
- `entities/scraper_factory.py`: Factory pattern for creating carrier-specific scrapers
- `enums.py`: Business enums (AccountType, ScraperType, SessionStatus, etc.)

**Application Layer** (`web_scrapers/application/`):
- `session_manager.py`: Core service orchestrating browser sessions and authentication strategies with persistent session reuse
- `cqrs/commands/`: Command handlers for scraping operations

**Infrastructure Layer** (`web_scrapers/infrastructure/`):
- `django/`: Django-specific implementations (models, repositories, admin)
- `playwright/`: Playwright browser automation implementations
  - `auth_strategies.py`: Concrete authentication strategies per carrier with 2FA support
  - `browser_factory.py`: Browser instance management
  - `browser_wrapper.py`: Playwright implementation with tab management and cache clearing capabilities
- `scrapers/`: Carrier-specific scraper implementations (bell_scrapers.py, att_scrapers.py, etc.)

### Key Patterns

**Strategy Pattern**: Used for both authentication (`AuthBaseStrategy`) and scraping (`ScraperBaseStrategy`) to support multiple carriers with different portal interfaces.

**Factory Pattern**: `ScraperStrategyFactory` creates appropriate scraper instances based on carrier and scraper type combinations.

**Template Method Pattern**: Base scraper strategies define the execution flow while concrete implementations provide carrier-specific logic.

**Session Management**: `SessionManager` class handles browser lifecycle, authentication state, and carrier switching with proper cleanup. Maintains persistent sessions across multiple scraper executions for efficiency.

**Browser Abstraction**: `BrowserWrapper` interface allows swapping browser implementations (currently Playwright, but designed for extensibility). Includes advanced tab management and cache clearing for error recovery.

**CQRS**: Command handlers in `application/cqrs/` separate read/write operations.

### System Flow and Execution

**Main Execution Flow** (see `SISTEMA_SCRAPERS_FLUJO_COMPLETO.md` for detailed flow):
1. **Initialization**: Create entities, SessionManager, and ScraperFactory
2. **Session Management**: Check existing session, authenticate if needed, reuse when possible
3. **Scraper Execution**: Factory creates appropriate strategy, executes with template method pattern
4. **Error Recovery**: Automatic cache clearing and re-authentication for specific error cases
5. **Cleanup**: Maintains session for next task, final cleanup only at end

**Session Reuse Logic**:
- Same carrier + same credentials = Reuse existing session
- Same carrier + different credentials = Logout and re-login
- Different carrier = Logout and login with new carrier
- Lost session = Automatic re-authentication

### Carrier Support
Currently supports: Bell, Telus, Rogers (Canada), AT&T, T-Mobile, Verizon (US). Each carrier has dedicated authentication and scraping strategies.

**Special Bell Implementation**:
- Advanced cache error detection and recovery
- Tab management for e-reports functionality
- Automatic browser data clearing when cache corruption detected
- Seamless re-authentication after cache recovery

**Special Telus Implementation**:
- Complex multi-step authentication flow through My Telus portal
- Advanced report generation with Telus IQ integration
- Queue monitoring system for long-running report generation
- Multiple report formats (CSV, Excel) with automatic format selection
- Sophisticated fallback mechanisms for download operations

### 2FA SMS Integration
**Bell Carrier** now supports automatic 2FA handling via SMS:
- **Webhook System**: `authenticator_webhook/sms2fa.py` provides SMS code reception endpoints
- **Detection**: Automatically detects 2FA verification fields after login
- **SMS Flow**: Selects text message option, requests code, waits for webhook reception
- **Code Extraction**: Extracts 6-digit codes from SMS messages via regex
- **Integration**: Bell auth strategy polls webhook for codes with timeout and consumption tracking

**Webhook Endpoints**:
- `POST /sms` - Receive SMS messages and extract codes
- `GET /code` - Get available code
- `POST /code/consume` - Mark code as used
- `GET /status` - Webhook status
- `GET /health` - Health check

**Usage**: Start webhook (`python authenticator_webhook/sms2fa.py`) before running Bell scrapers with 2FA enabled accounts.

### File Management
- Downloads stored in `downloads/` directory
- Scrapers handle file downloads and can upload to external endpoints
- Support for multiple file types (PDF invoices, usage reports, etc.)

## Important Notes

- All scraper strategies inherit from abstract base classes and must implement carrier-specific XPath selectors
- Session management includes proper browser cleanup and tab management
- The project uses dependency injection pattern for better testability
- Browser factory supports different navigator types (Chrome, Firefox, etc.)
- Authentication strategies handle carrier-specific login flows including 2FA where needed