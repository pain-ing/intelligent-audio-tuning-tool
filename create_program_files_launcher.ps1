# Create a launcher script for Program Files installation
$targetDir = "C:\Program Files\Audio Tuner"
$launcherScript = @"
@echo off
cd /d "C:\Program Files\Audio Tuner"
start "" "Audio Tuner.exe"
"@

$launcherPath = "$targetDir\Launch Audio Tuner.bat"

# Check admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "Admin privileges required. Restarting as admin..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Create launcher script
try {
    $launcherScript | Out-File -FilePath $launcherPath -Encoding ASCII -Force
    Write-Host "Launcher script created: $launcherPath" -ForegroundColor Green
} catch {
    Write-Host "Failed to create launcher: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Update shortcuts to use launcher
$shortcuts = @(
    "$env:PUBLIC\Desktop\Audio Tuner.lnk",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Audio Tuner.lnk"
)

foreach ($shortcutPath in $shortcuts) {
    try {
        if (Test-Path $shortcutPath) {
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut($shortcutPath)
            $Shortcut.TargetPath = $launcherPath
            $Shortcut.WorkingDirectory = $targetDir
            $Shortcut.Description = "AudioTuner Desktop v1.0.0 - Fixed Version"
            $Shortcut.Save()
            Write-Host "Updated shortcut: $shortcutPath" -ForegroundColor Green
        }
    } catch {
        Write-Host "Failed to update shortcut $shortcutPath : $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
