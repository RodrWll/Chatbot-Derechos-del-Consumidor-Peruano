# Chatbot de Simplificación de Derechos del Consumidor Peruano

## Qué es este proyecto

Chatbot académico (curso de PLN, décimo ciclo) que simplifica textos legales sobre derechos del consumidor en Perú para que ciudadanos comunes los entiendan. Usa arquitectura RAG: recupera fragmentos del corpus legal y los procesa con un LLM local para generar respuestas en lenguaje simple.

## Estado actual (actualizado 2026-06-28 — sesión 2)

- ✅ Fase 1 completa: corpus indexado, RAG funcionando, Streamlit operativo
- ✅ Fase 2 completa: evaluación de 5 modelos × 10 preguntas (manual)
- ✅ Fase 3 completa: evaluación automática con Gemini juez — baseline + v2 finalizadas
- ✅ Corpus ampliado (1356 docs): guía INDECOPI indexada en `chroma_db/`
- ✅ `evaluacion_resultados.json` — baseline: 5 modelos × 10 preguntas
- ✅ `evaluacion_resultados_v2.json` — v2: corpus + guía INDECOPI, 5 × 10
- ✅ `scores_gemini_baseline.json` / `scores_gemini_v2.json` — scores Gemini juez
- ✅ Prompt anti-alucinación actualizado en `rag_chain.py` (Ley N°29571, INDECOPI vs OSIPTEL/SBS, no indemnización vía INDECOPI)
- ✅ Modelo default actualizado a `qwen2.5:14b` en `rag_chain.py` y `app.py`
- ✅ Preguntas de evaluación ampliadas a **12** (P11: propina restaurante · P12: libros escolares)
- ✅ 5 ChromaDB de embeddings indexadas: `chroma_db_minilm/` `chroma_db_mpnet/` `chroma_db_e5large/` `chroma_db_bgem3/` `chroma_db_labse/`
- ⏳ **`evaluacion_embeddings.py` CORRIENDO** — 5 embeddings × 5 modelos × 12 = 300 combinaciones → `evaluacion_embeddings.json` (reanudable)
- ⏳ **Siguiente al terminar:** `python src/evaluar_llm_judge.py --entrada evaluacion_embeddings.json --salida scores_gemini_embeddings`
- ⏳ Documentar resultados de embeddings en `EVALUACION.md`
- ⏳ Notebooks 01, 02, 03 pendientes
- ⏳ Fase 4 (deploy) pendiente

## Hardware de desarrollo

Intel Core i9-14 · 64 GB RAM · NVIDIA RTX 4080 (16 GB VRAM)
→ Ollama usa CUDA automáticamente. Modelos 7B-14B corren completamente en GPU.

## Modelos Ollama instalados

| Modelo | Parámetros | Score manual | Score Gemini baseline | Score Gemini v2 | Estado |
|--------|-----------|:------------:|:---------------------:|:---------------:|--------|
| `qwen2.5:14b` | 14B | **15/20 🥇** | 9/20 | **10/20 🥇** | ✅ default |
| `mistral:7b-instruct` | 7B | 12/20 | 9/20 | 8/20 | ✅ instalado |
| `gemma2:9b` | 9B | 12/20 | 8/20 | 8/20 | ✅ instalado |
| `llama3.1:8b` | 8B | 11/20 | 6/20 | 5/20 | ✅ instalado |
| `mistral-nemo:12b` | 12B | 9/20 ⚠️ bug chars japoneses | 4/20 | 6/20 | ✅ instalado |

## Stack tecnológico

| Componente | Herramienta |
|------------|-------------|
| Lenguaje | Python 3.11.9 |
| Entorno | conda (`environment.yml`) — kernel Jupyter: "Python (chatbot-consumidor)" |
| Embeddings | `langchain_huggingface.HuggingFaceEmbeddings` — `paraphrase-multilingual-MiniLM-L12-v2` |
| Vector store | `langchain_chroma.Chroma` (local, persistente en `chroma_db/`) |
| LLM producción | `langchain_ollama.OllamaLLM` — modelo: `qwen2.5:14b` (ganador de la evaluación) |
| LLM juez evaluación | `gemini-2.5-flash` vía Google AI Studio API — SDK: `google-genai` (gratuito, 1500 req/día) |
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
├── CLAUDE.md                          ← este archivo
├── EVALUACION.md                      ← registro completo de experimentos y resultados
├── environment.yml                    ← entorno conda
├── .env                               ← API keys locales — NO en git
├── .env.example                       ← plantilla de variables de entorno
├── preguntas_evaluacion.json          ← 12 preguntas con respuestas de referencia
├── evaluacion_resultados.json         ← baseline: 5 modelos × 10 preguntas
├── evaluacion_resultados_v2.json      ← v2: corpus + guía INDECOPI, 5 × 10
├── scores_gemini_baseline.json/.csv   ← scores Gemini juez sobre baseline
├── scores_gemini_v2.json/.csv         ← scores Gemini juez sobre v2
├── evaluacion_embeddings.json         ← (generándose) 5 embeddings × 5 modelos × 12
├── scores_gemini_embeddings.json      ← (pendiente) scores Gemini sobre embeddings
├── final_json/                        ← corpus legal (NO modificar JSONs existentes)
│   ├── informes/                      ← 14 archivos (13 originales + guía INDECOPI)
│   ├── leyes/                         ← 5 archivos
│   └── normas reglamentarias/         ← 10 archivos
├── src/
│   ├── ingest.py                      ← indexa corpus en chroma_db/ (producción)
│   ├── ingest_embeddings.py           ← indexa corpus en 5 ChromaDB (experimento embeddings)
│   ├── rag_chain.py                   ← cadena RAG + PROMPT_TEMPLATE anti-alucinación
│   ├── app.py                         ← interfaz Streamlit (default: qwen2.5:14b)
│   ├── evaluacion.py                  ← evaluación multi-modelo (preguntas_evaluacion.json)
│   ├── evaluacion_embeddings.py       ← evaluación 5×5×12 con reanudación automática
│   └── evaluar_llm_judge.py           ← juez Gemini con reanudación por (pregunta,modelo,embedding)
├── notebooks/
│   ├── 01_exploracion_datos.ipynb
│   ├── 02_indexacion_vectorstore.ipynb
│   └── 03_chatbot_rag.ipynb
├── diagramas/                         ← 4 diagramas draw.io + PNG
├── chroma_db/                         ← producción (MiniLM-L12, corpus completo)
├── chroma_db_minilm/                  ← experimento embeddings
├── chroma_db_mpnet/                   ← experimento embeddings
├── chroma_db_e5large/                 ← experimento embeddings
├── chroma_db_bgem3/                   ← experimento embeddings
└── chroma_db_labse/                   ← experimento embeddings
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

### Evaluación estándar (un embedding, múltiples modelos)

```bash
# Generar respuestas
python src/evaluacion.py --modelos mistral:7b-instruct llama3.1:8b gemma2:9b mistral-nemo:12b qwen2.5:14b --salida evaluacion_resultados_v3

# Evaluar con Gemini juez (reanudable — si se corta, relanzar mismo comando)
python src/evaluar_llm_judge.py --entrada evaluacion_resultados_v3.json --salida scores_gemini_v3
```

### Experimento multi-embedding (5 embeddings × 5 modelos × 12 preguntas = 300)

```bash
# Paso 1 — Indexar 5 ChromaDB (ya hecho, idempotente si se vuelve a correr)
python src/ingest_embeddings.py

# Paso 2 — Evaluar 300 combinaciones (reanudable)
python src/evaluacion_embeddings.py

# Paso 3 — Puntuar con Gemini (reanudable)
python src/evaluar_llm_judge.py --entrada evaluacion_embeddings.json --salida scores_gemini_embeddings
```

**IMPORTANTE — reanudación:** todos los scripts retoman donde quedaron si se interrumpen. Relanzar el mismo comando es siempre seguro.

**Nota sobre aiohttp/google-genai:**
- SDK correcto: `from google import genai` / `from google.genai import types` (NO `google.generativeai`)
- Modelo juez: `gemini-2.5-flash`
- Si hay error SSL con aiohttp: `pip install "aiohttp<3.10"`

**Salida del juez:** JSON y CSV con score 0/1/2 por respuesta, justificación, conceptos encontrados/faltantes y alucinaciones detectadas.

## Configuración óptima encontrada

- **k=3** documentos recuperados (mejor balance ruido vs. contexto)
- **qwen2.5:14b** como modelo de producción (ganador con 10/20 en v2 según Gemini)
- **gemini-2.5-flash** como juez automático (gratuito, 1500 req/día)
- **Prompt anti-alucinación** activo en `rag_chain.py` (reglas explícitas sobre Ley N°29571, competencias de INDECOPI/OSIPTEL/SBS, prohibición de inventar leyes)

## Hallazgos críticos de evaluación

1. **P6 (indemnización) falla en todos los modelos en ambas versiones** — INDECOPI no puede otorgar indemnizaciones (solo multas y medidas correctivas); la vía correcta es el Poder Judicial. Ningún modelo llega a esto sin el corpus adecuado.
2. **El impacto de la guía INDECOPI fue marginal** — delta promedio +0.4 puntos. El retriever sigue trayendo documentos de dominio incorrecto.
3. **Las alucinaciones son masivas** — todos los modelos inventan leyes, instituciones y plazos inexistentes. El prompt anti-alucinación actualizado debe reducir esto.
4. **mistral-nemo:12b tiene bug crítico** — genera caracteres japoneses. Descartado para producción.
5. **El problema central es el retriever** — con mejor embedding y corpus más preciso todos los modelos mejorarían significativamente.

Detalles completos con scores en `EVALUACION.md`.

## Próximos pasos (en orden)

1. ⏳ **Esperar `evaluacion_embeddings.py`** (~2-3 horas, corriendo ahora)
2. ⏳ **Evaluar embeddings con Gemini**: `python src/evaluar_llm_judge.py --entrada evaluacion_embeddings.json --salida scores_gemini_embeddings`
3. ⏳ **Documentar resultados de embeddings** en `EVALUACION.md`
4. ⏳ **Completar notebooks** 01, 02 y 03
5. ⏳ **Fase 4 — Deploy** (Streamlit Community Cloud con API externa, o deploy local con Ollama documentado)

## Decisiones de diseño ya tomadas (no revertir sin razón)

- **No modificar los JSONs del corpus en disco** — transformación ocurre en memoria en `ingest.py`
- **No hacer fine-tuning del LLM** — RAG con buen prompt es suficiente para este corpus
- **No usar API de OpenAI/Groq** — RTX 4080 permite modelos locales equivalentes
- **Chunking adicional no necesario** — `texto` ya tiene granularidad adecuada
- **LangGraph no prioritario** — solo si sobra tiempo
- **Metodología de evaluación en dos fases** — baseline (corpus original) vs v2 (corpus ampliado) para documentar delta de impacto como resultado académico

## Archivo de preguntas de evaluación

Las **12 preguntas** están en `preguntas_evaluacion.json` con campos:
- `id`, `categoria`, `pregunta`, `respuesta_referencia`

Para agregar preguntas: editar el JSON directamente, sin tocar código.
Categorías existentes: `libro_reclamaciones`, `telecomunicaciones`, `indecopi`, `inmobiliario`, `servicios_financieros`, `productos_defectuosos`, `precios`, `educacion`

**Nota:** Los archivos `evaluacion_resultados.json` y `evaluacion_resultados_v2.json` tienen 10 preguntas (histórico). El experimento de embeddings (`evaluacion_embeddings.json`) usa las 12.

## Notas de entorno (problemas conocidos)

- **torch**: usar `torch==2.5.1+cu121` + `torchvision==0.20.1+cu121`. NO subir a 2.12.x (rompe torchvision). Si se sube accidentalmente: `pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121`
- **bge-m3 / LaBSE**: requieren `model_kwargs={"use_safetensors": True}` en `HuggingFaceEmbeddings` para evitar cargar `pytorch_model.bin` con torch 2.5.1. Ya configurado en `ingest_embeddings.py` y `evaluacion_embeddings.py`.
- **aiohttp**: mantener `aiohttp<3.10` para evitar error SSL de Windows. Si se rompe: `pip install "aiohttp<3.10"`
- **Caracteres unicode en consola Windows**: los scripts usan `[OK]`/`[FAIL]` en lugar de emojis/checkmarks para evitar errores de encoding.
