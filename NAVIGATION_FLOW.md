# Config Flow Navigation Structure

## Visual Navigation Map

```
┌─────────────────────────────────────────────────────────────┐
│                     MAIN MENU (init)                        │
│  ⚙️ Allgemeine Einstellungen → general                      │
│  📦 Entity Einstellungen → entities_menu                     │
│  💾 Speichern & Beenden → save_and_exit [SAVES & EXITS]    │
└─────────────────────────────────────────────────────────────┘
                    │                     │
                    │                     │
        ┌───────────┘                     └──────────────┐
        │                                                 │
        ▼                                                 ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│   GENERAL MENU (general)     │    │ ENTITIES MENU (entities_menu)│
│  🔍 Diagnostics → form       │    │  📊 Sensors → menu           │
│  ⏱️ Timeouts → form          │    │  🔌 Switches → form          │
│  🔄 Polling → form           │    │  🔢 Numbers → form           │
│  🔁 Rate Limiting → form     │    │  📝 Selects → form           │
│  ⬅️ Zurück → init            │    │  ⬅️ Zurück → init            │
└──────────────────────────────┘    └──────────────────────────────┘
        │ (forms return here)                  │
        │                                      │
        ▼                              ┌───────┴──────────┐
   [Updates pending_changes]           │                  │
                                       ▼                  ▼
                        ┌─────────────────────────┐  [Other entity forms]
                        │ SENSORS MENU (sensors)  │   Update pending_changes
                        │  📈 Dashboard → form    │   Return to entities_menu
                        │  🌡️ Thermal → form      │
                        │  ⏱️ Monitoring → form   │
                        │  📡 Telemetry → form    │
                        │  🔧 Properties → form   │
                        │  📋 Definition → form   │
                        │  🔍 Access Track → form │
                        │  ⬅️ Zurück → entities   │
                        └─────────────────────────┘
                               │ (forms return here)
                               │
                               ▼
                        [Updates pending_changes]
```

## Navigation Rules

### From Any Menu
- ⬅️ **Back Button**: Returns to parent menu
- 📝 **Form Submit**: Updates `pending_changes`, returns to current menu
- 💾 **Save & Exit**: Persists all `pending_changes`, exits config flow

### Form Behavior
1. User fills out form
2. Submits form
3. Form calls `_update_pending(user_input)`
4. Form returns to parent menu via `await self.async_step_<parent>()`
5. No data is saved yet

### Saving Changes
Only the "💾 Speichern & Beenden" option saves data:
```python
async def async_step_save_and_exit(self, user_input):
    new_options = {**self.entry.options, **self._pending_changes}
    return self.async_create_entry(title="", data=new_options)
```

## Example User Journey

### Scenario: User wants to change timeouts and enable a sensor

```
1. Start at MAIN MENU
   ↓ Select "⚙️ Allgemeine Einstellungen"

2. At GENERAL MENU
   ↓ Select "⏱️ Timeouts"

3. At TIMEOUT FORM
   ↓ Change read_timeout to 20
   ↓ Submit form
   → pending_changes = {read_timeout: 20}
   → Returns to GENERAL MENU

4. At GENERAL MENU
   ↓ Select "⬅️ Zurück zum Hauptmenü"

5. Back at MAIN MENU
   ↓ Select "📦 Entity Einstellungen"

6. At ENTITIES MENU
   ↓ Select "📊 Sensors"

7. At SENSORS MENU
   ↓ Select "📈 Dashboard Sensors"

8. At DASHBOARD FORM
   ↓ Enable "indoor_temperature" sensor
   ↓ Submit form
   → pending_changes = {read_timeout: 20, enabled_dashboard: [...]}
   → Returns to SENSORS MENU

9. At SENSORS MENU
   ↓ Select "⬅️ Zurück zu Entity Settings"

10. At ENTITIES MENU
    ↓ Select "⬅️ Zurück zum Hauptmenü"

11. Back at MAIN MENU
    ↓ Select "💾 Speichern & Beenden"

12. SAVED & EXITED ✅
    → All changes persisted to entry.options
```

## Key Points

✅ **Multiple Changes**: User changed 2 different settings  
✅ **No Accidental Saves**: Changes stayed in pending_changes  
✅ **Full Navigation**: User navigated back multiple times  
✅ **Explicit Save**: Only saved when user chose "Speichern & Beenden"  

## Code Flow

```python
# Initial state
pending_changes = {}

# User changes timeout
pending_changes = {read_timeout: 20}

# User enables sensor
pending_changes = {read_timeout: 20, enabled_dashboard: [...]}

# User clicks "Speichern & Beenden"
new_options = {**entry.options, **pending_changes}
# -> Saves merged options to Home Assistant
```

## Benefits

1. **No accidental data loss**: Changes are staged
2. **Review before commit**: Can make multiple changes
3. **Natural navigation**: Back buttons work as expected
4. **Clear intent**: Must explicitly save to persist
