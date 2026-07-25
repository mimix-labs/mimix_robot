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
from glob import glob
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Condition, Thread
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
    camera_index: str
    width: int
    height: int
    fps: float
    camera_pipeline: str | None
    video_bind_host: str
    video_port: int
    video_fps: float
    video_jpeg_quality: int

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            api_url=os.getenv(
                "MIMIX_VISION_API_URL",
                "http://127.0.0.1:4000/api/vision/hand-landmarks",
            ),
            camera_index=os.getenv("MIMIX_CAMERA_INDEX", "auto").strip(),
            width=int(os.getenv("MIMIX_CAMERA_WIDTH", "640")),
            height=int(os.getenv("MIMIX_CAMERA_HEIGHT", "480")),
            fps=float(os.getenv("MIMIX_VISION_FPS", "15")),
            camera_pipeline=os.getenv("MIMIX_CAMERA_PIPELINE") or None,
            video_bind_host=os.getenv("MIMIX_VIDEO_BIND_HOST", "127.0.0.1"),
            video_port=int(os.getenv("MIMIX_VIDEO_PORT", "8081")),
            video_fps=float(os.getenv("MIMIX_VIDEO_FPS", "15")),
            video_jpeg_quality=int(os.getenv("MIMIX_VIDEO_JPEG_QUALITY", "60")),
        )


def stop_service(_signal: int, _frame: Any) -> None:
    global RUNNING
    RUNNING = False


def configure_camera(camera: cv2.VideoCapture, settings: Settings) -> None:
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, settings.width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.height)
    camera.set(cv2.CAP_PROP_FPS, settings.fps)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)


def available_camera_indexes(requested_index: str) -> list[int]:
    detected = sorted({
        int(device.removeprefix("/dev/video"))
        for device in glob("/dev/video*")
        if device.removeprefix("/dev/video").isdigit()
    })
    if requested_index.lower() == "auto":
        return detected

    try:
        requested = int(requested_index)
    except ValueError as error:
        raise ValueError("MIMIX_CAMERA_INDEX debe ser un número o 'auto'.") from error
    return [requested, *(index for index in detected if index != requested)]


def wait_for_first_frame(camera: cv2.VideoCapture, label: str) -> Any | None:
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        ok, frame = camera.read()
        if ok and frame is not None and frame.size:
            height, width = frame.shape[:2]
            LOGGER.info(
                "Cámara %s entregó imagen %sx%s (brillo medio %.1f)",
                label,
                width,
                height,
                float(frame.mean()),
            )
            return frame
        time.sleep(0.05)
    return None


def open_camera(settings: Settings) -> tuple[cv2.VideoCapture, Any]:
    if settings.camera_pipeline:
        LOGGER.info("Abriendo camara con pipeline GStreamer")
        camera = cv2.VideoCapture(settings.camera_pipeline, cv2.CAP_GSTREAMER)
        if not camera.isOpened():
            raise RuntimeError("No se pudo abrir MIMIX_CAMERA_PIPELINE.")
        configure_camera(camera, settings)
        frame = wait_for_first_frame(camera, "CSI")
        if frame is not None:
            return camera, frame
        camera.release()
        raise RuntimeError("El pipeline CSI abrió, pero no entregó ninguna imagen.")

    candidates = available_camera_indexes(settings.camera_index)
    if not candidates:
        raise RuntimeError("No se encontraron dispositivos /dev/video*. Conecta una cámara USB o configura MIMIX_CAMERA_PIPELINE para una CSI.")

    for camera_index in candidates:
        LOGGER.info("Probando cámara V4L2 en /dev/video%s", camera_index)
        camera = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
        if not camera.isOpened():
            LOGGER.info("/dev/video%s no se pudo abrir", camera_index)
            camera.release()
            continue

        configure_camera(camera, settings)
        frame = wait_for_first_frame(camera, f"/dev/video{camera_index}")
        if frame is not None:
            LOGGER.info("Usando MIMIX_CAMERA_INDEX=%s", camera_index)
            return camera, frame

        LOGGER.warning("/dev/video%s abrió pero no entregó frames; probando el siguiente", camera_index)
        camera.release()

    raise RuntimeError(
        "Ninguna cámara V4L2 entregó imagen. Revisa cable, alimentación y permisos de /dev/video*."
    )


class LatestJpegFrame:
    """Conserva el JPEG mas reciente para los navegadores conectados."""

    def __init__(self) -> None:
        self._condition = Condition()
        self._frame: bytes | None = None
        self._version = 0

    def publish(self, frame: bytes) -> None:
        with self._condition:
            self._frame = frame
            self._version += 1
            self._condition.notify_all()

    def wait_for_next(self, previous_version: int) -> tuple[bytes | None, int]:
        with self._condition:
            self._condition.wait_for(
                lambda: self._version != previous_version or not RUNNING,
                timeout=2,
            )
            return self._frame, self._version


def create_video_server(frame_store: LatestJpegFrame, settings: Settings) -> ThreadingHTTPServer:
    class MjpegHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path != "/stream.mjpg":
                self.send_error(404, "Use /stream.mjpg")
                return

            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.end_headers()

            version = 0
            try:
                while RUNNING:
                    frame, version = frame_store.wait_for_next(version)
                    if frame is None:
                        continue
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    server = ThreadingHTTPServer((settings.video_bind_host, settings.video_port), MjpegHandler)
    Thread(target=server.serve_forever, name="mimix-mjpeg", daemon=True).start()
    LOGGER.info(
        "Video MJPEG disponible en http://%s:%s/stream.mjpg",
        settings.video_bind_host,
        settings.video_port,
    )
    return server


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
    video_interval = 1 / max(settings.video_fps, 1)
    camera, first_frame = open_camera(settings)
    session = requests.Session()
    hands_api = mp.solutions.hands
    frame_store = LatestJpegFrame()
    video_server = create_video_server(frame_store, settings)
    last_video_frame_at = 0.0

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
                if first_frame is not None:
                    ok, frame = True, first_frame
                    first_frame = None
                else:
                    ok, frame = camera.read()
                if not ok:
                    LOGGER.warning("La camara no entrego un frame; reintentando")
                    time.sleep(0.2)
                    continue

                now = time.monotonic()
                if now - last_video_frame_at >= video_interval:
                    encoded, jpeg_frame = cv2.imencode(
                        ".jpg",
                        frame,
                        [cv2.IMWRITE_JPEG_QUALITY, settings.video_jpeg_quality],
                    )
                    if encoded:
                        frame_store.publish(jpeg_frame.tobytes())
                    last_video_frame_at = now

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb_frame.flags.writeable = False
                results = hands.process(rgb_frame)
                publish(session, settings.api_url, hand_payload(results))

                remaining = frame_interval - (time.monotonic() - started_at)
                if remaining > 0:
                    time.sleep(remaining)
    finally:
        video_server.shutdown()
        video_server.server_close()
        session.close()
        camera.release()
        LOGGER.info("Vision detenida; camara liberada")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop_service)
    signal.signal(signal.SIGTERM, stop_service)
    run()
