"""
Pipeline para el radar_Actualizado.

Pasos:
  1. Carga los PKL de la carpeta Actualizacion (formato {depto}_{año}.pkl).
  2. Corre el pipeline de Transformers NLP sobre esos artículos.
  3. Exporta el CSV de indicadores a  Indicadores transformers/Actualizado/.
  4. Calcula radar_Actualizado (promedio simple → min-max → TERCILES).
  5. Agrega columnas radar_Actualizado_promedio_normalizado y
     Clasificacion_radar_Actualizado a comparacion_radares_V2.xlsx.
  6. Calcula métricas de clasificación (Actualizado vs Radar Oficial DANE)
     y las compara con el radar ya existente en el xlsx para los mismos departamentos.
  7. Guarda métricas en metricas_clasificacion_Actualizado.xlsx.
"""
import argparse
import glob
import os
import shutil
import sys

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

# --------------------------------------------------------------------------- #
# Rutas por defecto (apuntan al directorio principal del proyecto)
# --------------------------------------------------------------------------- #
_DIR_PROYECTO = os.path.dirname(os.path.abspath(__file__))
# Worktree path: .../webscrapping_transformers/.claude/worktrees/admiring-williamson-a508f3/
# _DIR_PROYECTO: .../webscrapping_transformers/  (4 niveles arriba del script)

DEFAULT_ACTUALIZACION = os.path.join(_DIR_PROYECTO, "Actualizacion")
DEFAULT_XLSX          = os.path.join(_DIR_PROYECTO, "comparacion_radares_V2.xlsx")
DEFAULT_SALIDA_IND    = os.path.join(_DIR_PROYECTO, "Indicadores transformers", "Actualizado")
DEFAULT_SALIDA_MET    = os.path.join(_DIR_PROYECTO, "metricas_clasificacion_Actualizado.xlsx")

# --------------------------------------------------------------------------- #
# Los 36 indicadores exportados por el pipeline de transformers
# --------------------------------------------------------------------------- #
INDICADORES_36 = [
    'participacion_comunitaria', 'incentivos_economicos', 'fortalecimiento_institucional',
    'impactos_ambientales', 'conflictos_socioambientales', 'desplazamiento_forzado',
    'reasentamiento', 'protesta_social', 'amenaza_intimidacion', 'consulta_previa',
    'audiencia_publica', 'taller_participativo', 'conflicto_territorial',
    'rechazo_proyecto', 'deficit_derechos', 'denuncia_violacion',
    'deficit_participacion_efectiva', 'ruptura_dialogo', 'reivindicacion_territorial',
    'exclusion_participacion', 'equidad_inclusion', 'grupos_etnicos',
    'movimientos_sociales', 'grupos_poblacionales_afectados',
    'participacion_economica_local', 'transparencia_contractual',
    'zonas_proteccion_alimentaria', 'respeto_territorios',
    'presencia_grupos_armados', 'desaparicion_lideres', 'grupos_etnicos_entidades',
    'grupos_armados_entidades', 'organizaciones_entidades', 'lideres_entidades',
    'instituciones_entidades', 'actores_economicos_entidades',
]

ETIQUETAS_3 = ['Bajo', 'Medio', 'Alto']

# --------------------------------------------------------------------------- #
# Normalización de nombres de departamento
# --------------------------------------------------------------------------- #
_EQUIV_DEPTO = {
    'San Andrés y Providencia': 'San Andrés',
    'San Andres y Providencia': 'San Andrés',
    'San Andres':               'San Andrés',
    'Bogota':                   'Bogotá D.C.',
    'Bogotá':                   'Bogotá D.C.',
}

def _norm_depto(nombre: str) -> str:
    s = str(nombre).strip()
    return _EQUIV_DEPTO.get(s, s)


# =========================================================================== #
# 1. CARGA DE PKLs DE ACTUALIZACION
# =========================================================================== #
def cargar_pkls_actualizacion(ruta_dir: str) -> pd.DataFrame:
    """
    Carga todos los archivos *.pkl de la carpeta Actualizacion.
    Los PKL tienen columnas: periodico, titulo, fecha, texto, url,
    terminos_encontrado, departamento.
    """
    archivos = sorted(glob.glob(os.path.join(ruta_dir, "*.pkl")))
    if not archivos:
        raise FileNotFoundError(f"No se encontraron *.pkl en '{ruta_dir}'")

    partes = []
    for ruta in archivos:
        try:
            df = pd.read_pickle(ruta)
            n = len(df)
            depto_val = df['departamento'].iloc[0] if ('departamento' in df.columns and n > 0) else '?'
            print(f"  {os.path.basename(ruta)}: {n} artículos | depto muestra: {depto_val}")
            partes.append(df)
        except Exception as exc:
            print(f"  ERROR cargando {ruta}: {exc}")

    if not partes:
        raise ValueError("No se pudo cargar ningún PKL válido")

    df_total = pd.concat(partes, ignore_index=True)

    # Asegurar columnas requeridas por CargadorCorpus / PipelineTransformers
    for col in ['periodico', 'titulo', 'fecha', 'texto', 'url', 'departamento']:
        if col not in df_total.columns:
            df_total[col] = None

    df_total['fecha'] = pd.to_datetime(df_total['fecha'], errors='coerce')
    df_total['departamento'] = df_total['departamento'].astype(str).str.strip()

    # Filtrar artículos sin texto
    sin_texto = df_total['texto'].isna() | (df_total['texto'].astype(str).str.strip() == '')
    df_total = df_total[~sin_texto].reset_index(drop=True)

    deptos = sorted(df_total['departamento'].unique().tolist())
    print(f"\nCorpus Actualizado: {len(df_total)} artículos | {len(deptos)} departamentos")
    print(f"Departamentos: {deptos}\n")
    return df_total


# =========================================================================== #
# 2. PIPELINE DE TRANSFORMERS
# =========================================================================== #
def correr_transformers(df_corpus: pd.DataFrame, salida: str) -> str:
    """
    Corre PipelineTransformers sobre df_corpus y exporta:
      - df_procesado.pkl / .csv
      - actualizado_indicadores_transformers_departamento.csv  (retornado)
    """
    os.makedirs(salida, exist_ok=True)

    from Transformer_optimo import PipelineTransformers
    from radar import CalculadorRadar

    pipe = PipelineTransformers()
    df_proc = pipe.procesar(df_corpus)

    # Guardar procesado completo
    df_proc.to_pickle(os.path.join(salida, "df_procesado_Actualizado.pkl"))
    df_proc.to_csv(os.path.join(salida, "df_procesado_Actualizado.csv"), index=False)
    print(f"df_procesado_Actualizado guardado en {salida}")

    # Exportar indicadores por departamento
    nombre_csv = "actualizado_indicadores_transformers_departamento.csv"
    cols_bin = [c for c in CalculadorRadar.COLUMNAS_BINARIAS if c in df_proc.columns]
    for c in cols_bin:
        if df_proc[c].dtype == bool:
            df_proc[c] = df_proc[c].astype(float)
        else:
            df_proc[c] = pd.to_numeric(df_proc[c], errors='coerce').fillna(0.0)

    df_ind = df_proc.groupby('departamento')[cols_bin].mean().reset_index()
    ruta_csv = os.path.join(salida, nombre_csv)
    df_ind.to_csv(ruta_csv, index=False)
    print(f"Indicadores exportados: {ruta_csv}")
    return ruta_csv


# =========================================================================== #
# 3. CALCULO DEL RADAR ACTUALIZADO (terciles — 3 clases)
# =========================================================================== #
def calcular_radar_Actualizado(df_indicadores: pd.DataFrame) -> pd.DataFrame:
    """
    Promedio simple de los 36 indicadores → min-max 0-1 → terciles (Bajo/Medio/Alto).
    """
    df = df_indicadores.copy()
    df['departamento'] = df['departamento'].astype(str).str.strip().apply(_norm_depto)

    faltantes = [c for c in INDICADORES_36 if c not in df.columns]
    if faltantes:
        print(f"[radar_Actualizado] Indicadores faltantes (-> 0): {faltantes}")
        for c in faltantes:
            df[c] = 0.0

    for c in INDICADORES_36:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

    radar_raw = df[INDICADORES_36].mean(axis=1)
    mn, mx = radar_raw.min(), radar_raw.max()
    if mx > mn:
        radar_norm = (radar_raw - mn) / (mx - mn)
    else:
        radar_norm = pd.Series([0.5] * len(radar_raw), index=radar_raw.index)

    # Terciles (q=3) para coincidir con Clasificacion_radar_oficial_promedio
    clasif = pd.qcut(radar_norm, q=3, labels=ETIQUETAS_3, duplicates='drop').astype(str)

    out = pd.DataFrame({
        'departamento':                         df['departamento'].values,
        'radar_Actualizado_promedio_normalizado': radar_norm.values,
        'Clasificacion_radar_Actualizado':       clasif.values,
    })

    print("\n=== Radar Actualizado ===")
    print(out.sort_values('radar_Actualizado_promedio_normalizado', ascending=False).to_string(index=False))
    return out


# =========================================================================== #
# 4. ACTUALIZAR XLSX
# =========================================================================== #
def actualizar_xlsx(ruta_xlsx: str, df_actualizado: pd.DataFrame) -> None:
    """
    Agrega (o sobreescribe) las columnas radar_Actualizado al xlsx.
    Hace backup automático si no existe.
    """
    if not os.path.isfile(ruta_xlsx):
        raise FileNotFoundError(f"xlsx no encontrado: {ruta_xlsx}")

    backup = ruta_xlsx.replace('.xlsx', '_backup_preActualizado.xlsx')
    if not os.path.isfile(backup):
        shutil.copy2(ruta_xlsx, backup)
        print(f"Backup creado: {backup}")

    wb = load_workbook(ruta_xlsx)
    ws = wb[wb.sheetnames[0]]

    # Mapa de headers existentes
    headers_ex = {}
    for c in range(1, ws.max_column + 1):
        h = ws.cell(row=1, column=c).value
        if h is not None:
            headers_ex[str(h).strip()] = c

    # Columnas a añadir / actualizar
    nuevas = ['radar_Actualizado_promedio_normalizado', 'Clasificacion_radar_Actualizado']
    col_idx = {}
    sig = ws.max_column + 1
    for nombre in nuevas:
        if nombre in headers_ex:
            col_idx[nombre] = headers_ex[nombre]
        else:
            ws.cell(row=1, column=sig, value=nombre)
            col_idx[nombre] = sig
            sig += 1

    col_depto = headers_ex.get('Departamento') or headers_ex.get('departamento')
    if col_depto is None:
        raise ValueError("xlsx no tiene columna 'Departamento'")

    mapa = {
        _norm_depto(r['departamento']): (
            float(r['radar_Actualizado_promedio_normalizado']),
            str(r['Clasificacion_radar_Actualizado']),
        )
        for _, r in df_actualizado.iterrows()
    }

    sin_match = []
    actualizados = 0
    for row in range(2, ws.max_row + 1):
        dep = ws.cell(row=row, column=col_depto).value
        if dep is None:
            continue
        dep_n = _norm_depto(str(dep))
        if dep_n in mapa:
            val, cls = mapa[dep_n]
            ws.cell(row=row, column=col_idx['radar_Actualizado_promedio_normalizado'], value=val)
            ws.cell(row=row, column=col_idx['Clasificacion_radar_Actualizado'], value=cls)
            actualizados += 1
        else:
            sin_match.append(dep_n)

    if sin_match:
        print(f"ADVERTENCIA: departamentos del xlsx sin datos Actualizado: {sin_match}")
    print(f"xlsx actualizado: {actualizados} departamentos escritos -> {ruta_xlsx}")
    wb.save(ruta_xlsx)


# =========================================================================== #
# 5. MÉTRICAS DE CLASIFICACIÓN
# =========================================================================== #
def _metricas_par(y_true, y_pred, etiqueta: str):
    """Calcula accuracy, F1, kappa, detalle y matriz de confusión."""
    mask = (
        pd.Series(y_true).notna()
        & pd.Series(y_pred).notna()
        & (pd.Series(y_true).astype(str).str.strip() != '')
        & (pd.Series(y_pred).astype(str).str.strip() != '')
        & (pd.Series(y_true).astype(str) != 'nan')
        & (pd.Series(y_pred).astype(str) != 'nan')
    )
    yt = [str(v) for v, m in zip(y_true, mask) if m]
    yp = [str(v) for v, m in zip(y_pred, mask) if m]

    if len(yt) == 0:
        print(f"  [{etiqueta}] Sin datos válidos para calcular métricas.")
        return None, None, None

    acc = accuracy_score(yt, yp)
    p, r, f, _ = precision_recall_fscore_support(
        yt, yp, labels=ETIQUETAS_3, average='macro', zero_division=0
    )
    kappa = cohen_kappa_score(yt, yp, labels=ETIQUETAS_3)

    resumen = {
        'comparacion': etiqueta,
        'n_departamentos': len(yt),
        'accuracy': round(float(acc), 4),
        'precision_macro': round(float(p), 4),
        'recall_macro': round(float(r), 4),
        'f1_macro': round(float(f), 4),
        'cohen_kappa': round(float(kappa), 4),
    }

    rep = classification_report(
        yt, yp, labels=ETIQUETAS_3, target_names=ETIQUETAS_3,
        output_dict=True, zero_division=0,
    )
    detalle_rows = []
    for clase in ETIQUETAS_3:
        d = rep[clase]
        detalle_rows.append({
            'comparacion': etiqueta,
            'clase': clase,
            'precision': round(float(d['precision']), 4),
            'recall': round(float(d['recall']), 4),
            'f1-score': round(float(d['f1-score']), 4),
            'support': int(d['support']),
        })

    cm = confusion_matrix(yt, yp, labels=ETIQUETAS_3)
    return resumen, pd.DataFrame(detalle_rows), cm


def calcular_metricas(ruta_xlsx: str, ruta_salida: str) -> None:
    """
    Genera metricas_clasificacion_Actualizado.xlsx con:
      - resumen: comparaciones Actualizado vs referencias
               + comparación del radar existente sobre los mismos deptos
      - detalle_por_clase
      - matrices_confusion
    """
    wb = load_workbook(ruta_xlsx, data_only=True)
    ws = wb[wb.sheetnames[0]]
    headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    data = {}
    for idx, h in enumerate(headers, 1):
        if h is None:
            continue
        data[str(h).strip()] = [ws.cell(row=r, column=idx).value for r in range(2, ws.max_row + 1)]
    df = pd.DataFrame(data)

    # Verificar columnas necesarias
    col_actual = 'Clasificacion_radar_Actualizado'
    col_oficial = 'Clasificacion_radar_oficial_promedio'
    col_exist   = 'Clasificacion_radar'  # radar ya existente en el xlsx

    for col in [col_actual, col_oficial]:
        if col not in df.columns:
            raise ValueError(f"Falta columna '{col}' en xlsx — asegúrate de haber corrido actualizar_xlsx primero.")

    # Solo filas donde Actualizado tiene dato
    mask_act = df[col_actual].notna() & (df[col_actual].astype(str).str.strip() != '') & (df[col_actual].astype(str) != 'nan')
    df_sub = df[mask_act].copy()
    n_sub = len(df_sub)
    print(f"\nMetricas sobre {n_sub} departamentos con datos Actualizado.")

    # Definir pares a comparar (solo Radar Oficial DANE — IDIC eliminado por falta de datos 2023)
    pares = [
        ('Actualizado_vs_radar_oficial', col_actual, col_oficial),
    ]
    # Si existe el radar previo, añadir comparación "justa" sobre los mismos deptos
    if col_exist in df.columns:
        pares += [
            ('Existente_vs_radar_oficial', col_exist, col_oficial),
        ]

    resumenes, detalles, matrices = [], [], {}
    for etiqueta, col_pred, col_true in pares:
        res, det, cm = _metricas_par(df_sub[col_true], df_sub[col_pred], etiqueta)
        if res is not None:
            resumenes.append(res)
            detalles.append(det)
            matrices[etiqueta] = cm

    df_res = pd.DataFrame(resumenes)
    df_det = pd.concat(detalles, ignore_index=True) if detalles else pd.DataFrame()

    filas_cm = []
    for etiqueta, cm in matrices.items():
        filas_cm.append({'comparacion': etiqueta, 'verdadero \\ predicho': '---',
                         **{c: '' for c in ETIQUETAS_3}})
        for i, cr in enumerate(ETIQUETAS_3):
            fila = {'comparacion': etiqueta, 'verdadero \\ predicho': cr}
            for j, cp in enumerate(ETIQUETAS_3):
                fila[cp] = int(cm[i, j])
            filas_cm.append(fila)
        filas_cm.append({'comparacion': '', 'verdadero \\ predicho': ''})
    df_cm = pd.DataFrame(filas_cm)

    with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
        df_res.to_excel(writer, sheet_name='resumen', index=False)
        df_det.to_excel(writer, sheet_name='detalle_por_clase', index=False)
        df_cm.to_excel(writer, sheet_name='matrices_confusion', index=False)

    print(f"\nMétricas exportadas: {ruta_salida}")
    print("\n=== RESUMEN DE MÉTRICAS ===")
    print(df_res.to_string(index=False))


# =========================================================================== #
# MAIN
# =========================================================================== #
def main():
    parser = argparse.ArgumentParser(
        description="Pipeline radar_Actualizado: Transformers → Radar → Métricas"
    )
    parser.add_argument(
        '--actualizacion', default=DEFAULT_ACTUALIZACION,
        help=f"Carpeta con los PKL nuevos (default: {DEFAULT_ACTUALIZACION})"
    )
    parser.add_argument(
        '--xlsx-comparacion', default=DEFAULT_XLSX,
        help=f"Ruta de comparacion_radares_V2.xlsx (default: {DEFAULT_XLSX})"
    )
    parser.add_argument(
        '--salida-indicadores', default=DEFAULT_SALIDA_IND,
        help=f"Carpeta de salida para indicadores CSV (default: {DEFAULT_SALIDA_IND})"
    )
    parser.add_argument(
        '--salida-metricas', default=DEFAULT_SALIDA_MET,
        help=f"Ruta del xlsx de métricas (default: {DEFAULT_SALIDA_MET})"
    )
    parser.add_argument(
        '--skip-transformers', action='store_true',
        help="Saltar el paso de transformers y usar CSV ya existente"
    )
    parser.add_argument(
        '--csv-indicadores', default=None,
        help="Usar este CSV de indicadores en lugar de correr los transformers "
             "(requiere --skip-transformers)"
    )
    parser.add_argument(
        '--incremental', action='store_true',
        help="Solo procesar PKLs cuyos departamentos no esten ya en el CSV existente, "
             "luego fusionar con el CSV previo."
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PIPELINE RADAR ACTUALIZADO")
    print("=" * 60)

    # ------------------------------------------------------------------ #
    # Paso 1 y 2: Cargar corpus y correr transformers (o usar CSV previo) #
    # ------------------------------------------------------------------ #
    _nombre_csv = "actualizado_indicadores_transformers_departamento.csv"

    if args.skip_transformers:
        if args.csv_indicadores is None:
            # Buscar el CSV por defecto en salida-indicadores
            ruta_csv = os.path.join(args.salida_indicadores, _nombre_csv)
        else:
            ruta_csv = args.csv_indicadores

        if not os.path.isfile(ruta_csv):
            raise FileNotFoundError(f"CSV de indicadores no encontrado: {ruta_csv}")
        print(f"[SKIP] Cargando CSV de indicadores: {ruta_csv}")
        df_indicadores = pd.read_csv(ruta_csv)

    elif args.incremental:
        # Leer CSV existente para saber qué departamentos ya están procesados
        ruta_csv = os.path.join(args.salida_indicadores, _nombre_csv)
        df_existente = None
        deptos_ya: set = set()
        if os.path.isfile(ruta_csv):
            df_existente = pd.read_csv(ruta_csv)
            deptos_ya = set(df_existente['departamento'].astype(str).str.strip().tolist())
            print(f"[incremental] {len(deptos_ya)} deptos ya procesados: {sorted(deptos_ya)}")
        else:
            print("[incremental] No existe CSV previo, procesando todo")

        # Cargar todos los PKLs y filtrar solo los nuevos
        print(f"\n[1] Cargando corpus desde: {args.actualizacion}")
        df_corpus_todos = cargar_pkls_actualizacion(args.actualizacion)
        df_corpus_nuevos = df_corpus_todos[
            ~df_corpus_todos['departamento'].astype(str).str.strip().isin(deptos_ya)
        ].reset_index(drop=True)

        deptos_nuevos = sorted(df_corpus_nuevos['departamento'].unique().tolist())
        print(f"[incremental] {len(deptos_nuevos)} deptos a procesar: {deptos_nuevos}")

        if df_corpus_nuevos.empty:
            print("[incremental] Nada nuevo que procesar. Usando CSV existente.")
            df_indicadores = df_existente
        else:
            print(f"\n[2] Corriendo Transformers NLP en {len(df_corpus_nuevos)} articulos nuevos...")
            os.makedirs(args.salida_indicadores, exist_ok=True)
            ruta_csv_nuevos = correr_transformers(df_corpus_nuevos, args.salida_indicadores)
            df_nuevos = pd.read_csv(ruta_csv_nuevos)

            # Fusionar con los departamentos existentes
            if df_existente is not None:
                df_merged = pd.concat([df_existente, df_nuevos], ignore_index=True)
            else:
                df_merged = df_nuevos

            # Sobreescribir el CSV parcial con el fusionado completo
            df_merged.to_csv(ruta_csv, index=False)
            print(f"[incremental] CSV fusionado: {len(df_merged)} deptos -> {ruta_csv}")
            df_indicadores = df_merged

    else:
        # Flujo completo: procesar todos los PKLs de la carpeta
        print(f"\n[1] Cargando corpus desde: {args.actualizacion}")
        df_corpus = cargar_pkls_actualizacion(args.actualizacion)

        print(f"\n[2] Corriendo pipeline de Transformers NLP...")
        os.makedirs(args.salida_indicadores, exist_ok=True)
        ruta_csv = correr_transformers(df_corpus, args.salida_indicadores)
        df_indicadores = pd.read_csv(ruta_csv)

    print(f"\nIndicadores cargados: {df_indicadores.shape}")

    # ------------------------------------------------------------------ #
    # Paso 3: Calcular radar_Actualizado                                  #
    # ------------------------------------------------------------------ #
    print("\n[3] Calculando radar_Actualizado (terciles)...")
    df_radar = calcular_radar_Actualizado(df_indicadores)

    # ------------------------------------------------------------------ #
    # Paso 4: Actualizar xlsx                                             #
    # ------------------------------------------------------------------ #
    print(f"\n[4] Actualizando xlsx: {args.xlsx_comparacion}")
    actualizar_xlsx(args.xlsx_comparacion, df_radar)

    # ------------------------------------------------------------------ #
    # Paso 5: Calcular métricas                                           #
    # ------------------------------------------------------------------ #
    print(f"\n[5] Calculando métricas de clasificación...")
    calcular_metricas(args.xlsx_comparacion, args.salida_metricas)

    print("\n" + "=" * 60)
    print("LISTO. Archivos generados:")
    print(f"  Indicadores CSV : {ruta_csv}")
    print(f"  xlsx comparación: {args.xlsx_comparacion}")
    print(f"  Métricas xlsx   : {args.salida_metricas}")
    print("=" * 60)


if __name__ == '__main__':
    main()
