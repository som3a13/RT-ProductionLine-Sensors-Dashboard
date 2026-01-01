#!/usr/bin/env python3
"""
Script to read sensor data from PTY device
Connects to PTY device and displays incoming sensor readings
Supports simplified config string format

Author: Mohammed Ismail AbdElmageid
"""
import serial
import json
import sys
import argparse
from datetime import datetime


def parse_config_string(config_str: str):
    """
    Parse simplified configuration string format:
    port:baudrate:bytesizeparitystopbits
    
    Example: /dev/pts/5:115200:8N1
    """
    parts = config_str.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid config format. Expected: port:baudrate:bytesizeparitystopbits\n"
                        f"Got {len(parts)} parts, expected 3\n"
                        f"Example: /dev/pts/5:115200:8N1")
    
    port = parts[0].strip()
    baudrate = int(parts[1].strip()) if parts[1].strip() else 115200
    
    # Parse serial parameters: bytesizeparitystopbits (e.g., 8N1)
    serial_params = parts[2].strip()
    # Extract bytesize (first digit)
    bytesize = int(serial_params[0]) if len(serial_params) > 0 and serial_params[0].isdigit() else 8
    
    # Extract parity (second character: N, E, or O)
    parity = serial_params[1] if len(serial_params) > 1 and serial_params[1] in 'NEO' else 'N'
    
    # Extract stopbits (last digit)
    stopbits = int(serial_params[2]) if len(serial_params) > 2 and serial_params[2].isdigit() else 1
    
    return {
        'port': port,
        'baudrate': baudrate,
        'bytesize': bytesize,
        'parity': parity,
        'stopbits': stopbits
    }


def read_sensor_data(port, baudrate=115200, bytesize=8, parity='N', stopbits=1):
    """
    Read sensor data from PTY device
    
    Args:
        port: PTY device path (e.g., /dev/pts/5)
        baudrate: Serial baudrate (default: 115200)
        bytesize: Data bits (default: 8)
        parity: Parity (default: 'N')
        stopbits: Stop bits (default: 1)
    """
    try:
        # Open serial connection to PTY device
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=1.0
        )
        
        print("=" * 80)
        print("Serial Sensor Frame Reader")
        print("=" * 80)
        print(f"✓ Connected to {port}")
        print(f"  Baudrate: {baudrate}, Serial: {bytesize}{parity}{stopbits}")
        print(f"\nReading sensor frames... (Press Ctrl+C to stop)")
        print("Each frame will show:")
        print("  - Raw frame (hex, ASCII, string)")
        print("  - Parsed JSON data")
        print("  - Formatted sensor reading")
        print("=" * 80)
        print()
        
        buffer = ""
        
        while True:
            try:
                # Read available data
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    buffer += data.decode('utf-8', errors='ignore')
                    
                    # Process complete JSON messages (frames end with \n)
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            # Get the raw frame bytes (including newline)
                            raw_frame = (line + '\n').encode('utf-8')
                            
                            # Display raw frame information
                            print("=" * 80)
                            print("RAW FRAME:")
                            print(f"  Length: {len(raw_frame)} bytes")
                            print(f"  Hex:    {raw_frame.hex()}")
                            print(f"  ASCII:  {repr(raw_frame)}")
                            print(f"  String: {raw_frame.decode('utf-8', errors='replace').rstrip()}")
                            print("-" * 80)
                            
                            try:
                                # Parse JSON frame
                                frame = json.loads(line.strip())
                                
                                # Display parsed frame data
                                print("PARSED FRAME:")
                                sensor_id = frame.get("sensor_id", "?")
                                sensor_name = frame.get("sensor_name", "Unknown")
                                value = frame.get("value", 0)
                                timestamp = frame.get("timestamp", "")
                                status = frame.get("status", "OK")
                                unit = frame.get("unit", "")
                                
                                # Format timestamp
                                try:
                                    dt = datetime.fromisoformat(timestamp)
                                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                except:
                                    time_str = timestamp
                                
                                # Display formatted output
                                print(f"  Timestamp: {time_str}")
                                print(f"  Sensor ID: {sensor_id}")
                                print(f"  Sensor Name: {sensor_name}")
                                print(f"  Value: {value} {unit}")
                                print(f"  Status: {status}")
                                
                                # Display full JSON structure
                                print("\nJSON Structure:")
                                print(json.dumps(frame, indent=2))
                                
                                # Check for alarms
                                if status == "FAULTY" or value == -999.0:
                                    print(f"\n  ⚠ WARNING: Sensor is FAULTY!")
                                elif value < 20.0 or value > 80.0:
                                    if value < 20.0:
                                        print(f"\n  ⚠ ALARM: LOW value ({value} < 20.0)")
                                    else:
                                        print(f"\n  ⚠ ALARM: HIGH value ({value} > 80.0)")
                                
                                print("=" * 80)
                                print()
                                
                            except json.JSONDecodeError as e:
                                print(f"ERROR: Failed to parse JSON: {e}")
                                print(f"Raw line: {line}")
                                print("=" * 80)
                                print()
                
            except KeyboardInterrupt:
                print("\n\nStopping...")
                break
            except Exception as e:
                print(f"Error reading data: {e}")
                break
        
        ser.close()
        print("Disconnected.")
        
    except serial.SerialException as e:
        print(f"Error connecting to {port}: {e}")
        print("\nMake sure:")
        print("  1. The sensor simulator is running (sensor_serial.py)")
        print("  2. The PTY device path is correct")
        print("  3. No other process is using the device")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Read sensor data from PTY device',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using simplified config string:
  python read_sensor_serial.py --config "/dev/pts/5:115200:8N1"
  python read_sensor_serial.py --config "/dev/pts/6:9600:7E2"
  
  # Using individual arguments:
  python read_sensor_serial.py /dev/pts/5
  python read_sensor_serial.py /dev/pts/5 --baudrate 115200 --bytesize 8 --parity N --stopbits 1
        """
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Simplified config string: port:baudrate:bytesizeparitystopbits\n'
             'Example: /dev/pts/5:115200:8N1'
    )
    parser.add_argument(
        'port',
        type=str,
        nargs='?',
        default=None,
        help='PTY device path (e.g., /dev/pts/5) - required if --config not used'
    )
    parser.add_argument(
        '--baudrate',
        type=int,
        default=115200,
        help='Baudrate (default: 115200)'
    )
    parser.add_argument(
        '--bytesize',
        type=int,
        default=8,
        choices=[5, 6, 7, 8],
        help='Data bits (default: 8)'
    )
    parser.add_argument(
        '--parity',
        type=str,
        default='N',
        choices=['N', 'E', 'O'],
        help='Parity (default: N)'
    )
    parser.add_argument(
        '--stopbits',
        type=int,
        default=1,
        choices=[1, 2],
        help='Stop bits (default: 1)'
    )
    
    args = parser.parse_args()
    
    # If config string is provided, parse it and override other arguments
    if args.config:
        try:
            config = parse_config_string(args.config)
            port = config['port']
            baudrate = config['baudrate']
            bytesize = config['bytesize']
            parity = config['parity']
            stopbits = config['stopbits']
        except ValueError as e:
            print(f"Error parsing config string: {e}")
            sys.exit(1)
    else:
        # Use individual arguments
        if not args.port:
            parser.error("Either --config or port argument is required")
        port = args.port
        baudrate = args.baudrate
        bytesize = args.bytesize
        parity = args.parity
        stopbits = args.stopbits
    
    read_sensor_data(
        port=port,
        baudrate=baudrate,
        bytesize=bytesize,
        parity=parity,
        stopbits=stopbits
    )


if __name__ == "__main__":
    main()

