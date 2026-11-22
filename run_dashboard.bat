@echo off
title Panel de Control - Casa Segura
echo ====================================================
echo   Iniciando Panel de Control - Casa Segura
echo ====================================================

echo [1/2] Limpiando procesos antiguos en el puerto 8501...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [2/2] Iniciando aplicacion Streamlit...
python -m streamlit run app.py
pause
