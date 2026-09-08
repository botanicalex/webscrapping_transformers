# -*- coding: utf-8 -*-
"""
Backlog punto 3 (07_backlog.md): A/B del pre-filtro social V2 (score_social_v2 >=
0.85), pero con AUC y control absurdo POR INDICADOR — no la correlacion agregada
del radar completo, que ya se midio el 2026-08-30 (+0.384 sin prefiltro vs +0.376
con, exp_correlacion_v2_nacional.py) y cuya propia entrada del log dice que no
alcanza para decidir esto.

El umbral 0.85 se eligio en exp_agregacion_v2.py Parte A mirando SOLO retencion de
positivos de plata (pasa 92.4%/95.0%) sobre el corpus de 5 lugares (1.647
articulos). Nunca se miro si enmascarar con ese umbral cambia el AUC. Aqui se
mide, sobre los 32 departamentos (scores_v2_32deptos.pkl, 11.439 articulos,
mucha mas potencia estadistica), sin volver a tocar la GPU (regla 8) y sin
recalcular el umbral (eso seria un experimento aparte, regla 7 - una variable).

Pregunta: aplicar el pre-filtro (forzar a 0 los articulos con score_social_v2 <
0.85) antes de puntuar, ¿mejora, empeora o no cambia el AUC contra el estandar de
plata en los 2 indicadores que lo tienen (presencia_grupos_armados,
grupos_etnicos_existentes)? Y el control absurdo (NULA_TEST, contenido
imposible): ¿el pre-filtro le agrega "AUC" espurio contra esos mismos silver
labels? Si lo hace, un AUC mas alto en el indicador real con prefiltro no se
podria atribuir al prefiltro filtrando irrelevancia: se podria atribuir a que el
prefiltro correlaciona con el TEMA (conflicto/comunidad) y por eso separa
cualquier cosa, real o absurda, igual de "bien".

Evidencia a favor de MANTENER el prefiltro: AUC igual o mejor con prefiltro en
los 2 indicadores reales, Y el control absurdo no gana AUC con el prefiltro (o
gana menos que el indicador real).
Evidencia a favor de RETIRARLO (backlog lo llama "prescindible"): AUC cae con el
prefiltro en cualquiera de los 2 indicadores reales, o cae igual que en el
indicador real y en el control absurdo (indistinguibles => no aporta nada
especifico del indicador).
No concluyente: diferencias dentro del intervalo de bootstrap (no se distinguen
de la variacion por muestreo).

Puertas del skill experimento-hipotesis (paso 7), adaptadas a "variante =
aplicar el prefiltro":
  1. El control absurdo corregido no debe empeorar (media sube) al aplicar el
     prefiltro.
  2. AUC real: si sube o se mantiene con el prefiltro -> a favor de mantenerlo.
     Si baja, ver cuanto.
  3. Si AUC real sube pero el AUC-espurio del control TAMBIEN sube en magnitud
     comparable, es el modo de fallo de la regla 1 (CLAUDE.md): un "si" que no
     significa nada especifico del indicador. Se rechaza igual.
"""
import os

import numpy as np
import pandas as pd

import hipotesis_base as HB
import silver

SCORES = "../datos/scores/scores_v2_32deptos.pkl"
CORPUS = "../datos/corpus/df_corpus_combinado_32deptos.pkl"
SALIDA = "resultados/exp_prefiltro_auc_indicador.xlsx"

UMBRAL_PREFILTRO = 0.85
N_BOOT = 2000
RNG = np.random.default_rng(20260831)


def cargar():
    """Alinea scores_v2_32deptos.pkl (sin 'texto') con el corpus (para poder
    etiquetar con silver.etiquetar, que necesita titulo+texto). Alineacion por
    POSICION: generar_scores_32deptos.py filtra el mismo corpus por 'texto' no
    vacio y hace reset_index(drop=True) en el mismo orden, sin barajar."""
    d = pd.read_pickle(SCORES)
    c = pd.read_pickle(CORPUS)
    sin_texto = c["texto"].isna() | (c["texto"].astype(str).str.strip() == "")
    c = c[~sin_texto].reset_index(drop=True)
    assert len(c) == len(d), f"desalineado: corpus={len(c)} scores={len(d)}"
    assert (c["titulo"].values == d["titulo"].values).all(), "titulo no coincide: desalineado"
    d = d.copy()
    d["texto"] = c["texto"].values
    return d


def corregido(d: pd.DataFrame, col: str) -> np.ndarray:
    e, n, sesgo = d[f"ent_{col}"].values, d[f"neu_{col}"].values, d["sesgo"].values
    return np.clip(np.clip(e - sesgo, 0, None) * (1 - n), 0, 1)


def bootstrap_delta_auc(s_sin, s_con, y, n_boot=N_BOOT):
    """IC 95% de (AUC_con - AUC_sin) por remuestreo de articulos con reemplazo."""
    m = ~np.isnan(y)
    s0, s1, yy = s_sin[m], s_con[m], y[m]
    n = len(yy)
    deltas = np.empty(n_boot)
    for i in range(n_boot):
        idx = RNG.integers(0, n, n)
        deltas[i] = silver.auc(s1[idx], yy[idx]) - silver.auc(s0[idx], yy[idx])
    return float(deltas.mean()), (float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5)))


def main():
    d = cargar()
    print(f"Scores: {d.shape[0]} articulos, {d['departamento'].nunique()} departamentos")

    rel = d["score_social_v2"].values >= UMBRAL_PREFILTRO
    print(f"Pre-filtro V2 (umbral {UMBRAL_PREFILTRO}): pasan {rel.sum()}/{len(rel)} ({rel.mean():.1%})")

    silver_labels = {ind: silver.etiquetar(d, kws)["label"].values
                      for ind, kws in HB.KEYWORDS_SILVER.items()}
    for ind, y in silver_labels.items():
        print(f"  {ind}: pos={int((y == 1).sum())} neg={int((y == 0).sum())}")

    filas = []

    # ── 1. AUC por indicador real, ent crudo y score corregido, sin/con prefiltro ──
    print(f"\n{'=' * 90}\n1. AUC POR INDICADOR REAL\n{'=' * 90}")
    for ind, y in silver_labels.items():
        ent = d[f"ent_{ind}"].values
        cor = corregido(d, ind)

        ent_sin, ent_con = ent, np.where(rel, ent, 0.0)
        cor_sin, cor_con = cor, np.where(rel, cor, 0.0)

        auc_ent_sin, auc_ent_con = silver.auc(ent_sin, y), silver.auc(ent_con, y)
        auc_cor_sin, auc_cor_con = silver.auc(cor_sin, y), silver.auc(cor_con, y)

        retencion = float(rel[y == 1].mean()) if (y == 1).any() else float("nan")

        d_ent, ic_ent = bootstrap_delta_auc(ent_sin, ent_con, y)
        d_cor, ic_cor = bootstrap_delta_auc(cor_sin, cor_con, y)

        print(f"\n{ind}  (retiene {retencion:.1%} de los positivos de plata)")
        print(f"  {'':<18}{'AUC sin':>10}{'AUC con':>10}{'delta':>9}{'IC95%':>22}")
        print(f"  {'ent crudo':<18}{auc_ent_sin:>10.4f}{auc_ent_con:>10.4f}{d_ent:>+9.4f}"
              f"   [{ic_ent[0]:+.4f}, {ic_ent[1]:+.4f}]")
        print(f"  {'score corregido':<18}{auc_cor_sin:>10.4f}{auc_cor_con:>10.4f}{d_cor:>+9.4f}"
              f"   [{ic_cor[0]:+.4f}, {ic_cor[1]:+.4f}]")

        filas.append({"tipo": "real", "indicador": ind, "escala": "ent_crudo",
                      "auc_sin": auc_ent_sin, "auc_con": auc_ent_con, "delta": d_ent,
                      "ic95_low": ic_ent[0], "ic95_high": ic_ent[1],
                      "retencion_positivos": retencion,
                      "n_pos": int((y == 1).sum()), "n_neg": int((y == 0).sum())})
        filas.append({"tipo": "real", "indicador": ind, "escala": "score_corregido",
                      "auc_sin": auc_cor_sin, "auc_con": auc_cor_con, "delta": d_cor,
                      "ic95_low": ic_cor[0], "ic95_high": ic_cor[1],
                      "retencion_positivos": retencion,
                      "n_pos": int((y == 1).sum()), "n_neg": int((y == 0).sum())})

    # ── 2. Control absurdo: NULA_TEST contra los MISMOS silver labels ──────────
    print(f"\n{'=' * 90}\n2. CONTROL ABSURDO — NULA_TEST contra los mismos silver labels\n{'=' * 90}")
    print("Si el pre-filtro le da AUC a una hipotesis de contenido imposible contra")
    print("estos labels, el AUC del indicador real no se puede atribuir al prefiltro")
    print("filtrando irrelevancia: el prefiltro estaria correlacionando con el TEMA.\n")

    ent_nula = d["ent_NULA_TEST"].values
    cor_nula = corregido(d, "NULA_TEST")
    ent_nula_sin, ent_nula_con = ent_nula, np.where(rel, ent_nula, 0.0)
    cor_nula_sin, cor_nula_con = cor_nula, np.where(rel, cor_nula, 0.0)

    for ind, y in silver_labels.items():
        auc_ent_sin, auc_ent_con = silver.auc(ent_nula_sin, y), silver.auc(ent_nula_con, y)
        auc_cor_sin, auc_cor_con = silver.auc(cor_nula_sin, y), silver.auc(cor_nula_con, y)
        d_ent, ic_ent = bootstrap_delta_auc(ent_nula_sin, ent_nula_con, y)
        d_cor, ic_cor = bootstrap_delta_auc(cor_nula_sin, cor_nula_con, y)

        print(f"\nNULA_TEST vs labels de {ind}")
        print(f"  {'':<18}{'AUC sin':>10}{'AUC con':>10}{'delta':>9}{'IC95%':>22}")
        print(f"  {'ent crudo':<18}{auc_ent_sin:>10.4f}{auc_ent_con:>10.4f}{d_ent:>+9.4f}"
              f"   [{ic_ent[0]:+.4f}, {ic_ent[1]:+.4f}]")
        print(f"  {'score corregido':<18}{auc_cor_sin:>10.4f}{auc_cor_con:>10.4f}{d_cor:>+9.4f}"
              f"   [{ic_cor[0]:+.4f}, {ic_cor[1]:+.4f}]")

        filas.append({"tipo": "absurdo", "indicador": f"NULA_TEST_vs_{ind}", "escala": "ent_crudo",
                      "auc_sin": auc_ent_sin, "auc_con": auc_ent_con, "delta": d_ent,
                      "ic95_low": ic_ent[0], "ic95_high": ic_ent[1],
                      "retencion_positivos": float("nan"),
                      "n_pos": int((y == 1).sum()), "n_neg": int((y == 0).sum())})
        filas.append({"tipo": "absurdo", "indicador": f"NULA_TEST_vs_{ind}", "escala": "score_corregido",
                      "auc_sin": auc_cor_sin, "auc_con": auc_cor_con, "delta": d_cor,
                      "ic95_low": ic_cor[0], "ic95_high": ic_cor[1],
                      "retencion_positivos": float("nan"),
                      "n_pos": int((y == 1).sum()), "n_neg": int((y == 0).sum())})

    # ── 3. Control absurdo cruda/corregida, escala completa (no vs silver) ─────
    print(f"\n{'=' * 90}\n3. CONTROL ABSURDO — escala completa (sin condicionar a silver labels)\n{'=' * 90}")
    print(f"{'':<20}{'media cruda':>14}{'prop>0.9 cruda':>16}{'media corregida':>18}")
    for etiqueta, ent_x, cor_x in [("sin_prefiltro", ent_nula_sin, cor_nula_sin),
                                    ("con_prefiltro", ent_nula_con, cor_nula_con)]:
        media_cruda = float(np.mean(ent_x))
        prop09 = float((ent_x > 0.9).mean())
        media_cor = float(np.mean(cor_x))
        print(f"{etiqueta:<20}{media_cruda:>14.4f}{prop09:>16.1%}{media_cor:>18.4f}")
        filas.append({"tipo": "absurdo_escala_completa", "indicador": "NULA_TEST", "escala": etiqueta,
                      "auc_sin": float("nan"), "auc_con": float("nan"), "delta": float("nan"),
                      "ic95_low": float("nan"), "ic95_high": float("nan"),
                      "retencion_positivos": float("nan"),
                      "media_cruda": media_cruda, "prop09_cruda": prop09, "media_corregida": media_cor,
                      "n_pos": float("nan"), "n_neg": float("nan")})

    os.makedirs("resultados", exist_ok=True)
    pd.DataFrame(filas).to_excel(SALIDA, index=False)
    print(f"\nGuardado -> {SALIDA}")


if __name__ == "__main__":
    main()
