# Chatbot de Derechos del Consumidor Peruano

Chatbot académico (curso de PLN, décimo ciclo) que simplifica textos legales sobre derechos del consumidor en Perú para que ciudadanos comunes los entiendan.

Arquitectura RAG: recupera fragmentos del corpus legal peruano y los procesa con un LLM local para generar respuestas en lenguaje simple.

**Resultado final de evaluación:** 24/24 (2.0/2.0) — configuración `qwen2.5:14b` + `bge-m3` + pre-filtrado por categoría.

---

## Requisitos de hardware

- GPU NVIDIA con al menos 16 GB VRAM (probado en RTX 4080)
- 16 GB RAM mínimo
- ~20 GB de espacio en disco (modelo qwen2.5:14b ~9 GB + dependencias)

> Sin GPU NVIDIA, la app no puede correr el modelo LLM local. Ver sección [Alternativa sin GPU](#alternativa-sin-gpu).

---

## Instalación

### 1. Requisitos previos

Instalar manualmente antes de ejecutar `setup.bat`:

| Herramienta | Versión | Descarga |
|---|---|---|
| Python | 3.11.x | https://www.python.org/downloads/ — marcar "Add Python to PATH" |
| Ollama | última | https://ollama.com |
| Driver NVIDIA + CUDA 12.1 | — | https://developer.nvidia.com/cuda-12-1-0-download-archive |

### 2. Ejecutar setup automático

```bat
setup.bat
```

El script hace automáticamente:
1. Crea el entorno virtual `venv/`
2. Instala PyTorch 2.5.1 con CUDA 12.1
3. Instala todas las dependencias (`requirements.txt`)
4. Registra el kernel de Jupyter
5. Descarga el modelo `qwen2.5:14b` vía Ollama (~9 GB)

### 3. Configurar API key de Google (para evaluación)

```bat
copy .env.example .env
```

Editar `.env` y poner la clave de Google AI Studio (gratuita en https://aistudio.google.com):

```
GOOGLE_API_KEY=tu_clave_aqui
```

> La API key solo se usa para los scripts de evaluación (`evaluar_llm_judge.py`). La app del chatbot no la necesita.

### 4. Indexar el corpus (solo la primera vez)

Si `chroma_db_bgem3_exp5/` ya existe en el repositorio, omitir este paso.

```bat
venv\Scripts\activate
python src\ingest_embeddings.py --embeddings bge-m3 --suffix _exp5
```

La indexación tarda ~5-10 minutos la primera vez (descarga el modelo bge-m3 y construye el índice vectorial con 1356 fragmentos del corpus legal).

---

## Uso

### Iniciar el chatbot

```bat
venv\Scripts\activate
streamlit run src\app.py
```

Se abre automáticamente en `http://localhost:8501`.

La interfaz incluye ejemplos de preguntas en el panel lateral y muestra las fuentes legales consultadas por cada respuesta.

### Iniciar Jupyter (notebooks)

```bat
venv\Scripts\activate
jupyter notebook
```

Seleccionar el kernel **"Python (chatbot-consumidor)"**.

---

## Estructura del proyecto

```
├── src/
│   ├── app.py                    ← Interfaz Streamlit
│   ├── rag_chain.py              ← Cadena RAG (config. ganadora: qwen2.5:14b + bge-m3)
│   ├── ingest_embeddings.py      ← Indexa el corpus en ChromaDB
│   ├── evaluacion_embeddings.py  ← Evaluación multi-embedding con pre-filtrado
│   ├── evaluar_llm_judge.py      ← Juez automático con Gemini Flash
│   └── generar_reporte.py        ← Genera reporte HTML comparativo
├── final_json/                   ← Corpus legal peruano (30 documentos)
│   ├── informes/
│   ├── leyes/
│   └── normas reglamentarias/
├── chroma_db_bgem3_exp5/         ← Índice vectorial de producción (bge-m3, 1356 docs)
├── notebooks/
│   ├── 01_exploracion_datos.ipynb
│   ├── 02_indexacion_vectorstore.ipynb
│   └── 03_chatbot_rag.ipynb
├── diagramas/                    ← Diagramas de arquitectura (draw.io + PNG)
├── preguntas_evaluacion.json     ← 12 preguntas de evaluación con respuestas de referencia
├── EVALUACION.md                 ← Registro completo Exp1→Exp7 con scores por pregunta
├── environment.yml               ← Entorno conda (alternativa a venv)
├── requirements.txt              ← Dependencias pip
└── setup.bat                     ← Instalación automática (Windows)
```

---

## Stack tecnológico

| Componente | Herramienta |
|---|---|
| LLM producción | `qwen2.5:14b` vía Ollama |
| Embeddings | `BAAI/bge-m3` (1024 dims) |
| Vector store | ChromaDB — `chroma_db_bgem3_exp5/` (1356 docs) |
| Pre-filtrado | Por categoría de consumo antes del retrieval |
| k documentos | 3 |
| Interfaz | Streamlit |
| Orquestación | LangChain |
| LLM juez (eval) | `gemini-2.5-flash` vía Google AI Studio |

---

## Corpus legal

30 documentos del sistema legal peruano de protección al consumidor:

- **Leyes**: Código de Protección y Defensa del Consumidor (Ley N°29571) y 4 leyes complementarias
- **Normas reglamentarias**: 10 resoluciones de INDECOPI, SBS, OSIPTEL, SUNASS, OSINERGMIN
- **Informes y cartillas**: 15 documentos de INDECOPI, SBS, OSIPTEL y entidades reguladoras

Categorías cubiertas: libro de reclamaciones, telecomunicaciones, INDECOPI, servicios inmobiliarios, servicios financieros, productos defectuosos, precios y educación.

---

## Pipeline de evaluación

```bat
REM Evaluar configuracion actual
venv\Scripts\activate
python src\evaluacion_embeddings.py --pares "qwen2.5:14b|bge-m3" --suffix _exp5 --prefiltrar --salida evaluacion_nuevo
python src\evaluar_llm_judge.py --entrada evaluacion_nuevo.json --salida scores_gemini_nuevo
python src\generar_reporte.py --entrada scores_gemini_nuevo.json --baseline scores_gemini_exp7.json --salida reporte_nuevo.html
```

Todos los scripts soportan reanudación: si se interrumpen, al relanzar continúan donde quedaron.

---

## Alternativa sin GPU

Para ejecutar en máquinas sin GPU NVIDIA:

1. Reemplazar el LLM en `src/rag_chain.py` con la API de Gemini Flash (gratuita, 1500 req/día)
2. Los embeddings `bge-m3` y ChromaDB corren en CPU (lento pero funcional)

Ver detalles en `EVALUACION.md` sección "Decisiones de diseño".

---

## Problemas conocidos

| Problema | Solución |
|---|---|
| Error SSL con aiohttp en Windows | `pip install "aiohttp<3.10"` (ya incluido en requirements.txt) |
| torch version incompatible | `pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121` |
| Caracteres extraños en consola Windows | Los scripts usan `[OK]`/`[FAIL]` — es comportamiento esperado |
| `chroma_db_bgem3_exp5/` no encontrado | Ejecutar `python src\ingest_embeddings.py --embeddings bge-m3 --suffix _exp5` |
