@echo off
echo ========================================
echo Testing AudioTuner Desktop Application
echo ========================================

if not exist "AudioTuner-Desktop.exe" (
    echo ERROR: AudioTuner-Desktop.exe not found
    echo Please run the build script first.
    pause
    exit /b 1
)

echo Executable found: AudioTuner-Desktop.exe

:: Get file info
for %%A in ("AudioTuner-Desktop.exe") do (
    set FILE_SIZE=%%~zA
    set FILE_DATE=%%~tA
)
set /a FILE_SIZE_MB=%FILE_SIZE%/1024/1024
echo File size: %FILE_SIZE_MB% MB
echo Last modified: %FILE_DATE%

echo.
echo Starting application...
echo (This will open the AudioTuner desktop application)
echo Press Ctrl+C to cancel, or any other key to continue...
pause >nul

echo.
echo Launching AudioTuner-Desktop.exe...
start "" "AudioTuner-Desktop.exe"

echo.
echo Application launched!
echo If the application doesn't start properly, check the following:
echo 1. Windows Defender or antivirus might be blocking it
echo 2. Required dependencies might be missing
echo 3. Check the application logs in %%USERPROFILE%%\.audio_tuner\app.log
echo.
pause
