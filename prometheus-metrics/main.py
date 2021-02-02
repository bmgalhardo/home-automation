import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import List
from prometheus_client import start_http_server, Gauge
import logging
import requests
from datetime import datetime, timedelta
import settings

logging.basicConfig(level=logging.INFO)

EDP_LOAD = Gauge(name='smart_meter_measurements',
                 documentation='Hold watts measurements of smart meter',
                 unit="watts")

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

BULB_BRIGHTNESS = Gauge(name='bulb_measurements_brightness',
                        documentation='Brightness of light bulb',
                        unit='percent',
                        labelnames=['group', 'location', 'type', 'device']
                        )

BULB_KELVIN = Gauge(name='bulb_measurements',
                    documentation='Colour temperature of light bulb',
                    unit='kelvin',
                    labelnames=['group', 'location', 'type', 'device']
                    )


class DeviceCollection:

    DISCOVERY_ENDPOINT: str = None
    METRICS_ENDPOINT: str = None
    DEVICE = None
    METRICS: dict = {}

    devices = []

    def discovery(self) -> None:
        """assigns devices to class"""
        response = requests.get(self.DISCOVERY_ENDPOINT)
        if response.status_code == 200:
            discovered_devices = [self.DEVICE(**b) for b in response.json()]
            disconnected = set(self.devices) - set(discovered_devices)
            if disconnected:
                for i in disconnected:
                    self.fill_null(i)
            self.devices = discovered_devices
        else:
            logging.warning("could not retrieve device info")

    def set_measurements(self) -> None:
        for device in self.devices:
            self.update_metrics(device)

    @staticmethod
    def get_label(device):
        return NotImplemented

    @staticmethod
    def get_post_data(device):
        return NotImplemented

    def fill_null(self, device) -> None:
        label_values = self.get_label(device)
        for key, item in self.METRICS.items():
            key.labels(*label_values).set('nan')

    def update_metrics(self, device) -> None:
        """update the metrics for a given bulb"""

        data = self.get_post_data(device)

        response = requests.post(self.METRICS_ENDPOINT, json=data)
        label_values = self.get_label(device)
        metrics = response.json()

        for key, item in self.METRICS.items():
            if response.status_code == 200:
                key.labels(*label_values).set(metrics[item])
            else:
                key.labels(*label_values).set('nan')


class Plug:

    def __init__(self, **kwargs):
        self.name = kwargs['alias']
        self.ip = kwargs['ip']


class PlugCollection(DeviceCollection):

    device: List[Plug] = []
    DEVICE = Plug
    DISCOVERY_ENDPOINT = f"{settings.PLUG_CONTROLLER}/all_plugs"
    METRICS_ENDPOINT = f"{settings.PLUG_CONTROLLER}/plug_metrics"
    METRICS = {
        PLUG_VOLTS: 'volt',
        PLUG_CURRENT: 'ampere',
        PLUG_LOAD: 'watts'
    }

    @staticmethod
    def get_label(device: Plug) -> list:
        return [device.name, "smart_plug"]

    @staticmethod
    def get_post_data(device: Plug) -> dict:
        return {'ip': device.ip}


class Bulb:
    def __init__(self, **kwargs):
        self.ip = kwargs['ip']
        self.mac = kwargs['mac_address']
        self.label = kwargs['label']
        self.group = kwargs['group']
        self.product = kwargs['product']


class BulbCollection(DeviceCollection):

    device: List[Bulb] = []
    DEVICE = Bulb
    DISCOVERY_ENDPOINT = f"{settings.BULB_CONTROLLER}/all_bulbs"
    METRICS_ENDPOINT = f"{settings.BULB_CONTROLLER}/bulb_metrics"
    METRICS = {
        BULB_STATE: 'state',
        BULB_HUE: 'hue',
        BULB_SATURATION: 'saturation',
        BULB_BRIGHTNESS: 'brightness',
        BULB_KELVIN: 'kelvin'
    }

    @staticmethod
    def get_label(device: Bulb) -> list:
        return [device.group, device.label, device.product, 'smart_bulb']

    @staticmethod
    def get_post_data(device: Bulb) -> dict:
        return {
            'ip': device.ip,
            'mac': device.mac,
        }


class EDP:

    @classmethod
    def set_measurements(cls):
        response = requests.get(f'{settings.EDP_CONTROLLER}/active_power')
        if response.status_code == 200:
            measurement = response.json()['total']*1000
        else:
            measurement = 'nan'

        EDP_LOAD.set(measurement)


if __name__ == '__main__':

    start_http_server(settings.SERVER_PORT)

    plugs = PlugCollection()
    bulbs = BulbCollection()

    loop = asyncio.get_event_loop()

    scheduler = AsyncIOScheduler()

    scheduler.add_job(plugs.discovery, 'interval', seconds=settings.DISCOVERY_PERIOD)
    scheduler.add_job(plugs.set_measurements, 'interval', seconds=settings.UPDATE_PERIOD)

    scheduler.add_job(bulbs.discovery, 'interval', seconds=settings.DISCOVERY_PERIOD)
    scheduler.add_job(bulbs.set_measurements, 'interval', seconds=settings.UPDATE_PERIOD)

    scheduler.add_job(EDP.set_measurements, 'interval', seconds=60*60*6, next_run_time=datetime.now()+timedelta(seconds=10))
    scheduler.start()
    loop.run_forever()
