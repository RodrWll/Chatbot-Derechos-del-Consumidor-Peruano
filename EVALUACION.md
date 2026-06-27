# Evaluación del Chatbot RAG — Derechos del Consumidor Peruano

## Configuración base

| Parámetro | Valor |
|-----------|-------|
| Modelo de embeddings | `paraphrase-multilingual-MiniLM-L12-v2` |
| Vector store | ChromaDB local |
| Documentos indexados | 1349 |
| Hardware | Intel Core i9-14 · 64 GB RAM · RTX 4080 (CUDA) |

---

## Experimento 1 — Efecto del parámetro k

**Pregunta de prueba:** "¿Qué hago si me vendieron un producto defectuoso?"
**Modelo:** `mistral:7b-instruct`

### k=4
**Fuentes recuperadas:**
- Código de Protección y Defensa del Consumidor — Responsabilidad civil
- Guía sobre productos y servicios inmobiliarios *(irrelevante)*
- Lineamientos sobre Protección al Consumidor 2022
- Decreto Supremo sobre Libro de Reclamaciones

**Resultado:** Respuesta mezcla contexto de inmuebles con productos en general. El LLM incluye la Defensoría del Cliente Inmobiliario (DCI) como opción general, lo cual es incorrecto para la pregunta planteada.

**Calificación:** ⚠️ Parcialmente correcta — ruido por contexto cruzado

---

### k=2
**Resultado:** Menos ruido de contexto, pero el LLM alucina detalles para llenar vacíos:
- Menciona "Defensoría del Consumidor (DC)" — entidad inexistente
- Inventa umbral de "50 soles" para recurrir a juzgado
- Cita "Ley N° 28334" — número incorrecto (la ley correcta es la N° 29571)

**Calificación:** ❌ Peor que k=4 — menos ruido externo pero más alucinación interna

---

### k=3 *(configuración adoptada)*
**Fuentes recuperadas:**
- Código de Protección y Defensa del Consumidor — Responsabilidad civil ✅
- Guía sobre productos y servicios inmobiliarios ⚠️ *(irrelevante)*
- Lineamientos sobre Protección al Consumidor 2022 ✅

**Resultado:**
- Punto 1 ✅: Reclamo ante proveedor vía Libro de Reclamaciones, plazo de 15 días hábiles
- Punto 2 ✅: Reclamo ante INDECOPI vía Reclama Virtual, audiencia de conciliación
- Punto 3 ⚠️: DCI incluido por contaminación de contexto (documento de inmuebles)
- Fuentes inventadas ❌: LLM citó Ley N° 30693, URL de Defensoría y reglamento inexistentes en el corpus

**Calificación:** ✅ Mejor configuración encontrada — 2/3 puntos correctos y precisos

---

## Experimento 2 — Umbral de similitud (score_threshold)

**Configuración:** k=3, `search_type="similarity_score_threshold"`, `score_threshold=0.45`

**Resultado:** El umbral filtró también los documentos relevantes. El LLM generó respuesta casi sin contexto:
- Inventó "juzgado de protección de consumidores" (no existe en Perú)
- Citó "Ley Nº 29561" (no existe; la correcta es la 29571)
- Plazos inventados (30 días para notificar, 30 días para reparación)

**Conclusión:** Umbral de 0.45 demasiado restrictivo para este modelo de embeddings. Se requiere calibración más fina o un modelo de embeddings con mejor separación semántica.

**Calificación:** ❌ Peor resultado — máxima alucinación por falta de contexto

---

## Análisis de causa raíz — Contaminación de contexto cruzado

**Problema identificado:** El modelo de embeddings `MiniLM-L12-v2` no distingue suficientemente entre:
- "producto defectuoso" (pregunta general de consumidor)
- "servicio inmobiliario que no coincide con lo ofrecido" (contexto de inmuebles)

Ambos fragmentos tienen alta similitud semántica en el espacio de embeddings, por lo que el retriever siempre recupera el documento de inmuebles en preguntas sobre productos defectuosos.

**Impacto práctico:** Bajo (los puntos 1 y 2 son suficientes para orientar al usuario). **Impacto en confiabilidad:** Alto (introduce información de un dominio específico como respuesta general).

---

## Tabla resumen de configuraciones

| Configuración | Ruido externo | Alucinación interna | Calidad general |
|--------------|--------------|---------------------|-----------------|
| k=2, sin umbral | Bajo | Alta | ❌ |
| k=3, sin umbral | Medio | Baja | ✅ (mejor) |
| k=4, sin umbral | Alto | Baja | ⚠️ |
| k=3, threshold=0.45 | Muy bajo | Muy alta | ❌ |

**Configuración adoptada:** k=3, sin umbral.

---

## Mejoras identificadas para trabajo futuro

| Mejora | Impacto esperado | Complejidad |
|--------|-----------------|-------------|
| Modelo de embeddings más potente (`bge-m3` o `multilingual-e5-large`) | Mejor separación semántica entre dominios | Media |
| Pre-filtrado por `categoria_consumo` antes del retrieval | Eliminaría contaminación de contexto cruzado | Media |
| Comparar con `llama3.1:8b` | Ver si un modelo más grande alucina menos fuentes | Baja |
| MMR (Maximum Marginal Relevance) como estrategia de retrieval | Mayor diversidad de documentos recuperados | Baja |

---

## Pendiente — Preguntas de prueba estándar

Registrar resultados para las 4 preguntas base con `mistral:7b-instruct` (k=3):

| Pregunta | Resultado | Observaciones |
|----------|-----------|---------------|
| ¿Cuáles son mis derechos si un producto que compré está defectuoso? | ⚠️ | Ver Experimento 1 arriba |
| ¿Cómo presento una queja ante INDECOPI? | — | Pendiente |
| ¿Qué cubre el SOAT en caso de accidente de tránsito? | — | Pendiente |
| ¿Tengo derecho a atención preferente si soy adulto mayor? | — | Pendiente |

---

## Pendiente — Comparación de modelos (Fase 2)

| Modelo | Estado | ROUGE-L | Alucinaciones observadas |
|--------|--------|---------|--------------------------|
| `mistral:7b-instruct` | ✅ Evaluado | — | DCI en preguntas generales, fuentes inventadas |
| `llama3.1:8b` | ⏳ Descargando | — | — |
| `gemma2:9b` | ⏳ Pendiente | — | — |
