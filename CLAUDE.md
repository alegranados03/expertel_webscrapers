# CLAUDE.md

This file provides guidance to Claude Code when working with the Expertel Web Scrapers project.

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

This is a **production-grade Clean Architecture Django project** for automated web scraping of telecommunication carrier portals with universal file upload integration and advanced session management.

### Supported Carriers
**Canada**: Bell, Telus, Rogers | **USA**: AT&T, T-Mobile, Verizon
Each carrier supports 3 scraper types: Monthly Reports, Daily Usage, PDF Invoices (18 total strategies)

### Core Architecture

**Domain Layer** (`web_scrapers/domain/`):
- `entities/models.py`: Complete Pydantic business entities (Client, Account, BillingCycle, FileDownloadInfo, ScraperConfig, etc.)
- `entities/auth_strategies.py`: Abstract authentication strategy base class
- `entities/scraper_strategies.py`: Advanced base strategies with built-in ZIP extraction, file mapping, and universal upload integration
- `entities/browser_wrapper.py`: Comprehensive browser abstraction (30+ methods) with tab management, cache clearing, and download handling
- `entities/session.py`: Session state management entities (SessionStatus, Credentials, Carrier)
- `entities/scraper_factory.py`: Factory pattern for creating all 18 carrier-specific scrapers
- `enums.py`: Business enums (Navigators, CarrierPortalUrls, FileStatus, AccountType, ScraperType, etc.)

**Application Layer** (`web_scrapers/application/`):
- `session_manager.py`: Advanced session orchestration with persistent session reuse, automatic re-authentication, and error recovery
- `cqrs/commands/`: Command handlers for scraping operations

**Infrastructure Layer** (`web_scrapers/infrastructure/`):
- `services/file_upload_service.py`: **NEW** Universal File Upload Service with external API integration
- `django/`: Complete Django implementations (models, repositories, admin interfaces)
- `playwright/`: Full Playwright automation with stealth features and comprehensive browser management
- `scrapers/`: Production-ready carrier-specific implementations with advanced features

### Key Architectural Patterns

**Strategy Pattern**: Authentication and scraping strategies for different carriers and portal interfaces
**Factory Pattern**: Dynamic scraper creation based on carrier and scraper type combinations
**Template Method Pattern**: Base strategies define execution flow, concrete implementations provide carrier-specific logic
**Repository Pattern**: Complete Django ORM integration with data access abstraction
**CQRS Pattern**: Command handlers in `application/cqrs/` for different operations

## Major System Components

### 1. Universal File Upload Service

**Location**: `web_scrapers/infrastructure/services/file_upload_service.py`

**Features**:
- **API Integration**: Configurable external API endpoints via environment variables
- **Multiple Upload Types**: Automatic routing for monthly, daily_usage, pdf_invoice files
- **Batch Processing**: Upload multiple files with comprehensive success/failure tracking
- **Error Handling**: Robust error handling with detailed logging and status reporting
- **File Validation**: Content type validation and file existence checks

**API Endpoint Configuration**:
```
Monthly Reports: /api/v1/accounts/billing-cycles/{cycle_id}/files/{file_id}/upload-file/
Daily Usage: /api/v1/accounts/billing-cycles/{cycle_id}/daily-usage/
PDF Invoice: /api/v1/accounts/billing-cycles/{cycle_id}/pdf-invoice/
```

**Environment Variables**:
```env
API_BASE_URL=https://api.expertel.com
API_TOKEN=your_api_bearer_token
```

### 2. Advanced Session Management

**Location**: `web_scrapers/application/session_manager.py`

**Capabilities**:
- **Persistent Session Reuse**: Maintains sessions across multiple scraper executions for efficiency
- **Intelligent Session Logic**: 
  - Same carrier + same credentials = Reuse existing session
  - Same carrier + different credentials = Logout and re-login
  - Different carrier = Logout and login with new carrier
  - Lost session = Automatic re-authentication
- **Browser Lifecycle Management**: Complete browser instance management with proper cleanup
- **Error Recovery**: Comprehensive error handling and automatic state recovery

### 3. SMS 2FA Integration System

**Location**: `authenticator_webhook/sms2fa.py`

**Complete 2FA Workflow**:
- **Flask Webhook Service**: Standalone service (port 8000) for SMS code reception
- **Thread-Safe Storage**: Secure code storage with 5-minute expiration and consumption tracking
- **Pattern Matching**: Supports 6-8 digit codes with regex extraction
- **Bell Integration**: Automatic 2FA handling in Bell authentication strategy

**Webhook Endpoints**:
- `POST /sms`: Receive and extract codes from SMS messages
- `GET /code`: Retrieve available code
- `POST /code/consume`: Mark code as used
- `GET /status`: Webhook status and health
- `GET /health`: Health check endpoint

**Usage**: Start webhook service (`python authenticator_webhook/sms2fa.py`) before running Bell scrapers with 2FA accounts.

### 4. Advanced Browser Automation

**Browser Factory** (`web_scrapers/infrastructure/playwright/browser_factory.py`):
- Multi-browser support (Chrome, Firefox, Edge, Safari)
- Stealth integration with anti-detection measures
- Environment-based configuration
- Singleton pattern for resource optimization

**Browser Wrapper** (`web_scrapers/infrastructure/playwright/browser_wrapper.py`):
- 30+ methods for navigation, interaction, and management
- Advanced tab management (switch, close, count)
- Download handling with automatic file saving
- Cache and browser data clearing capabilities
- Screenshot and debugging features

## System Execution Flow

### Complete Scraper Pipeline
1. **Initialization**: Create entities, SessionManager, and ScraperFactory
2. **Session Management**: Validate existing session, authenticate if needed, reuse when possible
3. **Scraper Execution**: Factory creates appropriate strategy, executes with template method pattern
4. **File Processing**: Discover files section, download files, extract ZIPs if needed
5. **File Upload**: Automatic upload to external API endpoints via universal service
6. **Cleanup**: Maintain session for next task, final cleanup only at end

### Error Recovery Workflows
- **Cache Recovery**: Automatic browser data clearing and re-authentication (Bell specific)
- **Session Recovery**: Automatic session validation and re-login on session loss
- **Upload Retry**: Comprehensive error handling for API uploads with detailed logging
- **File Processing Recovery**: Error handling for ZIP extraction and file processing

## Carrier-Specific Implementations

### Bell Canada (Most Advanced)
**Location**: `web_scrapers/infrastructure/scrapers/bell_scrapers.py`

**Advanced Features**:
- **SMS 2FA Integration**: Complete automated 2FA handling via webhook system
- **Cache Error Detection**: Sophisticated cache corruption detection and automatic recovery
- **Tab Management**: Advanced e-reports navigation with tab switching and cleanup
- **Multiple Report Types**: Cost Overview, Enhanced User Profile Report, Usage Overview
- **File Extraction**: Advanced ZIP handling with UUID-based extraction directories
- **Automatic Recovery**: Browser data clearing and seamless re-authentication on errors

**Authentication Strategy**: Complete 2FA flow with radio button selection, SMS code request, webhook polling, and automatic form completion.

### Telus (Advanced Report Generation)
**Location**: `web_scrapers/infrastructure/scrapers/telus_scrapers.py`

**Sophisticated Features**:
- **Complex Navigation**: Multi-step portal navigation through My Telus interface
- **Advanced Report Generation**: Multiple report types with queue monitoring system
- **Queue Management**: Monitors report generation status ("In Queue" → "Download")
- **Multiple Formats**: CSV, Excel with automatic format selection and fallback mechanisms
- **Billing Period Configuration**: Dynamic period selection based on billing cycle dates
- **Timeout Handling**: Configurable wait times for long-running report generation

**Report Types**: Wireless subscriber charges, usage reports, invoice details, mobility device summaries, data usage reports.

### Other Carriers
**Rogers, AT&T, T-Mobile, Verizon**: Standard implementations with generic authentication flows and basic scraping capabilities, ready for enhancement with carrier-specific features.

## File Processing Architecture

### Advanced ZIP Extraction
**Method**: `_extract_zip_files()` in `ScraperBaseStrategy`

**Features**:
- **UUID-based Directories**: Unique extraction directories to prevent conflicts
- **Flattened Extraction**: Removes nested folder structures for simplified processing
- **Collision Handling**: Automatic file renaming with counter suffixes for duplicates
- **System File Filtering**: Ignores hidden files and system directories
- **Comprehensive Logging**: Detailed extraction reporting and file tracking

### File Mapping and Upload Integration
**Methods**: `_create_file_mapping()`, `_upload_files_to_endpoint()` in base strategies

**Capabilities**:
- **Automatic Mapping**: Converts FileDownloadInfo to API-compatible formats
- **Universal Upload**: All scraper strategies automatically upload files to external API
- **Type Detection**: Automatic upload type detection based on scraper class names
- **Error Handling**: Comprehensive error handling with success/failure tracking

## Environment Configuration

### Required Environment Variables
```env
# API Configuration (Required for file uploads)
API_BASE_URL=https://api.expertel.com
API_TOKEN=your_api_bearer_token

# Browser Configuration (Optional)
BROWSER_TYPE=chrome
BROWSER_HEADLESS=false
BROWSER_SLOW_MO=1000
BROWSER_TIMEOUT=30000
BROWSER_VIEWPORT_WIDTH=1920
BROWSER_VIEWPORT_HEIGHT=1080

# Django Configuration
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///db.sqlite3
```

### Setup Instructions
1. Copy `.env.example` to `.env`
2. Configure API credentials for file upload functionality
3. Adjust browser settings as needed for your environment
4. Start SMS webhook service if using Bell 2FA: `python authenticator_webhook/sms2fa.py`

## Dependencies

### Core Dependencies
- **Django 5.1.4**: Web framework and ORM
- **Pydantic 2.10.3**: Data validation and business entities
- **Playwright 1.53.0**: Browser automation
- **Requests 2.32.0**: HTTP client for API uploads
- **Flask 3.1.0**: 2FA webhook service

### Development Dependencies
- **Black**: Code formatting
- **MyPy**: Type checking
- **isort**: Import sorting
- **pre-commit**: Git hooks

## Usage Examples

### Basic Scraper Execution
```python
from web_scrapers.application.session_manager import SessionManager
from web_scrapers.domain.entities.scraper_factory import ScraperStrategyFactory

# Initialize components
session_manager = SessionManager()
scraper_factory = ScraperStrategyFactory()

# Execute Bell monthly reports scraper
scraper = scraper_factory.create_scraper('bell', 'monthly')
result = scraper.execute(config, billing_cycle, credentials)
```

### File Upload Service Usage
```python
from web_scrapers.infrastructure.services.file_upload_service import FileUploadService

upload_service = FileUploadService()
success = upload_service.upload_files_batch(
    files=downloaded_files,
    billing_cycle=billing_cycle,
    upload_type='monthly'
)
```

## Important Implementation Notes

- **Session Persistence**: Sessions are maintained across multiple scraper executions for efficiency
- **Universal Upload**: All scrapers automatically upload files to external API endpoints
- **Error Recovery**: Advanced error handling with automatic cache clearing and re-authentication
- **2FA Integration**: Bell scrapers support automatic SMS 2FA handling via webhook system
- **File Processing**: Comprehensive ZIP extraction and file mapping for all carriers
- **Configuration**: Extensive environment variable support for all system components
- **Clean Architecture**: Strict separation of concerns with dependency injection throughout
- **Production Ready**: Comprehensive logging, error handling, and resource management

## Technical Documentation

Refer to the following technical documentation files for detailed implementation information:
- `SISTEMA_SCRAPERS_FLUJO_COMPLETO.md`: Complete system flow documentation
- `BELL_SESSION_MANAGEMENT_FLOW.md`: Bell-specific session management details
- `TELUS_SCRAPER_COMPLETE_FLOW.md`: Telus scraper implementation guide
- `PROJECT_TECHNICAL_REFERENCE.md`: Complete technical reference