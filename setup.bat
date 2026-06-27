@echo off
echo ============================================================
echo  Chatbot Derechos del Consumidor Peruano - Setup
echo ============================================================
echo.

REM Verificar que conda este instalado
where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Conda no encontrado. Instalar Miniconda desde:
    echo https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)

REM Si el entorno ya existe, preguntar si recrear
conda env list | findstr "chatbot-consumidor" >nul 2>&1
if %errorlevel% equ 0 (
    echo El entorno chatbot-consumidor ya existe.
    set /p RECREAR="Desea recrearlo? [s/N]: "
    if /i "%RECREAR%"=="s" (
        echo Eliminando entorno anterior...
        conda env remove -n chatbot-consumidor -y
    ) else (
        echo Usando entorno existente.
        goto :activar
    )
)

echo [1/4] Creando entorno conda con Python 3.11.9...
conda env create -f environment.yml
if %errorlevel% neq 0 (
    echo ERROR: Fallo al crear el entorno conda.
    pause
    exit /b 1
)

:activar
echo [2/4] Activando entorno...
call conda activate chatbot-consumidor

echo [3/4] Verificando PyTorch con CUDA...
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA disponible:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No detectada')"

echo [4/4] Verificando Ollama...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo AVISO: Ollama no encontrado. Instalar desde https://ollama.com
    echo Luego ejecutar: ollama pull mistral:7b-instruct
) else (
    echo Ollama encontrado.
    echo Para descargar el modelo recomendado ejecutar:
    echo   ollama pull mistral:7b-instruct
)

echo.
echo ============================================================
echo  Setup completado. Para usar el proyecto:
echo    conda activate chatbot-consumidor
echo    jupyter notebook
echo.
echo  Para indexar los datos (ejecutar solo una vez):
echo    python src/ingest.py
echo.
echo  Para la interfaz web:
echo    streamlit run src/app.py
echo ============================================================
pause
