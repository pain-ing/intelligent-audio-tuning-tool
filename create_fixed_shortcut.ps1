$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\AudioTuner 音频调音工具 (修复版).lnk")
$Shortcut.TargetPath = "D:\Mituanapp2\run_audiotuner.bat"
$Shortcut.WorkingDirectory = "D:\Mituanapp2"
$Shortcut.Description = "AudioTuner Desktop v1.0.0 - 修复版"
$Shortcut.Save()
Write-Host 'Fixed version desktop shortcut created'
