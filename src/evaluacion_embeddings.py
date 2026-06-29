"""
Evaluacion multi-embedding: N embeddings x M modelos LLM x P preguntas.

Uso basico (Exp4 — 5x5x12):
    python src/evaluacion_embeddings.py

Uso filtrado (Exp5 — top 3 modelos x top 2 embeddings en corpus ampliado):
    python src/evaluacion_embeddings.py \
        --modelos qwen2.5:14b llama3.1:8b mistral:7b-instruct \
        --embeddings bge-m3 e5-large \
        --suffix _exp5 \
        --salida evaluacion_exp5

Uso con pares exactos + pre-filtrado por categoria (Exp6):
    python src/evaluacion_embeddings.py \
        --pares "qwen2.5:14b|bge-m3" "llama3.1:8b|bge-m3" "mistral:7b-instruct|e5-large" \
        --suffix _exp5 \
        --prefiltrar \
        --salida evaluacion_exp6

Reanudacion automatica: si el archivo de salida ya existe, saltea las combinaciones
(embedding, modelo, id_pregunta) ya evaluadas y continua desde donde quedo.

Requiere haber corrido primero: python src/ingest_embeddings.py [--suffix _exp5]
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
    "fuentes", "tiempo_segundos", "num_docs_recuperados", "prefiltrado",
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
    parser.add_argument(
        "--modelos", nargs="+",
        help="Modelos LLM a evaluar (default: todos). Ej: qwen2.5:14b llama3.1:8b",
    )
    parser.add_argument(
        "--embeddings", nargs="+",
        help="Embeddings a evaluar por nombre (default: todos). Ej: bge-m3 e5-large",
    )
    parser.add_argument(
        "--suffix", default="",
        help="Sufijo de directorios ChromaDB (default: vacio). Ej: _exp5",
    )
    parser.add_argument(
        "--pares", nargs="+",
        help="Pares exactos modelo|embedding a evaluar. Ej: \"qwen2.5:14b|bge-m3\" \"llama3.1:8b|bge-m3\"",
    )
    parser.add_argument(
        "--prefiltrar", action="store_true",
        help="Pre-filtrar documentos por categoria de la pregunta antes del retrieval",
    )
    return parser.parse_args()


def main() -> None:
    args = parsear_args()
    preguntas = cargar_preguntas(args.preguntas)

    salida_json = f"{args.salida}.json"
    salida_csv = f"{args.salida}.csv"

    todos_resultados, ya_hechos = cargar_progreso(salida_json)

    # Filtrar embeddings y modelos según args
    emb_configs = list(EMBEDDINGS_CONFIG)
    if args.embeddings:
        nombres_filtro = {n.lower() for n in args.embeddings}
        emb_configs = [c for c in emb_configs if c["nombre"].lower() in nombres_filtro]
        if not emb_configs:
            print(f"[ERROR] Ningun embedding coincide con: {args.embeddings}")
            print(f"Disponibles: {[c['nombre'] for c in EMBEDDINGS_CONFIG]}")
            return

    if args.suffix:
        emb_configs = [{**c, "chroma_dir": c["chroma_dir"] + args.suffix} for c in emb_configs]

    modelos_llm = list(MODELOS_LLM)
    if args.modelos:
        modelos_llm = args.modelos

    # --pares: construir dict {emb_nombre: [modelos]} para iterar solo esas combinaciones
    # Formato de cada par: "modelo|embedding"  (| como separador para evitar conflicto con : del modelo)
    pares_por_emb: dict[str, list[str]] = {}
    if args.pares:
        for par in args.pares:
            if "|" not in par:
                print(f"[ERROR] Formato invalido en --pares: '{par}'. Usa 'modelo|embedding'.")
                return
            modelo_par, emb_par = par.rsplit("|", 1)
            pares_por_emb.setdefault(emb_par, []).append(modelo_par)
        # Asegurar que los embeddings del par están en emb_configs
        emb_nombres_disponibles = {c["nombre"] for c in emb_configs}
        for emb_par in pares_por_emb:
            if emb_par not in emb_nombres_disponibles:
                print(f"[ERROR] Embedding '{emb_par}' de --pares no encontrado en configuracion.")
                print(f"Disponibles: {sorted(emb_nombres_disponibles)}")
                return
        total_pares = sum(len(v) for v in pares_por_emb.values())
        print(f"Pares especificos: {args.pares}")
        total = total_pares * len(preguntas)
    else:
        total = len(emb_configs) * len(modelos_llm) * len(preguntas)
        print(f"Embeddings: {[c['nombre'] for c in emb_configs]}")
        print(f"Modelos LLM: {modelos_llm}")

    pendientes = total - len(ya_hechos)
    print(f"Pre-filtrado por categoria: {'SI' if args.prefiltrar else 'NO'}")
    print(f"Total combinaciones: {total} | Completadas: {len(ya_hechos)} | Pendientes: {pendientes}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo: {device}\n")

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=PROMPT_TEMPLATE,
    )

    for emb_cfg in emb_configs:
        emb_nombre = emb_cfg["nombre"]
        chroma_dir = emb_cfg["chroma_dir"]

        # Si se especificaron pares, saltar embeddings sin modelos asignados
        if pares_por_emb and emb_nombre not in pares_por_emb:
            continue

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

        # Modelos a usar para este embedding
        modelos_este_emb = pares_por_emb[emb_nombre] if pares_por_emb else modelos_llm

        for modelo_llm in modelos_este_emb:
            print(f"\n  LLM: {modelo_llm}")

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
                categoria = item.get("categoria", "")
                print(f"    [P{pid}] {pregunta[:65]}...", end=" ", flush=True)

                t0 = time.time()
                try:
                    # Pre-filtrado por categoría: filtra la ChromaDB antes del retrieval
                    # Si quedan menos de k docs con el filtro, cae a búsqueda sin filtro
                    filtro_aplicado = False
                    if args.prefiltrar and categoria:
                        docs = vectorstore.similarity_search(
                            pregunta, k=args.k,
                            filter={"categorias": {"$contains": categoria}},
                        )
                        if len(docs) >= args.k:
                            filtro_aplicado = True
                        else:
                            docs = retriever.invoke(pregunta)
                    else:
                        docs = retriever.invoke(pregunta)

                    context = "\n\n".join(doc.page_content for doc in docs)
                    respuesta = llm.invoke(prompt.format(context=context, question=pregunta))
                    elapsed = time.time() - t0

                    fuentes = [doc.metadata.get("nombre_doc", "desconocido") for doc in docs]
                    resultado = {
                        "embedding": emb_nombre,
                        "embedding_modelo": emb_cfg["modelo"],
                        "id_pregunta": pid,
                        "categoria": categoria,
                        "modelo": modelo_llm,
                        "pregunta": pregunta,
                        "respuesta": respuesta,
                        "respuesta_referencia": item.get("respuesta_referencia", ""),
                        "fuentes": fuentes,
                        "tiempo_segundos": round(elapsed, 2),
                        "num_docs_recuperados": len(fuentes),
                        "prefiltrado": filtro_aplicado,
                    }
                    todos_resultados.append(resultado)
                    ya_hechos.add(key)
                    filtro_tag = "[F]" if filtro_aplicado else "   "
                    print(f"[OK]{filtro_tag} {elapsed:.1f}s - {len(fuentes)} docs")

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
