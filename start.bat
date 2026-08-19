@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动中转站管理面板...
echo 浏览器访问: http://127.0.0.1:8000
echo 按 Ctrl+C 停止服务
echo.
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
