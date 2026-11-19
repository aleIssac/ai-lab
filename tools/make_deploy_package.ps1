#Requires -Version 5.1
<#
.SYNOPSIS
    Build an offline deployment package for another Windows machine.

.DESCRIPTION
    Produces a folder that can be copied to a USB drive (exFAT / NTFS, files are >4GB):

        <OutDir>\
          images\ai-lab-1.0.tar          docker image, ~6 GB
          images\ollama-latest.tar       docker image, ~9.4 GB
          project\                       the whole project (self contained)
          project\ollama-models\models\  ollama model store, ~1 GB
          install.bat                    run this on the target machine
          README.txt

.PARAMETER OutDir
    Where to write the package. Default D:\ai-lab-deploy

.PARAMETER OllamaModelsStore
    Host path of the ollama model store (the folder that contains blobs/ and manifests/).
    Default D:\Environment\Server\ollama\models\models

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\make_deploy_package.ps1 -OutDir E:\ai-lab-deploy
#>
param(
    [string]$OutDir = "D:\ai-lab-deploy",
    [string]$OllamaModelsStore = "D:\Environment\Server\ollama\models\models"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Write-Host "project root : $ProjectRoot"
Write-Host "output dir   : $OutDir"
Write-Host ""

# ---------- checks ----------
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    throw "docker not found in PATH. Start Docker Desktop and re-run."
}
& docker image inspect ai-lab:1.0 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw "image ai-lab:1.0 not found. Run start.bat once first." }
& docker image inspect ollama/ollama:latest 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw "image ollama/ollama:latest not found." }
if (-not (Test-Path $OllamaModelsStore)) { throw "ollama model store not found: $OllamaModelsStore" }

New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "images") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "project\ollama-models") | Out-Null

# ---------- 1. docker images ----------
# (docker save writes uncompressed layers, expect ~15.5 GB total)
Write-Host "[1/4] saving docker images (this takes several minutes)..."
& docker save -o (Join-Path $OutDir "images\ai-lab-1.0.tar") ai-lab:1.0
if ($LASTEXITCODE -ne 0) { throw "docker save ai-lab:1.0 failed" }
& docker save -o (Join-Path $OutDir "images\ollama-latest.tar") ollama/ollama:latest
if ($LASTEXITCODE -ne 0) { throw "docker save ollama failed" }

# ---------- 2. ollama models ----------
Write-Host "[2/4] copying ollama model store..."
$destModels = Join-Path $OutDir "project\ollama-models\models"
robocopy $OllamaModelsStore $destModels /E /R:2 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy ollama models failed ($LASTEXITCODE)" }

# ollama 的 manifests-v2 里是 WSL 符号链接，Windows 压缩工具读不了（报 1920 系统无法访问此文件）。
# 用容器把它们换成真实文件，内容完全一样，只是不再是链接。
Write-Host "      dereferencing WSL symlinks in manifests-v2..."
$pkgModels = Join-Path $OutDir "project\ollama-models"
$deref = 'cd /dest/models/manifests-v2 2>/dev/null && find . -type l | while read f; do cp "$(readlink -f "$f")" "$f.real" && rm -f "$f" && mv "$f.real" "$f"; done; echo deref-done'
& docker run --rm -v "${pkgModels}:/dest" --entrypoint bash ai-lab:1.0 -c $deref
if ($LASTEXITCODE -ne 0) { throw "dereferencing manifests-v2 failed" }

# ---------- 3. project ----------
# .workbuddy  = local memory, not needed
# .env        = machine specific (models path), target uses the default ./ollama-models
# ollama-models = already copied above
# config\index = Continue code index, rebuilt on demand (44 MB)
Write-Host "[3/4] copying project..."
$excludeDirs = @(
    (Join-Path $ProjectRoot ".workbuddy"),
    (Join-Path $ProjectRoot ".git"),
    (Join-Path $ProjectRoot "ollama-models"),
    (Join-Path $ProjectRoot "config\index")
)

# 如果输出目录在项目里面（比如 项目\部署包），必须排除它，否则会自己拷自己
$outFull = [System.IO.Path]::GetFullPath($OutDir)
$rootFull = [System.IO.Path]::GetFullPath($ProjectRoot)
if ($outFull.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Host "      (output dir is inside the project, excluding it)"
    $excludeDirs += $outFull
}

$robocopyArgs = @($ProjectRoot, (Join-Path $OutDir "project"), "/E", "/R:2", "/W:2", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/XD") + $excludeDirs + @("/XF", ".env")
robocopy @robocopyArgs | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy project failed ($LASTEXITCODE)" }

# ---------- 4. installer + readme ----------
Write-Host "[4/4] writing installer..."

$installBat = @'
@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo   AI Lab - offline installer
echo ================================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] docker not found in PATH.
    echo         Install Docker Desktop first, then run this again.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker engine is not running. Start Docker Desktop first.
    pause
    exit /b 1
)

echo [1/4] loading images, this takes a few minutes...
docker load -i images\ai-lab-1.0.tar
if errorlevel 1 goto :err
docker load -i images\ollama-latest.tar
if errorlevel 1 goto :err

echo [2/4] checking files...
if not exist "project\ollama-models\models\manifests-v2" (
    echo [ERROR] model store missing: project\ollama-models\models\manifests-v2
    pause
    exit /b 1
)

echo [3/4] checking models...
cd project
docker compose up -d ollama
timeout /t 8 /nobreak >nul
docker exec ollama ollama list | findstr /c:"qwen-coder-fim" >nul
if errorlevel 1 (
    echo       model not visible, recreating from Modelfile...
    docker cp docker\Modelfile.fim ollama:/tmp/Modelfile.fim
    docker exec ollama ollama create qwen-coder-fim -f /tmp/Modelfile.fim
)
docker exec ollama ollama list

echo [4/4] starting the stack...
call start.bat
exit /b 0

:err
echo.
echo [ERROR] failed. Check free disk space (need ~15 GB free on C:).
pause
exit /b 1
'@
Set-Content -Path (Join-Path $OutDir "install.bat") -Value $installBat -Encoding ASCII

# 中文操作手册（docs 里是母版，直接拷到包根目录）
$manual = Join-Path $ProjectRoot "docs\部署操作手册.txt"
if (Test-Path $manual) {
    Copy-Item $manual (Join-Path $OutDir "部署操作手册.txt") -Force
    Write-Host "      copied 部署操作手册.txt"
}

$readme = @'
AI Lab - offline deployment package
===================================

1. Target machine requirements
   - Windows 10/11 64-bit
   - Docker Desktop (WSL2 backend) installed and running
   - WSL2 needs at least 8 GB free disk for images + models
   - No Python, no internet required

2. Install
   Double click install.bat
   It loads the two docker images, checks the model store, then calls project\start.bat

3. After it starts, open http://localhost:3000
   code-server : http://localhost:8080   password: see CODE_SERVER_PASSWORD in .env
   MLflow      : http://localhost:5001
   Predict     : http://localhost:8501
   RAG         : http://localhost:8502
   API docs    : http://localhost:8000/docs

4. Daily restart
   Double click project\start.bat

5. Check Tab completion
   Open test.py in code-server, type   def avg(   and wait one second.
   Grey ghost text should appear. Press Tab to accept.

6. Troubleshooting
   - "docker not found"        -> add Docker Desktop to PATH, or run install.bat as admin once
   - portal 502 / blank page   -> docker exec -d ai-lab bash -c "cd /home/coder/project && /opt/venv/bin/python tools/serve_portal.py 3000 > /tmp/portal.log 2>&1"
   - no models in ollama       -> docker exec ollama ollama list
   - /tmp/*.log inside container holds each service log
'@
Set-Content -Path (Join-Path $OutDir "README.txt") -Value $readme -Encoding ASCII

# ---------- summary ----------
function Get-DirSize($p) {
    if (-not (Test-Path $p)) { return 0 }
    (Get-ChildItem $p -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
}
$total = (Get-ChildItem $OutDir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Host ""
Write-Host "done."
Write-Host ("  images : {0:N1} GB" -f ((Get-DirSize (Join-Path $OutDir 'images')) / 1GB))
Write-Host ("  models : {0:N1} GB" -f ((Get-DirSize (Join-Path $OutDir 'project\ollama-models')) / 1GB))
Write-Host ("  project: {0:N1} GB" -f ((Get-DirSize (Join-Path $OutDir 'project')) / 1GB))
Write-Host ("  total  : {0:N1} GB" -f ($total / 1GB))
Write-Host ""
Write-Host "copy the whole folder to the target machine (use exFAT or NTFS, files are larger than 4 GB),"
Write-Host "then run install.bat there."
