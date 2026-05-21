@echo off
setlocal
cd /d "%~dp0"

if defined RUN_TARGET_PATH (
    set "SCRIPT=%RUN_TARGET_PATH%"
) else (
    set "SCRIPT=%~dp0event_server.py"
)

if not exist "%SCRIPT%" (
    echo 未找到启动脚本：%SCRIPT%
    pause
    exit /b 2
)

set "PYTHON_EXE="
for %%I in (
    "%USERPROFILE%\miniconda3\envs\data\python.exe"
    "%USERPROFILE%\anaconda3\envs\data\python.exe"
    "C:\xhz\application\miniconda3\envs\data\python.exe"
) do (
    if not defined PYTHON_EXE if exist %%~I set "PYTHON_EXE=%%~I"
)

if not defined PYTHON_EXE (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo 未找到可用的 Python 解释器。
    echo 请确认 data 环境存在，或把 python.exe 加入 PATH。
    pause
    exit /b 9009
)

"%PYTHON_EXE%" "%SCRIPT%" %*
set "EXIT_CODE=%errorlevel%"
if not "%EXIT_CODE%"=="0" (
    echo 程序执行失败，错误代码：%EXIT_CODE%
    pause
)
exit /b %EXIT_CODE%
