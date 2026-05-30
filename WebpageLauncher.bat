@echo off
:: Webpage Launcher - Multi-Monitor Layout Manager
:: Launcher script with admin privilege check

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run
) else (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b 0
)

:run
:: Set working directory to the script's location
cd /d "%~dp0"

:: Launch Python with the main application in auto-launch mode
echo Starting Webpage Launcher...
python.exe "src\main.py" --auto-launch

:: If Python errors, keep window open to show errors
if %errorLevel% neq 0 (
    echo.
    echo ============================================
    echo ERROR: Application crashed!
    echo ============================================
    echo Check C:\Users\johnj\SystemLaunch\launch_log.txt for details.
    echo.
    pause
    exit /b %errorLevel%
)

exit /b 0
