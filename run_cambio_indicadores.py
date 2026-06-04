# -*- coding: utf-8 -*-
"""
Relanza los transformers usando los PKLs de la carpeta Actualizacion/ y guarda
todos los resultados (indicadores + metricas) en Cambio_indicadores/.

Uso:
    python run_cambio_indicadores.py
"""
import glob
import os
import sys

import pandas as pd

import Transformer_optimo as tf
import orquestador_pipeline as op
import radar as rd

CARPETA_ENTRADA = os.path.join(os.path.dirname(__file__), "Actualizacion")
CARPETA_SALIDA  = os.path.join(os.path.dirname(__file__), "Cambio_indicadores")
EXCEL_COMPARACION = os.path.join(os.path.dirname(__file__), "comparacion_radares.xlsx")
NOMBRE_EXPERIMENTO = "cambio_indicadores"

COLUMNAS_REQUERIDAS = ["periodico", "titulo", "fecha", "texto", "url", "departamento"]


# ---------------------------------------------------------------------------
# 1. Carga de PKLs
# ---------------------------------------------------------------------------

def cargar_corpus(carpeta: str) -> pd.DataFrame:
    archivos = sorted(glob.glob(os.path.join(carpeta, "*.pkl")))
    if not archivos:
        print(f"[ERROR] No se encontraron archivos .pkl en '{carpeta}'", file=sys.stderr)
        sys.exit(1)

    print(f"Cargando {len(archivos)} PKLs desde '{carpeta}'...")
    partes = []
    for ruta in archivos:
        try:
            df = pd.read_pickle(ruta)
            partes.append(df)
            print(f"  + {os.path.basename(ruta)}: {len(df)} articulos")
        except Exception as e:
            print(f"  [ADVERTENCIA] No se pudo leer {os.path.basename(ruta)}: {e}")

    if not partes:
        print("[ERROR] Ningún PKL pudo cargarse.", file=sys.stderr)
        sys.exit(1)

    df_total = pd.concat(partes, ignore_index=True)

    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df_total.columns]
    if faltantes:
        print(f"[ERROR] Columnas faltantes en el corpus: {faltantes}", file=sys.stderr)
        sys.exit(1)

    df_total = df_total.drop_duplicates(subset=["url"])
    df_total["fecha"] = pd.to_datetime(df_total["fecha"], errors="coerce")
    df_total = df_total[df_total["texto"].notna() & (df_total["texto"].astype(str).str.strip() != "")]
    df_total = df_total.reset_index(drop=True)

    print(f"Corpus total: {len(df_total)} articulos en {df_total['departamento'].nunique()} departamentos\n")
    return df_total


# ---------------------------------------------------------------------------
# 2. Pipeline transformers
# ---------------------------------------------------------------------------

def correr_transformers(df_corpus: pd.DataFrame, salida: str) -> str:
    os.makedirs(salida, exist_ok=True)

    print("[TRANSFORMERS] Iniciando clasificacion NLI / sentimiento / NER...")
    pipeline = tf.PipelineTransformers()
    df_procesado = pipeline.procesar(df_corpus)

    ruta_pkl = os.path.join(salida, "df_procesado.pkl")
    ruta_csv = os.path.join(salida, "df_procesado.csv")
    df_procesado.to_pickle(ruta_pkl)
    df_procesado.to_csv(ruta_csv, index=False)
    print(f"[TRANSFORMERS] Guardado: {ruta_pkl}")

    ruta_indicadores = tf.exportar_indicadores_transformers_por_departamento(df_procesado, salida)
    print(f"[TRANSFORMERS] Indicadores: {ruta_indicadores}")

    ruta_radar_pkl, ruta_radar_csv = tf.exportar_radar_base_por_departamento(df_procesado, salida)
    print(f"[TRANSFORMERS] Radar base: {ruta_radar_csv}")

    return ruta_indicadores, ruta_radar_csv, ruta_radar_pkl


# ---------------------------------------------------------------------------
# 3. Radar + metricas
# ---------------------------------------------------------------------------

def correr_radar_y_metricas(
    ruta_indicadores: str,
    ruta_radar_csv: str,
    salida: str,
    excel_comparacion: str,
    nombre_experimento: str,
) -> None:
    print("\n[RADAR] Calculando scores de radar...")
    try:
        resultados = op.ejecutar_radar_experimentos(
            ruta_indicadores_csv=ruta_indicadores,
            ruta_radar_csv=ruta_radar_csv,
            excel=excel_comparacion,
            salida=salida,
            nombre_experimento=nombre_experimento,
            numero_iteraciones=1,
            desactivar_aleatoriedad=True,
            operaciones_radar=[rd.CalculadorRadar.OPERACION_BLOQUES],
            salida_metricas=salida,
            archivo_metricas_excel=os.path.join(salida, "metricas_cambio_indicadores.xlsx"),
        )
        ruta_radar_final = resultados[-1]["RUTA_RADAR_ACTUAL"]
        ruta_radar_pkl   = resultados[-1]["RUTA_RADAR_ACTUAL_PKL"]
    except Exception as e:
        print(f"[ADVERTENCIA] Etapa radar fallo: {e}")
        return

    print("\n[METRICAS] Calculando metricas de error...")
    try:
        resultado_metricas = op.ejecutar_metricas(excel_comparacion, salida)
        op.generar_resumen(
            ruta_radar_csv=ruta_radar_final,
            ruta_procesado_pkl=os.path.join(salida, "df_procesado.pkl"),
            ruta_radar_pkl=ruta_radar_pkl,
            excel_comparacion=excel_comparacion,
            resultado_metricas=resultado_metricas,
        )
        op.evaluar_criterio_parada(resultado_metricas, umbral_mape=23.0, umbral_error_max=40.0)
    except Exception as e:
        print(f"[ADVERTENCIA] Etapa metricas fallo: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  RELANZAMIENTO TRANSFORMERS — NUEVOS INDICADORES")
    print(f"  Entrada : {CARPETA_ENTRADA}")
    print(f"  Salida  : {CARPETA_SALIDA}")
    print("=" * 60 + "\n")

    df_corpus = cargar_corpus(CARPETA_ENTRADA)

    ruta_indicadores, ruta_radar_csv, ruta_radar_pkl = correr_transformers(
        df_corpus, CARPETA_SALIDA
    )

    correr_radar_y_metricas(
        ruta_indicadores=ruta_indicadores,
        ruta_radar_csv=ruta_radar_csv,
        salida=CARPETA_SALIDA,
        excel_comparacion=EXCEL_COMPARACION,
        nombre_experimento=NOMBRE_EXPERIMENTO,
    )

    print("\n" + "=" * 60)
    print(f"  LISTO. Resultados en: {CARPETA_SALIDA}")
    print("=" * 60)
