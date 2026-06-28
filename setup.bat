@echo off
echo ============================================================
echo  Chatbot Derechos del Consumidor Peruano - Setup
echo ============================================================
echo.

REM Verificar que Python este disponible
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no encontrado en el PATH.
    echo Instalar Python 3.11 desde https://www.python.org/downloads/
    echo Marcar "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

REM Crear entorno virtual si no existe
if exist venv (
    echo El entorno virtual ya existe en venv\
    set /p RECREAR="Desea recrearlo? [s/N]: "
    if /i "%RECREAR%"=="s" (
        echo Eliminando entorno anterior...
        rmdir /s /q venv
    ) else (
        echo Usando entorno existente.
        goto :instalar_kernel
    )
)

echo [1/4] Creando entorno virtual...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: No se pudo crear el entorno virtual.
    pause
    exit /b 1
)

echo [2/4] Instalando PyTorch con CUDA 12.1 (RTX 4080)...
call venv\Scripts\activate.bat
pip install --upgrade pip --quiet
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
if %errorlevel% neq 0 (
    echo ERROR: Fallo la instalacion de PyTorch.
    pause
    exit /b 1
)

echo [3/4] Instalando dependencias del proyecto...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

:instalar_kernel
echo [4/4] Registrando kernel de Jupyter...
call venv\Scripts\activate.bat
python -m ipykernel install --user --name chatbot-consumidor --display-name "Python (chatbot-consumidor)"

echo.
echo Verificando instalacion...
python -c "import torch; print('  PyTorch :', torch.__version__); print('  CUDA    :', torch.cuda.is_available()); print('  GPU     :', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No detectada')"

echo.
echo Verificando Ollama...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo   AVISO: Ollama no encontrado. Instalar desde https://ollama.com
    echo   Luego ejecutar: ollama pull mistral:7b-instruct
) else (
    echo   Ollama encontrado OK.
)

echo.
echo ============================================================
echo  Setup completado. Comandos utiles:
echo.
echo  Activar entorno (CMD o PowerShell):
echo    venv\Scripts\activate
echo.
echo  Indexar datos (solo la primera vez):
echo    python src/ingest.py
echo.
echo  Iniciar chatbot:
echo    streamlit run src/app.py
echo.
echo  Iniciar Jupyter:
echo    jupyter notebook
echo    (usar kernel "Python (chatbot-consumidor)")
echo ============================================================
pause
