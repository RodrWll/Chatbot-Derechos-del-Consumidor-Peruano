@echo off
echo ============================================================
echo  Chatbot Derechos del Consumidor Peruano - Setup
echo ============================================================
echo.

REM Verificar que Python 3.11 este disponible
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no encontrado en el PATH.
    echo Instalar Python 3.11 desde https://www.python.org/downloads/
    echo Marcar "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

python --version 2>&1 | findstr /C:"3.11" >nul
if %errorlevel% neq 0 (
    echo AVISO: Se recomienda Python 3.11. La version detectada puede causar incompatibilidades.
    echo Continuar de todas formas? [S/N]
    set /p CONTINUAR=
    if /i not "%CONTINUAR%"=="S" exit /b 1
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

echo [1/5] Creando entorno virtual...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: No se pudo crear el entorno virtual.
    pause
    exit /b 1
)

echo [2/5] Instalando PyTorch con CUDA 12.1 (GPU NVIDIA requerida)...
call venv\Scripts\activate.bat
pip install --upgrade pip --quiet
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121 --quiet
if %errorlevel% neq 0 (
    echo ERROR: Fallo la instalacion de PyTorch.
    echo Verificar que tenga instalado el driver NVIDIA y CUDA 12.1.
    pause
    exit /b 1
)

echo [3/5] Instalando dependencias del proyecto...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ERROR: Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

:instalar_kernel
echo [4/5] Registrando kernel de Jupyter...
call venv\Scripts\activate.bat
python -m ipykernel install --user --name chatbot-consumidor --display-name "Python (chatbot-consumidor)"

echo [5/5] Verificando instalacion...
python -c "import torch; print('  PyTorch :', torch.__version__); print('  CUDA    :', torch.cuda.is_available()); print('  GPU     :', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No detectada')"

echo.
echo Verificando Ollama...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo   AVISO: Ollama no encontrado.
    echo   Instalar desde https://ollama.com y luego ejecutar:
    echo     ollama pull qwen2.5:14b
) else (
    echo   Ollama encontrado. Descargando modelo de produccion (qwen2.5:14b ~9 GB)...
    ollama pull qwen2.5:14b
)

echo.
echo ============================================================
echo  Setup completado. Proximos pasos:
echo.
echo  1. Activar entorno (CMD):
echo       venv\Scripts\activate
echo.
echo  2. Indexar el corpus (solo la primera vez si chroma_db_bgem3_exp5\ no existe):
echo       python src\ingest_embeddings.py --embeddings bge-m3 --suffix _exp5
echo.
echo  3. Iniciar el chatbot:
echo       streamlit run src\app.py
echo.
echo  4. Para notebooks:
echo       jupyter notebook
echo       (usar kernel "Python (chatbot-consumidor)")
echo ============================================================
pause
