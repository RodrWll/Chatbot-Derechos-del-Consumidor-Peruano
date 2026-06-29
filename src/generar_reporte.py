"""
Genera reporte.html con los resultados de evaluación LLM-judge.

Uso:
    python src/generar_reporte.py
    python src/generar_reporte.py --entrada scores_gemini_embeddings.json --salida reporte.html
"""

import argparse
import base64
import io
import json
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


COLOR_CORRECTO  = "#27ae60"
COLOR_PARCIAL   = "#e67e22"
COLOR_INCORRECTO = "#e74c3c"
AZUL            = "#2980b9"


# ── Gráficos ─────────────────────────────────────────────────────────────────

def _b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return data


def grafico_llm(df: pd.DataFrame) -> str:
    filas = []
    for modelo, g in df.groupby("modelo"):
        n = len(g)
        filas.append({
            "modelo": modelo,
            "correctas": (g["score_gemini"] == 2).sum() / n * 100,
            "parciales":  (g["score_gemini"] == 1).sum() / n * 100,
            "incorrectas":(g["score_gemini"] == 0).sum() / n * 100,
            "promedio":   g["score_gemini"].mean(),
        })
    r = pd.DataFrame(filas).sort_values("promedio")

    fig, ax = plt.subplots(figsize=(10, max(4, len(r) * 1.0)))
    y = range(len(r))
    ax.barh(list(y), r["correctas"],  color=COLOR_CORRECTO,  label="Correcto")
    ax.barh(list(y), r["parciales"],  left=r["correctas"],   color=COLOR_PARCIAL,   label="Parcial")
    ax.barh(list(y), r["incorrectas"],left=r["correctas"]+r["parciales"],
            color=COLOR_INCORRECTO, label="Incorrecto")
    ax.set_yticks(list(y))
    ax.set_yticklabels(r["modelo"].tolist(), fontsize=11)
    ax.set_xlabel("% de respuestas", fontsize=11)
    ax.set_xlim(0, 100)
    ax.axvline(50, color="gray", linestyle="--", alpha=0.35)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_title("Distribución de scores por modelo LLM", fontsize=13, fontweight="bold", pad=14)
    plt.tight_layout()
    return _b64(fig)


def grafico_embedding(df: pd.DataFrame) -> str:
    r = df.groupby("embedding")["score_gemini"].mean().reset_index()
    r = r.sort_values("score_gemini", ascending=False)

    fig, ax = plt.subplots(figsize=(max(6, len(r) * 1.6), 4))
    bars = ax.bar(r["embedding"], r["score_gemini"], color=AZUL, width=0.5)
    ax.set_ylim(0, 2.3)
    ax.set_ylabel("Score promedio (0–2)", fontsize=11)
    ax.axhline(1, color="gray", linestyle="--", alpha=0.4)
    ax.set_title("Score promedio por modelo de embeddings", fontsize=13, fontweight="bold", pad=14)
    for bar, val in zip(bars, r["score_gemini"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{val:.2f}", ha="center", va="bottom", fontsize=12, fontweight="bold")
    plt.tight_layout()
    return _b64(fig)


def grafico_tres_experimentos(
    df1: pd.DataFrame, df2: pd.DataFrame, df3: pd.DataFrame,
    label1: str, label2: str, label3: str,
) -> str:
    """Gráfico de barras agrupadas: score promedio por modelo en 3 experimentos."""
    modelos = sorted(set(df1["modelo"].unique()) | set(df2["modelo"].unique()) | set(df3["modelo"].unique()))
    s1 = df1.groupby("modelo")["score_gemini"].mean()
    s2 = df2.groupby("modelo")["score_gemini"].mean()
    s3 = df3.groupby("modelo")["score_gemini"].mean()

    x = np.arange(len(modelos))
    w = 0.26
    fig, ax = plt.subplots(figsize=(max(9, len(modelos) * 2.2), 5))
    b1 = ax.bar(x - w, [s1.get(m, 0) for m in modelos], w, label=label1, color="#7fb3d3")
    b2 = ax.bar(x,      [s2.get(m, 0) for m in modelos], w, label=label2, color="#f0a500")
    b3 = ax.bar(x + w,  [s3.get(m, 0) for m in modelos], w, label=label3, color="#27ae60")
    for bars in (b1, b2, b3):
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.03,
                        f"{h:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(modelos, rotation=15, ha="right", fontsize=10)
    ax.set_ylim(0, 2.4)
    ax.set_ylabel("Score promedio (0–2)", fontsize=11)
    ax.axhline(1, color="gray", linestyle="--", alpha=0.4)
    ax.legend(fontsize=10)
    ax.set_title("Evolución del score por modelo — 3 experimentos", fontsize=13, fontweight="bold", pad=14)
    plt.tight_layout()
    return _b64(fig)


def tabla_tres_experimentos(
    df1: pd.DataFrame, df2: pd.DataFrame, df3: pd.DataFrame,
    label1: str, label2: str, label3: str,
) -> str:
    modelos = sorted(set(df1["modelo"].unique()) | set(df2["modelo"].unique()) | set(df3["modelo"].unique()),
                     key=lambda m: df3.groupby("modelo")["score_gemini"].mean().get(m, 0), reverse=True)
    s1 = df1.groupby("modelo")["score_gemini"].mean()
    s2 = df2.groupby("modelo")["score_gemini"].mean()
    s3 = df3.groupby("modelo")["score_gemini"].mean()

    rows = ""
    for m in modelos:
        v1 = s1.get(m); v2 = s2.get(m); v3 = s3.get(m)
        def fmt(v): return f"{v:.3f}" if v is not None else "—"
        def delta_html(a, b):
            if a is None or b is None: return "—"
            d = b - a
            color = COLOR_CORRECTO if d > 0.01 else (COLOR_INCORRECTO if d < -0.01 else "#888")
            return f'<span style="color:{color};font-weight:700">{d:+.3f}</span>'
        rows += f"""<tr>
            <td><code>{m}</code></td>
            <td>{fmt(v1)}</td>
            <td>{fmt(v2)}</td>
            <td>{fmt(v3)}</td>
            <td>{delta_html(v1, v3)}</td>
        </tr>"""
    return f"""<table>
        <thead><tr>
            <th>Modelo</th>
            <th>{label1}</th><th>{label2}</th><th>{label3}</th>
            <th>Delta total</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>"""


def grafico_comparativa_baseline(
    df_emb: pd.DataFrame,
    df_base: pd.DataFrame,
    baseline_label: str = "Baseline (MiniLM-L12)",
    current_label: str = "Embeddings (promedio)",
) -> str:
    modelos = sorted(set(df_emb["modelo"].unique()) | set(df_base["modelo"].unique()))
    base_scores = df_base.groupby("modelo")["score_gemini"].mean()
    emb_scores  = df_emb.groupby("modelo")["score_gemini"].mean()

    x = np.arange(len(modelos))
    ancho = 0.35

    fig, ax = plt.subplots(figsize=(10, max(4, len(modelos) * 0.8)))
    bars1 = ax.bar(x - ancho/2, [base_scores.get(m, 0) for m in modelos],
                   ancho, label=baseline_label, color="#7fb3d3")
    bars2 = ax.bar(x + ancho/2, [emb_scores.get(m, 0) for m in modelos],
                   ancho, label=current_label, color="#27ae60")

    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03,
                f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03,
                f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(modelos, rotation=15, ha="right", fontsize=10)
    ax.set_ylim(0, 2.3)
    ax.set_ylabel("Score promedio (0–2)", fontsize=11)
    ax.axhline(1, color="gray", linestyle="--", alpha=0.4)
    ax.legend(fontsize=10)
    ax.set_title("Baseline vs Experimento de embeddings por modelo", fontsize=13, fontweight="bold", pad=14)
    plt.tight_layout()
    return _b64(fig)


def tabla_comparativa_baseline(df_emb: pd.DataFrame, df_base: pd.DataFrame) -> str:
    modelos = sorted(set(df_emb["modelo"].unique()) | set(df_base["modelo"].unique()))
    base_scores = df_base.groupby("modelo")["score_gemini"].mean()
    emb_scores  = df_emb.groupby("modelo")["score_gemini"].mean()

    # mejor embedding por modelo
    mejor_emb = (
        df_emb.groupby(["modelo", "embedding"])["score_gemini"]
        .mean()
        .reset_index()
        .sort_values("score_gemini", ascending=False)
        .drop_duplicates("modelo")
        .set_index("modelo")
    )

    rows = ""
    for modelo in sorted(modelos, key=lambda m: emb_scores.get(m, 0), reverse=True):
        base = base_scores.get(modelo)
        emb  = emb_scores.get(modelo)
        mejor = mejor_emb.loc[modelo] if modelo in mejor_emb.index else None

        base_str = f"{base:.2f}" if base is not None else "—"
        emb_str  = f"{emb:.2f}"  if emb  is not None else "—"

        if base is not None and emb is not None:
            delta = emb - base
            delta_color = COLOR_CORRECTO if delta > 0 else (COLOR_INCORRECTO if delta < 0 else "#888")
            delta_str = f'<span style="color:{delta_color};font-weight:700">{delta:+.2f}</span>'
        else:
            delta_str = "—"

        mejor_str = f"{mejor['embedding']} ({mejor['score_gemini']:.2f})" if mejor is not None else "—"

        rows += f"""<tr>
            <td><code>{modelo}</code></td>
            <td>{base_str}</td>
            <td>{emb_str}</td>
            <td>{delta_str}</td>
            <td>{mejor_str}</td>
        </tr>"""

    return f"""<table>
        <thead><tr>
            <th>Modelo</th>
            <th>Score Baseline</th>
            <th>Score Embeddings (prom.)</th>
            <th>Δ Mejora</th>
            <th>Mejor embedding</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>"""


def heatmap_modelo_embedding(df: pd.DataFrame) -> str:
    pivot = df.pivot_table(values="score_gemini", index="modelo",
                           columns="embedding", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 2.0),
                                    max(4, len(pivot) * 0.9)))
    im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=0, vmax=2, aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_yticks(range(len(pivot.index)))
    ax.set_xticklabels(pivot.columns, fontsize=11)
    ax.set_yticklabels(pivot.index, fontsize=10)
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if not np.isnan(val):
                color = "white" if val < 0.7 or val > 1.6 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=11, fontweight="bold", color=color)
    plt.colorbar(im, ax=ax, label="Score promedio  (0 = incorrecto · 2 = correcto)")
    ax.set_title("Score promedio por modelo LLM × embedding", fontsize=13, fontweight="bold", pad=14)
    plt.tight_layout()
    return _b64(fig)


def heatmap_categoria(df: pd.DataFrame) -> str:
    pivot = df.pivot_table(values="score_gemini", index="modelo",
                           columns="categoria", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 2.2),
                                    max(4, len(pivot) * 0.9)))
    im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=0, vmax=2, aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_yticks(range(len(pivot.index)))
    ax.set_xticklabels(pivot.columns, rotation=30, ha="right", fontsize=10)
    ax.set_yticklabels(pivot.index, fontsize=10)
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if not np.isnan(val):
                color = "white" if val < 0.7 or val > 1.6 else "black"
                ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                        fontsize=11, fontweight="bold", color=color)
    plt.colorbar(im, ax=ax, label="Score promedio  (0 = incorrecto · 2 = correcto)")
    ax.set_title("Score promedio por modelo × categoría", fontsize=13, fontweight="bold", pad=14)
    plt.tight_layout()
    return _b64(fig)


# ── Ejemplos destacados ───────────────────────────────────────────────────────

def _alucinaciones(val) -> list:
    if isinstance(val, list):
        return [a for a in val if a]
    return []


def obtener_ejemplos(df: pd.DataFrame) -> dict:
    correctas   = df[df["score_gemini"] == 2]
    incorrectas = df[df["score_gemini"] == 0]
    con_aluc    = df[df["alucinaciones"].apply(_alucinaciones).apply(bool)]

    mejor      = correctas.loc[correctas["justificacion_gemini"].str.len().idxmax()] \
                 if not correctas.empty else None
    peor       = incorrectas.iloc[0] if not incorrectas.empty else None
    alucinacion = con_aluc.iloc[0]   if not con_aluc.empty   else None

    return {"mejor": mejor, "peor": peor, "alucinacion": alucinacion}


# ── Tablas HTML ───────────────────────────────────────────────────────────────

def _badge(score) -> str:
    if score == 2:
        return f'<span class="badge correcto">Correcto</span>'
    if score == 1:
        return f'<span class="badge parcial">Parcial</span>'
    if score == 0:
        return f'<span class="badge incorrecto">Incorrecto</span>'
    return f'<span class="badge na">—</span>'


def tabla_modelo_embedding(df: pd.DataFrame) -> str:
    modelos    = sorted(df["modelo"].unique())
    embeddings = sorted(df["embedding"].unique())

    # encabezado con colspan por embedding
    header_emb = "".join(
        f'<th colspan="4" style="text-align:center;border-left:2px solid #dde3ea">{emb}</th>'
        for emb in embeddings
    )
    header_sub = "".join(
        '<th style="border-left:2px solid #dde3ea">Prom.</th>'
        '<th style="color:#27ae60">✓</th>'
        '<th style="color:#e67e22">~</th>'
        '<th style="color:#e74c3c">✗</th>'
        for _ in embeddings
    )

    rows = ""
    for modelo in modelos:
        celdas = ""
        for emb in embeddings:
            g = df[(df["modelo"] == modelo) & (df["embedding"] == emb)]
            if g.empty:
                celdas += '<td colspan="4" style="text-align:center;color:#aaa;border-left:2px solid #edf0f4">—</td>'
                continue
            s  = g["score_gemini"]
            n  = len(s)
            ok = (s == 2).sum()
            pa = (s == 1).sum()
            no = (s == 0).sum()
            prom = s.mean()
            # color de fondo según promedio
            if prom >= 1.5:
                bg = "#d5f5e3"
            elif prom >= 1.0:
                bg = "#fef9e7"
            else:
                bg = "#fadbd8"
            celdas += f"""
                <td style="font-weight:700;background:{bg};border-left:2px solid #dde3ea">{prom:.2f}</td>
                <td style="color:{COLOR_CORRECTO};font-weight:600">{ok/n*100:.0f}%</td>
                <td style="color:{COLOR_PARCIAL};font-weight:600">{pa/n*100:.0f}%</td>
                <td style="color:{COLOR_INCORRECTO};font-weight:600">{no/n*100:.0f}%</td>"""
        rows += f"<tr><td><code>{modelo}</code></td>{celdas}</tr>"

    return f"""<table>
        <thead>
            <tr><th rowspan="2">Modelo</th>{header_emb}</tr>
            <tr>{header_sub}</tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>"""


def tabla_llm(df: pd.DataFrame) -> str:
    filas = []
    for modelo, g in df.groupby("modelo"):
        n  = len(g)
        s  = g["score_gemini"]
        ok = (s == 2).sum()
        pa = (s == 1).sum()
        no = (s == 0).sum()
        aluc = sum(len(_alucinaciones(v)) for v in g["alucinaciones"])
        filas.append({
            "Modelo": modelo, "N": n,
            "Score": f"{s.sum():.0f}/{n*2}",
            "Promedio": f"{s.mean():.2f}",
            "% Correcto":   f"{ok/n*100:.0f}%",
            "% Parcial":    f"{pa/n*100:.0f}%",
            "% Incorrecto": f"{no/n*100:.0f}%",
            "Alucinaciones": aluc,
        })
    filas.sort(key=lambda x: float(x["Promedio"]), reverse=True)

    rows = ""
    for f in filas:
        rows += f"""<tr>
            <td><code>{f['Modelo']}</code></td>
            <td>{f['N']}</td>
            <td><strong>{f['Score']}</strong></td>
            <td><strong>{f['Promedio']}</strong></td>
            <td style="color:{COLOR_CORRECTO};font-weight:600">{f['% Correcto']}</td>
            <td style="color:{COLOR_PARCIAL};font-weight:600">{f['% Parcial']}</td>
            <td style="color:{COLOR_INCORRECTO};font-weight:600">{f['% Incorrecto']}</td>
            <td>{'⚠️ ' + str(f['Alucinaciones']) if f['Alucinaciones'] else '—'}</td>
        </tr>"""
    return f"""<table>
        <thead><tr>
            <th>Modelo</th><th>N</th><th>Score total</th><th>Promedio</th>
            <th>% Correcto</th><th>% Parcial</th><th>% Incorrecto</th><th>Alucinaciones</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>"""


def tabla_embedding(df: pd.DataFrame) -> str:
    filas = []
    for emb, g in df.groupby("embedding"):
        s = g["score_gemini"]
        n = len(g)
        filas.append({
            "Embedding": emb,
            "Modelo completo": g["embedding_modelo"].iloc[0] if "embedding_modelo" in g.columns else "—",
            "N": n,
            "Promedio": f"{s.mean():.2f}",
            "% Correcto": f"{(s==2).sum()/n*100:.0f}%",
            "% Incorrecto": f"{(s==0).sum()/n*100:.0f}%",
        })
    filas.sort(key=lambda x: float(x["Promedio"]), reverse=True)

    rows = ""
    for f in filas:
        rows += f"""<tr>
            <td><strong>{f['Embedding']}</strong></td>
            <td style="font-size:0.85em;color:#555">{f['Modelo completo']}</td>
            <td>{f['N']}</td>
            <td><strong>{f['Promedio']}</strong></td>
            <td style="color:{COLOR_CORRECTO};font-weight:600">{f['% Correcto']}</td>
            <td style="color:{COLOR_INCORRECTO};font-weight:600">{f['% Incorrecto']}</td>
        </tr>"""
    return f"""<table>
        <thead><tr>
            <th>Embedding</th><th>Modelo</th><th>N</th>
            <th>Promedio</th><th>% Correcto</th><th>% Incorrecto</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>"""


def card_ejemplo(row, titulo: str, color: str) -> str:
    aluc = _alucinaciones(row.get("alucinaciones", []))
    aluc_html = ""
    if aluc:
        items = "".join(f"<li>{a}</li>" for a in aluc)
        aluc_html = f'<div class="aluc"><strong>⚠️ Alucinaciones detectadas:</strong><ul>{items}</ul></div>'

    return f"""<div class="card" style="border-left:4px solid {color}">
        <div class="card-header" style="color:{color}">{titulo}</div>
        <p class="meta">
            <span class="tag">{row.get('modelo','?')}</span>
            <span class="tag">{row.get('embedding','?')}</span>
            <span class="tag">{row.get('categoria','?')}</span>
            {_badge(row.get('score_gemini'))}
        </p>
        <p><strong>Pregunta:</strong> {row.get('pregunta','')}</p>
        <div class="box-ref"><strong>Referencia:</strong><br>{row.get('respuesta_referencia','')}</div>
        <div class="box-resp"><strong>Respuesta del chatbot:</strong><br>{row.get('respuesta','').strip()}</div>
        {aluc_html}
        <p class="justif"><em>Justificación Gemini:</em> {row.get('justificacion_gemini','')}</p>
    </div>"""


# ── HTML principal ────────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f4f6f9; color: #2c3e50; line-height: 1.6; }
header { background: #1a252f; color: white; padding: 2rem 3rem; }
header h1 { font-size: 1.7rem; margin-bottom: 0.3rem; }
header p  { opacity: 0.75; font-size: 0.95rem; }
nav { background: #2c3e50; padding: 0.6rem 3rem; display: flex; gap: 2rem; }
nav a { color: #bdc3c7; text-decoration: none; font-size: 0.9rem; }
nav a:hover { color: white; }
.container { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }
section { background: white; border-radius: 8px; padding: 2rem;
          margin-bottom: 2rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
h2 { font-size: 1.25rem; margin-bottom: 1.2rem; color: #1a252f;
     padding-bottom: 0.5rem; border-bottom: 2px solid #e8edf2; }
h3 { font-size: 1rem; margin: 1.2rem 0 0.6rem; color: #34495e; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th { background: #f0f3f7; text-align: left; padding: 0.6rem 0.8rem;
     font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.05em;
     color: #555; border-bottom: 2px solid #dde3ea; }
td { padding: 0.55rem 0.8rem; border-bottom: 1px solid #edf0f4; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #fafbfc; }
code { background: #eef1f5; padding: 0.1em 0.4em; border-radius: 3px;
       font-size: 0.88em; color: #c0392b; }
.badge { display: inline-block; padding: 0.15em 0.6em; border-radius: 12px;
         font-size: 0.78rem; font-weight: 600; }
.correcto   { background: #d5f5e3; color: #1e8449; }
.parcial    { background: #fdebd0; color: #a04000; }
.incorrecto { background: #fadbd8; color: #922b21; }
.na         { background: #eee; color: #888; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
              gap: 1rem; margin-bottom: 1.5rem; }
.stat { background: #f8fafc; border-radius: 6px; padding: 1rem; text-align: center;
        border: 1px solid #e3e8ef; }
.stat .num  { font-size: 2rem; font-weight: 700; color: #2980b9; }
.stat .lbl  { font-size: 0.8rem; color: #777; margin-top: 0.2rem; }
.card { background: #fdfdfd; border-radius: 6px; padding: 1.4rem;
        margin-bottom: 1.2rem; border: 1px solid #e8edf2; }
.card-header { font-size: 1rem; font-weight: 700; margin-bottom: 0.8rem; }
.meta { margin-bottom: 0.8rem; display: flex; flex-wrap: wrap; gap: 0.4rem; align-items:center; }
.tag { background: #e8edf2; color: #444; padding: 0.15em 0.55em;
       border-radius: 10px; font-size: 0.78rem; }
.box-ref, .box-resp { background: #f8fafc; border-left: 3px solid #bdc3c7;
                       padding: 0.7rem 1rem; margin: 0.6rem 0; font-size: 0.9rem;
                       border-radius: 0 4px 4px 0; }
.box-resp { border-left-color: #2980b9; }
.aluc { background: #fef9e7; border-left: 3px solid #f39c12; padding: 0.6rem 1rem;
        margin: 0.6rem 0; font-size: 0.88rem; border-radius: 0 4px 4px 0; }
.aluc ul { margin: 0.3rem 0 0 1.2rem; }
.justif { font-size: 0.85rem; color: #666; margin-top: 0.8rem; }
img.chart { max-width: 100%; height: auto; display: block; margin: 1rem auto; }
footer { text-align: center; padding: 2rem; color: #aaa; font-size: 0.82rem; }
"""


def generar_html(
    df: pd.DataFrame,
    fecha: str,
    df_base: pd.DataFrame | None = None,
    baseline_label: str = "Baseline (MiniLM-L12)",
    current_label: str = "Embeddings (promedio)",
    df_base2: pd.DataFrame | None = None,
    baseline2_label: str = "Experimento 2",
) -> str:
    n_total   = len(df)
    n_emb     = df["embedding"].nunique()
    n_modelos = df["modelo"].nunique()
    pct_ok    = (df["score_gemini"] == 2).mean() * 100
    prom_gral = df["score_gemini"].mean()

    stats = f"""<div class="stats-grid">
        <div class="stat"><div class="num">{n_total}</div><div class="lbl">Evaluaciones</div></div>
        <div class="stat"><div class="num">{n_modelos}</div><div class="lbl">Modelos LLM</div></div>
        <div class="stat"><div class="num">{n_emb}</div><div class="lbl">Embeddings</div></div>
        <div class="stat"><div class="num">{pct_ok:.0f}%</div><div class="lbl">Respuestas correctas</div></div>
        <div class="stat"><div class="num">{prom_gral:.2f}</div><div class="lbl">Score promedio global (0–2)</div></div>
    </div>"""

    img_llm      = grafico_llm(df)
    img_emb      = grafico_embedding(df)
    img_emb_llm  = heatmap_modelo_embedding(df)
    img_heat     = heatmap_categoria(df)
    ejemplos     = obtener_ejemplos(df)

    if df_base is not None and df_base2 is not None:
        # Comparativa de 3 experimentos
        img_tres = grafico_tres_experimentos(df_base, df_base2, df, baseline_label, baseline2_label, current_label)
        tabla_tres = tabla_tres_experimentos(df_base, df_base2, df, baseline_label, baseline2_label, current_label)
        seccion_baseline = f"""
  <section id="baseline">
    <h2>Evolución por experimento</h2>
    <p style="font-size:0.88rem;color:#666;margin-bottom:1rem">
      Comparativa: <strong>{baseline_label}</strong> → <strong>{baseline2_label}</strong> → <strong>{current_label}</strong>.
      Delta total = diferencia entre el primer y último experimento.
    </p>
    {tabla_tres}
    <img class="chart" src="data:image/png;base64,{img_tres}" alt="Evolución 3 experimentos">
  </section>"""
    elif df_base is not None:
        img_base    = grafico_comparativa_baseline(df, df_base, baseline_label, current_label)
        tabla_base  = tabla_comparativa_baseline(df, df_base)
        seccion_baseline = f"""
  <section id="baseline">
    <h2>Comparativa con experimento anterior</h2>
    <p style="font-size:0.88rem;color:#666;margin-bottom:1rem">
      Comparativa: <strong>{baseline_label}</strong> vs <strong>{current_label}</strong>.
      Δ positivo significa mejora respecto al experimento anterior.
    </p>
    {tabla_base}
    <img class="chart" src="data:image/png;base64,{img_base}" alt="Comparativa baseline">
  </section>"""
    else:
        seccion_baseline = ""

    card_mejor = card_ejemplo(ejemplos["mejor"], "Mejor respuesta", COLOR_CORRECTO) \
                 if ejemplos["mejor"] is not None else "<p>Sin datos.</p>"
    card_peor  = card_ejemplo(ejemplos["peor"],  "Peor respuesta",  COLOR_INCORRECTO) \
                 if ejemplos["peor"] is not None else "<p>Sin datos.</p>"
    card_aluc  = card_ejemplo(ejemplos["alucinacion"], "Alucinación detectada", COLOR_PARCIAL) \
                 if ejemplos["alucinacion"] is not None else "<p>No se detectaron alucinaciones.</p>"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reporte de Evaluación — Chatbot Derechos del Consumidor</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>Chatbot de Simplificación de Derechos del Consumidor Peruano</h1>
  <p>Reporte de evaluación LLM-as-a-judge · Juez: Gemini 2.5 Flash · Generado: {fecha}</p>
</header>
<nav>
  <a href="#resumen">Resumen</a>
  <a href="#llm">LLM vs LLM</a>
  <a href="#embeddings">Embeddings</a>
  <a href="#categorias">Por categoría</a>
  {'<a href="#baseline">vs Baseline</a>' if df_base is not None else ''}
  <a href="#ejemplos">Ejemplos</a>
</nav>

<div class="container">

  <section id="resumen">
    <h2>Resumen general</h2>
    {stats}
  </section>

  <section id="llm">
    <h2>Comparativa LLM vs LLM</h2>
    {tabla_llm(df)}
    <img class="chart" src="data:image/png;base64,{img_llm}" alt="LLM chart">
  </section>

  <section id="embeddings">
    <h2>Comparativa de modelos de embeddings</h2>
    {tabla_embedding(df)}
    <img class="chart" src="data:image/png;base64,{img_emb}" alt="Embedding chart">
    <h3>Score por combinación modelo × embedding</h3>
    <p style="font-size:0.88rem;color:#666;margin-bottom:1rem">
      Promedio (0–2) con fondo verde ≥ 1.5 · amarillo ≥ 1.0 · rojo &lt; 1.0.
      Columnas ✓ correcto · ~ parcial · ✗ incorrecto.
    </p>
    {tabla_modelo_embedding(df)}
    <img class="chart" src="data:image/png;base64,{img_emb_llm}" alt="Heatmap modelo x embedding">
  </section>

  <section id="categorias">
    <h2>Score por categoría de pregunta</h2>
    <p style="font-size:0.88rem;color:#666;margin-bottom:1rem">
      Score promedio por combinación modelo × categoría (verde = correcto · rojo = incorrecto).
    </p>
    <img class="chart" src="data:image/png;base64,{img_heat}" alt="Heatmap categorías">
  </section>

  {seccion_baseline}

  <section id="ejemplos">
    <h2>Ejemplos destacados</h2>
    <h3>Mejor respuesta</h3>
    {card_mejor}
    <h3>Peor respuesta</h3>
    {card_peor}
    <h3>Caso con alucinación</h3>
    {card_aluc}
  </section>

</div>
<footer>
  Proyecto académico — Curso PLN · Décimo ciclo · {fecha}
</footer>
</body>
</html>"""


# ── main ──────────────────────────────────────────────────────────────────────

def parsear_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Genera reporte HTML de evaluación RAG")
    p.add_argument("--entrada", default="scores_gemini_embeddings.json",
                   help="JSON de scores (default: scores_gemini_embeddings.json)")
    p.add_argument("--baseline", default="scores_gemini_baseline.json",
                   help="JSON de scores baseline para comparativa (default: scores_gemini_baseline.json)")
    p.add_argument("--salida", default="reporte.html",
                   help="Archivo HTML de salida (default: reporte.html)")
    p.add_argument("--baseline-label", default="Baseline (MiniLM-L12)",
                   help="Etiqueta del baseline en gráficos comparativos")
    p.add_argument("--current-label", default="Embeddings (promedio)",
                   help="Etiqueta del experimento actual en gráficos comparativos")
    p.add_argument("--baseline2", default=None,
                   help="Segundo JSON de scores para comparativa de 3 experimentos")
    p.add_argument("--baseline2-label", default="Experimento 2",
                   help="Etiqueta del segundo baseline")
    return p.parse_args()


def _cargar_df(path: str) -> pd.DataFrame:
    with open(path, encoding="utf-8") as f:
        datos = json.load(f)
    df = pd.DataFrame(datos)
    df = df[df["score_gemini"].notna()].copy()
    df["score_gemini"] = df["score_gemini"].astype(int)
    df["alucinaciones"] = df["alucinaciones"].apply(
        lambda x: x if isinstance(x, list) else []
    )
    return df


def main() -> None:
    args = parsear_args()

    if not Path(args.entrada).exists():
        print(f"[ERROR] No se encontró: {args.entrada}")
        return

    print(f"Cargando {args.entrada}...")
    df = _cargar_df(args.entrada)
    print(f"  Entradas con score: {len(df)}")

    df_base = None
    if Path(args.baseline).exists():
        print(f"Cargando baseline: {args.baseline}...")
        df_base = _cargar_df(args.baseline)
        print(f"  Entradas baseline: {len(df_base)}")
    else:
        print(f"  (baseline no encontrado: {args.baseline} — se omite sección comparativa)")

    df_base2 = None
    if args.baseline2 and Path(args.baseline2).exists():
        print(f"Cargando baseline2: {args.baseline2}...")
        df_base2 = _cargar_df(args.baseline2)
        print(f"  Entradas baseline2: {len(df_base2)}")

    if df.empty:
        print("[ERROR] No hay entradas con score aún.")
        return

    html = generar_html(
        df, date.today().isoformat(), df_base,
        baseline_label=args.baseline_label,
        current_label=args.current_label,
        df_base2=df_base2,
        baseline2_label=args.baseline2_label,
    )
    Path(args.salida).write_text(html, encoding="utf-8")
    print(f"Reporte generado: {args.salida}")


if __name__ == "__main__":
    main()
