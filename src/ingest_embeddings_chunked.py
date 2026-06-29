"""
Indexa el corpus final_json_chunked/ con modelos de embedding.
Version adaptada de ingest_embeddings.py para el corpus pre-chunkeado por el equipo.

Diferencias respecto a ingest_embeddings.py:
  - Lee de final_json_chunked/ (chunks con max 400 palabras)
  - Normaliza categoria_consumo: [["valor"]] -> "valor"
  - Filtra chunks con menos de MIN_PALABRAS palabras (fragmentos sin informacion)
  - Los ChromaDB se crean con sufijo _chunked por defecto

Ejecutar antes de evaluar:
    python src/ingest_embeddings_chunked.py --embeddings bge-m3

Para indexar los embeddings del top-3 de experimentos anteriores:
    python src/ingest_embeddings_chunked.py --embeddings bge-m3 e5-large

Opciones:
    --embeddings bge-m3 e5-large   # indexar solo esos embeddings
    --suffix _chunked              # sufijo (default: _chunked)
    --min-palabras 30              # filtrar chunks con menos de N palabras (default: 30)
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

CORPUS_DIR = "final_json_chunked"
DEFAULT_SUFFIX = "_chunked"
MIN_PALABRAS_DEFAULT = 30

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


def normalizar_categoria(raw: object) -> list[str]:
    """
    Maneja los dos formatos posibles de categoria_consumo:
      - Corpus original:  "telecomunicaciones"  o  ["telecomunicaciones"]
      - Corpus chunked:   [["telecomunicaciones"]]  (lista anidada)
    Devuelve siempre una lista plana de strings.
    """
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        plana = []
        for item in raw:
            if isinstance(item, list):
                plana.extend(str(x) for x in item)
            else:
                plana.append(str(item))
        return plana
    return [str(raw)]


def cargar_documentos(corpus_dir: str, min_palabras: int) -> tuple[list[Document], dict]:
    archivos = glob.glob(f"{corpus_dir}/**/*.json", recursive=True)
    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos JSON en: {corpus_dir}")

    docs = []
    stats = {"total": 0, "filtrados_cortos": 0, "archivos": len(archivos)}

    for path in tqdm(archivos, desc="Cargando JSONs"):
        with open(path, encoding="utf-8") as f:
            entradas = json.load(f)
        for d in entradas:
            stats["total"] += 1
            texto = d.get("texto", "")
            if len(texto.split()) < min_palabras:
                stats["filtrados_cortos"] += 1
                continue
            cats = normalizar_categoria(d.get("categoria_consumo"))
            docs.append(Document(
                page_content=texto,
                metadata={
                    "nombre_doc": d.get("nombre_doc", ""),
                    "tipo_doc":   d.get("tipo_doc", ""),
                    "seccion":    d.get("capitulo_seccion", ""),
                    "categorias": ", ".join(cats),
                    "source":     d.get("source", ""),
                    "id":         str(d.get("id", "")),
                }
            ))

    return docs, stats


def indexar(docs: list[Document], config: dict, device: str) -> None:
    nombre = config["nombre"]
    modelo = config["modelo"]
    chroma_dir = config["chroma_dir"]

    print(f"\n{'='*60}")
    print(f"Embedding : {nombre}")
    print(f"Modelo    : {modelo}")
    print(f"ChromaDB  : {chroma_dir}")

    if chroma_ya_indexada(chroma_dir):
        print("[SKIP] ChromaDB ya existe con datos -- saltando.")
        return

    print("Cargando modelo de embedding (puede descargar ~500 MB la primera vez)...")
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
    parser = argparse.ArgumentParser(
        description="Indexa corpus chunked con modelos de embedding"
    )
    parser.add_argument(
        "--embeddings", nargs="+",
        help="Nombres de embeddings a indexar (default: todos). Ej: bge-m3 e5-large",
    )
    parser.add_argument(
        "--suffix", default=DEFAULT_SUFFIX,
        help=f"Sufijo para los dirs ChromaDB (default: {DEFAULT_SUFFIX}). "
             "Ej: _chunked crea chroma_db_bgem3_chunked",
    )
    parser.add_argument(
        "--min-palabras", type=int, default=MIN_PALABRAS_DEFAULT,
        dest="min_palabras",
        help=f"Filtrar chunks con menos de N palabras (default: {MIN_PALABRAS_DEFAULT})",
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

    configs = [{**c, "chroma_dir": c["chroma_dir"] + args.suffix} for c in configs]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo   : {device}")
    print(f"Corpus        : {CORPUS_DIR}/")
    print(f"Embeddings    : {[c['nombre'] for c in configs]}")
    print(f"Sufijo dirs   : {args.suffix}")
    print(f"Filtro minimo : {args.min_palabras} palabras")

    print("\nCargando corpus chunked...")
    docs, stats = cargar_documentos(CORPUS_DIR, args.min_palabras)
    print(f"Chunks totales en corpus : {stats['total']}")
    print(f"Filtrados (<{args.min_palabras} palabras) : {stats['filtrados_cortos']}")
    print(f"Documentos a indexar     : {len(docs)}")

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
