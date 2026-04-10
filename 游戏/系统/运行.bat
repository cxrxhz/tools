@echo off
cd /d "%~dp0"
echo 当前目录：%cd%
echo 正在运行 Python 脚本...
"C:\Users\xhz19\miniconda3\envs\data\python.exe" "%cd%\event_server.py" %*
if %errorlevel% == 0 (
    exit 0
) else (
    echo 程序执行失败，错误代码：%errorlevel%
    pause
    exit /b %errorlevel%
)
