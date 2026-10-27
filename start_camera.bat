@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Chua cai dat. Hay chay setup.ps1 truoc.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" run_music_game.py

