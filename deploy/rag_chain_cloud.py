"""
Cadena RAG para HuggingFace Spaces.
LLM: Groq API (llama-3.1-8b-instant)
Embeddings: BAAI/bge-m3 (CPU)
"""

import os
from typing import Optional

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

CHROMA_DIR = "./chroma_db_bgem3_exp5"
EMBED_MODEL = "BAAI/bge-m3"
GROQ_MODEL = "llama-3.1-8b-instant"
MAX_HISTORIAL = 3  # ultimas N turnos incluidos en el contexto de memoria

PROMPT_TEMPLATE = """Eres un asistente especializado en derechos del consumidor peruano.
Tu mision es ayudar a ciudadanos comunes a entender sus derechos de forma clara y practica.

Reglas de contenido:
- Responde SOLO con informacion del contexto que sea DIRECTAMENTE relevante a la pregunta.
- Si un fragmento del contexto habla de un tema distinto al preguntado, IGNORALO completamente.
- Si el contexto no contiene informacion suficiente para responder, di exactamente: \
"No tengo informacion suficiente en mi base de datos para responder esto con certeza."
- Usa lenguaje simple, sin tecnicismos legales, en espanol peruano.
- Si el usuario pregunta por un derecho, explica que puede hacer en la practica paso a paso.
- Si la pregunta no esta relacionada con derechos del consumidor peruano, indicalo amablemente.
- Al final cita SOLO las fuentes que aparecen en el contexto y que realmente usaste.

Reglas anti-alucinacion (criticas):
- NUNCA inventes nombres de leyes, numeros de decretos, instituciones o plazos. \
Si un dato no aparece textualmente en el contexto, no lo menciones.
- La ley principal de proteccion al consumidor en Peru es el Codigo de Proteccion y \
Defensa del Consumidor, Ley N 29571. No atribuyas ese rol a otras leyes.
- Distingue correctamente las entidades reguladoras: INDECOPI protege derechos del \
consumidor en general; OSIPTEL regula telecomunicaciones; SBS regula banca y seguros. \
No confundas sus competencias ni las mezcles.
- INDECOPI puede imponer multas y medidas correctivas a empresas, pero NO puede otorgar \
indemnizaciones por danos y perjuicios — eso requiere un proceso civil judicial separado.
- Los bancos y entidades financieras estan OBLIGADOS a notificar previamente al usuario \
antes de cobrar cualquier nueva comision o cargo en tarjetas de credito o cuentas. \
Es INCORRECTO afirmar que pueden hacerlo sin previo aviso.
{historial}
Contexto legal:
{context}

Pregunta del ciudadano: {question}

Respuesta clara, practica y en lenguaje simple:"""


def _formatear_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def construir_cadena(k: int = 3, chroma_dir: str = CHROMA_DIR):
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu", "model_kwargs": {"use_safetensors": True}},
        encode_kwargs={"normalize_embeddings": True},
    )
    vectorstore = Chroma(
        persist_directory=chroma_dir,
        embedding_function=embeddings,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    llm = ChatGroq(
        model=GROQ_MODEL,
        api_key=os.getenv("GROQ_API_KEY"),
    )
    prompt = PromptTemplate(
        input_variables=["context", "question", "historial"],
        template=PROMPT_TEMPLATE,
    )

    def invoke(query: str, chat_history: Optional[list] = None) -> dict:
        docs = retriever.invoke(query)
        context = _formatear_docs(docs)
        historial_texto = ""
        if chat_history:
            historial_texto = "\nHistorial de conversacion reciente:\n"
            for humano, ia in chat_history[-MAX_HISTORIAL:]:
                historial_texto += f"Usuario: {humano}\nAsistente: {ia}\n\n"
        ai_message = llm.invoke(
            prompt.format(context=context, question=query, historial=historial_texto)
        )
        respuesta = ai_message.content if hasattr(ai_message, "content") else str(ai_message)
        return {"result": respuesta, "source_documents": docs}

    return invoke
