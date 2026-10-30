# Source audit — Visio-AI

## Overall assessment

The uploaded archive contains a real Python prototype with meaningful integration work across Raspberry Pi GPIO, an L298N motor driver, speech recognition, text-to-speech, camera capture, Ultralytics YOLO, Flask streaming and optional Groq API responses. It is a credible student robotics project foundation, but the initial archive was not yet ready for a polished public GitHub release because it mixed machine-specific paths, inconsistent setup instructions, placeholder API-key literals, duplicate utilities and unqualified prototype claims.

The repository has been reorganized and the main release blockers below have been addressed. This is a source-level cleanup; the robot has not been physically tested as part of this review.

## Source-by-source review

| Original source | What it contains | Review and changes |
|---|---|---|
| `sr_mic_test.py` | Main speech-command loop, motor actions, camera commands, Groq fallback | Removed user-specific absolute import paths; added repository-relative imports; made AI availability check dynamic; corrected the code-level forward/backward mapping to match the command labels. Motor direction still requires wheels-up verification on the actual chassis. |
| `motor_control.py` | L298N direction outputs and PWM on six BCM GPIO signals | Added 0–100% speed validation. Wiring, polarity, current capability and emergency stop still require physical verification. |
| `visio_ai/ai.py` | Optional Groq chat completion | Removed placeholder hard-coded key and now reads `GROQ_API_KEY` / `GROQ_MODEL` from environment variables. |
| `visio_ai/audio.py` | `espeak` WAV generation and `aplay` playback | Uses ALSA default playback device, handles missing utilities more gracefully and keeps console output available when TTS is unavailable. |
| `visio_ai/stream.py` | Starts/stops the YOLO web server child process | Replaced fixed `/home/...` path with a repository-relative path; uses the active Python interpreter; redirects child output to an ignored log file rather than unread pipes; improves cleanup. |
| `camera_access.py` | PiCamera2/OpenCV still-photo capture | Removed fixed home-directory path; uses repository-relative imports and stores captures under ignored `data/captures/`; added guarded camera cleanup. |
| `camera_capture.py` | Still capture and Haar-cascade face boxes | Made PiCamera2 import lazy and moved camera shutdown into `finally`, allowing file-only face detection without PiCamera2 being installed. |
| `object_detection_yolo.py` | YOLO live camera preview and detection summary | Main preview loop now reuses one inference result for both drawing and periodic reporting, instead of running YOLO a second time every tenth frame. |
| `live_face_detection.py` | YOLO detection and automatic image capture for selected object classes | Kept as a separate utility. It detects selected COCO objects; its filename should not be interpreted as evidence of biometric face recognition. Hardware and model behavior require testing. |
| `yolo_stream_server.py` | Flask MJPEG stream with YOLO overlays | Default bind changed from all interfaces to localhost; certificate generation no longer uses `os.system`; bind and ports are configurable. The Flask development server has no login/authentication. |
| `register_face.py` | Face enrollment using Haar detection and flattened grayscale pixel features | Replaced machine-specific data paths and validates CLI names. The stored feature method is basic and experimental, not a production face-recognition algorithm. |
| `video_stream_server.py` | Camera stream, face matching and HTTP enrollment endpoint | Replaced machine-specific data/certificate paths; added upload filename sanitization and a 5 MiB request limit; defaults to localhost. The endpoint is unauthenticated and must not be exposed to untrusted networks. |
| `groq_assistant.py`, `groq_repl.py` | Two simple, duplicate Groq terminal clients with placeholder keys | Removed duplicate scripts and replaced them with one environment-configured `tools/groq_cli.py`. |
| `tts_rpi.py` | Standalone command-line TTS helper | Retained as a separate utility; the main robot package uses `visio_ai/audio.py`. |
| `requirements.txt` files | Python dependencies | Centralized dependencies at repository root; nested requirements file delegates to the root requirements file. Pi-specific apt packages are documented separately. |
| `.env.example`, `.gitignore` | Local config and Git exclusions | Added configurable model/stream settings and strengthened exclusions for local data, face material, captures, model weights, logs and TLS keys. |
| `README.md` files | Project setup and usage documentation | Rebuilt one main README with scope, feature matrix, hardware GPIO table, setup, commands, folder map and honest limitations. Removed the outdated nested README. |
| `LICENSE` | MIT license | Retained. |
| `opencv_cascades/haarcascade_frontalface_default.xml` | OpenCV face detector cascade | Retained because the face-enrollment and video-stream scripts reference it. |
| `docs/hardware/*.jpg` | Two hardware photos | Retained as visual evidence of the chassis and electronics assembly. |

## Findings that matter for public presentation

1. The main voice recognition path uses `recognize_google`; it is not offline speech recognition.
2. Groq responses are cloud-based and optional; they need a valid key and network access.
3. The face-matching method compares flattened grayscale face pixels. It is a learning prototype and does not establish reliable face identity recognition.
4. The YOLO scripts use a generic pretrained YOLOv8 model; there is no custom training evidence in the supplied archive.
5. The source archive contains no reproducible performance report for FPS, inference latency, accuracy, power consumption or battery life.
6. The Flask stream endpoints do not implement authentication. Localhost is the safe default; do not expose them to the public internet.
7. The supplied robot photographs support the presence of a Raspberry Pi-based chassis, motor driver, camera assembly and audio speaker. They do not prove the internal wiring, exact board revision or electrical ratings.

## Validation performed on the prepared source package

- Normalized all ZIP member paths to portable POSIX paths and established one `visio-ai/` repository root.
- Compiled Python sources with `python -m compileall -q .` — passed.
- Ran four hardware-independent unit tests — passed.
- Checked the source for the original `/home/kanakaraju` hard-coded path and literal `YOUR_GROQ_API_KEY` placeholder — none remain in Python source.

## Validation not performed

No physical Raspberry Pi, camera, microphone, speaker, L298N board, motor supply, or robot chassis was available for this review. The browser stream, YOLO runtime, GPIO outputs, speech-recognition service, TTS playback and Groq calls have not been end-to-end exercised here. The repository should be described as a source-reviewed prototype until those tests are run and recorded.
