"""
Evaluación automática de respuestas RAG usando Gemini como juez (LLM-as-a-judge).

Uso:
    python src/evaluar_llm_judge.py
    python src/evaluar_llm_judge.py --entrada evaluacion_resultados.json --salida scores_baseline
    python src/evaluar_llm_judge.py --entrada evaluacion_resultados_v2.json --salida scores_v2

API key — se carga desde .env (recomendado) o variable de entorno:
    Crea un archivo .env en la raíz del proyecto con:
        GOOGLE_API_KEY=tu_clave_aqui
    El archivo .env ya está en .gitignore — nunca se sube a git.
"""

import json
import csv
import os
import time
import argparse

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()  # carga .env automáticamente si existe

MODELO_JUEZ = "gemini-2.0-flash"  # Tier gratuito: 1500 req/día — suficiente para este proyecto
PAUSA_ENTRE_LLAMADAS = 1

PROMPT_JUEZ = """Eres un evaluador experto en derechos del consumidor peruano. \
Tu tarea es calificar la respuesta de un chatbot comparándola con la respuesta de referencia correcta.

PREGUNTA DEL CIUDADANO:
{pregunta}

RESPUESTA DE REFERENCIA (correcta y validada):
{respuesta_referencia}

RESPUESTA DEL CHATBOT A EVALUAR:
{respuesta_modelo}

Evalúa la respuesta del chatbot según estos criterios:

PUNTUACIÓN:
- 2 (CORRECTO): La respuesta cubre los conceptos clave de la referencia sin información incorrecta ni alucinaciones graves.
- 1 (PARCIAL): Cubre algunos conceptos clave pero omite información importante, O tiene imprecisiones menores que no cambian el sentido general.
- 0 (INCORRECTO): La respuesta es incorrecta, contradice la referencia, da una respuesta opuesta (ej: dice "sí" cuando la correcta es "no"), o está basada en información inventada.

CRITERIOS ESPECIALES:
- Si la pregunta tiene una respuesta de sí/no y el chatbot responde lo contrario → 0 automático.
- Si el chatbot inventa nombres de leyes, instituciones o plazos que no existen → penaliza con -1 punto.
- Si el chatbot da información de un dominio incorrecto (ej: habla de salud cuando la pregunta es sobre consumo general) → 0 automático.

Responde ÚNICAMENTE con este JSON, sin texto adicional:
{{
  "score": <0, 1 o 2>,
  "clasificacion": "<correcto|parcial|incorrecto>",
  "conceptos_clave_encontrados": ["<concepto1>", "<concepto2>"],
  "conceptos_clave_faltantes": ["<concepto3>"],
  "alucinaciones": ["<descripción breve de cada alucinación detectada, o lista vacía>"],
  "justificacion": "<explicación en 1-2 oraciones de por qué asignaste ese puntaje>"
}}"""


def configurar_gemini() -> genai.GenerativeModel:
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "Variable de entorno GOOGLE_API_KEY no encontrada.\n"
            "Ejecuta: $env:GOOGLE_API_KEY='tu_clave'  (PowerShell)"
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        MODELO_JUEZ,
        generation_config={"response_mime_type": "application/json"},
    )


def evaluar_respuesta(
    modelo_juez: genai.GenerativeModel,
    pregunta: str,
    respuesta_referencia: str,
    respuesta_modelo: str,
) -> dict:
    prompt = PROMPT_JUEZ.format(
        pregunta=pregunta,
        respuesta_referencia=respuesta_referencia,
        respuesta_modelo=respuesta_modelo,
    )
    respuesta = modelo_juez.generate_content(prompt)
    return json.loads(respuesta.text)


def cargar_resultados(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def guardar_json(resultados: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"Resultados guardados en: {path}")


def guardar_csv(resultados: list[dict], path: str) -> None:
    campos = [
        "id_pregunta", "categoria", "modelo", "pregunta",
        "score_gemini", "clasificacion_gemini",
        "conceptos_encontrados", "conceptos_faltantes",
        "alucinaciones", "justificacion_gemini",
        "tiempo_segundos", "num_docs_recuperados",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for r in resultados:
            writer.writerow({
                "id_pregunta": r.get("id_pregunta"),
                "categoria": r.get("categoria"),
                "modelo": r.get("modelo"),
                "pregunta": r.get("pregunta"),
                "score_gemini": r.get("score_gemini"),
                "clasificacion_gemini": r.get("clasificacion_gemini"),
                "conceptos_encontrados": " | ".join(r.get("conceptos_clave_encontrados", [])),
                "conceptos_faltantes": " | ".join(r.get("conceptos_clave_faltantes", [])),
                "alucinaciones": " | ".join(r.get("alucinaciones", [])),
                "justificacion_gemini": r.get("justificacion_gemini"),
                "tiempo_segundos": r.get("tiempo_segundos"),
                "num_docs_recuperados": r.get("num_docs_recuperados"),
            })
    print(f"CSV guardado en: {path}")


def imprimir_resumen(resultados: list[dict]) -> None:
    print("\n" + "=" * 65)
    print("RESUMEN — SCORES ASIGNADOS POR GEMINI")
    print("=" * 65)

    por_modelo: dict[str, list[dict]] = {}
    for r in resultados:
        por_modelo.setdefault(r["modelo"], []).append(r)

    print(f"\n{'Modelo':<25} {'Puntaje':>8} {'Correctas':>10} {'Parciales':>10} {'Incorrectas':>12}")
    print("-" * 65)

    for modelo, filas in por_modelo.items():
        total = sum(r.get("score_gemini", 0) for r in filas)
        maximo = len(filas) * 2
        correctas = sum(1 for r in filas if r.get("score_gemini") == 2)
        parciales = sum(1 for r in filas if r.get("score_gemini") == 1)
        incorrectas = sum(1 for r in filas if r.get("score_gemini") == 0)
        print(f"{modelo:<25} {total:>4}/{maximo:<3} {correctas:>10} {parciales:>10} {incorrectas:>12}")

    # Alucinaciones detectadas
    todas_alucinaciones = [
        (r["modelo"], r["id_pregunta"], a)
        for r in resultados
        for a in r.get("alucinaciones", [])
        if a
    ]
    if todas_alucinaciones:
        print(f"\n{'ALUCINACIONES DETECTADAS':}")
        print("-" * 65)
        for modelo, pid, alucinacion in todas_alucinaciones:
            print(f"  [{modelo} | P{pid}] {alucinacion}")


def parsear_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluación LLM-as-a-judge con Gemini")
    parser.add_argument(
        "--entrada",
        default="evaluacion_resultados.json",
        help="Archivo JSON con respuestas a evaluar (default: evaluacion_resultados.json)",
    )
    parser.add_argument(
        "--salida",
        default="scores_gemini",
        help="Prefijo para archivos de salida (default: scores_gemini)",
    )
    return parser.parse_args()


def main() -> None:
    args = parsear_args()

    if not os.path.exists(args.entrada):
        print(f"[ERROR] No se encontró el archivo: {args.entrada}")
        return

    print(f"Cargando resultados desde: {args.entrada}")
    resultados = cargar_resultados(args.entrada)
    print(f"Total de respuestas a evaluar: {len(resultados)}")

    print(f"\nConectando con Gemini ({MODELO_JUEZ})...")
    juez = configurar_gemini()

    evaluados: list[dict] = []
    errores = 0

    for i, resultado in enumerate(resultados, 1):
        modelo = resultado.get("modelo", "?")
        pid = resultado.get("id_pregunta", "?")
        pregunta = resultado.get("pregunta", "")
        ref = resultado.get("respuesta_referencia", "")
        respuesta = resultado.get("respuesta", "")

        print(f"  [{i:02d}/{len(resultados)}] {modelo} | P{pid} ...", end=" ", flush=True)

        if respuesta.startswith("ERROR:") or not ref:
            print("saltado (error o sin referencia)")
            resultado_aug = resultado.copy()
            resultado_aug.update({
                "score_gemini": None,
                "clasificacion_gemini": "no_evaluado",
                "conceptos_clave_encontrados": [],
                "conceptos_clave_faltantes": [],
                "alucinaciones": [],
                "justificacion_gemini": "Saltado por error en respuesta original o sin referencia.",
            })
            evaluados.append(resultado_aug)
            continue

        try:
            evaluacion = evaluar_respuesta(juez, pregunta, ref, respuesta)
            resultado_aug = resultado.copy()
            resultado_aug.update({
                "score_gemini": evaluacion.get("score"),
                "clasificacion_gemini": evaluacion.get("clasificacion"),
                "conceptos_clave_encontrados": evaluacion.get("conceptos_clave_encontrados", []),
                "conceptos_clave_faltantes": evaluacion.get("conceptos_clave_faltantes", []),
                "alucinaciones": evaluacion.get("alucinaciones", []),
                "justificacion_gemini": evaluacion.get("justificacion", ""),
            })
            evaluados.append(resultado_aug)
            score = evaluacion.get("score")
            icon = "✅" if score == 2 else "⚠️" if score == 1 else "❌"
            print(f"{icon} score={score}")

        except Exception as e:
            print(f"ERROR: {e}")
            errores += 1
            resultado_aug = resultado.copy()
            resultado_aug.update({
                "score_gemini": None,
                "clasificacion_gemini": "error_api",
                "conceptos_clave_encontrados": [],
                "conceptos_clave_faltantes": [],
                "alucinaciones": [],
                "justificacion_gemini": f"Error al llamar a Gemini: {e}",
            })
            evaluados.append(resultado_aug)

        time.sleep(PAUSA_ENTRE_LLAMADAS)

    guardar_json(evaluados, f"{args.salida}.json")
    guardar_csv(evaluados, f"{args.salida}.csv")
    imprimir_resumen(evaluados)

    if errores:
        print(f"\n[WARNING] {errores} llamadas a Gemini fallaron. Revisa tu API key y cuota.")


if __name__ == "__main__":
    main()
