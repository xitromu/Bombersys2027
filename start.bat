@echo off
rem Запуск игры двойным щелчком: поднимает сервер и открывает браузер.
chcp 65001 >nul
cd /d "%~dp0backend"
uv run bombersys
pause
