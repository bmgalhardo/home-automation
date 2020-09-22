import cv2
import os
from datetime import datetime


def capture_video(resolution: str = '720p'):

    frames_per_second = 1
    res_dict = {
        '720p': (1280, 720),
        '1080p': (1920, 1080)
    }
    res = res_dict[resolution]

    path = "/videos/"

    while True:
        cap = cv2.VideoCapture("rtsp://admin:notoo7luke@192.168.8.99:10554/tcp/av0_0")

        filename = f'{datetime.now().strftime("banhos-secos-%Y-%m-%d")}.avi'
        # check if file exists
        if os.path.isfile(os.path.join(path, filename)):
            filename = filename.replace('.avi', f'{datetime.now().strftime("-%H-%M-%S")}.avi')

        out = cv2.VideoWriter(os.path.join(path, filename), cv2.VideoWriter_fourcc(*'XVID'), frames_per_second, res)

        this_day = datetime.now().day
        while datetime.now().day == this_day:
            ret, frame = cap.read()
            if resolution != '1080p':
                frame = cv2.resize(frame, res)
            out.write(frame)

        cap.release()
        out.release()
        cv2.destroyAllWindows()


capture_video()
