"""Obtención de los datos de OWID y funciones de apoyo para explorarlos."""

from pathlib import Path

import pandas as pd
import requests

from co2.config import ARCHIVO_CODEBOOK, ARCHIVO_DATOS, CARPETA_DATOS, URL_BASE

CAMPOS_CLAVE = ["country", "iso_code", "year", "population", "co2", "co2_per_capita"]
GASES = ("co2", "ghg", "methane", "nitrous_oxide")
SEGUNDOS_ESPERA = 60


class ErrorDescarga(Exception):
    """No se ha podido descargar un archivo del repositorio de OWID."""


def descargar(nombre_archivo: str, carpeta: Path = CARPETA_DATOS) -> Path:
    """Descarga un archivo del repositorio de OWID si no existe ya en local."""
    destino = carpeta / nombre_archivo
    if destino.exists():
        print(f"Usando copia local: {destino.name}")
        return destino

    url = URL_BASE + nombre_archivo
    print(f"Descargando {url} ...")
    try:
        respuesta = requests.get(url, timeout=SEGUNDOS_ESPERA)
        respuesta.raise_for_status()
    except requests.RequestException as error:
        raise ErrorDescarga(
            f"No se ha podido descargar {nombre_archivo}.\n"
            "Comprueba la conexión a internet y vuelve a intentarlo.\n"
            f"Detalle: {error}"
        ) from error

    carpeta.mkdir(exist_ok=True)
    destino.write_bytes(respuesta.content)
    print(f"Guardado en: {destino}")
    return destino


def cargar_datos() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (datos, codebook). El codebook describe cada columna y su unidad."""
    datos = pd.read_csv(descargar(ARCHIVO_DATOS))
    codebook = pd.read_csv(descargar(ARCHIVO_CODEBOOK))
    return datos, codebook


def columnas_emisiones(df: pd.DataFrame) -> list[str]:
    """Columnas con cantidades de emisiones (sin las de cambio de temperatura)."""
    return [
        columna
        for columna in df.columns
        if any(gas in columna for gas in GASES) and "temperature" not in columna
    ]


def resumen_nulos(df: pd.DataFrame, campos: list[str]) -> pd.DataFrame:
    """Número y porcentaje de valores nulos de cada campo."""
    nulos = df[campos].isna().sum()
    return pd.DataFrame({"nulos": nulos, "porcentaje": nulos / len(df) * 100})


def entidades_sin_iso(df: pd.DataFrame) -> list[str]:
    """Entidades sin código ISO: agregados como continentes o grupos de países."""
    return sorted(df.loc[df["iso_code"].isna(), "country"].unique())
