# Create desktop shortcut for AudioTuner Desktop App
$sourceExe = "D:\Mituanapp2\AudioTuner-Desktop-App.exe"
$workingDir = "D:\Mituanapp2"

# Verify source exists
if (-not (Test-Path $sourceExe)) {
    Write-Host "Error: Desktop app executable not found: $sourceExe" -ForegroundColor Red
    exit 1
}

Write-Host "Creating desktop shortcut for AudioTuner Desktop App..." -ForegroundColor Green

# Create user desktop shortcut
$userDesktopPath = "$env:USERPROFILE\Desktop\AudioTuner 桌面应用.lnk"
try {
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($userDesktopPath)
    $Shortcut.TargetPath = $sourceExe
    $Shortcut.WorkingDirectory = $workingDir
    $Shortcut.Description = "AudioTuner Desktop App v1.0.0 - 原生桌面应用程序"
    $Shortcut.Save()
    Write-Host "Desktop shortcut created: $userDesktopPath" -ForegroundColor Green
} catch {
    Write-Host "Failed to create desktop shortcut: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Setup completed!" -ForegroundColor Green
Write-Host "You can now launch AudioTuner as a native desktop application!" -ForegroundColor White
Write-Host ""
Write-Host "Features:" -ForegroundColor Yellow
Write-Host "- Native desktop window (no browser required)" -ForegroundColor White
Write-Host "- Standard window controls (minimize, maximize, close)" -ForegroundColor White
Write-Host "- Appears in taskbar like other desktop apps" -ForegroundColor White
Write-Host "- Same powerful audio processing features" -ForegroundColor White
Write-Host ""
Write-Host "Launch methods:" -ForegroundColor Yellow
Write-Host "1. Double-click desktop shortcut: 'AudioTuner 桌面应用'" -ForegroundColor White
Write-Host "2. Direct execution: $sourceExe" -ForegroundColor White
