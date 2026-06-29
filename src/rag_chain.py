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

CHROMA_DIR = "./chroma_db_bgem3_exp5"
EMBED_MODEL = "BAAI/bge-m3"

PROMPT_TEMPLATE = """Eres un asistente especializado en derechos del consumidor peruano.
Tu misión es ayudar a ciudadanos comunes a entender sus derechos de forma clara y práctica.

Reglas de contenido:
- Responde SOLO con información del contexto que sea DIRECTAMENTE relevante a la pregunta.
- Si un fragmento del contexto habla de un tema distinto al preguntado, IGNÓRALO completamente.
- Si el contexto no contiene información suficiente para responder, di exactamente: \
"No tengo información suficiente en mi base de datos para responder esto con certeza."
- Usa lenguaje simple, sin tecnicismos legales, en español peruano.
- Si el usuario pregunta por un derecho, explica qué puede hacer en la práctica paso a paso.
- Si la pregunta no está relacionada con derechos del consumidor peruano, indícalo amablemente.
- Al final cita SOLO las fuentes que aparecen en el contexto y que realmente usaste.

Reglas anti-alucinación (críticas):
- NUNCA inventes nombres de leyes, números de decretos, instituciones o plazos. \
Si un dato no aparece textualmente en el contexto, no lo menciones.
- La ley principal de protección al consumidor en Perú es el Código de Protección y \
Defensa del Consumidor, Ley N° 29571. No atribuyas ese rol a otras leyes.
- Distingue correctamente las entidades reguladoras: INDECOPI protege derechos del \
consumidor en general; OSIPTEL regula telecomunicaciones; SBS regula banca y seguros. \
No confundas sus competencias ni las mezcles.
- INDECOPI puede imponer multas y medidas correctivas a empresas, pero NO puede otorgar \
indemnizaciones por daños y perjuicios — eso requiere un proceso civil judicial separado.
- Los bancos y entidades financieras están OBLIGADOS a notificar previamente al usuario \
antes de cobrar cualquier nueva comisión o cargo en tarjetas de crédito o cuentas. \
Es INCORRECTO afirmar que pueden hacerlo sin previo aviso.

Contexto legal:
{context}

Pregunta del ciudadano: {question}

Respuesta clara, práctica y en lenguaje simple:"""


def _formatear_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def construir_cadena(
    model: str = "qwen2.5:14b",
    k: int = 3,
    chroma_dir: str = CHROMA_DIR,
):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": device, "use_safetensors": True},
        encode_kwargs={"normalize_embeddings": True},
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
