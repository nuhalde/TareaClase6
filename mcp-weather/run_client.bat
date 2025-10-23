@echo off
SETLOCAL
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)
python -m client
ENDLOCAL
