#!/usr/bin/env python3
"""
Combined TCP Sensor System Launcher
Starts TCP servers and connects sensor clients in one command

Author: Mohammed Ismail AbdElmageid
"""
import sys
import argparse
import threading
import signal
import time
from pathlib import Path

# Add simulators directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tcp_sensor_server import TCPSensorServer
from run_tcp_sensor_clients import GenericTCPSensorClient, parse_sensor_spec, get_defaults_for_type


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Combined TCP Sensor System - Start servers and connect sensors',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server on port 5000 and connect one sensor
  python3 simulators/start_tcp_system.py \\
    --server-ports 5000 \\
    --sensor flow:3:localhost:5000
  
  # Start multiple servers and connect sensors
  python3 simulators/start_tcp_system.py \\
    --server-ports 5000 5001 \\
    --sensor flow:3:localhost:5000:10:100:L/min \\
    --sensor vibration:4:localhost:5000:0:5:mm/s \\
    --sensor flow:6:localhost:5001:10:100:L/min
  
  # Start server and connect multiple sensors to same server
  python3 simulators/start_tcp_system.py \\
    --server-ports 5000 \\
    --sensor flow:3:localhost:5000 \\
    --sensor vibration:4:localhost:5000
  
  # Start servers with custom host
  python3 simulators/start_tcp_system.py \\
    --server-host 0.0.0.0 \\
    --server-ports 5000 5001 \\
    --sensor flow:3:localhost:5000

Sensor Specification Format:
  TYPE:ID:HOST:PORT[:LOW:HIGH:UNIT]
  
  TYPE:    Sensor type (flow, vibration, temperature, pressure, voltage)
  ID:      Unique sensor ID (integer)
  HOST:    TCP server host
  PORT:    TCP server port
  LOW:     Lower alarm limit (optional, uses defaults if not specified)
  HIGH:    Upper alarm limit (optional, uses defaults if not specified)
  UNIT:    Unit of measurement (optional, uses defaults if not specified)
        """
    )
    
    parser.add_argument('--server-host', type=str, default='localhost',
                       help='TCP server host (default: localhost)')
    parser.add_argument('--server-ports', type=int, nargs='+', default=[5000],
                       help='TCP server ports to start (default: 5000)')
    parser.add_argument('--sensor', action='append', metavar='SPEC',
                       help='Sensor specification: TYPE:ID:HOST:PORT[:LOW:HIGH:UNIT]')
    parser.add_argument('--name-prefix', default='',
                       help='Prefix for sensor names (e.g., "Production Line 1 - ")')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay in seconds before starting sensors (default: 1.0)')
    
    args = parser.parse_args()
    
    servers = []
    sensors = []
    server_threads = []
    
    # Display configuration
    print("=" * 70)
    print("TCP Sensor System Launcher")
    print("=" * 70)
    print(f"Server Host: {args.server_host}")
    print(f"Server Ports: {', '.join(map(str, args.server_ports))}")
    if args.sensor:
        print(f"Number of Sensors: {len(args.sensor)}")
    print("=" * 70)
    print()
    
    # Start TCP servers
    print("Starting TCP servers...")
    for port in args.server_ports:
        server = TCPSensorServer(host=args.server_host, port=port)
        servers.append(server)
        
        def start_server(srv):
            try:
                srv.start()
            except Exception as e:
                print(f"Server error on port {srv.port}: {e}")
        
        thread = threading.Thread(
            target=start_server,
            args=(server,),
            daemon=False,
            name=f"TCP-Server-{port}"
        )
        thread.start()
        server_threads.append(thread)
        time.sleep(0.3)  # Small delay between server starts
    
    print(f"✓ {len(servers)} TCP server(s) starting...")
    print(f"  Waiting {args.delay} seconds for servers to initialize...\n")
    time.sleep(args.delay)
    
    # Parse and create sensors
    if args.sensor:
        print("Creating sensor clients...")
        for spec in args.sensor:
            try:
                sensor_config = parse_sensor_spec(spec)
                defaults = get_defaults_for_type(sensor_config['type'])
                
                # Use provided values or defaults
                low_limit = sensor_config['low_limit'] if sensor_config['low_limit'] is not None else defaults['low']
                high_limit = sensor_config['high_limit'] if sensor_config['high_limit'] is not None else defaults['high']
                unit = sensor_config['unit'] if sensor_config['unit'] else defaults['unit']
                sensor_name = f"{args.name_prefix}{defaults['name']} Sensor {sensor_config['id']}"
                
                client = GenericTCPSensorClient(
                    sensor_id=sensor_config['id'],
                    sensor_name=sensor_name,
                    sensor_type=sensor_config['type'],
                    low_limit=low_limit,
                    high_limit=high_limit,
                    unit=unit,
                    server_host=sensor_config['host'],
                    server_port=sensor_config['port']
                )
                sensors.append(client)
            except Exception as e:
                print(f"Error parsing sensor spec '{spec}': {e}")
        
        # Display sensor information
        if sensors:
            print("\nSensors:")
            for sensor in sensors:
                print(f"  - ID {sensor.sensor_id}: {sensor.sensor_name} ({sensor.sensor_type})")
                print(f"    Server: {sensor.server_host}:{sensor.server_port}")
                print(f"    Range: {sensor.low_limit} - {sensor.high_limit} {sensor.unit}")
            print()
        
        # Start all sensors
        print("Connecting sensors to servers...")
        started = []
        for sensor in sensors:
            if sensor.start():
                started.append(sensor)
                time.sleep(0.2)  # Small delay between sensor connections
            else:
                print(f"✗ Failed to start {sensor.sensor_name}")
        
        if started:
            print(f"✓ {len(started)} sensor(s) connected and running\n")
    
    print("=" * 70)
    print("System Status: RUNNING")
    print("=" * 70)
    print(f"  Servers: {len(servers)} running on ports {', '.join(map(str, args.server_ports))}")
    if sensors:
        print(f"  Sensors: {len([s for s in sensors if s.running])} connected")
    print("\nPress Ctrl+C to stop all servers and sensors.\n")
    print("=" * 70)
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\nStopping system...")
        
        # Stop all sensors
        for sensor in sensors:
            if sensor.running:
                sensor.stop()
        
        # Stop all servers
        for server in servers:
            server.stop()
        
        print("\nAll servers and sensors stopped.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
            
            # Check if servers are still running
            alive_servers = sum(1 for thread in server_threads if thread.is_alive())
            if alive_servers == 0:
                print("\nAll servers stopped. Exiting...")
                break
                
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()

