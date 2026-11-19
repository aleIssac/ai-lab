@echo off
cd /d "%~dp0"
set PY=D:\Environment\Server\venv\Scripts\python.exe

echo ================================================
echo   AI Lab - local demo (no Docker)
echo ================================================
echo.

if not exist "%PY%" (
    echo [ERROR] Python venv not found: %PY%
    pause
    exit /b 1
)

echo [1/4] portal   :3000
start "portal" cmd /c "%PY% tools\serve_portal.py 3000"

echo [2/4] api      :8000
start "api" cmd /c "%PY% -m uvicorn src.serve:app --host 0.0.0.0 --port 8000"

echo [3/4] mlflow   :5001
start "mlflow" cmd /c "%PY% -m mlflow ui --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5001"

echo [4/4] streamlit:8501
start "streamlit" cmd /c "%PY% -m streamlit run apps\streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true"

echo.
echo Waiting for services to boot...
timeout /t 8 /nobreak >nul

echo.
echo   Portal    http://localhost:3000
echo   API docs  http://localhost:8000/docs
echo   MLflow    http://localhost:5001
echo   Predict   http://localhost:8501
echo.
echo NOTE: code-server (8080) is provided by Docker - see start.bat
echo.
start http://localhost:3000
pause
