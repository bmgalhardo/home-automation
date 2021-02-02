from fastapi import FastAPI, status
from pydantic import BaseModel
from kasa import Discover, SmartPlug
import uvicorn
import os

app = FastAPI()
BROADCAST_IP = os.getenv('BROADCAST_IP', "192.168.8.255")


class Plug(BaseModel):
    ip: str


@app.get("/all_plugs")
async def get_plugs():
    devices = await Discover.discover(return_raw=True, target=BROADCAST_IP)
    relevant_raw = {}
    if devices:
        relevant_raw = [{
            "alias": devices[ip]['system']["get_sysinfo"]['alias'],
            "ip": ip
        } for ip in devices]
    return relevant_raw


@app.post("/plug_metrics")
async def get_light_info(plug: Plug):
    p = SmartPlug(plug.ip)
    await p.update()

    m = p.emeter_realtime
    volts = m['voltage_mv'] / 1000  # mV -> V
    amps = m['current_ma'] / 1000  # mA -> A
    watts = m['power_mw'] / 1000  # mW -> W

    data = {
        'volt': volts,
        'ampere': amps,
        'watts': watts,
    }
    return data


@app.post("/plug_info")
async def get_light_info(plug: Plug):
    p = SmartPlug(plug.ip)
    await p.update()
    return p.sys_info


@app.post("/switch", status_code=status.HTTP_201_CREATED)
async def toggle_switch(plug: Plug):
    p = SmartPlug(plug.ip)
    await p.update()
    if p.is_on:
        await p.turn_off()
        return {'on': False}
    else:
        await p.turn_on()
        return {'on': True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
