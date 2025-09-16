# 创建桌面快捷方式脚本
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\AudioTuner 音频调音工具.lnk")
$Shortcut.TargetPath = "D:\Mituanapp2\AudioTuner-Desktop.exe"
$Shortcut.WorkingDirectory = "D:\Mituanapp2"
$Shortcut.Description = "AudioTuner Desktop v1.0.0 - 智能音频调音工具"
$Shortcut.Save()
Write-Host "桌面快捷方式已创建：AudioTuner 音频调音工具.lnk"
Write-Host "快捷方式位置：$env:USERPROFILE\Desktop\AudioTuner 音频调音工具.lnk"
