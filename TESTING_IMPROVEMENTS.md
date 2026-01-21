# Testing Improvements Documentation

This document describes the improvements made to the test suite following the patterns outlined in `PYTHON_BEST_PRACTICES.md` section 8.

## MockComfoClimeAPI

A realistic mock implementation of the ComfoClimeAPI that provides:

### Features

1. **Configurable Responses**: Use `MockAPIResponses` dataclass to customize API responses
2. **Call Tracking**: Automatically records all method calls with arguments
3. **Assertion Helpers**: Built-in methods for verifying API calls

### Usage

```python
from conftest import MockAPIResponses, MockComfoClimeAPI

# Basic usage with defaults
api = MockComfoClimeAPI()

# Custom responses
responses = MockAPIResponses(
    uuid="custom-uuid",
    dashboard_data={"fanSpeed": 3, "season": 1}
)
api = MockComfoClimeAPI(responses)

# Verify calls
await api.async_update_dashboard(fan_speed=2)
api.assert_called_once("async_update_dashboard")
api.assert_called_with("async_update_dashboard", fan_speed=2)

# Get call history
calls = api.get_calls("async_update_dashboard")
for args, kwargs in calls:
    print(f"Called with: {kwargs}")
```

## New Fixtures

### `mock_api_responses`
Returns a `MockAPIResponses` instance that can be customized per test.

### `mock_api`
Returns a `MockComfoClimeAPI` instance using the `mock_api_responses` fixture.
This replaces the old MagicMock-based fixture with proper call tracking.

### `mock_api_with_devices`
Returns a `MockComfoClimeAPI` pre-configured with sample devices:
- ComfoAir Q350 (modelTypeId: 21)
- ComfoClime 200 (modelTypeId: 20)

## Parametrized Tests

### Fan Entity Tests

#### `test_fan_percentage_calculation`
Tests fan percentage calculation for all speed values (0-3).

**Parameters:**
- `speed`: Fan speed (0-3)
- `expected_percentage`: Expected percentage (0, 33, 66, 100)

#### `test_fan_percentage_to_step_conversion`
Tests percentage to step conversion for various input percentages.

**Parameters:**
- `percentage`: Input percentage (0-100)
- `expected_step`: Expected fan step (0-3)

### Climate Entity Tests

#### `test_climate_hvac_mode_variations`
Tests HVAC mode for different season and standby combinations.

**Parameters:**
- `season`: Season value (0=transition, 1=heating, 2=cooling)
- `hpStandby`: Standby state (True/False)
- `expected_mode`: Expected HVACMode

#### `test_climate_hvac_action_variations`
Tests HVAC action based on heat pump status.

**Parameters:**
- `heatPumpStatus`: Heat pump status bits
- `expected_action`: Expected HVACAction

#### `test_climate_preset_mode_variations`
Tests preset modes for different temperature profiles.

**Parameters:**
- `temperatureProfile`: Profile ID (0=comfort, 1=boost, 2=eco)
- `setPointTemperature`: Manual temperature (None for auto mode)
- `expected_preset`: Expected preset constant

#### `test_climate_scenario_modes`
Tests scenario mode activation.

**Parameters:**
- `scenario_preset`: Preset name ("cooking", "party", "away", "scenario_boost")
- `expected_scenario_id`: Expected scenario ID (4, 5, 7, 8)

## Benefits

1. **Better Test Isolation**: Each test gets a fresh mock with no state leakage
2. **Clearer Test Intent**: Parametrized tests clearly show what values are being tested
3. **Easier Debugging**: Call history makes it easy to see what happened
4. **More Coverage**: Parametrized tests cover more cases with less code
5. **Maintainability**: Adding new test cases is as simple as adding a tuple to the parameters

## Migration Guide

### Before (Old Pattern)
```python
@pytest.fixture
def mock_api():
    api = MagicMock()
    api.async_update_dashboard = AsyncMock()
    return api

async def test_fan_set_percentage(mock_api):
    await fan.async_set_percentage(66)
    mock_api.async_update_dashboard.assert_called_once_with(fan_speed=2)
```

### After (New Pattern)
```python
# Fixture automatically provided by conftest.py
@pytest.mark.parametrize("percentage,expected_step", [(66, 2), (33, 1), (100, 3)])
async def test_fan_percentage_to_step_conversion(
    percentage, expected_step, mock_api
):
    await fan.async_set_percentage(percentage)
    calls = mock_api.get_calls("async_update_dashboard")
    _, kwargs = calls[0]
    assert kwargs["fan_speed"] == expected_step
```

## Running Tests

While the full test suite requires Home Assistant dependencies, the mock infrastructure is validated independently. To add new parametrized tests:

1. Add parameters to the `@pytest.mark.parametrize` decorator
2. Use descriptive `ids` for each test case
3. Use `mock_api.get_calls()` to verify API interactions
4. Clear call history with `mock_api._call_history.clear()` if needed between checks

## Future Improvements

- [ ] Add more parametrized tests for sensor entities
- [ ] Add parametrized tests for switch entities
- [ ] Add integration tests using MockComfoClimeAPI
- [ ] Add performance benchmarks for parametrized tests
