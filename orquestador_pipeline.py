# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional, Tuple
import pandas as pd

import config_pipeline as cfg
import metricas_y_calculo_de_error as mc
import Transformer_optimo as tf


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _ejecutar_etapa(nombre: str, fn: Any) -> Any:
    print(f"\n[{nombre.upper()}] Iniciando etapa...")
    try:
        resultado = fn()
        print(f"[{nombre.upper()}] Etapa completada.")
        return resultado
    except Exception as exc:
        print(f"\n[ERROR] Etapa '{nombre}' falló: {exc}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Etapas del pipeline
# ---------------------------------------------------------------------------

def ejecutar_pipeline(skip_scraping: bool, ruta_pkl: str, salida: str) -> Tuple[str, str, str]:
    if not skip_scraping:
        tf.correr_scraping(tf.sc.FECHA_DESDE, tf.sc.FECHA_HASTA, ruta_pkl, temas=None)

    ruta_procesado_pkl, ruta_radar_pkl = tf.run_pipeline_transformers(ruta_pkl, salida)
    return ruta_procesado_pkl, ruta_radar_pkl, os.path.join(salida, "radar_departamentos.csv")


def actualizar_excel_experimento(excel: str, radar_csv: str, nombre_experimento: str) -> None:
    if not nombre_experimento.startswith("experimento_"):
        nombre_experimento = f"experimento_{nombre_experimento}"

    if not os.path.isfile(excel):
        raise FileNotFoundError(f"No existe el Excel de comparación: '{excel}'")
    if not os.path.isfile(radar_csv):
        raise FileNotFoundError(f"No existe el CSV de radar: '{radar_csv}'")

    with pd.ExcelFile(excel, engine="openpyxl") as xl:
        sheet_name = xl.sheet_names[0]
        df_excel = xl.parse(sheet_name)

    if "departamento" not in df_excel.columns:
        raise ValueError("El Excel debe contener la columna 'departamento'")

    df_radar = pd.read_csv(radar_csv)
    if "departamento" not in df_radar.columns or "radar_propio" not in df_radar.columns:
        raise ValueError(
            "El CSV de radar debe contener las columnas 'departamento' y 'radar_propio'"
        )

    df_excel["departamento"] = df_excel["departamento"].astype(str).str.strip()
    df_radar["departamento"] = df_radar["departamento"].astype(str).str.strip()

    radar_map = {
        k.casefold(): v
        for k, v in zip(df_radar["departamento"], df_radar["radar_propio"])
    }
    df_excel[nombre_experimento] = df_excel["departamento"].map(
        lambda d: radar_map.get(d.casefold())
    )

    with pd.ExcelWriter(excel, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df_excel.to_excel(writer, index=False, sheet_name=sheet_name)

    faltantes = int(df_excel[nombre_experimento].isna().sum())
    print(
        f"Excel actualizado en '{excel}' con columna '{nombre_experimento}'. "
        f"Departamentos sin valor: {faltantes}"
    )


def ejecutar_metricas(ruta_excel: str, salida: str) -> Dict[str, Any]:
    return mc.calcular_metricas(ruta_excel, salida)


# ---------------------------------------------------------------------------
# Resumen y criterio de parada
# ---------------------------------------------------------------------------

def generar_resumen(
    ruta_radar_csv: str,
    ruta_procesado_pkl: str,
    ruta_radar_pkl: str,
    excel_comparacion: str,
    resultado_metricas: Dict[str, Any],
) -> Dict[str, Any]:
    articulos_por_departamento: Dict[str, int] = {}
    n_departamentos = 0

    if os.path.isfile(ruta_radar_csv):
        df_radar = pd.read_csv(ruta_radar_csv)
        n_departamentos = int(len(df_radar))
        if "departamento" in df_radar.columns and "n_articulos" in df_radar.columns:
            articulos_por_departamento = {
                str(dep): int(n)
                for dep, n in zip(df_radar["departamento"], df_radar["n_articulos"])
            }

    metricas_clave = [
        {
            "experimento": m["experimento"],
            "MAE": round(float(m["MAE"]), 4),
            "RMSE": round(float(m["RMSE"]), 4),
            "MAPE_pct": round(float(m["MAPE_pct"]), 4),
            "Pearson": round(float(m["Pearson"]), 4),
        }
        for m in resultado_metricas["metricas"]
    ]

    resumen: Dict[str, Any] = {
        "n_departamentos": n_departamentos,
        "articulos_por_departamento": articulos_por_departamento,
        "metricas": metricas_clave,
        "artefactos": {
            "df_procesado_pkl": ruta_procesado_pkl,
            "radar_pkl": ruta_radar_pkl,
            "radar_csv": ruta_radar_csv,
            "excel_comparacion": excel_comparacion,
            "excel_resultado": resultado_metricas["excel_salida"],
            "graficos_dir": resultado_metricas["graficos_dir"],
        },
    }

    print("\n========== RESUMEN FINAL ==========")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))

    return resumen


def evaluar_criterio_parada(
    resultado_metricas: Dict[str, Any],
    umbral_mape: float,
    umbral_error_max: float,
) -> bool:
    """
    Evalúa criterios de parada del ciclo de optimización (docs/07_loop_optimizacion.md:78-83):
      - MAPE global < umbral_mape para todos los experimentos
      - Error absoluto máximo individual < umbral_error_max
        (nota: la exclusión de departamentos con 0 artículos queda pendiente para
        cuando el Excel de comparación incluya la columna n_articulos)
    Retorna True si ambas condiciones se cumplen.
    """
    metricas = resultado_metricas.get("metricas", [])
    if not metricas:
        print("\n[CRITERIO DE PARADA] Sin datos de métricas para evaluar.")
        return False

    mape_ok = all(m["MAPE_pct"] < umbral_mape for m in metricas)
    max_error_abs = resultado_metricas.get("max_error_abs", float("inf"))
    error_ok = max_error_abs < umbral_error_max
    alcanzado = mape_ok and error_ok

    print("\n========== CRITERIO DE PARADA ==========")
    for m in metricas:
        estado = "OK" if m["MAPE_pct"] < umbral_mape else "NO OK"
        print(f"  {m['experimento']}: MAPE={m['MAPE_pct']:.2f}% (umbral<{umbral_mape}%) [{estado}]")
    estado_err = "OK" if error_ok else "NO OK"
    print(
        f"  Error abs máx global: {max_error_abs:.2f} (umbral<{umbral_error_max}) [{estado_err}]"
    )

    if alcanzado:
        print(">>> CRITERIO DE PARADA ALCANZADO — ciclo de optimización puede detenerse.")
    else:
        print(">>> CICLO CONTINÚA — ajustar configuración y relanzar.")

    return alcanzado


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orquestador del pipeline radar de prensa"
    )
    parser.add_argument(
        "--only",
        choices=["scraping", "transformers", "excel", "metricas", "todo"],
        default="todo",
        help=(
            "Etapa única a ejecutar. "
            "'todo' corre el pipeline completo (default). "
            "Usar 'scraping', 'transformers', 'excel' o 'metricas' para iterar una sola etapa."
        ),
    )
    parser.add_argument(
        "--skip-scraping",
        action="store_true",
        help="En modo 'todo', omitir la etapa de scraping",
    )
    parser.add_argument(
        "--from-group",
        type=int,
        default=1,
        metavar="N",
        help="Retomar scraping desde el grupo N (1-based). Los grupos anteriores se saltan. Default: 1",
    )
    parser.add_argument("--ruta-pkl", default=cfg.RUTA_CORPUS_PKL)
    parser.add_argument("--salida", default=cfg.RUTA_SALIDA_PIPELINE)
    parser.add_argument("--excel", default=cfg.ARCHIVO_COMPARACION_EXCEL)
    parser.add_argument("--nombre-experimento", default="experimento_1")
    parser.add_argument("--salida-metricas", default=".")
    parser.add_argument(
        "--umbral-mape",
        type=float,
        default=23.0,
        help="Umbral MAPE%% para criterio de parada (default: 23.0)",
    )
    parser.add_argument(
        "--umbral-error-max",
        type=float,
        default=40.0,
        help="Umbral de error absoluto individual para criterio de parada (default: 40.0)",
    )
    args = parser.parse_args()

    only = args.only
    ruta_radar_csv = os.path.join(args.salida, "radar_departamentos.csv")
    ruta_procesado_pkl = os.path.join(args.salida, "df_procesado.pkl")
    ruta_radar_pkl = os.path.join(args.salida, "radar_departamentos.pkl")

    correr_scraping = only == "scraping" or (only == "todo" and not args.skip_scraping)
    correr_transformers = only in ("transformers", "todo")
    correr_excel = only in ("excel", "todo")
    correr_metricas = only in ("metricas", "todo")

    # --- Etapa A: scraping ---
    if correr_scraping:
        _ejecutar_etapa(
            "scraping",
            lambda: tf.correr_scraping(
                tf.sc.FECHA_DESDE, tf.sc.FECHA_HASTA, args.ruta_pkl, temas=None,
                from_group=args.from_group
            ),
        )

    # --- Etapa B: transformers + radar ---
    if correr_transformers:
        resultado_pipeline: Optional[Tuple[str, str]] = _ejecutar_etapa(
            "transformers",
            lambda: tf.run_pipeline_transformers(args.ruta_pkl, args.salida),
        )
        if resultado_pipeline is not None:
            ruta_procesado_pkl, ruta_radar_pkl = resultado_pipeline

    # --- Etapa C: actualizar Excel ---
    if correr_excel:
        _ejecutar_etapa(
            "excel",
            lambda: actualizar_excel_experimento(
                args.excel, ruta_radar_csv, args.nombre_experimento
            ),
        )

    # --- Etapa D: métricas + resumen + criterio de parada ---
    if correr_metricas:
        resultado_metricas: Optional[Dict[str, Any]] = _ejecutar_etapa(
            "metricas",
            lambda: ejecutar_metricas(args.excel, args.salida_metricas),
        )
        if resultado_metricas is not None:
            generar_resumen(
                ruta_radar_csv=ruta_radar_csv,
                ruta_procesado_pkl=ruta_procesado_pkl,
                ruta_radar_pkl=ruta_radar_pkl,
                excel_comparacion=args.excel,
                resultado_metricas=resultado_metricas,
            )
            evaluar_criterio_parada(
                resultado_metricas, args.umbral_mape, args.umbral_error_max
            )


if __name__ == "__main__":
    main()
