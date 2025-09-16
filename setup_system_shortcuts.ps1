# Setup system-wide shortcuts for AudioTuner (using project directory)
Write-Host "Setting up AudioTuner system shortcuts..." -ForegroundColor Green

$sourceExe = "D:\Mituanapp2\AudioTuner-Desktop-App.exe"
$workingDir = "D:\Mituanapp2"

# Verify source exists
if (-not (Test-Path $sourceExe)) {
    Write-Host "Error: Source executable not found: $sourceExe" -ForegroundColor Red
    exit 1
}

# Check admin privileges for system shortcuts
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "Admin privileges required for system shortcuts. Restarting as admin..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "Creating system shortcuts..." -ForegroundColor Yellow

# Create Start Menu shortcut (All Users)
$startMenuPath = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\AudioTuner.lnk"
try {
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($startMenuPath)
    $Shortcut.TargetPath = $sourceExe
    $Shortcut.WorkingDirectory = $workingDir
    $Shortcut.Description = "AudioTuner Desktop v1.0.0 - Fixed Version"
    $Shortcut.IconLocation = "D:\Mituanapp2\icons\AudioTuner.ico,0"
    $Shortcut.Save()
    Write-Host "Start Menu shortcut created: $startMenuPath" -ForegroundColor Green
} catch {
    Write-Host "Failed to create Start Menu shortcut: $($_.Exception.Message)" -ForegroundColor Red
}

# Create Desktop shortcut (All Users)
$desktopPath = "$env:PUBLIC\Desktop\AudioTuner.lnk"
try {
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($desktopPath)
    $Shortcut.TargetPath = $sourceExe
    $Shortcut.WorkingDirectory = $workingDir
    $Shortcut.Description = "AudioTuner Desktop v1.0.0 - Fixed Version"
    $Shortcut.IconLocation = "D:\Mituanapp2\icons\AudioTuner.ico,0"
    $Shortcut.Save()
    Write-Host "Desktop shortcut created: $desktopPath" -ForegroundColor Green
} catch {
    Write-Host "Failed to create Desktop shortcut: $($_.Exception.Message)" -ForegroundColor Red
}

# Update current user's desktop shortcut
$userDesktopPath = "$env:USERPROFILE\Desktop\AudioTuner 音频调音工具.lnk"
try {
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($userDesktopPath)
    $Shortcut.TargetPath = $sourceExe
    $Shortcut.WorkingDirectory = $workingDir
    $Shortcut.Description = "AudioTuner Desktop v1.0.0 - Fixed Version"
    $Shortcut.IconLocation = "D:\Mituanapp2\icons\AudioTuner.ico,0"
    $Shortcut.Save()
    Write-Host "User desktop shortcut updated: $userDesktopPath" -ForegroundColor Green
} catch {
    Write-Host "Failed to update user desktop shortcut: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Setup completed successfully!" -ForegroundColor Green
Write-Host "AudioTuner can now be launched from:" -ForegroundColor White
Write-Host "- Start Menu -> AudioTuner" -ForegroundColor White
Write-Host "- Desktop shortcut" -ForegroundColor White
Write-Host "- Direct execution: $sourceExe" -ForegroundColor White
Write-Host ""
Write-Host "The program uses the fixed version from the project directory." -ForegroundColor Yellow
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
