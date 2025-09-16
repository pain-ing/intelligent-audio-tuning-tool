@echo off
echo ========================================
echo Audio Tuner Desktop Build Script
echo ========================================

set ROOT_DIR=%~dp0..\..
set PACKAGING_DIR=%~dp0
set FRONTEND_DIR=%ROOT_DIR%\frontend

echo Root directory: %ROOT_DIR%
echo Packaging directory: %PACKAGING_DIR%
echo Frontend directory: %FRONTEND_DIR%

echo.
echo [1/5] Checking prerequisites...
echo ----------------------------------------

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Please install Node.js first.
    pause
    exit /b 1
)
echo Node.js: OK

:: Check npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm not found. Please install npm first.
    pause
    exit /b 1
)
echo npm: OK

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)
echo Python: OK

echo.
echo [2/5] Building frontend...
echo ----------------------------------------

cd /d "%FRONTEND_DIR%"
if not exist "package.json" (
    echo ERROR: Frontend package.json not found
    pause
    exit /b 1
)

echo Installing frontend dependencies...
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies
    pause
    exit /b 1
)

echo Building frontend...
call npm run build
if errorlevel 1 (
    echo ERROR: Failed to build frontend
    pause
    exit /b 1
)

if not exist "build\index.html" (
    echo ERROR: Frontend build failed - no index.html found
    pause
    exit /b 1
)
echo Frontend build: OK

echo.
echo [3/5] Preparing desktop packaging...
echo ----------------------------------------

cd /d "%PACKAGING_DIR%"

:: Kill any running Electron processes
echo Stopping any running Electron processes...
taskkill /F /IM electron.exe >nul 2>&1
taskkill /F /IM AudioTuner*.exe >nul 2>&1
timeout /t 3 /nobreak >nul

:: Clean build directories
echo Cleaning build directories...
if exist "dist" rmdir /s /q "dist" >nul 2>&1
if exist "dist_rf5" rmdir /s /q "dist_rf5" >nul 2>&1
if exist "out_build" rmdir /s /q "out_build" >nul 2>&1
if exist "release" rmdir /s /q "release" >nul 2>&1

:: Remove lock files
if exist "package-lock.json" del "package-lock.json" >nul 2>&1
if exist "yarn.lock" del "yarn.lock" >nul 2>&1

echo.
echo [4/5] Installing Electron dependencies...
echo ----------------------------------------

:: Try to remove node_modules if it exists
if exist "node_modules" (
    echo Removing existing node_modules...
    rmdir /s /q "node_modules" >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo Installing Electron dependencies...
call npm install --no-package-lock --legacy-peer-deps
if errorlevel 1 (
    echo WARNING: npm install failed, trying alternative approach...
    call npm install --force
    if errorlevel 1 (
        echo ERROR: Failed to install Electron dependencies
        pause
        exit /b 1
    )
)
echo Electron dependencies: OK

echo.
echo [5/5] Building Electron application...
echo ----------------------------------------

echo Building Electron app...
call npm run build
if errorlevel 1 (
    echo ERROR: Failed to build Electron application
    pause
    exit /b 1
)

:: Find the generated exe file
set EXE_FILE=
for /r "dist_rf5" %%f in (*.exe) do set EXE_FILE=%%f
if "%EXE_FILE%"=="" (
    for /r "dist" %%f in (*.exe) do set EXE_FILE=%%f
)
if "%EXE_FILE%"=="" (
    for /r "release" %%f in (*.exe) do set EXE_FILE=%%f
)

if "%EXE_FILE%"=="" (
    echo ERROR: No executable file found after build
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD COMPLETED SUCCESSFULLY!
echo ========================================
echo Executable: %EXE_FILE%

:: Get file size
for %%A in ("%EXE_FILE%") do set FILE_SIZE=%%~zA
set /a FILE_SIZE_MB=%FILE_SIZE%/1024/1024
echo Size: %FILE_SIZE_MB% MB

:: Copy to root directory with a friendly name
set TARGET_FILE=%ROOT_DIR%\AudioTuner-Desktop.exe
copy "%EXE_FILE%" "%TARGET_FILE%" >nul
if errorlevel 1 (
    echo WARNING: Failed to copy to root directory
) else (
    echo Copied to: %TARGET_FILE%
)

echo.
echo Build completed! You can now run the application.
echo.
pause
