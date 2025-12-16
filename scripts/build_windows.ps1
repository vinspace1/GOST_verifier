#!/usr/bin/env pwsh
set-StrictMode -Version Latest

# Simple local build script for Windows using PyInstaller
param(
    [string]$Python = "python",
    [switch]$Clean
)

if ($Clean) {
    Remove-Item -Recurse -Force dist, build, *.spec -ErrorAction SilentlyContinue
}

& $Python -m pip install --upgrade pip
& $Python -m pip install pyinstaller

# Build GUI (windowed)
& pyinstaller --noconfirm --onefile --windowed src\gui.py --name GOSTVerifierGUI

# Build core CLI
& pyinstaller --noconfirm --onefile src\core_stub.py --name gost_core

Write-Host "Build finished. Binaries in the dist\ directory"
