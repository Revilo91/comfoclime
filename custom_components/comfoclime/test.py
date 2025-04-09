from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI
import asyncio

async def test_set_property():
    api = ComfoClimeAPI("http://10.0.10.95")  # deine IP
    await api.async_get_uuid(None)  # nur wenn du die uuid brauchst

    await api.async_set_property_for_device(
        hass=None,  # Wenn du es im echten HA testest: echten Hass übergeben
        device_uuid="MBE4022d8393df5",  # deine echte UUID
        property_path="29/1/10",
        value=1,
        byte_count=1,
        signed=False,
        faktor=1.0,
    )

asyncio.run(test_set_property())