import time
from datetime import datetime

import cv2
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

# /dev/video0を指定
DEV_ID = 0

# パラメータ
WIDTH = 640
HEIGHT = 480


def cv2_sample():
    # /dev/video0を指定
    cap = cv2.VideoCapture(DEV_ID)
    # Set the camera format to a lower resolution
    # cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G"))  # MJPG format
    cap.set(
        cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("Y", "U", "Y", "V")
    )  # YUYV format

    # 解像度の指定
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    # キャプチャの実施
    if not cap.isOpened():
        print(
            f"Error: Could not open video device {DEV_ID}. Please check if the camera is connected and accessible."
        )
        return

    ret, frame = cap.read()
    if ret:
        # ファイル名に日付を指定
        date = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = "./" + date + ".jpg"
        cv2.imwrite(path, frame)

    # 後片付け
    cap.release()
    cv2.destroyAllWindows()
    return


def pycamera_sample():
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration()
    picam2.configure(video_config)
    encoder = H264Encoder(bitrate=10000000)
    output = "test.h264"
    picam2.start_recording(encoder, output)
    time.sleep(10)
    picam2.stop_recording()


if __name__ == "__main__":
    pycamera_sample()
