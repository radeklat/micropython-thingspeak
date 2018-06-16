import machine
import time
import dht

try:
    from thingspeak import ThingSpeakAPI, Channel, ProtoHTTP
except ImportError:
    from .lib.thingspeak import ThingSpeakAPI, Channel, ProtoHTTP

dht_sensor = dht.DHT22(machine.Pin(0))

channel_living_room = "living room"
channel_bedroom = "bedroom"

field_temperature = "Temperature"
field_humidity = "Humidity"

thing_speak = ThingSpeakAPI([
    Channel(channel_living_room, '<API KEY>', [field_temperature, field_humidity]),
    Channel(channel_bedroom, '<API KEY>', [field_temperature, field_humidity])
], protocol_class=ProtoHTTP, log=True)

active_channel = channel_living_room

while True:
    try:
        dht_sensor.measure()
    except OSError:
        continue

    thing_speak.send(active_channel, {
        field_temperature: dht_sensor.temperature(),
        field_humidity: dht_sensor.humidity()
    })

    time.sleep(thing_speak.free_api_delay)

