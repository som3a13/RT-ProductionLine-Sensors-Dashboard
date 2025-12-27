"""
TCP Sensor Server - Modular TCP server that accepts sensor connections
Sensors connect to this server as clients and send their data
"""
import socket
import threading
import sys
from datetime import datetime


class TCPSensorServer:
    """Modular TCP server that accepts connections from sensor clients"""
    
    def __init__(self, host="localhost", port=5000):
        """
        Initialize TCP sensor server
        
        Args:
            host: TCP server host (default: localhost)
            port: TCP server port (default: 5000)
        """
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.client_connections = []
        self.lock = threading.Lock()
        self.connected_sensors = {}  # Track connected sensors by address
    
    def handle_client(self, client_socket, address):
        """Handle client connection - receives data from sensors and forwards to monitoring clients"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Client connected: {address}")
        
        try:
            buffer = ""
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    buffer += data.decode('utf-8', errors='ignore')
                    
                    # Process complete lines (JSON frames)
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            # Add newline back for proper frame format (main app expects it)
                            frame_data = line + '\n'
                            # Forward this data to all other connected clients (monitoring clients)
                            # This allows the main app to receive data from sensor clients
                            self._broadcast_to_monitoring_clients(frame_data.encode('utf-8'), client_socket)
                            
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Error receiving data from {address}: {e}")
                    break
                    
        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
            with self.lock:
                if client_socket in self.client_connections:
                    self.client_connections.remove(client_socket)
                if address in self.connected_sensors:
                    del self.connected_sensors[address]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Client disconnected: {address}")
    
    def _broadcast_to_monitoring_clients(self, data: bytes, sender_socket):
        """Broadcast data to all monitoring clients (excluding the sender)"""
        disconnected = []
        with self.lock:
            clients_to_notify = [c for c in self.client_connections if c != sender_socket]
        
        if not clients_to_notify:
            return  # No monitoring clients connected yet
        
        for client in clients_to_notify:
            try:
                client.send(data)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.append(client)
        
        # Remove disconnected clients
        if disconnected:
            with self.lock:
                for client in disconnected:
                    if client in self.client_connections:
                        self.client_connections.remove(client)
    
    def start(self):
        """Start TCP server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)  # Allow up to 10 concurrent connections
            self.running = True
            
            print("=" * 60)
            print("✓ TCP Sensor Server started")
            print("=" * 60)
            print(f"  Host: {self.host}")
            print(f"  Port: {self.port}")
            print(f"  Status: Listening for sensor connections...")
            print(f"\nSensors should connect to: {self.host}:{self.port}")
            print("Press Ctrl+C to stop.\n")
            print("=" * 60)
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_socket.settimeout(5.0)  # Set timeout for recv
                    
                    with self.lock:
                        self.client_connections.append(client_socket)
                        self.connected_sensors[address] = datetime.now()
                    
                    # Start thread for each client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                except OSError:
                    # Socket closed
                    break
        except Exception as e:
            print(f"Failed to start TCP server: {e}")
            sys.exit(1)
    
    def stop(self):
        """Stop the server"""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        with self.lock:
            for conn in self.client_connections:
                try:
                    conn.close()
                except:
                    pass
            self.client_connections.clear()
            self.connected_sensors.clear()
        
        print("\nTCP Sensor Server stopped.")


def main():
    """Main function"""
    import argparse
    import threading
    import signal
    
    parser = argparse.ArgumentParser(
        description='TCP Sensor Server - Accepts sensor client connections',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run server on default port 5000
  python3 simulators/tcp_sensor_server.py
  
  # Run server on port 5001
  python3 simulators/tcp_sensor_server.py --port 5001
  
  # Run server on different host
  python3 simulators/tcp_sensor_server.py --host 0.0.0.0 --port 5000
  
  # Run multiple servers on different ports
  python3 simulators/tcp_sensor_server.py --ports 5000 5001
  
  # Run multiple servers with same host
  python3 simulators/tcp_sensor_server.py --host localhost --ports 5000 5001 5002
        """
    )
    parser.add_argument('--host', type=str, default='localhost',
                       help='TCP server host (default: localhost)')
    parser.add_argument('--port', type=int, default=None,
                       help='TCP server port (default: 5000, ignored if --ports is used)')
    parser.add_argument('--ports', type=int, nargs='+', default=None,
                       help='Multiple TCP server ports (e.g., --ports 5000 5001)')
    
    args = parser.parse_args()
    
    # Determine which ports to use
    if args.ports:
        ports = args.ports
    elif args.port:
        ports = [args.port]
    else:
        ports = [5000]  # Default
    
    # If only one port, run normally
    if len(ports) == 1:
        server = TCPSensorServer(host=args.host, port=ports[0])
        try:
            server.start()
        except KeyboardInterrupt:
            print("\n\nStopping server...")
            server.stop()
            sys.exit(0)
    else:
        # Run multiple servers in separate threads
        servers = []
        threads = []
        
        print("=" * 70)
        print("Starting Multiple TCP Sensor Servers")
        print("=" * 70)
        print(f"Host: {args.host}")
        print(f"Ports: {', '.join(map(str, ports))}")
        print("=" * 70)
        print()
        
        def signal_handler(sig, frame):
            """Handle Ctrl+C gracefully"""
            print("\n\nStopping all servers...")
            for server in servers:
                server.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start each server in a separate thread
        for port in ports:
            server = TCPSensorServer(host=args.host, port=port)
            servers.append(server)
            thread = threading.Thread(
                target=server.start,
                daemon=False,
                name=f"TCP-Server-{port}"
            )
            thread.start()
            threads.append(thread)
            import time
            time.sleep(0.3)  # Small delay between starts
        
        print("\nAll servers started. Press Ctrl+C to stop all servers.\n")
        
        # Wait for all threads
        try:
            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            signal_handler(None, None)


if __name__ == "__main__":
    main()
