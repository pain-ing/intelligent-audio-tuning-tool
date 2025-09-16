$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\AudioTuner-Fixed.lnk")
$Shortcut.TargetPath = "D:\Mituanapp2\run_audiotuner.bat"
$Shortcut.WorkingDirectory = "D:\Mituanapp2"
$Shortcut.Description = "AudioTuner Desktop Fixed Version"
$Shortcut.Save()
Write-Host 'Desktop shortcut created successfully'
