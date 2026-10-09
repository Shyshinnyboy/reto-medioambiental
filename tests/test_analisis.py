"""Tests de los cálculos con datos pequeños inventados (no usan internet)."""

import math

import pandas as pd
import pytest

from co2.analisis import (
    PeriodoInsuficiente,
    anios_comunes,
    calcular_medias,
    calcular_prediccion,
    calcular_total_vs_per_capita,
    calcular_variacion,
    filtrar_periodo,
    limpiar,
    pais_mayor_reduccion,
    rango_anios,
    resumen_por_pais,
)
from co2.config import Periodo
from co2.datos import columnas_emisiones
from co2.graficos import estilos


def fila(pais, anio, co2, poblacion=1_000_000):
    per_capita = None if co2 is None else co2 * 1e6 / poblacion
    return {
        "country": pais,
        "year": anio,
        "co2": co2,
        "co2_per_capita": per_capita,
        "population": poblacion,
    }


@pytest.fixture
def df():
    """
    Spain:   2000-2005, baja 10 Mt cada año (100 -> 50).
    France:  2000-2005, constante en 200 Mt; la población crece un 10 %.
    Germany: 2001-2005 (le falta 2000), de 300 a 260 Mt.
    """
    filas = [fila("Spain", 2000 + i, 100 - 10 * i) for i in range(6)]
    filas += [
        fila("France", 2000 + i, 200, poblacion=1_000_000 + 20_000 * i)
        for i in range(6)
    ]
    filas += [fila("Germany", 2001 + i, 300 - 10 * i) for i in range(5)]
    filas += [fila("Italy", 2000, 50)]  # no se pide: debe ignorarse
    return pd.DataFrame(filas)


@pytest.fixture
def validos(df):
    datos, _ = limpiar(df, ["Spain", "France", "Germany"])
    return datos


# ---------------------------------------------------------------------------
# Limpieza y filtrado
# ---------------------------------------------------------------------------
def test_limpiar_descarta_registros_invalidos():
    df = pd.DataFrame(
        [
            fila("Spain", 2000, 10),
            fila("Spain", 2001, None),  # nulo
            fila("Spain", 2002, -5),  # negativo
            {**fila("Spain", 2003, 10), "co2": "abc"},  # no numérico
            {**fila("Spain", 2004, 10), "year": None},  # sin año
        ]
    )
    validos, descartados = limpiar(df, ["Spain"])
    assert list(validos["year"]) == [2000]
    assert len(descartados) == 4
    assert set(validos["pais"]) == {"España"}


def test_limpiar_solo_deja_los_paises_pedidos(validos):
    assert set(validos["pais"]) == {"España", "Francia", "Alemania"}


def test_anios_comunes(validos):
    assert anios_comunes(validos) == [2001, 2002, 2003, 2004, 2005]


def test_filtrar_ultimos_anios(validos):
    filtrado, anios = filtrar_periodo(validos, Periodo(ultimos=3))
    assert anios == [2003, 2004, 2005]
    assert rango_anios(filtrado) == (2003, 2005)
    assert len(filtrado) == 9  # 3 países x 3 años


def test_filtrar_rango(validos):
    _, anios = filtrar_periodo(validos, Periodo.rango(1990, 2002))
    assert anios == [2001, 2002]  # 2000 no es común a los tres países


def test_filtrar_periodo_sin_anios_suficientes(validos):
    with pytest.raises(PeriodoInsuficiente):
        filtrar_periodo(validos, Periodo.rango(2005, 2010))


# ---------------------------------------------------------------------------
# Medias y variación
# ---------------------------------------------------------------------------
def test_calcular_medias(validos):
    filtrado, _ = filtrar_periodo(validos, Periodo(ultimos=5))
    medias = calcular_medias(filtrado)
    assert list(medias.index) == ["Alemania", "Francia", "España"]
    assert medias["España"] == pytest.approx(70)  # 90, 80, 70, 60, 50


def test_variacion_y_mayor_reduccion(validos):
    filtrado, _ = filtrar_periodo(validos, Periodo(ultimos=5))
    variacion = calcular_variacion(filtrado)
    assert variacion.at["España", "variacion_pct"] == pytest.approx(-100 * 40 / 90)
    assert variacion.at["Francia", "variacion_pct"] == pytest.approx(0)
    assert pais_mayor_reduccion(variacion) == ("España", pytest.approx(-44.444, 1e-3))


def test_variacion_con_valor_inicial_cero_es_nan():
    df = pd.DataFrame([fila("Spain", 2000, 0), fila("Spain", 2001, 10)])
    validos, _ = limpiar(df, ["Spain"])
    variacion = calcular_variacion(validos)
    assert math.isnan(variacion.at["España", "variacion_pct"])
    assert pais_mayor_reduccion(variacion) is None


# ---------------------------------------------------------------------------
# Predicción
# ---------------------------------------------------------------------------
def test_prediccion_de_una_recta_exacta(validos):
    filtrado, _ = filtrar_periodo(validos, Periodo(ultimos=5))
    modelos, prediccion = calcular_prediccion(filtrado, anios=2)
    assert modelos.at["España", "pendiente_mt_anio"] == pytest.approx(-10)
    assert modelos.at["España", "r2"] == pytest.approx(1)
    espania = prediccion[prediccion["pais"] == "España"]
    assert list(espania["year"]) == [2006, 2007]
    assert list(espania["co2_predicho"]) == pytest.approx([40, 30])


def test_prediccion_con_serie_constante_tiene_r2_nan(validos):
    filtrado, _ = filtrar_periodo(validos, Periodo(ultimos=5))
    modelos, _ = calcular_prediccion(filtrado)
    assert math.isnan(modelos.at["Francia", "r2"])


def test_prediccion_nunca_es_negativa():
    df = pd.DataFrame([fila("Spain", 2000 + i, 30 - 10 * i) for i in range(4)])
    validos, _ = limpiar(df, ["Spain"])
    _, prediccion = calcular_prediccion(validos, anios=3)
    assert (prediccion["co2_predicho"] >= 0).all()


def test_prediccion_necesita_minimo_de_anios(validos):
    filtrado, _ = filtrar_periodo(validos, Periodo(ultimos=2))
    with pytest.raises(PeriodoInsuficiente):
        calcular_prediccion(filtrado)


# ---------------------------------------------------------------------------
# Totales frente a por habitante y resumen
# ---------------------------------------------------------------------------
def test_total_vs_per_capita(validos):
    filtrado, _ = filtrar_periodo(validos, Periodo.rango(2001, 2005))
    tabla = calcular_total_vs_per_capita(filtrado)
    francia = tabla.loc["Francia"]
    # Población de 1,02 M (2001) a 1,10 M (2005); emisiones constantes
    assert francia["variacion_poblacion_pct"] == pytest.approx(100 * 0.08 / 1.02)
    assert francia["variacion_total_pct"] == pytest.approx(0)
    assert francia["variacion_per_capita_pct"] < 0


def test_resumen_por_pais_sin_prediccion_con_dos_anios(validos):
    filtrado, _ = filtrar_periodo(validos, Periodo(ultimos=2))
    resumen = resumen_por_pais(filtrado)
    assert "tendencia_mt_anio" not in resumen.columns
    assert len(resumen) == 3


# ---------------------------------------------------------------------------
# Otros
# ---------------------------------------------------------------------------
def test_columnas_emisiones_excluye_temperatura():
    df = pd.DataFrame(
        columns=["country", "co2", "methane_per_capita", "temperature_change_from_co2"]
    )
    assert columnas_emisiones(df) == ["co2", "methane_per_capita"]


def test_colores_fijos_de_los_paises_por_defecto():
    con_francia = estilos(["Spain", "France", "Germany"])
    sin_francia = estilos(["Spain", "Italy"])
    assert con_francia["España"] == sin_francia["España"]
    assert (
        len({e["color"] for e in estilos(["Spain", "Italy", "Poland"]).values()}) == 3
    )
