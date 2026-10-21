@echo off
REM Buoc 18-21 - Chay Phase 3 tren Windows: PostgreSQL bang Docker Desktop, API bang .venv cua project.
REM Can: Docker Desktop dang chay; da co .venv (tai_du_lieu.bat) va da chay Phase 1-2.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo [LOI] Chua co .venv. Hay chay tai_du_lieu.bat truoc.
    pause
    exit /b 1
)
set PY=%~dp0.venv\Scripts\python.exe
"%PY%" -c "import fastapi, sqlalchemy, psycopg, alembic" 2>/dev/null || (
    echo == Cai thu vien backend lan dau
    "%PY%" -m pip install -r backend\requirements.txt || goto :err
)
echo == 0. Khoi dong PostgreSQL bang Docker
docker compose up -d db || goto :err
timeout /t 6 >nul
set DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/traffic_bigdata
cd backend
echo == 1. Tao / cap nhat bang (Alembic)
"%PY%" -m alembic upgrade head || goto :err
echo == 2. Nap ket qua Phase 1-2 vao PostgreSQL
"%PY%" -m app.etl.load_processed || goto :err
echo == 3. Dashboard: http://localhost:8000   API: http://localhost:8000/docs   (dung: Ctrl+C)
start "" http://localhost:8000
"%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
goto :eof
:err
echo.
echo [LOI] Xem thong bao phia tren. Huong dan: docs\huong-dan\21_end_to_end.md
pause
