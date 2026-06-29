---
title: Chatbot Derechos del Consumidor Peru
emoji: ⚖️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: mit
---

# Chatbot de Derechos del Consumidor Peruano

Chatbot académico que simplifica textos legales sobre derechos del consumidor en Perú
para que ciudadanos comunes los entiendan. Usa arquitectura RAG (Retrieval-Augmented Generation).

## Tecnología

- **LLM:** llama-3.1-8b via [Groq API](https://console.groq.com) (gratuito)
- **Embeddings:** BAAI/bge-m3 (1024 dims)
- **Base de conocimiento:** Corpus legal peruano — leyes, normas reglamentarias e informes INDECOPI/SPIJ
- **Framework:** LangChain + ChromaDB + Streamlit

## Configuración requerida

Este Space requiere configurar **`GROQ_API_KEY`** como Secret:

1. Ve a Settings > Secrets del Space
2. Agrega `GROQ_API_KEY` con tu clave de [console.groq.com](https://console.groq.com)

## Proyecto académico

Curso de Procesamiento de Lenguaje Natural — 10mo ciclo.
Score evaluado: ~19/24 con llama3.1:8b + bge-m3 + prompt anti-alucinación v3.
