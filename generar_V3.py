"""
Genera comparacion_radares_V3.xlsx y metricas_clasificacion_V3.xlsx.

Estructura V3:
  Departamento | radar_oficial_promedio | radar_oficial_promedio_normalizado
  | Clasificacion_radar_oficial_promedio (DANE, sin invertir)
  | Radar_completo_promedio_normalizado | Clasificacion_Radar_completo (INVERTIDA)
  | radar_actualizado_promedio_normalizado | Clasificacion_radar_actualizado (INVERTIDA)

Sin IDIC, sin rankings.

Inversión: Alto -> Bajo, Bajo -> Alto, Medio -> Medio
Razón: los indicadores detectan presencia de conflictos/riesgos.
Alto score = muchos conflictos detectados = peor situación = etiqueta 'Bajo'.
"""

import os
import shutil
from typing import Dict, List, Tuple

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

# =========================================================================== #
# Rutas
# =========================================================================== #
_DIR_PROYECTO = os.path.dirname(os.path.abspath(__file__))

RUTA_V2 = os.path.join(_DIR_PROYECTO, "comparacion_radares_V2.xlsx")
RUTA_NUEVO_ALEXA = os.path.join(
    _DIR_PROYECTO, "Indicadores transformers",
    "nuevo_alexa_indicadores_transformers_departamento.csv"
)
RUTA_ACTUALIZADO = os.path.join(
    _DIR_PROYECTO, "Indicadores transformers",
    "Actualizado", "actualizado_indicadores_transformers_departamento.csv"
)
RUTA_V3 = os.path.join(_DIR_PROYECTO, "comparacion_radares_V3.xlsx")
RUTA_METRICAS_V3 = os.path.join(_DIR_PROYECTO, "metricas_clasificacion_V3.xlsx")

# =========================================================================== #
# Constantes
# =========================================================================== #
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

# Inversión de etiquetas: alto score de conflicto = baja gobernanza
INVERSION: Dict[str, str] = {'Alto': 'Bajo', 'Bajo': 'Alto', 'Medio': 'Medio'}

_EQUIV_DEPTO: Dict[str, str] = {
    'San Andrés y Providencia': 'San Andrés',
    'San Andres y Providencia': 'San Andrés',
    'San Andres': 'San Andrés',
    'San Andrés y Providencia': 'San Andrés',
}


def _norm_depto(nombre: str) -> str:
    s = str(nombre).strip()
    return _EQUIV_DEPTO.get(s, s)


# =========================================================================== #
# 1. Leer radar oficial de V2
# =========================================================================== #
def leer_radar_oficial_v2(ruta_v2: str) -> pd.DataFrame:
    """
    Extrae del xlsx V2 las 4 columnas del radar oficial DANE.
    Retorna DataFrame con: Departamento, radar_oficial_promedio,
                           radar_oficial_promedio_normalizado,
                           Clasificacion_radar_oficial_promedio
    """
    wb = load_workbook(ruta_v2, data_only=True)
    ws = wb[wb.sheetnames[0]]

    headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    data: Dict[str, List] = {}
    for c_idx, h in enumerate(headers, start=1):
        if h is not None:
            data[str(h).strip()] = [
                ws.cell(row=r, column=c_idx).value for r in range(2, ws.max_row + 1)
            ]

    df = pd.DataFrame(data)

    # Normalizar nombre de columna Departamento
    if 'Departamento' in df.columns:
        col_dep = 'Departamento'
    elif 'departamento' in df.columns:
        col_dep = 'departamento'
    else:
        raise ValueError("V2.xlsx no tiene columna 'Departamento'")

    cols_oficiales = [
        col_dep,
        'radar_oficial_promedio',
        'radar_oficial_promedio_normalizado',
        'Clasificacion_radar_oficial_promedio',
    ]
    faltantes = [c for c in cols_oficiales if c not in df.columns]
    if faltantes:
        raise ValueError(f"V2.xlsx falta columnas: {faltantes}")

    df_out = df[cols_oficiales].copy()
    df_out = df_out.rename(columns={col_dep: 'Departamento'})
    df_out = df_out[df_out['Departamento'].notna()].reset_index(drop=True)
    df_out['Departamento'] = df_out['Departamento'].astype(str).str.strip()

    # Invertir clasificacion del radar oficial para que Alto = riesgo alto
    df_out['Clasificacion_radar_oficial_promedio'] = (
        df_out['Clasificacion_radar_oficial_promedio'].astype(str).map(INVERSION)
    )

    print(f"Radar oficial V2: {len(df_out)} departamentos")
    return df_out


# =========================================================================== #
# 2. Calcular radar con clasificación invertida
# =========================================================================== #
def calcular_radar_invertido(df_ind: pd.DataFrame, nombre_radar: str) -> pd.DataFrame:
    """
    Promedio simple de 36 indicadores -> min-max 0-1 -> terciles -> invierte etiquetas.

    Parámetros
    ----------
    df_ind       : DataFrame con columna 'departamento' y los 36 indicadores
    nombre_radar : 'Radar_completo' o 'radar_actualizado'

    Retorna
    -------
    DataFrame con columnas:
        departamento,
        f'{nombre_radar}_promedio_normalizado',
        f'Clasificacion_{nombre_radar}'
    """
    df = df_ind.copy()
    df['departamento'] = df['departamento'].astype(str).str.strip().apply(_norm_depto)

    # Rellenar indicadores faltantes
    faltantes = [c for c in INDICADORES_36 if c not in df.columns]
    if faltantes:
        print(f"[{nombre_radar}] Indicadores faltantes (-> 0): {faltantes}")
        for c in faltantes:
            df[c] = 0.0

    for c in INDICADORES_36:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

    # Promedio simple -> normalización min-max
    radar_raw = df[INDICADORES_36].mean(axis=1)
    mn, mx = radar_raw.min(), radar_raw.max()
    if mx > mn:
        radar_norm = (radar_raw - mn) / (mx - mn)
    else:
        radar_norm = pd.Series([0.5] * len(radar_raw), index=radar_raw.index)

    # Terciles: alto valor -> 'Alto', medio -> 'Medio', bajo -> 'Bajo'
    clasif = pd.qcut(radar_norm, q=3, labels=ETIQUETAS_3, duplicates='drop').astype(str)

    col_norm = f'{nombre_radar}_promedio_normalizado'
    col_cls = f'Clasificacion_{nombre_radar}'

    out = pd.DataFrame({
        'departamento': df['departamento'].values,
        col_norm: radar_norm.values,
        col_cls: clasif.values,
    })

    print(f"\n=== {nombre_radar} ===")
    print(
        out.sort_values(col_norm, ascending=False)
        .to_string(index=False)
    )
    return out


# =========================================================================== #
# 3. Construir V3.xlsx
# =========================================================================== #
def construir_v3(
    ruta_v2: str,
    ruta_nuevo_alexa: str,
    ruta_actualizado: str,
    ruta_v3: str,
) -> pd.DataFrame:
    """
    Une las 3 fuentes en un único DataFrame y lo guarda como V3.xlsx.
    Left join desde el radar oficial (32 deptos) -> todos los deptos aparecen.
    """
    # Fuente 1: radar oficial
    df_oficial = leer_radar_oficial_v2(ruta_v2)

    # Fuente 2: Radar_completo (nuevo_alexa, 32 deptos)
    df_alexa = pd.read_csv(ruta_nuevo_alexa)
    print(f"\nnuevo_alexa: {len(df_alexa)} departamentos")
    df_completo = calcular_radar_invertido(df_alexa, 'Radar_completo')
    df_completo = df_completo.rename(columns={'departamento': 'Departamento'})
    df_completo['Departamento'] = df_completo['Departamento'].apply(_norm_depto)

    # Fuente 3: radar_actualizado (23 deptos)
    df_act_ind = pd.read_csv(ruta_actualizado)
    print(f"\nactualizado: {len(df_act_ind)} departamentos")
    df_actualizado = calcular_radar_invertido(df_act_ind, 'radar_actualizado')
    df_actualizado = df_actualizado.rename(columns={'departamento': 'Departamento'})
    df_actualizado['Departamento'] = df_actualizado['Departamento'].apply(_norm_depto)

    # Normalizar Departamento en oficial para merge
    df_oficial['Departamento'] = df_oficial['Departamento'].apply(_norm_depto)

    # Merge
    df_v3 = df_oficial.merge(df_completo, on='Departamento', how='left')
    df_v3 = df_v3.merge(df_actualizado, on='Departamento', how='left')

    # Guardar
    df_v3.to_excel(ruta_v3, index=False, engine='openpyxl')
    print(f"\nV3.xlsx guardado: {ruta_v3}")
    print(f"Shape: {df_v3.shape}  |  Columnas: {df_v3.columns.tolist()}")

    return df_v3


# =========================================================================== #
# 4. Métricas
# =========================================================================== #
def _metricas_par(
    y_true: pd.Series,
    y_pred: pd.Series,
    etiqueta: str,
) -> Tuple[dict, pd.DataFrame, np.ndarray]:
    """Calcula accuracy, F1-macro, Kappa y matriz de confusión para un par."""
    mask = (
        y_true.notna() & y_pred.notna()
        & (y_true.astype(str).str.strip() != '')
        & (y_pred.astype(str).str.strip() != '')
        & (y_true.astype(str) != 'nan')
        & (y_pred.astype(str) != 'nan')
    )
    yt = y_true[mask].astype(str).tolist()
    yp = y_pred[mask].astype(str).tolist()

    if len(yt) == 0:
        print(f"[{etiqueta}] Sin datos suficientes para métricas")
        return None, None, None

    acc = accuracy_score(yt, yp)
    p, r, f, _ = precision_recall_fscore_support(
        yt, yp, labels=ETIQUETAS_3, average='macro', zero_division=0
    )
    kappa = cohen_kappa_score(yt, yp, labels=ETIQUETAS_3)

    resumen = {
        'comparacion': etiqueta,
        'n_departamentos': len(yt),
        'accuracy': float(acc),
        'precision_macro': float(p),
        'recall_macro': float(r),
        'f1_macro': float(f),
        'cohen_kappa': float(kappa),
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
            'precision': float(d['precision']),
            'recall': float(d['recall']),
            'f1-score': float(d['f1-score']),
            'support': int(d['support']),
        })
    detalle_df = pd.DataFrame(detalle_rows)

    cm = confusion_matrix(yt, yp, labels=ETIQUETAS_3)
    return resumen, detalle_df, cm


def calcular_metricas_v3(ruta_v3: str, ruta_metricas: str) -> None:
    """
    Lee V3.xlsx y calcula métricas de clasificación:
      - Radar_completo vs radar_oficial (32 deptos)
      - radar_actualizado vs radar_oficial (deptos con datos)
    Exporta metricas_clasificacion_V3.xlsx con 3 hojas.
    """
    df = pd.read_excel(ruta_v3, engine='openpyxl')

    col_oficial = 'Clasificacion_radar_oficial_promedio'
    col_completo = 'Clasificacion_Radar_completo'
    col_actualizado = 'Clasificacion_radar_actualizado'

    for col in [col_oficial, col_completo, col_actualizado]:
        if col not in df.columns:
            raise ValueError(f"V3.xlsx falta columna: '{col}'")

    pares = [
        ('Radar_completo_vs_radar_oficial', col_completo, col_oficial),
        ('radar_actualizado_vs_radar_oficial', col_actualizado, col_oficial),
    ]

    resumenes, detalles, matrices = [], [], {}
    for etiqueta, col_pred, col_true in pares:
        res, det, cm = _metricas_par(df[col_true], df[col_pred], etiqueta)
        if res is not None:
            resumenes.append(res)
            detalles.append(det)
            matrices[etiqueta] = cm

    df_res = pd.DataFrame(resumenes)
    df_det = pd.concat(detalles, ignore_index=True) if detalles else pd.DataFrame()

    filas_cm = []
    for etiqueta, cm in matrices.items():
        filas_cm.append({
            'comparacion': etiqueta,
            'verdadero \\ predicho': '---',
            **{c: '' for c in ETIQUETAS_3},
        })
        for i, cr in enumerate(ETIQUETAS_3):
            fila = {'comparacion': etiqueta, 'verdadero \\ predicho': cr}
            for j, cp in enumerate(ETIQUETAS_3):
                fila[cp] = int(cm[i, j])
            filas_cm.append(fila)
        filas_cm.append({'comparacion': '', 'verdadero \\ predicho': ''})
    df_cm = pd.DataFrame(filas_cm)

    with pd.ExcelWriter(ruta_metricas, engine='openpyxl') as writer:
        df_res.to_excel(writer, sheet_name='resumen', index=False)
        df_det.to_excel(writer, sheet_name='detalle_por_clase', index=False)
        df_cm.to_excel(writer, sheet_name='matrices_confusion', index=False)

    print(f"\nMetricas exportadas: {ruta_metricas}")
    print("\n=== RESUMEN DE METRICAS V3 ===")
    print(df_res.to_string(index=False))


# =========================================================================== #
# Main
# =========================================================================== #
def main():
    print("=" * 60)
    print("GENERANDO comparacion_radares_V3.xlsx")
    print("=" * 60)
    print(f"Proyecto  : {_DIR_PROYECTO}")
    print(f"V2 fuente : {RUTA_V2}")
    print(f"nuevo_alexa: {RUTA_NUEVO_ALEXA}")
    print(f"actualizado: {RUTA_ACTUALIZADO}")
    print(f"Salida V3 : {RUTA_V3}")
    print(f"Metricas  : {RUTA_METRICAS_V3}")
    print()

    # Verificar entradas
    for ruta in [RUTA_V2, RUTA_NUEVO_ALEXA, RUTA_ACTUALIZADO]:
        if not os.path.isfile(ruta):
            raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

    # Construir V3
    construir_v3(RUTA_V2, RUTA_NUEVO_ALEXA, RUTA_ACTUALIZADO, RUTA_V3)

    # Calcular métricas
    print("\n" + "=" * 60)
    calcular_metricas_v3(RUTA_V3, RUTA_METRICAS_V3)

    print("\n" + "=" * 60)
    print("LISTO.")
    print(f"  V3 xlsx     : {RUTA_V3}")
    print(f"  Metricas V3 : {RUTA_METRICAS_V3}")
    print("=" * 60)


if __name__ == '__main__':
    main()
