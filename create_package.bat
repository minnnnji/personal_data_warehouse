@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0create_package.ps1"
