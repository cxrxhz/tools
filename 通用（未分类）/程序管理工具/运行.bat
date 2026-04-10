@echo off
cd /d "%~dp0"

<<<<<<< HEAD
"C:\users\xhz19\anaconda3\envs\data\python.exe" run.py %*
=======
"C:\Users\xhz19\miniconda3\envs\data\python.exe" run.py %*
>>>>>>> e306f001e72a3140d5f087730268c6f1d6ac83d7
if %errorlevel% == 0 (
    exit 0
) else (
    echo 程序执行失败，错误代码：%errorlevel%
    pause
    exit /b %errorlevel%
)

