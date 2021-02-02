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


class Plug:

    def __init__(self, **kwargs):
        self.name = kwargs['alias']
        self.ip = kwargs['ip']


class PlugCollection:

    def __init__(self) -> None:
        self.plugs: List[Plug] = []

    def discovery(self) -> None:
        """assigns devices to class"""
        response = requests.get(f"{settings.PLUG_CONTROLLER}/all_plugs")
        if response.status_code == 200:
            self.plugs = [Plug(**b) for b in response.json()]
        else:
            logging.warning("could not retrieve plug info")

    def set_measurements(self) -> None:
        for plug in self.plugs:
            self.update_metrics(plug)

    @staticmethod
    def update_metrics(plug) -> None:
        """update the metrics for a given bulb"""

        data = {'ip': plug.ip}

        response = requests.post(f"{settings.PLUG_CONTROLLER}/plug_metrics", json=data)
        label_values = [plug.name, "smart_plug"]
        metrics = response.json()

        if response.status_code == 200:
            PLUG_VOLTS.labels(*label_values).set(metrics['volt'])
            PLUG_CURRENT.labels(*label_values).set(metrics['ampere'])
            PLUG_LOAD.labels(*label_values).set(metrics['watts'])
        else:
            PLUG_VOLTS.labels(*label_values).set('nan')
            PLUG_CURRENT.labels(*label_values).set('nan')
            PLUG_LOAD.labels(*label_values).set('nan')


class Bulb:
    def __init__(self, **kwargs):
        self.ip = kwargs['ip']
        self.mac = kwargs['mac_address']
        self.label = kwargs['label']
        self.group = kwargs['group']
        self.product = kwargs['product']


class BulbCollection:

    def __init__(self):
        self.bulbs: List[Bulb] = []

    def discovery(self):
        response = requests.get(f"{settings.BULB_CONTROLLER}/all_bulbs")
        if response.status_code == 200:
            self.bulbs = [Bulb(**b) for b in response.json()]
        else:
            logging.warning("could not retrieve bulb info")

    def set_measurements(self) -> None:
        for bulb in self.bulbs:
            self.update_metrics(bulb)

    @staticmethod
    def update_metrics(bulb) -> None:
        """update the metrics for a given bulb"""

        data = {
            'ip': bulb.ip,
            'mac': bulb.mac,
        }

        response = requests.post(f"{settings.BULB_CONTROLLER}/bulb_metrics", json=data)
        label_values = [bulb.group, bulb.label, bulb.product, 'smart_bulb']
        metrics = response.json()

        if response.status_code == 200:
            BULB_STATE.labels(*label_values).set(metrics['state'])
            BULB_HUE.labels(*label_values).set(metrics['hue'])
            BULB_SATURATION.labels(*label_values).set(metrics['saturation'])
            BULB_Brightness.labels(*label_values).set(metrics['brightness'])
            BULB_Kelvin.labels(*label_values).set(metrics['kelvin'])
        else:
            BULB_STATE.labels(*label_values).set('nan')
            BULB_HUE.labels(*label_values).set('nan')
            BULB_SATURATION.labels(*label_values).set('nan')
            BULB_Brightness.labels(*label_values).set('nan')
            BULB_Kelvin.labels(*label_values).set('nan')


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
