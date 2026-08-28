@echo off
REM ============================================================
REM  12345agent backend venv launcher
REM  Double click this file to open PowerShell in backend\venv.
REM  After activation, you can run:
REM      python -m uvicorn app.main:app --reload
REM ============================================================
set "PROJECT_DIR=%~dp0"
set "BACKEND_DIR=%PROJECT_DIR%backend\"
start "" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "& '%BACKEND_DIR%venv\Scripts\Activate.ps1'; Set-Location '%BACKEND_DIR%'; python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
