from typing import TYPE_CHECKING

import cv2
import mediapipe as mp

from src.types import FingerEvent

if TYPE_CHECKING:
    from src.main import HandState


def start(state: "HandState"):
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    callback = state.callback

    cap = cv2.VideoCapture(0)
    with mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
    ) as hands:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            # BGR to RGB
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = hands.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            image = frame.copy()
            image[:] = 0

            if results.multi_hand_landmarks:
                import math

                finger_names = [
                    "WRIST",
                    "THUMB_CMC",
                    "THUMB_MCP",
                    "THUMB_IP",
                    "THUMB_TIP",  # 1
                    "INDEX_FINGER_MCP",
                    "INDEX_FINGER_PIP",
                    "INDEX_FINGER_DIP",
                    "INDEX_FINGER_TIP",  # 2
                    "MIDDLE_FINGER_MCP",
                    "MIDDLE_FINGER_PIP",
                    "MIDDLE_FINGER_DIP",
                    "MIDDLE_FINGER_TIP",  # 3
                    "RING_FINGER_MCP",
                    "RING_FINGER_PIP",
                    "RING_FINGER_DIP",
                    "RING_FINGER_TIP",  # 4
                    "PINKY_MCP",
                    "PINKY_PIP",
                    "PINKY_DIP",
                    "PINKY_TIP",  # 5
                ]

                def get_vec(a, b):
                    return [b["x"] - a["x"], b["y"] - a["y"], b["z"] - a["z"]]

                def vec_angle(v1, v2):
                    dot = sum([v1[i] * v2[i] for i in range(3)])
                    norm1 = math.sqrt(sum([v1[i] ** 2 for i in range(3)]))
                    norm2 = math.sqrt(sum([v2[i] ** 2 for i in range(3)]))
                    if norm1 == 0 or norm2 == 0:
                        return 0
                    cos_theta = dot / (norm1 * norm2)
                    cos_theta = max(-1, min(1, cos_theta))
                    return math.degrees(math.acos(cos_theta))

                for hand_landmarks in results.multi_hand_landmarks:
                    coords = {}
                    for idx, landmark in enumerate(hand_landmarks.landmark):
                        coords[finger_names[idx]] = {
                            "x": landmark.x,
                            "y": landmark.y,
                            "z": landmark.z,
                        }

                    # 3,4,5번째 손가락(중,약,소) 접힘 판별
                    def is_folded(finger):
                        # TIP y > MCP y 이면 접힘(손바닥 기준, y는 위가 0)
                        return coords[finger + "_TIP"]["y"] > coords[finger + "_MCP"]["y"]

                    folded = all([
                        is_folded("MIDDLE_FINGER"),
                        is_folded("RING_FINGER"),
                        is_folded("PINKY"),
                    ])

                    # 1,2번째 손가락(엄지, 검지) 펴짐 판별

                    def is_straight(finger):
                        # TIP y < MCP y 이면 펴짐
                        return coords[finger + "_TIP"]["y"] < coords[finger + "_MCP"]["y"]

                    straight = all([is_straight("THUMB"), is_straight("INDEX_FINGER")])

                    if folded and straight:
                        callback(FingerEvent.FOLD, None)
                        # 각도 계산: 엄지(THUMB), 검지(INDEX_FINGER)
                        # 엄지: CMC-MCP-TIP, 검지: MCP-PIP-TIP
                        thumb_vec1 = get_vec(coords["THUMB_CMC"], coords["THUMB_MCP"])
                        thumb_vec2 = get_vec(coords["THUMB_MCP"], coords["THUMB_TIP"])
                        thumb_angle = vec_angle(thumb_vec1, thumb_vec2)
                        if thumb_angle > 30:
                            callback(FingerEvent.THUMB_FOLD, thumb_angle)
                        elif thumb_angle < 10:
                            callback(FingerEvent.THUMB_STRAIT, thumb_angle)

                        index_vec1 = get_vec(coords["INDEX_FINGER_MCP"], coords["INDEX_FINGER_PIP"])
                        index_vec2 = get_vec(coords["INDEX_FINGER_PIP"], coords["INDEX_FINGER_TIP"])
                        index_angle = vec_angle(index_vec1, index_vec2)
                        if index_angle > 45:
                            callback(FingerEvent.INDEX_FOLD, index_angle)
                        elif index_angle < 15:
                            callback(FingerEvent.INDEX_STRAIT, index_angle)

                        # 엄지와 검지 사이의 각도 계산 (THUMB_TIP - THUMB_MCP, INDEX_FINGER_TIP - INDEX_FINGER_MCP)
                        thumb_tip_vec = get_vec(coords["THUMB_MCP"], coords["THUMB_TIP"])
                        index_tip_vec = get_vec(coords["INDEX_FINGER_MCP"], coords["INDEX_FINGER_TIP"])
                        thumb_index_angle = vec_angle(thumb_tip_vec, index_tip_vec)

                        if thumb_index_angle < 15:
                            callback(FingerEvent.THUMB_INDEX_CLOSE, thumb_index_angle)
                        elif thumb_index_angle > 25:
                            callback(FingerEvent.THUMB_INDEX_OPEN, thumb_index_angle)

                    mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                cv2.putText(image, str(state.bullet), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                # 리볼버 총알 UI 그리기
                center_x, center_y = 80, 80  # 원 중심 좌표
                radius = 50  # 바깥 원 반지름
                bullet_radius = 12  # 각 총알 원 반지름
                bullet_count = 6
                angle_step = 360 / bullet_count
                for i in range(bullet_count):
                    angle = (i * angle_step - 90) * math.pi / 180  # 12시 방향부터 시작
                    bx = int(center_x + radius * math.cos(angle))
                    by = int(center_y + radius * math.sin(angle))
                    if i < state.bullet:
                        color = (0, 255, 0)  # 초록색(남은 총알)
                    else:
                        color = (0, 100, 0)  # 어두운 초록색(빈 슬롯)
                    cv2.circle(image, (bx, by), bullet_radius, color, -1)

            cv2.imshow("Hand Tracking", image)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC 키로 종료
                break

    cap.release()
    cv2.destroyAllWindows()
