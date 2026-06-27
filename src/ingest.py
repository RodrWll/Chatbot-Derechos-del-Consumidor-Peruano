"""
Pipeline de ingestión: carga los JSONs de final_json/ y construye el vector store ChromaDB.
Ejecutar una sola vez (o cuando se actualice el corpus):
    python src/ingest.py
"""

import json
import glob
from pathlib import Path
from tqdm import tqdm

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

CORPUS_DIR = "final_json"
CHROMA_DIR = "./chroma_db"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def cargar_documentos(ruta: str = CORPUS_DIR) -> list[Document]:
    archivos = glob.glob(f"{ruta}/**/*.json", recursive=True)
    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos JSON en: {ruta}")

    docs = []
    for path in tqdm(archivos, desc="Cargando JSONs"):
        with open(path, encoding="utf-8") as f:
            entradas = json.load(f)
        for d in entradas:
            docs.append(Document(
                page_content=d["texto"],
                metadata={
                    "nombre_doc": d.get("nombre_doc", ""),
                    "tipo_doc":   d.get("tipo_doc", ""),
                    "seccion":    d.get("capitulo_seccion", ""),
                    "categorias": ", ".join(d.get("categoria_consumo", [])),
                    "source":     d.get("source", ""),
                    "id":         str(d.get("id", "")),
                }
            ))
    return docs


def construir_vectorstore(docs: list[Document], directorio: str = CHROMA_DIR) -> Chroma:
    print(f"\nGenerando embeddings con: {EMBED_MODEL}")
    print("(Primera ejecución descarga el modelo ~120 MB — puede tardar unos minutos)")

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Usando dispositivo: {device}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": device},
        encode_kwargs={"batch_size": 64},
    )

    print(f"\nIndexando {len(docs)} documentos en ChromaDB...")
    vectorstore = Chroma.from_documents(
        docs,
        embeddings,
        persist_directory=directorio,
    )
    return vectorstore


if __name__ == "__main__":
    print("=" * 60)
    print("  Ingestión del corpus de derechos del consumidor peruano")
    print("=" * 60)

    docs = cargar_documentos()
    print(f"\nDocumentos cargados: {len(docs)}")

    categorias = set()
    for d in docs:
        for cat in d.metadata["categorias"].split(", "):
            if cat:
                categorias.add(cat)
    print(f"Categorías encontradas: {len(categorias)}")
    for cat in sorted(categorias):
        print(f"  - {cat}")

    vs = construir_vectorstore(docs)

    print("\nVerificando vector store...")
    resultado = vs.similarity_search("libro de reclamaciones", k=1)
    print(f"Test OK — documento recuperado: {resultado[0].metadata['nombre_doc']}")

    print("\n" + "=" * 60)
    print(f"  Vector store guardado en: {CHROMA_DIR}")
    print("  Listo para usar con rag_chain.py")
    print("=" * 60)
