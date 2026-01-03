# Fix for asyncio.Lock Deadlock in UUID Retrieval

## Problem

The ComfoClime Home Assistant integration was experiencing a bootstrap timeout error:

```
asyncio.exceptions.CancelledError: Global task timeout: Bootstrap stage 2 timeout
```

The error occurred during setup when calling `api.async_get_connected_devices()`.

## Root Cause

The issue was an **asyncio.Lock deadlock** caused by attempting to acquire the same lock twice:

1. `async_get_connected_devices()` uses `@api_get` decorator with `requires_uuid=True`
2. The `@api_get` decorator acquires `self._request_lock` (line 80 of api_decorators.py)
3. If UUID is not set, it calls `_async_get_uuid_internal()` (line 85)
4. `_async_get_uuid_internal()` ALSO had `@api_get` decorator which tried to acquire the same lock
5. **Result**: Deadlock because asyncio.Lock is NOT reentrant

## Solution

### Changes Made

**1. Refactored `_async_get_uuid_internal()` in `comfoclime_api.py`:**
   - Removed the `@api_get` decorator
   - Made it a simple async method that performs a direct HTTP GET request
   - It no longer tries to acquire the lock (assumes it's already held by caller)

**2. Updated `async_get_uuid()` in `comfoclime_api.py`:**
   - Added `@with_request_lock` decorator to properly acquire the lock
   - Added rate limiting via `_wait_for_rate_limit()`
   - Calls the internal method after acquiring lock

**3. Fixed `api_put` decorator in `api_decorators.py`:**
   - Changed to call `async_get_uuid()` instead of `_async_get_uuid_internal()`
   - This ensures proper lock acquisition when UUID needs to be fetched

### Code Flow After Fix

**Scenario 1: UUID needed in api_get context (e.g., async_get_connected_devices)**
```
api_get decorator (line 80) → acquires lock
  → checks requires_uuid (line 84-85)
  → calls _async_get_uuid_internal() [NO lock acquisition, already held]
  → makes GET /monitoring/ping
  → sets uuid
  → continues with original request
  → releases lock
```

**Scenario 2: UUID needed in api_put context**
```
api_put decorator (line 162-163)
  → checks requires_uuid
  → calls async_get_uuid() [acquires lock via @with_request_lock]
    → waits for rate limit
    → calls _async_get_uuid_internal() [NO lock acquisition]
    → releases lock
  → continues with PUT request
```

**Scenario 3: Direct call to async_get_uuid()**
```
async_get_uuid() [acquires lock via @with_request_lock]
  → waits for rate limit
  → calls _async_get_uuid_internal() [NO lock acquisition]
  → releases lock
```

## Testing

Created tests to verify:
1. asyncio.Lock deadlock is resolved (demonstrated with simplified test)
2. UUID retrieval works in all contexts
3. Both public and internal methods work correctly

## Impact

- **Minimal changes**: Only modified UUID retrieval logic
- **No breaking changes**: Public API remains the same
- **Fixes critical bug**: Integration now loads successfully without timeout
- **Maintains thread safety**: Proper lock handling throughout

## Files Changed

- `custom_components/comfoclime/comfoclime_api.py`: Refactored UUID retrieval methods
- `custom_components/comfoclime/api_decorators.py`: Fixed api_put to use public method
- `tests/test_api_decorators.py`: Updated test mocks
- `.gitignore`: Added .venv to exclusions
