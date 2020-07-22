import asyncio
from typing import List
import redis
from prometheus_client import start_http_server, Gauge
import time

from kasa import SmartPlug


class MyPlug(SmartPlug):

    def __init__(self, name: str, host: str):
        super().__init__(host)
        self.name = name


class PlugCollection:

    def __init__(self):
        self.devices: List[MyPlug] = []

    def set_devices(self, ips: dict):
        self.devices = [MyPlug(host=ip, name=name) for name, ip in ips.items()]

    @staticmethod
    def update(device: MyPlug):
        asyncio.run(device.update())

    def update_all(self):
        for _d in self.devices:
            self.update(_d)


UPDATE_PERIOD = 5
PLUG_VOLTS = Gauge('plug_measurements_volts',
                   'Hold voltage measurements of smart plugs, in Volt',
                   ['plug_name'])

PLUG_CURRENT = Gauge('plug_measurements_amps',
                     'Hold current measurements of smart plugs, in Ampere',
                     ['plug_name'])

PLUG_LOAD = Gauge('plug_measurements_watts',
                  'Hold power measurements of smart plugs, in Watts',
                  ['plug_name'])

MONITORING_DEVICES = ["plug-office", "plug-tv-room"]

if __name__ == '__main__':

    r = redis.Redis(host="redis")
    # r = redis.Redis(port=6380)

    start_http_server(9999)

    plugs = PlugCollection()

    while True:  # setup loop
        plug_ip_dict = {i: r.get(i) for i in MONITORING_DEVICES}
        print(plug_ip_dict)
        if not any(plug_ip_dict.values()):
            time.sleep(30)
            continue

        plugs.set_devices(plug_ip_dict)

        while True:  # measurement loop

            plugs.update_all()
            # TODO add break if no device found
            for d in plugs.devices:
                m = d.emeter_realtime
                volts = m['voltage_mv']/1000  # mV -> V
                amps = m['current_ma']/1000  # mA -> A
                watts = m['power_mw']/1000  # mW -> W

                PLUG_VOLTS.labels(d.name).set(volts)
                PLUG_CURRENT.labels(d.name).set(amps)
                PLUG_LOAD.labels(d.name).set(watts)

            time.sleep(UPDATE_PERIOD)
