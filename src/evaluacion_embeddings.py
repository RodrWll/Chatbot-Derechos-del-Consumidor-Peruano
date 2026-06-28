"""
Evaluacion multi-embedding: 5 embeddings x 5 modelos LLM x 10 preguntas = 250 respuestas.

Uso:
    python src/evaluacion_embeddings.py
    python src/evaluacion_embeddings.py --k 3 --salida evaluacion_embeddings

Reanudacion automatica: si el archivo de salida ya existe, saltea las combinaciones
(embedding, modelo, id_pregunta) ya evaluadas y continua desde donde quedo.

Requiere haber corrido primero: python src/ingest_embeddings.py
"""

import json
import time
import csv
import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from src.rag_chain import PROMPT_TEMPLATE

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

MODELOS_LLM = [
    "mistral:7b-instruct",
    "llama3.1:8b",
    "gemma2:9b",
    "mistral-nemo:12b",
    "qwen2.5:14b",
]

CAMPOS_CSV = [
    "embedding", "embedding_modelo", "id_pregunta", "categoria",
    "modelo", "pregunta", "respuesta", "respuesta_referencia",
    "fuentes", "tiempo_segundos", "num_docs_recuperados",
]


def cargar_preguntas(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Cargadas {len(data)} preguntas desde '{path}'.")
    return data


def cargar_progreso(salida_json: str) -> tuple[list[dict], set]:
    if not os.path.exists(salida_json):
        return [], set()
    with open(salida_json, encoding="utf-8") as f:
        existentes = json.load(f)
    ya_hechos = {
        (r["id_pregunta"], r["modelo"], r["embedding"])
        for r in existentes
    }
    print(f"Progreso previo cargado: {len(ya_hechos)} combinaciones ya evaluadas.")
    return existentes, ya_hechos


def guardar(resultados: list[dict], json_path: str, csv_path: str) -> None:
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        writer.writeheader()
        for r in resultados:
            row = r.copy()
            row["fuentes"] = " | ".join(r["fuentes"])
            writer.writerow(row)


def parsear_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluacion multi-embedding del chatbot RAG")
    parser.add_argument("--preguntas", default="preguntas_evaluacion.json")
    parser.add_argument("--k", type=int, default=3, help="Documentos recuperados por consulta")
    parser.add_argument("--salida", default="evaluacion_embeddings")
    return parser.parse_args()


def main() -> None:
    args = parsear_args()
    preguntas = cargar_preguntas(args.preguntas)

    salida_json = f"{args.salida}.json"
    salida_csv = f"{args.salida}.csv"

    todos_resultados, ya_hechos = cargar_progreso(salida_json)

    total = len(EMBEDDINGS_CONFIG) * len(MODELOS_LLM) * len(preguntas)
    pendientes = total - len(ya_hechos)
    print(f"Total combinaciones: {total} | Completadas: {len(ya_hechos)} | Pendientes: {pendientes}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo: {device}\n")

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=PROMPT_TEMPLATE,
    )

    for emb_cfg in EMBEDDINGS_CONFIG:
        emb_nombre = emb_cfg["nombre"]
        chroma_dir = emb_cfg["chroma_dir"]

        sqlite_path = Path(chroma_dir) / "chroma.sqlite3"
        if not sqlite_path.exists():
            print(f"\n[SKIP] {emb_nombre}: ChromaDB no encontrada en '{chroma_dir}'.")
            print("       Corre primero: python src/ingest_embeddings.py")
            continue

        print(f"\n{'='*60}")
        print(f"Embedding: {emb_nombre} ({emb_cfg['modelo']})")

        emb_model_kwargs = {"device": device}
        emb_model_kwargs.update(emb_cfg.get("st_kwargs", {}))
        embeddings = HuggingFaceEmbeddings(
            model_name=emb_cfg["modelo"],
            model_kwargs=emb_model_kwargs,
            encode_kwargs={"normalize_embeddings": True},
        )
        vectorstore = Chroma(persist_directory=chroma_dir, embedding_function=embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": args.k})

        for modelo_llm in MODELOS_LLM:
            print(f"\n  LLM: {modelo_llm}")

            # Verificar si todas las preguntas de esta combinacion ya estan hechas
            pendientes_llm = [
                item for item in preguntas
                if (item["id"], modelo_llm, emb_nombre) not in ya_hechos
            ]
            if not pendientes_llm:
                print("  [SKIP] Todas las preguntas ya evaluadas.")
                continue

            try:
                llm = OllamaLLM(model=modelo_llm)
            except Exception as e:
                print(f"  [ERROR] No se pudo cargar '{modelo_llm}': {e}")
                continue

            for item in preguntas:
                pid = item["id"]
                key = (pid, modelo_llm, emb_nombre)

                if key in ya_hechos:
                    continue

                pregunta = item["pregunta"]
                print(f"    [P{pid}] {pregunta[:65]}...", end=" ", flush=True)

                t0 = time.time()
                try:
                    docs = retriever.invoke(pregunta)
                    context = "\n\n".join(doc.page_content for doc in docs)
                    respuesta = llm.invoke(prompt.format(context=context, question=pregunta))
                    elapsed = time.time() - t0

                    fuentes = [doc.metadata.get("nombre_doc", "desconocido") for doc in docs]
                    resultado = {
                        "embedding": emb_nombre,
                        "embedding_modelo": emb_cfg["modelo"],
                        "id_pregunta": pid,
                        "categoria": item.get("categoria", ""),
                        "modelo": modelo_llm,
                        "pregunta": pregunta,
                        "respuesta": respuesta,
                        "respuesta_referencia": item.get("respuesta_referencia", ""),
                        "fuentes": fuentes,
                        "tiempo_segundos": round(elapsed, 2),
                        "num_docs_recuperados": len(fuentes),
                    }
                    todos_resultados.append(resultado)
                    ya_hechos.add(key)
                    print(f"[OK] {elapsed:.1f}s - {len(fuentes)} docs")

                    guardar(todos_resultados, salida_json, salida_csv)

                except Exception as e:
                    elapsed = time.time() - t0
                    print(f"[ERROR] {e}")
                    # No se agrega a ya_hechos para que se reintente en la proxima corrida

    print(f"\n{'='*60}")
    print(f"Evaluacion completada. {len(todos_resultados)} resultados guardados en '{salida_json}'.")

    # Resumen por embedding x modelo
    print(f"\n{'Embedding':<15} {'Modelo':<25} {'Preguntas':>9} {'Tiempo prom':>12} {'Docs prom':>10}")
    print("-" * 75)
    agrupado: dict[tuple, list] = {}
    for r in todos_resultados:
        k = (r["embedding"], r["modelo"])
        agrupado.setdefault(k, []).append(r)
    for (emb, mod), filas in sorted(agrupado.items()):
        n = len(filas)
        t_prom = sum(f["tiempo_segundos"] for f in filas) / n
        d_prom = sum(f["num_docs_recuperados"] for f in filas) / n
        print(f"{emb:<15} {mod:<25} {n:>9} {t_prom:>11.1f}s {d_prom:>9.1f}")


if __name__ == "__main__":
    main()
