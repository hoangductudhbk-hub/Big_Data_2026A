@echo off
REM Buoc 08 - Schema alignment. Can chay buoc 07 truoc.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo [LOI] Chua co .venv. Hay chay tai_du_lieu.bat truoc.
    pause
    exit /b 1
)
echo Cai thu vien Phase 1 ...
.venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements-integration.txt || goto :error
.venv\Scripts\python -m data_integration.alignment.run || goto :error
echo.
echo ===== HOAN TAT. Bao cao: docs\bao-cao\08_alignment.md =====
pause
exit /b 0
:error
echo ===== CO LOI =====
pause
exit /b 1
