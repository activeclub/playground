from datetime import datetime

import cv2

# /dev/video0を指定
DEV_ID = 0

# パラメータ
WIDTH = 640
HEIGHT = 480

def main():
    # /dev/video0を指定
    cap = cv2.VideoCapture(DEV_ID)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G"))

    # 解像度の指定
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    # キャプチャの実施
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


if __name__ == "__main__":
    main()