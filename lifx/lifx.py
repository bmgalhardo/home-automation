from typing import List

import lifxlan as lifx
from lifxlan.errors import WorkflowException
from fastapi import FastAPI, status
import uvicorn
from pydantic import BaseModel

app = FastAPI()


class BulbModel(BaseModel):
    ip: str
    mac: str


class Bulb(lifx.Light):

    def __init__(self, mac_addr, ip_addr):
        super().__init__(mac_addr, ip_addr)
        self._hue, self._saturation, self._brightness, self._kelvin = self.get_color()

    @property
    def state(self):
        return min(self.get_power(), 1)

    @property
    def hue(self):
        hue = self._hue / 65535 * 360
        return round(hue, 2)

    @property
    def saturation(self):
        """converts saturation to 0-1"""
        saturation = self._saturation / 65535
        return round(saturation, 2)

    @property
    def brightness(self):
        """converts brightness to 0-1"""
        brightness = self._brightness / 65535
        return round(brightness, 2)

    @property
    def kelvin(self):
        return self._kelvin


@app.get("/all_bulbs")
def get_lights():
    lan = lifx.LifxLAN()
    lights: List[lifx.Device] = lan.get_lights()
    data = [{
        "ip": l.ip_addr,
        "mac_address": l.mac_addr,
        "group": l.get_group(),
        "label": l.get_label(),
        "product": lifx.product_map[l.get_product()] or "Unknown",
    } for l in lights]
    return data


@app.post("/bulb_metrics")
def get_light_info(bulb: BulbModel):
    try:
        ip = bulb.ip
        mac = bulb.mac

        light = Bulb(mac, ip)
        data = {
            'state': light.state,
            'hue': light.hue,
            'saturation': light.saturation,
            'brightness': light.brightness,
            'kelvin': light.kelvin,
        }
        return data
    except WorkflowException:
        return {"error": "Bad parameters"}


@app.post("/switch", status_code=status.HTTP_201_CREATED)
def toggle_switch(bulb: BulbModel):
    try:
        ip = bulb.ip
        mac = bulb.mac

        light = Bulb(mac, ip)
        state = light.state

        if state:
            light.set_power(False)
            return {'on': False}
        else:
            light.set_power(True)
            return {'on': True}
    except WorkflowException:
        return {"error": "Bad parameters"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
