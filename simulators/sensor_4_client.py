"""
Sensor 4 Client - Vibration Sensor (TCP Client)
Connects to TCP server as a client and sends sensor data
"""
import socket
import threading
import time
import json
import random
import sys
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
                self.current_value = self.low_limit - random.uniform(0.1, min(1.0, self.range * 0.1))
                return round(self.current_value, 2)
            else:
                self.current_value = self.high_limit + random.uniform(0.1, min(1.0, self.range * 0.1))
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


class Sensor4Client:
    """TCP client for Sensor 4 (Vibration Sensor)"""
    
    def __init__(self, server_host="localhost", server_port=5000):
        """
        Initialize Sensor 4 TCP client
        
        Args:
            server_host: TCP server host (default: localhost)
            server_port: TCP server port (default: 5000)
        """
        self.server_host = server_host
        self.server_port = server_port
        self.running = False
        self.socket = None
        self.reconnect_thread = None
        
        # Sensor configuration
        self.sensor_id = 4
        self.sensor_name = "Vibration Sensor 1"
        self.low_limit = 0.0
        self.high_limit = 5.0
        self.unit = "mm/s"
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
    
    def generate_sensor_value(self) -> float:
        """Generate a realistic trend-based sensor value"""
        value = self.value_generator.generate_value()
        self.faulty = self.value_generator.faulty
        return value
    
    def create_working_frame(self, value: float) -> bytes:
        """
        Create working frame for Sensor 4
        This sensor uses JSON frame format over TCP
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
    
    def connect_to_server(self) -> bool:
        """Connect to TCP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.server_host, self.server_port))
            print(f"✓ {self.sensor_name} connected to server {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"✗ {self.sensor_name} connection error: {e}")
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False
    
    def send_data_loop(self):
        """Main loop to send sensor data to server"""
        while self.running:
            try:
                if not self.socket:
                    # Try to reconnect
                    if not self.connect_to_server():
                        time.sleep(2)  # Wait before retry
                        continue
                
                value = self.generate_sensor_value()
                frame = self.create_working_frame(value)
                
                try:
                    self.socket.send(frame)
                except Exception as e:
                    print(f"Error sending data: {e}")
                    # Connection lost, close socket
                    if self.socket:
                        try:
                            self.socket.close()
                        except:
                            pass
                        self.socket = None
                    continue
                
                time.sleep(0.5)  # Update every 0.5 seconds
                
            except Exception as e:
                if self.running:
                    print(f"Error in send loop: {e}")
                break
    
    def start(self):
        """Start sensor client"""
        self.running = True
        
        print("=" * 60)
        print(f"Starting {self.sensor_name} (TCP Client)")
        print("=" * 60)
        print(f"  Server: {self.server_host}:{self.server_port}")
        print(f"  Frame Format: {self.frame_format}")
        print(f"  Sensor ID: {self.sensor_id}")
        print(f"  Unit: {self.unit}")
        print(f"\nConnecting to server...")
        print("Press Ctrl+C to stop.\n")
        print("=" * 60)
        
        # Connect to server
        if not self.connect_to_server():
            print(f"Failed to connect to server. Make sure TCP server is running on {self.server_host}:{self.server_port}")
            print("Start the server with: python3 simulators/tcp_sensor_server.py")
            sys.exit(1)
        
        # Start sending data
        try:
            self.send_data_loop()
        except KeyboardInterrupt:
            print("\n\nStopping sensor client...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the sensor client"""
        self.running = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        print(f"{self.sensor_name} client stopped.")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sensor 4 (Vibration) TCP Client')
    parser.add_argument('--server-host', type=str, default='localhost', help='TCP server host (default: localhost)')
    parser.add_argument('--server-port', type=int, default=5000, help='TCP server port (default: 5000)')
    
    args = parser.parse_args()
    
    client = Sensor4Client(server_host=args.server_host, server_port=args.server_port)
    
    try:
        client.start()
    except KeyboardInterrupt:
        print("\n\nStopping client...")
        client.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()

