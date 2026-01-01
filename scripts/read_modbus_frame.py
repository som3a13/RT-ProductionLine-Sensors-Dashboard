#!/usr/bin/env python3
"""
Script to read and display complete Modbus/TCP frames
Captures both request and response frames with full hex dump and decoding

Author: Mohammed Ismail AbdElmageid
"""
import socket
import struct
import sys
import argparse
from datetime import datetime


class ModbusFrameReader:
    """Reads and decodes complete Modbus/TCP frames"""
    
    def __init__(self, host="localhost", port=1502, unit_id=1):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.sock = None
    
    def connect(self):
        """Connect to Modbus server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((self.host, self.port))
            print(f"✓ Connected to Modbus server at {self.host}:{self.port}\n")
            return True
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False
    
    def decode_mbap_header(self, data):
        """Decode MBAP (Modbus Application Protocol) header"""
        if len(data) < 7:
            return None
        
        transaction_id = struct.unpack('>H', data[0:2])[0]
        protocol_id = struct.unpack('>H', data[2:4])[0]
        length = struct.unpack('>H', data[4:6])[0]
        unit_id = data[6]
        
        return {
            'transaction_id': transaction_id,
            'protocol_id': protocol_id,
            'length': length,
            'unit_id': unit_id
        }
    
    def decode_pdu(self, data, is_response=False):
        """Decode PDU (Protocol Data Unit)"""
        if len(data) < 1:
            return None
        
        function_code = data[0]
        decoded = {'function_code': function_code}
        
        if is_response:
            # Response PDU
            if function_code == 0x03:  # Read Holding Registers
                if len(data) >= 2:
                    byte_count = data[1]
                    decoded['byte_count'] = byte_count
                    
                    # Read register values
                    if len(data) >= 2 + byte_count:
                        registers = []
                        for i in range(0, byte_count, 2):
                            if i + 2 <= byte_count:
                                value = struct.unpack('>H', data[2+i:4+i])[0]
                                registers.append(value)
                        decoded['registers'] = registers
        else:
            # Request PDU
            if function_code == 0x03:  # Read Holding Registers
                if len(data) >= 5:
                    start_address = struct.unpack('>H', data[1:3])[0]
                    quantity = struct.unpack('>H', data[3:5])[0]
                    decoded['start_address'] = start_address
                    decoded['quantity'] = quantity
        
        return decoded
    
    def format_hex(self, data, bytes_per_line=16):
        """Format data as hex dump"""
        lines = []
        for i in range(0, len(data), bytes_per_line):
            chunk = data[i:i+bytes_per_line]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f"{i:04X}:  {hex_str:<48}  {ascii_str}")
        return '\n'.join(lines)
    
    def read_holding_register(self, register_address, quantity=1):
        """Read holding register and capture complete frames"""
        if not self.sock:
            print("Not connected!")
            return None
        
        # Build Modbus/TCP Request Frame
        transaction_id = 0x0001
        protocol_id = 0x0000
        unit_id = self.unit_id
        function_code = 0x03  # Read Holding Registers
        
        # MBAP Header (7 bytes)
        mbap_header = struct.pack('>HHHB',
            transaction_id,    # Transaction ID
            protocol_id,       # Protocol ID (0 = Modbus)
            0x0006,           # Length (6 bytes following)
            unit_id           # Unit ID
        )
        
        # PDU (6 bytes)
        pdu = struct.pack('>BHH',
            function_code,      # Function Code 3
            register_address,   # Starting Address
            quantity           # Quantity of Registers
        )
        
        # Complete Request Frame
        request_frame = mbap_header + pdu
        
        print("=" * 80)
        print("MODBUS/TCP REQUEST FRAME")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        print(f"\nHex Dump ({len(request_frame)} bytes):")
        print(self.format_hex(request_frame))
        
        # Decode and display
        mbap = self.decode_mbap_header(request_frame)
        pdu_data = self.decode_pdu(request_frame[7:], is_response=False)
        
        print(f"\nMBAP Header Decoding:")
        print(f"  Transaction ID: 0x{mbap['transaction_id']:04X} ({mbap['transaction_id']})")
        print(f"  Protocol ID:    0x{mbap['protocol_id']:04X} ({mbap['protocol_id']} = Modbus)")
        print(f"  Length:         0x{mbap['length']:04X} ({mbap['length']} bytes following)")
        print(f"  Unit ID:        0x{mbap['unit_id']:02X} ({mbap['unit_id']})")
        
        print(f"\nPDU Decoding:")
        print(f"  Function Code:  0x{pdu_data['function_code']:02X} ({pdu_data['function_code']} = Read Holding Registers)")
        print(f"  Start Address:  0x{pdu_data['start_address']:04X} (Register {pdu_data['start_address']})")
        print(f"  Quantity:       0x{pdu_data['quantity']:04X} ({pdu_data['quantity']} register(s))")
        
        # Send request
        print(f"\n→ Sending request frame...")
        self.sock.send(request_frame)
        
        # Receive response
        print(f"← Waiting for response...")
        response_frame = self.sock.recv(1024)
        
        if not response_frame:
            print("✗ No response received")
            return None
        
        print("\n" + "=" * 80)
        print("MODBUS/TCP RESPONSE FRAME")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        print(f"\nHex Dump ({len(response_frame)} bytes):")
        print(self.format_hex(response_frame))
        
        # Decode response
        mbap_resp = self.decode_mbap_header(response_frame)
        pdu_resp = self.decode_pdu(response_frame[7:], is_response=True)
        
        print(f"\nMBAP Header Decoding:")
        print(f"  Transaction ID: 0x{mbap_resp['transaction_id']:04X} ({mbap_resp['transaction_id']})")
        print(f"  Protocol ID:    0x{mbap_resp['protocol_id']:04X} ({mbap_resp['protocol_id']} = Modbus)")
        print(f"  Length:         0x{mbap_resp['length']:04X} ({mbap_resp['length']} bytes following)")
        print(f"  Unit ID:        0x{mbap_resp['unit_id']:02X} ({mbap_resp['unit_id']})")
        
        print(f"\nPDU Decoding:")
        print(f"  Function Code:  0x{pdu_resp['function_code']:02X} ({pdu_resp['function_code']} = Read Holding Registers)")
        
        if 'byte_count' in pdu_resp:
            print(f"  Byte Count:     0x{pdu_resp['byte_count']:02X} ({pdu_resp['byte_count']} bytes)")
        
        if 'registers' in pdu_resp and pdu_resp['registers']:
            for i, reg_value in enumerate(pdu_resp['registers']):
                # Handle negative values (two's complement)
                if reg_value > 32767:
                    signed_value = reg_value - 65536
                else:
                    signed_value = reg_value
                
                # Convert to float (divide by 10)
                float_value = signed_value / 10.0
                
                print(f"\n  Register {register_address + i}:")
                print(f"    Raw Value:    0x{reg_value:04X} ({reg_value} unsigned, {signed_value} signed)")
                print(f"    Scaled Value: {float_value} (raw / 10.0)")
        
        print("=" * 80)
        
        return {
            'request': request_frame,
            'response': response_frame,
            'mbap_req': mbap,
            'pdu_req': pdu_data,
            'mbap_resp': mbap_resp,
            'pdu_resp': pdu_resp
        }
    
    def close(self):
        """Close connection"""
        if self.sock:
            self.sock.close()
            print("\nConnection closed.")


def main():
    parser = argparse.ArgumentParser(
        description='Read and display complete Modbus/TCP frames'
    )
    parser.add_argument('--host', type=str, default='localhost',
                       help='Modbus server host (default: localhost)')
    parser.add_argument('--port', type=int, default=1502,
                       help='Modbus server port (default: 1502)')
    parser.add_argument('--unit-id', type=int, default=1,
                       help='Modbus unit ID (default: 1)')
    parser.add_argument('--register', type=int, default=0,
                       help='Register address to read (default: 0)')
    parser.add_argument('--quantity', type=int, default=1,
                       help='Number of registers to read (default: 1)')
    parser.add_argument('--continuous', action='store_true',
                       help='Continuously read frames (press Ctrl+C to stop)')
    parser.add_argument('--interval', type=float, default=1.0,
                       help='Interval between reads in seconds (default: 1.0)')
    
    args = parser.parse_args()
    
    reader = ModbusFrameReader(
        host=args.host,
        port=args.port,
        unit_id=args.unit_id
    )
    
    if not reader.connect():
        sys.exit(1)
    
    try:
        if args.continuous:
            import time
            print("Continuous mode: Reading frames every {:.1f} seconds...".format(args.interval))
            print("Press Ctrl+C to stop.\n")
            count = 0
            while True:
                count += 1
                print(f"\n{'#' * 80}")
                print(f"READ #{count}")
                print(f"{'#' * 80}\n")
                reader.read_holding_register(args.register, args.quantity)
                time.sleep(args.interval)
        else:
            reader.read_holding_register(args.register, args.quantity)
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        reader.close()


if __name__ == "__main__":
    main()





