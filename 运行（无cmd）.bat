@echo off
setlocal
cd /d "%~dp0"

if defined RUN_TARGET_PATH (
    set "SCRIPT=%RUN_TARGET_PATH%"
) else (
    set "SCRIPT=%~dp0run.py"
)

if not exist "%SCRIPT%" (
    echo 未找到启动脚本：%SCRIPT%
    pause
    exit /b 2
)

set "PYTHONW_EXE="
for %%I in (
    "%USERPROFILE%\miniconda3\envs\data\pythonw.exe"
    "%USERPROFILE%\anaconda3\envs\data\pythonw.exe"
    "C:\xhz\application\miniconda3\envs\data\pythonw.exe"
) do (
    if not defined PYTHONW_EXE if exist %%~I set "PYTHONW_EXE=%%~I"
)

if not defined PYTHONW_EXE (
    where pythonw >nul 2>nul
    if not errorlevel 1 set "PYTHONW_EXE=pythonw"
)

if not defined PYTHONW_EXE (
    echo 未找到可用的 pythonw.exe。
    pause
    exit /b 9009
)

start "" "%PYTHONW_EXE%" "%SCRIPT%" %*
exit /b 0
