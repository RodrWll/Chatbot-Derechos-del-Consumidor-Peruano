# Chatbot de Simplificación de Derechos del Consumidor Peruano

## Qué es este proyecto

Chatbot académico (curso de PLN, décimo ciclo) que simplifica textos legales sobre derechos del consumidor en Perú para que ciudadanos comunes los entiendan. Usa arquitectura RAG: recupera fragmentos del corpus legal y los procesa con un LLM local para generar respuestas en lenguaje simple.

## Estado actual (actualizado 2026-06-28)

- ✅ Fase 1 completa: corpus indexado, RAG funcionando, Streamlit operativo
- ✅ Fase 2 completa: evaluación de 5 modelos × 10 preguntas — **qwen2.5:14b ganó (15/20)**
- ✅ Fase 3 completa: `src/evaluacion.py` y `src/evaluar_llm_judge.py` creados
- ✅ Corpus ampliado: guía INDECOPI agregada (`final_json/informes/Guía de procedimientos INDECOPI - Reclamos y Denuncias.json`)
- ⏳ **Tarea inmediata A:** re-indexar ChromaDB con el nuevo corpus → `python src/ingest.py`
- ⏳ **Tarea inmediata B:** correr evaluación v2 → `python src/evaluacion.py --modelos mistral:7b-instruct llama3.1:8b gemma2:9b mistral-nemo:12b qwen2.5:14b --salida evaluacion_resultados_v2`
- ⏳ **Tarea inmediata C:** evaluar ambas versiones con Gemini juez → ver sección "Pipeline de evaluación automática"
- ⏳ Notebooks 01, 02, 03 ejecutados parcialmente — continuar
- ⏳ Fase 4 (deploy) pendiente

## Hardware de desarrollo

Intel Core i9-14 · 64 GB RAM · NVIDIA RTX 4080 (16 GB VRAM)
→ Ollama usa CUDA automáticamente. Modelos 7B-14B corren completamente en GPU.

## Modelos Ollama instalados

| Modelo | Parámetros | Puntaje evaluación | Estado |
|--------|-----------|-------------------|--------|
| `qwen2.5:14b` | 14B | **15/20 🥇** | ✅ instalado |
| `mistral:7b-instruct` | 7B | 12/20 🥈 | ✅ instalado |
| `gemma2:9b` | 9B | 12/20 🥈 | ✅ instalado |
| `llama3.1:8b` | 8B | 11/20 | ✅ instalado |
| `mistral-nemo:12b` | 12B | 9/20 ⚠️ bug chars japoneses | ✅ instalado |

## Stack tecnológico

| Componente | Herramienta |
|------------|-------------|
| Lenguaje | Python 3.11.9 |
| Entorno | conda (`environment.yml`) — kernel Jupyter: "Python (chatbot-consumidor)" |
| Embeddings | `langchain_huggingface.HuggingFaceEmbeddings` — `paraphrase-multilingual-MiniLM-L12-v2` |
| Vector store | `langchain_chroma.Chroma` (local, persistente en `chroma_db/`) |
| LLM producción | `langchain_ollama.OllamaLLM` — modelo: `qwen2.5:14b` (ganador de la evaluación) |
| LLM juez evaluación | `gemini-2.0-flash` vía Google AI Studio API (gratuito, 1500 req/día) |
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
├── CLAUDE.md                     ← este archivo
├── EVALUACION.md                 ← registro completo de experimentos y resultados
├── environment.yml               ← entorno conda (incluye google-generativeai>=0.8)
├── .env                          ← API keys locales — NO en git (en .gitignore)
├── .env.example                  ← plantilla de variables de entorno
├── setup.bat
├── requirements.txt
├── .gitignore
├── preguntas_evaluacion.json     ← 10 preguntas con respuestas de referencia validadas
├── evaluacion_resultados.json    ← baseline: 5 modelos × 10 preguntas, corpus original
├── evaluacion_resultados_v2.json ← (a generar) corpus ampliado con guía INDECOPI
├── final_json/                   ← corpus legal (NO modificar JSONs existentes)
│   ├── informes/                 ← 14 archivos (13 originales + guía INDECOPI)
│   ├── leyes/                    ← 5 archivos
│   └── normas reglamentarias/    ← 10 archivos
├── src/
│   ├── ingest.py                 ← pipeline JSON → ChromaDB (re-ejecutar al agregar docs)
│   ├── rag_chain.py              ← cadena RAG con prompt de simplificación
│   ├── app.py                    ← interfaz Streamlit
│   ├── evaluacion.py             ← evaluación automática multi-modelo (lee preguntas_evaluacion.json)
│   └── evaluar_llm_judge.py      ← juez automático con Gemini (LLM-as-a-judge)
├── notebooks/
│   ├── 01_exploracion_datos.ipynb
│   ├── 02_indexacion_vectorstore.ipynb
│   └── 03_chatbot_rag.ipynb
├── diagramas/                    ← 4 diagramas draw.io + PNG
└── chroma_db/                    ← generado localmente, NO en git
```

## Cómo arrancar (PC con entorno ya instalado)

```bash
# Abrir Anaconda Prompt
conda activate chatbot-consumidor

# Iniciar la app (usa qwen2.5:14b por defecto — actualizar default en rag_chain.py)
streamlit run src/app.py

# Iniciar Jupyter para notebooks
jupyter notebook
# Kernel a usar: "Python (chatbot-consumidor)"

# Si chroma_db/ no existe o se agregaron documentos nuevos al corpus:
python src/ingest.py
```

## Pipeline de evaluación automática

### Paso 1 — Generar respuestas de los modelos

```bash
# Evaluación baseline (corpus original) — ya ejecutada, resultado en evaluacion_resultados.json
python src/evaluacion.py --modelos mistral:7b-instruct llama3.1:8b gemma2:9b mistral-nemo:12b qwen2.5:14b

# Evaluación v2 (corpus + guía INDECOPI) — pendiente
python src/evaluacion.py --modelos mistral:7b-instruct llama3.1:8b gemma2:9b mistral-nemo:12b qwen2.5:14b --salida evaluacion_resultados_v2

# Argumentos disponibles:
# --preguntas   archivo JSON de preguntas (default: preguntas_evaluacion.json)
# --modelos     lista de modelos Ollama a evaluar
# --k           número de documentos recuperados (default: 3)
# --salida      prefijo del archivo de salida (default: evaluacion_resultados)
```

### Paso 2 — Evaluar con Gemini como juez

```bash
# Requiere GOOGLE_API_KEY en .env (ver .env.example)

# Evaluar baseline
python src/evaluar_llm_judge.py --entrada evaluacion_resultados.json --salida scores_gemini_baseline

# Evaluar v2 (después de generarla)
python src/evaluar_llm_judge.py --entrada evaluacion_resultados_v2.json --salida scores_gemini_v2

# Argumentos disponibles:
# --entrada   archivo JSON con respuestas a evaluar
# --salida    prefijo del archivo de salida (default: scores_gemini)
```

**Salida del juez:** JSON y CSV con score 0/1/2 por respuesta, justificación, conceptos encontrados/faltantes y alucinaciones detectadas.

## Configuración óptima encontrada

- **k=3** documentos recuperados (mejor balance ruido vs. contexto)
- **qwen2.5:14b** como modelo de producción (ganador con 15/20)
- **gemini-2.0-flash** como juez automático (gratuito, 1500 req/día)

## Hallazgos críticos de evaluación

1. **P6 (indemnización) falla en todos los modelos** — el corpus no tenía documento que explique los límites de INDECOPI. La guía INDECOPI agregada debe resolver esto en v2.
2. **P1 y P3 fallan por documentos de dominio incorrecto** — el retriever trae resoluciones de OSIPTEL/SBS en lugar de documentos INDECOPI generales. La guía INDECOPI nueva debe mejorar esto.
3. **mistral-nemo:12b tiene bug crítico** — genera caracteres japoneses en respuestas. Descartado para producción.
4. **El problema es el retriever, no el LLM** — con mejor corpus todos los modelos mejorarían.

Detalles completos en `EVALUACION.md`.

## Próximos pasos (en orden)

1. **Re-indexar ChromaDB** con guía INDECOPI: `python src/ingest.py`
2. **Correr evaluación v2**: `python src/evaluacion.py ... --salida evaluacion_resultados_v2`
3. **Evaluar baseline con Gemini juez**: `python src/evaluar_llm_judge.py --entrada evaluacion_resultados.json --salida scores_gemini_baseline`
4. **Evaluar v2 con Gemini juez**: `python src/evaluar_llm_judge.py --entrada evaluacion_resultados_v2.json --salida scores_gemini_v2`
5. **Documentar delta de impacto** en `EVALUACION.md` (v1 vs v2)
6. **Actualizar modelo default** en `src/rag_chain.py` y `src/app.py` de `mistral:7b-instruct` a `qwen2.5:14b`
7. **Completar notebooks** 01, 02 y 03
8. **Fase 4 — Deploy** (opciones: Streamlit Community Cloud con API externa, o documentar como deploy local con Ollama)

## Decisiones de diseño ya tomadas (no revertir sin razón)

- **No modificar los JSONs del corpus en disco** — transformación ocurre en memoria en `ingest.py`
- **No hacer fine-tuning del LLM** — RAG con buen prompt es suficiente para este corpus
- **No usar API de OpenAI/Groq** — RTX 4080 permite modelos locales equivalentes
- **Chunking adicional no necesario** — `texto` ya tiene granularidad adecuada
- **LangGraph no prioritario** — solo si sobra tiempo
- **Metodología de evaluación en dos fases** — baseline (corpus original) vs v2 (corpus ampliado) para documentar delta de impacto como resultado académico

## Archivo de preguntas de evaluación

Las 10 preguntas están en `preguntas_evaluacion.json` con campos:
- `id`, `categoria`, `pregunta`, `respuesta_referencia`

Para agregar preguntas: editar el JSON directamente, sin tocar código.
Categorías existentes: `libro_reclamaciones`, `telecomunicaciones`, `indecopi`, `inmobiliario`, `servicios_financieros`, `productos_defectuosos`, `precios`
