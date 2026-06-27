"""
Cadena RAG reutilizable. Importar desde notebooks o app.py:
    from src.rag_chain import construir_cadena

Uso básico:
    chain = construir_cadena()
    resultado = chain.invoke("¿qué cubre el SOAT?")
    print(resultado["result"])
    for doc in resultado["source_documents"]:
        print(doc.metadata["nombre_doc"])
"""

import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

CHROMA_DIR = "./chroma_db"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

PROMPT_TEMPLATE = """Eres un asistente especializado en derechos del consumidor peruano.
Tu misión es ayudar a ciudadanos comunes a entender sus derechos de forma clara y práctica.

Reglas:
- Responde SOLO con información del contexto que sea DIRECTAMENTE relevante a la pregunta.
- Si un fragmento del contexto habla de un tema distinto al preguntado (por ejemplo, inmuebles \
cuando se pregunta por productos en general), IGNÓRALO completamente.
- Usa lenguaje simple, sin tecnicismos legales, en español peruano.
- Si el usuario pregunta por un derecho, explica qué puede hacer en la práctica paso a paso.
- Si la pregunta no está relacionada con derechos del consumidor peruano, indícalo amablemente.
- Al final cita solo las fuentes legales que realmente usaste en tu respuesta.

Contexto legal:
{context}

Pregunta del ciudadano: {question}

Respuesta clara, práctica y en lenguaje simple:"""


def _formatear_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def construir_cadena(
    model: str = "mistral:7b-instruct",
    k: int = 4,
    chroma_dir: str = CHROMA_DIR,
):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": device},
    )
    vectorstore = Chroma(
        persist_directory=chroma_dir,
        embedding_function=embeddings,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    llm = OllamaLLM(model=model)
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=PROMPT_TEMPLATE,
    )

    def invoke(query: str) -> dict:
        docs = retriever.invoke(query)
        context = _formatear_docs(docs)
        respuesta = llm.invoke(prompt.format(context=context, question=query))
        return {"result": respuesta, "source_documents": docs}

    return invoke


def formatear_respuesta(resultado: dict) -> str:
    respuesta = resultado["result"]
    fuentes = {doc.metadata["nombre_doc"] for doc in resultado.get("source_documents", [])}
    if fuentes:
        respuesta += "\n\n**Fuentes consultadas:** " + " | ".join(sorted(fuentes))
    return respuesta


if __name__ == "__main__":
    print("Cargando cadena RAG...")
    chain = construir_cadena()

    preguntas_prueba = [
        "¿Cuáles son mis derechos si un producto que compré está defectuoso?",
        "¿Cómo presento una queja ante INDECOPI?",
        "¿Qué cubre el SOAT en caso de accidente?",
        "¿Tengo derecho a atención preferente si soy adulto mayor?",
    ]

    for pregunta in preguntas_prueba:
        print("\n" + "=" * 60)
        print(f"Pregunta: {pregunta}")
        print("-" * 60)
        resultado = chain(pregunta)
        print(formatear_respuesta(resultado))
