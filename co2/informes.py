"""Salida por pantalla: títulos, tablas e interpretación de los resultados."""

from pathlib import Path

import pandas as pd

from co2.config import ANIOS_PREDICCION, Periodo, nombre_es
from co2.datos import CAMPOS_CLAVE, columnas_emisiones, entidades_sin_iso, resumen_nulos

ANCHO = 70
EJEMPLOS_AGREGADOS = 8
MILLON = 1_000_000


def titulo(texto: str) -> None:
    print("\n" + "=" * ANCHO)
    print(texto)
    print("=" * ANCHO)


# ---------------------------------------------------------------------------
# Exploración y procesamiento
# ---------------------------------------------------------------------------
def mostrar_exploracion(df: pd.DataFrame, codebook: pd.DataFrame) -> None:
    titulo("EXPLORACIÓN DE LOS DATOS")
    print(f"Número de registros (filas): {df.shape[0]}")
    print(f"Número de columnas:          {df.shape[1]}")
    print(f"Años cubiertos:              {df['year'].min()} - {df['year'].max()}")
    print(f"Países/regiones distintos:   {df['country'].nunique()}")
    print("\nOrganización: cada fila es una combinación (país, año) y cada")
    print("columna una variable (población, PIB, emisiones por fuente, etc.).")

    info = codebook.set_index("column")
    print("\nCampos principales:")
    for campo in CAMPOS_CLAVE:
        unidad = info["unit"].get(campo)
        unidad = "" if pd.isna(unidad) else f" [{unidad}]"
        print(f"  - {campo:<15}{unidad} {info['title'].get(campo, '')}")

    emisiones = columnas_emisiones(df)
    print(f"\nColumnas con cantidades de emisiones: {len(emisiones)}")
    print("  " + ", ".join(emisiones))

    print("\nValores nulos:")
    total_nulos = int(df.isna().sum().sum())
    print(f"  Celdas nulas: {total_nulos} de {df.size} ({total_nulos / df.size:.1%})")
    filas_con_nulos = int(df.isna().any(axis=1).sum())
    print(f"  Filas con al menos un nulo: {filas_con_nulos} de {len(df)}")
    print("  Nulos en los campos principales:")
    for campo, fila in resumen_nulos(df, CAMPOS_CLAVE).iterrows():
        print(f"    - {campo:<15} {fila['nulos']:>6.0f} ({fila['porcentaje']:.1f} %)")

    agregados = entidades_sin_iso(df)
    print(
        f"\n  Entidades sin iso_code (agregados como continentes o grupos): "
        f"{len(agregados)}"
    )
    print("    Ejemplos: " + ", ".join(agregados[:EJEMPLOS_AGREGADOS]) + ", ...")


def mostrar_descartados(
    total: int, descartados: pd.DataFrame, paises: list[str]
) -> None:
    print(f"Registros de {', '.join(map(nombre_es, paises))}: {total}")
    print(
        "Registros descartados por no tener un valor de emisiones válido: "
        f"{len(descartados)}"
    )
    if not descartados.empty:
        resumen = descartados.groupby("pais")["year"].agg(["count", "min", "max"])
        resumen.columns = ["descartados", "desde", "hasta"]
        print(resumen.to_string())


def mostrar_periodo(anios: list[int], periodo: Periodo) -> None:
    if periodo.ultimos is not None and len(anios) < periodo.ultimos:
        print(
            f"Aviso: solo hay {len(anios)} años con datos de todos los países "
            f"(se pidieron {periodo.ultimos})."
        )
    print(
        f"\nPeríodo analizado: {anios[0]} - {anios[-1]} "
        f"({len(anios)} años con datos de todos los países)"
    )


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------
def mostrar_medias_y_reduccion(
    medias: pd.Series,
    variacion: pd.DataFrame,
    reduccion: tuple[str, float] | None,
    primer: int,
    ultimo: int,
) -> None:
    print("\nEmisiones medias anuales de CO2 en el período (millones de t):")
    for pais, valor in medias.items():
        print(f"  - {pais:<15} {valor:8.2f} Mt")

    tabla = variacion.rename(
        columns={
            "valor_inicial": f"CO2 {primer} (Mt)",
            "valor_final": f"CO2 {ultimo} (Mt)",
            "variacion_pct": "Variación (%)",
        }
    )
    print(f"\nVariación entre {primer} y {ultimo}:")
    print(tabla.round(2).to_string())

    if reduccion is None:
        print("\n>> No se puede calcular la variación (no hay valores iniciales).")
    elif reduccion[1] < 0:
        print(
            f"\n>> Mayor reducción porcentual: {reduccion[0]} ({-reduccion[1]:.2f} %)"
        )
    else:
        print(
            "\n>> Ningún país ha reducido sus emisiones en este período "
            f"(el menor aumento es el de {reduccion[0]}: {reduccion[1]:.2f} %)"
        )


def mostrar_prediccion(modelos: pd.DataFrame, prediccion: pd.DataFrame) -> None:
    print("Modelo por país (recta ajustada a los datos del período):")
    for pais, fila in modelos.iterrows():
        print(
            f"  - {pais:<15} tendencia {fila['pendiente_mt_anio']:+7.2f} Mt/año"
            f"   R² = {fila['r2']:.2f}"
        )

    tabla = prediccion.pivot(index="year", columns="pais", values="co2_predicho")
    print(f"\nEmisiones previstas para los próximos {ANIOS_PREDICCION} años (Mt):")
    print(tabla.round(2).to_string())
    print(
        "\nNota: es un modelo muy simple que supone que la tendencia del período\n"
        "se mantiene. La recta resume los años del período, no parte del último\n"
        "dato, por eso el primer año previsto puede quedar por encima o por debajo\n"
        "del último valor real. Un R² bajo indica que la recta explica mal los datos."
    )


def mostrar_total_vs_per_capita(tabla: pd.DataFrame, sin_dato_per_capita: int) -> None:
    if sin_dato_per_capita:
        print(
            f"Aviso: {sin_dato_per_capita} registros sin dato por habitante; "
            "se ignoran en este apartado."
        )

    vista = pd.DataFrame(
        {
            "CO2 medio (Mt)": tabla["co2_medio_mt"],
            "CO2/hab medio (t)": tabla["co2_per_capita_medio_t"],
            "Población media (M)": tabla["poblacion_media"] / MILLON,
            "Var. total (%)": tabla["variacion_total_pct"],
            "Var. por hab. (%)": tabla["variacion_per_capita_pct"],
            "Var. población (%)": tabla["variacion_poblacion_pct"],
        }
    )
    print(vista.round(2).to_string())
    _interpretar_total_vs_per_capita(tabla)


def _interpretar_total_vs_per_capita(tabla: pd.DataFrame) -> None:
    """Explicación generada a partir de los datos de la tabla."""
    orden_total = list(tabla["co2_medio_mt"].sort_values(ascending=False).index)
    orden_hab = list(tabla["co2_per_capita_medio_t"].sort_values(ascending=False).index)
    print("\nInterpretación:")
    print("  * Las emisiones totales dependen del tamaño del país (población y")
    print("    actividad económica). Las emisiones por habitante eliminan el efecto")
    print("    de la población y permiten comparar países de distinto tamaño.")
    print(f"  * Orden por emisiones totales:   {' > '.join(orden_total)}")
    print(f"  * Orden por emisiones por hab.:  {' > '.join(orden_hab)}")
    if orden_total != orden_hab:
        print("    El orden cambia: un país puede emitir más en total solo por tener")
        print("    más habitantes, sin que cada habitante emita más.")

    mayor, menor = orden_total[0], orden_total[-1]
    if mayor != menor:
        veces_total = tabla.at[mayor, "co2_medio_mt"] / tabla.at[menor, "co2_medio_mt"]
        veces_hab = (
            tabla.at[mayor, "co2_per_capita_medio_t"]
            / tabla.at[menor, "co2_per_capita_medio_t"]
        )
        print(
            f"  * {mayor} emite de media {veces_total:.1f} veces más CO₂ que {menor},"
        )
        print(f"    pero por habitante la diferencia es de {veces_hab:.1f} veces.")

    for pais, fila in tabla.iterrows():
        print(
            f"  * {pais}: población {fila['variacion_poblacion_pct']:+.1f} %, "
            f"emisiones totales {fila['variacion_total_pct']:+.1f} %, "
            f"por habitante {fila['variacion_per_capita_pct']:+.1f} %."
        )
    print("    Cuando la población crece, la variación por habitante queda por debajo")
    print("    de la total: si las emisiones bajan, bajan más por habitante; si suben,")
    print("    suben menos. Si la población disminuye ocurre lo contrario.")


def mostrar_archivos(archivos: list[tuple[Path, int]]) -> None:
    for ruta, filas in archivos:
        print(f"Guardado: {ruta} ({filas} filas)")
