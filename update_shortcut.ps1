# 更新桌面快捷方式指向修复后的可执行文件
$WshShell = New-Object -comObject WScript.Shell

# 更新原有快捷方式
$OriginalShortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\AudioTuner 音频调音工具.lnk")
$OriginalShortcut.TargetPath = "D:\Mituanapp2\AudioTuner-Desktop.exe"
$OriginalShortcut.WorkingDirectory = "D:\Mituanapp2"
$OriginalShortcut.Description = "AudioTuner Desktop v1.0.0 - Fixed Version"
$OriginalShortcut.Save()

Write-Host 'Original shortcut updated successfully'

# 删除临时修复版快捷方式（如果存在）
$TempShortcuts = @(
    "$env:USERPROFILE\Desktop\AudioTuner-Fixed.lnk"
)

foreach ($shortcut in $TempShortcuts) {
    if (Test-Path $shortcut) {
        Remove-Item $shortcut -Force
        Write-Host "Removed temporary shortcut: $shortcut"
    }
}

Write-Host 'Desktop shortcuts updated successfully!'
Write-Host 'You can now use the original AudioTuner shortcut with the fixed executable.'
