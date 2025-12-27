#!/usr/bin/env python3
"""Check which TCP servers are needed from config.json"""
import json
from pathlib import Path

config_path = Path(__file__).parent.parent / 'config' / 'config.json'
with open(config_path, 'r') as f:
    config = json.load(f)

tcp_sensors = [s for s in config['sensors'] if s.get('protocol') == 'tcp']
print(f"Total TCP sensors: {len(tcp_sensors)}")

servers = {}
for sensor in tcp_sensors:
    host = sensor['protocol_config']['host']
    port = sensor['protocol_config']['port']
    key = (host, port)
    if key not in servers:
        servers[key] = []
    servers[key].append((sensor['id'], sensor['name']))

print(f"\nUnique TCP servers needed: {len(servers)}\n")
for (host, port), sensors in servers.items():
    sensor_list = ', '.join([f"ID {sid} ({name})" for sid, name in sensors])
    print(f"  {host}:{port}")
    print(f"    Sensors: {sensor_list}")

