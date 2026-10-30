#!/usr/bin/env python3
"""
Face Registration Script
Captures images from camera and registers faces for recognition
"""

import cv2
import os
import pickle
import numpy as np
import sys
import time
from pathlib import Path

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

# Store biometric data locally; these paths are ignored by Git.
REPOSITORY_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPOSITORY_ROOT / 'data'
faces_dir = str(DATA_DIR / 'known_faces')
faces_data_file = str(DATA_DIR / 'faces_data.pkl')
cascade_path = str(REPOSITORY_ROOT / 'opencv_cascades' / 'haarcascade_frontalface_default.xml')

def extract_face_features(face_image):
    """Extract features from a face image for recognition"""
    face_resized = cv2.resize(face_image, (128, 128))
    if len(face_resized.shape) == 3:
        face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
    else:
        face_gray = face_resized
    features = face_gray.flatten().astype(np.float32) / 255.0
    return features

def load_known_faces():
    """Load existing known faces"""
    if os.path.isfile(faces_data_file):
        try:
            with open(faces_data_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"⚠️  Failed to load known faces: {e}")
            return {}
    return {}

def save_known_faces(known_faces):
    """Save known faces to file"""
    with open(faces_data_file, 'wb') as f:
        pickle.dump(known_faces, f)

def register_face_from_camera(name):
    """Register a face by capturing from camera"""
    # Load face cascade
    if not os.path.isfile(cascade_path):
        print(f"❌ Error: Cascade file not found at {cascade_path}")
        return False
    
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        print("❌ Error: Could not load face cascade classifier")
        return False
    
    # Initialize camera
    camera = None
    if PICAMERA2_AVAILABLE:
        try:
            camera = Picamera2()
            preview_config = camera.create_preview_configuration(main={"size": (640, 480)})
            camera.configure(preview_config)
            camera.start()
            print("✅ Camera initialized (Picamera2)")
        except Exception as e:
            print(f"⚠️  Picamera2 error: {e}, trying OpenCV...")
            camera = None
    
    if camera is None:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("❌ Error: Could not open camera")
            return False
        print("✅ Camera initialized (OpenCV)")
    
    # Load existing known faces
    known_faces = load_known_faces()
    
    print(f"\n📸 Registering face for: {name}")
    print("💡 Position your face in front of the camera")
    print("💡 Will automatically capture when face is detected")
    
    capture_count = 0
    required_captures = 3  # Capture 3 images for better recognition
    frames_with_face = 0
    required_stable_frames = 5  # Require face detected in 5 consecutive frames
    
    try:
        while capture_count < required_captures:
            # Get frame
            if PICAMERA2_AVAILABLE and isinstance(camera, Picamera2):
                frame = camera.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                ret, frame = camera.read()
                if not ret:
                    print("❌ Could not read frame")
                    break
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Check if face is detected
            if len(faces) > 0:
                frames_with_face += 1
                print(f"Face detected ({frames_with_face}/{required_stable_frames} frames)...", end='\r')
                
                # Capture when face is stable for required frames
                if frames_with_face >= required_stable_frames:
                    # Capture face
                    x, y, w, h = faces[0]  # Use first detected face
                    face_roi = frame[y:y+h, x:x+w]
                    
                    # Extract features
                    face_features = extract_face_features(face_roi)
                    
                    # Add to known faces
                    if name not in known_faces:
                        known_faces[name] = []
                    known_faces[name].append(face_features)
                    
                    # Save face image
                    os.makedirs(faces_dir, exist_ok=True)
                    face_filename = os.path.join(faces_dir, f"{name}_{len(known_faces[name])}.jpg")
                    cv2.imwrite(face_filename, face_roi)
                    
                    capture_count += 1
                    print(f"\n✅ Captured {capture_count}/{required_captures} for {name}")
                    
                    # Reset counter and wait a bit before next capture
                    frames_with_face = 0
                    time.sleep(1)  # Wait 1 second before next capture
            else:
                frames_with_face = 0
                print("Looking for face...", end='\r')
            
            time.sleep(0.05)  # Small delay to prevent 100% CPU usage
        
        # Save all known faces
        if capture_count > 0:
            save_known_faces(known_faces)
            print(f"\n✅ Successfully registered {capture_count} image(s) for {name}")
            print(f"✅ Total encodings for {name}: {len(known_faces[name])}")
            return True
        else:
            print("\n⚠️  No images captured")
            return False
            
    finally:
        # Cleanup
        if camera:
            if PICAMERA2_AVAILABLE and isinstance(camera, Picamera2):
                camera.stop()
            else:
                camera.release()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 register_face.py <name>")
        print("Example: python3 register_face.py John")
        sys.exit(1)
    
    name = " ".join(sys.argv[1:]).strip()
    if not name or len(name) > 48 or any(ch in name for ch in "/\\\0"):
        print("Name must be 1–48 characters and cannot contain path separators.")
        sys.exit(2)
    success = register_face_from_camera(name)
    sys.exit(0 if success else 1)

