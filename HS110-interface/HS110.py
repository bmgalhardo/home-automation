import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import List
import os
from prometheus_client import start_http_server, Gauge

from kasa import SmartPlug, Discover
import logging

logging.basicConfig(level=logging.DEBUG)

UPDATE_PERIOD = int(os.getenv('UPDATE_PERIOD', 5))
DISCOVERY_PERIOD = int(os.getenv('DISCOVERY_PERIOD', 60))

PLUG_VOLTS = Gauge(name='plug_measurements',
                   documentation='Hold voltage measurements of smart plugs',
                   unit="volts",
                   labelnames=['plug_name'])

PLUG_CURRENT = Gauge(name='plug_measurements',
                     documentation='Hold current measurements of smart plugs',
                     unit="amperes",
                     labelnames=['plug_name'],
                     )

PLUG_LOAD = Gauge(name='plug_measurements',
                  documentation='Hold power measurements of smart plugs',
                  unit="watts",
                  labelnames=['plug_name'],
                  )


class MyPlug(SmartPlug):

    def __init__(self, name: str, host: str):
        super().__init__(host)
        self.name = name


class PlugCollection:

    def __init__(self) -> None:
        self.devices: List[MyPlug] = []

    def set_devices(self, ips: dict) -> None:
        """assigns devices to class"""
        self.devices = [MyPlug(host=ip, name=name) for name, ip in ips.items()]

    def discover_devices(self, broadcast_ip: str) -> None:
        """discovers kasa devices in network"""

        loop = asyncio.get_event_loop()

        async def _on_device(_dev: SmartPlug):
            await _dev.update()

        # TODO clean shutdown behaviour
        devices = loop.run_until_complete(
            Discover.discover(on_discovered=_on_device, return_raw=True, target=broadcast_ip))

        if devices:
            relevant_raw = {
                devices[ip]['system']["get_sysinfo"]['alias']: ip
                for ip in devices
            }
            logging.info(relevant_raw)
            self.set_devices(relevant_raw)

    async def set_measurements(self) -> None:
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
