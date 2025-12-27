"""
Test Modbus connection and reading
"""
from pymodbus.client import ModbusTcpClient
import time

def test_modbus():
    """Test Modbus connection and register reading"""
    host = "localhost"
    port = 1502
    unit_id = 1
    register = 0
    
    print(f"Testing Modbus connection to {host}:{port}...")
    
    try:
        client = ModbusTcpClient(host=host, port=port)
        print(f"Connecting...")
        
        if client.connect():
            print(f"✓ Connected successfully!")
            
            # Try reading register
            print(f"Reading holding register {register} (unit {unit_id})...")
            # Try both slave and unit parameters for compatibility
            try:
                result = client.read_holding_registers(register, 1, slave=unit_id)
            except TypeError:
                result = client.read_holding_registers(register, 1, unit=unit_id)
            
            if result.isError():
                print(f"✗ Error reading register: {result}")
            else:
                if hasattr(result, 'registers') and result.registers:
                    raw_value = result.registers[0]
                    # Handle negative values
                    if raw_value > 32767:
                        raw_value = raw_value - 65536
                    value = raw_value / 10.0
                    print(f"✓ Register {register} value: {raw_value} (raw) = {value} (scaled)")
                else:
                    print(f"✗ No registers returned")
            
            client.close()
        else:
            print(f"✗ Connection failed")
            print("Make sure the Modbus simulator is running!")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_modbus()

