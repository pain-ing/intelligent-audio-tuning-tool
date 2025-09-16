@echo off
echo 正在恢复 Audio Tuner 到 Program Files...
echo.

REM 检查是否以管理员权限运行
net session >nul 2>&1
if %errorLevel% == 0 (
    echo 管理员权限确认，开始复制文件...
    copy "D:\Mituanapp2\AudioTuner-Desktop.exe" "C:\Program Files\Audio Tuner\Audio Tuner.exe"
    if %errorLevel% == 0 (
        echo 成功！Audio Tuner 已恢复到 Program Files
        echo 文件位置: C:\Program Files\Audio Tuner\Audio Tuner.exe
    ) else (
        echo 复制失败，错误代码: %errorLevel%
    )
) else (
    echo 需要管理员权限，正在重新启动...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
pause
