@echo off
echo ========================================
echo GitHub Release Creator for AudioTuner
echo ========================================

set VERSION=1.0.0
set TAG_NAME=v%VERSION%
set RELEASE_NAME=AudioTuner Desktop v%VERSION%
set REPO=pain-ing/intelligent-audio-tuning-tool

echo Creating GitHub Release: %RELEASE_NAME%
echo Repository: %REPO%
echo Tag: %TAG_NAME%
echo.

:: Check if gh CLI is installed
where gh >nul 2>&1
if errorlevel 1 (
    echo ERROR: GitHub CLI ^(gh^) not found
    echo.
    echo Please install GitHub CLI first:
    echo 1. Visit: https://cli.github.com/
    echo 2. Download and install GitHub CLI
    echo 3. Run: gh auth login
    echo 4. Then run this script again
    echo.
    echo Alternative: Create release manually at:
    echo https://github.com/%REPO%/releases/new
    pause
    exit /b 1
)

:: Check if user is authenticated
gh auth status >nul 2>&1
if errorlevel 1 (
    echo ERROR: Not authenticated with GitHub
    echo Please run: gh auth login
    pause
    exit /b 1
)

echo GitHub CLI found and authenticated!
echo.

:: Check if files exist
set FILES_TO_UPLOAD=
if exist "AudioTuner-Desktop.exe" (
    echo ✓ Found: AudioTuner-Desktop.exe
    set FILES_TO_UPLOAD=%FILES_TO_UPLOAD% "AudioTuner-Desktop.exe"
) else (
    echo ✗ Missing: AudioTuner-Desktop.exe
)

if exist "installer\AudioTuner-Desktop-Setup-%VERSION%.exe" (
    echo ✓ Found: AudioTuner-Desktop-Setup-%VERSION%.exe
    set FILES_TO_UPLOAD=%FILES_TO_UPLOAD% "installer\AudioTuner-Desktop-Setup-%VERSION%.exe"
) else (
    echo ✗ Missing: AudioTuner-Desktop-Setup-%VERSION%.exe
    echo   Run create_installer.bat first to create the installer
)

if exist "BUILD_INSTRUCTIONS.md" (
    echo ✓ Found: BUILD_INSTRUCTIONS.md
    set FILES_TO_UPLOAD=%FILES_TO_UPLOAD% "BUILD_INSTRUCTIONS.md"
)

if "%FILES_TO_UPLOAD%"=="" (
    echo.
    echo ERROR: No files to upload found
    echo Please ensure the following files exist:
    echo - AudioTuner-Desktop.exe
    echo - installer\AudioTuner-Desktop-Setup-%VERSION%.exe
    pause
    exit /b 1
)

echo.
echo Files to upload:%FILES_TO_UPLOAD%
echo.

:: Create the release
echo Creating GitHub release...
gh release create "%TAG_NAME%" ^
    --repo "%REPO%" ^
    --title "%RELEASE_NAME%" ^
    --notes-file "create_release.md" ^
    --draft ^
    %FILES_TO_UPLOAD%

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create GitHub release
    echo.
    echo Possible solutions:
    echo 1. Check your internet connection
    echo 2. Verify repository permissions
    echo 3. Ensure the tag doesn't already exist
    echo 4. Try creating the release manually
    pause
    exit /b 1
)

echo.
echo ========================================
echo GITHUB RELEASE CREATED SUCCESSFULLY!
echo ========================================
echo.
echo Release: %RELEASE_NAME%
echo Tag: %TAG_NAME%
echo Status: Draft ^(you can publish it from GitHub web interface^)
echo.
echo Next steps:
echo 1. Visit: https://github.com/%REPO%/releases
echo 2. Edit the draft release if needed
echo 3. Click "Publish release" to make it public
echo.
echo Uploaded files:
for %%f in (%FILES_TO_UPLOAD%) do (
    if exist %%f (
        for %%A in (%%f) do (
            set FILE_SIZE=%%~zA
            set /a FILE_SIZE_MB=!FILE_SIZE!/1024/1024
            echo - %%~nxA ^(!FILE_SIZE_MB! MB^)
        )
    )
)

echo.
pause
