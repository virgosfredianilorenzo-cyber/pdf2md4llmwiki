@echo off
:: ============================================================
:: start.bat - PDF2LLMWiki · Windows
:: Double-clic ou : start.bat depuis cmd
:: ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo   ╔══════════════════════════════╗
echo   ║       PDF2LLMWiki            ║
echo   ║       Windows                ║
echo   ╚══════════════════════════════╝
echo.

:: ── 1. Python ───────────────────────────────────────────────
echo [1/7] Verification Python...
set PYTHON=
for %%C in (python3.12 python3.11 python3.10 python3 python) do (
    if "!PYTHON!"=="" (
        where %%C >nul 2>&1 && (
            for /f "tokens=2 delims= " %%V in ('%%C --version 2^>^&1') do (
                for /f "tokens=1,2 delims=." %%A in ("%%V") do (
                    if %%A GEQ 3 if %%B GEQ 10 set PYTHON=%%C
                )
            )
        )
    )
)

if "!PYTHON!"=="" (
    echo [ERREUR] Python 3.10+ non trouve.
    echo Telecharge-le sur https://python.org/downloads
    echo Coche bien "Add Python to PATH" lors de l'installation.
    pause
    exit /b 1
)
echo   OK  !PYTHON! trouve
for /f "tokens=*" %%V in ('!PYTHON! --version 2^>^&1') do echo        %%V

:: ── 2. Venv ─────────────────────────────────────────────────
echo.
echo [2/7] Environnement virtuel...
if not exist ".venv\" (
    !PYTHON! -m venv .venv
    echo   OK  venv cree dans .venv\
) else (
    echo   OK  venv existant
)
call .venv\Scripts\activate.bat

:: ── 3. Dépendances Python ───────────────────────────────────
echo.
echo [3/7] Dependances Python...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo   Installation en cours...
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo   OK  dependances installees
) else (
    echo   OK  dependances deja presentes
)

:: ── 4. Ollama ───────────────────────────────────────────────
echo.
echo [4/7] Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
    echo   Ollama non trouve.
    echo   Telechargement automatique de l'installeur Windows...
    echo.
    :: Télécharge l'installeur Ollama via PowerShell (disponible sur toutes les versions Windows 10+)
    powershell -NoProfile -Command ^
        "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%TEMP%\OllamaSetup.exe'"
    if errorlevel 1 (
        echo   [ERREUR] Telechargement echoue.
        echo   Installe manuellement : https://ollama.com/download/windows
        pause
        exit /b 1
    )
    echo   Lancement de l'installeur Ollama...
    "%TEMP%\OllamaSetup.exe" /S
    :: Attend que l'install termine
    timeout /t 10 /nobreak >nul
    :: Recharge le PATH
    for /f "tokens=*" %%P in ('powershell -NoProfile -Command ^
        "[System.Environment]::GetEnvironmentVariable(\"PATH\",\"Machine\")"') do (
        set "PATH=%%P;%PATH%"
    )
    where ollama >nul 2>&1 || (
        echo   [ERREUR] Ollama toujours introuvable apres installation.
        echo   Redemarre le terminal et relance start.bat
        pause
        exit /b 1
    )
    echo   OK  Ollama installe
) else (
    for /f "tokens=*" %%V in ('ollama --version 2^>^&1') do echo   OK  %%V
)

:: ── 5. Daemon Ollama ────────────────────────────────────────
echo.
echo [5/7] Daemon Ollama...
curl -sf http://localhost:11434 >nul 2>&1
if errorlevel 1 (
    echo   Demarrage du daemon Ollama en arriere-plan...
    start /b "" ollama serve > "%TEMP%\ollama_pdf2llm.log" 2>&1
    :: Attend jusqu'à 20s que le daemon réponde
    set /a TRIES=0
    :WAIT_OLLAMA
    timeout /t 1 /nobreak >nul
    curl -sf http://localhost:11434 >nul 2>&1 && goto OLLAMA_OK
    set /a TRIES+=1
    if !TRIES! LSS 20 goto WAIT_OLLAMA
    echo   [ERREUR] Ollama ne repond pas apres 20s.
    echo   Log : %TEMP%\ollama_pdf2llm.log
    pause
    exit /b 1
    :OLLAMA_OK
    echo   OK  daemon actif
) else (
    echo   OK  daemon deja actif
)

:: ── 6. Modèle LLM ───────────────────────────────────────────
echo.
echo [6/7] Modele LLM...
for /f "tokens=*" %%M in ('python -c "import yaml; print(yaml.safe_load(open(\"config.yaml\"))[\"model\"])" 2^>nul') do set MODEL=%%M
if "!MODEL!"=="" set MODEL=qwen2.5:7b

for /f "tokens=1 delims=:" %%B in ("!MODEL!") do set MODEL_BASE=%%B
ollama list 2>nul | findstr /i "^!MODEL_BASE!" >nul 2>&1
if errorlevel 1 (
    echo   Modele !MODEL! absent.
    echo   Telechargement en cours (4-6 Go selon le modele)...
    echo   Patiente, cela peut prendre plusieurs minutes selon ta connexion.
    ollama pull !MODEL!
    if errorlevel 1 (
        echo   [ERREUR] Telechargement du modele echoue.
        echo   Verifie ta connexion internet et relance start.bat
        pause
        exit /b 1
    )
    echo   OK  modele !MODEL! pret
) else (
    echo   OK  modele !MODEL! present
)

:: ── 7. Dossier output ───────────────────────────────────────
echo.
echo [7/7] Preparation...
if not exist "output\" mkdir output
echo   OK  dossier output\ pret

:: Port
for /f "tokens=*" %%P in ('python -c "import yaml; print(yaml.safe_load(open(\"config.yaml\")).get(\"port\",8000))" 2^>nul') do set PORT=%%P
if "!PORT!"=="" set PORT=8000

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║  Tout est pret !                         ║
echo   ║  Ouvre : http://localhost:!PORT!             ║
echo   ║  Ferme cette fenetre pour arreter        ║
echo   ╚══════════════════════════════════════════╝
echo.

:: Ouvre le navigateur après 2s
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:!PORT!"

:: Lance le serveur
python app.py

pause
