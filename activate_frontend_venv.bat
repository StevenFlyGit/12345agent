@echo off
REM ============================================================
REM  12345agent frontend dev server launcher
REM  Double click this file to open PowerShell and run npm dev.
REM  Requires Node.js and frontend dependencies to be installed.
REM ============================================================
set "PROJECT_DIR=%~dp0"
set "FRONTEND_DIR=%PROJECT_DIR%frontend\"
start "" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "Set-Location '%FRONTEND_DIR%'; npm run dev"
