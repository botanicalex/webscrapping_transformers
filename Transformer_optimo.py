import os
import glob
import argparse
from typing import Dict, List, Tuple
import re
import pandas as pd
import numpy as np
import torch
from transformers import pipeline as hf_pipeline
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForTokenClassification
import scrappers as sc
import config_pipeline as cfg
from radar import CalculadorRadar


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
PIPELINE_DEVICE = 0 if DEVICE.type == "cuda" else -1

class CargadorCorpus:
    def __init__(self, ruta_pkl: str = cfg.RUTA_CORPUS_PKL):
        self.ruta_pkl = ruta_pkl

    def cargar(self) -> pd.DataFrame:
        archivos = sorted(glob.glob(os.path.join(self.ruta_pkl, "df_corpus_*.pkl")))
        if not archivos:
            raise FileNotFoundError(f"No se encontraron archivos df_corpus_*.pkl en '{self.ruta_pkl}'")
        partes = []
        for ruta in archivos:
            try:
                partes.append(pd.read_pickle(ruta))
            except Exception:
                pass
        if not partes:
            raise ValueError("No se pudo cargar ningún pkl válido")
        df = pd.concat(partes, ignore_index=True)
        columnas_requeridas = ['periodico', 'titulo', 'fecha', 'texto', 'url', 'departamento']
        faltantes = [c for c in columnas_requeridas if c not in df.columns]
        if faltantes:
            raise ValueError(f"Faltan columnas requeridas: {faltantes}")
        df = df.drop_duplicates(subset=['url'])
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        sin_contenido = df['texto'].isna() | (df['texto'].astype(str).str.strip() == '')
        df = df[~sin_contenido].reset_index(drop=True)
        return df

class PipelineTransformers:
    def __init__(self):
        self.modelo_nli_nombre = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
        self.modelo_sent_nombre = "finiteautomata/beto-sentiment-analysis"
        self.modelo_ner_nombre = "dccuchile/bert-base-spanish-wwm-cased-finetuned-ner"
        self.device = DEVICE
        self.cuda_disponible = self.device.type == "cuda"
        print(f"CUDA disponible: {self.cuda_disponible} | dispositivo: {self.device}")

        self.tokenizer_nli = AutoTokenizer.from_pretrained(self.modelo_nli_nombre)
        self.modelo_nli = AutoModelForSequenceClassification.from_pretrained(self.modelo_nli_nombre).to(self.device)
        self.modelo_nli.eval()
        self.label_ent, self.label_neu, self.label_con = self._resolver_labels_nli()
        self.zero_shot = hf_pipeline(
            "zero-shot-classification",
            model=self.modelo_nli,
            tokenizer=self.tokenizer_nli,
            device=PIPELINE_DEVICE
        )

        self.tokenizer_sent = AutoTokenizer.from_pretrained(self.modelo_sent_nombre)
        self.modelo_sent = AutoModelForSequenceClassification.from_pretrained(self.modelo_sent_nombre).to(self.device)
        self.modelo_sent.eval()
        self.sentiment = hf_pipeline(
            "sentiment-analysis",
            model=self.modelo_sent,
            tokenizer=self.tokenizer_sent,
            device=PIPELINE_DEVICE
        )

        self.tokenizer_ner = AutoTokenizer.from_pretrained(self.modelo_ner_nombre)
        self.modelo_ner = AutoModelForTokenClassification.from_pretrained(self.modelo_ner_nombre).to(self.device)
        self.modelo_ner.eval()
        self.ner = hf_pipeline(
            "ner",
            model=self.modelo_ner,
            tokenizer=self.tokenizer_ner,
            aggregation_strategy="simple",
            device=PIPELINE_DEVICE
        )

        self.temas = {
            "participacion_comunitaria": "déficit de participación comunitaria, ausencia de participación ciudadana, exclusión de veedurías ciudadanas, debilidad del control social",
            "incentivos_economicos": "concentración desigual de beneficios, distribución inequitativa de incentivos económicos, captura de rentas, exclusión económica de comunidades locales",
            "fortalecimiento_institucional": "debilidad institucional grave y documentada: entidades con déficit de recursos verificado, incapacidad demostrada para cumplir su mandato",
            "impactos_ambientales": "daño ambiental concreto y medible con consecuencias directas para comunidades",
            "conflictos_socioambientales": "conflicto socioambiental activo y en curso entre comunidades y actores extractivos o estatales"
        }

        self.eventos = {
            "desplazamiento_forzado": "Este texto reporta que OCURRIÓ un desplazamiento forzado, expulsión o éxodo de comunidades",
            "reasentamiento": "Este texto reporta que SE REALIZÓ un reasentamiento, reubicación o traslado planificado de población",
            "protesta_social": "Este texto reporta que OCURRIÓ una protesta social, manifestación, bloqueo, movilización o paro",
            "amenaza_intimidacion": "Este texto reporta que OCURRIERON amenazas, intimidación, hostigamiento o violencia contra personas",
            "consulta_previa": "Este texto reporta ESPECÍFICAMENTE la realización o la omisión deliberada de una consulta previa libre e informada",
            "audiencia_publica": "Este texto reporta que SE REALIZÓ o SE OMITIÓ una audiencia pública, socialización o reunión informativa oficial",
            "taller_participativo": "Este texto reporta que SE REALIZÓ o SE OMITIÓ un taller participativo, taller comunitario o sesión de trabajo con comunidades",
            "conflicto_territorial": "Este texto reporta un CONFLICTO TERRITORIAL ACTIVO Y ESPECÍFICO con partes identificadas"
        }

        self.posturas = {
            "nivel_acuerdo_proyecto": "Este texto expresa explícitamente apoyo o rechazo a un proyecto o iniciativa específico",
            "demanda_derechos": "Este texto expresa demandas urgentes, exigencias o reclamos intensos de derechos vulnerados",
            "denuncia_violacion": "Este texto reporta una denuncia formal o explícita de violaciones de derechos humanos",
            "propuesta_alternativa": "Este texto propone alternativas porque los canales de participación existentes son insuficientes",
            "llamado_dialogo": "Este texto hace un llamado al diálogo, negociación o búsqueda de acuerdos",
            "defensa_territorio": "Este texto expresa resistencia activa o reivindicación del territorio frente a una amenaza",
            "exigencia_participacion": "Este texto exige participación o inclusión porque las comunidades han sido excluidas"
        }

        self.indicadores = {
            "equidad_inclusion": "Este texto describe brechas concretas de exclusión en acceso a servicios, derechos u oportunidades",
            "grupos_etnicos": "Este texto menciona exposición diferencial de pueblos indígenas o comunidades afrodescendientes",
            "movimientos_sociales": "Este texto reporta movilización organizada y activa de movimientos sociales",
            "grupos_poblacionales_afectados": "Este texto identifica poblaciones concretas afectadas de forma diferenciada y severa",
            "participacion_economica_local": "Este texto reporta exclusión explícita de comunidades locales de beneficios económicos",
            "transparencia_contractual": "Este texto reporta irregularidades concretas y verificables en procesos contractuales",
            "zonas_proteccion_alimentaria": "Este texto menciona áreas agrícolas o seguridad alimentaria",
            "respeto_territorios": "Este texto reporta pérdida o daño concreto a territorios o medios de vida comunitarios",
            "presencia_grupos_armados": "Este texto menciona grupos armados ilegales o violencia armada",
            "desaparicion_lideres": "Este texto menciona amenazas o violencia contra líderes sociales"
        }

        self.ref_entidades = {
            "grupos_etnicos_entidades": {"indígena", "indigena", "afrodescendiente", "afrocolombiano", "raizal", "palenquero", "resguardo", "cabildo"},
            "grupos_armados_entidades": {"eln", "farc", "disidencias", "epl", "auc", "agc", "clan del golfo", "guerrilla", "paramilitar"},
            "organizaciones_entidades": {"onic", "cric", "opiac", "anuc", "fecode", "sindicato", "colectivo", "organización", "organizacion"},
            "lideres_entidades": {"líder social", "lider social", "defensor de derechos humanos", "activista"},
            "instituciones_entidades": {"alcaldía", "alcaldia", "gobernación", "gobernacion", "ministerio", "anla", "defensoría", "defensoria", "contraloría", "contraloria"},
            "actores_economicos_entidades": {"empresa", "minera", "petrolera", "contratista", "consorcio", "multinacional"}
        }

    def _resolver_labels_nli(self) -> Tuple[int, int, int]:
        id2label = self.modelo_nli.config.id2label
        ent = neu = con = None
        for idx, label in id2label.items():
            l = str(label).lower()
            if "entail" in l:
                ent = int(idx)
            elif "neutral" in l:
                neu = int(idx)
            elif "contrad" in l:
                con = int(idx)
        if ent is None or neu is None or con is None:
            ent, neu, con = 0, 1, 2
        return ent, neu, con

    def _nli_probs(self, premisa: str, hipotesis: str) -> Dict[str, float]:
        inputs = self.tokenizer_nli(
            premisa, hipotesis,
            truncation=True, max_length=512, padding=True, return_tensors="pt"
        ).to(self.device)
        with torch.no_grad():
            logits = self.modelo_nli(**inputs).logits
            probs = torch.softmax(logits, dim=1)[0]
        return {
            "entailment": float(probs[self.label_ent].item()),
            "neutral": float(probs[self.label_neu].item()),
            "contradiction": float(probs[self.label_con].item())
        }

    def _clasificar_temas(self, texto: str) -> Dict[str, float]:
        labels = list(self.temas.values())
        claves = list(self.temas.keys())
        with torch.no_grad():
            resultado = self.zero_shot(texto[:3000], candidate_labels=labels, multi_label=False)
        score_por_label = {l: s for l, s in zip(resultado["labels"], resultado["scores"])}
        return {k: float(score_por_label.get(v, 0.0)) for k, v in zip(claves, labels)}

    def _detectar_por_nli(self, texto: str, diccionario: Dict[str, str]) -> Dict[str, float]:
        out = {}
        for k, h in diccionario.items():
            out[k] = self._nli_probs(texto, h)["entailment"]
        return out

    def _analizar_sentimiento(self, texto: str) -> Tuple[str, float]:
        with torch.no_grad():
            r = self.sentiment(texto[:512])[0]
        label = r["label"]
        score = float(r["score"])
        if label == "POS":
            s = "positivo"
        elif label == "NEG":
            s = "negativo"
        else:
            s = "neutral"
        return s, score

    def _entidades_booleanas(self, texto: str) -> Dict[str, bool]:
        texto_low = texto.lower()
        res = {k: False for k in self.ref_entidades.keys()}
        for cat, refs in self.ref_entidades.items():
            if any(ref in texto_low for ref in refs):
                res[cat] = True
        try:
            with torch.no_grad():
                ents = self.ner(texto[:3000])
            for e in ents:
                w = str(e.get("word", "")).lower()
                for cat, refs in self.ref_entidades.items():
                    if any(ref in w for ref in refs):
                        res[cat] = True
        except Exception:
            pass
        return res

    def procesar(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in list(self.temas.keys()) + list(self.eventos.keys()) + list(self.posturas.keys()) + list(self.indicadores.keys()):
            if col not in df.columns:
                df[col] = 0.0
        if "sentimiento" not in df.columns:
            df["sentimiento"] = "neutral"
        if "sentimiento_confianza" not in df.columns:
            df["sentimiento_confianza"] = 0.0
        for c in self.ref_entidades.keys():
            if c not in df.columns:
                df[c] = False

        for i, texto in enumerate(df["texto"].fillna("").astype(str).tolist()):
            if not texto.strip():
                continue
            temas_scores = self._clasificar_temas(texto)
            eventos_scores = self._detectar_por_nli(texto, self.eventos)
            posturas_scores = self._detectar_por_nli(texto, self.posturas)
            indicadores_scores = self._detectar_por_nli(texto, self.indicadores)
            sent, sent_conf = self._analizar_sentimiento(texto)
            ents = self._entidades_booleanas(texto)

            for k, v in temas_scores.items():
                df.at[i, k] = v
            for k, v in eventos_scores.items():
                df.at[i, k] = v
            for k, v in posturas_scores.items():
                df.at[i, k] = v
            for k, v in indicadores_scores.items():
                df.at[i, k] = v
            for k, v in ents.items():
                df.at[i, k] = bool(v)
            df.at[i, "sentimiento"] = sent
            df.at[i, "sentimiento_confianza"] = sent_conf

            if (i + 1) % 10 == 0 or (i + 1) == len(df):
                print(f"Transformers procesados: {i+1}/{len(df)}")

        self._crear_scores_dimension(df)
        return df

    def _crear_scores_dimension(self, df: pd.DataFrame) -> None:
        dim1 = ["transparencia_contractual","consulta_previa","exigencia_participacion","propuesta_alternativa","participacion_comunitaria","audiencia_publica","taller_participativo","llamado_dialogo"]
        dim2 = ["fortalecimiento_institucional"]
        dim3 = ["incentivos_economicos","protesta_social","nivel_acuerdo_proyecto","equidad_inclusion","movimientos_sociales","grupos_poblacionales_afectados","participacion_economica_local"]
        dim4 = ["impactos_ambientales","conflictos_socioambientales","reasentamiento","conflicto_territorial","defensa_territorio","respeto_territorios"]
        dim5 = ["desplazamiento_forzado","amenaza_intimidacion","denuncia_violacion","demanda_derechos","presencia_grupos_armados","desaparicion_lideres"]
        for c in dim1 + dim2 + dim3 + dim4 + dim5:
            if c not in df.columns:
                df[c] = 0.0
        df["score_dim1_gobernanza"] = df[dim1].astype(float).mean(axis=1).round(4)
        df["score_dim2_capacidad_institucional"] = df[dim2].astype(float).mean(axis=1).round(4)
        df["score_dim3_vulneracion_socioeconomica"] = df[dim3].astype(float).mean(axis=1).round(4)
        df["score_dim4_vulnerabilidad_territorial"] = df[dim4].astype(float).mean(axis=1).round(4)
        df["score_dim5_derechos_humanos_conflicto"] = df[dim5].astype(float).mean(axis=1).round(4)

def correr_scraping(fecha_desde: str, fecha_hasta: str, salida: str, temas: List[str] = None):
    os.makedirs(salida, exist_ok=True)
    for i, grupo in enumerate(sc.GRUPOS_DEPARTAMENTOS, 1):
        print(f"\nGrupo {i}/{len(sc.GRUPOS_DEPARTAMENTOS)}: {grupo}")
        sc.scrape_multiples_departamentos(
            departamentos=grupo,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            min_menciones=None,
            directorio_salida=salida,
            temas=temas
        )

class ValidadorPrecondiciones:
    COLUMNAS_CORPUS = ['periodico', 'titulo', 'fecha', 'texto', 'url', 'departamento']

    @staticmethod
    def etapa_corpus(ruta_pkl: str) -> None:
        archivos = sorted(glob.glob(os.path.join(ruta_pkl, "df_corpus_*.pkl")))
        if not archivos:
            raise FileNotFoundError(
                f"Precondición corpus: no se encontraron archivos df_corpus_*.pkl en '{ruta_pkl}'"
            )
        faltantes_por_archivo: Dict[str, List[str]] = {}
        for ruta in archivos:
            try:
                df = pd.read_pickle(ruta)
            except Exception as e:
                raise RuntimeError(f"Precondición corpus: no se pudo leer '{ruta}': {e}")
            faltantes = [c for c in ValidadorPrecondiciones.COLUMNAS_CORPUS if c not in df.columns]
            if faltantes:
                faltantes_por_archivo[os.path.basename(ruta)] = faltantes
        if faltantes_por_archivo:
            detalle = "; ".join(f"{f}: {cols}" for f, cols in faltantes_por_archivo.items())
            raise ValueError(f"Precondición corpus: columnas requeridas faltantes — {detalle}")

    @staticmethod
    def etapa_salida_no_vacia(ruta_pkl: str, nombre_etapa: str) -> None:
        if not os.path.isfile(ruta_pkl):
            raise FileNotFoundError(
                f"Precondición {nombre_etapa}: archivo de salida no existe '{ruta_pkl}'"
            )
        if os.path.getsize(ruta_pkl) == 0:
            raise ValueError(
                f"Precondición {nombre_etapa}: archivo de salida vacío '{ruta_pkl}'"
            )
        try:
            df = pd.read_pickle(ruta_pkl)
        except Exception as e:
            raise RuntimeError(
                f"Precondición {nombre_etapa}: no se pudo deserializar '{ruta_pkl}': {e}"
            )
        if df.empty:
            raise ValueError(
                f"Precondición {nombre_etapa}: DataFrame sin filas en '{ruta_pkl}'"
            )


def exportar_indicadores_transformers_por_departamento(df_procesado: pd.DataFrame, salida: str) -> str:
    df = df_procesado.copy()
    if 'departamento' not in df.columns or not df['departamento'].notna().any():
        df['departamento'] = df['periodico'].map(CalculadorRadar.MAPEO_PERIODICO_DEPARTAMENTO)
    df = df.dropna(subset=['departamento'])
    cols = [c for c in CalculadorRadar.COLUMNAS_BINARIAS if c in df.columns]
    for c in cols:
        if df[c].dtype == bool:
            df[c] = df[c].astype(float)
        else:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    df_indicadores = df.groupby('departamento')[cols].mean().reset_index()
    ruta_indicadores_csv = os.path.join(salida, "indicadores_transformers_departamento.csv")
    df_indicadores.to_csv(ruta_indicadores_csv, index=False)
    return ruta_indicadores_csv


def exportar_radar_base_por_departamento(df_procesado: pd.DataFrame, salida: str) -> Tuple[str, str]:
    df = df_procesado.copy()
    if 'departamento' not in df.columns or not df['departamento'].notna().any():
        df['departamento'] = df['periodico'].map(CalculadorRadar.MAPEO_PERIODICO_DEPARTAMENTO)
    df = df.dropna(subset=['departamento'])
    df['departamento'] = df['departamento'].astype(str).str.strip()
    df_base = df.groupby('departamento').size().reset_index(name='n_articulos')
    df_base = df_base.sort_values('departamento').reset_index(drop=True)
    for col in ['bloque_A', 'bloque_B', 'bloque_C', 'bloque_D', 'bloque_E', 'corrupcion_score', 'vulneracion_score', 'radar_propio']:
        df_base[col] = np.nan
    df_base['categoria_riesgo'] = "None"
    columnas = ['departamento', 'n_articulos', 'bloque_A', 'bloque_B', 'bloque_C', 'bloque_D', 'bloque_E', 'corrupcion_score', 'vulneracion_score', 'radar_propio', 'categoria_riesgo']
    df_base = df_base[columnas]
    ruta_radar_pkl = os.path.join(salida, "radar_departamentos.pkl")
    ruta_radar_csv = os.path.join(salida, "radar_departamentos.csv")
    df_base.to_pickle(ruta_radar_pkl)
    df_base.to_csv(ruta_radar_csv, index=False)
    return ruta_radar_pkl, ruta_radar_csv


def run_pipeline_transformers(ruta_pkl: str, salida: str) -> Tuple[str, str]:
    os.makedirs(salida, exist_ok=True)

    ValidadorPrecondiciones.etapa_corpus(ruta_pkl)

    df_corpus = CargadorCorpus(ruta_pkl).cargar()
    print(f"Corpus cargado: {len(df_corpus)} artículos")

    pipeline = PipelineTransformers()
    df_procesado = pipeline.procesar(df_corpus)
    ruta_procesado_pkl = os.path.join(salida, "df_procesado.pkl")
    ruta_procesado_csv = os.path.join(salida, "df_procesado.csv")
    df_procesado.to_pickle(ruta_procesado_pkl)
    df_procesado.to_csv(ruta_procesado_csv, index=False)

    ValidadorPrecondiciones.etapa_salida_no_vacia(ruta_procesado_pkl, "NLP")

    ruta_indicadores_csv = exportar_indicadores_transformers_por_departamento(df_procesado, salida)
    ruta_radar_pkl, ruta_radar_csv = exportar_radar_base_por_departamento(df_procesado, salida)

    ValidadorPrecondiciones.etapa_salida_no_vacia(ruta_radar_pkl, "radar_base")

    print(f"\nGuardado:\n- {ruta_procesado_pkl}\n- {ruta_procesado_csv}\n- {ruta_indicadores_csv}\n- {ruta_radar_pkl}\n- {ruta_radar_csv}")

    return ruta_procesado_pkl, ruta_radar_pkl

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha-desde", default=sc.FECHA_DESDE)
    parser.add_argument("--fecha-hasta", default=sc.FECHA_HASTA)
    parser.add_argument("--ruta-pkl", default=cfg.RUTA_CORPUS_PKL)
    parser.add_argument("--salida", default=cfg.RUTA_SALIDA_PIPELINE)
    parser.add_argument("--skip-scraping", action="store_true")
    args = parser.parse_args()

    if not args.skip_scraping:
        correr_scraping(args.fecha_desde, args.fecha_hasta, args.ruta_pkl, temas=None)

    run_pipeline_transformers(args.ruta_pkl, args.salida)

if __name__ == "__main__":
    main()