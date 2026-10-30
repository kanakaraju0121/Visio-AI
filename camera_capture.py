#!/usr/bin/env python3
"""
Script to capture a still image from the camera with face detection
"""

from datetime import datetime
import time
import cv2
import os

def detect_faces(image_path, output_path=None):
    """
    Detect faces in an image using OpenCV's Haar cascade classifier
    
    Args:
        image_path: Path to input image
        output_path: Optional path for output image with face detection. 
                     If None, adds '_faces' suffix to input filename
    
    Returns:
        Number of faces detected
    """
    # Load the Haar cascade face detector
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    if face_cascade.empty():
        print("Error: Could not load face cascade classifier")
        return 0
    
    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image from {image_path}")
        return 0
    
    # Convert to grayscale for face detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    
    # Draw rectangles around detected faces
    face_count = len(faces)
    for idx, (x, y, w, h) in enumerate(faces, 1):
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        # Add face number label
        cv2.putText(img, f'Face {idx}', 
                   (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Generate output filename if not provided
    if output_path is None:
        base, ext = os.path.splitext(image_path)
        output_path = f"{base}_faces{ext}"
    
    # Save the annotated image
    cv2.imwrite(output_path, img)
    print(f"Face detection complete: {face_count} face(s) detected")
    print(f"Annotated image saved to {output_path}")
    
    return face_count

def capture_image(filename=None, detect_faces_flag=True):
    """
    Capture a still image from the camera with optional face detection
    
    Args:
        filename: Optional filename. If not provided, uses timestamp
        detect_faces_flag: If True, detect and annotate faces in the image
    
    Returns:
        Filename of captured image, or None if camera not available
    """
    picam2 = None
    try:
        # Import lazily so image-file face detection also works without PiCamera2.
        from picamera2 import Picamera2
        picam2 = Picamera2()
        
        # Configure camera for still capture
        capture_config = picam2.create_still_configuration()
        picam2.configure(capture_config)
        
        # Start the camera
        picam2.start()
        
        # Wait a moment for camera to stabilize
        time.sleep(2)
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
        
        # Capture the image
        print(f"Capturing image to {filename}...")
        picam2.capture_file(filename)
        print(f"Image saved to {filename}")
        
        # Detect faces if requested
        if detect_faces_flag:
            face_count = detect_faces(filename)
            if face_count > 0:
                print(f"✅ Detected {face_count} face(s) in the image")
            else:
                print("ℹ️ No faces detected in the image")
        
        return filename
    except Exception as e:
        print(f"❌ Camera not available: {e}")
        print("💡 Tip: Make sure a camera is connected and accessible")
        return None
    finally:
        if picam2 is not None:
            try:
                picam2.stop()
            except Exception:
                pass

if __name__ == "__main__":
    import sys
    
    # Check for special flags
    if '--detect-faces' in sys.argv:
        # Test face detection on an existing image file
        if len(sys.argv) > 2:
            image_path = sys.argv[2]
            if os.path.isfile(image_path):
                print(f"Running face detection on {image_path}...")
                face_count = detect_faces(image_path)
                if face_count > 0:
                    print(f"✅ Detected {face_count} face(s) in the image")
                else:
                    print("ℹ️ No faces detected in the image")
            else:
                print(f"Error: File not found: {image_path}")
                sys.exit(1)
        else:
            print("Usage: python3 camera_capture.py --detect-faces <image_file>")
            sys.exit(1)
    else:
        # Normal capture mode
        filename = None
        for arg in sys.argv[1:]:
            if arg != '--no-faces' and not arg.startswith('--'):
                filename = arg
                break
        
        # Check if user wants to disable face detection
        no_faces = '--no-faces' in sys.argv
        result = capture_image(filename, detect_faces_flag=not no_faces)
        
        if result is None:
            print("\n💡 Alternative: Test face detection on an existing image:")
            print("   python3 camera_capture.py --detect-faces <image_file>")

