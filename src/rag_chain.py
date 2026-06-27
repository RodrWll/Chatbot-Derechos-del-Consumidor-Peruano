"""
Cadena RAG reutilizable. Importar desde notebooks o app.py:
    from src.rag_chain import construir_cadena

Uso básico:
    chain = construir_cadena()
    resultado = chain.invoke({"query": "¿qué cubre el SOAT?"})
    print(resultado["result"])
    for doc in resultado["source_documents"]:
        print(doc.metadata["nombre_doc"])
"""

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

CHROMA_DIR = "./chroma_db"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

PROMPT_TEMPLATE = """Eres un asistente especializado en derechos del consumidor peruano.
Tu misión es ayudar a ciudadanos comunes a entender sus derechos de forma clara y práctica.

Reglas:
- Responde SOLO con información del contexto proporcionado.
- Usa lenguaje simple, sin tecnicismos legales.
- Si el usuario pregunta por un derecho, explica qué puede hacer en la práctica.
- Si la pregunta no está relacionada con derechos del consumidor peruano, indica amablemente \
que solo puedes ayudar con ese tema.
- Al final de la respuesta, indica la fuente legal entre paréntesis.

Contexto legal:
{context}

Pregunta del ciudadano: {question}

Respuesta en lenguaje claro y accesible:"""


def construir_cadena(
    model: str = "mistral:7b-instruct",
    k: int = 4,
    chroma_dir: str = CHROMA_DIR,
) -> RetrievalQA:
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": device},
    )
    vectorstore = Chroma(
        persist_directory=chroma_dir,
        embedding_function=embeddings,
    )
    llm = OllamaLLM(model=model)
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=PROMPT_TEMPLATE,
    )
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": k}),
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True,
    )


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
        resultado = chain.invoke({"query": pregunta})
        print(formatear_respuesta(resultado))
