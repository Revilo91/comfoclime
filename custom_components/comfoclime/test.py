from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI
import asyncio

async def test_set_property():
    api = ComfoClimeAPI("http://10.0.10.95")  # deine IP
    await api.async_get_uuid()  # nur wenn du die uuid brauchst

    await api.async_set_property_for_device(
        device_uuid="MBE4022d8393df5",  # deine echte UUID
        property_path="29/1/10",
        value=1,
        byte_count=1,
        signed=False,
        faktor=1.0,
    )
    
    # Close the session when done
    await api.close()

asyncio.run(test_set_property())