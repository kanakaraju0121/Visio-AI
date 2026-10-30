#!/usr/bin/env python3
"""
Text-to-Speech on Raspberry Pi
"""
import subprocess
import sys

def speak(text, voice='en-us', rate=110, pitch=50, gender='female'):
    """
    Speak text using TTS via espeak (more reliable than pyttsx3 on Raspberry Pi)
    
    Args:
        text: Text to speak
        voice: Voice to use (e.g., 'en-us', 'en-gb', 'en', 'en-uk-rp')
        rate: Speech rate in words per minute (lower = slower)
        pitch: Pitch adjustment (0-99, default 50). Higher = more feminine (70-85), Lower = more masculine (30-40)
        gender: 'male', 'female', or 'auto' (default: auto uses pitch parameter)
    """
    # Adjust pitch based on gender preference
    if gender == 'female':
        pitch = 75  # Higher pitch for female voice
    elif gender == 'male':
        pitch = 40  # Lower pitch for male voice
    # else use the provided pitch value
    
    try:
        # Use espeak directly - more reliable than pyttsx3
        # -v for voice, -s for speed, -a for amplitude (volume, max 200), -p for pitch (0-99)
        subprocess.run(['espeak', '-v', voice, '-s', str(rate), '-a', '200', '-p', str(pitch), text], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Could not use espeak: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: espeak not found. Please install it with: sudo apt-get install espeak")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Text-to-Speech on Raspberry Pi')
    parser.add_argument('text', nargs='?', default='Hello from Raspberry Pi', 
                       help='Text to speak')
    parser.add_argument('-v', '--voice', default='en-us',
                       choices=['en', 'en-us', 'en-gb', 'en-uk-rp', 'en-sc', 
                               'en-uk-north', 'en-uk-wmids', 'en-wi'],
                       help='Voice to use (default: en-us)')
    parser.add_argument('-r', '--rate', type=int, default=110,
                       help='Speech rate in words per minute (default: 110, lower = slower)')
    parser.add_argument('-p', '--pitch', type=int, default=50,
                       help='Pitch adjustment 0-99 (default: 50, higher = more feminine, 70-85 for female voice)')
    parser.add_argument('-g', '--gender', default='female',
                       choices=['auto', 'female', 'male'],
                       help='Gender of voice: female (higher pitch), male (lower pitch), or auto (use pitch parameter). Default: female')
    
    args = parser.parse_args()
    speak(args.text, voice=args.voice, rate=args.rate, pitch=args.pitch, gender=args.gender)

