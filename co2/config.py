"""Configuración general: rutas, parámetros del análisis y nombres de países."""

from dataclasses import dataclass, field
from pathlib import Path

# Origen de los datos y carpetas del proyecto
URL_BASE = "https://raw.githubusercontent.com/owid/co2-data/master/"
ARCHIVO_DATOS = "owid-co2-data.csv"
ARCHIVO_CODEBOOK = "owid-co2-codebook.csv"

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_DATOS = CARPETA_PROYECTO / "datos"
CARPETA_RESULTADOS = CARPETA_PROYECTO / "resultados"

# Columnas del dataset que se analizan
COLUMNA_EMISIONES = "co2"  # millones de toneladas (Mt)
COLUMNA_PER_CAPITA = "co2_per_capita"  # toneladas por habitante
COLUMNA_POBLACION = "population"  # personas

# Parámetros del análisis
PAISES_POR_DEFECTO = ("Spain", "France", "Germany")
NUM_ANIOS_POR_DEFECTO = 20
OPCIONES_ULTIMOS_ANIOS = (10, 20, 30)
ANIOS_PREDICCION = 5
MAX_PAISES = 6
MIN_ANIOS_PERIODO = 2
MIN_ANIOS_PREDICCION = 3

# Países que se ofrecen en el menú, con su nombre en español
NOMBRES_ES = {
    "Spain": "España",
    "France": "Francia",
    "Germany": "Alemania",
    "Italy": "Italia",
    "Portugal": "Portugal",
    "United Kingdom": "Reino Unido",
    "Netherlands": "Países Bajos",
    "Belgium": "Bélgica",
    "Poland": "Polonia",
    "Sweden": "Suecia",
    "United States": "Estados Unidos",
    "China": "China",
    "Japan": "Japón",
    "India": "India",
}


def nombre_es(country: str) -> str:
    """Nombre del país en español (o el original si no hay traducción)."""
    return NOMBRES_ES.get(country, country)


@dataclass(frozen=True)
class Periodo:
    """Últimos N años con datos (`ultimos`) o un rango de años (`desde`-`hasta`)."""

    ultimos: int | None = NUM_ANIOS_POR_DEFECTO
    desde: int | None = None
    hasta: int | None = None

    @classmethod
    def rango(cls, desde: int, hasta: int) -> "Periodo":
        return cls(ultimos=None, desde=desde, hasta=hasta)

    def describir(self) -> str:
        if self.ultimos is not None:
            return f"últimos {self.ultimos} años disponibles"
        return f"{self.desde}-{self.hasta}"


@dataclass
class Configuracion:
    """Lo que se está analizando y si los gráficos se abren en una ventana."""

    paises: list[str] = field(default_factory=lambda: list(PAISES_POR_DEFECTO))
    periodo: Periodo = field(default_factory=Periodo)
    mostrar_ventanas: bool = True
