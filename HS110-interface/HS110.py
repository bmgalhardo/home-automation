import sys
import time
import socket
import json
import threading
from struct import pack


class CarbonDB:

    CARBON_SERVER = "graphite"  # docker container
    CARBON_PORT = 2003

    @classmethod
    def store_data(cls, collection_name: str, data: dict) -> None:

        timestamp = int(time.time())

        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            tcp_sock.connect((cls.CARBON_SERVER, cls.CARBON_PORT))
            for d in data.keys():
                message = f'{collection_name}.{d} {data[d]} {timestamp}\n'
                tcp_sock.send(message.encode())
        except socket.error:
            print("Unable to open socket on graphite-carbon.", file=sys.stderr)
        finally:
            tcp_sock.close()


class SmartPlug:

    COMMANDS = {
        # list of commands
        # https://github.com/softScheck/tplink-smartplug/blob/master/tplink-smarthome-commands.txt
        "info": '{"system": {"get_sysinfo": null}}',
        "current_data": '{"emeter":{"get_realtime":{}}}'
    }

    PORT = 9999

    def __init__(self, name, ip):
        self.name = name
        self.ip = ip

    # https://github.com/softScheck/tplink-smartplug/blob/master/tplink-smartplug.py
    @classmethod
    def encrypt(cls, string: str) -> bytes:
        key = 171
        result = pack('>I', len(string))
        for i in string:
            a = key ^ ord(i)
            key = a
            result += bytes([a])

        return result

    @classmethod
    def decrypt(cls, data: bytes) -> str:
        key = 171
        result = ""
        for i in data:
            a = key ^ i
            key = i
            result += chr(a)
        return result

    def send_command(self, cmd: str) -> dict:

        data = b''

        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            tcp_sock.connect((self.ip, self.PORT))
            tcp_sock.send(self.encrypt(self.COMMANDS[cmd]))
            data = tcp_sock.recv(2048)
        except socket.error:
            print("Socket closed.", file=sys.stderr)
        finally:
            tcp_sock.close()

        if not data:
            print("No data returned on power request.", file=sys.stderr)
            # store_metrics(0, 0, 0)
            return {}

        decrypted_data = self.decrypt(data[4:])
        json_data = json.loads(decrypted_data)

        return json_data

    def get_version(self) -> dict:
        data = self.send_command('info')['system']['get_sysinfo']
        data = {key: data[key] for key in ['alias', 'hw_ver', 'mac', 'model', 'sw_ver']}
        return data

    def get_measurement(self, save: bool = False) -> dict:
        data = self.send_command('current_data')
        emeter = data["emeter"]["get_realtime"]

        if not emeter:
            print("No emeter data returned on power request.", file=sys.stderr)
            emeter_data = {
                'current': 0,
                'voltage': 0,
                'power': 0
            }
        else:
            emeter_data = {
                'current': emeter['current_ma'],
                'voltage': emeter['voltage_mv'],
                'power': emeter['power_mw'],
            }

        if save:
            # stores data in db
            CarbonDB.store_data(collection_name=self.name,
                                data=emeter_data)

        return emeter_data


def run():
    threading.Timer(15.0, run).start()

    SmartPlug(name='HS110', ip='192.168.8.107').get_measurement(save=True)

run()

