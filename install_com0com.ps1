# com0com Automated Installation Script
# This script automates the installation and setup of com0com virtual COM ports

param(
    [string]$ZipFile = "com0com-3.0.0.0-i386-and-x64-signed.zip",
    [string[]]$PortPairs = @("COM20,COM21", "COM22,COM23"),
    [switch]$SkipInstall = $false
)

# Setup logging
$LogFile = Join-Path $PSScriptRoot "com0com_install.log"
$StartTime = Get-Date

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Color = "White"
    )
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    
    # Write to console with color
    Write-Host $Message -ForegroundColor $Color
    
    # Write to log file
    Add-Content -Path $LogFile -Value $LogMessage -ErrorAction SilentlyContinue
}

function Write-Log-Success {
    param([string]$Message)
    Write-Log $Message "SUCCESS" "Green"
}

function Write-Log-Error {
    param([string]$Message)
    Write-Log $Message "ERROR" "Red"
}

function Write-Log-Warning {
    param([string]$Message)
    Write-Log $Message "WARNING" "Yellow"
}

function Write-Log-Info {
    param([string]$Message)
    Write-Log $Message "INFO" "Cyan"
}

# Initialize log file
$StartTimeStr = $StartTime.ToString("yyyy-MM-dd HH:mm:ss")
$LogHeader = @"
========================================
com0com Installation Log
Started: $StartTimeStr
========================================
"@
$LogHeader | Out-File -FilePath $LogFile -Encoding UTF8
Write-Log-Info "Log file created: $LogFile"

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Log-Error "This script must be run as Administrator!"
    Write-Log-Info "Right-click PowerShell and select 'Run as Administrator'"
    exit 1
}

Write-Log-Success "Running with Administrator privileges"
Write-Log-Info "=== com0com Automated Installation ==="
Write-Log-Info ""

# Check if zip file exists (look in script directory)
$ZipFilePath = Join-Path $PSScriptRoot $ZipFile
Write-Log-Info "Checking for zip file: $ZipFilePath"
if (-not (Test-Path $ZipFilePath)) {
    Write-Log-Error "Zip file not found: $ZipFilePath"
    Write-Log-Info "Please ensure the com0com zip file is in the script directory: $PSScriptRoot"
    exit 1
}
Write-Log-Success "Zip file found: $ZipFilePath"

# Extract zip file
$ExtractPath = Join-Path $PSScriptRoot "com0com_extracted"
Write-Log-Info "[1/4] Extracting zip file..."
Write-Log-Info "Extraction path: $ExtractPath"

if (Test-Path $ExtractPath) {
    Write-Log-Info "Removing existing extraction directory..."
    Remove-Item $ExtractPath -Recurse -Force
    Write-Log-Success "Removed existing directory"
}
New-Item -ItemType Directory -Path $ExtractPath -Force | Out-Null
Write-Log-Success "Created extraction directory"

Write-Log-Info "Extracting archive..."
try {
    Expand-Archive -Path $ZipFilePath -DestinationPath $ExtractPath -Force
    Write-Log-Success "Extracted to: $ExtractPath"
} catch {
    Write-Log-Error "Failed to extract archive: $_"
    exit 1
}

# Find setup executable
Write-Log-Info "Searching for setup executable..."
# Detect system architecture
$Architecture = if ([Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
Write-Log-Info "Detected system architecture: $Architecture"

# Try to find architecture-specific setup first
$SetupExe = Get-ChildItem -Path $ExtractPath -Recurse -Filter "*Setup*$Architecture*.exe" | Select-Object -First 1

# If not found, try generic setup.exe
if (-not $SetupExe) {
    Write-Log-Info "Architecture-specific setup not found, searching for generic setup.exe..."
    $SetupExe = Get-ChildItem -Path $ExtractPath -Recurse -Filter "setup.exe" | Select-Object -First 1
}

# If still not found, try any Setup*.exe
if (-not $SetupExe) {
    Write-Log-Info "Generic setup.exe not found, searching for any Setup*.exe..."
    $SetupExe = Get-ChildItem -Path $ExtractPath -Recurse -Filter "Setup*.exe" | Select-Object -First 1
}

if (-not $SetupExe) {
    Write-Log-Error "Setup executable not found in extracted files"
    Write-Log-Info "Searched in: $ExtractPath"
    Write-Log-Info "Available files:"
    Get-ChildItem -Path $ExtractPath -Recurse -File | ForEach-Object { Write-Log-Info "  - $($_.Name)" }
    exit 1
}

$SetupPath = $SetupExe.FullName
Write-Log-Success "Found setup executable: $($SetupExe.Name)"
Write-Log-Info "Full path: $SetupPath"
Write-Log-Info ""

# Install com0com
if (-not $SkipInstall) {
    Write-Log-Info "[2/4] Installing com0com driver..."
    Write-Log-Info "This may take a moment and may require a restart..."
    Write-Log-Info "Note: You may see an error dialog about 'com0com.inf' - this is sometimes normal."
    Write-Log-Info "      If the dialog appears, click 'Cancel' and the script will continue."
    Write-Log-Info "Running: $SetupPath /S"
    Write-Log-Info "Working directory: $($SetupExe.DirectoryName)"
    
    try {
        $InstallStartTime = Get-Date
        # Run setup from its directory so it can find any required files (like .inf files)
        # Note: Some setup executables may show error dialogs even with /S flag
        $process = Start-Process -FilePath $SetupPath -ArgumentList "/S" -WorkingDirectory $SetupExe.DirectoryName -Wait -PassThru -NoNewWindow
        $InstallDuration = (Get-Date) - $InstallStartTime
        Write-Log-Info "Installation process completed in $($InstallDuration.TotalSeconds) seconds"
        Write-Log-Info "Exit code: $($process.ExitCode)"
        
        # Check if setupc.exe exists to verify installation
        $SetupcCheck = Get-ChildItem -Path "C:\Program Files*" -Recurse -Filter "setupc.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        
        if ($process.ExitCode -eq 0 -or $process.ExitCode -eq 3010) {
            if ($SetupcCheck) {
                Write-Log-Success "Installation completed successfully (setupc.exe found)"
            } else {
                Write-Log-Warning "Installation reported success, but setupc.exe not found yet."
                Write-Log-Info "This may be normal - the script will search for it in the next step."
            }
            if ($process.ExitCode -eq 3010) {
                Write-Log-Warning "Restart may be required (exit code 3010)"
            }
        } else {
            Write-Log-Warning "Installation exit code: $($process.ExitCode) (may indicate issue)"
            if ($SetupcCheck) {
                Write-Log-Info "However, setupc.exe was found, so installation may have succeeded."
            }
        }
    } catch {
        Write-Log-Error "Exception during installation: $_"
        Write-Log-Warning "Installation may have completed (check manually if needed)"
    }
    Write-Log-Info ""
} else {
    Write-Log-Info "[2/4] Skipping installation (--SkipInstall flag)"
    Write-Log-Info ""
}

# Find setupc.exe (command-line tool)
Write-Log-Info "[3/4] Searching for setupc.exe..."
Write-Log-Info "Searching in Program Files directories..."

$SetupcExe = Get-ChildItem -Path "C:\Program Files*" -Recurse -Filter "setupc.exe" -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $SetupcExe) {
    Write-Log-Info "Not found in Program Files, searching in extracted folder..."
    $SetupcExe = Get-ChildItem -Path $ExtractPath -Recurse -Filter "setupc.exe" | Select-Object -First 1
}

if (-not $SetupcExe) {
    Write-Log-Warning "setupc.exe not found. Port pairs cannot be created automatically."
    Write-Log-Info "You may need to install com0com manually or restart your computer first."
    Write-Log-Info ""
    Write-Log-Info "To create port pairs manually, run:"
    Write-Log-Info "  cd `"C:\Program Files (x86)\com0com`""
    Write-Log-Info "  setupc.exe install PortName=COM10 PortName=COM11"
    exit 0
}

$SetupcPath = $SetupcExe.FullName
Write-Log-Success "Found setupc.exe: $SetupcPath"
Write-Log-Info ""

# Check if com0com.inf exists in system32, if not, try to find and copy it
$InfPath = "C:\WINDOWS\system32\com0com.inf"
if (-not (Test-Path $InfPath)) {
    Write-Log-Warning "com0com.inf not found in C:\WINDOWS\system32"
    Write-Log-Info "Attempting to locate and copy com0com.inf..."
    
    # Search for .inf file in common locations
    $InfFile = $null
    
    # Check in Program Files
    $InfFile = Get-ChildItem -Path "C:\Program Files*" -Recurse -Filter "com0com.inf" -ErrorAction SilentlyContinue | Select-Object -First 1
    
    # Check in Windows\System32\drivers
    if (-not $InfFile) {
        $InfFile = Get-ChildItem -Path "C:\WINDOWS\System32\drivers" -Filter "com0com.inf" -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    
    # Check in extracted folder (in case setup extracted files there)
    if (-not $InfFile) {
        $InfFile = Get-ChildItem -Path $ExtractPath -Recurse -Filter "com0com.inf" -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    
    # Check in Windows temp directory (setup might have extracted there)
    if (-not $InfFile) {
        $TempDirs = Get-ChildItem -Path $env:TEMP -Directory -Filter "*com0com*" -ErrorAction SilentlyContinue
        foreach ($TempDir in $TempDirs) {
            $InfFile = Get-ChildItem -Path $TempDir.FullName -Recurse -Filter "com0com.inf" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($InfFile) { break }
        }
    }
    
    # Try to extract from setup executable using 7-Zip if available
    if (-not $InfFile) {
        Write-Log-Info "Attempting to extract setup executable to find .inf file..."
        $TempExtract = Join-Path $env:TEMP "com0com_setup_extract"
        if (Test-Path $TempExtract) {
            Remove-Item $TempExtract -Recurse -Force -ErrorAction SilentlyContinue
        }
        New-Item -ItemType Directory -Path $TempExtract -Force | Out-Null
        
        # Try using 7-Zip if available
        $7ZipPath = "C:\Program Files\7-Zip\7z.exe"
        if (-not (Test-Path $7ZipPath)) {
            $7ZipPath = "C:\Program Files (x86)\7-Zip\7z.exe"
        }
        
        if (Test-Path $7ZipPath) {
            Write-Log-Info "Using 7-Zip to extract setup executable..."
            try {
                & $7ZipPath x $SetupPath "-o$TempExtract" | Out-Null
                $InfFile = Get-ChildItem -Path $TempExtract -Recurse -Filter "com0com.inf" -ErrorAction SilentlyContinue | Select-Object -First 1
            } catch {
                Write-Log-Warning "Failed to extract with 7-Zip: $_"
            }
        }
    }
    
    # If found, copy to system32
    if ($InfFile) {
        Write-Log-Info "Found com0com.inf at: $($InfFile.FullName)"
        try {
            Copy-Item -Path $InfFile.FullName -Destination $InfPath -Force
            Write-Log-Success "Copied com0com.inf to C:\WINDOWS\system32"
        } catch {
            Write-Log-Error "Failed to copy com0com.inf: $_"
            Write-Log-Warning "Port pair creation may fail without the .inf file"
        }
    } else {
        Write-Log-Warning "Could not locate com0com.inf file"
        Write-Log-Info "The setup executable may need to be run interactively to properly install the .inf file"
        Write-Log-Info "Port pair creation may fail - you may need to manually install com0com or restart your computer"
    }
} else {
    Write-Log-Success "com0com.inf found in C:\WINDOWS\system32"
}
Write-Log-Info ""

# Create COM port pairs
Write-Log-Info "[4/4] Creating virtual COM port pairs..."
Write-Log-Info "Port pairs to create: $($PortPairs -join ', ')"

$created = 0
$failed = 0
foreach ($pair in $PortPairs) {
    $ports = $pair -split ","
    if ($ports.Count -ne 2) {
        Write-Log-Warning "Skipping invalid pair format: $pair (expected: COM1,COM2)"
        continue
    }
    
    $port1 = $ports[0].Trim()
    $port2 = $ports[1].Trim()
    
    Write-Log-Info "Creating pair: $port1 <-> $port2"
    Write-Log-Info "Command: $SetupcPath install PortName=$port1 PortName=$port2"
    
    try {
        # Run setupc.exe from its own directory
        Push-Location $SetupcExe.DirectoryName
        $result = & $SetupcPath install "PortName=$port1" "PortName=$port2" 2>&1
        Pop-Location
        $output = $result | Out-String
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log-Success "Created: $port1 <-> $port2"
            if ($output) {
                Write-Log-Info "Output: $output"
            }
            $created++
        } else {
            Write-Log-Warning "Failed to create $port1 <-> $port2 (exit code: $LASTEXITCODE)"
            if ($output) {
                Write-Log-Info "Output: $output"
            }
            $failed++
        }
    } catch {
        Write-Log-Error "Exception creating $port1 <-> $port2 : $_"
        $failed++
    }
}

Write-Log-Info "Port pair creation summary: $created created, $failed failed"
Write-Log-Info ""

# List all created ports
Write-Log-Info "=== Verification ==="
Write-Log-Info "Listing all COM port pairs..."
try {
    Push-Location $SetupcExe.DirectoryName
    $list = & $SetupcPath list 2>&1
    Pop-Location
    if ($LASTEXITCODE -eq 0) {
        Write-Log-Success "Current COM port pairs:"
        Write-Log-Info $list
        $list | ForEach-Object { Write-Host $_ -ForegroundColor Green }
    } else {
        Write-Log-Warning "Could not list ports (exit code: $LASTEXITCODE)"
    }
} catch {
    Write-Log-Warning "Exception listing ports: $_"
}

Write-Log-Info ""
Write-Log-Success "=== Installation Complete ==="
Write-Log-Info ""
Write-Log-Info "Summary:"
Write-Log-Info "  - Port pairs created: $created"
Write-Log-Info "  - Port pairs failed: $failed"
Write-Log-Info "  - Total pairs requested: $($PortPairs.Count)"
Write-Log-Info ""
Write-Host "Created $created COM port pair(s)" -ForegroundColor Cyan
Write-Host ""
Write-Log-Info "Usage example:"
Write-Host "Usage example:" -ForegroundColor Yellow
Write-Host "  # Simulator side:" -ForegroundColor White
Write-Host "  python simulators\sensor_serial.py --config `"temperature:1:115200:8N1`" --com-port COM10" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Application side (config.json):" -ForegroundColor White
Write-Host "  `"port`": `"COM11`"" -ForegroundColor Gray
Write-Host ""

# Cleanup extracted files
Write-Log-Info "Cleaning up extracted files..."
if (Test-Path $ExtractPath) {
    try {
        Remove-Item $ExtractPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-Log-Success "Cleanup complete: Removed $ExtractPath"
        Write-Host "Cleanup complete" -ForegroundColor Green
    } catch {
        Write-Log-Warning "Could not remove extraction directory: $_"
    }
} else {
    Write-Log-Info "Extraction directory already removed or does not exist"
}

$EndTime = Get-Date
$Duration = $EndTime - $StartTime
Write-Log-Info ""
Write-Log-Info "Total execution time: $($Duration.TotalSeconds) seconds"
Write-Log-Info "========================================"
$CompletionTime = $EndTime.ToString("yyyy-MM-dd HH:mm:ss")
Write-Log-Info "Installation completed at: $CompletionTime"
Write-Log-Info "Log file saved to: $LogFile"
Write-Log-Info "========================================"

Write-Host ""
Write-Host "Done! You can now use the virtual COM ports." -ForegroundColor Green
Write-Host "Log file: $LogFile" -ForegroundColor Cyan

