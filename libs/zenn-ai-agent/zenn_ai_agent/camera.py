import time
from datetime import datetime

import cv2

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
    from libcamera import controls
    from picamera2 import Picamera2, Preview

    picam2 = Picamera2()

    # video_config = picam2.create_video_configuration()
    # picam2.configure(video_config)
    # encoder = H264Encoder(bitrate=10000000)
    # output = "test.h264"
    # picam2.start_recording(encoder, output)
    # time.sleep(10)
    # picam2.stop_recording()

    sensor_modes = picam2.sensor_modes
    print("=== sensor_modes ===")
    print(sensor_modes)
    full_resolution_mode = sensor_modes[1]

    camera_controls = {
        # AF設定
        "AfMode": controls.AfModeEnum.Continuous,
        # "AfSpeed": controls.AfSpeedEnum.Fast,
        # フリッカー低減モード
        # "AeFlickerMode": controls.AeFlickerModeEnum.Manual,  # manual flicker
        # "AeFlickerPeriod": 10000,  # 50Hz=10000, 60Hz=8333
        # 測光モード
        # "AeMeteringMode": controls.AeMeteringModeEnum.Matrix,  # CenterWeighted, Matrix, Spot
        # オートホワイトバランス
        # "AwbEnable": True,  # True or False
        # "AwbMode": controls.AwbModeEnum.Indoor,  # Auto, Indoor, Daylight, Cloudy
        # HDR
        # Picamera2では、RaspberryPiカメラモジュール3のハードウェアHDRをサポートしていないため、有効・無効の切り替えは外部コマンドで行う
        # ちなみにソフトウェアHDRの機能は存在するが、ラズパイ5にならないと使えない
        #   - 有効化: v4l2-ctl --set-ctrl wide_dynamic_range=1 -d /dev/v4l-subdev0
        #   - 無効化: v4l2-ctl --set-ctrl wide_dynamic_range=0 -d /dev/v4l-subdev0
    }

    picam2.start_preview(Preview.QTGL)
    preview_config = picam2.create_preview_configuration(
        main={
            "format": "XRGB8888",
            "size": (1920, 1080),
            # "size": picam2.sensor_resolution,
        },
        # buffer_count=4,
        controls=camera_controls,
        # lores={"format": "YUV420", "size": (1280, 720)},
        # display="lores",
        # sensor={
        #     "output_size": full_resolution_mode["size"],
        #     "bit_depth": full_resolution_mode["bit_depth"],
        # },
        raw=full_resolution_mode,
    )
    print("=== preview_config ===")
    print(preview_config)
    still_config = picam2.create_still_configuration(
        main={"size": picam2.sensor_resolution},
        buffer_count=1,
        controls=camera_controls,
    )

    picam2.configure(preview_config)

    # config = picam2.camera_configuration()

    picam2.start(config=preview_config)
    picam2.set_controls({"ScalerCrop": full_resolution_mode["crop_limits"]})

    metadata = picam2.capture_metadata()
    print("=== metadata ===")
    print(metadata)

    time.sleep(3.0)

    ##
    # picam2.capture_file("test.jpg")
    ##

    ##
    # while True:
    #     im = picam2.capture_array()
    #     cv2.imshow("Camera", im)

    #     key = cv2.waitKey(1)
    #     # Escキーを入力されたら画面を閉じる
    #     if key == 27:
    #         break
    # cv2.destroyAllWindows()
    ##

    ##
    frame = picam2.capture_array()
    # 画像が3チャンネル以外の場合は3チャンネルに変換する
    channels = 1 if len(frame.shape) == 2 else frame.shape[2]
    if channels == 1:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    if channels == 4:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    # jpgに保存
    cv2.imwrite("test_cv2.jpg", frame)
    ##

    picam2.stop()


if __name__ == "__main__":
    pycamera_sample()
