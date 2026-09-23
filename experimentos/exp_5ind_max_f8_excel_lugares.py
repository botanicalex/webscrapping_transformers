"""
F8 del plan 5ind MAX, paso 5: Excel de lugares (Maicao, Oicata, Paraguachon) antes/despues,
con el formato de los `radar_resumen_<lugar>.xlsx` de la profesora (sin GPU).

Formato (copiado de los archivos de la profesora, que no estan en el repo): hoja `Resumen`,
columnas `Dimensión | Indicador | Score (0-100) | URL artículo top`, 26 filas en el orden de
los bloques A-E de radar.py, score = MAX del lugar x 100 redondeado, sin estilos. Se agrega
una hoja `Radar` (radar = media de los 26 MAX, clase y cortes usados), que el original no trae.

  antes   = V01: score de produccion hasta F7 (df_procesado_5lugares.pkl), cortes 0.766/0.9233
  despues = V08: grupos armados x compuerta de src/Transformer_optimo.py, cortes de
            src/config_pipeline.py (0.7574/0.9233)

Lugares desde experimentos/resultados/juicio_5ind/url_lugares.csv (Paraguachon = pkl
individual, 77 articulos; 57 tambien son de Maicao).

  python experimentos/exp_5ind_max_f8_excel_lugares.py
Salida: experimentos/resultados/excel_lugares_f8/
"""
import inspect
import math
import os
import sys

import numpy as np
import pandas as pd
from openpyxl import Workbook

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "src"))
import config_pipeline as cfg  # noqa: E402
import hipotesis_5ind_max as H  # noqa: E402
import Transformer_optimo as T  # noqa: E402

PROCESADO = "resultados/tablas_lugares_max/df_procesado_5lugares.pkl"
URL_LUGARES = "experimentos/resultados/juicio_5ind/url_lugares.csv"
DIR = "experimentos/resultados/excel_lugares_f8"
PROFESORA = {"Maicao": "C:/Users/Usuario/Downloads/radar_resumen_Maicao (6).xlsx",
             "Oicata": "C:/Users/Usuario/Downloads/radar_resumen_Oicat_.xlsx",
             "Paraguachon": "C:/Users/Usuario/Downloads/radar_resumen_Paraguach_n.xlsx"}
GA = "presencia_grupos_armados"
CORTES_ANTES = (0.766, 0.9233)
CORTES_DESPUES = (cfg.CORTE_BAJO_MEDIO_RADAR, cfg.CORTE_MEDIO_ALTO_RADAR)

# (clave, Dimensión, Indicador) tal como aparecen en los Excel de la profesora.
FILAS = [(k, d, n) for d, ks in [
    ("A — Derechos e Institucionalidad Formal", [
        ("violacion_derechos_humanos", "Violación Derechos Humanos"),
        ("irregularidad_contractual", "Irregularidad Contractual"),
        ("conflicto_territorial", "Conflicto Territorial")]),
    ("B — Violencia y Actores Armados", [
        ("presencia_grupos_armados", "Presencia Grupos Armados"),
        ("amenaza_lideres", "Amenaza a Líderes"),
        ("amenaza_intimidacion", "Amenaza e Intimidación"),
        ("conflictos_socioambientales", "Conflictos Socioambientales")]),
    ("C — Debilidad Institucional / Económica", [
        ("debilidad_institucional", "Debilidad Institucional"),
        ("conflicto_activo", "Conflicto Activo"),
        ("incentivos_economicos_inequitativos", "Incentivos Económicos Inequitativos")]),
    ("D — Afectación Territorial y Poblacional", [
        ("desplazamiento_forzado", "Desplazamiento Forzado"),
        ("reasentamiento", "Reasentamiento"),
        ("poblacion_afectada", "Población Afectada"),
        ("zonas_proteccion_alimentaria", "Zonas Protección Alimentaria"),
        ("dano_territorios", "Daño a Territorios"),
        ("exclusion_servicios_derechos", "Exclusión Servicios y Derechos"),
        ("grupos_etnicos_existentes", "Grupos Étnicos Existentes"),
        ("danos_ambientales", "Daños Ambientales"),
        ("derechos_vulnerados", "Derechos Vulnerados"),
        ("resistencia_territorial", "Resistencia Territorial")]),
    ("E — Participación y Movilización Social", [
        ("deficit_participacion_comunitaria", "Déficit Participación Comunitaria"),
        ("exclusion_comunidades", "Exclusión de Comunidades"),
        ("movimientos_sociales", "Movimientos Sociales"),
        ("rechazo_proyecto", "Rechazo al Proyecto"),
        ("protesta_social", "Protesta Social"),
        ("exclusion_beneficios_economicos", "Exclusión Beneficios Económicos")]),
] for k, n in ks]
assert [k for k, _, _ in FILAS] == [c for b in T.CalculadorRadar.BLOQUES_PCA.values() for c in b]
assert sorted(k for k, _, _ in FILAS) == sorted(T.CalculadorRadar.COLUMNAS_BINARIAS)


def clasificar(v, cb, ca):
    return "Bajo" if v < cb else ("Medio" if v < ca else "Alto")


def a_100(v: float) -> int:
    return int(math.floor(v * 100 + 0.5))


def resumen(g: pd.DataFrame) -> pd.DataFrame:
    """MAX por indicador y URL del articulo que lo fija (vacia si el MAX es 0)."""
    filas = []
    for k, dim, nom in FILAS:
        s = g[k].astype(float)
        v = float(s.max())
        filas.append({"clave": k, "Dimensión": dim, "Indicador": nom, "max": v,
                      "Score (0-100)": a_100(v), "URL artículo top": s.idxmax() if v > 0 else None})
    return pd.DataFrame(filas)


def escribir(ruta, r: pd.DataFrame, lugar, n, cortes, version):
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Dimensión", "Indicador", "Score (0-100)", "URL artículo top"])
    for _, x in r.iterrows():
        ws.append([x["Dimensión"], x["Indicador"], int(x["Score (0-100)"]), x["URL artículo top"]])
    radar = float(r["max"].mean())
    wr = wb.create_sheet("Radar")
    for fila in (["Lugar", lugar], ["Artículos", n], ["Radar (media de los 26 MAX)", round(radar, 4)],
                 ["Clase", clasificar(radar, *cortes)], ["Corte Bajo/Medio", cortes[0]],
                 ["Corte Medio/Alto", cortes[1]], ["Presencia Grupos Armados", version]):
        wr.append(fila)
    wb.save(ruta)
    return radar


def main():
    p = pd.read_pickle(PROCESADO)
    ul = pd.read_csv(URL_LUGARES)
    textos = p["texto"].fillna("").astype(str).tolist()

    vig = H.HIPOTESIS[GA]["vig"]
    assert f'"{GA}": "{vig}"' in inspect.getsource(T.PipelineTransformers.__init__)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(T._ruta_modelo_local("MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"))
    g = T.compuerta_grupos_armados(T.premisa_visible(textos, tok, vig))
    g_exp = pd.read_pickle("experimentos/resultados/juicio_5ind/premisas_visibles.pkl").loc[p["url"]]
    g_exp = np.asarray(H.compuerta(g_exp.values, GA))
    print(f"Compuerta src en el corpus de lugares: abre {g.mean():.1%}; distinta de la de F3/F5 "
          f"(truncacion del experimento) en {int((g != g_exp).sum())} de {len(g)} articulos")

    antes = p.set_index("url")
    despues = antes.copy()
    despues[GA] = despues[GA].values * g

    os.makedirs(DIR, exist_ok=True)
    comp = []
    print(f"{'lugar':12} {'n':>5} {'radar antes':>12} {'clase':>6} {'radar despues':>14} {'clase':>6}  grupos armados")
    for lugar in ("Maicao", "Oicata", "Paraguachon"):
        urls = ul.loc[ul["lugar"] == lugar, "url"]
        ra, rd = resumen(antes.loc[urls]), resumen(despues.loc[urls])
        va = escribir(os.path.join(DIR, f"radar_resumen_{lugar}_antes_V01.xlsx"), ra, lugar, len(urls),
                      CORTES_ANTES, "V01: hipótesis vigente (score NLI corregido)")
        vd = escribir(os.path.join(DIR, f"radar_resumen_{lugar}_despues_V08.xlsx"), rd, lugar, len(urls),
                      CORTES_DESPUES, "V08: hipótesis vigente × compuerta léxica")
        ia = ra.set_index("clave").loc[GA]
        idd = rd.set_index("clave").loc[GA]
        print(f"{lugar:12} {len(urls):5d} {va:12.4f} {clasificar(va, *CORTES_ANTES):>6} {vd:14.4f} "
              f"{clasificar(vd, *CORTES_DESPUES):>6}  {ia['Score (0-100)']} -> {idd['Score (0-100)']}")
        c = ra[["clave", "Indicador", "Score (0-100)", "URL artículo top"]].rename(
            columns={"Score (0-100)": "score_antes", "URL artículo top": "url_antes"})
        c["score_despues"] = rd["Score (0-100)"].values
        c["url_despues"] = rd["URL artículo top"].values
        c.insert(0, "lugar", lugar)
        if os.path.exists(PROFESORA[lugar]):
            x = pd.read_excel(PROFESORA[lugar])
            assert list(x["Indicador"]) == [n for _, _, n in FILAS]
            c["score_profesora"] = x["Score (0-100)"].values
            c["url_profesora"] = x["URL artículo top"].values
        comp.append(c)
    comp = pd.concat(comp, ignore_index=True)
    comp.to_csv(os.path.join(DIR, "comparacion_antes_despues.csv"), index=False)

    cambia = comp[(comp.score_antes != comp.score_despues) | (comp.url_antes.fillna("") != comp.url_despues.fillna(""))]
    print(f"Celdas que cambian antes -> despues: {len(cambia)} (indicadores: {sorted(set(cambia.clave))})")
    if "score_profesora" in comp:
        dif = comp[comp.score_antes != comp.score_profesora]
        print(f"'Antes' vs Excel de la profesora: score distinto en {len(dif)} de {len(comp)} celdas "
              f"({dif.groupby('lugar').size().to_dict()}); en todas, el nuestro es mayor: "
              f"{bool((dif.score_antes > dif.score_profesora).all())}")
    print(f"-> {DIR}/")


if __name__ == "__main__":
    main()
