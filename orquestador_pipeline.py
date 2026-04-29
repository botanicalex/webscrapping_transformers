import argparse
import os
import sys
import subprocess
import pandas as pd

import config_pipeline as cfg
import Transformer_optimo as tf


def ejecutar_pipeline(skip_scraping: bool, ruta_pkl: str, salida: str) -> str:
    os.makedirs(salida, exist_ok=True)

    if not skip_scraping:
        tf.correr_scraping(tf.sc.FECHA_DESDE, tf.sc.FECHA_HASTA, ruta_pkl, temas=None)

    df_corpus = tf.CargadorCorpus(ruta_pkl).cargar()
    print(f"Corpus cargado: {len(df_corpus)} artículos")

    pipeline = tf.PipelineTransformers()
    df_procesado = pipeline.procesar(df_corpus)

    ruta_procesado_pkl = os.path.join(salida, "df_procesado.pkl")
    ruta_procesado_csv = os.path.join(salida, "df_procesado.csv")
    df_procesado.to_pickle(ruta_procesado_pkl)
    df_procesado.to_csv(ruta_procesado_csv, index=False)

    radar = tf.CalculadorRadar()
    df_radar = radar.calcular(df_procesado)

    ruta_radar_pkl = os.path.join(salida, "radar_departamentos.pkl")
    ruta_radar_csv = os.path.join(salida, "radar_departamentos.csv")
    df_radar.to_pickle(ruta_radar_pkl)
    df_radar.to_csv(ruta_radar_csv, index=False)

    print("Radar final:")
    print(df_radar.to_string(index=False))
    print(f"Guardado: {ruta_procesado_pkl}, {ruta_procesado_csv}, {ruta_radar_pkl}, {ruta_radar_csv}")
    return ruta_radar_csv


def actualizar_excel_experimento(excel: str, radar_csv: str, nombre_experimento: str) -> None:
    if not os.path.exists(excel):
        raise FileNotFoundError(f"No existe el Excel de comparación: {excel}")

    df_excel = pd.read_excel(excel)
    if "departamento" not in df_excel.columns:
        raise ValueError("El Excel debe contener la columna 'departamento'")

    df_radar = pd.read_csv(radar_csv)
    if "departamento" not in df_radar.columns or "radar_propio" not in df_radar.columns:
        raise ValueError("El radar generado debe contener columnas 'departamento' y 'radar_propio'")

    df_excel["departamento"] = df_excel["departamento"].astype(str).str.strip()
    df_radar["departamento"] = df_radar["departamento"].astype(str).str.strip()

    radar_por_departamento = dict(zip(df_radar["departamento"], df_radar["radar_propio"]))
    df_excel[nombre_experimento] = df_excel["departamento"].map(radar_por_departamento)

    df_excel.to_excel(excel, index=False)
    faltantes = int(df_excel[nombre_experimento].isna().sum())
    print(f"Excel actualizado en '{excel}' con columna '{nombre_experimento}'. Departamentos sin valor: {faltantes}")


def ejecutar_metricas() -> None:
    subprocess.run([sys.executable, "metricas_y_calculo_de_error.py"], check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-scraping", action="store_true")
    parser.add_argument("--ruta-pkl", default=cfg.RUTA_CORPUS_PKL)
    parser.add_argument("--salida", default=cfg.RUTA_SALIDA_PIPELINE)
    parser.add_argument("--excel", default=cfg.ARCHIVO_COMPARACION_EXCEL)
    parser.add_argument("--nombre-experimento", default="experimento_orquestado")
    args = parser.parse_args()

    radar_csv = ejecutar_pipeline(args.skip_scraping, args.ruta_pkl, args.salida)
    actualizar_excel_experimento(args.excel, radar_csv, args.nombre_experimento)
    ejecutar_metricas()


if __name__ == "__main__":
    main()