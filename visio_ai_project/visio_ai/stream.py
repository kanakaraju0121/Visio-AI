"""Lifecycle management for the optional YOLO browser-stream process."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, TextIO

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SERVER_SCRIPT = REPOSITORY_ROOT / "yolo_stream_server.py"
LOG_PATH = REPOSITORY_ROOT / "data" / "logs" / "yolo_stream.log"
_stream_process: Optional[subprocess.Popen] = None
_log_file: Optional[TextIO] = None


def is_stream_running() -> bool:
    return _stream_process is not None and _stream_process.poll() is None


def start_object_detection_stream() -> None:
    """Start the stream server once; output is written to an ignored local log."""
    global _stream_process, _log_file
    if is_stream_running():
        from .audio import say
        say("Object detection stream is already running.")
        return

    if not SERVER_SCRIPT.is_file():
        from .audio import say
        say("Object detection server script was not found.")
        print(f"Missing server script: {SERVER_SCRIPT}")
        return

    _close_log()
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _log_file = LOG_PATH.open("a", encoding="utf-8")
        _stream_process = subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT)],
            cwd=str(REPOSITORY_ROOT),
            stdout=_log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(1.5)
        if is_stream_running():
            from .audio import say
            say("Object detection stream started. Open the local stream address.")
            print("YOLO stream process started. Check data/logs/yolo_stream.log for details.")
        else:
            code = _stream_process.poll() if _stream_process else "unknown"
            print(f"YOLO stream failed during startup (exit code: {code}).")
            _close_log()
            _stream_process = None
            from .audio import say
            say("Could not start object detection stream.")
    except OSError as exc:
        print(f"Could not launch YOLO stream: {exc}")
        _close_log()
        _stream_process = None
        from .audio import say
        say("Could not start object detection stream.")


def _close_log() -> None:
    global _log_file
    if _log_file is not None:
        try:
            _log_file.close()
        except OSError:
            pass
        _log_file = None


def stop_object_detection_stream() -> None:
    """Stop the child server and close the log handle."""
    global _stream_process
    if not is_stream_running():
        _stream_process = None
        _close_log()
        from .audio import say
        say("Object detection stream is not running.")
        return

    from .audio import say
    say("Stopping object detection stream.")
    try:
        assert _stream_process is not None
        _stream_process.terminate()
        _stream_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _stream_process.kill()
        _stream_process.wait(timeout=2)
    finally:
        _stream_process = None
        _close_log()
    say("Object detection stream stopped.")
