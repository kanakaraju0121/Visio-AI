#!/usr/bin/env python3
"""
L298N Dual Motor Driver Control for Raspberry Pi
Controls 2 DC motors using L298N driver module
"""

import RPi.GPIO as GPIO
import time

class L298N_MotorDriver:
    def __init__(self, ena_pin, in1_pin, in2_pin, enb_pin, in3_pin, in4_pin):
        """
        Initialize L298N Motor Driver
        
        Args:
            ena_pin: Enable pin for Motor 1 (PWM)
            in1_pin: Input 1 for Motor 1
            in2_pin: Input 2 for Motor 1
            enb_pin: Enable pin for Motor 2 (PWM)
            in3_pin: Input 1 for Motor 2
            in4_pin: Input 2 for Motor 2
        """
        # Motor 1 pins
        self.ENA = ena_pin
        self.IN1 = in1_pin
        self.IN2 = in2_pin
        
        # Motor 2 pins
        self.ENB = enb_pin
        self.IN3 = in3_pin
        self.IN4 = in4_pin
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup Motor 1 pins
        GPIO.setup(self.ENA, GPIO.OUT)
        GPIO.setup(self.IN1, GPIO.OUT)
        GPIO.setup(self.IN2, GPIO.OUT)
        
        # Setup Motor 2 pins
        GPIO.setup(self.ENB, GPIO.OUT)
        GPIO.setup(self.IN3, GPIO.OUT)
        GPIO.setup(self.IN4, GPIO.OUT)
        
        # Setup PWM for speed control
        self.pwm_motor1 = GPIO.PWM(self.ENA, 1000)  # 1000 Hz frequency
        self.pwm_motor2 = GPIO.PWM(self.ENB, 1000)
        
        # Start PWM with 0 duty cycle (stopped)
        self.pwm_motor1.start(0)
        self.pwm_motor2.start(0)
        
        print("L298N Motor Driver initialized")
    
    @staticmethod
    def _validate_speed(speed):
        if not isinstance(speed, (int, float)) or not 0 <= speed <= 100:
            raise ValueError("Motor speed must be between 0 and 100 percent")

    def motor1_forward(self, speed=50):
        """Move Motor 1 forward."""
        self._validate_speed(speed)
        GPIO.output(self.IN1, GPIO.HIGH)
        GPIO.output(self.IN2, GPIO.LOW)
        self.pwm_motor1.ChangeDutyCycle(speed)
        print(f"Motor 1: Forward at {speed}% speed")
    
    def motor1_backward(self, speed=50):
        """Move Motor 1 backward."""
        self._validate_speed(speed)
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.HIGH)
        self.pwm_motor1.ChangeDutyCycle(speed)
        print(f"Motor 1: Backward at {speed}% speed")
    
    def motor1_stop(self):
        """Stop Motor 1"""
        GPIO.output(self.IN1, GPIO.LOW)
        GPIO.output(self.IN2, GPIO.LOW)
        self.pwm_motor1.ChangeDutyCycle(0)
        print("Motor 1: Stopped")
    
    def motor2_forward(self, speed=50):
        """Move Motor 2 forward."""
        self._validate_speed(speed)
        GPIO.output(self.IN3, GPIO.HIGH)
        GPIO.output(self.IN4, GPIO.LOW)
        self.pwm_motor2.ChangeDutyCycle(speed)
        print(f"Motor 2: Forward at {speed}% speed")
    
    def motor2_backward(self, speed=50):
        """Move Motor 2 backward."""
        self._validate_speed(speed)
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.HIGH)
        self.pwm_motor2.ChangeDutyCycle(speed)
        print(f"Motor 2: Backward at {speed}% speed")
    
    def motor2_stop(self):
        """Stop Motor 2"""
        GPIO.output(self.IN3, GPIO.LOW)
        GPIO.output(self.IN4, GPIO.LOW)
        self.pwm_motor2.ChangeDutyCycle(0)
        print("Motor 2: Stopped")
    
    def both_forward(self, speed=50):
        """Move both motors forward."""
        self._validate_speed(speed)
        self.motor1_forward(speed)
        self.motor2_forward(speed)
    
    def both_backward(self, speed=50):
        """Move both motors backward."""
        self._validate_speed(speed)
        self.motor1_backward(speed)
        self.motor2_backward(speed)
    
    def both_stop(self):
        """Stop both motors"""
        self.motor1_stop()
        self.motor2_stop()
    
    def cleanup(self):
        """Clean up GPIO resources"""
        self.both_stop()
        self.pwm_motor1.stop()
        self.pwm_motor2.stop()
        GPIO.cleanup()
        print("GPIO cleaned up")


def main():
    # Define GPIO pins (BCM numbering)
    # Motor 1: ENA=18, IN1=23, IN2=24
    # Motor 2: ENB=12, IN3=25, IN4=8
    motor_driver = L298N_MotorDriver(
        ena_pin=18,  # Motor 1 PWM
        in1_pin=23,  # Motor 1 Input 1
        in2_pin=24,  # Motor 1 Input 2
        enb_pin=12,  # Motor 2 PWM
        in3_pin=25,  # Motor 2 Input 1
        in4_pin=8    # Motor 2 Input 2
    )
    
    try:
        print("\n=== Motor Control Test ===")
        
        # Test Motor 1
        print("\n1. Testing Motor 1 Forward...")
        motor_driver.motor1_forward(50)
        time.sleep(2)
        motor_driver.motor1_stop()
        time.sleep(1)
        
        print("\n2. Testing Motor 1 Backward...")
        motor_driver.motor1_backward(50)
        time.sleep(2)
        motor_driver.motor1_stop()
        time.sleep(1)
        
        # Test Motor 2
        print("\n3. Testing Motor 2 Forward...")
        motor_driver.motor2_forward(50)
        time.sleep(2)
        motor_driver.motor2_stop()
        time.sleep(1)
        
        print("\n4. Testing Motor 2 Backward...")
        motor_driver.motor2_backward(50)
        time.sleep(2)
        motor_driver.motor2_stop()
        time.sleep(1)
        
        # Test Both Motors
        print("\n5. Testing Both Motors Forward...")
        motor_driver.both_forward(50)
        time.sleep(2)
        motor_driver.both_stop()
        time.sleep(1)
        
        print("\n6. Testing Both Motors Backward...")
        motor_driver.both_backward(50)
        time.sleep(2)
        motor_driver.both_stop()
        
        print("\n=== Test Complete ===")
        
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        motor_driver.cleanup()


if __name__ == "__main__":
    main()

