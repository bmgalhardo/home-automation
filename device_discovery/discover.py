import asyncio
import time
import redis
from kasa import Discover, SmartPlug
import os

DISCOVERY_PERIOD = int(os.getenv('DISCOVERY_PERIOD', 60))


def discover(broadcast_ip: str) -> dict:
    """discovers kasa devices in network"""

    loop = asyncio.get_event_loop()

    async def _on_device(_dev: SmartPlug):
        await _dev.update()

    # TODO clean shutdown behaviour
    devices = loop.run_until_complete(Discover.discover(on_discovered=_on_device, return_raw=True, target=broadcast_ip))

    if devices:
        relevant_raw = {
            devices[ip]['system']["get_sysinfo"]['alias']: ip
            for ip in devices
        }
        return relevant_raw
    else:
        return {}


if __name__ == '__main__':

    # discovery in host mode to broadcast ping
    r = redis.Redis(port=6380)
    while True:
        devices = discover("192.168.8.255")
        if devices:
            current_plugs = r.hkeys('plugs')

            # add detected ones
            for d_key, d_value in devices.items():
                r.hset('plugs', d_key, d_value)

            # remove installations not detected
            dropped = set(a.decode() for a in current_plugs) - set(devices.keys())

            for d in dropped:
                r.hdel('plugs', d)

        else:
            r.delete('plugs')

        time.sleep(DISCOVERY_PERIOD)
