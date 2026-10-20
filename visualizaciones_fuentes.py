#!/usr/bin/env python3
"""Genera graficas, tablas y un esquema del proyecto inmobiliario cubano.

Reglas de las graficas:
- Se usan `precio_analisis` y `moneda_analisis`, no el campo publicado.
- No se recortan precios: la distribucion usa escala logaritmica.
- Las monedas con menos de 5 anuncios no se grafican; se anotan.
- Municipios y zonas no se mezclan: los municipios se homologan a los 15 de
  La Habana y las zonas de Cubisima se muestran en un panel aparte.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from precio_moneda import detalle_analisis, normalizar_moneda, precios_analisis

ROOT = Path(__file__).resolve().parent
MASTER_GLOB = "outputs/integracion/dataset_maestro_*.csv"
OUT = ROOT / "outputs" / "visualizaciones"
OUT.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 130
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["axes.titlesize"] = 11
plt.rcParams["axes.labelsize"] = 9.5
plt.rcParams["xtick.labelsize"] = 9
plt.rcParams["ytick.labelsize"] = 9


def newest_master() -> Path:
    files = sorted((ROOT / "outputs" / "integracion").glob("dataset_maestro_*.csv"))
    if not files:
        raise FileNotFoundError("No hay dataset maestro. Ejecuta primero integrar_fuentes.py")
    return files[-1]


def money_labels(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["moneda"] = frame["moneda"].map(normalizar_moneda).fillna("")
    frame.loc[frame["moneda"].eq("CUP"), "precio_original"] = pd.to_numeric(
        frame.loc[frame["moneda"].eq("CUP"), "precio_original"], errors="coerce"
    )
    return frame


def save(fig, name: str) -> Path:
    path = OUT / name
    fig.savefig(path, dpi=140, facecolor="white")
    plt.close(fig)
    return path


def _currency_counts(frame: pd.DataFrame) -> pd.Series:
    return (
        frame.loc[frame["precio_analisis"].notna() & frame["moneda_analisis"].ne(""), "moneda_analisis"]
        .value_counts()
    )


def plot_price_distribution(frame: pd.DataFrame):
    subset = frame[
        frame["precio_analisis"].notna()
        & frame["precio_analisis"].gt(0)
        & frame["moneda_analisis"].ne("")
    ].copy()
    if subset.empty:
        return None
    pares = subset.groupby(["moneda_analisis", "fuente"]).size()
    excluidas_pares = pares[pares < 10]
    subset = subset[
        subset.set_index(["moneda_analisis", "fuente"]).index.isin(pares[pares >= 10].index)
    ].copy()
    if subset.empty:
        return None
    counts = subset["moneda_analisis"].value_counts()
    currencies = [currency for currency in ["CUC", "USD", "EUR", "CUP"] if counts.get(currency, 0) >= 5]
    excluidas = {currency: int(counts[currency]) for currency in counts.index if counts[currency] < 5}
    if not currencies:
        return None
    fig, axes = plt.subplots(len(currencies), 1, figsize=(10, 3.5 * len(currencies)), sharex=False)
    axes = np.atleast_1d(axes)
    for ax, currency in zip(axes, currencies):
        data = subset[subset["moneda_analisis"].eq(currency)]
        sns.histplot(
            data=data,
            x="precio_analisis",
            hue="fuente",
            bins=40,
            element="step",
            fill=False,
            stat="count",
            common_norm=False,
            log_scale=(True, False),
            ax=ax,
        )
        mediana = data["precio_analisis"].median()
        ax.axvline(mediana, color="#222222", linestyle="--", linewidth=1.2)
        ax.text(
            0.99,
            0.95,
            f"n={len(data):,}; mediana={mediana:,.0f}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=8.5,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#bbbbbb", "alpha": 0.9},
        )
        ax.set_title(f"{currency}: distribución del precio de análisis por fuente")
        ax.set_xlabel(f"Precio de análisis ({currency}, escala log)")
        ax.set_ylabel("Anuncios")
        leyenda = ax.get_legend()
        if leyenda is not None:
            leyenda.set_title("Fuente")
    notas = []
    if excluidas:
        notas.append("moneda n<5: " + ", ".join(f"{m} ({n})" for m, n in sorted(excluidas.items())))
    if not excluidas_pares.empty:
        notas.append(
            "fuente-moneda n<10: "
            + ", ".join(f"{m}/{f} ({n})" for (m, f), n in excluidas_pares.items())
        )
    nota = (" Sin gráfico: " + " | ".join(notas) + ".") if notas else ""
    fig.suptitle(
        "Distribución de precios de análisis (sin recortes; monedas con n>=5)." + nota,
        y=1.01,
    )
    fig.tight_layout()
    return save(fig, "01_distribucion_precios_por_moneda.png")


def plot_municipality_median(frame: pd.DataFrame):
    required = {"precio_analisis", "moneda_analisis", "ubicacion_analisis"}
    if not required.issubset(frame.columns):
        return None
    subset = frame[
        frame["precio_analisis"].notna()
        & frame["moneda_analisis"].ne("")
        & frame["ubicacion_analisis"].fillna("").astype(str).str.strip().ne("")
    ].copy()
    if "municipio_homologado" not in subset.columns:
        subset["municipio_homologado"] = ""
    subset["municipio_homologado"] = subset["municipio_homologado"].fillna("").astype(str).str.strip()
    subset["ubicacion_analisis"] = subset["ubicacion_analisis"].fillna("").astype(str).str.strip()

    usd = subset[
        subset["moneda_analisis"].eq("USD")
        & subset["municipio_homologado"].ne("")
        & subset["fuente"].isin(["Revolico", "HogarEnCuba"])
    ]
    cuc = subset[
        subset["fuente"].eq("Cubisima")
        & subset["moneda_analisis"].eq("CUC")
        & subset["ubicacion_analisis"].ne("")
    ]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), gridspec_kw={"width_ratios": [1.15, 1]})
    ax_izq, ax_der = axes

    if not usd.empty:
        total = usd.groupby("municipio_homologado").size()
        keep = total[total >= 10].index
        usd = usd[usd["municipio_homologado"].isin(keep)]
    if not usd.empty:
        med = usd.groupby(["municipio_homologado", "fuente"])["precio_analisis"].median().unstack()
        n_total = usd.groupby("municipio_homologado").size()
        orden = med.median(axis=1).sort_values().index
        med = med.loc[orden]
        y = np.arange(len(med))
        fuentes = list(med.columns)
        alto = 0.36
        colores = {"Revolico": "#c00000", "HogarEnCuba": "#2e75b6"}
        for i, fuente in enumerate(fuentes):
            valores = med[fuente]
            mascara = valores.notna()
            posiciones = y[mascara] + (i - (len(fuentes) - 1) / 2) * alto
            barras = ax_izq.barh(
                posiciones,
                valores[mascara],
                height=alto,
                color=colores.get(fuente, "#7f7f7f"),
                label=fuente,
            )
            ax_izq.bar_label(barras, fmt="%.0f", padding=2, fontsize=7)
        ax_izq.set_yticks(y)
        ax_izq.set_yticklabels([f"{m} (n={int(n_total[m])})" for m in med.index], fontsize=8.5)
        ax_izq.set_xlabel("Precio mediano (USD)")
        ax_izq.set_title("USD: municipios de La Habana (Revolico y HogarEnCuba; n>=10)")
        ax_izq.legend(title="Fuente", fontsize=8, loc="lower right")
    else:
        ax_izq.text(0.5, 0.5, "Sin municipios USD con n>=10", ha="center", va="center", transform=ax_izq.transAxes)
        ax_izq.set_axis_off()

    if not cuc.empty:
        total = cuc.groupby("ubicacion_analisis").size()
        keep = total[total >= 10].index
        cuc = cuc[cuc["ubicacion_analisis"].isin(keep)]
    if not cuc.empty:
        med_z = cuc.groupby("ubicacion_analisis")["precio_analisis"].agg(["median", "count"]).sort_values("median")
        y = np.arange(len(med_z))
        barras = ax_der.barh(y, med_z["median"], height=0.55, color="#70ad47")
        ax_der.bar_label(barras, fmt="%.0f", padding=2, fontsize=7)
        ax_der.set_yticks(y)
        ax_der.set_yticklabels([f"{z} (n={int(n)})" for z, n in zip(med_z.index, med_z["count"])], fontsize=8.5)
        ax_der.set_xlabel("Precio mediano (CUC)")
        ax_der.set_title("CUC: zonas/barrios de Cubisima (n>=10)")
    else:
        ax_der.text(0.5, 0.5, "Sin zonas CUC con n>=10", ha="center", va="center", transform=ax_der.transAxes)
        ax_der.set_axis_off()

    fig.suptitle(
        "Precio mediano por ubicación: municipios (USD) y zonas (CUC), sin mezclar niveles geográficos",
        y=1.02,
    )
    fig.text(
        0.01,
        0.005,
        "Cubisima USD (n=8) no se incluye en el panel municipal; sus zonas se muestran en el panel CUC. "
        "Los municipios se homologan a los 15 de La Habana; las zonas conservan la etiqueta de Cubisima.",
        fontsize=7.5,
        va="bottom",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return save(fig, "02_mediana_precio_por_municipio.png")


def plot_rooms_price(frame: pd.DataFrame):
    subset = frame[
        frame["habitaciones_analisis"].notna()
        & frame["precio_analisis"].notna()
        & frame["moneda_analisis"].ne("")
    ].copy()
    if subset.empty:
        return None
    counts = subset.groupby("moneda_analisis").size()
    usables = counts[counts >= 5].index
    excluidas = counts[counts < 5]
    subset = subset[subset["moneda_analisis"].isin(usables)].copy()
    if subset.empty:
        return None
    pares = subset.groupby(["moneda_analisis", "fuente"]).size()
    excluidas_pares = pares[pares < 10]
    keep_pares = pares[pares >= 10].index
    subset = subset[subset.set_index(["moneda_analisis", "fuente"]).index.isin(keep_pares)].copy()
    if subset.empty:
        return None
    subset["habitaciones_grupo"] = np.where(
        subset["habitaciones_analisis"] >= 8,
        "8+",
        subset["habitaciones_analisis"].astype(int).astype(str),
    )
    conteo_rooms = subset.groupby(["moneda_analisis", "habitaciones_grupo"]).size()
    excluidas_rooms = conteo_rooms[conteo_rooms < 5]
    keep_rooms = conteo_rooms[conteo_rooms >= 5].index
    subset = subset[subset.set_index(["moneda_analisis", "habitaciones_grupo"]).index.isin(keep_rooms)].copy()
    if subset.empty:
        return None
    presentes = set(subset["habitaciones_grupo"].unique())
    order = [str(i) for i in range(1, 8) if str(i) in presentes]
    if "8+" in presentes:
        order.append("8+")
    g = sns.catplot(
        data=subset,
        x="habitaciones_grupo",
        y="precio_analisis",
        hue="fuente",
        col="moneda_analisis",
        kind="box",
        height=4.8,
        aspect=1.05,
        order=order,
        showfliers=False,
    )
    g.set(yscale="log")
    g.set_axis_labels("Habitaciones (8+ agrupa 8 o más; incluye 10.5)", "Precio de análisis (escala log)")
    g.set_titles("Moneda: {col_name}")
    try:
        g.legend.set_title("Fuente")
    except AttributeError:
        pass
    notas = []
    if not excluidas.empty:
        notas.append("moneda n<5: " + ", ".join(f"{m} ({n})" for m, n in excluidas.items()))
    if not excluidas_pares.empty:
        notas.append("fuente-moneda n<10: " + ", ".join(f"{m}/{f} ({n})" for (m, f), n in excluidas_pares.items()))
    if not excluidas_rooms.empty:
        notas.append("habitaciones n<5: " + ", ".join(f"{m}/{h} ({n})" for (m, h), n in excluidas_rooms.items()))
    g.fig.suptitle("Precio por habitaciones (mejor dato disponible)", y=1.03)
    if notas:
        g.fig.text(0.5, 0.005, "Sin gráfico: " + " | ".join(notas), ha="center", va="bottom", fontsize=7.2)
    g.fig.subplots_adjust(top=0.85, bottom=0.16)
    g.fig.savefig(OUT / "03_habitaciones_precio_por_moneda.png", dpi=140, facecolor="white")
    plt.close(g.fig)
    return OUT / "03_habitaciones_precio_por_moneda.png"


def plot_feature_frequency(frame: pd.DataFrame):
    cub = frame[frame["fuente"].eq("Cubisima")]
    if cub.empty:
        return None
    feature_cols = ["garaje", "piscina", "terraza", "patio", "balcon", "jardin"]
    means = {}
    for col in feature_cols:
        if col not in cub.columns:
            continue
        series = pd.to_numeric(cub[col], errors="coerce")
        if series.notna().any():
            # Los campos ausentes se cuentan como "no declarado" (0), no se imputan.
            means[col] = float(series.fillna(0).mean())
    if not means:
        return None
    features = sorted(means, key=means.get, reverse=True)
    values = [means[f] * 100 for f in features]
    etiquetas = {
        "garaje": "Garaje",
        "piscina": "Piscina",
        "terraza": "Terraza",
        "patio": "Patio",
        "balcon": "Balcón",
        "jardin": "Jardín",
    }
    nombres = [etiquetas.get(feature, feature) for feature in features]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(nombres, values, color="#70ad47")
    ax.bar_label(bars, labels=[f"{v:.1f}%" for v in values], padding=2, fontsize=8)
    ax.set_xlabel("% de anuncios Cubisima con la característica")
    ax.set_ylabel("Característica")
    ax.set_title(f"Características declaradas en Cubisima (n={len(cub)}; ausente = no declarado)")
    ax.set_xlim(0, max(values) * 1.15 if values else 1)
    fig.tight_layout()
    return save(fig, "04_frecuencia_caracteristicas_cubisima.png")


def plot_metadata_quality(frame: pd.DataFrame):
    fields = ["ubicacion_raw", "habitaciones", "banos", "precio_original", "moneda", "fecha_publicacion"]
    labels = {
        "ubicacion_raw": "Ubicación",
        "habitaciones": "Habitaciones",
        "banos": "Baños",
        "precio_original": "Precio",
        "moneda": "Moneda",
        "fecha_publicacion": "Fecha",
    }
    rows = []
    for source, g in frame.groupby("fuente"):
        for field in fields:
            if field == "moneda" and field in g:
                coverage = float(g[field].fillna("").astype(str).str.strip().ne("").mean())
            else:
                coverage = float(pd.notna(g[field]).mean()) if field in g else 0.0
            rows.append({"fuente": source, "campo": labels.get(field, field), "cobertura_pct": 100 * coverage})
    q = pd.DataFrame(rows)
    if q.empty:
        return None
    fig, ax = plt.subplots(figsize=(10, 5.2))
    sns.barplot(data=q, x="campo", y="cobertura_pct", hue="fuente", ax=ax)
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    ax.set_ylabel("Cobertura (%)")
    ax.set_xlabel("Campo publicado")
    ax.set_title("Cobertura del campo publicado por fuente")
    ax.set_ylim(0, 100)
    ax.legend(title="Fuente", loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.28)
    return save(fig, "05_calidad_metadatos_fuentes.png")


def plot_analysis_coverage(frame: pd.DataFrame):
    fields = [
        ("precio_analisis", "Precio análisis"),
        ("ubicacion_analisis", "Ubicación análisis"),
        ("municipio_homologado", "Municipio homologado"),
        ("habitaciones_analisis", "Habitaciones análisis"),
        ("banos_analisis", "Baños análisis"),
        ("fecha_analisis", "Fecha análisis"),
    ]
    rows = []
    for source, g in frame.groupby("fuente"):
        for field, label in fields:
            if field == "precio_analisis":
                coverage = float(pd.to_numeric(g[field], errors="coerce").notna().mean()) if field in g else 0.0
            elif field == "fecha_analisis":
                publicada = g["fecha_publicacion"].fillna("").astype(str).str.strip().ne("")
                reextraida = g["fecha_reextraida"].fillna("").astype(str).str.strip().ne("")
                coverage = float((publicada | reextraida).mean())
            elif field in ("habitaciones_analisis", "banos_analisis"):
                coverage = float(pd.to_numeric(g[field], errors="coerce").notna().mean()) if field in g else 0.0
            else:
                coverage = float(g[field].fillna("").astype(str).str.strip().ne("").mean()) if field in g else 0.0
            rows.append({"fuente": source, "campo": label, "cobertura_pct": 100 * coverage})
    q = pd.DataFrame(rows)
    if q.empty:
        return None
    fig, ax = plt.subplots(figsize=(11, 5.4))
    sns.barplot(data=q, x="campo", y="cobertura_pct", hue="fuente", ax=ax)
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    ax.set_ylabel("Cobertura (%)")
    ax.set_xlabel("Dato de análisis")
    ax.set_title("Cobertura del dato de análisis (texto, página o slug)")
    ax.set_ylim(0, 100)
    ax.legend(title="Fuente", loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.28)
    return save(fig, "05b_cobertura_analisis_fuentes.png")


def plot_exchange_rates():
    folder = ROOT / "data" / "tasas"
    rate_files = sorted(folder.glob("tasas_cambio_*.csv")) if folder.exists() else []
    if not rate_files:
        return None, None, None
    r = pd.read_csv(rate_files[-1])
    if r.empty:
        return None, rate_files[-1], None
    long_rows = []
    for col_stem, label in [
        ("usd_informal_cup", "USD informal"),
        ("usd_formal_cup", "USD formal"),
        ("eur_informal_cup", "EUR informal"),
        ("eur_formal_cup", "EUR formal"),
    ]:
        if col_stem in r.columns and pd.notna(r[col_stem]).any():
            long_rows.append({"moneda": label, "cup_por_unidad": float(r[col_stem].iloc[0])})
    rates = pd.DataFrame(long_rows)
    if rates.empty:
        return None, rate_files[-1], None
    fecha = pd.to_datetime(r["fecha_utc"].iloc[0], errors="coerce")
    fecha_txt = fecha.strftime("%d/%m/%Y") if pd.notna(fecha) else "fecha no registrada"
    fuente = str(r["fuente"].iloc[0]) if "fuente" in r else "fuente no registrada"
    estado = str(r["estado_acceso"].iloc[0]) if "estado_acceso" in r else "estado no registrado"
    fig, ax = plt.subplots(figsize=(8, 4.8))
    colors = ["#bf8f00", "#f4c20d", "#4472c4", "#9bc2e6"]
    bars = ax.bar(rates["moneda"], rates["cup_por_unidad"], color=colors[: len(rates)])
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in rates["cup_por_unidad"]], padding=2, fontsize=8)
    ax.set_ylabel("CUP por unidad")
    ax.set_title(f"Tasas registradas el {fecha_txt} (CUP por unidad)")
    ax.set_ylim(0, max(rates["cup_por_unidad"]) * 1.15)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.text(
        0.01,
        0.01,
        f"Fuente: {fuente} ({'acceso bloqueado; valores manuales' if estado == 'bloqueado_o_no_disponible' else estado}).\n"
        "CUC no tiene tasa de mercado: solo se usa paridad nominal 1 CUC = 1 USD, identificada en el análisis.",
        fontsize=7.5,
        va="bottom",
    )
    fig.tight_layout(rect=[0, 0.1, 1, 1])
    return save(fig, "06_tasas_usd_eur_cup.png"), rate_files[-1], fecha_txt


def _latest_count(prefix: str) -> int:
    files = sorted((ROOT / "outputs" / "integracion").glob(f"{prefix}_*.csv"))
    if not files:
        return 0
    try:
        return len(pd.read_csv(files[-1]))
    except Exception:
        return 0


def _interview_count() -> int:
    files = sorted((ROOT / "outputs" / "entrevistas").glob("entrevistas_codificadas_*.csv"))
    if not files:
        return 0
    try:
        return len(pd.read_csv(files[-1]))
    except Exception:
        return 0


def plot_schema(frame: pd.DataFrame, rate_file: Path | None = None, fecha_tasas: str | None = None):
    fig, ax = plt.subplots(figsize=(13, 8.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def caja(x, y, w, h, texto, color, fontsize=8.6, titulo=None):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.45", linewidth=1.2,
            edgecolor="#555555", facecolor=color,
        )
        ax.add_patch(rect)
        if titulo:
            ax.text(x + 1.2, y + h - 1.2, titulo, ha="left", va="top",
                    fontsize=fontsize + 1.1, weight="bold")
        ax.text(x + 1.2, y + h - 3.4, texto, ha="left", va="top",
                fontsize=fontsize, linespacing=1.35)

    def flecha(x1, y1, x2, y2):
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops={"arrowstyle": "->", "lw": 1.8, "color": "#404040"},
        )

    counts = frame.groupby("fuente").size().to_dict()
    rev = frame[frame["fuente"].eq("Revolico")]
    estado = rev["estado_anuncio"].fillna("").astype(str).str.strip()
    inaccesibles = int(
        estado.str.startswith("anuncio_inexistente").sum()
        + estado.eq("despublicado").sum()
    )
    total = len(frame)
    price_n = int(frame["precio_analisis"].notna().sum())
    price_pct = 100 * price_n / total if total else 0
    hab_n = int(pd.to_numeric(frame["habitaciones_analisis"], errors="coerce").notna().sum())
    banos_n = int(pd.to_numeric(frame["banos_analisis"], errors="coerce").notna().sum())
    muni_n = int(
        frame.get("municipio_homologado", pd.Series("", index=frame.index))
        .fillna("").astype(str).str.strip().ne("").sum()
    )
    pending = int(frame["precio_analisis"].isna().sum())
    no_viv = _latest_count("anuncios_no_residenciales")
    alcance = _latest_count("anuncios_fuera_de_alcance")
    entrevistas = _interview_count()

    # Fuentes
    caja(2, 82, 29, 14,
         f"{counts.get('Revolico', 0):,} integrados\nHTML guardado; {inaccesibles} inaccesibles\nsin API pública",
         "#dbe5ff", titulo="Revolico")
    caja(35.5, 82, 29, 14,
         f"{counts.get('Cubisima', 0):,} integrados\nHTML accesible; fechas dd/mm/aaaa\ncaracterísticas auxiliares",
         "#d9f2d9", titulo="Cubisima")
    caja(69, 82, 29, 14,
         f"{counts.get('HogarEnCuba', 0):,} integrados\nHTML estructurado; m² escaso\nUSD y 2 fichas EUR",
         "#fff2cc", titulo="HogarEnCuba")

    # Integracion
    caja(2, 55, 96, 21,
         f"- Deduplicación por URL e id_maestro estable\n"
         f"- {no_viv} no vivienda/alquiler + {alcance} fuera de alcance, en CSV auditables\n"
         f"- Reextracción de municipio, fecha, habitaciones y baños desde la página\n"
         f"- Precio de análisis: campo publicado o reextracción manual verificada\n"
         f"- Homologación de los 15 municipios de La Habana; zonas sin imputar",
         "#f2d9ff", titulo="Integración no destructiva (integrar_fuentes.py)")

    # Maestro y analisis
    caja(2, 33, 45, 17,
         f"{total:,} anuncios\n"
         f"Precio de análisis: {price_n:,} ({price_pct:.1f}%)\n"
         f"Habitaciones: {hab_n:,}; baños: {banos_n:,}\n"
         f"Municipio homologado: {muni_n:,}\n"
         f"Campos publicados intactos + columnas de análisis",
         "#f7e2bd", titulo="Dataset maestro")
    caja(52, 33, 46, 17,
         "Q1-Q5: precios, municipios, habitaciones,\n"
         "       características y canales\n"
         "Q6: conversión USD/EUR (tasas) y CUC nominal 1:1\n"
         "Q7: terciles y k-means por moneda\n"
         f"Q8: entrevistas anónimas E01-E10 (n={entrevistas})\n"
         "Q9: límites y cobertura",
         "#d9eaf7", titulo="Análisis (preguntas 1-9)")

    # Salidas y limites
    caja(2, 13, 45, 15,
         "outputs/: CSV, MD y PNG\n"
         "pruebas automatizadas\n"
         "Git solo con código y documentación\n"
         "trazabilidad fuente -> anuncio -> análisis",
         "#e2e2e2", titulo="Salidas y reproducibilidad")
    caja(52, 13, 46, 15,
         "Anuncios != transacciones\n"
         f"{inaccesibles} anuncios inaccesibles en Revolico\n"
         f"{pending} sin precio de análisis (revisión documentada)\n"
         "m² fuera del análisis; tasas ElToque bloqueadas\n"
         "entrevistas no probabilísticas (n=10)",
         "#fce4d6", titulo="Límites")

    ax.text(
        50, 5.5,
        f"Corte: 19/10/2026. Tasas: {fecha_tasas or 'sin fecha'} ({rate_file.name if rate_file else 'sin archivo'}). "
        "Los CSV originales no se modifican; los derivados van a outputs/.",
        ha="center", va="center", fontsize=8,
    )

    flecha(16, 82, 16, 76.5)
    flecha(50, 82, 50, 76.5)
    flecha(83, 82, 83, 76.5)
    flecha(24, 55, 24, 50.5)
    flecha(74, 55, 74, 50.5)
    flecha(24, 33, 24, 28.5)
    flecha(74, 33, 74, 28.5)
    ax.set_title("Esquema del proyecto: fuentes, integración, análisis y límites", fontsize=13, weight="bold")
    return save(fig, "07_esquema_integracion.png")


def write_summary(frame: pd.DataFrame, paths: dict):
    lines = []
    lines.append("# Resumen visual y tabular de fuentes")
    lines.append("")
    lines.append(f"Dataset maestro más reciente: `{newest_master().name}`")
    lines.append("")
    lines.append("## Filas y cobertura")
    fecha_publicada = frame["fecha_publicacion"].fillna("").astype(str).str.strip().ne("")
    fecha_analisis = fecha_publicada | frame["fecha_reextraida"].fillna("").astype(str).str.strip().ne("")
    counts = frame.groupby("fuente").agg(
        anuncios=("id_maestro", "count"),
        precio_publicado=("precio_original", lambda s: int(pd.notna(s).sum())),
        precio_analisis=("precio_analisis", lambda s: int(pd.notna(s).sum())),
        ubicacion_analisis=("ubicacion_analisis", lambda s: int(s.fillna("").astype(str).str.strip().ne("").sum())),
        municipio_homologado=("municipio_homologado", lambda s: int(s.fillna("").astype(str).str.strip().ne("").sum())),
        habitaciones_analisis=("habitaciones_analisis", lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())),
        banos_analisis=("banos_analisis", lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())),
    )
    counts["fecha_publicada"] = fecha_publicada.groupby(frame["fuente"]).sum().astype(int)
    counts["fecha_analisis"] = fecha_analisis.groupby(frame["fuente"]).sum().astype(int)
    lines.append(counts.to_markdown())
    lines.append("")
    lines.append("## Precio central por fuente y moneda")
    usable = frame[frame["precio_analisis"].notna() & frame["moneda_analisis"].ne("")]
    stats = usable.groupby(["fuente", "moneda_analisis"])["precio_analisis"].agg(
        ["count", "median", "mean", "min", "max"]
    ).reset_index()
    stats = stats.rename(
        columns={
            "count": "anuncios",
            "median": "mediana",
            "mean": "media",
            "min": "minimo",
            "max": "maximo",
        }
    )
    lines.append(stats.to_markdown(index=False))
    lines.append("")
    lines.append("## Habitaciones y precio en Cubisima")
    cub = usable[usable["fuente"].eq("Cubisima") & usable["habitaciones_analisis"].notna()]
    if not cub.empty:
        hab_stats = (
            cub.groupby(["moneda_analisis", "habitaciones_analisis"])["precio_analisis"]
            .agg(["count", "median", "mean"])
            .round(2)
            .reset_index()
            .rename(
                columns={
                    "moneda_analisis": "moneda",
                    "habitaciones_analisis": "habitaciones",
                    "count": "anuncios",
                    "median": "mediana",
                    "mean": "media",
                }
            )
        )
        lines.append(hab_stats.to_markdown(index=False))
        lines.append(
            "\nLas celdas con n<5 se muestran para trazabilidad, pero no se interpretan. "
            "La categoria 8+ agrupa 8 habitaciones o mas, incluido el valor 10.5."
        )
    else:
        lines.append("Sin datos suficientes.")
    lines.append("")
    lines.append("## Características declaradas en Cubisima")
    feats = {
        "garaje": "Garaje",
        "piscina": "Piscina",
        "terraza": "Terraza",
        "patio": "Patio",
        "balcon": "Balcón",
        "jardin": "Jardín",
    }
    cubisima = frame[frame["fuente"].eq("Cubisima")]
    for feature, label in feats.items():
        if feature in cubisima.columns:
            series = pd.to_numeric(cubisima[feature], errors="coerce")
            lines.append(
                f"- **{label}**: {int(series.fillna(0).sum())} de {len(cubisima)} anuncios "
                "(los campos ausentes cuentan como no declarados)"
            )
    lines.append("")
    lines.append("## Gráficos generados")
    for name, p in paths.items():
        if p:
            lines.append(f"- `{p.name}`")
    lines.append("")
    lines.append("## Nota metodológica")
    lines.append(
        "Los gráficos y las medianas usan `precio_analisis`/`moneda_analisis`: prefiere el precio "
        "verificado en la revisión manual de descripciones y excluye los campos marcados como "
        "sospechosos; el campo publicado se conserva sin corregir para auditoría. No se comparan "
        "directamente importes de monedas distintas."
    )
    lines.append(
        "Las monedas con menos de 5 anuncios no se grafican (EUR: 3 anuncios; se conserva en las "
        "tablas). Tampoco se grafican las combinaciones fuente-moneda con menos de 10 anuncios "
        "(USD de Cubisima: 8), para no presentar histogramas inestables como si fueran comparables. "
        "Las dos fichas EUR de HogarEnCuba se mantienen como EUR porque la descripción del vendedor "
        "dice literalmente EUR, aunque el título y el JSON-LD digan USD; la ficha EUR de Cubisima "
        "también es explícita en el texto. El conflicto queda documentado en el diccionario de datos."
    )
    lines.append(
        "Municipios y zonas se muestran por separado: `municipio_homologado` solo contiene los 15 "
        "municipios de La Habana; las zonas o barrios de Cubisima no se imputan como municipios. "
        "El maestro tiene 1,532 anuncios: se excluyeron 6 fichas que no eran vivienda en venta y "
        "28 fuera de alcance (otras provincias o inmuebles no residenciales/cuartos)."
    )
    path = OUT / "visualizaciones_resumen.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    frame = pd.read_csv(newest_master(), dtype=str)
    for col in ["precio_original", "habitaciones", "banos"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in ["garaje", "piscina", "terraza", "patio", "balcon", "jardin"]:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame["precio_sospechoso"] = frame["precio_sospechoso"].astype(str).str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    frame["fecha_descarga"] = pd.to_datetime(frame["fecha_descarga"], errors="coerce")
    frame["precio_analisis"], frame["moneda_analisis"] = precios_analisis(frame)
    (
        frame["habitaciones_analisis"],
        frame["banos_analisis"],
        _,
        _,
    ) = detalle_analisis(frame)
    if "municipio_homologado" not in frame.columns:
        frame["municipio_homologado"] = ""
    frame["municipio_homologado"] = frame["municipio_homologado"].fillna("").astype(str).str.strip()
    frame = money_labels(frame)

    paths = {}
    paths["distribucion"] = plot_price_distribution(frame)
    paths["municipio"] = plot_municipality_median(frame)
    paths["habitaciones"] = plot_rooms_price(frame)
    paths["caracteristicas"] = plot_feature_frequency(frame)
    paths["calidad"] = plot_metadata_quality(frame)
    paths["calidad_analisis"] = plot_analysis_coverage(frame)
    tasa_path, rate_file, fecha_tasas = plot_exchange_rates()
    paths["tasas"] = tasa_path
    paths["esquema"] = plot_schema(frame, rate_file, fecha_tasas)
    summary = write_summary(frame, paths)
    if rate_file:
        print(f"Tasa reciente usada como fuente: {rate_file}")
    print(f"Resumen escrito en: {summary}")
    for name, p in paths.items():
        if p:
            print(f"Imagen guardada: {p}")


if __name__ == "__main__":
    main()
