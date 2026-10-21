@echo off
REM ============================================================
REM  Buoc 05 - Tai du lieu: thoi tiet (Open-Meteo), luu luong va toc do (NYC Open Data)
REM  Double-click de chay. Neu bi ngat, chay lai: phan da tai xong se duoc bo qua.
REM ============================================================
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

set PY=
py -3 --version >nul 2>nul && set PY=py -3
if not defined PY python --version >nul 2>nul && set PY=python
if not defined PY (
    echo [LOI] Chua cai Python. Tai Python 3.12 tai https://www.python.org/downloads/
    echo       Khi cai nho tick "Add python.exe to PATH", sau do chay lai file nay.
    pause
    exit /b 1
)
echo Dung Python:
%PY% --version

if not exist .venv\Scripts\python.exe (
    echo Tao moi truong ao .venv ...
    %PY% -m venv .venv || goto :error
)
echo Cai thu vien can thiet ...
.venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements-collect.txt || goto :error

echo.
echo Bat dau tai du lieu. Phan toc do (~12 trieu dong) mat nhieu thoi gian nhat.
echo Log duoc luu tai data\raw\collect_log.txt
echo.
.venv\Scripts\python -m data_integration.collect.run_all || goto :error

echo.
echo ===== HOAN TAT. Du lieu nam trong data\raw =====
pause
exit /b 0

:error
echo.
echo ===== CO LOI. Xem chi tiet trong data\raw\collect_log.txt =====
pause
exit /b 1
