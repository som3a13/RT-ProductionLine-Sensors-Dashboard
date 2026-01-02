@echo off
REM Simple launcher - just double-click this file!

echo ========================================
echo  com0com Automated Installation
echo ========================================
echo.
echo This will request Administrator privileges
echo and run the installation script.
echo.
pause

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%install_com0com.ps1"

:: Run PowerShell script as Administrator
powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -NoExit -File \"%PS_SCRIPT%\"' -Verb RunAs"

