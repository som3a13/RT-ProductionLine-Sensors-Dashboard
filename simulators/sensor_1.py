"""
Sensor 1 Simulator - Temperature Sensor
Uses PTY (pseudo-terminal) to create a fake serial port
Configurable baudrate and serial parameters (8N1)
"""
import pty
import os
import time
import json
import random
import sys
import termios
import struct
from datetime import datetime


class TrendBasedGenerator:
    """Trend-based sensor value generator for realistic gradual changes"""
    
    def __init__(self, low_limit: float, high_limit: float, base_value: float = None):
        self.low_limit = low_limit
        self.high_limit = high_limit
        self.base_value = base_value if base_value is not None else (low_limit + high_limit) / 2
        self.current_value = self.base_value
        self.trend_direction = random.choice([-1, 1])
        self.trend_rate = random.uniform(0.01, 0.05)
        self.trend_change_probability = 0.02
        self.range = high_limit - low_limit
        self.step_size = self.range * self.trend_rate
        self.noise_level = self.range * 0.01
        self.faulty = False
        self.alarm_cooldown = 0
    
    def generate_value(self) -> float:
        """Generate next trend-based sensor value"""
        if self.faulty:
            if random.random() < 0.1:
                self.faulty = False
                self.current_value = self.base_value
            else:
                return -999.0
        
        if random.random() < 0.01:
            self.faulty = True
            return -999.0
        
        if self.alarm_cooldown > 0:
            self.alarm_cooldown -= 1
        
        if self.alarm_cooldown == 0 and random.random() < 0.05:
            self.alarm_cooldown = 20
            if random.random() < 0.5:
                self.current_value = self.low_limit - random.uniform(1, min(10, self.range * 0.1))
                return round(self.current_value, 2)
            else:
                self.current_value = self.high_limit + random.uniform(1, min(10, self.range * 0.1))
                return round(self.current_value, 2)
        
        if random.random() < self.trend_change_probability:
            self.trend_direction *= -1
            self.trend_rate = random.uniform(0.01, 0.05)
            self.step_size = self.range * self.trend_rate
        
        self.current_value += self.trend_direction * self.step_size
        noise = random.uniform(-self.noise_level, self.noise_level)
        self.current_value += noise
        
        if self.current_value < self.low_limit - self.range * 0.2:
            self.current_value = self.low_limit - self.range * 0.1
            self.trend_direction = 1
        elif self.current_value > self.high_limit + self.range * 0.2:
            self.current_value = self.high_limit + self.range * 0.1
            self.trend_direction = -1
        
        return round(self.current_value, 2)


class Sensor1Simulator:
    """PTY-based simulator for Sensor 1 (Temperature Sensor)"""
    
    def __init__(self, baudrate=115200, bytesize=8, parity='N', stopbits=1):
        """
        Initialize sensor simulator
        
        Args:
            baudrate: Serial baudrate (default: 115200)
            bytesize: Data bits (default: 8)
            parity: Parity ('N' for None, 'E' for Even, 'O' for Odd)
            stopbits: Stop bits (1 or 2)
        """
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.running = False
        self.master_fd = None
        self.slave_name = None
        
        # Sensor configuration
        self.sensor_id = 1
        self.sensor_name = "Temperature Sensor 1"
        self.low_limit = 20.0
        self.high_limit = 80.0
        self.unit = "°C"
        self.base_value = (self.low_limit + self.high_limit) / 2
        self.faulty = False
        
        # Trend-based value generator
        self.value_generator = TrendBasedGenerator(
            low_limit=self.low_limit,
            high_limit=self.high_limit,
            base_value=self.base_value
        )
        
        # Working frame configuration for this sensor
        self.frame_format = "JSON"  # This sensor uses JSON frame format
        
    def create_pty(self):
        """Create PTY pair and configure serial parameters"""
        try:
            # Create PTY pair
            master_fd, slave_fd = pty.openpty()
            self.slave_name = os.ttyname(slave_fd)
            
            # Configure PTY with serial parameters
            # Set baudrate and other serial parameters on the master side
            try:
                # Get current terminal attributes
                attrs = termios.tcgetattr(master_fd)
                
                # Set baudrate
                if self.baudrate == 115200:
                    attrs[4] = termios.B115200  # Input speed
                    attrs[5] = termios.B115200  # Output speed
                elif self.baudrate == 9600:
                    attrs[4] = termios.B9600
                    attrs[5] = termios.B9600
                elif self.baudrate == 19200:
                    attrs[4] = termios.B19200
                    attrs[5] = termios.B19200
                elif self.baudrate == 38400:
                    attrs[4] = termios.B38400
                    attrs[5] = termios.B38400
                elif self.baudrate == 57600:
                    attrs[4] = termios.B57600
                    attrs[5] = termios.B57600
                else:
                    # Default to 115200 if not supported
                    attrs[4] = termios.B115200
                    attrs[5] = termios.B115200
                
                # Set data bits, parity, stop bits
                attrs[2] &= ~termios.CSIZE  # Clear current size
                if self.bytesize == 8:
                    attrs[2] |= termios.CS8
                elif self.bytesize == 7:
                    attrs[2] |= termios.CS7
                elif self.bytesize == 6:
                    attrs[2] |= termios.CS6
                elif self.bytesize == 5:
                    attrs[2] |= termios.CS5
                
                # Set parity
                attrs[2] &= ~(termios.PARENB | termios.PARODD)  # Clear parity
                if self.parity == 'E':
                    attrs[2] |= termios.PARENB  # Enable parity
                elif self.parity == 'O':
                    attrs[2] |= termios.PARENB | termios.PARODD  # Odd parity
                
                # Set stop bits
                if self.stopbits == 2:
                    attrs[2] |= termios.CSTOPB
                else:
                    attrs[2] &= ~termios.CSTOPB
                
                # Apply attributes
                termios.tcsetattr(master_fd, termios.TCSANOW, attrs)
            except Exception as e:
                print(f"Warning: Could not set serial parameters: {e}")
                print("PTY will use default parameters")
            
            self.master_fd = master_fd
            os.close(slave_fd)  # Close slave FD, we only need master for writing
            
            print(f"✓ Created PTY for {self.sensor_name}")
            print(f"  Device: {self.slave_name}")
            print(f"  Baudrate: {self.baudrate}")
            print(f"  Serial Parameters: {self.bytesize}{self.parity}{self.stopbits} (8N1)")
            print(f"  Frame Format: {self.frame_format}")
            
            return self.slave_name
        except Exception as e:
            print(f"Failed to create PTY: {e}")
            return None
    
    def generate_sensor_value(self) -> float:
        """Generate a realistic trend-based sensor value"""
        value = self.value_generator.generate_value()
        self.faulty = self.value_generator.faulty
        return value
    
    def create_working_frame(self, value: float) -> bytes:
        """
        Create working frame for Sensor 1
        This sensor uses JSON frame format
        """
        is_faulty = self.faulty or value == -999.0
        
        frame_data = {
            "sensor_id": self.sensor_id,
            "sensor_name": self.sensor_name,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "status": "FAULTY" if is_faulty else "OK",
            "unit": self.unit
        }
        
        # JSON frame format: JSON message + newline
        frame = json.dumps(frame_data) + "\n"
        return frame.encode('utf-8')
    
    def run(self):
        """Main loop - sends sensor data"""
        if not self.master_fd:
            print("Error: PTY not created. Call create_pty() first.")
            return
        
        self.running = True
        print(f"\n{self.sensor_name} simulator running...")
        print("Press Ctrl+C to stop.\n")
        
        try:
            while self.running:
                value = self.generate_sensor_value()
                frame = self.create_working_frame(value)
                
                # Write frame to PTY master side
                os.write(self.master_fd, frame)
                
                time.sleep(0.5)  # Update every 0.5 seconds
        except KeyboardInterrupt:
            print("\n\nStopping simulator...")
            self.stop()
        except Exception as e:
            print(f"Error: {e}")
            self.stop()
    
    def stop(self):
        """Stop the simulator"""
        self.running = False
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except:
                pass
        print(f"{self.sensor_name} simulator stopped.")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sensor 1 (Temperature) PTY Simulator')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baudrate (default: 115200)')
    parser.add_argument('--bytesize', type=int, default=8, choices=[5, 6, 7, 8], help='Data bits (default: 8)')
    parser.add_argument('--parity', type=str, default='N', choices=['N', 'E', 'O'], help='Parity (default: N)')
    parser.add_argument('--stopbits', type=int, default=1, choices=[1, 2], help='Stop bits (default: 1)')
    
    args = parser.parse_args()
    
    simulator = Sensor1Simulator(
        baudrate=args.baudrate,
        bytesize=args.bytesize,
        parity=args.parity,
        stopbits=args.stopbits
    )
    
    slave_name = simulator.create_pty()
    if slave_name:
        print(f"\nWorker thread should connect to: {slave_name}")
        print(f"Serial parameters: {args.bytesize}{args.parity}{args.stopbits} @ {args.baudrate} baud\n")
        simulator.run()
    else:
        print("Failed to create PTY")
        sys.exit(1)


if __name__ == "__main__":
    main()

