"""Small hardware-independent regression tests for Visio-AI helpers."""

from __future__ import annotations

import os
import sys
import types
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = REPOSITORY_ROOT / "visio_ai_project"
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(REPOSITORY_ROOT))


class AIHelperTests(unittest.TestCase):
    def test_sentence_limit(self):
        from visio_ai.ai import _limit_sentences

        self.assertEqual(_limit_sentences("First. Second. Third."), "First. Second.")
        self.assertEqual(_limit_sentences("One sentence only."), "One sentence only.")
        self.assertEqual(_limit_sentences(""), "I could not generate a response.")

    def test_ai_disabled_without_key(self):
        from visio_ai.ai import is_ai_available

        original = os.environ.pop("GROQ_API_KEY", None)
        try:
            self.assertFalse(is_ai_available())
        finally:
            if original is not None:
                os.environ["GROQ_API_KEY"] = original


class MotorConfigurationTests(unittest.TestCase):
    def test_speed_range_validation_without_gpio_hardware(self):
        fake_gpio = types.ModuleType("RPi.GPIO")
        fake_gpio.BCM = 1
        fake_gpio.OUT = 1
        fake_gpio.HIGH = 1
        fake_gpio.LOW = 0
        fake_gpio.setmode = lambda *_: None
        fake_gpio.setwarnings = lambda *_: None
        fake_gpio.setup = lambda *_: None
        fake_gpio.PWM = lambda *_: None
        fake_gpio.cleanup = lambda *_: None
        fake_gpio.output = lambda *_: None
        fake_rpi = types.ModuleType("RPi")
        fake_rpi.GPIO = fake_gpio
        sys.modules.setdefault("RPi", fake_rpi)
        sys.modules.setdefault("RPi.GPIO", fake_gpio)

        from motor_control import L298N_MotorDriver

        L298N_MotorDriver._validate_speed(0)
        L298N_MotorDriver._validate_speed(50)
        L298N_MotorDriver._validate_speed(100)
        for invalid in (-1, 101, "fast", None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    L298N_MotorDriver._validate_speed(invalid)


class PathConfigurationTests(unittest.TestCase):
    def test_stream_server_path_is_repository_relative(self):
        from visio_ai.stream import SERVER_SCRIPT, REPOSITORY_ROOT

        self.assertEqual(SERVER_SCRIPT, REPOSITORY_ROOT / "yolo_stream_server.py")


if __name__ == "__main__":
    unittest.main()
