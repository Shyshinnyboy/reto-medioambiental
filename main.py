"""
Reto práctico: Analista de datos medioambientales
-------------------------------------------------
Evolución de las emisiones de CO2 de España, Francia y Alemania (o de los
países que se elijan en el menú) con datos de Our World in Data
(https://github.com/owid/co2-data).

Uso:
  python main.py          -> menú interactivo
  python main.py --todo   -> todo con la configuración por defecto, sin menú
"""

import argparse
import sys

from co2.acciones import ejecutar_todo
from co2.config import Configuracion
from co2.datos import ErrorDescarga, cargar_datos
from co2.menu import menu


def leer_argumentos(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Análisis de las emisiones de CO2 (datos de Our World in Data)."
    )
    parser.add_argument(
        "--todo",
        action="store_true",
        help="ejecuta todo el análisis sin menú; los gráficos se guardan sin abrirse",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argumentos = leer_argumentos(argv)
    try:
        df, codebook = cargar_datos()
        if argumentos.todo:
            ejecutar_todo(df, codebook, Configuracion(mostrar_ventanas=False))
        else:
            menu(df, codebook)
    except ErrorDescarga as error:
        print(f"\nError: {error}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print()  # Ctrl+C o Ctrl+D: salir sin mostrar el error
    print("¡Hasta luego!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
