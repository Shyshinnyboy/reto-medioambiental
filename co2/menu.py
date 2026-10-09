"""Menú interactivo: todo se elige escribiendo un número y pulsando Enter."""

import pandas as pd

from co2 import acciones, analisis, informes
from co2.config import (
    MAX_PAISES,
    MIN_ANIOS_PERIODO,
    NOMBRES_ES,
    OPCIONES_ULTIMOS_ANIOS,
    PAISES_POR_DEFECTO,
    Configuracion,
    Periodo,
    nombre_es,
)

TEXTO_MENU = """
¿Qué quieres hacer? Escribe el número y pulsa Enter.

  VER RESULTADOS
   1. Medias, país con mayor reducción y gráfico de evolución
   2. Predicción de emisiones para los próximos 5 años
   3. Comparar emisiones totales y por habitante
   4. Todo lo anterior y además exportar a CSV

  CAMBIAR LO QUE SE ANALIZA
   5. Cambiar países
   6. Cambiar años

  OTROS
   7. Exportar resultados a CSV (carpeta resultados)
   8. Ver cómo es el dataset (exploración de los datos)
   0. Salir"""

# Opciones que trabajan sobre los datos filtrados -> acciones que ejecutan
ACCIONES_POR_OPCION = {
    "1": (acciones.ver_reduccion,),
    "2": (acciones.ver_prediccion,),
    "3": (acciones.ver_total_vs_per_capita,),
    "4": acciones.TODAS,
    "7": (acciones.exportar,),
}


def leer(texto: str) -> str:
    return input(texto).strip()


def elegir_paises(df: pd.DataFrame) -> list[str]:
    """Muestra una lista numerada y devuelve los países elegidos."""
    disponibles = set(df["country"])
    lista = [pais for pais in NOMBRES_ES if pais in disponibles]
    informes.titulo("CAMBIAR PAÍSES")
    for numero, pais in enumerate(lista, start=1):
        print(f"  {numero:>2}. {nombre_es(pais)}")
    print(
        f"\nEscribe los números de los países separados por comas "
        f"(máximo {MAX_PAISES})."
    )
    print("Ejemplo: 1,2,3   ·   Enter sin escribir nada = España, Francia y Alemania")

    while True:
        texto = leer("Países: ").replace(" ", "")
        if not texto:
            return list(PAISES_POR_DEFECTO)
        try:
            numeros = list(dict.fromkeys(int(x) for x in texto.split(",") if x))
        except ValueError:
            print("Escribe solo números separados por comas, por ejemplo: 1,4,5")
            continue

        if not numeros:
            print("No has elegido ningún país.")
        elif any(not 1 <= n <= len(lista) for n in numeros):
            print(f"Los números deben estar entre 1 y {len(lista)}.")
        elif len(numeros) > MAX_PAISES:
            print(f"Como máximo {MAX_PAISES} países.")
        else:
            elegidos = [lista[n - 1] for n in numeros]
            print("Elegidos: " + ", ".join(map(nombre_es, elegidos)))
            return elegidos


def leer_anio(texto: str, minimo: int, maximo: int) -> int:
    while True:
        valor = leer(texto)
        if valor.isdigit() and minimo <= int(valor) <= maximo:
            return int(valor)
        print(f"Escribe un año entre {minimo} y {maximo}.")


def elegir_periodo(anios: list[int]) -> Periodo:
    """Ofrece los períodos habituales o un rango de años elegido."""
    informes.titulo("CAMBIAR AÑOS")
    if len(anios) < MIN_ANIOS_PERIODO:
        print("Los países elegidos no tienen años en común. Se mantiene el período.")
        return Periodo()

    print(f"Hay datos de todos los países elegidos entre {anios[0]} y {anios[-1]}.\n")
    opciones = {str(i): n for i, n in enumerate(OPCIONES_ULTIMOS_ANIOS, start=1)}
    for clave, num_anios in opciones.items():
        print(f"   {clave}. Últimos {num_anios} años")
    opcion_rango = str(len(opciones) + 1)
    print(f"   {opcion_rango}. Elegir el año de inicio y el de fin")

    while True:
        opcion = leer("\nOpción: ")
        if opcion in opciones:
            return Periodo(ultimos=opciones[opcion])
        if opcion == opcion_rango:
            desde = leer_anio("Año de inicio: ", anios[0], anios[-1] - 1)
            hasta = leer_anio("Año de fin:    ", desde + 1, anios[-1])
            return Periodo.rango(desde, hasta)
        print(f"Escribe un número del 1 al {opcion_rango}.")


def menu(df: pd.DataFrame, codebook: pd.DataFrame) -> None:
    config = Configuracion()

    while True:
        informes.titulo("ANÁLISIS DE EMISIONES DE CO2")
        print("Ahora mismo se analizan:")
        print(f"   Países: {', '.join(map(nombre_es, config.paises))}")
        print(f"   Años:   {config.periodo.describir()}")
        print(TEXTO_MENU)
        opcion = leer("\nOpción: ")

        if opcion == "0":
            break
        if opcion == "5":
            config.paises = elegir_paises(df)
            continue
        if opcion == "6":
            validos, _ = analisis.limpiar(df, config.paises)
            config.periodo = elegir_periodo(analisis.anios_comunes(validos))
            continue

        if opcion == "8":
            informes.mostrar_exploracion(df, codebook)
        elif opcion in ACCIONES_POR_OPCION:
            acciones.ejecutar(df, config, ACCIONES_POR_OPCION[opcion])
        else:
            print("Opción no válida: escribe un número del 0 al 8.")
            continue

        # Pausa para poder leer los resultados antes de volver al menú
        leer("\nPulsa Enter para volver al menú...")
