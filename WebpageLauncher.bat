@echo off
:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run
) else (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit
)

:run
cd /d "C:\Users\johnj\OneDrive\Documents\___DesktopSetup\webpage-launcher"
start /B "" "C:\Users\johnj\OneDrive\Documents\VS_projects\Prohram_IDE_files\webpage_launcher_venv\Scripts\python.exe" "src\main.py"
timeout /t 1 /nobreak >nul
exit /b 0
