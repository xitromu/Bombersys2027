@echo off
rem Сборка BOMBERSYS.exe: один файл, в котором сервер, страница и картинки.
rem Результат: backend\dist\BOMBERSYS.exe
chcp 65001 >nul
cd /d "%~dp0.."
uv run --group build pyinstaller --noconfirm --onefile --name BOMBERSYS ^
  --icon ..\legacy\UMIRAYUT\res\B.ico ^
  --add-data "..\frontend;frontend" ^
  --collect-submodules uvicorn --collect-submodules websockets ^
  packaging\bombersys_exe.py
