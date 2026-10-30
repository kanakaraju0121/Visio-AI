"""Voice command loop for the Visio-AI Raspberry Pi robot."""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

# Raspberry Pi OS may provide RPi.GPIO through the system Python packages.
SYSTEM_DIST_PACKAGES = "/usr/lib/python3/dist-packages"
if SYSTEM_DIST_PACKAGES not in sys.path:
    sys.path.append(SYSTEM_DIST_PACKAGES)

import speech_recognition as sr
from motor_control import L298N_MotorDriver
from visio_ai.audio import say
from visio_ai.ai import get_ai_response, is_ai_available
from visio_ai.stream import (
    is_stream_running,
    start_object_detection_stream,
    stop_object_detection_stream,
)


def main() -> None:
    recognizer = sr.Recognizer()
    # Tuning for less false triggers and shorter phrases
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    recognizer.non_speaking_duration = 0.5

    driver = L298N_MotorDriver(
        ena_pin=18, in1_pin=23, in2_pin=24,
        enb_pin=12, in3_pin=25, in4_pin=8
    )

    if is_ai_available():
        say("Visio A I ready with Groq AI. Say a command or ask me anything.")
    else:
        say("Visio A I ready. Say a command after the beep.")

    try:
        while True:
            try:
                with sr.Microphone() as source:
                    print("🎤 Say something...")
                    recognizer.adjust_for_ambient_noise(source, duration=1.5)
                    audio = recognizer.listen(source, timeout=6, phrase_time_limit=5)
                    print("✅ Audio captured, recognizing...")
                text = recognizer.recognize_google(audio)
                consecutive_misses = 0
            except sr.WaitTimeoutError:
                print("⏳ Listen timeout - no speech detected")
                consecutive_misses = consecutive_misses + 1 if 'consecutive_misses' in locals() else 1
                if consecutive_misses % 3 == 0:
                    from visio_ai.audio import say as _say
                    _say("I did not catch that. Please repeat.")
                continue
            except sr.UnknownValueError:
                print("❌ Could not understand audio")
                consecutive_misses = consecutive_misses + 1 if 'consecutive_misses' in locals() else 1
                if consecutive_misses % 3 == 0:
                    from visio_ai.audio import say as _say
                    _say("I did not catch that. Please repeat.")
                continue
            except sr.RequestError:
                print("⚠️ Google speech API not reachable / No internet")
                from visio_ai.audio import say as _say
                _say("Network is unavailable for recognition.")
                time.sleep(1)
                continue

            print("🗣 You said:", text)
            lower = text.lower()

            # Check for quit/exit commands
            if "quit" in lower or "exit" in lower:
                # Stop streaming server if running
                if is_stream_running():
                    stop_object_detection_stream()
                say("Goodbye! Shutting down.")
                print("👋 Exiting...")
                break

            # Check for camera/detection commands
            is_camera_command = False
            camera_keywords = ["detect face", "detect object", "detect objects", "open camera", 
                              "start camera", "start detection", "object detection", "face detection",
                              "show camera", "camera stream", "detection stream", "start stream"]
            
            for keyword in camera_keywords:
                if keyword in lower:
                    is_camera_command = True
                    start_object_detection_stream()
                    break
            
            # Check for stop camera/detection commands
            if "stop detection" in lower or "stop camera" in lower or "stop stream" in lower:
                is_camera_command = True
                stop_object_detection_stream()
            
            if is_camera_command:
                time.sleep(0.5)
                say("Anything else?")
                continue

            # Check for picture capture commands
            if any(kw in lower for kw in [
                "take picture", "take a picture", "capture picture", "capture a picture",
                "take photo", "take a photo", "capture photo", "capture a photo",
                "take image", "snap a photo", "snap picture", "snap a picture"
            ]):
                stream_was_running = is_stream_running()
                if stream_was_running:
                    say("Pausing detection to take a picture.")
                    stop_object_detection_stream()
                    time.sleep(0.4)
                try:
                    from camera_access import take_picture as _take_picture
                    _take_picture()
                except Exception as _e:
                    print(f"⚠️ Picture capture error: {_e}")
                    say("Failed to capture image.")
                finally:
                    if stream_was_running:
                        time.sleep(0.5)
                        start_object_detection_stream()
                time.sleep(0.4)
                say("Anything else?")
                continue

            # Check if it's a motor command
            is_motor_command = False

            # Motor commands with feedback (2s action then stop)
            if "forward" in lower or "move forward" in lower:
                say("Moving forward")
                driver.both_forward(50)
                time.sleep(2)
                driver.both_stop()
                is_motor_command = True
            elif "back" in lower or "backward" in lower or "move back" in lower:
                say("Moving backward")
                driver.both_backward(50)
                time.sleep(2)
                driver.both_stop()
                is_motor_command = True
            elif "turn left" in lower or "go left" in lower or "move left" in lower:
                say("Turning left")
                driver.motor1_backward(50)
                driver.motor2_forward(50)
                time.sleep(2)
                driver.both_stop()
                is_motor_command = True
            elif "turn right" in lower or "go right" in lower or "move right" in lower:
                say("Turning right")
                driver.motor1_forward(50)
                driver.motor2_backward(50)
                time.sleep(2)
                driver.both_stop()
                is_motor_command = True
            elif "stop" in lower:
                driver.both_stop()
                say("Stopped")
                is_motor_command = True

            # If not a motor command, ask Groq AI
            if not is_motor_command:
                print("🤔 Thinking...")
                ai_response = get_ai_response(text)
                say(ai_response)
                time.sleep(0.5)
                say("What else would you like to know?")
            else:
                # After motor command, also prompt for next input
                time.sleep(0.5)
                say("Anything else?")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Stop streaming server if running
        if is_stream_running():
            stop_object_detection_stream()
        driver.cleanup()


if __name__ == "__main__":
    main()


