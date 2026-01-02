#!/usr/bin/env python3
"""
Headless System Startup Script
Starts all simulators and services, automatically updating config.json with correct ports

Author: Mohammed Ismail AbdElmageid
"""
import os
import sys
import json
import re
import subprocess
import time
import signal
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import select for non-blocking I/O (Unix only)
if sys.platform != 'win32':
    import select

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
SIMULATORS_DIR = PROJECT_ROOT / "simulators"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Store process references for cleanup
processes: List[subprocess.Popen] = []


def signal_handler(sig, frame):
    """Handle Ctrl+C to stop all processes"""
    print("\n\nStopping all processes...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception as e:
            print(f"Error stopping process: {e}")
    print("All processes stopped.")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def load_config() -> dict:
    """Load config.json"""
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config.json: {e}")
        sys.exit(1)


def save_config(config: dict):
    """Save config.json"""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"[OK] Updated {CONFIG_PATH}")
    except Exception as e:
        print(f"Error saving config.json: {e}")
        sys.exit(1)


def parse_serial_config(config_str: str) -> dict:
    """Parse serial sensor config string: temperature:1:115200:8N1"""
    parts = config_str.split(':')
    if len(parts) < 2:
        raise ValueError(f"Invalid serial config format: {config_str}")
    
    sensor_type = parts[0]
    sensor_id = int(parts[1])
    baudrate = int(parts[2]) if len(parts) > 2 else 115200
    serial_params = parts[3] if len(parts) > 3 else "8N1"
    
    # Parse serial parameters (8N1 -> bytesize=8, parity=N, stopbits=1)
    bytesize = int(serial_params[0])
    parity = serial_params[1]
    stopbits = int(serial_params[2])
    
    return {
        'sensor_type': sensor_type,
        'sensor_id': sensor_id,
        'baudrate': baudrate,
        'bytesize': bytesize,
        'parity': parity,
        'stopbits': stopbits
    }


def parse_modbus_config(config_str: str) -> dict:
    """Parse Modbus sensor config string: voltage:5:localhost:1502:1:0"""
    parts = config_str.split(':')
    if len(parts) < 6:
        raise ValueError(f"Invalid Modbus config format: {config_str}")
    
    sensor_type = parts[0]
    sensor_id = int(parts[1])
    host = parts[2]
    port = int(parts[3])
    unit_id = int(parts[4])
    register = int(parts[5])
    
    return {
        'sensor_type': sensor_type,
        'sensor_id': sensor_id,
        'host': host,
        'port': port,
        'unit_id': unit_id,
        'register': register
    }


def parse_tcp_sensor_spec(spec: str) -> dict:
    """Parse TCP sensor spec: flow:3:localhost:5000"""
    parts = spec.split(':')
    if len(parts) < 4:
        raise ValueError(f"Invalid TCP sensor spec format: {spec}")
    
    sensor_type = parts[0]
    sensor_id = int(parts[1])
    host = parts[2]
    port = int(parts[3])
    
    # Optional: low:high:unit
    low = float(parts[4]) if len(parts) > 4 else None
    high = float(parts[5]) if len(parts) > 5 else None
    unit = parts[6] if len(parts) > 6 else None
    
    return {
        'sensor_type': sensor_type,
        'sensor_id': sensor_id,
        'host': host,
        'port': port,
        'low': low,
        'high': high,
        'unit': unit
    }


def start_serial_simulator(configs: List[str], com_ports: Optional[List[str]] = None) -> Dict[int, str]:
    """Start serial simulator and capture PTY paths (Linux) or COM ports (Windows)
    
    Args:
        configs: List of serial sensor config strings
        com_ports: Optional list of COM ports for Windows (must match order of configs)
    """
    print("\n" + "="*60)
    print("Starting Serial Sensor Simulator...")
    print("="*60)
    
    # Build command
    cmd = [sys.executable, "-u", str(SIMULATORS_DIR / "sensor_serial.py")]  # -u for unbuffered output
    
    # On Windows, add COM ports if provided
    if sys.platform == 'win32' and com_ports:
        if len(com_ports) != len(configs):
            print(f"Warning: Number of COM ports ({len(com_ports)}) doesn't match number of serial configs ({len(configs)})")
            print("COM ports will be ignored. Please ensure --com-port matches each --serial argument.")
        else:
            # Interleave configs and COM ports
            for i, config_str in enumerate(configs):
                cmd.extend(["--config", config_str])
                if i < len(com_ports):
                    cmd.extend(["--com-port", com_ports[i]])
    else:
        # Linux or no COM ports specified
        for config_str in configs:
            cmd.extend(["--config", config_str])
    
    # Start process and capture output
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,  # Unbuffered
        cwd=str(PROJECT_ROOT),
        env={**os.environ, 'PYTHONUNBUFFERED': '1'}  # Force unbuffered output
    )
    processes.append(proc)
    
    # Parse PTY paths from output
    pty_paths = {}
    configs_parsed = [parse_serial_config(c) for c in configs]
    
    # Wait for PTY/COM port creation (max 10 seconds, but read limited lines)
    start_time = time.time()
    output_buffer = ""
    recent_lines = []  # Keep last 10 lines for pattern matching
    lines_read = 0
    max_lines = 50  # Read max 50 lines to avoid hanging
    timeout_seconds = 5  # Reduced timeout for Windows
    
    # Read output line by line with timeout
    while time.time() - start_time < timeout_seconds and lines_read < max_lines:
        # Use select to check if data is available (non-blocking)
        if sys.platform != 'win32':
            # Unix: use select
            ready, _, _ = select.select([proc.stdout], [], [], 0.5)
            if not ready:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
        else:
            # Windows: check if process is still running and use timeout
            if proc.poll() is not None:
                break
            # On Windows, readline can block, so check if we already have enough information
            if len(pty_paths) >= len(configs):
                # We have all the ports we need, break early
                break
        
        # Try to read a line (may block on Windows, but we have timeout and early exit checks)
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            # On Windows, if no line and process still running, check if we have enough info
            if sys.platform == 'win32' and len(pty_paths) >= len(configs):
                break
            time.sleep(0.1)
            continue
        
        lines_read += 1
        output_buffer += line
        print(line.rstrip(), flush=True)
        
        # Keep recent lines (last 10)
        recent_lines.append(line)
        if len(recent_lines) > 10:
            recent_lines.pop(0)
        
        # Look for pattern: Device: X followed by Sensor ID: Y (or vice versa) in recent lines
        recent_text = ''.join(recent_lines)
        
        # Pattern 1: Device/Port comes before Sensor ID
        pattern1 = r'(?:Device|Port):\s+(/dev/pts/\d+|COM\d+).*?Sensor ID:\s+(\d+)'
        matches1 = re.finditer(pattern1, recent_text, re.DOTALL)
        for match in matches1:
            device = match.group(1)
            sensor_id = int(match.group(2))
            if sensor_id not in pty_paths:
                pty_paths[sensor_id] = device
        
        # Pattern 2: Sensor ID comes before Device/Port
        pattern2 = r'Sensor ID:\s+(\d+).*?(?:Device|Port):\s+(/dev/pts/\d+|COM\d+)'
        matches2 = re.finditer(pattern2, recent_text, re.DOTALL)
        for match in matches2:
            sensor_id = int(match.group(1))
            device = match.group(2)
            if sensor_id not in pty_paths:
                pty_paths[sensor_id] = device
        
        # If we've captured all PTY paths, we can exit early
        if len(pty_paths) >= len(configs):
            break
    
    # Final attempt: parse all collected output if we missed any
    if len(pty_paths) < len(configs):
        for config in configs_parsed:
            if config['sensor_id'] not in pty_paths:
                # Look for sensor ID and device in any order within reasonable distance
                pattern1 = rf"Device:\s+((?:/dev/pts/\d+|COM\d+)).*?Sensor ID:\s+{config['sensor_id']}"
                pattern2 = rf"Sensor ID:\s+{config['sensor_id']}.*?Device:\s+((?:/dev/pts/\d+|COM\d+))"
                match = re.search(pattern1, output_buffer, re.DOTALL) or re.search(pattern2, output_buffer, re.DOTALL)
                if match:
                    pty_paths[config['sensor_id']] = match.group(1)
    
    print(f"\n[OK] Serial simulator started")
    if pty_paths:
        print(f"  Captured PTY paths: {pty_paths}")
    else:
        print(f"  Warning: Could not capture all PTY paths")
        print(f"  You may need to manually update config.json with PTY paths")
    
    return pty_paths


def start_modbus_simulator(configs: List[str]):
    """Start Modbus simulator"""
    print("\n" + "="*60)
    print("Starting Modbus Sensor Simulator...")
    print("="*60)
    
    cmd = [sys.executable, "-u", str(SIMULATORS_DIR / "sensor_modbus.py")]  # -u for unbuffered output
    for config_str in configs:
        cmd.extend(["--config", config_str])
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,  # Unbuffered
        cwd=str(PROJECT_ROOT),
        env={**os.environ, 'PYTHONUNBUFFERED': '1'}  # Force unbuffered output
    )
    processes.append(proc)
    
    # Print initial output with timeout
    start_time = time.time()
    lines_read = 0
    max_lines = 20
    
    while time.time() - start_time < 5 and lines_read < max_lines:
        if sys.platform != 'win32':
            ready, _, _ = select.select([proc.stdout], [], [], 0.5)
            if not ready:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
        else:
            if proc.poll() is not None:
                break
        
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        
        lines_read += 1
        print(line.rstrip(), flush=True)
    
    print(f"[OK] Modbus simulator started")
    return proc


def start_tcp_system(server_ports: List[int], sensors: List[str]):
    """Start TCP sensor system"""
    print("\n" + "="*60)
    print("Starting TCP Sensor System...")
    print("="*60)
    
    cmd = [sys.executable, "-u", str(SIMULATORS_DIR / "start_tcp_system.py")]  # -u for unbuffered output
    cmd.extend(["--server-ports"] + [str(p) for p in server_ports])
    for sensor in sensors:
        cmd.extend(["--sensor", sensor])
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,  # Unbuffered
        cwd=str(PROJECT_ROOT),
        env={**os.environ, 'PYTHONUNBUFFERED': '1'}  # Force unbuffered output
    )
    processes.append(proc)
    
    # Print initial output with timeout
    start_time = time.time()
    lines_read = 0
    max_lines = 25
    
    while time.time() - start_time < 5 and lines_read < max_lines:
        if sys.platform != 'win32':
            ready, _, _ = select.select([proc.stdout], [], [], 0.5)
            if not ready:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
        else:
            if proc.poll() is not None:
                break
        
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        
        lines_read += 1
        print(line.rstrip(), flush=True)
    
    print(f"[OK] TCP system started")
    return proc


def start_webhook_server():
    """Start webhook test server"""
    print("\n" + "="*60)
    print("Starting Webhook Server...")
    print("="*60)
    
    cmd = [sys.executable, "-u", str(SCRIPTS_DIR / "test_webhook_server.py")]  # -u for unbuffered output
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,  # Unbuffered
        cwd=str(PROJECT_ROOT),
        env={**os.environ, 'PYTHONUNBUFFERED': '1'}  # Force unbuffered output
    )
    processes.append(proc)
    
    # Print initial output with timeout
    start_time = time.time()
    lines_read = 0
    max_lines = 10
    
    while time.time() - start_time < 3 and lines_read < max_lines:
        if sys.platform != 'win32':
            ready, _, _ = select.select([proc.stdout], [], [], 0.5)
            if not ready:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
        else:
            if proc.poll() is not None:
                break
        
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        
        lines_read += 1
        print(line.rstrip(), flush=True)
    
    print(f"[OK] Webhook server started")
    return proc


def start_main_application():
    """Start main GUI application"""
    print("\n" + "="*60)
    print("Starting Main Application...")
    print("="*60)
    
    cmd = [sys.executable, str(PROJECT_ROOT / "main.py")]
    
    # For GUI applications, don't redirect stdout/stderr to prevent pipe buffer issues
    # Instead, let output go to the terminal or use DEVNULL for headless
    # Check if running in headless environment
    env = os.environ.copy()
    if sys.platform != 'win32':
        # On Linux, check for DISPLAY variable
        if 'DISPLAY' not in env:
            # No display available, set offscreen platform
            env['QT_QPA_PLATFORM'] = 'offscreen'
            print("  Note: No DISPLAY detected, using offscreen platform")
        # Set unbuffered output for Linux
        env['PYTHONUNBUFFERED'] = '1'
    else:
        # Windows: Set unbuffered output to prevent buffering issues
        env['PYTHONUNBUFFERED'] = '1'
        # Windows: Check if running in headless/server environment
        # On Windows Server or without GUI, we might need special handling
        if 'QT_QPA_PLATFORM' not in env:
            # Check if we're in a headless environment (no console window)
            try:
                # Try to detect if we're in a service or headless environment
                import ctypes
                # Check if we have a console window
                kernel32 = ctypes.windll.kernel32
                if kernel32.GetConsoleWindow() == 0:
                    # No console window, might be headless
                    env['QT_QPA_PLATFORM'] = 'windows:darkmode=0'
                    print("  Note: Running in headless environment on Windows")
            except:
                pass  # Ignore if we can't detect
    
    # Don't redirect stdout/stderr to prevent pipe buffer filling up
    # This allows the GUI to write to console if needed, and prevents hangs
    proc = subprocess.Popen(
        cmd,
        stdout=None,  # Let it go to terminal
        stderr=None,  # Let it go to terminal
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env
    )
    processes.append(proc)
    
    # Give it a moment to start
    time.sleep(1)
    
    # Check if process is still running
    if proc.poll() is None:
        print(f"[OK] Main application started (PID: {proc.pid})")
    else:
        print(f"[ERROR] Main application exited immediately with code {proc.returncode}")
    
    return proc


def update_config_with_serial_paths(config: dict, pty_paths: Dict[int, str]):
    """Update config.json with serial PTY paths (Linux) or COM ports (Windows)
    
    On Windows, virtual COM ports come in pairs (e.g., COM20-COM21, COM22-COM23).
    The simulator uses one end (COM20), and the application should connect to the other end (COM21).
    """
    updated = False
    for sensor in config.get('sensors', []):
        if sensor.get('protocol') == 'serial' and sensor.get('id') in pty_paths:
            old_port = sensor['protocol_config'].get('port')
            simulator_port = pty_paths[sensor['id']]
            
            # On Windows, increment COM port number by 1 (virtual COM ports come in pairs)
            if sys.platform == 'win32' and simulator_port.startswith('COM'):
                try:
                    # Extract COM port number (e.g., "COM20" -> 20)
                    port_num = int(simulator_port[3:])
                    # Increment by 1 for the paired port (COM20 -> COM21)
                    new_port = f"COM{port_num + 1}"
                except (ValueError, IndexError):
                    # If parsing fails, use simulator port as-is
                    new_port = simulator_port
            else:
                # Linux: use PTY path directly
                new_port = simulator_port
            
            if old_port != new_port:
                sensor['protocol_config']['port'] = new_port
                updated = True
                print(f"  Updated sensor {sensor['id']} ({sensor['name']}): {old_port} -> {new_port} (simulator uses {simulator_port})")
    
    return updated


def update_config_with_modbus_configs(config: dict, modbus_configs: List[dict]):
    """Update config.json with Modbus configurations"""
    updated = False
    for modbus_config in modbus_configs:
        sensor_id = modbus_config['sensor_id']
        for sensor in config.get('sensors', []):
            if sensor.get('id') == sensor_id and sensor.get('protocol') == 'modbus':
                protocol_config = sensor['protocol_config']
                if (protocol_config.get('host') != modbus_config['host'] or
                    protocol_config.get('port') != modbus_config['port'] or
                    protocol_config.get('unit_id') != modbus_config['unit_id'] or
                    protocol_config.get('register') != modbus_config['register']):
                    protocol_config['host'] = modbus_config['host']
                    protocol_config['port'] = modbus_config['port']
                    protocol_config['unit_id'] = modbus_config['unit_id']
                    protocol_config['register'] = modbus_config['register']
                    updated = True
                    print(f"  Updated sensor {sensor_id} ({sensor['name']}): Modbus config")
    
    return updated


def update_config_with_tcp_configs(config: dict, tcp_sensors: List[dict]):
    """Update config.json with TCP sensor configurations"""
    updated = False
    for tcp_sensor in tcp_sensors:
        sensor_id = tcp_sensor['sensor_id']
        for sensor in config.get('sensors', []):
            if sensor.get('id') == sensor_id and sensor.get('protocol') == 'tcp':
                protocol_config = sensor['protocol_config']
                if (protocol_config.get('host') != tcp_sensor['host'] or
                    protocol_config.get('port') != tcp_sensor['port']):
                    protocol_config['host'] = tcp_sensor['host']
                    protocol_config['port'] = tcp_sensor['port']
                    updated = True
                    print(f"  Updated sensor {sensor_id} ({sensor['name']}): TCP config")
    
    return updated


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Headless System Startup - Starts all simulators and services',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full system startup (Linux)
  python3 scripts/start_system.py \\
    --serial "temperature:1:115200:8N1" \\
    --serial "pressure:2:115200:8N1" \\
    --modbus "voltage:5:localhost:1502:1:0" \\
    --modbus "pressure:7:localhost:1502:2:0" \\
    --tcp-server-ports 5000 5001 \\
    --tcp-sensor "flow:3:localhost:5000" \\
    --tcp-sensor "vibration:4:localhost:5000" \\
    --tcp-sensor "flow:6:localhost:5001" \\
    --webhook \\
    --main-app
        """
    )
    
    parser.add_argument('--serial', action='append', dest='serial_configs',
                       help='Serial sensor config: TYPE:ID:BAUDRATE:PARAMS (e.g., temperature:1:115200:8N1)')
    parser.add_argument('--com-port', action='append', dest='com_ports',
                       help='COM port for Windows serial sensors (e.g., COM20). Must match order of --serial arguments.')
    parser.add_argument('--modbus', action='append', dest='modbus_configs',
                       help='Modbus sensor config: TYPE:ID:HOST:PORT:UNIT_ID:REGISTER')
    parser.add_argument('--tcp-server-ports', nargs='+', type=int,
                       help='TCP server ports (e.g., 5000 5001)')
    parser.add_argument('--tcp-sensor', action='append', dest='tcp_sensors',
                       help='TCP sensor spec: TYPE:ID:HOST:PORT[:LOW:HIGH:UNIT]')
    parser.add_argument('--webhook', action='store_true',
                       help='Start webhook test server')
    parser.add_argument('--main-app', action='store_true',
                       help='Start main GUI application')
    parser.add_argument('--no-update-config', action='store_true',
                       help='Skip automatic config.json updates')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    
    print("="*60)
    print("RT Production Line Sensors Dashboard - System Startup")
    print("="*60)
    print(f"Config file: {CONFIG_PATH}")
    print(f"Project root: {PROJECT_ROOT}")
    print()
    
    # Start serial simulators
    pty_paths = {}
    if args.serial_configs:
        com_ports = getattr(args, 'com_ports', None)
        pty_paths = start_serial_simulator(args.serial_configs, com_ports)
        time.sleep(3)  # Give time for PTY/COM port creation and output
    
    # Start Modbus simulators
    modbus_procs = []
    modbus_configs_parsed = []
    if args.modbus_configs:
        modbus_configs_parsed = [parse_modbus_config(c) for c in args.modbus_configs]
        start_modbus_simulator(args.modbus_configs)
        time.sleep(2)
    
    # Start TCP system
    tcp_sensors_parsed = []
    if args.tcp_server_ports and args.tcp_sensors:
        tcp_sensors_parsed = [parse_tcp_sensor_spec(s) for s in args.tcp_sensors]
        start_tcp_system(args.tcp_server_ports, args.tcp_sensors)
        time.sleep(2)
    
    # Update config.json
    if not args.no_update_config:
        print("\n" + "="*60)
        print("Updating config.json...")
        print("="*60)
        
        updated = False
        
        if pty_paths:
            if update_config_with_serial_paths(config, pty_paths):
                updated = True
        
        if modbus_configs_parsed:
            if update_config_with_modbus_configs(config, modbus_configs_parsed):
                updated = True
        
        if tcp_sensors_parsed:
            if update_config_with_tcp_configs(config, tcp_sensors_parsed):
                updated = True
        
        if updated:
            save_config(config)
        else:
            print("  No updates needed")
    
    # Start webhook server
    if args.webhook:
        start_webhook_server()
        time.sleep(1)
    
    # Start main application
    if args.main_app:
        start_main_application()
    
    print("\n" + "="*60)
    print("System Startup Complete!")
    print("="*60)
    print("\nAll processes are running. Press Ctrl+C to stop all processes.\n")
    
    # Keep script running and monitor processes
    try:
        while True:
            time.sleep(1)
            # Check if any process has died
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    exit_code = proc.returncode
                    if exit_code is not None:
                        # Negative exit codes indicate signals (e.g., -11 = SIGSEGV, -9 = SIGKILL)
                        if exit_code < 0:
                            signal_name = {
                                -11: "SIGSEGV (Segmentation fault)",
                                -9: "SIGKILL (Killed)",
                                -15: "SIGTERM (Terminated)",
                                -2: "SIGINT (Interrupted)"
                            }.get(exit_code, f"Signal {abs(exit_code)}")
                            print(f"\n[ERROR] Process {i} crashed with {signal_name} (exit code: {exit_code})")
                            print(f"  This usually indicates:")
                            print(f"    - Memory issue (SIGSEGV): Check for memory leaks or invalid memory access")
                            print(f"    - Out of memory (SIGKILL): Process was killed by OOM killer")
                            print(f"    - Segmentation fault: Check for threading or resource issues")
                        else:
                            print(f"\nWarning: Process {i} has exited with code {exit_code}")
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()

