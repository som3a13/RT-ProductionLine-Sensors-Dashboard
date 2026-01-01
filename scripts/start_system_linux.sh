#!/bin/bash
# Quick Start Script for Linux
# Starts all simulators and services, automatically updating config.json

# Author: Mohammed Ismail AbdElmageid

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "============================================================"
echo "RT Production Line Sensors Dashboard - Quick Start (Linux)"
echo "============================================================"
echo ""

# Start all services using the Python startup script
python3 "$SCRIPT_DIR/start_system.py" \
    --serial "temperature:1:115200:8N1" \
    --serial "pressure:2:115200:8N1" \
    --modbus "voltage:5:localhost:1502:1:0" \
    --modbus "pressure:7:localhost:1502:2:0" \
    --tcp-server-ports 5000 5001 \
    --tcp-sensor "flow:3:localhost:5000" \
    --tcp-sensor "vibration:4:localhost:5000" \
    --tcp-sensor "flow:6:localhost:5001" \
    --webhook \
    --main-app

