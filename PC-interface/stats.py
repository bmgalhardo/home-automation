import subprocess
import threading
import time
import socket
import sys


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


def read_nvidia(save: bool = False):

    result = subprocess.run(["./nvidia.sh"], stdout=subprocess.PIPE)

    r_list = [float(a) for i, a in enumerate(result.stdout.decode('utf-8').split()) if i not in [2, 5, 6]]
    gpu_data = {
        'mem_usage_cap': r_list[0],
        'mem_usage': r_list[1],
        'temp': r_list[2],
        'temp_cap': r_list[3],
        'power': r_list[4],
        'power_cap': r_list[5]
    }

    if save:
        CarbonDB.store_data(collection_name='nvidia',
                            data=gpu_data)
    return gpu_data


def read_disks(save: bool = False):

    result = subprocess.run(["./disks.sh"], stdout=subprocess.PIPE)
    result = result.stdout.decode('utf-8').split()

    data = {
        disk.replace('/', '-'): int(value.replace('%', '')) for idx, (disk, value) in enumerate(zip(result[1:], result))
        if idx % 2 == 0
    }

    if save:
        CarbonDB.store_data(collection_name='disks',
                            data=data)

    return data


def run():
    threading.Timer(15.0, run).start()

    read_disks(save=True)


run()
