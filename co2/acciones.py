"""
Acciones del programa. Cada una combina cálculos (analisis), salida por
pantalla (informes) y gráficos, y recibe (datos filtrados, configuración).
"""

import pandas as pd

from co2 import analisis, graficos, informes
from co2.config import ANIOS_PREDICCION, COLUMNA_PER_CAPITA, Configuracion
from co2.exportar import exportar_csv


def preparar(df: pd.DataFrame, config: Configuracion) -> pd.DataFrame | None:
    """Limpia y filtra los datos. Devuelve None si el período no tiene datos."""
    informes.titulo("PROCESAMIENTO")
    validos, descartados = analisis.limpiar(df, config.paises)
    informes.mostrar_descartados(
        len(validos) + len(descartados), descartados, config.paises
    )
    try:
        filtrado, anios = analisis.filtrar_periodo(validos, config.periodo)
    except analisis.PeriodoInsuficiente as error:
        print(f"\nNo se puede analizar: {error}. Elige otros años.")
        return None
    informes.mostrar_periodo(anios, config.periodo)
    return filtrado


def ver_reduccion(filtrado: pd.DataFrame, config: Configuracion) -> None:
    informes.titulo("MEDIAS Y MAYOR REDUCCIÓN")
    variacion = analisis.calcular_variacion(filtrado)
    informes.mostrar_medias_y_reduccion(
        analisis.calcular_medias(filtrado),
        variacion,
        analisis.pais_mayor_reduccion(variacion),
        *analisis.rango_anios(filtrado),
    )
    graficos.grafico_evolucion(
        filtrado, graficos.estilos(config.paises), config.mostrar_ventanas
    )


def ver_prediccion(filtrado: pd.DataFrame, config: Configuracion) -> None:
    informes.titulo(
        f"PREDICCIÓN DE EMISIONES ({ANIOS_PREDICCION} AÑOS) - REGRESIÓN LINEAL"
    )
    try:
        modelos, prediccion = analisis.calcular_prediccion(filtrado)
    except analisis.PeriodoInsuficiente as error:
        print(f"No se puede calcular la predicción: {error}.")
        return
    informes.mostrar_prediccion(modelos, prediccion)
    graficos.grafico_prediccion(
        filtrado, prediccion, graficos.estilos(config.paises), config.mostrar_ventanas
    )


def ver_total_vs_per_capita(filtrado: pd.DataFrame, config: Configuracion) -> None:
    informes.titulo("COMPARACIÓN: EMISIONES TOTALES vs. EMISIONES POR HABITANTE")
    informes.mostrar_total_vs_per_capita(
        analisis.calcular_total_vs_per_capita(filtrado),
        int(filtrado[COLUMNA_PER_CAPITA].isna().sum()),
    )
    graficos.grafico_total_vs_per_capita(
        filtrado, graficos.estilos(config.paises), config.mostrar_ventanas
    )


def exportar(filtrado: pd.DataFrame, config: Configuracion) -> None:
    informes.titulo("EXPORTACIÓN DE RESULTADOS A CSV")
    informes.mostrar_archivos(exportar_csv(filtrado))


TODAS = (ver_reduccion, ver_prediccion, ver_total_vs_per_capita, exportar)


def ejecutar(df: pd.DataFrame, config: Configuracion, pasos) -> None:
    """Prepara los datos una vez y ejecuta las acciones indicadas."""
    filtrado = preparar(df, config)
    if filtrado is None:
        return
    for paso in pasos:
        paso(filtrado, config)


def ejecutar_todo(
    df: pd.DataFrame, codebook: pd.DataFrame, config: Configuracion
) -> None:
    informes.mostrar_exploracion(df, codebook)
    ejecutar(df, config, TODAS)
