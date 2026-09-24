"""
Diagnostico de `exclusion_beneficios_economicos` (informe 08). Todo offline, sin GPU, sobre
datos ya calculados:

  python experimentos/exp_exclusion_diagnostico.py

1. Referencia: SI de cada juez y SI/SI en las 962 juzgadas (rondas 1-2 y prueba del modelo NLI,
   sin los controles) y lista de los articulos con algun SI o DUDOSO.
2. 4 lugares (produccion, `candidatas_r2.pkl`): articulos > 0.766, top-3 del MAX y MAX de la
   gemela de osos polares.
3. Nacional (produccion, `scores_v2_32deptos.pkl`, MAX por departamento): rango de exclusion,
   % de articulos > 0.766 y efecto en el radar de quitarlo (25 indicadores, mismos cortes).
Salida: experimentos/resultados/exclusion/ (log por tee y casos_dudosos.csv).
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import exp_5ind_max_cortes as K  # noqa: E402

EX = "exclusion_beneficios_economicos"
R = "experimentos/resultados"
DIR = os.path.join(R, "exclusion")
JUICIOS = ["juicio_5ind", "juicio_5ind_holdout", "juicio_5ind_r2", "juicio_modelo_nli"]
LUGARES = ["Antioquia", "Maicao", "Oicata", "Paraguachon"]
CORTES = (0.766, 0.9233)


def _etiquetas(d: str, carpeta: str) -> dict:
    out = {}
    base = os.path.join(R, d, carpeta)
    for fn in sorted(os.listdir(base)):
        with open(os.path.join(base, fn), encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    o = json.loads(linea)
                    out[o["id"]] = o[EX]
    return out


def referencia(titulos: pd.DataFrame):
    filas, casos = [], []
    for d in JUICIOS:
        r = pd.read_csv(os.path.join(R, d, "referencia.csv"))
        if "origen" in r.columns:
            r = r[r["origen"] != "control"]
        a, b = _etiquetas(d, "etiquetas_a"), _etiquetas(d, "etiquetas_b")
        filas.append({"juicio": d, "juzgados": len(r), "SI_a": int((r[EX + "__a"] == "SI").sum()),
                      "SI_b": int((r[EX + "__b"] == "SI").sum()), "SI_SI": int(r[EX].sum())})
        for _, x in r[(r[EX + "__a"] != "NO") | (r[EX + "__b"] != "NO")].iterrows():
            t = titulos.loc[x["url"]] if x["url"] in titulos.index else {}
            casos.append({"juicio": d, "juez_a": x[EX + "__a"], "juez_b": x[EX + "__b"],
                          "departamento": t.get("departamento", ""), "titulo": t.get("titulo", ""),
                          "cita_a": a.get(x["id"], ["", ""])[1], "cita_b": b.get(x["id"], ["", ""])[1],
                          "url": x["url"]})
    F = pd.DataFrame(filas)
    F.loc[len(F)] = ["total", *F[["juzgados", "SI_a", "SI_b", "SI_SI"]].sum().tolist()]
    return F, pd.DataFrame(casos)


def lugares(titulos: pd.DataFrame):
    c = pd.read_pickle(os.path.join(R, "juicio_5ind_r2", "candidatas_r2.pkl"))
    lug = pd.read_csv(os.path.join(R, "juicio_5ind", "url_lugares.csv"))
    col, gem = f"{EX}__vig", f"{EX}__vig__abs"
    for l in LUGARES:
        s = c[c["url"].isin(set(lug.loc[lug["lugar"] == l, "url"]))]
        s = s.sort_values([col, "url"], ascending=[False, True])
        print(f"{l}: {len(s)} articulos; > {CORTES[0]}: {int((s[col] > CORTES[0]).sum())}; "
              f"MAX vigente {s[col].max():.3f}; MAX gemela (osos polares) {s[gem].max():.3f}")
        for _, x in s.head(3).iterrows():
            print(f"    {x[col]:.3f}  {titulos['titulo'].get(x['url'], '')}")


def nacional():
    corpus = pd.read_pickle(K.CORPUS).reset_index(drop=True)
    d = pd.read_pickle(K.V2NAC).reset_index(drop=True)
    assert len(d) == len(corpus)
    sesgo = d["sesgo"].values
    S = pd.DataFrame({c: np.clip(np.clip(d[f"ent_{c}"].values - sesgo, 0, None) * (1 - d[f"neu_{c}"].values), 0, 1)
                      for c in K.V2.TODAS})
    m = S.groupby(corpus["departamento"].values).max()
    assert m.shape == (32, 26)
    ex, std = m[EX], m.std().sort_values()
    print(f"MAX por departamento: min {ex.min():.3f} ({ex.idxmin()}), mediana {ex.median():.3f}, "
          f"max {ex.max():.3f}; std {ex.std():.4f} (puesto {std.index.get_loc(EX) + 1} de 26 de menor a mayor)")
    print(f"Articulos con s > {CORTES[0]}: {(S[EX] > CORTES[0]).mean():.1%} de {len(S)}")
    r26, r25 = m.mean(axis=1), m.drop(columns=[EX]).mean(axis=1)
    of = pd.read_excel(K.REFERENCIA, engine="openpyxl")
    of.columns = [str(c).strip() for c in of.columns]
    of["_k"] = of["Departamento"].map(K._norm)
    c26, c25 = K.constancia(r26, *CORTES, of), K.constancia(r25, *CORTES, of)
    cambian = int((c26["m"]["clase"].values != c25["m"]["clase"].values).sum())
    print(f"Radar sin exclusion (25) frente a 26: Spearman {spearmanr(r26, r25).correlation:.4f}; "
          f"diferencia media {float((r25 - r26).mean()):+.4f}, max |dif| {float(np.abs(r25 - r26).max()):.4f}")
    for nom, c in (("26 indicadores", c26), ("25, sin exclusion, mismos cortes", c25)):
        print(f"  {nom}: clases {c['dist']}; accuracy {c['acc']:.3f}; Spearman frente al DANE {c['rho']:+.4f}")
    print(f"  Departamentos que cambian de clase: {cambian}")


def main():
    os.makedirs(DIR, exist_ok=True)
    c5 = pd.read_pickle("datos/corpus/df_corpus_5lugares.pkl").set_index("url")
    cn = pd.read_pickle(K.CORPUS).set_index("url")[["titulo", "departamento"]]
    titulos = pd.concat([cn, c5[["titulo"]]])
    titulos = titulos[~titulos.index.duplicated()]
    print("== 1. Referencia (962 juzgados, sin controles)")
    F, casos = referencia(titulos)
    print(F.to_string(index=False))
    casos.to_csv(os.path.join(DIR, "casos_dudosos.csv"), index=False)
    print(f"Articulos con algun SI o DUDOSO: {len(casos)} (detalle en {DIR}/casos_dudosos.csv)")
    print("\n== 2. Cuatro lugares (produccion)")
    lugares(titulos)
    print("\n== 3. Nacional (produccion, MAX por departamento)")
    nacional()


if __name__ == "__main__":
    main()
