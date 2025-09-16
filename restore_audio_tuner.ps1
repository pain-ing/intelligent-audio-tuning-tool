# AudioTuner Recovery Script
Write-Host "AudioTuner Recovery Script" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green

$sourceExe = "D:\Mituanapp2\AudioTuner-Desktop.exe"
$targetDir = "C:\Program Files\Audio Tuner"
$targetExe = "$targetDir\Audio Tuner.exe"

# Check source file
if (-not (Test-Path $sourceExe)) {
    Write-Host "Error: Source file not found: $sourceExe" -ForegroundColor Red
    exit 1
}

Write-Host "Source: $sourceExe" -ForegroundColor Yellow
Write-Host "Target: $targetExe" -ForegroundColor Yellow

# Check admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "Admin privileges required. Restarting as admin..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "Admin privileges confirmed" -ForegroundColor Green

# Ensure target directory exists
if (-not (Test-Path $targetDir)) {
    Write-Host "Creating target directory: $targetDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

# Copy file
try {
    Write-Host "Copying file..." -ForegroundColor Yellow
    Copy-Item $sourceExe $targetExe -Force
    Write-Host "File copied successfully!" -ForegroundColor Green
} catch {
    Write-Host "Copy failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Verify
if (Test-Path $targetExe) {
    $fileInfo = Get-Item $targetExe
    Write-Host "Recovery successful!" -ForegroundColor Green
    Write-Host "File size: $([math]::Round($fileInfo.Length / 1MB, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "Verification failed" -ForegroundColor Red
    exit 1
}

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
