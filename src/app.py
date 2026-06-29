"""
Interfaz web del chatbot usando Streamlit.
Ejecutar con:
    streamlit run src/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.rag_chain import construir_cadena, formatear_respuesta

st.set_page_config(
    page_title="Chatbot Derechos del Consumidor Peruano",
    page_icon="⚖️",
    layout="centered",
)


@st.cache_resource(show_spinner="Cargando modelo y base de conocimiento...")
def cargar_cadena(model: str, k: int):
    return construir_cadena(model=model, k=k)


st.title("⚖️ Chatbot de Derechos del Consumidor Peruano")
st.caption("Consulta tus derechos como consumidor en lenguaje simple. Basado en normativa de INDECOPI y SPIJ.")

with st.sidebar:
    st.header("Configuración")
    modelo = st.selectbox(
        "Modelo LLM (Ollama)",
        ["qwen2.5:14b", "gemma2:9b", "llama3.1:8b", "mistral:7b-instruct"],
        index=0,
    )
    k_docs = st.slider("Documentos a recuperar", min_value=2, max_value=8, value=3)
    mostrar_fuentes = st.toggle("Mostrar fuentes legales", value=True)
    st.divider()
    st.markdown("**Preguntas de ejemplo:**")
    ejemplos = [
        "¿Qué hago si me vendieron un producto defectuoso?",
        "¿Cómo presento un reclamo ante INDECOPI?",
        "¿Qué cubre el SOAT en caso de accidente?",
        "¿Tengo derecho a atención preferente si soy adulto mayor?",
        "¿Qué es el libro de reclamaciones?",
    ]
    for ej in ejemplos:
        if st.button(ej, use_container_width=True):
            st.session_state.pregunta_ejemplo = ej

chain = cargar_cadena(modelo, k_docs)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

pregunta_inicial = st.session_state.pop("pregunta_ejemplo", None)
prompt = st.chat_input("Escribe tu consulta sobre derechos del consumidor...") or pregunta_inicial

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando normativa peruana..."):
            resultado = chain(prompt)
            respuesta = resultado["result"]

            if mostrar_fuentes:
                fuentes = {
                    (doc.metadata["nombre_doc"], doc.metadata["seccion"])
                    for doc in resultado.get("source_documents", [])
                }
                if fuentes:
                    respuesta += "\n\n---\n**Fuentes consultadas:**\n"
                    for nombre, seccion in sorted(fuentes):
                        respuesta += f"- *{nombre}* — {seccion}\n"

        st.markdown(respuesta)

    st.session_state.messages.append({"role": "assistant", "content": respuesta})

if st.session_state.messages:
    if st.button("Limpiar conversación", type="secondary"):
        st.session_state.messages = []
        st.rerun()
