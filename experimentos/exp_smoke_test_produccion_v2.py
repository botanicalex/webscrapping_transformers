# -*- coding: utf-8 -*-
"""
Smoke test CON GPU de la promoción de V2 a `src/` (2026-08-31, ver
contexto/08_log_decisiones.md). Autorizado explícitamente por el usuario:
GPU para transformers sí, scraping no.

Corre el `src/Transformer_optimo.py` REAL (modificado) de punta a punta
sobre el corpus de 5 lugares (datos/corpus/df_corpus_5lugares.pkl, 1.647
artículos, ya existente -- sin scraping nuevo). Para 2 indicadores, compara
el resultado contra `nli_core` calculándolo de forma independiente -- mismo
patrón que `nli_core.verificar_contra_produccion()` (regla 6 del proyecto),
que hoy solo compara contra el baseline V0 y quedó obsoleto en cuanto
Transformer_optimo.py cambió de hipótesis.

Qué confirma: que el código de producción (batching, tokenización, el orden
de operaciones de la fórmula corregida) ejecuta igual que el motor de
experimentos ya validado -- no solo que la lógica en papel es la misma
(eso ya lo confirmó exp_verificar_promocion_v2.py, sin GPU).

Guarda el resultado como el nuevo baseline de verificación
(datos/scores/df_procesado_baseline_v2.pkl) para que
nli_core.verificar_contra_produccion() tenga contra qué comparar de ahora
en adelante.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import numpy as np
import pandas as pd

import Transformer_optimo as tf  # noqa: E402
from nli_core import NLIScorer  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402

CORPUS = "../datos/corpus/df_corpus_5lugares.pkl"
BASELINE_SALIDA = "../datos/scores/df_procesado_baseline_v2.pkl"

INDICADORES_A_VERIFICAR = ["presencia_grupos_armados", "grupos_etnicos_existentes"]
TOL = 1e-4


def main():
    t0 = time.time()
    df = pd.read_pickle(CORPUS)
    df = df[df["texto"].notna() & (df["texto"].astype(str).str.strip() != "")].reset_index(drop=True)
    print(f"Corpus: {len(df)} articulos")

    print("\n[1/2] Corriendo src/Transformer_optimo.py (PipelineTransformers.procesar) real...")
    pipeline = tf.PipelineTransformers()
    df_procesado = pipeline.procesar(df)
    dt = time.time() - t0
    print(f"Completado en {dt/60:.1f} min")

    df_procesado.to_pickle(BASELINE_SALIDA)
    print(f"Guardado como nuevo baseline -> {BASELINE_SALIDA}")

    print("\n[2/2] Verificando contra nli_core (motor independiente, ya validado)...")
    scorer = NLIScorer()
    prem = df["texto"].fillna("").astype(str).tolist()

    sesgo_nli_core = np.mean(
        [np.asarray(scorer.score(prem, h), dtype=float) for h in V2.NULAS_CALIBRACION], axis=0
    )
    diff_sesgo = np.abs(sesgo_nli_core - df_procesado["sesgo"].values).max()
    print(f"  sesgo: max|dif| = {diff_sesgo:.2e}  -> {'OK' if diff_sesgo < TOL else 'DESVIACION'}")

    todo_ok = diff_sesgo < TOL
    for ind in INDICADORES_A_VERIFICAR:
        hip = V2.TODAS[ind]
        p = scorer.score(prem, hip, devolver_todo=True)
        ent = np.asarray(p["entailment"], dtype=float)
        neu = np.asarray(p["neutral"], dtype=float)
        corregido_nli_core = np.clip(np.clip(ent - sesgo_nli_core, 0, None) * (1 - neu), 0, 1)
        diff = np.abs(corregido_nli_core - df_procesado[ind].values).max()
        ok = diff < TOL
        todo_ok = todo_ok and ok
        print(f"  '{ind}': max|dif| = {diff:.2e}  -> {'OK' if ok else 'DESVIACION'}")

    print(f"\n{'OK' if todo_ok else 'FALLO'}: src/Transformer_optimo.py {'reproduce' if todo_ok else 'NO reproduce'} "
          f"nli_core dentro de tolerancia ({TOL:.0e}).")
    assert todo_ok, "Transformer_optimo.py (V2) no reproduce nli_core -- no promover sin investigar"


if __name__ == "__main__":
    main()
