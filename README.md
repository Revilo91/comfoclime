# comfoclime
HomeAssistant integration of Zehnder ComfoClime

## Features
ComfoClime is a HVAC solution as additional device for the ComfoAir Q series. It comes with its own app and an propietary JSON API. The ComfoClime unit is connected to the local network via WiFi/WLAN, the API is available only local via HTTP requests without authentication. This integration currently offers:
* reading the dashboard data similar to the official app (sensors)
* writing the active temperature profile (select)
* setting the ventilation fan speed (fan)
* reading and writing the thermalprofile (sensors, selects and numbers)
* reading additional telemetry values of all connected devices (sensors; known already from ComfoConnect integration)
* arranging telemetry and property values into different devices
* reading additional property values of all connected devices (sensors)
* writing additional property values of all connected devices (service, numbers)
* configuration via config flow by host/ip
* locals in english and german

All reverse engineered knowledge about the API is found here: https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md
Feel free to extend!

## Current ToDo / development
There are many more telemetry and property values, that make sense to be offered by the integration. For now my primary goal is to control the ComfoClime unit, as I already integrated the ComfoAirQ via KNX. Only a few sensors, that are not available via KNX, are integrated.

I'm not a python native speaker, so this integration may lack of good error handling and coding style. I appreciate any suggestions or pull requests that clean up my messy code 😊

Feel free to participate! 🙋‍♂️

## Thanks to...

@michaelarnauts and his integration of ComfoConnect, where I discovered a lot of telemetries and properties of the ventilation unit:
https://github.com/michaelarnauts/aiocomfoconnect 
