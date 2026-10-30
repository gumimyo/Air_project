
import time
from pathlib import Path

import cv2
import mediapipe as mp
from PySide6.QtCore import QThread, Signal


class GestureWorker(QThread):
    # GUI에 현재 인식 상태 전달
    status_changed = Signal(str)

    # 전송 트리거가 발생했음을 GUI에 알림
    trigger_detected = Signal()

    def run(self):
        model_path = (
            Path(__file__).resolve().parents[1]
            / "hand_landmarker.task"
        )

        if not model_path.exists():
            self.status_changed.emit("모델 파일을 찾을 수 없습니다.")
            return

        camera = cv2.VideoCapture(0)

        if not camera.isOpened():
            self.status_changed.emit("카메라를 열 수 없습니다.")
            return

        BaseOptions = mp.tasks.BaseOptions
        HandLandmarker = mp.tasks.vision.HandLandmarker
        Options = mp.tasks.vision.HandLandmarkerOptions
        RunningMode = mp.tasks.vision.RunningMode

        options = Options(
            base_options=BaseOptions(
                model_asset_path=str(model_path)
            ),
            running_mode=RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        open_since = None
        ready = False
        last_timestamp = 0
        last_status = ""

        try:
            with HandLandmarker.create_from_options(
                options
            ) as detector:

                while not self.isInterruptionRequested():
                    success, frame = camera.read()

                    if not success:
                        self.status_changed.emit(
                            "카메라 영상을 읽을 수 없습니다."
                        )
                        break

                    frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(
                        frame, cv2.COLOR_BGR2RGB
                    )

                    mp_image = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=rgb,
                    )

                    timestamp = time.monotonic_ns() // 1_000_000
                    timestamp = max(
                        timestamp, last_timestamp + 1
                    )
                    last_timestamp = timestamp

                    result = detector.detect_for_video(
                        mp_image, timestamp
                    )

                    gesture = "손을 카메라에 보여 주세요"
                    now = time.monotonic()

                    if result.hand_landmarks:
                        landmarks = result.hand_landmarks[0]

                        tips = [8, 12, 16, 20]
                        pips = [6, 10, 14, 18]

                        fingers = [
                            landmarks[tip].y
                            < landmarks[pip].y
                            for tip, pip in zip(tips, pips)
                        ]

                        if all(fingers):
                            gesture = "손바닥 인식 중"

                            if open_since is None:
                                open_since = now

                            if now - open_since >= 0.7:
                                ready = True
                                gesture = (
                                    "준비 완료 - 주먹을 쥐세요"
                                )

                        else:
                            open_since = None

                            if not any(fingers):
                                gesture = "주먹 인식"

                                if ready:
                                    ready = False
                                    gesture = "전송 요청 감지!"
                                    self.trigger_detected.emit()
                            else:
                                gesture = "다른 손 모양"

                    else:
                        open_since = None

                    if gesture != last_status:
                        if gesture != "주먹 인식":
                            self.status_changed.emit(gesture)
                        last_status = gesture

        except Exception as error:
            self.status_changed.emit(
                f"제스처 인식 오류: {error}"
            )

        finally:
            camera.release()
            self.status_changed.emit("카메라 인식 종료")

    def stop(self):
        self.requestInterruption()
