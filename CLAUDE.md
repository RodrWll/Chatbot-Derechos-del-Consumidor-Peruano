# Chatbot de Simplificación de Derechos del Consumidor Peruano

## Qué es este proyecto

Chatbot académico (curso de PLN, décimo ciclo) que simplifica textos legales sobre derechos del consumidor en Perú para que ciudadanos comunes los entiendan. Usa arquitectura RAG: recupera fragmentos del corpus legal y los procesa con un LLM local para generar respuestas en lenguaje simple.

## Estado actual (actualizado 2026-06-29 — sesión 4)

### Fase 3 COMPLETA — Ciclo de experimentos cerrado

- ✅ **Exp5** — Corpus ampliado (2 docs nuevos) + top embeddings: regresión por ruido competitivo
- ✅ **Exp6** — Pre-filtrado por categoría: recupera nivel Exp4, mistral+e5 supera Exp4
- ✅ **Exp7** — Fix de prompt para P8: **24/24 = 2.0/2.0 puntuación perfecta**
- ✅ `src/rag_chain.py` actualizado con configuración ganadora final (bge-m3, k=3, chroma_db_bgem3_exp5)
- ✅ `EVALUACION.md` actualizado con resultados completos Exp5→Exp7

### Resultado final del ciclo de experimentos

**Configuración ganadora: qwen2.5:14b + bge-m3 + pre-filtrado + prompt v3 = 24/24 (2.0/2.0)**

| Palanca de mejora | Impacto |
|-------------------|---------|
| Mejor embedding (bge-m3 vs MiniLM) | +0.52 pts sobre baseline |
| Corpus ampliado sin filtro (Exp5) | Neutro/negativo — ruido competitivo |
| Pre-filtrado por categoría (Exp6) | +0.167 vs Exp5 |
| Fix de prompt para P8 (Exp7) | +0.083 — resuelve sesgo LLM en comisiones bancarias |
| **Score final** | **24/24 = 2.0/2.0** ✅ |

### Pendiente — Fase 4

- ⏳ **Fase 4 — Deploy** (decisión pendiente: HuggingFace Spaces CPU Basic con Gemini API, o deploy local documentado)
- ⏳ **Actualizar diagramas** en `diagramas/` — instrucciones detalladas en `.claude/plans/quiero-que-revises-el-gentle-feather.md`
- ⏳ **Notebooks** 01, 02, 03 — exploración y análisis

## Hardware de desarrollo

Intel Core i9-14 · 64 GB RAM · NVIDIA RTX 4080 (16 GB VRAM)
→ Ollama usa CUDA automáticamente. Modelos 7B-14B corren completamente en GPU.

## Modelos Ollama instalados

| Modelo | Parámetros | Score Gemini Exp7 | Estado |
|--------|-----------|:-----------------:|--------|
| `qwen2.5:14b` | 14B | **24/24 🥇** | ✅ **producción** |
| `mistral:7b-instruct` | 7B | 19/24 (Exp6) | ✅ instalado |
| `llama3.1:8b` | 8B | 17/24 (Exp6) | ✅ instalado |
| `gemma2:9b` | 9B | — (no en top-3) | ✅ instalado |
| `mistral-nemo:12b` | 12B | — (bug japonés) | ⚠️ descartado producción |

## Stack tecnológico

| Componente | Herramienta |
|------------|-------------|
| Lenguaje | Python 3.11.9 |
| Entorno | conda (`environment.yml`) — kernel Jupyter: "Python (chatbot-consumidor)" |
| Embeddings | `langchain_huggingface.HuggingFaceEmbeddings` — **`BAAI/bge-m3`** (1024 dims) |
| Vector store | `langchain_chroma.Chroma` — **`chroma_db_bgem3_exp5/`** (1356 docs) |
| Pre-filtrado | `CATEGORIA_MAP` en `evaluacion_embeddings.py` — filtro por `categoria_consumo` antes del retrieval |
| LLM producción | `langchain_ollama.OllamaLLM` — modelo: **`qwen2.5:14b`** |
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
├── EVALUACION.md                      ← registro completo Exp1→Exp7
├── environment.yml                    ← entorno conda
├── .env                               ← API keys locales — NO en git
├── .env.example                       ← plantilla de variables de entorno
├── preguntas_evaluacion.json          ← 12 preguntas con respuestas de referencia
├── evaluacion_resultados.json         ← baseline: 5 modelos × 10 preguntas (histórico)
├── evaluacion_resultados_v2.json      ← v2: corpus + guía INDECOPI (histórico)
├── scores_gemini_baseline.json/.csv   ← scores Gemini juez sobre baseline
├── scores_gemini_v2.json/.csv         ← scores Gemini juez sobre v2
├── evaluacion_embeddings.json         ← Exp4: 5 embeddings × 5 modelos × 12 = 300
├── scores_gemini_embeddings.json/.csv ← scores Gemini Exp4 (300 evaluaciones)
├── evaluacion_exp5.json               ← Exp5: 3 modelos × 2 embeddings × 12 = 72
├── scores_gemini_exp5.json/.csv       ← scores Gemini Exp5
├── evaluacion_exp6.json               ← Exp6: 3 pares × 12 = 36 (pre-filtrado)
├── scores_gemini_exp6.json/.csv       ← scores Gemini Exp6
├── evaluacion_exp7.json               ← Exp7: 1 par × 12 = 12 (prompt P8 fix)
├── scores_gemini_exp7.json/.csv       ← scores Gemini Exp7 — 24/24 perfecto
├── reporte.html                       ← reporte comparativo generado
├── final_json/                        ← corpus legal (NO modificar JSONs existentes)
│   ├── informes/                      ← 15 archivos (13 originales + guía INDECOPI + 2 nuevos Exp5)
│   ├── leyes/                         ← 5 archivos
│   └── normas reglamentarias/         ← 10 archivos
├── src/
│   ├── ingest.py                      ← indexa corpus en chroma_db/ (producción legacy)
│   ├── ingest_embeddings.py           ← indexa corpus en ChromaDBs con --suffix (Exp4/Exp5)
│   ├── rag_chain.py                   ← cadena RAG + PROMPT_TEMPLATE anti-alucinación v3
│   ├── app.py                         ← interfaz Streamlit (default: qwen2.5:14b)
│   ├── evaluacion.py                  ← evaluación multi-modelo estándar
│   ├── evaluacion_embeddings.py       ← evaluación multi-embedding con reanudación + pre-filtrado
│   ├── evaluar_llm_judge.py           ← juez Gemini con reanudación
│   └── generar_reporte.py             ← genera reporte.html comparativo
├── notebooks/
│   ├── 01_exploracion_datos.ipynb
│   ├── 02_indexacion_vectorstore.ipynb
│   └── 03_chatbot_rag.ipynb
├── diagramas/                         ← 4 diagramas draw.io + PNG (pendiente actualizar)
├── chroma_db/                         ← legacy (MiniLM-L12, corpus 1349 docs) — NO usar en prod
├── chroma_db_minilm/                  ← Exp4
├── chroma_db_mpnet/                   ← Exp4
├── chroma_db_e5large/                 ← Exp4
├── chroma_db_bgem3/                   ← Exp4
├── chroma_db_labse/                   ← Exp4
├── chroma_db_bgem3_exp5/              ← PRODUCCIÓN — bge-m3, corpus ampliado (1356 docs)
└── chroma_db_e5large_exp5/            ← Exp5/Exp6 con e5-large
```

## Cómo arrancar (PC con entorno ya instalado)

```bash
# Abrir Anaconda Prompt
conda activate chatbot-consumidor

# Iniciar la app — usa qwen2.5:14b + bge-m3 + chroma_db_bgem3_exp5 (configuración ganadora)
streamlit run src/app.py

# Iniciar Jupyter para notebooks
jupyter notebook
# Kernel a usar: "Python (chatbot-consumidor)"

# Si chroma_db_bgem3_exp5/ no existe (primer arranque en otra máquina):
python src/ingest_embeddings.py --embeddings bge-m3 --suffix _exp5
```

## Pipeline de evaluación automática

### Evaluación estándar (un embedding, múltiples modelos)

```bash
python src/evaluacion.py --modelos qwen2.5:14b llama3.1:8b mistral:7b-instruct --salida evaluacion_nuevo
python src/evaluar_llm_judge.py --entrada evaluacion_nuevo.json --salida scores_gemini_nuevo
```

### Experimento con pre-filtrado por categoría (como Exp6/Exp7)

```bash
# Par específico + pre-filtrado (usa chroma_db_bgem3_exp5 ya existente)
python src/evaluacion_embeddings.py \
    --pares "qwen2.5:14b|bge-m3" \
    --suffix _exp5 \
    --prefiltrar \
    --salida evaluacion_nuevo

python src/evaluar_llm_judge.py --entrada evaluacion_nuevo.json --salida scores_gemini_nuevo

python src/generar_reporte.py \
    --entrada scores_gemini_nuevo.json \
    --baseline scores_gemini_exp7.json \
    --salida reporte_nuevo.html \
    --baseline-label "Exp7 (baseline perfecto)" \
    --current-label "Nuevo experimento"
```

**IMPORTANTE — reanudación:** todos los scripts retoman donde quedaron si se interrumpen. Relanzar el mismo comando es siempre seguro.

**Nota sobre aiohttp/google-genai:**
- SDK correcto: `from google import genai` / `from google.genai import types` (NO `google.generativeai`)
- Modelo juez: `gemini-2.5-flash`
- Si hay error SSL con aiohttp: `pip install "aiohttp<3.10"`

## Configuración óptima encontrada (DEFINITIVA)

- **Embedding:** `BAAI/bge-m3` (1024 dims) — ganador absoluto del Exp4
- **k=3** documentos recuperados — validado en Exp1, usado en todos los experimentos
- **Pre-filtrado por categoría** — `CATEGORIA_MAP` en `evaluacion_embeddings.py` — mejora Exp6
- **qwen2.5:14b** como modelo de producción — ganador consistente en todos los experimentos
- **gemini-2.5-flash** como juez automático (gratuito, 1500 req/día)
- **Prompt anti-alucinación v3** en `src/rag_chain.py`:
  - Reglas sobre Ley N°29571, competencias INDECOPI/OSIPTEL/SBS
  - INDECOPI NO puede otorgar indemnizaciones (solo multas y medidas correctivas)
  - Bancos OBLIGADOS a notificar antes de cobrar nuevas comisiones (regla agregada en Exp7)

## Hallazgos críticos de evaluación (resultado final)

1. **El embedding es más determinante que el LLM** — bge-m3 supera a MiniLM en +40% de score promedio.
2. **P8 fue el último fallo sistémico** — resuelto con regla explícita en el prompt (Exp7). Antes fallaba por sesgo del LLM, no por retrieval.
3. **Pre-filtrado por categoría es necesario** — corpus ampliado sin filtro introduce ruido competitivo (Exp5 regression).
4. **Cero alucinaciones alcanzado** — primer resultado limpio en Exp7 con la config final.
5. **mistral-nemo:12b tiene bug crítico** — genera caracteres japoneses. Descartado para producción.

Detalles completos con scores por pregunta en `EVALUACION.md`.

## Decisiones de diseño ya tomadas (no revertir sin razón)

- **No modificar los JSONs del corpus en disco** — transformación ocurre en memoria en `ingest.py`
- **No hacer fine-tuning del LLM** — RAG con buen prompt es suficiente para este corpus
- **bge-m3 es el embedding de producción** — no revertir a MiniLM-L12-v2 (rendimiento ~40% inferior)
- **chroma_db_bgem3_exp5/ es el vector store de producción** — corpus ampliado (1356 docs)
- **Pre-filtrado por categoría activo** — CATEGORIA_MAP mapea categoría de pregunta → valores Chroma
- **k=3 sin umbral de similitud** — threshold=0.45 fue probado en Exp1 y descartado
- **Chunking adicional no necesario** — `texto` ya tiene granularidad adecuada
- **LangGraph no prioritario** — solo si sobra tiempo en Fase 4
- **Para Fase 4 cloud (0 costo):** LLM debe cambiar a Gemini API — qwen2.5:14b necesita GPU local

## Archivo de preguntas de evaluación

Las **12 preguntas** están en `preguntas_evaluacion.json` con campos:
- `id`, `categoria`, `pregunta`, `respuesta_referencia`

Para agregar preguntas: editar el JSON directamente, sin tocar código.
Categorías existentes: `libro_reclamaciones`, `telecomunicaciones`, `indecopi`, `inmobiliario`, `servicios_financieros`, `productos_defectuosos`, `precios`, `educacion`

## Notas de entorno (problemas conocidos)

- **torch**: usar `torch==2.5.1+cu121` + `torchvision==0.20.1+cu121`. NO subir a 2.12.x (rompe torchvision). Si se sube accidentalmente: `pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121`
- **bge-m3**: requiere `model_kwargs={"use_safetensors": True}` y `encode_kwargs={"normalize_embeddings": True}` en `HuggingFaceEmbeddings`. Ya configurado en `rag_chain.py`, `ingest_embeddings.py` y `evaluacion_embeddings.py`.
- **aiohttp**: mantener `aiohttp<3.10` para evitar error SSL de Windows. Si se rompe: `pip install "aiohttp<3.10"`
- **Caracteres unicode en consola Windows**: los scripts usan `[OK]`/`[FAIL]` en lugar de emojis/checkmarks para evitar errores de encoding.
