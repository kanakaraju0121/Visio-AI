#!/usr/bin/env python3
"""Capture a still image from Raspberry Pi Camera 2 or an OpenCV webcam."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

REPOSITORY_ROOT = Path(__file__).resolve().parent
PROJECT_DIR = REPOSITORY_ROOT / "visio_ai_project"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

try:
    from visio_ai.audio import say
except ImportError:
    def say(message: str) -> None:
        print(f"[TTS] {message}")

try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None  # type: ignore[assignment,misc]

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]


def _capture_picamera2() -> Tuple[bool, Optional[bytes]]:
    if Picamera2 is None or cv2 is None:
        return False, None
    camera = None
    try:
        camera = Picamera2()
        camera.configure(camera.create_still_configuration(main={"size": (1280, 720)}))
        say("Opening camera, please wait.")
        camera.start()
        time.sleep(1.0)
        for word in ("Three", "Two", "One"):
            say(word)
            time.sleep(1.0)
        frame = camera.capture_array()
        success, encoded = cv2.imencode(".jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        return (True, encoded.tobytes()) if success else (False, None)
    except Exception as exc:
        print(f"Picamera2 capture failed: {type(exc).__name__}")
        return False, None
    finally:
        if camera is not None:
            try:
                camera.stop()
            except Exception:
                pass


def _capture_opencv() -> Tuple[bool, Optional[bytes]]:
    if cv2 is None:
        return False, None
    camera = None
    try:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            return False, None
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        say("Opening camera, please wait.")
        for _ in range(8):
            camera.read()
            time.sleep(0.03)
        for word in ("Three", "Two", "One"):
            say(word)
            time.sleep(1.0)
        success, frame = camera.read()
        if not success or frame is None:
            return False, None
        encoded_ok, encoded = cv2.imencode(".jpg", frame)
        return (True, encoded.tobytes()) if encoded_ok else (False, None)
    except Exception as exc:
        print(f"OpenCV capture failed: {type(exc).__name__}")
        return False, None
    finally:
        if camera is not None:
            camera.release()


def take_picture(save_dir: Optional[str] = None) -> Optional[str]:
    """Capture an image and return its path, or ``None`` if capture fails."""
    destination = Path(save_dir) if save_dir else REPOSITORY_ROOT / "data" / "captures"
    destination.mkdir(parents=True, exist_ok=True)

    success, image_bytes = _capture_picamera2()
    if not success:
        success, image_bytes = _capture_opencv()
    if not success or not image_bytes:
        say("Failed to capture image.")
        return None

    output = destination / f"photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
    try:
        output.write_bytes(image_bytes)
    except OSError as exc:
        print(f"Could not save image: {exc}")
        say("Failed to save the picture.")
        return None

    say("Picture taken and saved.")
    print(f"Image saved to: {output}")
    return str(output)


if __name__ == "__main__":
    take_picture()
