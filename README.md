# micropython-thingspeak

Library for sending data to [thingspeak.com](thingspeak.com) from IoT 
devices running MicroPython (such as ESP8266).

# Features

* Supports HTTP and HTTPS API (extension is possible)
* Automatically calculates delay required to conform to Free plan
* Allows naming channels (you can use _Humidity_ instead of cryptic 
  _field1_ required by the API)
* Resolves thingspeak.com IP address only once
* Optionally logs sent values to console

# Usage guide

[Download the library](https://raw.githubusercontent.com/radeklat/micropython-thingspeak/master/src/lib/thingspeak.py) 
and put it in the _lib_ folder of your project (see 
[esp8266-deploy-micropython](https://github.com/radeklat/esp8266-deploy-micropython) 
for easy deployments!).

## Get ThingSpeak API keys

1. Login on [ThingSpeak website](https://thingspeak.com)
1. Go to _Channels/My channels_
1. Choose a channel
1. Go to _API Keys_ tab
1. Make note of the _Write API Key_

## Configure channels

API rate limiting is calculated based on number of channels. So it is 
necessary to specify all your active channels, even if they are not used
on current device.

Each channel requires a name (for logging and self-defensive coding), 
Write API key () and list of field names.

Field names are internally transformed into _field1_ ... _fieldN_ so 
they need to be in this order. 

```python
from thingspeak import Channel

channel_living_room = "living room"
channel_bedroom = "bedroom"
active_channel = channel_living_room

field_temperature = "Temperature"
field_humidity = "Humidity"

channels = [
    Channel(channel_living_room, '<API KEY>', [field_temperature, field_humidity]),
    Channel(channel_bedroom, '<API KEY>', [field_temperature, field_humidity])
]
``` 

## Create API instance

By default will library use HTTP protocol and logging is turned off.

```python
from thingspeak import ThingSpeakAPI, ProtoHTTPS

thing_speak = ThingSpeakAPI(channels, protocol_class=ProtoHTTPS, log=True)
```

## Send values

```python
import machine
import time
import dht

dht_sensor = dht.DHT22(machine.Pin(0))

while True:
    try:
        dht_sensor.measure()
    except OSError:
        continue

    thing_speak.send(active_channel, {
        field_temperature: dht_sensor.temperature(),
        field_humidity: dht_sensor.humidity()
    })

    time.sleep(thing_speak.min_delay)
```

`ThingSpeak.send()` returns False when sending values fails. This is in 
most cases due to a wrong API key.

# Examples

You can find a working example of sending values from DHT22 on ESP8266
in [src/main.py](src/main.py).

# Testing

There are unit tests present in the [tests](tests) directory. Before 
running them, set _API_KEY_ environment variable to a _Write API Key_
of some testing channel. 