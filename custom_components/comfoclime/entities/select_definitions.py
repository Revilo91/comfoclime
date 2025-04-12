SELECT_ENTITIES = [
    {
        "key": "temperatureProfile",
        "name": "Temperature Profile",
        "translation_key": "temperature_profile",
        "options": {0: "Comfort", 1: "Power", 2: "Eco"},
    },
    {
        "key": "season.season",
        "name": "Season Mode",
        "translation_key": "season_mode",
        "options": {1: "Heating", 0: "Transition", 2: "Cooling"},
    },
]

PROPERTY_SELECT_ENTITIES = {
    1: [
        {
            "path": "29/1/6",
            "name": "Humidity Comfort Control",
            "translation_key": "humidity_comfort_control",
            "options": {0: "Off", 1: "AutoOnly", 2: "On"},
        },
        {
            "path": "29/1/7",  # X/Y/Z
            "name": "Humidity Protection",
            "translation_key": "humidity_protection",
            "options": {0: "Off", 1: "AutoOnly", 2: "On"},
        },
    ]
}
