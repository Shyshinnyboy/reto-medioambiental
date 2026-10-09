"""Exportación de los resultados a CSV (separador ';' y coma decimal, para Excel)."""

from pathlib import Path

import pandas as pd

from co2.analisis import PeriodoInsuficiente, calcular_prediccion, resumen_por_pais
from co2.config import (
    CARPETA_RESULTADOS,
    COLUMNA_EMISIONES,
    COLUMNA_PER_CAPITA,
    COLUMNA_POBLACION,
)

ARCHIVO_PREDICCION = "prediccion_co2.csv"
OPCIONES_CSV = {
    "sep": ";",
    "decimal": ",",
    "encoding": "utf-8-sig",
    "float_format": "%.3f",
}


def _tabla_emisiones(filtrado: pd.DataFrame) -> pd.DataFrame:
    """Datos anuales usados en el análisis, con nombres de columna en español."""
    columnas = {
        "pais": "pais",
        "year": "anio",
        COLUMNA_EMISIONES: "co2_mt",
        COLUMNA_PER_CAPITA: "co2_per_capita_t",
        COLUMNA_POBLACION: "poblacion",
    }
    tabla = filtrado[list(columnas)].rename(columns=columnas)
    tabla["poblacion"] = tabla["poblacion"].round().astype("Int64")
    return tabla.sort_values(["pais", "anio"])


def exportar_csv(
    filtrado: pd.DataFrame, carpeta: Path = CARPETA_RESULTADOS
) -> list[tuple[Path, int]]:
    """Guarda los CSV y devuelve [(ruta, número de filas)]."""
    tablas = {
        "emisiones_filtradas.csv": (_tabla_emisiones(filtrado), False),
        "resumen_por_pais.csv": (resumen_por_pais(filtrado), True),
    }
    try:
        _, prediccion = calcular_prediccion(filtrado)
        prediccion = prediccion.rename(
            columns={"year": "anio", "co2_predicho": "co2_predicho_mt"}
        )
        tablas[ARCHIVO_PREDICCION] = (prediccion, False)
    except PeriodoInsuficiente:
        # Con muy pocos años no hay predicción: se borra la de un análisis anterior
        (carpeta / ARCHIVO_PREDICCION).unlink(missing_ok=True)

    carpeta.mkdir(exist_ok=True)
    guardados = []
    for nombre_archivo, (tabla, con_indice) in tablas.items():
        ruta = carpeta / nombre_archivo
        tabla.to_csv(ruta, index=con_indice, **OPCIONES_CSV)
        guardados.append((ruta, len(tabla)))
    return guardados
