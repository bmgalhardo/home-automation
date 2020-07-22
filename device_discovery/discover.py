import asyncio
import time
import redis
from kasa import Discover, SmartPlug


def get_plug_name(plug_alias: str) -> str:
    """set device name according to whats monitoring"""

    device_mapping = {
        "SP-01": "plug-tv-room",
        "SP-02": "plug-office",
        "SP-03": None
    }
    if plug_alias not in device_mapping.keys():
        raise KeyError

    return device_mapping[plug_alias]


def discover(broadcast_ip: str) -> dict:
    """discovers kasa devices in network"""

    loop = asyncio.get_event_loop()

    async def _on_device(_dev: SmartPlug):
        await _dev.update()

    # TODO clean shutdown behaviour
    devices = loop.run_until_complete(Discover.discover(on_discovered=_on_device, return_raw=True, target=broadcast_ip))

    if devices:
        relevant_raw = {
            get_plug_name(devices[ip]['system']["get_sysinfo"]['alias']): ip
            for ip in devices
        }
        return relevant_raw
    else:
        return {}


if __name__ == '__main__':

    r = redis.Redis(port=6380)
    while True:
        devices = discover("192.168.8.255")
        if devices:
            r.mset(devices)
        time.sleep(60)
