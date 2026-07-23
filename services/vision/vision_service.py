#!/usr/bin/env python3
"""Publica landmarks de manos desde la camara local de una Jetson.

El proceso no envia video a Mimix Web. Publica solo coordenadas normalizadas
por HTTP, para que Chromium conserve la GPU disponible para Three.js.
"""

from __future__ import annotations

import logging
import os
import signal
import time
from dataclasses import dataclass
from typing import Any

import cv2
import mediapipe as mp
import requests


logging.basicConfig(
    level=os.getenv("MIMIX_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("mimix.vision")
RUNNING = True


@dataclass(frozen=True)
class Settings:
    api_url: str
    camera_index: int
    width: int
    height: int
    fps: float
    camera_pipeline: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            api_url=os.getenv(
                "MIMIX_VISION_API_URL",
                "http://127.0.0.1:4000/api/vision/hand-landmarks",
            ),
            camera_index=int(os.getenv("MIMIX_CAMERA_INDEX", "0")),
            width=int(os.getenv("MIMIX_CAMERA_WIDTH", "640")),
            height=int(os.getenv("MIMIX_CAMERA_HEIGHT", "480")),
            fps=float(os.getenv("MIMIX_VISION_FPS", "15")),
            camera_pipeline=os.getenv("MIMIX_CAMERA_PIPELINE") or None,
        )


def stop_service(_signal: int, _frame: Any) -> None:
    global RUNNING
    RUNNING = False


def open_camera(settings: Settings) -> cv2.VideoCapture:
    if settings.camera_pipeline:
        LOGGER.info("Abriendo camara con pipeline GStreamer")
        camera = cv2.VideoCapture(settings.camera_pipeline, cv2.CAP_GSTREAMER)
    else:
        LOGGER.info("Abriendo camara V4L2 en /dev/video%s", settings.camera_index)
        camera = cv2.VideoCapture(settings.camera_index, cv2.CAP_V4L2)

    if not camera.isOpened():
        raise RuntimeError(
            "No se pudo abrir la camara. Verifica MIMIX_CAMERA_INDEX o "
            "MIMIX_CAMERA_PIPELINE para una camara CSI."
        )

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, settings.width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.height)
    camera.set(cv2.CAP_PROP_FPS, settings.fps)
    return camera


def hand_payload(results: Any) -> dict[str, Any]:
    landmarks: list[list[dict[str, float]]] = []
    handedness: list[list[dict[str, Any]]] = []

    for index, hand in enumerate(results.multi_hand_landmarks or []):
        landmarks.append(
            [
                {"x": point.x, "y": point.y, "z": point.z}
                for point in hand.landmark
            ]
        )
        classification = results.multi_handedness[index].classification[0]
        handedness.append(
            [
                {
                    "categoryName": classification.label,
                    "score": classification.score,
                }
            ]
        )

    return {
        "landmarks": landmarks,
        "handedness": handedness,
        "timestamp": int(time.time() * 1000),
        "source": "jetson-native",
    }


def publish(session: requests.Session, api_url: str, payload: dict[str, Any]) -> None:
    try:
        response = session.post(api_url, json=payload, timeout=0.75)
        response.raise_for_status()
    except requests.RequestException as error:
        # Mimix Web puede arrancar despues. Se reintenta en el siguiente frame.
        LOGGER.warning("No se pudo publicar vision en Mimix Web: %s", error)


def run() -> None:
    settings = Settings.from_environment()
    frame_interval = 1 / max(settings.fps, 1)
    camera = open_camera(settings)
    session = requests.Session()
    hands_api = mp.solutions.hands

    LOGGER.info(
        "Vision iniciada (%sx%s a %.1f FPS) -> %s",
        settings.width,
        settings.height,
        settings.fps,
        settings.api_url,
    )

    try:
        with hands_api.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=0.65,
            min_tracking_confidence=0.55,
        ) as hands:
            while RUNNING:
                started_at = time.monotonic()
                ok, frame = camera.read()
                if not ok:
                    LOGGER.warning("La camara no entrego un frame; reintentando")
                    time.sleep(0.2)
                    continue

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb_frame.flags.writeable = False
                results = hands.process(rgb_frame)
                publish(session, settings.api_url, hand_payload(results))

                remaining = frame_interval - (time.monotonic() - started_at)
                if remaining > 0:
                    time.sleep(remaining)
    finally:
        session.close()
        camera.release()
        LOGGER.info("Vision detenida; camara liberada")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop_service)
    signal.signal(signal.SIGTERM, stop_service)
    run()
