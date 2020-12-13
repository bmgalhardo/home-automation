import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import List
import redis
from prometheus_client import start_http_server, Gauge

from kasa import SmartPlug


UPDATE_PERIOD = 5
DISCOVERY_PERIOD = 60
PLUG_VOLTS = Gauge('plug_measurements_volts',
                   'Hold voltage measurements of smart plugs, in Volt',
                   ['plug_name'])

PLUG_CURRENT = Gauge('plug_measurements_amps',
                     'Hold current measurements of smart plugs, in Ampere',
                     ['plug_name'])

PLUG_LOAD = Gauge('plug_measurements_watts',
                  'Hold power measurements of smart plugs, in Watts',
                  ['plug_name'])


class MyPlug(SmartPlug):

    def __init__(self, name: str, host: str):
        super().__init__(host)
        self.name = name


class PlugCollection:

    # connect in local mode within docker network
    cache = redis.Redis(host='redis')

    def __init__(self):
        self.devices: List[MyPlug] = []

    def set_devices(self, ips: dict):
        """assigns devices to class"""
        self.devices = [MyPlug(host=ip, name=name) for name, ip in ips.items()]

    def discover_devices(self):
        """retrieves devices from cache"""
        redis_dict = self.cache.hgetall('plugs')
        plug_ip_dict = {k.decode(): v.decode() for k, v in redis_dict.items()}
        self.set_devices(plug_ip_dict)

    async def set_measurements(self):
        """update retrieves new measurements from the device which are then made available at endpoint"""
        for d in self.devices:
            await d.update()
            m = d.emeter_realtime
            volts = m['voltage_mv']/1000  # mV -> V
            amps = m['current_ma']/1000  # mA -> A
            watts = m['power_mw']/1000  # mW -> W

            PLUG_VOLTS.labels(d.name).set(volts)
            PLUG_CURRENT.labels(d.name).set(amps)
            PLUG_LOAD.labels(d.name).set(watts)


if __name__ == '__main__':

    start_http_server(9999)

    plugs = PlugCollection()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(plugs.discover_devices, 'interval', seconds=DISCOVERY_PERIOD)
    scheduler.add_job(plugs.set_measurements, 'interval', seconds=UPDATE_PERIOD)
    scheduler.start()

    asyncio.get_event_loop().run_forever()
