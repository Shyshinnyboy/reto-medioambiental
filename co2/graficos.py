"""Gráficos con matplotlib. Cada función guarda el PNG y devuelve su ruta."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

from co2.analisis import rango_anios
from co2.config import (
    ANIOS_PREDICCION,
    CARPETA_RESULTADOS,
    COLUMNA_EMISIONES,
    COLUMNA_PER_CAPITA,
    nombre_es,
)

# Colores y marcadores en orden fijo. Los tres países por defecto conservan
# siempre el mismo color; el resto ocupa los huecos libres.
COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
MARCADORES = ["s", "o", "^", "D", "v", "P"]
HUECO_FIJO = {"France": 0, "Spain": 1, "Germany": 2}
ORDEN_HUECOS_LIBRES = (3, 4, 5, 0, 1, 2)

COLOR_REJILLA = "#dddddd"
COLOR_NOTA = "#666666"
COLOR_NEUTRO = "#555555"
FUENTE = "Fuente: Our World in Data (github.com/owid/co2-data)"
EJE_CO2_MT = "Emisiones de CO₂ (millones de toneladas)"
PPP = 150  # resolución de los PNG (puntos por pulgada)

Estilos = dict[str, dict[str, str]]


def estilos(paises: list[str]) -> Estilos:
    """{nombre en español: {'color', 'marker'}} para cada país."""
    usados = {HUECO_FIJO[p] for p in paises if p in HUECO_FIJO}
    libres = [h for h in ORDEN_HUECOS_LIBRES if h not in usados]
    resultado = {}
    for pais in paises:
        hueco = HUECO_FIJO[pais] if pais in HUECO_FIJO else libres.pop(0)
        resultado[nombre_es(pais)] = {
            "color": COLORES[hueco],
            "marker": MARCADORES[hueco],
        }
    return resultado


# ---------------------------------------------------------------------------
# Funciones comunes
# ---------------------------------------------------------------------------
def _dibujar_lineas(ax, datos: pd.DataFrame, estilo: Estilos, columna: str) -> None:
    for pais, e in estilo.items():
        serie = (
            datos[datos["pais"] == pais].dropna(subset=[columna]).sort_values("year")
        )
        ax.plot(
            serie["year"],
            serie[columna],
            label=pais,
            color=e["color"],
            marker=e["marker"],
            linewidth=2,
            markersize=5,
        )


def _formato_ejes(ax, primer: int, ultimo: int, max_marcas: int = 10) -> None:
    paso = max(1, -(-(ultimo - primer) // max_marcas))  # división redondeando arriba
    ax.set_xticks(range(primer, ultimo + 1, paso))
    ax.set_xlabel("Año")
    ax.set_ylim(bottom=0)
    ax.grid(True, color=COLOR_REJILLA, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)


def _guardar(
    fig, nombre_archivo: str, mostrar: bool, nota: str = "", margen_inferior=0.03
) -> Path:
    """Añade la fuente, guarda el PNG y, si se pide, abre la ventana."""
    fig.text(0.01, 0.01, FUENTE + nota, fontsize=8, color=COLOR_NOTA)
    fig.tight_layout(rect=(0, margen_inferior, 1, 1))
    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    ruta = CARPETA_RESULTADOS / nombre_archivo
    fig.savefig(ruta, dpi=PPP)
    print(f"Gráfico guardado en: {ruta}")
    if mostrar:
        print("(Se ha abierto una ventana con el gráfico: ciérrala para continuar)")
        plt.show()
    plt.close(fig)
    return ruta


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------
def grafico_evolucion(filtrado: pd.DataFrame, estilo: Estilos, mostrar: bool) -> Path:
    primer, ultimo = rango_anios(filtrado)
    fig, ax = plt.subplots(figsize=(11, 6))
    _dibujar_lineas(ax, filtrado, estilo, COLUMNA_EMISIONES)
    ax.set_title(
        f"Evolución de las emisiones anuales de CO₂ ({primer}-{ultimo})", fontsize=14
    )
    ax.set_ylabel(EJE_CO2_MT)
    _formato_ejes(ax, primer, ultimo)
    ax.legend(title="País", frameon=False)
    return _guardar(fig, "evolucion_co2.png", mostrar)


def grafico_prediccion(
    filtrado: pd.DataFrame, prediccion: pd.DataFrame, estilo: Estilos, mostrar: bool
) -> Path:
    primer, ultimo = rango_anios(filtrado)
    fin = ultimo + ANIOS_PREDICCION
    fig, ax = plt.subplots(figsize=(11, 6))
    _dibujar_lineas(ax, filtrado, estilo, COLUMNA_EMISIONES)

    for pais, e in estilo.items():
        # La línea discontinua empieza en el último dato real para que no haya hueco
        real = filtrado.loc[
            (filtrado["pais"] == pais) & (filtrado["year"] == ultimo), COLUMNA_EMISIONES
        ]
        prevista = prediccion[prediccion["pais"] == pais]
        ax.plot(
            [ultimo, *prevista["year"]],
            [*real, *prevista["co2_predicho"]],
            color=e["color"],
            linestyle="--",
            linewidth=2,
            marker=e["marker"],
            markersize=5,
            markerfacecolor="white",
        )

    ax.axvline(ultimo + 0.5, color=COLOR_NEUTRO, linestyle=":", linewidth=1)
    ax.set_title(
        f"Emisiones de CO₂: datos {primer}-{ultimo} y predicción hasta {fin}",
        fontsize=14,
    )
    ax.set_ylabel(EJE_CO2_MT)
    _formato_ejes(ax, primer, fin)

    # Leyenda: un elemento por país y otros dos para el tipo de línea
    manejadores, etiquetas = ax.get_legend_handles_labels()
    manejadores += [
        Line2D([], [], color=COLOR_NEUTRO, linewidth=2),
        Line2D([], [], color=COLOR_NEUTRO, linewidth=2, linestyle="--"),
    ]
    etiquetas += ["Datos reales", "Predicción (regresión lineal)"]
    ax.legend(manejadores, etiquetas, frameon=False)
    return _guardar(
        fig, "prediccion_co2.png", mostrar, nota=" · Predicción: regresión lineal"
    )


def grafico_total_vs_per_capita(
    filtrado: pd.DataFrame, estilo: Estilos, mostrar: bool
) -> Path:
    """Dos paneles, cada medida con su propio eje (no se mezclan escalas)."""
    primer, ultimo = rango_anios(filtrado)
    fig, (ax_total, ax_hab) = plt.subplots(1, 2, figsize=(13, 5.5))
    paneles = [
        (
            ax_total,
            COLUMNA_EMISIONES,
            "Emisiones totales",
            "Millones de toneladas de CO₂",
        ),
        (
            ax_hab,
            COLUMNA_PER_CAPITA,
            "Emisiones por habitante",
            "Toneladas de CO₂ por habitante",
        ),
    ]
    for ax, columna, titulo, eje_y in paneles:
        _dibujar_lineas(ax, filtrado, estilo, columna)
        ax.set_title(titulo)
        ax.set_ylabel(eje_y)
        _formato_ejes(ax, primer, ultimo, max_marcas=6)

    # Leyenda común debajo de los paneles para no tapar las líneas
    fig.legend(
        *ax_total.get_legend_handles_labels(),
        loc="lower center",
        ncol=len(estilo),
        frameon=False,
        bbox_to_anchor=(0.5, 0.04),
    )
    fig.suptitle(
        f"Emisiones de CO₂ totales y por habitante ({primer}-{ultimo})", fontsize=14
    )
    return _guardar(fig, "total_vs_per_capita.png", mostrar, margen_inferior=0.1)
