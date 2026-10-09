"""
Cálculos del análisis. Ninguna función imprime ni dibuja: todas reciben y
devuelven tablas de pandas, para poder probarlas y reutilizarlas.
"""

import numpy as np
import pandas as pd

from co2.config import (
    ANIOS_PREDICCION,
    COLUMNA_EMISIONES,
    COLUMNA_PER_CAPITA,
    COLUMNA_POBLACION,
    MIN_ANIOS_PERIODO,
    MIN_ANIOS_PREDICCION,
    Periodo,
    nombre_es,
)

COLUMNAS_NUMERICAS = ["year", COLUMNA_EMISIONES, COLUMNA_PER_CAPITA, COLUMNA_POBLACION]


class PeriodoInsuficiente(ValueError):
    """No hay suficientes años con datos para hacer el cálculo."""


# ---------------------------------------------------------------------------
# Limpieza y filtrado
# ---------------------------------------------------------------------------
def limpiar(df: pd.DataFrame, paises: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Se queda con los países pedidos y devuelve (válidos, descartados).

    Un registro es válido si tiene año y unas emisiones totales numéricas y no
    negativas. Las emisiones por habitante pueden quedar vacías (NaN): se
    tratan aparte en la comparación total / por habitante.
    """
    datos = df.loc[df["country"].isin(paises), ["country", *COLUMNAS_NUMERICAS]].copy()
    datos["pais"] = datos["country"].map(nombre_es)

    # Cualquier valor no numérico pasa a NaN
    for columna in COLUMNAS_NUMERICAS:
        datos[columna] = pd.to_numeric(datos[columna], errors="coerce")

    # .ge(0) es False para NaN, así que también descarta las emisiones vacías
    validos = datos["year"].notna() & datos[COLUMNA_EMISIONES].ge(0)
    return datos[validos].astype({"year": int}), datos[~validos]


def anios_comunes(datos: pd.DataFrame) -> list[int]:
    """Años en los que todos los países tienen dato (años comparables)."""
    anios_por_pais = [set(grupo["year"]) for _, grupo in datos.groupby("pais")]
    if not anios_por_pais:
        return []
    return sorted(set.intersection(*anios_por_pais))


def filtrar_periodo(
    datos: pd.DataFrame, periodo: Periodo
) -> tuple[pd.DataFrame, list[int]]:
    """Devuelve (registros del período, años seleccionados)."""
    comunes = anios_comunes(datos)
    if periodo.ultimos is not None:
        seleccion = comunes[-periodo.ultimos :]
    else:
        seleccion = [a for a in comunes if periodo.desde <= a <= periodo.hasta]

    if len(seleccion) < MIN_ANIOS_PERIODO:
        raise PeriodoInsuficiente(
            f"en ese período hay {len(seleccion)} años con datos de todos los "
            f"países y se necesitan al menos {MIN_ANIOS_PERIODO}"
        )
    return datos[datos["year"].isin(seleccion)].copy(), seleccion


def rango_anios(filtrado: pd.DataFrame) -> tuple[int, int]:
    """Primer y último año de los datos."""
    return int(filtrado["year"].min()), int(filtrado["year"].max())


# ---------------------------------------------------------------------------
# Medias y variación
# ---------------------------------------------------------------------------
def calcular_medias(
    filtrado: pd.DataFrame, columna: str = COLUMNA_EMISIONES
) -> pd.Series:
    """Media anual de cada país, de mayor a menor."""
    return filtrado.groupby("pais")[columna].mean().sort_values(ascending=False)


def calcular_variacion(
    filtrado: pd.DataFrame, columna: str = COLUMNA_EMISIONES
) -> pd.DataFrame:
    """
    Variación porcentual entre el primer y el último año, ordenada de mayor
    reducción a mayor aumento. Si el valor inicial es 0 no se puede calcular
    y queda como NaN.
    """
    primer, ultimo = rango_anios(filtrado)
    tabla = filtrado.pivot(index="year", columns="pais", values=columna)
    inicial, final = tabla.loc[primer], tabla.loc[ultimo]
    variacion = (final - inicial) / inicial.where(inicial != 0) * 100
    resultado = pd.DataFrame(
        {"valor_inicial": inicial, "valor_final": final, "variacion_pct": variacion}
    )
    return resultado.sort_values("variacion_pct")


def pais_mayor_reduccion(variacion: pd.DataFrame) -> tuple[str, float] | None:
    """(país, variación %) con la variación más negativa, o None si no hay datos."""
    validas = variacion["variacion_pct"].dropna()
    if validas.empty:
        return None
    pais = validas.idxmin()
    return pais, float(validas[pais])


# ---------------------------------------------------------------------------
# Predicción con regresión lineal
# ---------------------------------------------------------------------------
def coeficiente_r2(y: np.ndarray, ajuste: np.ndarray) -> float:
    """Proporción de la variación de los datos que explica el ajuste (0 a 1)."""
    suma_total = np.sum((y - y.mean()) ** 2)
    if suma_total == 0:
        return float("nan")
    return float(1 - np.sum((y - ajuste) ** 2) / suma_total)


def calcular_prediccion(
    filtrado: pd.DataFrame, anios: int = ANIOS_PREDICCION
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ajusta una recta (co2 = pendiente * año + ordenada) por mínimos cuadrados
    a los datos de cada país y la prolonga `anios` años.

    Devuelve (modelos, predicción):
      - modelos: pendiente (Mt/año) y R² de cada país.
      - predicción: país, año y emisiones previstas (nunca negativas).
    """
    if filtrado["year"].nunique() < MIN_ANIOS_PREDICCION:
        raise PeriodoInsuficiente(
            f"la regresión necesita al menos {MIN_ANIOS_PREDICCION} años de datos"
        )

    _, ultimo = rango_anios(filtrado)
    futuros = np.arange(ultimo + 1, ultimo + anios + 1)
    modelos, filas = {}, []

    for pais, grupo in filtrado.groupby("pais"):
        x = grupo["year"].to_numpy(dtype=float)
        y = grupo[COLUMNA_EMISIONES].to_numpy(dtype=float)
        pendiente, ordenada = np.polyfit(x, y, 1)
        modelos[pais] = {
            "pendiente_mt_anio": pendiente,
            "r2": coeficiente_r2(y, pendiente * x + ordenada),
        }
        previstos = np.clip(pendiente * futuros + ordenada, 0, None)
        filas += [
            {"pais": pais, "year": int(anio), "co2_predicho": valor}
            for anio, valor in zip(futuros, previstos, strict=True)
        ]

    tabla_modelos = pd.DataFrame.from_dict(modelos, orient="index")
    tabla_modelos.index.name = "pais"
    return tabla_modelos, pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Emisiones totales frente a emisiones por habitante
# ---------------------------------------------------------------------------
def calcular_total_vs_per_capita(filtrado: pd.DataFrame) -> pd.DataFrame:
    """Medias y variaciones de las emisiones totales, por habitante y población."""
    tabla = filtrado.groupby("pais").agg(
        co2_medio_mt=(COLUMNA_EMISIONES, "mean"),
        co2_per_capita_medio_t=(COLUMNA_PER_CAPITA, "mean"),
        poblacion_media=(COLUMNA_POBLACION, "mean"),
    )
    variaciones = {
        "variacion_total_pct": COLUMNA_EMISIONES,
        "variacion_per_capita_pct": COLUMNA_PER_CAPITA,
        "variacion_poblacion_pct": COLUMNA_POBLACION,
    }
    for nombre, columna in variaciones.items():
        tabla[nombre] = calcular_variacion(filtrado, columna)["variacion_pct"]
    return tabla.sort_values("co2_medio_mt", ascending=False)


# ---------------------------------------------------------------------------
# Resumen para exportar
# ---------------------------------------------------------------------------
def resumen_por_pais(filtrado: pd.DataFrame) -> pd.DataFrame:
    """Una fila por país con todos los resultados del análisis."""
    primer, ultimo = rango_anios(filtrado)
    variacion = calcular_variacion(filtrado)
    comparacion = calcular_total_vs_per_capita(filtrado)

    resumen = pd.DataFrame(
        {
            "co2_medio_mt": comparacion["co2_medio_mt"],
            "primer_anio": primer,
            "co2_primer_anio_mt": variacion["valor_inicial"],
            "ultimo_anio": ultimo,
            "co2_ultimo_anio_mt": variacion["valor_final"],
            "variacion_pct": variacion["variacion_pct"],
            "co2_per_capita_medio_t": comparacion["co2_per_capita_medio_t"],
            "variacion_per_capita_pct": comparacion["variacion_per_capita_pct"],
        }
    )
    try:
        modelos, _ = calcular_prediccion(filtrado)
        resumen["tendencia_mt_anio"] = modelos["pendiente_mt_anio"]
        resumen["r2_regresion"] = modelos["r2"]
    except PeriodoInsuficiente:
        pass  # con muy pocos años el resumen va sin la tendencia

    resumen.index.name = "pais"
    return resumen.sort_values("variacion_pct")
