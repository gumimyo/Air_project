import time
from pathlib import Path

import cv2
import mediapipe as mp

MODEL_PATH = Path(__file__).parent / "hand_landmarker.task"

if not MODEL_PATH.exists():
    raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {MODEL_PATH}")

CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
]

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
Options = mp.tasks.vision.HandLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode

options = Options(
    base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
    running_mode=RunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

camera = cv2.VideoCapture(0)

# 제스처 상태 관리
open_since = None
ready = False
trigger_time = 0
message = ""
last_timestamp = 0

try:
    if not camera.isOpened():
        raise RuntimeError("카메라를 열 수 없습니다.")

    with HandLandmarker.create_from_options(options) as detector:
        while True:
            success, frame = camera.read()
            if not success:
                print("카메라 영상을 가져올 수 없습니다.")
                break

            frame = cv2.flip(frame, 1)
            height, width, _ = frame.shape

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb,
            )

            # VIDEO 모드에서는 타임스탬프가 계속 증가해야 함
            timestamp = time.monotonic_ns() // 1_000_000
            timestamp = max(timestamp, last_timestamp + 1)
            last_timestamp = timestamp

            result = detector.detect_for_video(mp_image, timestamp)

            gesture = "No hand"
            now = time.monotonic()

            if result.hand_landmarks:
                landmarks = result.hand_landmarks[0]
                points = [
                    (int(p.x * width), int(p.y * height))
                    for p in landmarks
                ]

                for start, end in CONNECTIONS:
                    cv2.line(
                        frame, points[start], points[end],
                        (0, 255, 0), 2,
                    )

                for x, y in points:
                    cv2.circle(frame, (x, y), 4, (0, 100, 255), -1)

                # 네 손가락 끝이 아래 관절보다 위에 있는지 확인
                tips = [8, 12, 16, 20]
                pips = [6, 10, 14, 18]
                fingers = [
                    landmarks[tip].y < landmarks[pip].y
                    for tip, pip in zip(tips, pips)
                ]

                if all(fingers):
                    gesture = "Open Palm"
                elif not any(fingers):
                    gesture = "Fist"
                else:
                    gesture = "Other Gesture"

                if gesture == "Open Palm":
                    if open_since is None:
                        open_since = now

                    # 손바닥을 0.7초 이상 유지하면 준비
                    if now - open_since >= 0.7:
                        ready = True

                else:
                    open_since = None

                    # 준비된 상태에서 주먹을 쥐면 트리거
                    if ready and gesture == "Fist":
                        trigger_time = now
                        message = "Transfer request detected!"
                        ready = False

            else:
                open_since = None

            # 트리거 메시지는 2초 동안 표시
            if now - trigger_time < 2:
                display_text = message
                color = (0, 200, 0)
            elif ready:
                display_text = "READY - Make a fist"
                color = (0, 200, 0)
            else:
                display_text = f"Gesture: {gesture}"
                color = (255, 255, 255)

            cv2.putText(
                frame, display_text, (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2,
            )

            cv2.imshow("GestureDrop - Trigger Test", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

finally:
    camera.release()
    cv2.destroyAllWindows()
