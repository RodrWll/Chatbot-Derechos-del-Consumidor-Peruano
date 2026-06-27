# Chatbot de Simplificación de Derechos del Consumidor Peruano

## Qué es este proyecto

Chatbot académico (curso de PLN, décimo ciclo) que simplifica textos legales sobre derechos del consumidor en Perú para que ciudadanos comunes los entiendan. Usa arquitectura RAG: recupera fragmentos del corpus legal y los procesa con un LLM local para generar respuestas en lenguaje simple.

## Estado actual (actualizado 2026-06-27)

- ✅ Fase 1 completa: corpus indexado, RAG funcionando, Streamlit operativo
- ✅ Fase 2 parcial: comparativa mistral vs llama3.1 iniciada — **mistral:7b-instruct ganó**
- ⏳ **Tarea inmediata:** crear `src/evaluacion.py` — script de evaluación automática
- ⏳ Notebooks ejecutados parcialmente — continuar con 01, 02 y 03
- ⏳ Fase 4 (deploy) pendiente

## Hardware de desarrollo

Intel Core i9-14 · 64 GB RAM · NVIDIA RTX 4080 (16 GB VRAM)
→ Ollama usa CUDA automáticamente. Modelos 7B-9B corren completamente en GPU.

## Stack tecnológico

| Componente | Herramienta |
|------------|-------------|
| Lenguaje | Python 3.11.9 |
| Entorno | conda (`environment.yml`) — kernel Jupyter: "Python (chatbot-consumidor)" |
| Embeddings | `langchain_huggingface.HuggingFaceEmbeddings` — `paraphrase-multilingual-MiniLM-L12-v2` |
| Vector store | `langchain_chroma.Chroma` (local, persistente en `chroma_db/`) |
| LLM | `langchain_ollama.OllamaLLM` — modelo: `mistral:7b-instruct` (ganador de la evaluación) |
| UI | Streamlit (`src/app.py`) con `@st.cache_resource` |
| Orquestación | LangChain (cadena manual con closure en `rag_chain.py`) |

**IMPORTANTE — imports correctos** (versiones instaladas usan los paquetes nuevos):
```python
from langchain_huggingface import HuggingFaceEmbeddings   # NO langchain_community
from langchain_chroma import Chroma                        # NO langchain_community
from langchain_ollama import OllamaLLM                    # NO langchain_community
from langchain_core.documents import Document             # NO langchain.schema
from langchain_core.prompts import PromptTemplate         # NO langchain.prompts
```

## Estructura del proyecto

```
├── CLAUDE.md                ← este archivo
├── EVALUACION.md            ← registro de experimentos y resultados
├── environment.yml          ← entorno conda
├── setup.bat                ← instalación automática (Windows)
├── requirements.txt
├── .gitignore
├── final_json/              ← corpus legal (NO modificar)
│   ├── informes/            ← 13 archivos (guías INDECOPI)
│   ├── leyes/               ← 5 archivos (Código del Consumidor, etc.)
│   └── normas reglamentarias/ ← 10 archivos (decretos, resoluciones)
├── src/
│   ├── ingest.py            ← pipeline JSON → ChromaDB (ejecutar 1 vez)
│   ├── rag_chain.py         ← cadena RAG con prompt de simplificación
│   ├── app.py               ← interfaz Streamlit
│   └── evaluacion.py        ← PENDIENTE DE CREAR (ver spec abajo)
├── notebooks/
│   ├── 01_exploracion_datos.ipynb
│   ├── 02_indexacion_vectorstore.ipynb
│   └── 03_chatbot_rag.ipynb
├── diagramas/               ← 4 diagramas draw.io + PNG
└── chroma_db/               ← generado localmente, NO en git
```

## Cómo arrancar (PC con entorno ya instalado)

```bash
# Abrir Anaconda Prompt
conda activate chatbot-consumidor

# Iniciar la app
streamlit run src/app.py

# Iniciar Jupyter para notebooks
jupyter notebook
# Kernel a usar: "Python (chatbot-consumidor)"

# Si chroma_db/ no existe (PC nueva), regenerar:
python src/ingest.py
```

## Tarea inmediata: crear src/evaluacion.py

**Qué debe hacer este script:**

Enviar automáticamente las 4 preguntas estándar a cada modelo disponible en Ollama y guardar las respuestas en `evaluacion_resultados.json` y `evaluacion_resultados.csv`.

**Especificación:**

```python
# Modelos a evaluar
MODELOS = ["mistral:7b-instruct", "llama3.1:8b", "gemma2:9b"]

# Preguntas estándar
PREGUNTAS = [
    "¿Cuáles son mis derechos si un producto que compré está defectuoso?",
    "¿Cómo presento una queja ante INDECOPI?",
    "¿Qué cubre el SOAT en caso de accidente de tránsito?",
    "¿Tengo derecho a atención preferente si soy adulto mayor?",
]

# Para cada modelo × pregunta, guardar:
# - modelo: str
# - pregunta: str
# - respuesta: str
# - fuentes: list[str] (nombre_doc de source_documents)
# - tiempo_segundos: float
# - num_docs_recuperados: int
```

**Salida esperada:**
- `evaluacion_resultados.json` — array de objetos con los campos anteriores
- `evaluacion_resultados.csv` — misma data en formato tabular para comparar fácilmente

**Comportamiento:**
- Usar `construir_cadena(model=modelo, k=3)` de `src/rag_chain.py`
- Medir tiempo de respuesta con `time.time()`
- Mostrar progreso por consola (qué modelo y pregunta está procesando)
- Si un modelo no está descargado en Ollama, saltar con un warning y continuar
- Al terminar, imprimir tabla resumen en consola

**Ejecutar con:**
```bash
python src/evaluacion.py
```

## Resultados de evaluación hasta ahora

### Configuración óptima encontrada
- **k=3** (mejor balance ruido vs. contexto)
- **mistral:7b-instruct** (ganador vs. llama3.1:8b)

### Problema conocido: contaminación de contexto cruzado
El retriever siempre incluye "Guía sobre productos y servicios inmobiliarios" en preguntas sobre productos defectuosos porque tiene similitud semántica superficial. El LLM incluye entonces la Defensoría del Cliente Inmobiliario (DCI) como opción general — es incorrecto. Documentado en `EVALUACION.md`.

### Comparativa mistral vs llama3.1 (pregunta: producto defectuoso)
| Aspecto | mistral:7b-instruct | llama3.1:8b |
|---------|--------------------|-|
| Libro de Reclamaciones | ✅ | ❌ Omitido |
| Reclama Virtual INDECOPI | ✅ | ❌ Omitido |
| Plazo 15 días hábiles | ✅ | ❌ Inventa "un mes hábil" |
| Nombre INDECOPI correcto | ✅ | ⚠️ "Autoridad Nacional de Consumo" |

## Decisiones de diseño ya tomadas (no revertir sin razón)

- **No modificar los JSONs en disco** — transformación ocurre en memoria en `ingest.py`
- **No hacer fine-tuning** — RAG con buen prompt es suficiente
- **No usar API de OpenAI/Groq** — RTX 4080 permite modelos locales equivalentes
- **Chunking adicional no necesario** — `texto` ya tiene granularidad adecuada
- **LangGraph no prioritario** — solo si sobra tiempo tras la evaluación

## Preguntas de prueba estándar

```python
PREGUNTAS = [
    "¿Cuáles son mis derechos si un producto que compré está defectuoso?",
    "¿Cómo presento una queja ante INDECOPI?",
    "¿Qué cubre el SOAT en caso de accidente de tránsito?",
    "¿Tengo derecho a atención preferente si soy adulto mayor?",
]
```
