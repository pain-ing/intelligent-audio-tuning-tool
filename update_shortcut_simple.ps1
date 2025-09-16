$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\AudioTuner 音频调音工具.lnk")
$Shortcut.TargetPath = "D:\Mituanapp2\AudioTuner-Desktop.exe"
$Shortcut.WorkingDirectory = "D:\Mituanapp2"
$Shortcut.Description = "AudioTuner Desktop v1.0.0 - Fixed Version"
$Shortcut.Save()
Write-Host 'Desktop shortcut updated successfully!'
