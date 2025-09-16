# Downloads embeddable Python and FFmpeg portable and places them under packaging/desktop/vendor
param(
  [string]$PythonVersion = "3.11.9",
  [string]$FfmpegPackage = "ffmpeg-6.1.1-essentials_build"
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktopDir = Split-Path -Parent $root
Set-Location $desktopDir

$vendorDir = Join-Path $desktopDir 'vendor'
$pythonDir = Join-Path $vendorDir 'python'
$ffmpegDir = Join-Path $vendorDir 'ffmpeg'

New-Item -ItemType Directory -Force -Path $vendorDir | Out-Null
New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null
New-Item -ItemType Directory -Force -Path $ffmpegDir | Out-Null

# Download embeddable Python
$pyUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$pyZip = Join-Path $vendorDir "python-$PythonVersion-embed-amd64.zip"
Write-Host "Downloading Python runtime: $pyUrl"
Invoke-WebRequest -Uri $pyUrl -OutFile $pyZip

Write-Host "Extracting Python..."
Expand-Archive -Path $pyZip -DestinationPath $pythonDir -Force
Remove-Item $pyZip -Force

# Download FFmpeg portable (Gyan.dev builds)
$ffUrl = "https://www.gyan.dev/ffmpeg/builds/packages/$FfmpegPackage.zip"
$ffZip = Join-Path $vendorDir "$FfmpegPackage.zip"
Write-Host "Downloading FFmpeg: $ffUrl"
Invoke-WebRequest -Uri $ffUrl -OutFile $ffZip

Write-Host "Extracting FFmpeg..."
Expand-Archive -Path $ffZip -DestinationPath $ffmpegDir -Force
# Move binaries up if needed (package structure may be ffmpeg-*/bin)
$binPath = Get-ChildItem -Path $ffmpegDir -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'bin') } | Select-Object -First 1
if ($binPath) {
  Copy-Item -Path (Join-Path $binPath.FullName 'bin/*') -Destination $ffmpegDir -Recurse -Force
  Remove-Item -Recurse -Force $binPath
}
Remove-Item $ffZip -Force

Write-Host "Vendor downloads complete."

