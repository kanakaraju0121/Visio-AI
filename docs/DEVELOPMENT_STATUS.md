# Development status and known limitations

This document separates what is present in the uploaded source package from behavior that still needs physical validation. Static inspection is not a substitute for testing on the target robot.

## Present in the source tree

A small standard-library test suite covers the sentence limiter, optional-AI configuration behavior, motor speed range validation (with mocked GPIO import) and repository-relative stream-server path. These tests do not communicate with physical hardware.

- L298N motor driver class using Raspberry Pi BCM GPIO pins and software PWM.
- Voice command loop based on `SpeechRecognition` and the Google speech-recognition endpoint.
- Text-to-speech helper based on `espeak` and `aplay`.
- PiCamera2 / OpenCV camera capture paths.
- Ultralytics YOLOv8-based object-detection preview and MJPEG stream scripts.
- Optional Groq conversational API integration.
- Haar-cascade face detection and a simple grayscale feature-storage / comparison prototype.

## Not demonstrated by the uploaded source package

- A reproducible end-to-end test log on a named Raspberry Pi OS and board revision.
- Measured object-detection precision, recall, mAP, latency, frame rate or power consumption.
- Quantified face-recognition accuracy or false-accept / false-reject rates.
- Offline speech recognition. The main voice path uses `recognize_google`.
- Autonomous navigation, mapping, SLAM, PID speed control, obstacle avoidance or closed-loop localization.
- A trained custom AI model or a custom-trained YOLO dataset.

Do not add these claims to a CV, LinkedIn post or README until they have been implemented and validated.

## Important technical limitations to address

1. **Face matching is a prototype.** `register_face.py` flattens resized grayscale face crops and compares them with Euclidean distance. This is not a robust face-embedding model. The threshold is not calibrated and must not be used for identity or access-control decisions.
2. **Network stream security.** The Flask stream servers are development servers. They now bind to localhost by default; changing `VISIO_HOST` to `0.0.0.0` exposes them to the LAN. They do not implement user authentication. Use only on a trusted isolated network, never port-forward them to the internet.
3. **Voice recognition depends on the network.** `recognize_google` sends audio to an external speech service. Do not describe the current main application as offline or private local speech recognition.
4. **Motor polarity is build-specific.** Software direction labels assume that both motor channels are wired so `INx=HIGH/LOW` corresponds to the named direction. Raise the wheels and verify the actual chassis direction before operating on the floor. Reverse a motor's wiring or GPIO logic if required by the physical assembly.
5. **Runtime dependencies are platform-specific.** RPi.GPIO, Picamera2, PortAudio, ALSA and espeak must be installed and configured on the target Raspberry Pi OS.
6. **Hardware cleanup and faults need physical tests.** Validate camera failure, microphone unavailable, network loss, AI API error, low battery, stalled motors and Ctrl+C shutdown.
7. **The current YOLO model is a generic pretrained model.** A successful detection result is not evidence of custom model training or a specific application accuracy.

## Recommended next work

### Priority 1 — reliability and safety
- Test motor direction with wheels raised and verify emergency stop behavior.
- Add a hardware-level motor power cutoff and a command timeout/watchdog.
- Test camera, microphone, speaker and GPIO initialization independently.
- Replace the Flask development server with a hardened deployment method if remote viewing is required.
- Add authentication before allowing access from other devices on a shared network.

### Priority 2 — software quality
- Add unit tests for command parsing, speed validation and configuration handling using mocked hardware modules.
- Add structured logging and explicit error messages for missing devices.
- Add a single configuration module for GPIO pins, camera index, model name, stream bind address and ports.
- Pin and validate dependency versions on the exact Raspberry Pi OS image.

### Priority 3 — engineering evidence
- Record Raspberry Pi model, OS release, Python version, camera model, motor driver, battery and test conditions.
- Measure end-to-end speech-command latency, YOLO frame rate and average CPU/memory usage.
- Record a short reproducible test procedure and include genuine output screenshots / demo video.
- If face matching is retained, replace raw pixel vectors with a validated embedding approach and document privacy, consent and evaluation metrics.
