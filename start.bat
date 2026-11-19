@echo off
setlocal
cd /d "%~dp0"

rem ============================================================
rem  AI Lab launcher (Windows)
rem  Requires Docker Desktop only - no Python needed on the host.
rem  docker is auto-detected (hard-coded path first, then PATH).
rem ============================================================

set "DOCKER="
if exist "D:\Environment\Server\Docker\resources\bin\docker.exe" set "DOCKER=D:\Environment\Server\Docker\resources\bin\docker.exe"
if not defined DOCKER for /f "delims=" %%i in ('where docker 2^>nul') do if not defined DOCKER set "DOCKER=%%i"
if not defined DOCKER (
    echo [ERROR] docker not found.
    echo         Install Docker Desktop first, or edit the DOCKER path in this file.
    pause
    exit /b 1
)

echo ================================================
echo   AI Lab - full stack
echo ================================================
echo   docker : %DOCKER%
echo.

echo [1/5] Checking Docker engine...
"%DOCKER%" info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Start Docker Desktop first.
    pause
    exit /b 1
)

echo [2/5] Starting containers...
"%DOCKER%" compose up -d
if errorlevel 1 (
    echo [ERROR] docker compose up failed
    pause
    exit /b 1
)

echo [3/5] Waiting for container...
timeout /t 10 /nobreak >nul

echo [4/5] Starting services inside container...
rem ---- Tab autocomplete extension (local build, talks to Ollama FIM directly) ----
"%DOCKER%" exec ai-lab mkdir -p /home/coder/.local/share/code-server/extensions/ailab.ailab-autocomplete-0.1.0
"%DOCKER%" exec ai-lab cp /home/coder/project/docker/autocomplete-ext/package.json /home/coder/project/docker/autocomplete-ext/extension.js /home/coder/.local/share/code-server/extensions/ailab.ailab-autocomplete-0.1.0/

rem ---- backend services ----
rem ---- MLflow UI Chinese patch (idempotent: copy js + inject script tag) ----
"%DOCKER%" exec -u root ai-lab bash -c "B=$(ls -d /opt/venv/lib/python3*/site-packages/mlflow/server/js/build); cp /home/coder/project/docker/mlflow-zh/mlflow-zh.js $B/; grep -q mlflow-zh.js $B/index.html || sed -i 's|</body>|<script charset=utf-8 src=static-files/mlflow-zh.js></script></body>|' $B/index.html"
"%DOCKER%" exec -d ai-lab bash -c "cd /home/coder/project && /opt/venv/bin/python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5001 > /tmp/mlflow.log 2>&1"
"%DOCKER%" exec -d ai-lab bash -c "cd /home/coder/project && /opt/venv/bin/python -m streamlit run apps/streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true > /tmp/st.log 2>&1"
"%DOCKER%" exec -d ai-lab bash -c "cd /home/coder/project && /opt/venv/bin/python -m streamlit run apps/rag_app.py --server.address 0.0.0.0 --server.port 8502 --server.headless true > /tmp/rag.log 2>&1"
"%DOCKER%" exec -d ai-lab bash -c "cd /home/coder/project && /opt/venv/bin/python -m uvicorn src.serve:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1"

rem ---- Ollama proxy: adds raw:true to autocomplete requests ----
rem Ollama 0.40 ignores TEMPLATE in the Modelfile, so FIM markers need raw:true.
"%DOCKER%" exec -d ai-lab bash -c "cd /home/coder/project && /opt/venv/bin/python src/ollama_proxy.py > /tmp/proxy.log 2>&1"

echo [5/5] Starting portal on :3000...
rem Portal runs inside the container, so the host needs no Python at all.
"%DOCKER%" exec -d ai-lab bash -c "cd /home/coder/project && /opt/venv/bin/python tools/serve_portal.py 3000 > /tmp/portal.log 2>&1"

echo.
echo Waiting for services...
timeout /t 15 /nobreak >nul

echo.
echo ================================================
echo   Portal        http://localhost:3000
echo   code-server   http://localhost:8080   (pwd ai-lab-2026)
echo   MLflow        http://localhost:5001
echo   Predict       http://localhost:8501
echo   RAG           http://localhost:8502
echo   API docs      http://localhost:8000/docs
echo ================================================
echo.
echo Tip: type "def avg(" in any python file and wait 1s for Tab completion.
echo.
start http://localhost:3000
pause
