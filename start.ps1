# Whitfield WMS - Local Startup Script
# Double-click or run: powershell -ExecutionPolicy Bypass -File start.ps1

$projectRoot = "c:\Users\pawpa\OneDrive\Desktop\Whitfield-WMS-Updated-2026-08-17"
Write-Host "Starting Whitfield WMS..." -ForegroundColor Cyan

# 1. Ensure local mongod is running on port 27018
$mongodRunning = netstat -ano | Select-String ":27018 "
if (-not $mongodRunning) {
    Write-Host "Starting MongoDB replica set..." -ForegroundColor Yellow
    $dataDir = "C:\Users\$env:USERNAME\mongo-rs0\data"
    $logFile  = "C:\Users\$env:USERNAME\mongo-rs0\log\mongod.log"
    New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
    Start-Process "C:\Program Files\MongoDB\Server\8.3\bin\mongod.exe" `
        -ArgumentList "--replSet wms-rs --dbpath `"$dataDir`" --logpath `"$logFile`" --port 27018 --bind_ip 127.0.0.1" `
        -WindowStyle Hidden
    Start-Sleep -Seconds 5
    Write-Host "MongoDB started on port 27018" -ForegroundColor Green
} else {
    Write-Host "MongoDB already running on port 27018" -ForegroundColor Green
}

# 2. Start backend
Write-Host "Starting FastAPI backend on port 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit -Command Set-Location '$projectRoot\backend'; $env:MONGODB_URI='mongodb://127.0.0.1:27018/?replicaSet=wms-rs'; uvicorn main:app --reload --host 0.0.0.0 --port 8000"
Start-Sleep -Seconds 4

# 3. Start frontend
Write-Host "Starting Next.js frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit -Command Set-Location '$projectRoot\frontend'; pnpm dev"

Start-Sleep -Seconds 3
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Whitfield WMS is running!" -ForegroundColor Green
Write-Host "  Frontend:  http://localhost:3001" -ForegroundColor Cyan
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Health:    http://localhost:8000/api/v1/health" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
