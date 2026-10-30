#!/usr/bin/env python3
"""
HTTPS Video Streaming Server with Face Detection
Streams live video from camera with face detection over HTTPS
"""

import cv2
import os
import time
import numpy as np
import pickle
from datetime import datetime
from flask import Flask, Response, render_template_string, request, jsonify
from werkzeug.utils import secure_filename
import ssl
import subprocess
from pathlib import Path

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MiB upload limit

# Global variables for camera and face detection
camera = None
face_cascade = None
face_recognizer = None
known_faces = {}  # Dictionary: {name: [encoding1, encoding2, ...]}
REPOSITORY_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPOSITORY_ROOT / 'data'
faces_dir = str(DATA_DIR / 'known_faces')
faces_data_file = str(DATA_DIR / 'faces_data.pkl')
cascade_path = str(REPOSITORY_ROOT / 'opencv_cascades' / 'haarcascade_frontalface_default.xml')

def extract_face_features(face_image):
    """Extract features from a face image for recognition"""
    # Resize to standard size for comparison
    face_resized = cv2.resize(face_image, (128, 128))
    # Convert to grayscale if needed
    if len(face_resized.shape) == 3:
        face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
    else:
        face_gray = face_resized
    # Flatten and normalize
    features = face_gray.flatten().astype(np.float32) / 255.0
    return features

def compare_faces(face_features, known_faces_dict, threshold=0.6):
    """Compare face features with known faces"""
    best_match = None
    min_distance = float('inf')
    
    for name, encodings_list in known_faces_dict.items():
        for encoding in encodings_list:
            # Calculate Euclidean distance
            distance = np.linalg.norm(face_features - encoding)
            if distance < min_distance and distance < threshold:
                min_distance = distance
                best_match = name
    
    return best_match, min_distance

def load_known_faces():
    """Load known faces from storage"""
    global known_faces
    
    if os.path.isfile(faces_data_file):
        try:
            with open(faces_data_file, 'rb') as f:
                known_faces = pickle.load(f)
            print(f"✅ Loaded {len(known_faces)} known face(s)")
            for name, encodings in known_faces.items():
                print(f"   - {name}: {len(encodings)} encoding(s)")
        except Exception as e:
            print(f"⚠️  Failed to load known faces: {e}")
            known_faces = {}
    else:
        print("ℹ️  No known faces database found. Register faces first.")
        known_faces = {}
        # Create faces directory if it doesn't exist
        os.makedirs(faces_dir, exist_ok=True)

def init_camera():
    """Initialize camera and face detection"""
    global camera, face_cascade
    
    # Load known faces
    load_known_faces()
    
    # Load face cascade
    if not os.path.isfile(cascade_path):
        print(f"❌ Error: Cascade file not found at {cascade_path}")
        return False
    
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        print("❌ Error: Could not load face cascade classifier")
        return False
    
    # Initialize camera
    if PICAMERA2_AVAILABLE:
        try:
            camera = Picamera2()
            preview_config = camera.create_preview_configuration(main={"size": (640, 480)})
            camera.configure(preview_config)
            camera.start()
            print("✅ Camera initialized (Picamera2)")
            return True
        except Exception as e:
            print(f"❌ Picamera2 error: {e}")
            camera = None
    
    # Fallback to OpenCV VideoCapture
    try:
        camera = cv2.VideoCapture(0)
        if camera.isOpened():
            print("✅ Camera initialized (OpenCV fallback)")
            return True
        else:
            print("❌ Could not open camera")
            return False
    except Exception as e:
        print(f"❌ VideoCapture error: {e}")
        return False

def get_frame():
    """Get frame from camera with face detection"""
    global camera, face_cascade
    
    if camera is None or face_cascade is None:
        return None
    
    # Get frame from Picamera2
    if PICAMERA2_AVAILABLE and isinstance(camera, Picamera2):
        frame = camera.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    # Get frame from OpenCV VideoCapture
    elif isinstance(camera, cv2.VideoCapture):
        ret, frame = camera.read()
        if not ret:
            return None
    else:
        return None
    
    # Convert to grayscale for face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    
    # Recognize and draw rectangles around detected faces
    for (x, y, w, h) in faces:
        # Extract face region
        face_roi = frame[y:y+h, x:x+w]
        
        # Recognize face if we have known faces
        name = "Unknown"
        color = (0, 0, 255)  # Red for unknown
        
        if known_faces:
            try:
                face_features = extract_face_features(face_roi)
                recognized_name, distance = compare_faces(face_features, known_faces)
                if recognized_name:
                    name = recognized_name
                    color = (0, 255, 0)  # Green for recognized
            except Exception as e:
                # If recognition fails, just show as unknown
                pass
        
        # Draw rectangle and label
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(frame, name, (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Encode frame as JPEG
    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ret:
        return None
    
    return buffer.tobytes()

def generate_frames():
    """Generator function for video streaming"""
    while True:
        frame_bytes = get_frame()
        if frame_bytes is None:
            time.sleep(0.1)
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)  # ~30 FPS

# HTML template for video streaming
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Live Video Stream - Face Detection</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #1a1a1a;
            color: #fff;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        h1 {
            color: #4CAF50;
        }
        img {
            border: 3px solid #4CAF50;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(76, 175, 80, 0.3);
            max-width: 100%;
            height: auto;
        }
        .info {
            margin-top: 20px;
            color: #aaa;
        }
    </style>
</head>
<body>
    <h1>🔴 Live Video Stream - Face Detection</h1>
    <img src="{{ url_for('video_feed') }}" alt="Video Stream">
    <div class="info">
        <p>🔴 Streaming live video from camera with face detection & recognition</p>
        <p>🟢 Green rectangles: Recognized faces (names shown)</p>
        <p>🔴 Red rectangles: Unknown faces</p>
        <p>💡 Register faces using: python3 register_face.py &lt;name&gt;</p>
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
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/test')
def test():
    """Test endpoint to verify server is running"""
    return "Server is running! Camera status: " + ("OK" if camera else "Not initialized")

@app.route('/register_face', methods=['POST'])
def register_face():
    """Register a new face from uploaded image"""
    global known_faces
    
    if 'name' not in request.form or 'image' not in request.files:
        return jsonify({'error': 'Missing name or image'}), 400
    
    name = secure_filename(request.form['name'].strip())
    if not name or len(name) > 48:
        return jsonify({'error': 'Invalid name. Use 1–48 safe filename characters.'}), 400
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No image file provided'}), 400
    
    try:
        # Read image
        image_bytes = file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'error': 'Invalid image format'}), 400
        
        # Detect faces in the image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) == 0:
            return jsonify({'error': 'No face detected in image'}), 400
        
        # Extract features from the first detected face
        x, y, w, h = faces[0]
        face_roi = image[y:y+h, x:x+w]
        face_features = extract_face_features(face_roi)
        
        # Add to known faces
        if name not in known_faces:
            known_faces[name] = []
        known_faces[name].append(face_features)
        
        # Save to file
        with open(faces_data_file, 'wb') as f:
            pickle.dump(known_faces, f)
        
        # Save face image for reference
        os.makedirs(faces_dir, exist_ok=True)
        face_filename = os.path.join(faces_dir, f"{name}_{len(known_faces[name])}.jpg")
        cv2.imwrite(face_filename, face_roi)
        
        return jsonify({
            'success': True,
            'message': f'Face registered for {name}',
            'total_encodings': len(known_faces[name])
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_ssl_context():
    """Create SSL context with self-signed certificate"""
    cert_file = str(REPOSITORY_ROOT / 'cert.pem')
    key_file = str(REPOSITORY_ROOT / 'key.pem')
    
    # Generate self-signed certificate if not exists
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
    # Initialize camera
    if not init_camera():
        print("❌ Failed to initialize camera. Exiting.")
        exit(1)
    
    print("\n" + "="*50)
    print("🌐 Starting Video Streaming Server")
    print("="*50)
    print("📹 Camera: Ready")
    print("🔍 Face Detection: Active")
    
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
            elif isinstance(camera, cv2.VideoCapture):
                camera.release()
        print("✅ Camera released")
        print("👋 Goodbye!")

