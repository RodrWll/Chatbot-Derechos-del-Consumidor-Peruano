# Chatbot de Simplificación de Derechos del Consumidor Peruano

## Qué es este proyecto

Chatbot académico (curso de PLN, décimo ciclo) que simplifica textos legales sobre derechos del consumidor en Perú para que ciudadanos comunes los entiendan. Usa arquitectura RAG: recupera fragmentos del corpus legal y los procesa con un LLM local para generar respuestas en lenguaje simple.

## Estado actual

- Corpus listo: 28 archivos JSON en `final_json/` (leyes, normas reglamentarias, informes de INDECOPI/SPIJ)
- Código base creado: `src/ingest.py`, `src/rag_chain.py`, `src/app.py`
- Notebooks listos: `notebooks/01`, `02`, `03`
- El vector store ChromaDB (`chroma_db/`) NO está en el repositorio — se genera localmente ejecutando `python src/ingest.py`
- **El LLM aún no ha sido definido definitivamente** — se comparan `mistral:7b-instruct` y `llama3.1:8b` vía Ollama

## Hardware de desarrollo

Intel Core i9-14 · 64 GB RAM · NVIDIA RTX 4080 (16 GB VRAM)
→ Ollama usa CUDA automáticamente. Modelos 7B-9B corren completamente en GPU.

## Stack tecnológico

| Componente | Herramienta |
|------------|-------------|
| Lenguaje | Python 3.11.9 |
| Entorno | conda (`environment.yml`) |
| Embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| Vector store | ChromaDB (local, persistente en `chroma_db/`) |
| LLM | Ollama (`mistral:7b-instruct` o `llama3.1:8b`) |
| UI | Streamlit (`src/app.py`) |
| Orquestación | LangChain (`RetrievalQA`) |

## Estructura del proyecto

```
├── CLAUDE.md                ← este archivo
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
│   └── app.py               ← interfaz Streamlit
├── notebooks/
│   ├── 01_exploracion_datos.ipynb
│   ├── 02_indexacion_vectorstore.ipynb
│   └── 03_chatbot_rag.ipynb ← MVP interactivo + evaluación ROUGE-L
└── chroma_db/               ← generado localmente, NO en git
```

## Esquema JSON del corpus

Todos los archivos en `final_json/` tienen el mismo esquema:
```json
{
  "id": 1,
  "nombre_doc": "Nombre del documento",
  "tipo_doc": "ley | informe | norma reglamentaria",
  "capitulo_seccion": "Título de la sección",
  "categoria_consumo": ["categoría1", "categoría2"],
  "texto": "Contenido legal a simplificar",
  "source": "archivo_original.pdf"
}
```

El campo `texto` se mapea a `page_content` de LangChain. El resto va a `metadata`. No modificar los JSONs en disco — la transformación ocurre en `src/ingest.py`.

## Cómo arrancar desde cero (PC nueva)

```bash
# 1. Instalar Miniconda si no está instalado
# 2. Doble clic en setup.bat (crea el entorno conda)
# 3. Instalar Ollama desde https://ollama.com
ollama pull mistral:7b-instruct

# 4. Activar entorno y generar el vector store
conda activate chatbot-consumidor
python src/ingest.py

# 5. Probar el chatbot
streamlit run src/app.py
# o abrir notebooks/03_chatbot_rag.ipynb en Jupyter
```

## Ruta de implementación pendiente

### Fase 2 — Evaluación de LLMs (próxima)
- Comparar `mistral:7b-instruct` vs `llama3.1:8b` con las 4 preguntas de prueba
- Medir ROUGE-L vs. respuestas de referencia escritas manualmente
- Medir legibilidad Flesch-Szigriszt de la respuesta generada vs. el texto fuente
- Elegir el modelo final basándose en calidad + velocidad

### Fase 3 — LangGraph (opcional)
- Solo implementar si hay tiempo y se quiere manejar consultas multi-paso
- El RAG lineal ya es suficiente para el curso

### Fase 4 — Web (post-MVP)
- Backend FastAPI + frontend Streamlit ya scaffoldeado en `src/app.py`
- Deploy en HuggingFace Spaces o Render.com

## Decisiones de diseño ya tomadas (no revertir sin razón)

- **No modificar los JSONs en disco** — la transformación al esquema LangChain ocurre en memoria en `ingest.py`
- **No hacer fine-tuning** — RAG con prompt bien diseñado es suficiente para este corpus
- **No usar API de OpenAI/Groq** — el hardware permite modelos locales de calidad equivalente
- **Chunking adicional no necesario** — los `texto` ya tienen granularidad adecuada (50-800 palabras); solo aplicar `RecursiveCharacterTextSplitter` si un texto supera ~512 tokens
- **LangGraph no prioritario** — agregar solo si se completan las fases 1 y 2

## Preguntas de prueba estándar

Usar siempre estas 4 para evaluar y comparar:
1. "¿Cuáles son mis derechos si un producto que compré está defectuoso?"
2. "¿Cómo presento una queja ante INDECOPI?"
3. "¿Qué cubre el SOAT en caso de accidente de tránsito?"
4. "¿Tengo derecho a atención preferente si soy adulto mayor?"
