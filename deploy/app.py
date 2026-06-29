import os
import streamlit as st
from rag_chain_cloud import construir_cadena

st.set_page_config(
    page_title="Chatbot Derechos del Consumidor Peruano",
    page_icon="⚖️",
    layout="centered",
)

if not os.getenv("GROQ_API_KEY"):
    st.error(
        "**API Key no configurada.** El administrador del Space debe agregar `GROQ_API_KEY` "
        "en Settings > Secrets antes de usar el chatbot."
    )
    st.stop()


@st.cache_resource(show_spinner="Cargando modelo y base de conocimiento...")
def cargar_cadena():
    return construir_cadena()


st.title("⚖️ Chatbot de Derechos del Consumidor Peruano")
st.caption(
    "Consulta tus derechos como consumidor en lenguaje simple. "
    "Basado en normativa de INDECOPI y SPIJ."
)

with st.sidebar:
    st.header("Configuración")
    st.markdown("**Modelo:** llama3.1:8b (Groq API)")
    st.markdown("**Documentos recuperados:** 3")
    st.divider()
    mostrar_fuentes = st.toggle("Mostrar fuentes legales", value=True)
    usar_memoria = st.checkbox(
        "Memoria conversacional",
        value=False,
        help=(
            "El asistente recordará el contexto de los últimos mensajes de esta sesión. "
            "Útil para preguntas de seguimiento."
        ),
    )
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

chain = cargar_cadena()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    # Lista de tuplas (pregunta_usuario, respuesta_llm) para el contexto de memoria
    st.session_state.chat_history = []

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
            historia = st.session_state.chat_history if usar_memoria else None
            resultado = chain(prompt, chat_history=historia)
            respuesta = resultado["result"]

            if mostrar_fuentes:
                fuentes = {
                    (doc.metadata.get("nombre_doc", ""), doc.metadata.get("seccion", ""))
                    for doc in resultado.get("source_documents", [])
                    if doc.metadata.get("nombre_doc")
                }
                if fuentes:
                    respuesta += "\n\n---\n**Fuentes consultadas:**\n"
                    for nombre, seccion in sorted(fuentes):
                        if seccion:
                            respuesta += f"- *{nombre}* — {seccion}\n"
                        else:
                            respuesta += f"- *{nombre}*\n"

        st.markdown(respuesta)

    st.session_state.messages.append({"role": "assistant", "content": respuesta})
    # Guardar solo la respuesta del LLM (sin el bloque de fuentes) en el historial de memoria
    st.session_state.chat_history.append((prompt, resultado["result"]))

if st.session_state.messages:
    if st.button("Limpiar conversación", type="secondary"):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()
