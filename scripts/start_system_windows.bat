@echo off
REM Quick Start Script for Windows
REM Starts all simulators and services, automatically updating config.json
REM
REM Author: Mohammed Ismail AbdElmageid

setlocal enabledelayedexpansion

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Change to project root
cd /d "%PROJECT_ROOT%"

echo ============================================================
echo RT Production Line Sensors Dashboard - Quick Start (Windows)
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to your PATH
    pause
    exit /b 1
)

REM Start all services using the Python startup script
REM Note: Windows requires COM ports to be specified for serial sensors
REM Adjust COM ports (COM20, COM22) based on your available ports
REM For virtual COM ports, install com0com to create COM port pairs
python "%SCRIPT_DIR%start_system.py" ^
    --serial "temperature:1:115200:8N1" ^
    --com-port COM20 ^
    --serial "pressure:2:115200:8N1" ^
    --com-port COM22 ^
    --modbus "voltage:5:localhost:1502:1:0" ^
    --modbus "pressure:7:localhost:1502:2:0" ^
    --tcp-server-ports 5000 5001 ^
    --tcp-sensor "flow:3:localhost:5000" ^
    --tcp-sensor "vibration:4:localhost:5000" ^
    --tcp-sensor "flow:6:localhost:5001" ^
    --webhook ^
    --main-app

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start system
    pause
    exit /b 1
)

endlocal

