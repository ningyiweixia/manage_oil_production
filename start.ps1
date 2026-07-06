Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 采油二厂井下作业管理系统" -ForegroundColor Cyan
Write-Host " 正在启动前后端服务..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "[1/2] 启动后端服务..." -ForegroundColor Green
Start-Process powershell -WindowStyle Normal -ArgumentList @"
cd '$ProjectRoot'; Write-Host '后端服务 - UVICORN' -ForegroundColor Yellow; `$env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload; pause
"@

Write-Host "[2/2] 启动前端服务..." -ForegroundColor Green
Start-Process powershell -WindowStyle Normal -ArgumentList @"
cd '$ProjectRoot\frontend'; Write-Host '前端服务 - VITE' -ForegroundColor Yellow; npm run dev; pause
"@

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 启动完成！" -ForegroundColor Cyan
Write-Host ""
Write-Host " ⚙ 后端: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host " ⚙ 前端: http://127.0.0.1:5173" -ForegroundColor Cyan
Write-Host " ⚙ 接口文档: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host " 关闭独立的 PowerShell 窗口来停止服务。" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan
pause
