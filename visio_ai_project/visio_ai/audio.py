"""Linux text-to-speech helper used by the robot command loop."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile


def say(reply: str) -> None:
    """Speak text with espeak/aplay when available; always retain console output."""
    message = str(reply).strip()
    if not message:
        return
    print(f"Visio-AI: {message}")
    if not shutil.which("espeak") or not shutil.which("aplay"):
        return

    wav_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        subprocess.run(
            ["espeak", "-v", "en-us", "-s", "120", "-a", "200", "-p", "70", "-w", wav_path, message],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Use ALSA's default device instead of a machine-specific card name.
        subprocess.run(
            ["aplay", "-q", wav_path],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"TTS is unavailable: {type(exc).__name__}")
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass
