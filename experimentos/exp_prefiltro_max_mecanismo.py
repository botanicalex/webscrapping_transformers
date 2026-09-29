# -*- coding: utf-8 -*-
"""
Mecanismo del pre-filtro social bajo MAX. EXPLORATORIO y posterior al pre-registro
(experimentos/PREREG_prefiltro_max.md): no decide nada, solo explica por que C4 no mejora. Reutiliza
las funciones de exp_prefiltro_max.py (sin llamar a su main()) y las mismas celdas del bloque C.

Preguntas:
  1. De los puestos de los top-10 de las 23 celdas (sin mascara), ¿cuantos artefactos saca la mascara
     y de que tipo (positivo / no positivo de referencia)?
  2. En los 759 juzgados, ¿que fraccion de positivos y de negativos enmascara, por indicador?
  3. Los positivos de grupos armados con puntaje social < umbral: ¿en que lugar y en que rango del
     ranking sin mascara estaban?
  4. El caso de Chocó (unico positivo que sale de un top-10): top-10 antes y despues.

  PYTHONIOENCODING=utf-8 python experimentos/exp_prefiltro_max_mecanismo.py
Salida: experimentos/resultados/exp_prefiltro_max_mecanismo.xlsx
"""
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import exp_prefiltro_max as X  # noqa: E402

U = X.UMBRAL
SALIDA = "experimentos/resultados/exp_prefiltro_max_mecanismo.xlsx"


def main():
    D = X.cargar()
    places = X.armar_lugares(D)
    cells = X.celdas(places)
    tit = D.nac.set_index("url")["titulo"]
    tit_l = D.l.set_index("url")["titulo"]
    titulo = lambda u: str((tit_l if u in tit_l.index else tit).get(u, ""))  # noqa: E731

    # 1. articulos que la mascara saca de los top-10 (sin mascara) de cada celda
    filas, n_puestos = [], 0
    for p, i in cells:
        m = p.social >= U
        x = p.S[i]
        o = np.lexsort((np.arange(p.n), -x))
        k = min(10, int((x > 0).sum()))
        n_puestos += k
        for rango, j in enumerate(o[:k], 1):
            if not m[j]:
                filas.append({"indicador": i, "lugar": p.name, "rango_sin_mascara": rango, "score": float(x[j]),
                              "score_social": float(p.social[j]), "positivo_de_referencia": bool(p.pos[i][j]),
                              "titulo": titulo(p.urls[j])})
    sacados = pd.DataFrame(filas)
    resumen = pd.DataFrame([{
        "umbral": U, "celdas": len(cells), "puestos_top10": n_puestos, "articulos_sacados": len(sacados),
        "sacados_positivos": int(sacados["positivo_de_referencia"].sum()),
        "sacados_no_positivos": int((~sacados["positivo_de_referencia"]).sum())}])
    print("1.", resumen.to_dict("records")[0])

    # 2. juzgados (759) enmascarados, por indicador y etiqueta
    J = X.tabla_juzgados(D)
    mk = J.social >= U
    filas = []
    for i in X.IND5:
        y = J.y[i]
        filas.append({"indicador": i, "positivos": int(y.sum()), "positivos_enmascarados": int(y[~mk].sum()),
                      "frac_positivos_enmascarados": float(y[~mk].sum() / max(y.sum(), 1)),
                      "negativos": int((1 - y).sum()), "negativos_enmascarados": int((1 - y)[~mk].sum()),
                      "frac_negativos_enmascarados": float((1 - y)[~mk].sum() / max((1 - y).sum(), 1))})
    juz = pd.DataFrame(filas)
    print(f"2. juzgados {J.n}, enmascarados {int((~mk).sum())} ({(~mk).mean():.1%})")
    print(juz.round(3).to_string(index=False))

    # 3. positivos de grupos armados enmascarados
    filas = []
    for p in places:
        x, m = p.S[X.GA], p.social >= U
        rango = pd.Series(-x).rank(method="first").values.astype(int)
        for j in np.where(p.pos[X.GA] & ~m)[0]:
            filas.append({"lugar": p.name, "rango_sin_mascara": int(rango[j]), "score": float(x[j]),
                          "score_social": float(p.social[j]), "titulo": titulo(p.urls[j])})
    perd = pd.DataFrame(filas)
    print("3. positivos de grupos armados enmascarados:", len(perd))
    print(perd[["lugar", "rango_sin_mascara", "score", "score_social"]].round(3).to_string(index=False))

    # 4. Chocó, grupos armados: top-10 antes y despues
    p = [q for q in places if q.name == "Chocó"][0]
    x = p.S[X.GA]
    m = p.social >= U
    filas = []
    for cond, arr in (("sin mascara", x), ("con mascara", x * m)):
        for rango, j in enumerate(np.lexsort((np.arange(p.n), -arr))[:10], 1):
            filas.append({"condicion": cond, "rango": rango, "score": float(arr[j]), "score_social": float(p.social[j]),
                          "positivo": bool(p.pos[X.GA][j]), "titulo": titulo(p.urls[j])})
    choco = pd.DataFrame(filas)

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with pd.ExcelWriter(SALIDA, engine="openpyxl") as w:
        resumen.to_excel(w, sheet_name="resumen_top10", index=False)
        sacados.to_excel(w, sheet_name="sacados_del_top10", index=False)
        juz.to_excel(w, sheet_name="juzgados_enmascarados", index=False)
        perd.to_excel(w, sheet_name="positivos_GA_enmascarados", index=False)
        choco.to_excel(w, sheet_name="choco_GA_top10", index=False)
    print(f"\nGuardado -> {SALIDA}")


if __name__ == "__main__":
    main()
