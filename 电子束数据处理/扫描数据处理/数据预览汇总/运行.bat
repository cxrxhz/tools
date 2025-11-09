@echo off
cd /d "%~dp0"

"C:\xhz\application\miniconda3\envs\data\python.exe" run.py %*
if %errorlevel% == 0 (
    exit 0
) else (
    echo 程序执行失败，错误代码：%errorlevel%
    pause
    exit /b %errorlevel%
)
