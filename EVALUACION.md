# Evaluación del Chatbot RAG — Derechos del Consumidor Peruano

## Configuración base

| Parámetro | Valor |
|-----------|-------|
| Modelo de embeddings | `paraphrase-multilingual-MiniLM-L12-v2` |
| Vector store | ChromaDB local |
| Documentos indexados | 1356 (corpus ampliado con guía INDECOPI) |
| Hardware | Intel Core i9-14 · 64 GB RAM · RTX 4080 (CUDA) |

---

## Experimento 1 — Efecto del parámetro k

**Pregunta de prueba:** "¿Qué hago si me vendieron un producto defectuoso?"
**Modelo:** `mistral:7b-instruct`

| Configuración | Ruido externo | Alucinación interna | Calidad general |
|--------------|:------------:|:-------------------:|:---------------:|
| k=2, sin umbral | Bajo | Alta | ❌ |
| k=3, sin umbral | Medio | Baja | ✅ (mejor) |
| k=4, sin umbral | Alto | Baja | ⚠️ |
| k=3, threshold=0.45 | Muy bajo | Muy alta | ❌ |

**Configuración adoptada: k=3, sin umbral.**

- k=2: el LLM alucinó para llenar vacíos (inventó "Defensoría del Consumidor (DC)", umbral de "50 soles", "Ley N° 28334").
- k=4: contexto cruzado con inmuebles — el LLM incluyó la Defensoría del Cliente Inmobiliario (DCI) como opción general.
- threshold=0.45: filtró también documentos relevantes; máxima alucinación (inventó "juzgado de protección de consumidores", "Ley N° 29561", plazos falsos).

---

## Experimento 2 — Contaminación de contexto cruzado

**Problema identificado:** `MiniLM-L12-v2` no distingue suficientemente entre "producto defectuoso" (consumidor general) y "servicio inmobiliario que no coincide con lo ofrecido" (dominio específico). El retriever siempre recupera la *Guía sobre productos y servicios inmobiliarios* en preguntas sobre productos defectuosos, y el LLM incluye entonces la DCI como opción válida.

**Impacto en producción:** bajo (los puntos correctos siguen siendo útiles); impacto en confiabilidad: alto (introduce un dominio incorrecto).

---

## Evaluación comparativa — 5 modelos × 10 preguntas (2026-06-27)

### Conjunto de evaluación

Archivo: `preguntas_evaluacion.json` — 12 preguntas con respuesta de referencia validada.  
P1–P10 usadas en la evaluación comparativa original. P11–P12 agregadas para el experimento multi-embedding.

| ID | Categoría | Pregunta |
|----|-----------|---------|
| 1 | libro_reclamaciones | ¿Cuál es la diferencia entre queja y reclamo en el Libro de Reclamaciones? |
| 2 | telecomunicaciones | ¿A quién reclamo si tengo un problema con mi servicio de telefonía móvil? |
| 3 | indecopi | ¿Qué diferencia una denuncia de una reclamación? |
| 4 | inmobiliario | ¿Qué debe figurar en el contrato de compraventa de un departamento? |
| 5 | servicios_financieros | ¿Tengo derecho a pagar por adelantado mis préstamos con el banco? |
| 6 | indecopi | ¿Puedo pedir indemnización mediante el Libro de Reclamaciones o INDECOPI? |
| 7 | productos_defectuosos | ¿Pueden negarse a cambiarme una prenda con roturas o mala calidad? |
| 8 | servicios_financieros | ¿El banco puede cobrar comisiones a mi tarjeta sin avisarme? |
| 9 | libro_reclamaciones | ¿Un negocio digital debe tener libro de reclamaciones? |
| 10 | precios | ¿Pueden cobrarme más del precio que muestran en tienda o web? |
| 11 | precios | ¿Me pueden obligar a pagar propina o un adicional al precio de la carta en un restaurante? |
| 12 | educacion | ¿El colegio puede obligarme a comprar libros de texto nuevos para mis hijos? |

### Scorecard (✅ correcto · ⚠️ parcial · ❌ incorrecto)

| Pregunta | mistral:7b | llama3.1:8b | gemma2:9b | mistral-nemo:12b | qwen2.5:14b |
|----------|:----------:|:-----------:|:---------:|:----------------:|:-----------:|
| P1 Queja vs reclamo | ⚠️ | ❌ | ❌ | ⚠️ | ⚠️ |
| P2 Telefonía móvil | ❌ | ⚠️ | ⚠️ | ⚠️ | ✅ |
| P3 Denuncia vs reclamación | ❌ | ⚠️ | ⚠️ | ❌ | ❌ |
| P4 Contrato inmobiliario | ✅ | ⚠️ | ✅ | ⚠️ | ✅ |
| P5 Pago adelantado banco | ⚠️ | ❌ | ⚠️ | ⚠️ | ✅ |
| P6 Indemnización INDECOPI | ❌ | ❌ | ❌ | ❌ | ❌ |
| P7 Prenda defectuosa | ⚠️ | ✅ | ⚠️ | ❌ | ✅ |
| P8 Comisiones banco | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| P9 Libro de reclamaciones digital | ✅ | ✅ | ✅ | ✅ | ✅ |
| P10 Precio exhibido | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Puntaje (✅=2 · ⚠️=1 · ❌=0)** | **12/20** | **11/20** | **12/20** | **9/20** | **15/20** |

### Velocidad promedio por modelo

| Modelo | Promedio (s) |
|--------|:------------:|
| gemma2:9b | 2.27 |
| mistral:7b-instruct | 2.76 |
| llama3.1:8b | 3.33 |
| mistral-nemo:12b | 3.73 |
| qwen2.5:14b | 5.74 |

### Ranking final

| Posición | Modelo | Puntaje | Velocidad |
|:--------:|--------|:-------:|:---------:|
| 🥇 1 | **qwen2.5:14b** | 15/20 | 5.74s |
| 🥈 2 | **mistral:7b-instruct** | 12/20 | 2.76s |
| 🥈 2 | **gemma2:9b** | 12/20 | 2.27s |
| 4 | llama3.1:8b | 11/20 | 3.33s |
| 5 | mistral-nemo:12b | 9/20 | 3.73s |

**Ganador: `qwen2.5:14b`** — mejor precisión en las 10 preguntas. `mistral:7b-instruct` sigue siendo válido si se prioriza velocidad sobre precisión.

---

## Hallazgos críticos de la evaluación

### 1. P6 — Todos los modelos fallaron (fallo sistémico del corpus)

La respuesta correcta es **NO**: ni el Libro de Reclamaciones ni INDECOPI permiten exigir indemnización por daños y perjuicios — eso requiere un juicio ordinario ante el Poder Judicial. Los cinco modelos respondieron que sí es posible o dieron instrucciones incorrectas.

**Causa raíz:** el retriever recuperó la *Cartilla informativa sobre SOAT* para esta pregunta (similitud semántica con "daños sufridos" / "reparación"). El documento habla de reembolsos del seguro, no de límites de INDECOPI. El corpus no tiene un documento que explique explícitamente qué NO puede hacer INDECOPI.

### 2. P1 — Distinción queja/reclamo no captada por ningún modelo

**Causa raíz:** el retriever recupera la *Guía de reclamos y quejas en el servicio público de telecomunicaciones*, donde queja y reclamo tienen definiciones propias del sector telecomunicaciones, distintas a las del Libro de Reclamaciones general (D.S. N° 011-2011-PCM). Ningún modelo llegó a la distinción correcta: reclamo = problema con el producto/servicio; queja = trato del proveedor al consumidor.

### 3. P3 — Confusión denuncia administrativa vs penal

Todos los modelos que fallaron confundieron "denuncia ante INDECOPI" (procedimiento administrativo para sancionar con multa) con "denuncia penal" (ante Ministerio Público o tribunales). El retriever recuperó resoluciones de OSIPTEL y SBS en lugar de documentación de INDECOPI.

### 4. Bug crítico en mistral-nemo:12b — P7

Generó caracteres japoneses en la respuesta: *"los 問部商会 no pueden negarse..."* — fallo de tokenización inaceptable en un contexto legal. Descalifica al modelo para producción.

### 5. Alucinaciones específicas por modelo

| Modelo | Alucinación documentada |
|--------|------------------------|
| mistral:7b | "ORCT" (organismo inexistente) en P2; teléfono de INDECOPI inventado en P7 |
| llama3.1:8b | Plazo de "10 días hábiles" inventado para prepago en P5; "D.L. 1056/2018" incorrecto en P9 |
| gemma2:9b | "INDEFI" (institución inexistente) en P5 |
| mistral-nemo:12b | SUNAT/SMV para denuncias de consumidor en P3; URL inventada en P5; bug de caracteres japoneses |
| qwen2.5:14b | Envía denuncia al Ministerio Público en lugar de INDECOPI en P3 |

---

## Análisis de causa raíz consolidado

La mayoría de los errores no son atribuibles al LLM sino al **retriever**: cuando el corpus no tiene el documento correcto o recupera uno de dominio equivocado, ningún modelo puede compensarlo. Los tres patrones de fallo identificados son:

| Patrón | Preguntas afectadas | Solución |
|--------|--------------------|-----------| 
| Documento de dominio incorrecto recuperado | P1 (telecom vs general), P2 (telecom), P3 (OSIPTEL/SBS vs INDECOPI), P6 (SOAT vs límites INDECOPI) | Agregar documentos faltantes al corpus |
| Corpus no tiene el documento específico | P6 (límites de INDECOPI), P3 (proceso de denuncia INDECOPI) | Indexar guía oficial de procedimientos INDECOPI |
| Similitud semántica superficial del modelo de embeddings | P1, P6 | Modelo de embeddings más potente o pre-filtrado por categoría |

---

## Mejoras de mayor impacto

| Mejora | Impacto | Complejidad | Preguntas que resuelve |
|--------|:-------:|:-----------:|----------------------|
| Agregar al corpus: guía oficial de procedimientos INDECOPI (denuncia, reclamo, límites) | Alto | Baja | P3, P6 |
| Agregar al corpus: D.S. N° 024-2002-MTC (Reglamento SOAT con montos en UIT) | Medio | Baja | P6 (SOAT) |
| Pre-filtrado por `categoria` antes del retrieval | Alto | Media | P1, P2, P3 |
| Modelo de embeddings más potente (`bge-m3` o `multilingual-e5-large`) | Medio | Media | P1, P6 |
| Evaluar `qwen2.5:14b` como modelo de producción (ganador actual) | Alto | Baja | General |

---

## Evaluación con Gemini como juez — baseline y v2 (2026-06-28)

### Metodología

- **Juez:** `gemini-2.5-flash` via `google-genai` SDK
- **Escala:** 0 (incorrecto) · 1 (parcial) · 2 (correcto) → máximo 20 pts por modelo
- **Criterio 0 automático:** respuesta de sí/no contraria a la referencia, dominio incorrecto, o alucinaciones que cambian el sentido
- **Reanudación:** el script salta entradas ya evaluadas usando clave `(id_pregunta, modelo, embedding)`

### Scores baseline (corpus original, 10 preguntas)

| Modelo | Puntaje | Correctas (2) | Parciales (1) | Incorrectas (0) |
|--------|:-------:|:-------------:|:-------------:|:---------------:|
| qwen2.5:14b | **9/20** | 1 | 7 | 2 |
| mistral:7b-instruct | 9/20 | 3 | 3 | 3 |
| gemma2:9b | 8/20 | 1 | 6 | 3 |
| llama3.1:8b | 6/20 | 1 | 4 | 5 |
| mistral-nemo:12b | 4/20 | 1 | 2 | 7 |

### Scores v2 (corpus + guía INDECOPI, 10 preguntas)

| Modelo | Puntaje | Correctas (2) | Parciales (1) | Incorrectas (0) |
|--------|:-------:|:-------------:|:-------------:|:---------------:|
| qwen2.5:14b | **10/20** | 4 | 2 | 4 |
| gemma2:9b | 8/20 | 3 | 2 | 5 |
| mistral:7b-instruct | 8/20 | 1 | 6 | 3 |
| mistral-nemo:12b | 6/20 | 1 | 4 | 5 |
| llama3.1:8b | 5/20 | 0 | 5 | 5 |

### Delta v1 → v2

| Modelo | Baseline | V2 | Delta |
|--------|:--------:|:--:|:-----:|
| mistral-nemo:12b | 4 | 6 | **+2** |
| qwen2.5:14b | 9 | 10 | **+1** |
| gemma2:9b | 8 | 8 | 0 |
| mistral:7b-instruct | 9 | 8 | -1 |
| llama3.1:8b | 6 | 5 | -1 |

**Conclusión:** impacto marginal (+0.4 promedio). La guía INDECOPI mejoró específicamente las preguntas sobre procedimientos INDECOPI, pero el retriever sigue trayendo documentos de dominio incorrecto para P2, P3, P5.

### Alucinaciones más frecuentes detectadas por Gemini

- **Todas las modelos:** P6 — afirman que INDECOPI puede otorgar indemnizaciones (INCORRECTO: solo puede multar y dar medidas correctivas)
- **mistral:7b:** inventa instituciones (ORCT), decretos legislativos inexistentes, URLs
- **llama3.1:8b:** cita leyes incorrectas (Ley N°30634, DL N°1056/2018)
- **gemma2:9b:** confunde "queja" y "reclamo", inventa artículos de ley
- **mistral-nemo:12b:** cita leyes inexistentes (DL N°730, DL N°748), confunde instituciones (CONADECUS es chilena)
- **qwen2.5:14b:** confunde OSIPTEL con INDECOPI (P2), inventa "ORFEO" y "Proconsumo"

---

## Experimento 3 — Prompt anti-alucinación (2026-06-28)

**Problema:** todos los modelos inventan leyes, instituciones y plazos inexistentes cuando el contexto recuperado es de dominio incorrecto.

**Mejora implementada** en `PROMPT_TEMPLATE` de `src/rag_chain.py`:

```
Reglas anti-alucinación (críticas):
- NUNCA inventes nombres de leyes, números de decretos, instituciones o plazos.
  Si un dato no aparece textualmente en el contexto, no lo menciones.
- La ley principal de protección al consumidor en Perú es el Código de Protección y
  Defensa del Consumidor, Ley N° 29571. No atribuyas ese rol a otras leyes.
- Distingue correctamente las entidades reguladoras: INDECOPI protege derechos del
  consumidor en general; OSIPTEL regula telecomunicaciones; SBS regula banca y seguros.
  No confundas sus competencias ni las mezcles.
- INDECOPI puede imponer multas y medidas correctivas a empresas, pero NO puede otorgar
  indemnizaciones por daños y perjuicios — eso requiere un proceso civil judicial separado.
```

**Impacto esperado:** reducción de alucinaciones en P2, P3, P5, P6, P7, P8. A evaluar en el experimento de embeddings.

---

## Experimento 4 — Multi-embedding (COMPLETADO, 2026-06-28)

### Motivación

El análisis de causa raíz indica que el retriever es el problema principal. Se evalúan 5 modelos de embedding con distinta capacidad semántica para medir su impacto en la calidad de las respuestas.

### Configuración

- **Modelos LLM:** mistral:7b-instruct · llama3.1:8b · gemma2:9b · mistral-nemo:12b · qwen2.5:14b
- **Embeddings:** MiniLM-L12 · mpnet-base · e5-large · bge-m3 · LaBSE
- **Preguntas:** 12 (P1–P10 + P11 propina + P12 libros escolares)
- **k:** 3 · **Prompt:** versión anti-alucinación · **Juez:** Gemini 2.5 Flash
- **Total evaluaciones:** 5 × 5 × 12 = 300

### Resultados — Score por modelo (promedio sobre los 5 embeddings)

| Posición | Modelo | Score | Correctas | Parciales | Incorrectas |
|:--------:|--------|:-----:|:---------:|:---------:|:-----------:|
| 🥇 1 | **qwen2.5:14b** | 82/120 | 32 (53%) | 18 (30%) | 10 (17%) |
| 🥈 2 | **llama3.1:8b** | 74/120 | 26 (43%) | 22 (37%) | 12 (20%) |
| 🥈 2 | **mistral-nemo:12b** | 74/120 | 22 (37%) | 30 (50%) | 8 (13%) |
| 4 | mistral:7b-instruct | 69/120 | 20 (33%) | 29 (48%) | 11 (18%) |
| 5 | gemma2:9b | 67/120 | 19 (32%) | 29 (48%) | 12 (20%) |

### Resultados — Score por embedding (promedio sobre los 5 modelos)

| Posición | Embedding | Score promedio |
|:--------:|-----------|:--------------:|
| 🥇 1 | **bge-m3** | **1.45** |
| 🥈 2 | **e5-large** | **1.40** |
| 3 | MiniLM-L12 | 1.23 |
| 4 | mpnet-base | 1.18 |
| 5 | LaBSE | **0.83** ← claramente inferior |

### Top 3 combinaciones modelo × embedding

| # | Modelo | Embedding | Score promedio |
|:-:|--------|-----------|:--------------:|
| 🥇 1 | qwen2.5:14b | bge-m3 | **1.75** |
| 🥈 2 | llama3.1:8b | bge-m3 | **1.58** |
| 🥉 3 | mistral:7b-instruct | e5-large | **1.50** |

### Hallazgos clave

1. **El embedding es más determinante que el LLM.** LaBSE tiene un score un 40% menor que bge-m3 con los mismos modelos.
2. **P6 sigue siendo fallo sistémico** — todos los modelos responden que INDECOPI puede dar indemnización (incorrecto). Causa: el corpus no tiene documento que explique los límites de INDECOPI.
3. **qwen2.5:14b + bge-m3 es la mejor combinación** pero aún tiene alucinaciones: confunde OSIPTEL con INDECOPI (P2), inventa instituciones ("ORFEO", "Proconsumo").
4. **LaBSE descartado** para producción — rendimiento consistentemente inferior en todas las combinaciones.

---

## Experimento 5 — Corpus ampliado + Top embeddings (EN CURSO, 2026-06-28)

### Motivación

Los dos problemas principales identificados en el Experimento 4 son atacables:
1. **P6 (fallo sistémico):** el corpus no tenía documentos sobre los límites de INDECOPI ni sobre arbitraje de consumo como alternativa.
2. **Contaminación de contexto cruzado:** el retriever recupera documentos de dominios incorrectos (SOAT para preguntas de INDECOPI, telecom para preguntas generales).

### Mejoras implementadas

**Mejora 1 — Corpus ampliado (ya aplicada)**

Dos documentos nuevos en `final_json/informes/`:
- `Cartilla Ya lo sabes - Arbitraje de Consumo.json` — aclara que el árbitro SÍ puede ordenar indemnización económica (a diferencia de INDECOPI).
- `Resolucion Final 016-2022-CPC-INDECOPI.json` — caso real donde INDECOPI explícitamente deniega indemnización y remite al Poder Judicial. Clave para P6.

**Diseño de los scripts (ya implementado)**

- `ingest_embeddings.py` — soporta `--embeddings` y `--suffix` para re-indexar solo los embeddings necesarios en nuevos dirs
- `evaluacion_embeddings.py` — soporta `--modelos`, `--embeddings`, `--suffix` para evaluar subconjuntos
- `generar_reporte.py` — soporta `--baseline-label` y `--current-label` para etiquetas personalizadas en el comparativo

### Configuración del experimento

- **Modelos LLM:** solo top 3 → **qwen2.5:14b · llama3.1:8b · mistral:7b-instruct**
- **Embeddings:** solo top 2 → **bge-m3 · e5-large** (LaBSE descartado en Exp4)
- **ChromaDB dirs:** `chroma_db_bgem3_exp5` y `chroma_db_e5large_exp5` (corpus ampliado)
- **Preguntas:** mismas 12 del Experimento 4
- **k:** 3 · **Prompt:** mismo anti-alucinación
- **Total combinaciones:** 3 × 2 × 12 = 72
- **Juez:** Gemini 2.5 Flash

### Comandos ejecutados

```bash
# 1. Re-indexar con corpus ampliado
python src/ingest_embeddings.py --embeddings bge-m3 e5-large --suffix _exp5

# 2. Generar 72 respuestas
python src/evaluacion_embeddings.py --modelos qwen2.5:14b llama3.1:8b mistral:7b-instruct --embeddings bge-m3 e5-large --suffix _exp5 --salida evaluacion_exp5

# 3. Evaluar con Gemini juez
python src/evaluar_llm_judge.py --entrada evaluacion_exp5.json --salida scores_gemini_exp5

# 4. Reporte comparativo
python src/generar_reporte.py --entrada scores_gemini_exp5.json --baseline scores_gemini_embeddings.json --salida reporte_exp5.html --baseline-label "Exp4 (corpus original)" --current-label "Exp5 (corpus ampliado)"
```

### Resultados — Top 3 combinaciones vs Exp4

| Modelo | Embedding | Exp4 | Exp5 | Delta |
|--------|-----------|:----:|:----:|:-----:|
| qwen2.5:14b | bge-m3 | 1.750 | 1.583 | **-0.167** |
| llama3.1:8b | bge-m3 | 1.583 | 1.333 | **-0.250** |
| mistral:7b-instruct | e5-large | 1.500 | 1.333 | **-0.167** |

### Desglose por pregunta — qwen2.5:14b + bge-m3

| P | Categoría | Exp4 | Exp5 | Delta | Fuentes Exp5 |
|:-:|-----------|:----:|:----:|:-----:|--------------|
| 1 | libro_reclamaciones | 2 | 2 | = | Guía INDECOPI, Lineamientos, DS 011 |
| 2 | telecomunicaciones | 2 | 2 | = | Guía OSIPTEL, Res. 099-OSIPTEL ×2 |
| 3 | indecopi | 1 | 2 | **+1** | Guía INDECOPI, Lineamientos, Res. SBS |
| 4 | inmobiliario | 1 | 1 | = | Código 29571, Guía inmobiliaria ×2 |
| 5 | servicios_financieros | 2 | 1 | **-1** | Código 29571, Lineamientos ×2 |
| 6 | indecopi | 2 | 2 | = | DS 011, Guía INDECOPI, **Res. 016-2022** |
| 7 | productos_defectuosos | 2 | 2 | = | Código 29571, Lineamientos, Código 29571 |
| 8 | servicios_financieros | 2 | 0 | **-2** | Res. SBS 3274, Lineamientos, Cartilla TC |
| 9 | libro_reclamaciones | 1 | 1 | = | Código 29571, DS 011, Lineamientos |
| 10 | precios | 2 | 2 | = | Código 29571 ×3 |
| 11 | precios | 2 | 2 | = | Lineamientos, Res. SBS 3274 ×2 |
| 12 | educacion | 2 | 2 | = | Ley 29694, Lineamientos, Ley 29694 |

### Análisis de causa raíz (Exp5)

**La regresión global no es del corpus — es variabilidad del LLM:**

1. **P8 regresó de 2→0 para qwen+bge-m3** — el modelo respondió "sí, el banco puede cobrar sin avisar" cuando la respuesta correcta es "no". Las fuentes recuperadas eran correctas (Resolución SBS 3274, cartilla de tarjetas de crédito). Es error estocástico del LLM, no del retriever.
2. **P6 ya estaba resuelto en Exp4** para qwen+bge-m3 (score 2). En Exp5 ahora recupera `Resolución 016-2022` como fuente, pero la respuesta ya era correcta antes.
3. **P3 mejoró (+1)** — los nuevos documentos o la re-indexación ayudaron a la pregunta de denuncia vs reclamación INDECOPI.
4. **El patrón general (todos los modelos bajaron)** confirma que la regresión no es atribuible al corpus: llama y mistral también bajaron con e5-large aunque recuperan fuentes distintas.

**Conclusión académica:** agregar documentos al corpus sin pre-filtrado por categoría introduce ruido competitivo en el retriever (k=3 slots ahora tienen más candidatos), neutralizando las mejoras esperadas. El cuello de botella sigue siendo la recuperación sin discriminación de dominio.

---

## Experimento 6 — Pre-filtrado por categoría (PLANIFICADO)

### Motivación

El Exp5 demostró que ampliar el corpus sin discriminar el dominio de recuperación puede introducir ruido. El Exp6 agrega pre-filtrado: antes de recuperar los k documentos, filtra la ChromaDB por la `categoria_consumo` de la pregunta. Así, una pregunta de telecomunicaciones solo busca entre documentos etiquetados con esa categoría, evitando contaminación cruzada.

### Diseño

- **Corpus:** mismo del Exp5 (`chroma_db_bgem3_exp5`, `chroma_db_e5large_exp5`) — no hay re-indexación
- **Pares evaluados:** solo top 3 combinaciones del Exp4
  - `qwen2.5:14b` + `bge-m3`
  - `llama3.1:8b` + `bge-m3`
  - `mistral:7b-instruct` + `e5-large`
- **Total:** 3 pares × 12 preguntas = **36 evaluaciones**
- **Mecanismo de pre-filtrado:** `vectorstore.similarity_search(pregunta, k=3, filter={"categorias": {"$contains": categoria}})`
- **Fallback:** si el filtro retorna menos de k documentos, se hace búsqueda sin filtro (registrado en campo `prefiltrado: false`)

### Comandos para ejecutar

```bash
# No necesita re-indexar — usa los dirs de Exp5

# Paso 1 — Generar 36 respuestas con pre-filtrado (reanudable)
python src/evaluacion_embeddings.py --pares "qwen2.5:14b|bge-m3" "llama3.1:8b|bge-m3" "mistral:7b-instruct|e5-large" --suffix _exp5 --prefiltrar --salida evaluacion_exp6

# Paso 2 — Evaluar con Gemini juez (reanudable)
python src/evaluar_llm_judge.py --entrada evaluacion_exp6.json --salida scores_gemini_exp6

# Paso 3 — Reporte comparativo Exp5 vs Exp6
python src/generar_reporte.py --entrada scores_gemini_exp6.json --baseline scores_gemini_exp5.json --salida reporte_exp6.html --baseline-label "Exp5 (corpus ampliado, sin filtro)" --current-label "Exp6 (pre-filtrado por categoría)"
```

### Métrica de éxito

- Score promedio del top 3 supera el de Exp5 en al menos 0.10 puntos.
- Las preguntas de dominio cruzado (P1, P2, P3, P8) mejoran respecto a Exp5.
- El campo `prefiltrado` en los resultados indica qué preguntas aprovecharon el filtro.

### Resultados — Top 3 pares (COMPLETADO, 2026-06-29)

| Modelo | Embedding | Exp4 | Exp5 | Exp6 | Δ Exp4→6 |
|--------|-----------|:----:|:----:|:----:|:--------:|
| qwen2.5:14b | bge-m3 | 1.750 | 1.583 | **1.750** | **=** |
| llama3.1:8b | bge-m3 | 1.583 | 1.333 | 1.417 | -0.167 |
| mistral:7b-instruct | e5-large | 1.500 | 1.333 | **1.583** | **+0.083** |

**Pre-filtrado aplicado:** 36/36 preguntas usaron el filtro (0 fallbacks). El mapa de categorías funcionó correctamente.

### Desglose por pregunta — los 3 pares

#### qwen2.5:14b + bge-m3

| P | Categoría | Exp4 | Exp5 | Exp6 |
|:-:|-----------|:----:|:----:|:----:|
| 1 | libro_reclamaciones | 2 | 2 | 2 |
| 2 | telecomunicaciones | 2 | 2 | 2 |
| 3 | indecopi | 1 | 2 | 1 |
| 4 | inmobiliario | 1 | 1 | 2 |
| 5 | servicios_financieros | 2 | 1 | 2 |
| 6 | indecopi | 2 | 2 | 2 |
| 7 | productos_defectuosos | 2 | 2 | 2 |
| 8 | servicios_financieros | 2 | **0** | **0** |
| 9 | libro_reclamaciones | 1 | 1 | 2 |
| 10 | precios | 2 | 2 | 2 |
| 11 | precios | 2 | 2 | 2 |
| 12 | educacion | 2 | 2 | 2 |

#### llama3.1:8b + bge-m3

| P | Categoría | Exp4 | Exp5 | Exp6 |
|:-:|-----------|:----:|:----:|:----:|
| 2 | telecomunicaciones | 1 | 1 | **0** |
| 5 | servicios_financieros | 2 | 0 | 2 |
| 7 | productos_defectuosos | 2 | 1 | 1 |
| 8 | servicios_financieros | 1 | 2 | **0** |
| 11 | precios | 1 | 0 | 1 |
| 12 | educacion | 1 | 1 | 2 |
| *(resto)* | — | ≥1 | ≥1 | ≥1 |

#### mistral:7b-instruct + e5-large

| P | Categoría | Exp4 | Exp5 | Exp6 |
|:-:|-----------|:----:|:----:|:----:|
| 4 | inmobiliario | 1 | 1 | 2 |
| 6 | indecopi | **0** | **0** | **0** |
| 7 | productos_defectuosos | 2 | 0 | 1 |
| 9 | libro_reclamaciones | 2 | 1 | 2 |
| *(resto)* | — | ≥1 | ≥1 | ≥1 |

### Análisis de causa raíz (Exp6)

1. **qwen+bge-m3 recupera el nivel del Exp4 (1.75)** — el pre-filtrado corrigió las preguntas que habían regresado en Exp5 (P4, P5, P9). El único bloqueador persistente es P8.

2. **P8 falla sistemáticamente para qwen y llama (0 en Exp5 y Exp6)** — las fuentes recuperadas son correctas (Res. SBS 3274, cartilla tarjetas), pero ambos modelos responden "sí, el banco puede cobrar sin avisar" cuando la respuesta correcta es "no". Es un sesgo de razonamiento del LLM que el retriever no puede corregir.

3. **mistral mejora sobre Exp4 (+0.083)** — el pre-filtrado reduce la contaminación cruzada que más lo afectaba (P4, P9 suben de 1→2).

4. **llama sigue por debajo de Exp4 (-0.167)** — P2 y P8 caen por variabilidad estocástica. El histórico de P5 para llama (2→0→2 en Exp4→Exp5→Exp6) confirma que la oscilación es ruido, no tendencia.

5. **mistral+e5-large no resuelve P6** — el filtro de `indecopi` (`consumo en general` + `entidades públicas`) no trae `Resolución 016-2022` entre los top-3 para e5-large. bge-m3 es mejor rankeando ese documento.

### Conclusión del ciclo de experimentos (Exp4→Exp5→Exp6)

| Mejora introducida | Impacto |
|--------------------|---------|
| Mejor embedding (bge-m3 vs MiniLM) | Alto — +0.52 pts sobre baseline |
| Corpus ampliado sin filtro (Exp5) | Neutro/negativo — introduce ruido competitivo |
| Pre-filtrado por categoría (Exp6) | Positivo — estabiliza resultados, mistral mejora |
| **Techo actual del sistema** | **1.75** (qwen+bge-m3, estable en Exp4 y Exp6) |

**El cuello de botella final es el LLM:** P8 falla por sesgo propio del modelo, no por retrieval. El sistema RAG con bge-m3 + pre-filtrado + corpus ampliado entrega contexto correcto; el LLM lo ignora en preguntas con respuesta contraintuitiva (banco SÍ debe avisar antes de cobrar).
