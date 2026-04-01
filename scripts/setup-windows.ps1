# PDF Compare - Windows Build Setup
# Run this script on a fresh Windows machine to install all dependencies and build the app.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\setup-windows.ps1

param(
    [switch]$SkipInstall,  # Skip dependency installation, only build
    [switch]$BuildOnly     # Alias for SkipInstall
)

$ErrorActionPreference = "Stop"
$SkipDeps = $SkipInstall -or $BuildOnly

# Ensure we run from project root regardless of where the script is called from
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "`n=== PDF Compare - Windows Build Setup ===" -ForegroundColor Cyan
Write-Host ""

# --- Helper ---
function Test-Command($cmd) {
    try { Get-Command $cmd -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}

function Install-WithWinget($id, $name) {
    Write-Host "Installing $name via winget..." -ForegroundColor Yellow
    winget install --id $id --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install $name. Please install manually." -ForegroundColor Red
        exit 1
    }
}

# --- Step 1: Check/Install Rust ---
if (-not $SkipDeps) {
    Write-Host "[1/5] Checking Rust..." -ForegroundColor Green
    if (Test-Command "rustc") {
        $rustVersion = rustc --version
        Write-Host "  Found: $rustVersion"
    } else {
        Write-Host "  Rust not found. Installing via rustup..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri "https://win.rustup.rs/x86_64" -OutFile "$env:TEMP\rustup-init.exe"
        & "$env:TEMP\rustup-init.exe" -y --default-toolchain stable
        $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
        if (-not (Test-Command "rustc")) {
            Write-Host "ERROR: Rust installation failed. Please restart terminal and try again." -ForegroundColor Red
            exit 1
        }
        Write-Host "  Installed: $(rustc --version)"
    }

    # --- Step 2: Check/Install Node.js ---
    Write-Host "[2/5] Checking Node.js..." -ForegroundColor Green
    if (Test-Command "node") {
        $nodeVersion = node --version
        Write-Host "  Found: Node.js $nodeVersion"
    } else {
        if (Test-Command "winget") {
            Install-WithWinget "OpenJS.NodeJS.LTS" "Node.js"
        } else {
            Write-Host "  ERROR: Node.js not found and winget not available." -ForegroundColor Red
            Write-Host "  Please install Node.js LTS from https://nodejs.org/" -ForegroundColor Red
            exit 1
        }
        # Refresh PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
    }

    # --- Step 3: Check/Install Python ---
    Write-Host "[3/5] Checking Python..." -ForegroundColor Green
    $pythonCmd = $null
    if (Test-Command "python") { $pythonCmd = "python" }
    elseif (Test-Command "python3") { $pythonCmd = "python3" }

    if ($pythonCmd) {
        $pyVersion = & $pythonCmd --version
        Write-Host "  Found: $pyVersion"
    } else {
        if (Test-Command "winget") {
            Install-WithWinget "Python.Python.3.12" "Python 3.12"
        } else {
            Write-Host "  ERROR: Python not found and winget not available." -ForegroundColor Red
            Write-Host "  Please install Python 3.11+ from https://python.org/" -ForegroundColor Red
            exit 1
        }
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        $pythonCmd = "python"
    }

    # --- Step 4: Install npm dependencies ---
    Write-Host "[4/5] Installing npm dependencies..." -ForegroundColor Green
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: npm install failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "  npm dependencies installed."

    # --- Step 5: Install Python dependencies ---
    Write-Host "[5/5] Installing Python dependencies..." -ForegroundColor Green
    & $pythonCmd -m pip install --upgrade pip --quiet
    Push-Location pdfdiff
    & $pythonCmd -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: pip install failed." -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location
    Write-Host "  Python dependencies installed."
}

# --- Build Sidecar ---
Write-Host "`n[Build] Building pdfdiff sidecar..." -ForegroundColor Cyan
Push-Location pdfdiff
$pythonCmd = if (Test-Command "python") { "python" } else { "python3" }
& $pythonCmd -m PyInstaller pdfdiff.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyInstaller build failed." -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# Copy sidecar with correct Tauri target suffix
$target = (rustc -vV | Select-String "host:").ToString().Split(" ")[1]
$sidecarSrc = "pdfdiff\dist\pdfdiff.exe"
$sidecarDst = "src-tauri\binaries\pdfdiff-$target.exe"

if (-not (Test-Path "src-tauri\binaries")) {
    New-Item -ItemType Directory -Path "src-tauri\binaries" | Out-Null
}

Copy-Item $sidecarSrc $sidecarDst -Force
Write-Host "  Sidecar copied to $sidecarDst"

# --- Build Tauri App ---
Write-Host "`n[Build] Building Tauri app..." -ForegroundColor Cyan
npx tauri build
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Tauri build failed." -ForegroundColor Red
    exit 1
}

# --- Done ---
Write-Host "`n=== Build Complete! ===" -ForegroundColor Green
$msiPath = Get-ChildItem -Path "src-tauri\target\release\bundle\msi\*.msi" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($msiPath) {
    Write-Host "MSI Installer: $($msiPath.FullName)" -ForegroundColor Cyan
} else {
    Write-Host "Check src-tauri\target\release\bundle\ for build output." -ForegroundColor Yellow
}
Write-Host ""
