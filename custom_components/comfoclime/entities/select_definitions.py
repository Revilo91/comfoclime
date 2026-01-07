SELECT_ENTITIES = [
    {
        "key": "temperatureProfile",
        "name": "Temperature Profile",
        "translation_key": "temperature_profile",
        "options": {0: "comfort", 1: "power", 2: "eco"},
    },
    {
        "key": "season.season",
        "name": "Season Mode",
        "translation_key": "season_mode",
        "options": {1: "heating", 0: "transition", 2: "cooling"},
    },
]

PROPERTY_SELECT_ENTITIES = {
    1: [
        {
            "path": "29/1/4",
            "name": "Passive Temperature",
            "translation_key": "passive_temperature",
            "options": {0: "off", 1: "autoonly", 2: "on"},
        },
        {
            "path": "29/1/6",
            "name": "Humidity Comfort Control",
            "translation_key": "humidity_comfort_control",
            "options": {0: "off", 1: "autoonly", 2: "on"},
        },
        {
            "path": "29/1/7",
            "name": "Humidity Protection",
            "translation_key": "humidity_protection",
            "options": {0: "off", 1: "autoonly", 2: "on"},
        },
        {
            "path": "29/1/8",
            "name": "Temperature Profile Modus",
            "translation_key": "temperature_profile_modus",
            "options": {0: "adaptiv", 1: "fixed value"},
        },
        {
            "path": "29/1/14",
            "name": "Temp Passively Preset",
            "translation_key": "temp_passively_preset",
            "options": {0: "slow", 1: "medium", 2: "fast"},
        },
    ]
}
