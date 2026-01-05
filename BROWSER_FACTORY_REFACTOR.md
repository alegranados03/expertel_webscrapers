# Browser Factory Refactor Strategy

## Current Flow (Too Many Layers)

```
SessionManager
    ↓ browser_manager.get_browser(browser_type)
BrowserManager (singleton)
    ↓ factory.create_full_setup(browser_type)
BrowserDriverFactory
    ↓ create_browser() → get_default_browser_type() → reads BROWSER_TYPE
    ↓ create_context()
DriverBuilder (Chrome/Firefox/Edge/Safari)
    ↓ get_browser() → pw.chromium.launch()
Playwright
```

## Problems Identified

### 1. BrowserManager is Unnecessary
- It's just a singleton wrapper over `BrowserDriverFactory`
- `BrowserDriverFactory` already handles everything
- Extra layer with no added value

### 2. Double Configuration Reading
- `get_browser_options()` reads env variables
- `get_default_browser_type()` reads `BROWSER_TYPE`
- Drivers have hardcoded args duplicated

### 3. Duplicated Args in Drivers (`drivers.py`)

```python
# In get_browser() - hardcoded (lines 92-102)
launch_options["args"] += ["--no-sandbox", "--disable-web-security", ...]

# In set_driver_options() - dynamic (lines 106-125)
if kwargs.get("no_sandbox", False):
    chrome_args.append("--no-sandbox")
```

The same args are added twice if `no_sandbox=True` is passed.

### 4. browser_type Parameter Can Be Ignored
- If `SessionManager(browser_type=Navigators.FIREFOX)` → works
- If `browser_type=None` → reads from env (expected)
- But the flow is confusing

## Proposed Simplified Flow

```
SessionManager
    ↓ BrowserDriverFactory.create_full_setup(browser_type)
BrowserDriverFactory (singleton)
    ↓ create_browser() + create_context()
DriverBuilder
    ↓ get_browser()
Playwright
```

## Action Items

### 1. Remove BrowserManager
- Delete `BrowserManager` class
- Use `BrowserDriverFactory` directly in `SessionManager`
- Make `BrowserDriverFactory` a proper singleton if needed

### 2. Clean Up Driver Args
- Remove hardcoded args from `get_browser()` methods
- Keep only dynamic args in `set_driver_options()`
- Or vice versa - pick one approach

### 3. Consolidate Configuration
- Single place to read all browser config from env
- Pass config down the chain, don't re-read

### 4. Files to Modify
- `web_scrapers/infrastructure/playwright/browser_factory.py`
- `web_scrapers/infrastructure/playwright/drivers.py`
- `web_scrapers/application/session_manager.py`

## Priority
LOW - Current implementation works, this is optimization/cleanup.
