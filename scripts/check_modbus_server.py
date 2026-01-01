"""
Check if Modbus server is running and accessible

Author: Mohammed Ismail AbdElmageid
"""
import socket
from pymodbus.client import ModbusTcpClient

def check_port(host, port):
    """Check if port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def test_modbus_connection(host, port, unit_id=1, register=0):
    """Test Modbus connection and read"""
    print(f"Checking Modbus server at {host}:{port}...")
    
    # Check if port is open
    if not check_port(host, port):
        print(f"✗ Port {port} is not open. Modbus server may not be running.")
        print(f"  Make sure to start: python3 simulators/sensor_simulator_simple.py")
        return False
    
    print(f"[OK] Port {port} is open")
    
    # Try Modbus connection
    try:
        print(f"Connecting to Modbus server...")
        client = ModbusTcpClient(host=host, port=port)
        
        if client.connect():
            print(f"[OK] Modbus client connected")
            
            # Try reading a register
            print(f"Reading register {register} (unit {unit_id})...")
            # Try both slave and unit parameters for compatibility
            try:
                result = client.read_holding_registers(register, 1, slave=unit_id)
            except TypeError:
                result = client.read_holding_registers(register, 1, unit=unit_id)
            
            if result.isError():
                print(f"✗ Read error: {result}")
                client.close()
                return False
            
            if hasattr(result, 'registers') and result.registers:
                raw_value = result.registers[0]
                if raw_value > 32767:
                    raw_value = raw_value - 65536
                value = raw_value / 10.0
                print(f"[OK] Register {register} value: {raw_value} (raw) = {value} (scaled)")
                client.close()
                return True
            else:
                print(f"✗ No registers returned")
                client.close()
                return False
        else:
            print(f"✗ Failed to connect to Modbus server")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    
    host = "localhost"
    port = 1502
    unit_id = 1
    register = 0
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        unit_id = int(sys.argv[2])
    if len(sys.argv) > 3:
        register = int(sys.argv[3])
    
    success = test_modbus_connection(host, port, unit_id, register)
    sys.exit(0 if success else 1)

