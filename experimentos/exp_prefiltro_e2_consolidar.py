"""
F2 de la etapa 2 del pre-filtro por indicador: consolida las etiquetas de juez-c y juez-d.

Comprueba que cada salida tenga los mismos ids y en el mismo orden que su lote, une por url con
mapa_ids.csv y escribe etiquetas.csv (una fila por url x indicador: etiqueta_c, etiqueta_d, ref).
Reporta kappa por indicador (SI frente a {NO, DUDOSO}), SI/SI en el pool de cada indicador y
cobertura de cada top-k. No calcula M1-M4 (eso es la F3).
Uso: python experimentos/exp_prefiltro_e2_consolidar.py
"""
import glob
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from hipotesis_prefiltro_e2 import TRAMO_1  # noqa: E402

CARPETA = "experimentos/resultados/juicio_prefiltro_e2"


def leer(carpeta_etiquetas):
    filas = []
    for ruta_lote in sorted(glob.glob(f"{CARPETA}/lotes/lote_*.jsonl")):
        nombre = os.path.basename(ruta_lote)
        with open(ruta_lote, encoding="utf-8") as f:
            ids_lote = [json.loads(l)["id"] for l in f if l.strip()]
        with open(f"{CARPETA}/{carpeta_etiquetas}/{nombre}", encoding="utf-8") as f:
            salida = [json.loads(l) for l in f if l.strip()]
        assert [s["id"] for s in salida] == ids_lote, f"ids distintos en {carpeta_etiquetas}/{nombre}"
        for s in salida:
            for ind in TRAMO_1:
                valor = s[ind][0]
                assert valor in ("SI", "NO", "DUDOSO"), (nombre, s["id"], ind, valor)
                filas.append({"id": s["id"], "indicador": ind, "etiqueta": valor})
    return pd.DataFrame(filas)


def kappa(a, b):
    a, b = pd.Series(a).astype(bool), pd.Series(b).astype(bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def main():
    c = leer("etiquetas_c").rename(columns={"etiqueta": "etiqueta_c"})
    d = leer("etiquetas_d").rename(columns={"etiqueta": "etiqueta_d"})
    et = c.merge(d, on=["id", "indicador"], how="outer", validate="1:1")
    mapa = pd.read_csv(f"{CARPETA}/mapa_ids.csv")
    et = et.merge(mapa, on="id", how="left", validate="m:1")
    assert et["url"].notna().all() and et[["etiqueta_c", "etiqueta_d"]].notna().all().all()
    et["ref"] = (et["etiqueta_c"] == "SI") & (et["etiqueta_d"] == "SI")
    et.to_csv(f"{CARPETA}/etiquetas.csv", index=False)

    pool = pd.read_csv(f"{CARPETA}/pool.csv")
    juzgadas = set(et["url"])
    filas = []
    for ind in TRAMO_1:
        e = et[et["indicador"] == ind]
        p = pool[pool["indicador"] == ind]
        urls_pool = set(p["url"])
        e_pool = e[e["url"].isin(urls_pool)]
        cob = []
        for col in ("en_topk_v01", "en_topk_v08"):
            for _, g in p[p[col]].groupby("lugar"):
                cob.append(g["url"].isin(juzgadas).mean())
        filas.append({
            "indicador": ind,
            "kappa_todo": round(kappa(e["etiqueta_c"] == "SI", e["etiqueta_d"] == "SI"), 3),
            "kappa_pool": round(kappa(e_pool["etiqueta_c"] == "SI", e_pool["etiqueta_d"] == "SI"), 3),
            "si_c_pool": int((e_pool["etiqueta_c"] == "SI").sum()),
            "si_d_pool": int((e_pool["etiqueta_d"] == "SI").sum()),
            "si_si_pool": int(e_pool["ref"].sum()),
            "n_pool": len(urls_pool),
            "cobertura_min": round(min(cob), 3) if cob else float("nan"),
            "no_medible": int(e_pool["ref"].sum()) < 5,
            "kappa_baja": kappa(e_pool["etiqueta_c"] == "SI", e_pool["etiqueta_d"] == "SI") < 0.4,
        })
    res = pd.DataFrame(filas)
    res.to_csv(f"{CARPETA}/consolidacion.csv", index=False)
    print(f"url juzgadas: {len(juzgadas)}; filas url x indicador: {len(et)}")
    print(res.to_string(index=False))


if __name__ == "__main__":
    main()
