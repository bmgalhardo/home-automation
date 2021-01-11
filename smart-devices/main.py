import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import List
import os
from prometheus_client import start_http_server, Gauge
import aiolifx as lifx
from kasa import SmartPlug, Discover
import logging
from functools import partial

logging.basicConfig(level=logging.INFO)

UPDATE_PERIOD = int(os.getenv('UPDATE_PERIOD', 5))
DISCOVERY_PERIOD = int(os.getenv('DISCOVERY_PERIOD', 10))
BROADCAST_IP = os.getenv('BROADCAST_IP', "192.168.8.255")
SERVER_PORT = int(os.getenv('SERVER_PORT', 9999))

PLUG_VOLTS = Gauge(name='plug_measurements',
                   documentation='Hold voltage measurements of smart plugs',
                   unit="volts",
                   labelnames=['location', 'device'])

PLUG_CURRENT = Gauge(name='plug_measurements',
                     documentation='Hold current measurements of smart plugs',
                     unit="amperes",
                     labelnames=['location', 'device'],
                     )

PLUG_LOAD = Gauge(name='plug_measurements',
                  documentation='Hold power measurements of smart plugs',
                  unit="watts",
                  labelnames=['location', 'device'],
                  )

BULB_STATE = Gauge(name='bulb_measurements_state',
                   documentation='Power state of light bulb',
                   labelnames=['group', 'location', 'type', 'device']
                   )

BULB_HUE = Gauge(name='bulb_measurements_hue',
                 documentation='Hue of light bulb',
                 labelnames=['group', 'location', 'type', 'device']
                 )

BULB_SATURATION = Gauge(name='bulb_measurements_saturation',
                        documentation='Saturation of light bulb',
                        unit='percent',
                        labelnames=['group', 'location', 'type', 'device']
                        )

BULB_Brightness = Gauge(name='bulb_measurements_brightness',
                        documentation='Brightness of light bulb',
                        unit='percent',
                        labelnames=['group', 'location', 'type', 'device']
                        )

BULB_Kelvin = Gauge(name='bulb_measurements',
                    documentation='Colour temperature of light bulb',
                    unit='kelvin',
                    labelnames=['group', 'location', 'type', 'device']
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

    async def set_devices_by_ip(self, ips: list = []) -> None:
        s = []
        for ip in ips:
            d = await self.get_info(ip)
            s.append(MyPlug(host=ip, name=d['alias']))
            logging.info(f"{d['alias']}: {ip}")
        self.devices = s

    async def discover_devices(self) -> None:
        """discovers kasa devices in network"""

        devices = await Discover.discover(return_raw=True, target=BROADCAST_IP)
        logging.debug(devices)
        if devices:
            relevant_raw = {
                devices[ip]['system']["get_sysinfo"]['alias']: ip
                for ip in devices
            }
            logging.info(f"Devices Found: {relevant_raw}")
            self.set_devices(relevant_raw)

    async def set_measurements(self) -> None:
        """update retrieves new measurements from the device which are then made available at endpoint"""
        for d in self.devices:
            await d.update()
            m = d.emeter_realtime
            volts = m['voltage_mv']/1000  # mV -> V
            amps = m['current_ma']/1000  # mA -> A
            watts = m['power_mw']/1000  # mW -> W

            label_values = [d.name, "smart_plug"]

            PLUG_VOLTS.labels(*label_values).set(volts)
            PLUG_CURRENT.labels(*label_values).set(amps)
            PLUG_LOAD.labels(*label_values).set(watts)

    @staticmethod
    async def get_info(ip):
        s = SmartPlug(ip)
        await s.update()
        return s.sys_info


class BulbCollection:

    def __init__(self):
        self.bulbs = []

    def register(self, bulb):
        bulb.get_label()
        bulb.get_location()
        bulb.get_version()
        bulb.get_group()
        logging.info(f'bulb {bulb.ip_addr}')
        self.bulbs.append(bulb)

    def unregister(self, bulb):
        idx = 0
        for x in list([y.mac_addr for y in self.bulbs]):
            if x == bulb.mac_addr:
                del(self.bulbs[idx])
                break
            idx += 1

    def set_measurements(self):
        """Update the status of our bulbs"""
        for bulb in self.bulbs:
            colour_callback = partial(self.update_metrics)
            bulb.get_color(callb=colour_callback)

    def update_metrics(self, bulb, resp):
        """Given a callback from a colour request, update some metrics"""

        product = lifx.aiolifx.product_map[bulb.product] or "Unknown"

        label_values = [bulb.group, bulb.label, product, 'smart_bulb']

        if not resp:
            BULB_STATE.labels(*label_values).set('nan')
            BULB_HUE.labels(*label_values).set('nan')
            BULB_SATURATION.labels(*label_values).set('nan')
            BULB_Brightness.labels(*label_values).set('nan')
            BULB_Kelvin.labels(*label_values).set('nan')
            return

        BULB_STATE.labels(*label_values).set(min(resp.power_level, 1))
        BULB_HUE.labels(*label_values).set(self.get_true_hue(resp.color[0]))
        BULB_SATURATION.labels(*label_values).set(self.true_saturation(resp.color[1]))
        BULB_Brightness.labels(*label_values).set(self.true_brightness(resp.color[2]))
        BULB_Kelvin.labels(*label_values).set(self.true_kelvin(resp.color[3]))

    @staticmethod
    def get_true_hue(lifx_hue):
        hue = lifx_hue / 65535 * 360
        return round(hue, 2)

    @staticmethod
    def true_saturation(lifx_saturation):
        """converts saturation to 0-1"""
        saturation = lifx_saturation / 65535
        return round(saturation, 2)

    @staticmethod
    def true_brightness(lifx_brightness):
        """converts brightness to 0-1"""
        brightness = lifx_brightness / 65535
        return round(brightness, 2)

    @staticmethod
    def true_kelvin(lifx_kelvin):
        return lifx_kelvin


if __name__ == '__main__':

    start_http_server(SERVER_PORT)

    plugs = PlugCollection()
    bulbs = BulbCollection()

    loop = asyncio.get_event_loop()
    # asyncio.get_event_loop().run_until_complete(plugs.set_devices_by_ip([f"192.168.8.10{i}" for i in [5, 6, 7]]))
    lifx.LifxDiscovery(loop, bulbs, discovery_interval=DISCOVERY_PERIOD, broadcast_ip=BROADCAST_IP).start()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(plugs.discover_devices, 'interval', seconds=DISCOVERY_PERIOD)
    scheduler.add_job(plugs.set_measurements, 'interval', seconds=UPDATE_PERIOD)
    scheduler.add_job(bulbs.set_measurements, 'interval', seconds=UPDATE_PERIOD)
    scheduler.start()
    loop.run_forever()
