"""
Evaluación automática del chatbot RAG con múltiples modelos.

Uso:
    python src/evaluacion.py
    python src/evaluacion.py --preguntas preguntas_evaluacion.json
    python src/evaluacion.py --modelos mistral:7b-instruct gemma2:9b

Salida:
    evaluacion_resultados.json
    evaluacion_resultados.csv
"""

import json
import time
import csv
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag_chain import construir_cadena

MODELOS_DEFAULT = ["mistral:7b-instruct", "llama3.1:8b", "gemma2:9b"]
PREGUNTAS_FILE_DEFAULT = "preguntas_evaluacion.json"

PREGUNTAS_FALLBACK = [
    "¿Cuáles son mis derechos si un producto que compré está defectuoso?",
    "¿Cómo presento una queja ante INDECOPI?",
    "¿Qué cubre el SOAT en caso de accidente de tránsito?",
    "¿Tengo derecho a atención preferente si soy adulto mayor?",
]

CAMPOS_CSV = [
    "id_pregunta",
    "categoria",
    "modelo",
    "pregunta",
    "respuesta",
    "respuesta_referencia",
    "fuentes",
    "tiempo_segundos",
    "num_docs_recuperados",
]


def cargar_preguntas(path: str) -> list[dict]:
    if not os.path.exists(path):
        print(f"[WARNING] No se encontró '{path}'. Usando las 4 preguntas estándar.")
        return [
            {"id": i + 1, "categoria": "general", "pregunta": p, "respuesta_referencia": "", "conceptos_clave": []}
            for i, p in enumerate(PREGUNTAS_FALLBACK)
        ]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Cargadas {len(data)} preguntas desde '{path}'.")
    return data


def evaluar_modelo(modelo: str, preguntas: list[dict], k: int = 3) -> list[dict]:
    print(f"\n{'='*60}")
    print(f"Modelo: {modelo}")
    print("=" * 60)

    try:
        chain = construir_cadena(model=modelo, k=k)
    except Exception as e:
        print(f"  [WARNING] No se pudo cargar el modelo '{modelo}': {e}")
        print("  Saltando este modelo...")
        return []

    resultados = []
    for i, item in enumerate(preguntas, 1):
        pregunta = item["pregunta"]
        print(f"  [{i}/{len(preguntas)}] {pregunta[:70]}...")
        t0 = time.time()
        try:
            resultado = chain(pregunta)
            elapsed = time.time() - t0

            fuentes = [
                doc.metadata.get("nombre_doc", "desconocido")
                for doc in resultado.get("source_documents", [])
            ]

            resultados.append(
                {
                    "id_pregunta": item.get("id", i),
                    "categoria": item.get("categoria", "general"),
                    "modelo": modelo,
                    "pregunta": pregunta,
                    "respuesta": resultado["result"],
                    "respuesta_referencia": item.get("respuesta_referencia", ""),
                    "fuentes": fuentes,
                    "tiempo_segundos": round(elapsed, 2),
                    "num_docs_recuperados": len(fuentes),
                }
            )
            print(f"      [OK] {elapsed:.1f}s - {len(fuentes)} docs recuperados")

        except Exception as e:
            elapsed = time.time() - t0
            print(f"      [ERROR] {e}")
            resultados.append(
                {
                    "id_pregunta": item.get("id", i),
                    "categoria": item.get("categoria", "general"),
                    "modelo": modelo,
                    "pregunta": pregunta,
                    "respuesta": f"ERROR: {e}",
                    "respuesta_referencia": item.get("respuesta_referencia", ""),
                    "fuentes": [],
                    "tiempo_segundos": round(elapsed, 2),
                    "num_docs_recuperados": 0,
                }
            )

    return resultados


def guardar_json(resultados: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\nResultados guardados en: {path}")


def guardar_csv(resultados: list[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        writer.writeheader()
        for r in resultados:
            row = r.copy()
            row["fuentes"] = " | ".join(r["fuentes"])
            writer.writerow(row)
    print(f"Resultados guardados en: {path}")


def parsear_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluación automática del chatbot RAG")
    parser.add_argument(
        "--preguntas",
        default=PREGUNTAS_FILE_DEFAULT,
        help=f"Archivo JSON con preguntas y respuestas de referencia (default: {PREGUNTAS_FILE_DEFAULT})",
    )
    parser.add_argument(
        "--modelos",
        nargs="+",
        default=MODELOS_DEFAULT,
        help="Modelos a evaluar (default: mistral:7b-instruct llama3.1:8b gemma2:9b)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Número de documentos a recuperar por pregunta (default: 3)",
    )
    parser.add_argument(
        "--salida",
        default="evaluacion_resultados",
        help="Prefijo para archivos de salida (default: evaluacion_resultados)",
    )
    return parser.parse_args()


def imprimir_tabla_resumen(resultados: list[dict]) -> None:
    if not resultados:
        print("\nNo hay resultados para mostrar.")
        return

    print("\n" + "=" * 70)
    print("RESUMEN DE EVALUACIÓN")
    print("=" * 70)

    por_modelo: dict[str, list[dict]] = {}
    for r in resultados:
        por_modelo.setdefault(r["modelo"], []).append(r)

    header = f"{'Modelo':<25} {'Preguntas':>9} {'Tiempo prom (s)':>16} {'Docs prom':>10}"
    print(header)
    print("-" * 70)

    for modelo, filas in por_modelo.items():
        n = len(filas)
        tiempo_prom = sum(f["tiempo_segundos"] for f in filas) / n if n else 0
        docs_prom = sum(f["num_docs_recuperados"] for f in filas) / n if n else 0
        print(f"{modelo:<25} {n:>9} {tiempo_prom:>16.1f} {docs_prom:>10.1f}")


def main() -> None:
    args = parsear_args()
    preguntas = cargar_preguntas(args.preguntas)
    todos_resultados: list[dict] = []

    for modelo in args.modelos:
        resultados = evaluar_modelo(modelo, preguntas, k=args.k)
        todos_resultados.extend(resultados)

    if not todos_resultados:
        print("\nNo se obtuvieron resultados. Verifica que Ollama esté corriendo.")
        return

    guardar_json(todos_resultados, f"{args.salida}.json")
    guardar_csv(todos_resultados, f"{args.salida}.csv")
    imprimir_tabla_resumen(todos_resultados)


if __name__ == "__main__":
    main()
