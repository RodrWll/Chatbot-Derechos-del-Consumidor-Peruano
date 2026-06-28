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

Archivo: `preguntas_evaluacion.json` — 10 preguntas con respuesta de referencia validada.

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
