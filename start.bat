@echo off
chcp 65001 >nul
title 采油二厂井下作业管理系统 - 启动器
echo ============================================
echo  采油二厂井下作业管理系统
echo  正在启动前后端服务...
echo ============================================
echo.

cd /d "%~dp0"

echo [1/2] 启动后端服务...
start "采油二厂-后端" cmd /c ".venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] 启动前端服务...
cd /d "%~dp0frontend"
start "采油二厂-前端" cmd /c "npm run dev"

echo.
echo ============================================
echo  启动完成！
echo.
echo  ⚙ 后端: http://127.0.0.1:8000
echo  ⚙ 前端: http://127.0.0.1:5173
echo  ⚙ 接口文档: http://127.0.0.1:8000/docs
echo.
echo  关闭窗口不会停止服务，请关闭独立的CMD窗口来停止。
echo ============================================
pause
