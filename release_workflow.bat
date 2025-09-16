@echo off
echo ========================================
echo AudioTuner Desktop Release Workflow
echo ========================================

set VERSION=1.0.0

echo This script will:
echo 1. Verify all files are ready
echo 2. Create installer package
echo 3. Create GitHub release
echo 4. Upload all assets
echo.
echo Version: %VERSION%
echo.
echo Press any key to continue, or Ctrl+C to cancel...
pause >nul

echo.
echo [1/4] Verifying files...
echo ----------------------------------------

:: Check main executable
if not exist "AudioTuner-Desktop.exe" (
    echo ERROR: AudioTuner-Desktop.exe not found
    echo Please build the application first using packaging/desktop/build.bat
    goto :error
)

for %%A in ("AudioTuner-Desktop.exe") do set FILE_SIZE=%%~zA
set /a FILE_SIZE_MB=%FILE_SIZE%/1024/1024
echo ✓ AudioTuner-Desktop.exe (%FILE_SIZE_MB% MB)

:: Check documentation
if not exist "BUILD_INSTRUCTIONS.md" (
    echo WARNING: BUILD_INSTRUCTIONS.md not found
) else (
    echo ✓ BUILD_INSTRUCTIONS.md
)

if not exist "create_release.md" (
    echo WARNING: create_release.md not found
) else (
    echo ✓ create_release.md
)

echo.
echo [2/4] Creating installer...
echo ----------------------------------------

call create_installer.bat
if errorlevel 1 (
    echo ERROR: Failed to create installer
    goto :error
)

echo.
echo [3/4] Checking GitHub CLI...
echo ----------------------------------------

where gh >nul 2>&1
if errorlevel 1 (
    echo GitHub CLI not found. Skipping automatic release creation.
    echo.
    echo Manual steps:
    echo 1. Visit: https://github.com/pain-ing/intelligent-audio-tuning-tool/releases/new
    echo 2. Create a new release with tag: v%VERSION%
    echo 3. Upload the following files:
    echo    - AudioTuner-Desktop.exe
    if exist "installer\AudioTuner-Desktop-Setup-%VERSION%.exe" (
        echo    - installer\AudioTuner-Desktop-Setup-%VERSION%.exe
    )
    echo    - BUILD_INSTRUCTIONS.md
    echo 4. Copy the content from create_release.md as the release description
    goto :manual_release
)

gh auth status >nul 2>&1
if errorlevel 1 (
    echo GitHub CLI found but not authenticated.
    echo Please run: gh auth login
    goto :error
)

echo ✓ GitHub CLI ready

echo.
echo [4/4] Creating GitHub release...
echo ----------------------------------------

call create_github_release.bat
if errorlevel 1 (
    echo ERROR: Failed to create GitHub release
    goto :error
)

goto :success

:manual_release
echo.
echo ========================================
echo MANUAL RELEASE REQUIRED
echo ========================================
echo.
echo Files ready for upload:
echo - AudioTuner-Desktop.exe (%FILE_SIZE_MB% MB)
if exist "installer\AudioTuner-Desktop-Setup-%VERSION%.exe" (
    for %%A in ("installer\AudioTuner-Desktop-Setup-%VERSION%.exe") do (
        set INSTALLER_SIZE=%%~zA
        set /a INSTALLER_SIZE_MB=!INSTALLER_SIZE!/1024/1024
        echo - AudioTuner-Desktop-Setup-%VERSION%.exe ^(!INSTALLER_SIZE_MB! MB^)
    )
)
echo - BUILD_INSTRUCTIONS.md
echo.
echo Please create the release manually at:
echo https://github.com/pain-ing/intelligent-audio-tuning-tool/releases/new
goto :end

:success
echo.
echo ========================================
echo RELEASE WORKFLOW COMPLETED!
echo ========================================
echo.
echo ✓ Application built and verified
echo ✓ Installer created
echo ✓ GitHub release created
echo.
echo The release is created as a draft. To publish:
echo 1. Visit: https://github.com/pain-ing/intelligent-audio-tuning-tool/releases
echo 2. Edit the draft release if needed
echo 3. Click "Publish release"
echo.
echo Release assets:
echo - AudioTuner-Desktop.exe (%FILE_SIZE_MB% MB) - Portable application
if exist "installer\AudioTuner-Desktop-Setup-%VERSION%.exe" (
    for %%A in ("installer\AudioTuner-Desktop-Setup-%VERSION%.exe") do (
        set INSTALLER_SIZE=%%~zA
        set /a INSTALLER_SIZE_MB=!INSTALLER_SIZE!/1024/1024
        echo - AudioTuner-Desktop-Setup-%VERSION%.exe ^(!INSTALLER_SIZE_MB! MB^) - Windows installer
    )
)
echo - BUILD_INSTRUCTIONS.md - Build documentation
goto :end

:error
echo.
echo ========================================
echo RELEASE WORKFLOW FAILED
echo ========================================
echo.
echo Please check the errors above and try again.
goto :end

:end
echo.
pause
