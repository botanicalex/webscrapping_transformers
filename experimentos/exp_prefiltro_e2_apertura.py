"""
F1-T1 (PREREG_prefiltro_indicador_e2.md §2): tasas de apertura, solo texto (sin GPU).
Premisa visible = cuerpo recortado con la hipotesis DE CADA indicador (tokenizer del NLI), normalizada;
tasa = fraccion de los 11.439 articulos nacionales que cumple la lista.

  PYTHONIOENCODING=utf-8 python experimentos/exp_prefiltro_e2_apertura.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_prefiltro_e2_comun as C  # noqa: E402

DIR = "experimentos/resultados/juicio_prefiltro_e2"


def main():
    src_txt = open(C.SRC, encoding="utf-8").read()
    for k, h in C.V2.TODAS.items():
        assert h in src_txt, f"hipotesis V2 de {k} no esta en src"
    prod = C.prefiltro_produccion()
    corpus = pd.read_pickle(C.CORPUS_NAC).reset_index(drop=True)
    assert len(corpus) == 11439
    textos = corpus["texto"].fillna("").astype(str).tolist()
    tok = C.cargar_tokenizer()
    grupos = ([(i, "tramo", C.P.LISTAS_TRAMO_1[i]) for i in C.P.TRAMO_1]
              + [(i, "solo_apertura", rx) for i, rx in C.P.LISTAS_SOLO_APERTURA.items()]
              + [(i, "produccion", rx) for i, rx in prod.items()])
    filas = []
    for ind, grupo, rx in grupos:
        pv = C.premisa_visible_prod(textos, tok, C.V2.TODAS[ind])
        g = C.compuerta(pv, rx)
        n = int(sum(g))
        tasa = n / len(g)
        filas.append({"indicador": ind, "grupo": grupo, "n_abre": n, "tasa": round(tasa, 4),
                      "supera_techo": bool(tasa > C.P.TECHO_APERTURA)})
        print(f"{grupo:14s} {ind:38s} {n:6d} {tasa:.4f} {'SUPERA' if tasa > C.P.TECHO_APERTURA else ''}", flush=True)
    os.makedirs(DIR, exist_ok=True)
    pd.DataFrame(filas).to_csv(os.path.join(DIR, "aperturas.csv"), index=False)


if __name__ == "__main__":
    main()
