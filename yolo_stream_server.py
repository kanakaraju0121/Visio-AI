#!/usr/bin/env python3
"""
YOLO Object Detection Video Streaming Server
Streams live video with YOLO object detection over HTTP/HTTPS
"""

import cv2
import os
import time
import logging
from collections import deque
from flask import Flask, Response, render_template_string
import ssl
import subprocess
from pathlib import Path

# Tuning parameters
DETECTION_INTERVAL = 3  # run YOLO every N frames
JPEG_QUALITY = 45       # lower quality for faster transmission

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  YOLO not installed. Install with: pip install ultralytics")

app = Flask(__name__)
REPOSITORY_ROOT = Path(__file__).resolve().parent

# Global variables
camera = None
yolo_model = None
fps_deque = deque(maxlen=30)
fps_start_time = time.time()
frame_count = 0
last_detected_objects = {}  # Track last detected objects to avoid spam

# Suppress Flask error logging for common SSL disconnection errors
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Filter out SSL and connection errors from logs
class ConnectionErrorFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # Filter out common connection errors that are normal
        if any(keyword in msg for keyword in ['SSL', 'Broken pipe', 'BrokenPipeError', 'UNEXPECTED_EOF']):
            return False
        return True

logging.getLogger('werkzeug').addFilter(ConnectionErrorFilter())

def load_yolo_model(model_size='nano'):
    """Load YOLO model"""
    if not YOLO_AVAILABLE:
        return None
    
    model_size_map = {
        'nano': 'n',
        'small': 's',
        'medium': 'm',
        'large': 'l',
        'xlarge': 'x'
    }
    
    if model_size not in model_size_map:
        model_size = 'nano'
    
    model_name = f'yolov8{model_size_map[model_size]}'
    print(f"📦 Loading YOLO model: {model_name}")
    
    try:
        model = YOLO(model_name)
        print(f"✅ Model loaded successfully")
        return model
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return None

def init_camera():
    """Initialize camera"""
    global camera
    
    if PICAMERA2_AVAILABLE:
        try:
            camera = Picamera2()
            # Lower resolution for faster streaming (320x240)
            preview_config = camera.create_preview_configuration(
                main={"size": (320, 240)}
            )
            camera.configure(preview_config)
            camera.start()
            print("✅ Camera initialized (Picamera2) - Low resolution mode (320x240)")
            return True
        except Exception as e:
            print(f"⚠️  Picamera2 error: {e}")
            camera = None
    
    # Fallback to OpenCV VideoCapture
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("❌ Error: Could not open camera")
        return False
    # Lower resolution for faster streaming
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    # Try to force MJPG to reduce CPU usage
    try:
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        camera.set(cv2.CAP_PROP_FOURCC, fourcc)
        camera.set(cv2.CAP_PROP_FPS, 30)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    except Exception:
        pass
    print("✅ Camera initialized (OpenCV VideoCapture) - Low resolution mode (320x240)")
    return True

# Cache last annotated frame to reuse when skipping detection
_last_annotated = None


def get_frame():
    """Get frame from camera with YOLO object detection"""
    global camera, yolo_model, fps_start_time, fps_deque, frame_count, last_detected_objects, _last_annotated
    
    if camera is None or yolo_model is None:
        return None
    
    # Get frame
    if PICAMERA2_AVAILABLE and isinstance(camera, Picamera2):
        frame = camera.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    else:
        ret, frame = camera.read()
        if not ret:
            return None
    
    # Ensure frame size 320x240 for consistent processing/display
    if frame.shape[1] != 320 or frame.shape[0] != 240:
        frame_resized = cv2.resize(frame, (320, 240))
    else:
        frame_resized = frame

    # Decide whether to run detection on this frame
    run_detection = (frame_count % DETECTION_INTERVAL == 0)

    if run_detection:
        # Run YOLO detection with small imgsz for speed
        results = yolo_model(frame_resized, conf=0.25, verbose=False, imgsz=320)
        annotated_frame = results[0].plot()

        # Extract detected objects
        detected_objects = {}
        try:
            if hasattr(results[0], 'boxes') and results[0].boxes is not None:
                for box in results[0].boxes:
                    class_id = int(box.cls[0])
                    class_name = yolo_model.names[class_id]
                    confidence = float(box.conf[0])
                    if confidence > 0.25:
                        detected_objects[class_name] = detected_objects.get(class_name, 0) + 1
        except (AttributeError, IndexError):
            detected_objects = {}

        # Log occasionally or when changed
        if frame_count % 10 == 0 or detected_objects != last_detected_objects:
            if detected_objects:
                obj_list = [f"{name}({count})" for name, count in detected_objects.items()]
                print(f"🔍 Detected: {', '.join(obj_list)}")
            else:
                print("🔍 No objects detected")
            last_detected_objects = detected_objects.copy()

        # Save last annotated
        _last_annotated = annotated_frame
    else:
        # Reuse last annotated frame if available
        if _last_annotated is not None:
            annotated_frame = _last_annotated.copy()
        else:
            annotated_frame = frame_resized

    # FPS calc
    fps_end_time = time.time()
    fps = 1.0 / (fps_end_time - fps_start_time) if fps_start_time else 0
    fps_deque.append(fps)
    fps_start_time = fps_end_time
    avg_fps = sum(fps_deque) / len(fps_deque) if fps_deque else 0

    frame_count += 1

    # Overlay metrics
    cv2.putText(annotated_frame, f"FPS: {avg_fps:.1f}", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    try:
        detection_count = len(results[0].boxes) if run_detection and hasattr(results[0], 'boxes') and results[0].boxes is not None else 0
    except Exception:
        detection_count = 0
    cv2.putText(annotated_frame, f"Objects: {detection_count}", (10, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Encode JPEG
    ret, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ret:
        return None
    
    return buffer.tobytes()


def generate_frames():
    """Generator function for video streaming"""
    try:
        while True:
            frame_bytes = get_frame()
            if frame_bytes is None:
                time.sleep(0.02)
                continue
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            # Faster cadence; actual FPS depends on processing time
            time.sleep(0.02)
    except (BrokenPipeError, ConnectionError, OSError) as e:
        print(f"ℹ️  Client disconnected: {type(e).__name__}")
    except Exception as e:
        print(f"⚠️  Error in video stream: {e}")

# HTML template for video streaming
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>YOLO Object Detection Stream</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            background-color: #1a1a1a; 
            color: #fff;
            margin: 0;
            padding: 20px;
        }
        h1 { 
            color: #4CAF50; 
            margin-bottom: 10px;
        }
        .info {
            margin: 20px auto;
            padding: 15px;
            background-color: #2a2a2a;
            border-radius: 8px;
            max-width: 800px;
            text-align: left;
        }
        img { 
            border: 3px solid #4CAF50; 
            max-width: 100%; 
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .status {
            display: inline-block;
            padding: 5px 15px;
            background-color: #4CAF50;
            border-radius: 20px;
            margin: 10px 0;
        }
        .warning {
            color: #ff9800;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <h1>🔍 YOLO Object Detection - Live Stream</h1>
    <div class="status">🟢 Streaming Active</div>
    <br>
    <img src="{{ url_for('video_feed') }}" alt="Video Stream">
    <div class="info">
        <h3>📊 Stream Information</h3>
        <p><strong>Model:</strong> YOLOv8nano (optimized for Raspberry Pi)</p>
        <p><strong>Resolution:</strong> 320x240 (low resolution for fast streaming)</p>
        <p><strong>Detection:</strong> Real-time object detection with 80 COCO classes</p>
        <p><strong>Performance:</strong> FPS displayed on stream</p>
        <p class="warning">💡 Detected objects are shown with bounding boxes and labels</p>
        <p class="warning">💡 Press Ctrl+C on the server to stop streaming</p>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Main page with video stream"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    try:
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        # Handle connection errors gracefully
        print(f"ℹ️  Video feed connection closed: {type(e).__name__}")
        return "Connection closed", 200

@app.route('/test')
def test():
    """Test endpoint to verify server is running"""
    return f"Server is running! Camera: {'OK' if camera else 'Not initialized'}, YOLO: {'OK' if yolo_model else 'Not loaded'}"

def create_ssl_context():
    """Create SSL context with self-signed certificate"""
    cert_file = str(REPOSITORY_ROOT / 'cert.pem')
    key_file = str(REPOSITORY_ROOT / 'key.pem')
    
    if not os.path.isfile(cert_file) or not os.path.isfile(key_file):
        print("🔐 Generating self-signed SSL certificate...")
        try:
            subprocess.run([
                'openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                '-keyout', key_file, '-out', cert_file, '-days', '365',
                '-subj', '/CN=localhost',
            ], check=True, capture_output=True, text=True)
            result = 0
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"Certificate generation failed: {exc}")
            result = 1
        if result != 0:
            print("❌ Failed to generate SSL certificate")
            return None
        print("✅ SSL certificate generated")
    
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        return context
    except Exception as e:
        print(f"❌ Failed to load SSL certificate: {e}")
        return None

if __name__ == "__main__":
    # Check YOLO availability
    if not YOLO_AVAILABLE:
        print("❌ YOLO not available. Please install: pip install ultralytics")
        exit(1)
    
    # Load YOLO model
    print("\n" + "="*50)
    print("🔍 YOLO Object Detection Streaming Server")
    print("="*50)
    yolo_model = load_yolo_model('nano')
    if yolo_model is None:
        print("❌ Failed to load YOLO model. Exiting.")
        exit(1)
    
    # Initialize camera
    if not init_camera():
        print("❌ Failed to initialize camera. Exiting.")
        exit(1)
    
    print("\n" + "="*50)
    print("🌐 Starting Video Streaming Server")
    print("="*50)
    print("📹 Camera: Ready")
    print("🤖 YOLO Model: Ready")
    
    try:
        # Try to create SSL context for HTTPS
        ssl_context = create_ssl_context()
        if ssl_context:
            port = int(os.getenv('VISIO_PORT_HTTPS', '8443'))
            host = os.getenv('VISIO_HOST', '127.0.0.1')
            print("\n💡 Access the stream at:")
            print(f"   https://localhost:{port}")
            print(f"   Bind address: {host}")
            print("   (You may need to accept the self-signed certificate)")
            print("\n⚠️  Press Ctrl+C to stop the server")
            print("="*50 + "\n")
            app.run(host=host, port=port, ssl_context=ssl_context, threaded=True, debug=False)
        else:
            port = int(os.getenv('VISIO_PORT_HTTP', '8080'))
            host = os.getenv('VISIO_HOST', '127.0.0.1')
            print("\n⚠️  SSL certificate generation failed, using HTTP instead")
            print("\n💡 Access the stream at:")
            print(f"   http://localhost:{port}")
            print(f"   Bind address: {host}")
            print("\n⚠️  Press Ctrl+C to stop the server")
            print("="*50 + "\n")
            app.run(host=host, port=port, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\n\n⚠️  Server stopped by user")
    finally:
        # Cleanup
        if camera:
            if PICAMERA2_AVAILABLE and isinstance(camera, Picamera2):
                camera.stop()
            else:
                camera.release()
        print("✅ Cleanup complete")

