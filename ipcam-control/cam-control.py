import time
import requests
import redis


class IPCam:
    IP = "192.168.8.99"
    PORT = "3979"
    USER = "admin"
    PASS = "notoo7luke"

    FRONT_GATE = 31
    SMALLER_GATE = 35
    FRONT_DOOR = 33
    FREE_WAY = 37

    @classmethod
    def front_gate(cls) -> None:
        cls.execute_message(cls.FRONT_GATE)

    @classmethod
    def smaller_gate(cls) -> None:
        cls.execute_message(cls.SMALLER_GATE)

    @classmethod
    def front_door(cls) -> None:
        cls.execute_message(cls.FRONT_DOOR)

    @classmethod
    def free_way(cls) -> None:
        cls.execute_message(cls.FREE_WAY)

    @classmethod
    def execute_message(cls, command: int) -> None:
        # check commands here
        # https://onlinecamera.net/lapok/letoltesek/cgi-instructions-fd.pdf

        message = f"http://{cls.IP}:{cls.PORT}/decoder_control.cgi?" \
                  f"loginuse={cls.USER}&loginpas={cls.PASS}&" \
                  f"command={command}&onestep=0"

        r = requests.get(url=message)
        if r.status_code != 200:
            print('could not execute cmd')

        return


def camera_loop():
    r = redis.Redis(host='redis')
    # r = redis.Redis(port=6380)
    r.mset({"loop": 1})
    a = 0

    loop = [
        IPCam.FRONT_GATE,
        IPCam.SMALLER_GATE,
        IPCam.FRONT_DOOR,
        IPCam.SMALLER_GATE,
        IPCam.FRONT_GATE,
        IPCam.FREE_WAY
    ]

    while True:

        if r.get("loop").decode() == "0":
            time.sleep(5)
            continue

        if a == len(loop):
            a = 0

        IPCam.execute_message(loop[a])

        a += 1
        time.sleep(10)


camera_loop()
