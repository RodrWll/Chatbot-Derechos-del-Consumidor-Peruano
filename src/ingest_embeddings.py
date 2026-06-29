"""
Indexa el corpus con modelos de embedding, cada uno en su propia ChromaDB.
Ejecutar una sola vez antes de evaluacion_embeddings.py:
    python src/ingest_embeddings.py

Si una ChromaDB ya existe y tiene datos, la saltea automaticamente.

Opciones:
    --embeddings bge-m3 e5-large   # indexar solo esos embeddings
    --suffix _exp5                 # usa dirs chroma_db_bgem3_exp5, chroma_db_e5large_exp5, etc.
"""

import argparse
import json
import glob
import sys
import os
from pathlib import Path

import torch
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CORPUS_DIR = "final_json"

EMBEDDINGS_CONFIG = [
    {
        "nombre": "MiniLM-L12",
        "modelo": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "chroma_dir": "./chroma_db_minilm",
    },
    {
        "nombre": "mpnet-base",
        "modelo": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "chroma_dir": "./chroma_db_mpnet",
    },
    {
        "nombre": "e5-large",
        "modelo": "intfloat/multilingual-e5-large",
        "chroma_dir": "./chroma_db_e5large",
    },
    {
        "nombre": "bge-m3",
        "modelo": "BAAI/bge-m3",
        "chroma_dir": "./chroma_db_bgem3",
        "st_kwargs": {"model_kwargs": {"use_safetensors": True}},
    },
    {
        "nombre": "LaBSE",
        "modelo": "sentence-transformers/LaBSE",
        "chroma_dir": "./chroma_db_labse",
        "st_kwargs": {"model_kwargs": {"use_safetensors": True}},
    },
]


def chroma_ya_indexada(chroma_dir: str) -> bool:
    sqlite_path = Path(chroma_dir) / "chroma.sqlite3"
    return sqlite_path.exists() and sqlite_path.stat().st_size > 100_000


def cargar_documentos() -> list[Document]:
    archivos = glob.glob(f"{CORPUS_DIR}/**/*.json", recursive=True)
    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos JSON en: {CORPUS_DIR}")

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


def indexar(docs: list[Document], config: dict, device: str) -> None:
    nombre = config["nombre"]
    modelo = config["modelo"]
    chroma_dir = config["chroma_dir"]

    print(f"\n{'='*60}")
    print(f"Embedding : {nombre}")
    print(f"Modelo    : {modelo}")
    print(f"ChromaDB  : {chroma_dir}")

    if chroma_ya_indexada(chroma_dir):
        print("[SKIP] ChromaDB ya existe con datos — saltando.")
        return

    print(f"Cargando modelo de embedding (puede descargar ~500 MB la primera vez)...")
    model_kwargs = {"device": device}
    model_kwargs.update(config.get("st_kwargs", {}))
    embeddings = HuggingFaceEmbeddings(
        model_name=modelo,
        model_kwargs=model_kwargs,
        encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
    )

    print(f"Indexando {len(docs)} documentos...")
    Chroma.from_documents(docs, embeddings, persist_directory=chroma_dir)
    print(f"[OK] Indexado en {chroma_dir}")


def parsear_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Indexa corpus con modelos de embedding")
    parser.add_argument(
        "--embeddings", nargs="+",
        help="Nombres de embeddings a indexar (default: todos). Ej: bge-m3 e5-large",
    )
    parser.add_argument(
        "--suffix", default="",
        help="Sufijo para los directorios ChromaDB. Ej: _exp5 crea chroma_db_bgem3_exp5",
    )
    return parser.parse_args()


def main() -> None:
    args = parsear_args()

    configs = list(EMBEDDINGS_CONFIG)
    if args.embeddings:
        nombres_filtro = {n.lower() for n in args.embeddings}
        configs = [c for c in configs if c["nombre"].lower() in nombres_filtro]
        if not configs:
            nombres_disponibles = [c["nombre"] for c in EMBEDDINGS_CONFIG]
            print(f"[ERROR] Ningun embedding coincide con: {args.embeddings}")
            print(f"Disponibles: {nombres_disponibles}")
            return

    if args.suffix:
        configs = [{**c, "chroma_dir": c["chroma_dir"] + args.suffix} for c in configs]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo: {device}")
    print(f"Embeddings a indexar: {[c['nombre'] for c in configs]}")
    if args.suffix:
        print(f"Sufijo de dirs: {args.suffix}")

    print("\nCargando corpus...")
    docs = cargar_documentos()
    print(f"Documentos cargados: {len(docs)}")

    for config in configs:
        indexar(docs, config, device)

    print("\n" + "=" * 60)
    print("Indexacion completada.")
    for cfg in configs:
        status = "[OK]" if chroma_ya_indexada(cfg["chroma_dir"]) else "[FALTA]"
        print(f"  {status} {cfg['nombre']:15} -> {cfg['chroma_dir']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
