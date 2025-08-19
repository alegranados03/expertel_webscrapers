# Detailed Execution Flow Analysis - Scraper System

## Overview

This document provides a comprehensive, step-by-step analysis of the execution flow from `main()` through all function calls and bifurcations at maximum depth. This analysis covers the complete scraper job processing system with `available_at` field support.

## 1. Entry Point - `main()` Function

**Location**: `main.py:172-188`

```python
def main():
    setup_logging(log_level="INFO")
    logger = get_logger("main")
    
    try:
        logger.info("Starting ScraperJob processor")
        processor = ScraperJobProcessor()
        processor.execute_available_scrapers()
        logger.info("ScraperJob processor completed successfully")
    except Exception as e:
        logger.error(f"Error in main processor: {str(e)}", exc_info=True)
```

### 1.1 ScraperJobProcessor Initialization

**Location**: `main.py:25-29`

```python
def __init__(self):
    self.logger = get_logger("scraper_job_processor")
    self.scraper_job_service = ScraperJobService()
    self.session_manager = SessionManager()
    self.scraper_factory = ScraperStrategyFactory()
```

**Component Initialization**:
- **ScraperJobService**: Initializes 9 repositories for Django→Pydantic conversion
- **SessionManager**: Browser automation and authentication management
- **ScraperStrategyFactory**: Dynamic scraper strategy creation

## 2. Main Execution Flow - `execute_available_scrapers()`

**Location**: `main.py:138-170`

```python
def execute_available_scrapers(self) -> None:
    self.logger.info("Fetching available scraper jobs...")
    
    # Display statistics
    self.log_statistics()
    
    # Get available jobs with complete context
    available_jobs = self.scraper_job_service.get_available_jobs_with_complete_context()
    
    if not available_jobs:
        self.logger.info("No scraper jobs available for execution at this time")
        return
    
    # Process each job
    for i, job_context in enumerate(available_jobs, 1):
        success = self.process_scraper_job(job_context, i, len(available_jobs))
        # Track success/failure counts
```

## 3. Statistics Logging Flow - `log_statistics()`

**Location**: `main.py:31-38`

```python
def log_statistics(self) -> None:
    stats = self.scraper_job_service.get_scraper_statistics()
    self.logger.info(
        f"Scraper statistics: {stats.available_now} available now, "
        f"{stats.future_scheduled} scheduled for future, "
        f"{stats.total_pending} total pending"
    )
```

### 3.1 Deep Analysis of `get_scraper_statistics()`

**Location**: `web_scrapers/application/scraper_job_service.py:178-207`

**Database Queries Executed**:

1. **Total Pending Count**:
   ```python
   total_pending = DjangoScraperJob.objects.filter(status=ScraperJobStatus.PENDING).count()
   ```
   **SQL**: `SELECT COUNT(*) FROM scraper_job WHERE status = 'PENDING'`

2. **Available Now Count**:
   ```python
   available_now = DjangoScraperJob.objects.filter(
       status=ScraperJobStatus.PENDING, available_at__lte=current_time
   ).count()
   ```
   **SQL**: `SELECT COUNT(*) FROM scraper_job WHERE status = 'PENDING' AND available_at <= '2025-08-18 XX:XX:XX'`

3. **Future Scheduled Count**:
   ```python
   future_scheduled = DjangoScraperJob.objects.filter(
       status=ScraperJobStatus.PENDING, available_at__gt=current_time
   ).count()
   ```
   **SQL**: `SELECT COUNT(*) FROM scraper_job WHERE status = 'PENDING' AND available_at > '2025-08-18 XX:XX:XX'`

4. **NULL Available Count**:
   ```python
   null_available = DjangoScraperJob.objects.filter(
       status=ScraperJobStatus.PENDING, available_at__isnull=True
   ).count()
   ```
   **SQL**: `SELECT COUNT(*) FROM scraper_job WHERE status = 'PENDING' AND available_at IS NULL`

**Return**: `ScraperStatistics` Pydantic model with all counts and timestamp

## 4. Deep Analysis of `get_available_jobs_with_complete_context()` Flow

**Location**: `web_scrapers/application/scraper_job_service.py:161`

```python
def get_available_jobs_with_complete_context(self, include_null_available_at: bool = True) -> List[ScraperJobCompleteContext]:
```

### 4.1 Call to `get_available_scraper_jobs()`

**Location**: `scraper_job_service.py:174`

```python
available_jobs = self.get_available_scraper_jobs(include_null_available_at)
```

**Deep Flow in `get_available_scraper_jobs()`**:

1. **Timezone Setup**: `current_time = timezone.now()` - Gets Django timezone-aware current time
2. **Query Filter Construction**: 
   ```python
   query_filter = Q(status=ScraperJobStatus.PENDING)
   if include_null_available_at:
       query_filter &= Q(available_at__lte=current_time) | Q(available_at__isnull=True)
   ```
3. **Database Query**: `DjangoScraperJob.objects.filter(query_filter).order_by("available_at")`
   - **SQL Generated**: `SELECT * FROM scraper_job WHERE status = 'PENDING' AND (available_at <= '2025-08-18 XX:XX:XX' OR available_at IS NULL) ORDER BY available_at`
4. **Repository Conversion**: List comprehension with `self.scraper_job_repo.to_entity(job)` for each Django model

### 4.2 Iterative `get_scraper_job_with_complete_context()` Calls

**Location**: `scraper_job_service.py:176`

```python
return [self.get_scraper_job_with_complete_context(job.id) for job in available_jobs]
```

**For EACH available job, this triggers the complete context building flow:**

#### 4.2.1 Complex Django Query with Relationships

**Location**: `scraper_job_service.py:100-110`

```python
django_job = DjangoScraperJob.objects.select_related(
    "billing_cycle",
    "scraper_config", 
    "scraper_config__account",
    "scraper_config__credential",
    "scraper_config__carrier",
    "billing_cycle__account",
    "billing_cycle__account__workspace", 
    "billing_cycle__account__workspace__client",
    "billing_cycle__account__carrier",
).get(id=scraper_job_id)
```

**Generated SQL JOIN Query** (approximate):
```sql
SELECT scraper_job.*, billing_cycle.*, scraper_config.*, account.*, 
       credential.*, carrier.*, workspace.*, client.*
FROM scraper_job 
JOIN billing_cycle ON scraper_job.billing_cycle_id = billing_cycle.id
JOIN scraper_config ON scraper_job.scraper_config_id = scraper_config.id
JOIN account ON scraper_config.account_id = account.id
JOIN carrier_portal_credential ON scraper_config.credential_id = credential.id
JOIN carrier ON scraper_config.carrier_id = carrier.id
JOIN workspace ON account.workspace_id = workspace.id  
JOIN client ON workspace.client_id = client.id
WHERE scraper_job.id = %s
```

#### 4.2.2 Repository Conversions (Django → Pydantic)

**Location**: `scraper_job_service.py:112-120`

Each line triggers a repository `to_entity()` method:
```python
scraper_job = self.scraper_job_repo.to_entity(django_job)           # ScraperJobRepository.to_entity()
scraper_config = self.scraper_config_repo.to_entity(django_job.scraper_config)  # ScraperConfigRepository.to_entity()  
billing_cycle = self.billing_cycle_repo.to_entity(django_job.billing_cycle)     # BillingCycleRepository.to_entity()
credential = self.credential_repo.to_entity(django_job.scraper_config.credential) # CarrierPortalCredentialRepository.to_entity()
account = self.account_repo.to_entity(django_job.billing_cycle.account)         # AccountRepository.to_entity()
carrier = self.carrier_repo.to_entity(django_job.scraper_config.carrier)       # CarrierRepository.to_entity()
workspace = self.workspace_repo.to_entity(django_job.billing_cycle.account.workspace) # WorkspaceRepository.to_entity()
client = self.client_repo.to_entity(django_job.billing_cycle.account.workspace.client) # ClientRepository.to_entity()
```

#### 4.2.3 Related Files Collection

**Location**: `scraper_job_service.py:122-127`

Additional database queries for file relationships:
```python
billing_cycle_files_django = django_job.billing_cycle.billing_cycle_files.select_related("carrier_report").all()
daily_usage_files_django = django_job.billing_cycle.daily_usage_files.all()  
pdf_files_django = django_job.billing_cycle.pdf_files.all()
```

**Generated SQL Queries**:
```sql
SELECT * FROM billing_cycle_file JOIN carrier_report ON billing_cycle_file.carrier_report_id = carrier_report.id WHERE billing_cycle_id = %s
SELECT * FROM billing_cycle_daily_usage_file WHERE billing_cycle_id = %s  
SELECT * FROM billing_cycle_pdf_file WHERE billing_cycle_id = %s
```

#### 4.2.4 File Collections Conversion Loop

**Location**: `scraper_job_service.py:129-141`

```python
billing_cycle_files = []
for file_django in billing_cycle_files_django:
    file_pydantic = self.billing_cycle_file_repo.to_entity(file_django)  # Repository conversion
    if hasattr(file_django, "carrier_report") and file_django.carrier_report:
        file_pydantic.carrier_report = self.carrier_report_repo.to_entity(file_django.carrier_report)  # Additional repository conversion
    billing_cycle_files.append(file_pydantic)

daily_usage_files = [self.daily_usage_file_repo.to_entity(file_django) for file_django in daily_usage_files_django]
pdf_files = [self.pdf_file_repo.to_entity(file_django) for file_django in pdf_files_django]
```

#### 4.2.5 Complete Structure Assembly

**Location**: `scraper_job_service.py:143-147`

```python
billing_cycle.account = account                           # Attach Account to BillingCycle
billing_cycle.billing_cycle_files = billing_cycle_files   # Attach converted files list
billing_cycle.daily_usage_files = daily_usage_files       # Attach daily usage files  
billing_cycle.pdf_files = pdf_files                       # Attach PDF files
```

#### 4.2.6 Final Pydantic Model Creation

**Location**: `scraper_job_service.py:149-159`

```python
return ScraperJobCompleteContext(
    scraper_job=scraper_job,        # All Pydantic entities
    scraper_config=scraper_config,  
    billing_cycle=billing_cycle,    # Complete with all attached files
    credential=credential,
    account=account,
    carrier=carrier, 
    workspace=workspace,
    client=client,
)
```

## 5. Main Processing Loop Analysis - `process_scraper_job()`

**Location**: `main.py:158-159`

```python
for i, job_context in enumerate(available_jobs, 1):
    success = self.process_scraper_job(job_context, i, len(available_jobs))
```

### 5.1 Entity Extraction from Context

**Location**: `main.py:52-58`

```python
scraper_job = job_context.scraper_job      # Extract Pydantic ScraperJob
scraper_config = job_context.scraper_config # Extract Pydantic ScraperConfig  
billing_cycle = job_context.billing_cycle   # Extract complete BillingCycle with files
credential = job_context.credential         # Extract CarrierPortalCredential
account = job_context.account              # Extract Account
carrier = job_context.carrier              # Extract Carrier
```

### 5.2 Database Status Update

**Location**: `main.py:68-73`

```python
self.scraper_job_service.update_scraper_job_status(
    scraper_job.id,
    ScraperJobStatus.RUNNING, 
    f"Starting processing - Carrier: {carrier.name}, Type: {scraper_job.type}",
)
```

**Deep Flow in `update_scraper_job_status()`**:

**Location**: `scraper_job_service.py:220-230`

1. **Django Query**: `django_job = DjangoScraperJob.objects.get(id=scraper_job_id)`
2. **Status Update**: `django_job.status = status`
3. **Log Append**: Concatenates new log message with timestamp
4. **Completion Timestamp**: Sets `completed_at` for SUCCESS/ERROR statuses
5. **Database Save**: `django_job.save()` - Commits to database

### 5.3 Carrier Enum Mapping

**Location**: `main.py:76-92`

```python
carrier_enum_map = {
    "bell canada": CarrierEnum.BELL,
    "bell": CarrierEnum.BELL, 
    "telus": CarrierEnum.TELUS,
    "rogers": CarrierEnum.ROGERS,
    "at&t": CarrierEnum.ATT,
    "att": CarrierEnum.ATT,
    "t-mobile": CarrierEnum.TMOBILE,
    "tmobile": CarrierEnum.TMOBILE, 
    "verizon": CarrierEnum.VERIZON,
}
carrier_enum = carrier_enum_map.get(carrier.name.lower(), CarrierEnum.BELL)
credentials = Credentials(id=credential.id, username=credential.username, password=credential.password, carrier=carrier_enum)
```

### 5.4 Session Management Flow

**Location**: `main.py:94-101`

```python
browser_wrapper = self.session_manager.get_browser_wrapper()
if not browser_wrapper:
    login_success = self.session_manager.login(credentials)
    if not login_success:
        raise Exception("Failed to login and get browser wrapper")
    browser_wrapper = self.session_manager.get_browser_wrapper()
```

**Deep SessionManager Flow** (referencing `web_scrapers/application/session_manager.py`):

1. **get_browser_wrapper()**: Checks if `self._browser_wrapper` exists and is valid
2. **login(credentials)**: Complex authentication flow:
   - Checks existing session compatibility (same carrier + credentials)
   - Handles logout if credentials differ  
   - Creates new browser instance via factory
   - Executes carrier-specific authentication strategy
   - Stores session state (credentials, carrier, browser_wrapper)

### 5.5 Scraper Factory and Strategy Creation

**Location**: `main.py:103-106`

```python
scraper_strategy = self.scraper_factory.create_scraper(
    carrier=carrier_enum, scraper_type=scraper_job.type, browser_wrapper=browser_wrapper
)
```

**Deep Factory Flow** (referencing `web_scrapers/domain/entities/scraper_factory.py`):

1. **Strategy Selection**: Maps carrier + scraper_type to specific strategy class
2. **Dynamic Import**: Imports carrier-specific scraper module
3. **Class Instantiation**: Creates strategy instance with browser_wrapper
4. **Returns**: Concrete strategy (e.g., `BellMonthlyReportsScraperStrategy`)

### 5.6 Scraper Execution - The Core Process

**Location**: `main.py:111`

```python
result = scraper_strategy.execute(scraper_config, billing_cycle, credentials)
```

**Deep Strategy Execution Flow** (referencing `web_scrapers/domain/entities/scraper_strategies.py`):

Each strategy follows the **Template Method Pattern**:

1. **_find_files_section()**: Carrier-specific navigation to files area
2. **_download_files()**: Downloads files, returns `List[FileDownloadInfo]`
3. **_extract_zip_files()**: Handles ZIP extraction with UUID directories
4. **_create_file_mapping()**: Converts to `List[FileMappingInfo]`
5. **_upload_files_to_endpoint()**: Calls `FileUploadService` for external API upload

#### 5.6.1 Template Method Pattern Detail

**Location**: `web_scrapers/domain/entities/scraper_strategies.py:195-214`

```python
def execute(self, config: ScraperConfig, billing_cycle: BillingCycle, credentials: Credentials) -> ScraperResult:
    try:
        files_section = self._find_files_section(config, billing_cycle)
        if not files_section:
            return ScraperResult(False, error="Could not find files section")

        downloaded_files = self._download_files(files_section, config, billing_cycle)
        if not downloaded_files:
            return ScraperResult(False, error="Could not download files")

        upload_result = self._upload_files_to_endpoint(downloaded_files, config, billing_cycle)
        if not upload_result:
            return ScraperResult(False, error="Error sending files to external endpoint")

        return ScraperResult(
            True, f"Processed {len(downloaded_files)} files", self._create_file_mapping(downloaded_files)
        )
    except Exception as e:
        return ScraperResult(False, error=str(e))
```

#### 5.6.2 File Upload Service Flow

**Location**: `scraper_strategies.py:162-178`

```python
def _upload_files_to_endpoint(self, files: List[FileDownloadInfo], config: ScraperConfig, billing_cycle: BillingCycle) -> bool:
    try:
        upload_service = FileUploadService()
        upload_type = self._get_upload_type()  # Determines: monthly/daily_usage/pdf_invoice
        
        return upload_service.upload_files_batch(
            files=files, billing_cycle=billing_cycle, upload_type=upload_type, additional_data=None
        )
    except Exception as e:
        self.logger.error(f"Error uploading files: {str(e)}")
        return False
```

**FileUploadService API Integration**:
- **Monthly Reports**: `/api/v1/accounts/billing-cycles/{cycle_id}/files/{file_id}/upload-file/`
- **Daily Usage**: `/api/v1/accounts/billing-cycles/{cycle_id}/daily-usage/`
- **PDF Invoice**: `/api/v1/accounts/billing-cycles/{cycle_id}/pdf-invoice/`

### 5.7 Result Processing and Final Status Update

**Location**: `main.py:113-125`

```python
if result.success:
    self.logger.info(f"Files processed: {len(result.files)}")
    self.scraper_job_service.update_scraper_job_status(
        scraper_job.id, ScraperJobStatus.SUCCESS, f"Scraper executed successfully: {result.message}"
    )
else:
    self.logger.error(f"Scraper execution failed: {result.error}")
    self.scraper_job_service.update_scraper_job_status(
        scraper_job.id, ScraperJobStatus.ERROR, f"Scraper execution failed: {result.error}"
    )
```

## 6. Advanced File Processing Flows

### 6.1 ZIP Extraction Process

**Location**: `scraper_strategies.py:66-161`

```python
def _extract_zip_files(self, zip_file_path: str, extract_to_dir: Optional[str] = None) -> List[str]:
```

**Deep ZIP Processing Flow**:

1. **File Validation**: 
   - `os.path.exists(zip_file_path)` - Verify file exists
   - `zipfile.is_zipfile(zip_file_path)` - Validate ZIP format

2. **UUID Directory Creation**:
   ```python
   zip_basename = os.path.splitext(os.path.basename(zip_file_path))[0]
   unique_id = str(uuid.uuid4())[:8]
   extract_to_dir = os.path.join(os.path.dirname(zip_file_path), f"{zip_basename}_extracted_{unique_id}")
   ```

3. **Flattened Extraction Loop**:
   ```python
   for file_name in file_list:
       if not file_name.endswith("/"):  # Only files, not directories
           base_filename = os.path.basename(file_name)  # Flatten structure
           if base_filename and not base_filename.startswith("."):  # Filter system files
               # Handle name collisions with counter
               # Extract to first level only
   ```

4. **Collision Handling**:
   ```python
   counter = 1
   while os.path.exists(flattened_file_path):
       name, ext = os.path.splitext(base_filename)
       flattened_file_path = os.path.join(extract_to_dir, f"{name}_{counter}{ext}")
       counter += 1
   ```

### 6.2 File Mapping Creation

**Location**: `scraper_strategies.py:46-64`

```python
def _create_file_mapping(self, downloaded_files: List[FileDownloadInfo]) -> List[FileMappingInfo]:
    return [
        FileMappingInfo(
            file_id=file_info.file_id,
            file_name=file_info.file_name,
            file_path=file_info.file_path,
            download_url=file_info.download_url,
            billing_cycle_file_id=file_info.billing_cycle_file.id if file_info.billing_cycle_file else None,
            carrier_report_name=(
                file_info.billing_cycle_file.carrier_report.name
                if (file_info.billing_cycle_file and file_info.billing_cycle_file.carrier_report)
                else None
            ),
            daily_usage_file_id=file_info.daily_usage_file.id if file_info.daily_usage_file else None,
            pdf_file_id=file_info.pdf_file.id if file_info.pdf_file else None,
        )
        for file_info in downloaded_files
    ]
```

## 7. Summary of Complete Flow Bifurcations

### Key Decision Points:

1. **Statistics vs Execution**: `log_statistics()` vs `get_available_jobs_with_complete_context()`
2. **Job Availability**: NULL `available_at` inclusion logic
3. **Session State**: Existing browser_wrapper vs new login required
4. **Scraper Result**: Success vs Error path with different status updates
5. **File Processing**: ZIP extraction vs direct file handling
6. **Upload Integration**: External API success vs failure handling

### Database Interaction Points:

- **Statistics queries**: 4 separate COUNT queries
- **Available jobs query**: Complex JOIN with `available_at` filtering
- **Complete context query**: 8-10 JOINs per job
- **File relationship queries**: 3 additional queries per job
- **Status updates**: 2 database writes per job minimum

### Repository Conversion Points:

- Every Django model → Pydantic entity conversion
- File collections with nested carrier_report conversions
- Complete structure assembly with manual attachment

### Error Handling Bifurcations:

1. **No Available Jobs**: Early return with log message
2. **Login Failure**: Exception raised, job marked as ERROR
3. **Scraper Execution Failure**: ScraperResult.success = False, job marked as ERROR
4. **File Processing Failure**: Individual file errors logged, overall result may still succeed
5. **Upload Failure**: External API errors, job marked as ERROR

## 8. Performance Considerations

### Database Query Optimization:

- **select_related()**: Used for single JOIN operations to reduce N+1 queries
- **Prefetch optimization**: File relationships loaded with additional queries
- **Index usage**: `available_at` field has database index for efficient filtering

### Memory Management:

- **Iterative processing**: Jobs processed one at a time to limit memory usage
- **Repository pattern**: Clean conversion between Django ORM and Pydantic models
- **Session reuse**: Browser sessions maintained across multiple jobs for efficiency

### Scalability Points:

- **Batch processing**: Multiple jobs processed in single execution
- **Session management**: Intelligent session reuse based on carrier and credentials
- **File upload**: External API integration with batch upload capabilities

This represents the **complete execution flow at maximum depth** showing every function call, database query, repository conversion, and decision point in the scraper system.