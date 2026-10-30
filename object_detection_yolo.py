#!/usr/bin/env python3
"""
Basic Object Detection using YOLO on Raspberry Pi
Detects objects in real-time from camera feed
"""

import cv2
import time
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
    print("⚠️  This script requires YOLOv8 from Ultralytics")

def load_yolo_model(model_size='nano'):
    """
    Load YOLO model. For Raspberry Pi, use 'nano' or 'small' models.
    
    Args:
        model_size: 'nano', 'small', 'medium', 'large', 'xlarge'
    Returns:
        YOLO model object
    """
    if not YOLO_AVAILABLE:
        return None
    
    # Model size mapping: nano -> n, small -> s, medium -> m, large -> l, xlarge -> x
    model_size_map = {
        'nano': 'n',
        'small': 's',
        'medium': 'm',
        'large': 'l',
        'xlarge': 'x'
    }
    
    if model_size not in model_size_map:
        print(f"⚠️  Invalid model size: {model_size}. Using 'nano' instead.")
        model_size = 'nano'
    
    # YOLO model name format: yolov8n, yolov8s, etc. (will auto-download if not found)
    model_name = f'yolov8{model_size_map[model_size]}'
    print(f"📦 Loading YOLO model: {model_name}")
    print("💡 First run will download the model automatically (~6MB for nano)")
    
    try:
        model = YOLO(model_name)
        print(f"✅ Model loaded successfully")
        return model
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print("💡 Tip: Make sure you have internet connection for first-time download")
        return None

def detect_objects(model, frame, conf_threshold=0.25):
    """
    Detect objects in a frame using YOLO
    
    Args:
        model: YOLO model
        frame: Input frame (BGR format)
        conf_threshold: Confidence threshold (0.0-1.0)
    
    Returns:
        Annotated frame with bounding boxes and labels
    """
    if model is None:
        return frame
    
    # Run inference
    results = model(frame, conf=conf_threshold, verbose=False)
    
    # Draw results on frame
    annotated_frame = results[0].plot()
    
    return annotated_frame

def _summarize_results(model, results):
    """
    Get detection information (counts, labels) without drawing
    
    Args:
        model: YOLO model
        frame: Input frame
        conf_threshold: Confidence threshold
    
    Returns:
        Dictionary with detection info
    """
    if model is None:
        return {"count": 0, "objects": []}
    
    detections = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = model.names[class_id]
            detections.append({
                "class": class_name,
                "confidence": confidence,
                "bbox": box.xyxy[0].tolist()
            })
    
    # Count objects by class
    object_counts = {}
    for det in detections:
        class_name = det["class"]
        object_counts[class_name] = object_counts.get(class_name, 0) + 1
    
    return {
        "count": len(detections),
        "objects": detections,
        "counts": object_counts
    }

def get_detection_info(model, frame, conf_threshold=0.25):
    """Run inference once and return structured detections."""
    if model is None:
        return {"count": 0, "objects": [], "counts": {}}
    results = model(frame, conf=conf_threshold, verbose=False)
    return _summarize_results(model, results)


def main():
    """Main function for object detection"""
    
    # Check if YOLO is available
    if not YOLO_AVAILABLE:
        print("❌ YOLO not available. Please install: pip install ultralytics")
        return
    
    # Load YOLO model (use 'nano' for Raspberry Pi - fastest)
    print("\n" + "="*50)
    print("🔍 YOLO Object Detection on Raspberry Pi")
    print("="*50)
    print("💡 Using YOLOv8nano model for best performance on Pi")
    print("💡 Press 'q' to quit")
    print("="*50 + "\n")
    
    model = load_yolo_model('nano')
    if model is None:
        print("❌ Failed to load YOLO model")
        return
    
    # Initialize camera
    camera = None
    if PICAMERA2_AVAILABLE:
        try:
            camera = Picamera2()
            preview_config = camera.create_preview_configuration(
                main={"size": (640, 480)}  # Lower resolution for better performance
            )
            camera.configure(preview_config)
            camera.start()
            print("✅ Camera initialized (Picamera2)")
        except Exception as e:
            print(f"⚠️  Picamera2 error: {e}")
            print("💡 Falling back to OpenCV VideoCapture...")
            camera = None
    
    if camera is None:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("❌ Error: Could not open camera")
            return
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("✅ Camera initialized (OpenCV VideoCapture)")
    
    # FPS calculation
    fps_deque = deque(maxlen=30)
    fps_start_time = time.time()
    
    print("\n🎥 Starting object detection...")
    print("📊 Detected objects will be shown with bounding boxes\n")
    
    try:
        frame_count = 0
        while True:
            # Get frame
            if PICAMERA2_AVAILABLE and isinstance(camera, Picamera2):
                frame = camera.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                ret, frame = camera.read()
                if not ret:
                    print("❌ Could not read frame")
                    break
            
            # Run one inference pass; reuse it for annotations and console statistics.
            results = model(frame, conf=0.25, verbose=False)
            annotated_frame = results[0].plot()
            
            if frame_count % 10 == 0:  # Print every 10 frames to avoid spam
                info = _summarize_results(model, results)
                if info["count"] > 0:
                    print(f"🔍 Frame {frame_count}: Detected {info['count']} object(s)")
                    for obj_class, count in info["counts"].items():
                        print(f"   - {obj_class}: {count}")
            
            # Calculate FPS
            fps_end_time = time.time()
            fps = 1.0 / (fps_end_time - fps_start_time) if fps_start_time else 0
            fps_deque.append(fps)
            fps_start_time = fps_end_time
            avg_fps = sum(fps_deque) / len(fps_deque) if fps_deque else 0
            
            # Display FPS on frame
            cv2.putText(annotated_frame, f"FPS: {avg_fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Display frame (if display available)
            try:
                cv2.imshow('YOLO Object Detection - Press Q to quit', annotated_frame)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n👋 Quitting...")
                    break
            except (cv2.error, AttributeError):
                # No display available (headless mode)
                # Just continue processing
                # In headless mode, run for a limited time or until interrupted
                pass
            
            frame_count += 1
            
            # Small delay to prevent 100% CPU usage
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        if camera:
            if PICAMERA2_AVAILABLE and isinstance(camera, Picamera2):
                camera.stop()
            else:
                camera.release()
        try:
            cv2.destroyAllWindows()
        except:
            pass
        print("✅ Done")

if __name__ == "__main__":
    main()
