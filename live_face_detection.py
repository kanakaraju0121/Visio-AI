#!/usr/bin/env python3
"""
Live object detection using YOLO - captures photo when objects are detected
Detects: people, bottles, mobile phones, and other common objects
"""

import cv2
import os
import time
from datetime import datetime
from collections import deque

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

# Objects to detect (COCO class names)
TARGET_OBJECTS = ['person', 'bottle', 'cell phone', 'cup', 'laptop', 'keyboard', 
                  'mouse', 'remote', 'book', 'backpack', 'handbag', 'umbrella']

def load_yolo_model(model_size='nano'):
    """Load YOLO model - using nano for best FPS on Raspberry Pi"""
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
    print(f"📦 Loading YOLO model: {model_name} (optimized for high FPS)")
    
    try:
        model = YOLO(model_name)
        print(f"✅ Model loaded successfully")
        return model
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return None

def detect_objects_capture():
    """
    Capture live video, detect objects using YOLO, and take a photo when target objects are detected
    """
    if not YOLO_AVAILABLE:
        print("❌ YOLO not available. Please install: pip install ultralytics")
        return None
    
    # Load YOLO model
    yolo_model = load_yolo_model('nano')
    if yolo_model is None:
        return None
    
    print(f"\n🎯 Looking for objects: {', '.join(TARGET_OBJECTS)}")
    print("💡 Will capture photo automatically when target objects detected")
    
    # FPS tracking
    fps_deque = deque(maxlen=30)
    fps_start_time = time.time()
    
    # Try Picamera2 first (native to Raspberry Pi - better FPS)
    if PICAMERA2_AVAILABLE:
        try:
            picam2 = Picamera2()
            preview_config = picam2.create_preview_configuration(
                main={"size": (640, 480)}  # Lower resolution for better FPS
            )
            picam2.configure(preview_config)
            picam2.start()
            print("📹 Starting live video capture (Picamera2)...")
            
            object_detected = False
            frames_with_object = 0
            required_frames = 2  # Reduced for faster detection
            frame_skip = 5  # Process every 5th frame for better FPS
            frame_count = 0
            
            while True:
                # Get frame from Picamera2
                frame = picam2.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                frame_count += 1
                
                # Skip frames - only process every Nth frame
                if frame_count % frame_skip != 0:
                    # Still update FPS counter (use camera FPS, not processing FPS)
                    fps_end_time = time.time()
                    fps = 1.0 / (fps_end_time - fps_start_time) if fps_start_time else 0
                    fps_deque.append(fps)
                    fps_start_time = fps_end_time
                    avg_fps = sum(fps_deque) / len(fps_deque) if fps_deque else 0
                    # Show camera FPS for skipped frames
                    print(f"Looking for objects... | Camera FPS: {avg_fps:.1f}", end='\r')
                    continue
                
                # Run YOLO detection (optimized for speed - smaller image size)
                # Use 320 instead of 640 for much faster processing
                results = yolo_model(frame, conf=0.25, verbose=False, imgsz=320, half=False)
                
                # Check for target objects
                detected_objects = []
                if results[0].boxes is not None:
                    for box in results[0].boxes:
                        class_id = int(box.cls[0])
                        class_name = yolo_model.names[class_id]
                        confidence = float(box.conf[0])
                        
                        if class_name in TARGET_OBJECTS and confidence > 0.25:
                            detected_objects.append((class_name, confidence, box.xyxy[0].tolist()))
                
                # Calculate and display FPS (only count processed frames)
                fps_end_time = time.time()
                processing_time = fps_end_time - fps_start_time
                fps = 1.0 / processing_time if processing_time > 0 else 0
                fps_deque.append(fps)
                fps_start_time = fps_end_time
                avg_fps = sum(fps_deque) / len(fps_deque) if fps_deque else 0
                # Adjust effective FPS based on frame skipping
                effective_fps = avg_fps / frame_skip
                
                # Check if target objects detected
                if len(detected_objects) > 0:
                    frames_with_object += 1
                    obj_names = [obj[0] for obj in detected_objects]
                    unique_objs = list(set(obj_names))
                    print(f"🔍 Detected: {', '.join(unique_objs)} ({frames_with_object}/{required_frames} frames) | FPS: {effective_fps:.1f}", end='\r')
                    
                    if frames_with_object >= required_frames and not object_detected:
                        object_detected = True
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"capture_objects_{timestamp}.jpg"
                        
                        # Draw annotations on frame
                        annotated_frame = results[0].plot()
                        
                        # Add FPS to frame
                        cv2.putText(annotated_frame, f"FPS: {avg_fps:.1f}", (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        # Save original and annotated versions
                        cv2.imwrite(filename, frame)
                        annotated_filename = f"capture_objects_{timestamp}_annotated.jpg"
                        cv2.imwrite(annotated_filename, annotated_frame)
                        
                        print(f"\n✅ Objects detected! Photo saved to {filename}")
                        print(f"✅ Annotated version saved to {annotated_filename}")
                        print(f"📊 Detected objects: {', '.join(unique_objs)}")
                        print(f"⚡ Average FPS: {effective_fps:.1f}")
                        break
                else:
                    frames_with_object = 0
                    print(f"Looking for objects... | FPS: {effective_fps:.1f}", end='\r')
            
            picam2.stop()
            
            if object_detected:
                return filename
            else:
                return None
                
        except Exception as e:
            print(f"❌ Picamera2 error: {e}")
            print("💡 Trying fallback to OpenCV VideoCapture...")
    
    # Fallback to OpenCV VideoCapture
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Could not open camera")
        print("💡 Tip: Make sure a camera is connected")
        return None
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print("📹 Starting live video capture (OpenCV fallback)...")
    
    object_detected = False
    frames_with_object = 0
    required_frames = 2
    frame_skip = 5  # Process every 5th frame for better FPS
    frame_count = 0
    fps_deque = deque(maxlen=30)
    fps_start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Error: Could not read frame from camera")
            break
        
        frame_count += 1
        
        # Skip frames - only process every Nth frame
        if frame_count % frame_skip != 0:
            # Still update FPS counter (use camera FPS, not processing FPS)
            fps_end_time = time.time()
            fps = 1.0 / (fps_end_time - fps_start_time) if fps_start_time else 0
            fps_deque.append(fps)
            fps_start_time = fps_end_time
            avg_fps = sum(fps_deque) / len(fps_deque) if fps_deque else 0
            # Show camera FPS for skipped frames
            print(f"Looking for objects... | Camera FPS: {avg_fps:.1f}", end='\r')
            continue
        
        # Run YOLO detection (optimized - smaller image size)
        results = yolo_model(frame, conf=0.25, verbose=False, imgsz=320, half=False)
        
        # Check for target objects
        detected_objects = []
        if results[0].boxes is not None:
            for box in results[0].boxes:
                class_id = int(box.cls[0])
                class_name = yolo_model.names[class_id]
                confidence = float(box.conf[0])
                
                if class_name in TARGET_OBJECTS and confidence > 0.25:
                    detected_objects.append((class_name, confidence, box.xyxy[0].tolist()))
        
        # Calculate FPS (only count processed frames)
        fps_end_time = time.time()
        processing_time = fps_end_time - fps_start_time
        fps = 1.0 / processing_time if processing_time > 0 else 0
        fps_deque.append(fps)
        fps_start_time = fps_end_time
        avg_fps = sum(fps_deque) / len(fps_deque) if fps_deque else 0
        # Adjust effective FPS based on frame skipping
        effective_fps = avg_fps / frame_skip
        
        # Check if target objects detected
        if len(detected_objects) > 0:
            frames_with_object += 1
            obj_names = [obj[0] for obj in detected_objects]
            unique_objs = list(set(obj_names))
            print(f"🔍 Detected: {', '.join(unique_objs)} ({frames_with_object}/{required_frames} frames) | FPS: {effective_fps:.1f}", end='\r')
            
            if frames_with_object >= required_frames and not object_detected:
                object_detected = True
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"capture_objects_{timestamp}.jpg"
                
                # Draw annotations on frame
                annotated_frame = results[0].plot()
                
                # Add FPS to frame
                cv2.putText(annotated_frame, f"FPS: {effective_fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Save original and annotated versions
                cv2.imwrite(filename, frame)
                annotated_filename = f"capture_objects_{timestamp}_annotated.jpg"
                cv2.imwrite(annotated_filename, annotated_frame)
                
                print(f"\n✅ Objects detected! Photo saved to {filename}")
                print(f"✅ Annotated version saved to {annotated_filename}")
                print(f"📊 Detected objects: {', '.join(unique_objs)}")
                print(f"⚡ Average FPS: {effective_fps:.1f}")
                break
        else:
            frames_with_object = 0
            print(f"Looking for objects... | FPS: {effective_fps:.1f}", end='\r')
    
    # Cleanup
    cap.release()
    
    if object_detected:
        return filename
    else:
        return None

if __name__ == "__main__":
    result = detect_objects_capture()
    if result:
        print(f"\n✅ Program completed successfully!")
        print(f"📸 Captured image: {result}")
    else:
        print(f"\n⚠️ Program ended without capturing a photo")
