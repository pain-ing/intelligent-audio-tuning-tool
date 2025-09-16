@echo off
echo ========================================
echo AudioTuner Desktop Installer Creator
echo ========================================

set VERSION=1.0.0
set APP_NAME=AudioTuner Desktop
set EXE_FILE=AudioTuner-Desktop.exe
set INSTALLER_NAME=AudioTuner-Desktop-Setup-%VERSION%.exe

echo Creating installer for %APP_NAME% v%VERSION%
echo.

:: Check if the main executable exists
if not exist "%EXE_FILE%" (
    echo ERROR: %EXE_FILE% not found
    echo Please build the application first using packaging/desktop/build.bat
    pause
    exit /b 1
)

:: Get file size
for %%A in ("%EXE_FILE%") do set FILE_SIZE=%%~zA
set /a FILE_SIZE_MB=%FILE_SIZE%/1024/1024
echo Main executable: %EXE_FILE% (%FILE_SIZE_MB% MB)

:: Create installer directory
if not exist "installer" mkdir installer
cd installer

:: Create installer script
echo Creating NSIS installer script...
(
echo ; AudioTuner Desktop Installer
echo ; Generated automatically
echo.
echo !define APP_NAME "%APP_NAME%"
echo !define APP_VERSION "%VERSION%"
echo !define APP_PUBLISHER "AudioTuner Team"
echo !define APP_URL "https://github.com/pain-ing/intelligent-audio-tuning-tool"
echo !define APP_EXE "AudioTuner-Desktop.exe"
echo.
echo ; Installer settings
echo Name "${APP_NAME}"
echo OutFile "%INSTALLER_NAME%"
echo InstallDir "$PROGRAMFILES64\${APP_NAME}"
echo InstallDirRegKey HKLM "Software\${APP_NAME}" "InstallDir"
echo RequestExecutionLevel admin
echo.
echo ; Modern UI
echo !include "MUI2.nsh"
echo.
echo ; Pages
echo !insertmacro MUI_PAGE_WELCOME
echo !insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
echo !insertmacro MUI_PAGE_DIRECTORY
echo !insertmacro MUI_PAGE_INSTFILES
echo !insertmacro MUI_PAGE_FINISH
echo.
echo !insertmacro MUI_UNPAGE_WELCOME
echo !insertmacro MUI_UNPAGE_CONFIRM
echo !insertmacro MUI_UNPAGE_INSTFILES
echo !insertmacro MUI_UNPAGE_FINISH
echo.
echo ; Languages
echo !insertmacro MUI_LANGUAGE "English"
echo !insertmacro MUI_LANGUAGE "SimpChinese"
echo.
echo ; Installer sections
echo Section "Main Application" SecMain
echo   SetOutPath "$INSTDIR"
echo   File "..\${APP_EXE}"
echo   File "LICENSE.txt"
echo   File "README.txt"
echo.
echo   ; Create shortcuts
echo   CreateDirectory "$SMPROGRAMS\${APP_NAME}"
echo   CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
echo   CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
echo   CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
echo.
echo   ; Registry entries
echo   WriteRegStr HKLM "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
echo   WriteRegStr HKLM "Software\${APP_NAME}" "Version" "${APP_VERSION}"
echo.
echo   ; Uninstaller
echo   WriteUninstaller "$INSTDIR\Uninstall.exe"
echo   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
echo   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
echo   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
echo   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
echo   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${APP_URL}"
echo SectionEnd
echo.
echo ; Uninstaller section
echo Section "Uninstall"
echo   Delete "$INSTDIR\${APP_EXE}"
echo   Delete "$INSTDIR\LICENSE.txt"
echo   Delete "$INSTDIR\README.txt"
echo   Delete "$INSTDIR\Uninstall.exe"
echo   RMDir "$INSTDIR"
echo.
echo   Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
echo   Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
echo   RMDir "$SMPROGRAMS\${APP_NAME}"
echo   Delete "$DESKTOP\${APP_NAME}.lnk"
echo.
echo   DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
echo   DeleteRegKey HKLM "Software\${APP_NAME}"
echo SectionEnd
) > installer.nsi

:: Create LICENSE.txt
echo Creating LICENSE file...
(
echo MIT License
echo.
echo Copyright ^(c^) 2025 AudioTuner Team
echo.
echo Permission is hereby granted, free of charge, to any person obtaining a copy
echo of this software and associated documentation files ^(the "Software"^), to deal
echo in the Software without restriction, including without limitation the rights
echo to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
echo copies of the Software, and to permit persons to whom the Software is
echo furnished to do so, subject to the following conditions:
echo.
echo The above copyright notice and this permission notice shall be included in all
echo copies or substantial portions of the Software.
echo.
echo THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
echo IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
echo FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
echo AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
echo LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
echo OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
echo SOFTWARE.
) > LICENSE.txt

:: Create README.txt
echo Creating README file...
(
echo AudioTuner Desktop v%VERSION%
echo =============================
echo.
echo 智能音频调音工具桌面版
echo.
echo 功能特性:
echo - 智能音频风格匹配
echo - Adobe Audition集成
echo - 批量音频处理
echo - 多格式音频转换
echo - 音频质量评估
echo - 实时性能监控
echo.
echo 系统要求:
echo - Windows 7/8/10/11 ^(64位^)
echo - 至少2GB RAM
echo - 500MB可用磁盘空间
echo.
echo 使用说明:
echo 1. 双击桌面图标启动应用
echo 2. 首次运行会在用户目录创建配置文件夹
echo 3. 支持拖拽音频文件进行处理
echo.
echo 技术支持:
echo GitHub: https://github.com/pain-ing/intelligent-audio-tuning-tool
echo.
echo 版权信息:
echo Copyright ^(c^) 2025 AudioTuner Team
echo Licensed under MIT License
) > README.txt

echo.
echo Installer files created successfully!
echo.
echo Files in installer directory:
dir /b
echo.

:: Check if NSIS is available
echo Checking for NSIS compiler...
where makensis >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: NSIS compiler not found
    echo To create the installer, please:
    echo 1. Download NSIS from https://nsis.sourceforge.io/
    echo 2. Install NSIS
    echo 3. Run: makensis installer.nsi
    echo.
    echo Alternative: Use the portable executable directly
    echo The %EXE_FILE% file is already a complete portable application
) else (
    echo NSIS found! Creating installer...
    makensis installer.nsi
    if errorlevel 1 (
        echo ERROR: Failed to create installer
    ) else (
        echo.
        echo ========================================
        echo INSTALLER CREATED SUCCESSFULLY!
        echo ========================================
        echo Installer: %INSTALLER_NAME%
        if exist "%INSTALLER_NAME%" (
            for %%A in ("%INSTALLER_NAME%") do set INSTALLER_SIZE=%%~zA
            set /a INSTALLER_SIZE_MB=!INSTALLER_SIZE!/1024/1024
            echo Size: !INSTALLER_SIZE_MB! MB
        )
        echo.
        echo You can now distribute this installer file.
    )
)

cd ..
echo.
pause
