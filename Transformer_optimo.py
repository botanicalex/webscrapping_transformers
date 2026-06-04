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

HF_HUB_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")

def _ruta_modelo_local(nombre_modelo: str) -> str:
    """Devuelve la ruta del snapshot local si existe; si no, retorna el nombre original."""
    carpeta = "models--" + nombre_modelo.replace("/", "--")
    refs_main = os.path.join(HF_HUB_CACHE, carpeta, "refs", "main")
    if os.path.isfile(refs_main):
        with open(refs_main) as f:
            commit = f.read().strip()
        ruta = os.path.join(HF_HUB_CACHE, carpeta, "snapshots", commit)
        if os.path.isdir(ruta):
            return ruta
    return nombre_modelo


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

        nli_path  = _ruta_modelo_local(self.modelo_nli_nombre)
        sent_path = _ruta_modelo_local(self.modelo_sent_nombre)
        ner_path  = _ruta_modelo_local(self.modelo_ner_nombre)
        print(f"NLI: {nli_path}\nSent: {sent_path}\nNER: {ner_path}")

        self.tokenizer_nli = AutoTokenizer.from_pretrained(nli_path)
        self.modelo_nli = AutoModelForSequenceClassification.from_pretrained(nli_path).to(self.device)
        self.modelo_nli.eval()
        self.label_ent, self.label_neu, self.label_con = self._resolver_labels_nli()
        self.zero_shot = hf_pipeline(
            "zero-shot-classification",
            model=self.modelo_nli,
            tokenizer=self.tokenizer_nli,
            device=PIPELINE_DEVICE
        )

        self.tokenizer_sent = AutoTokenizer.from_pretrained(sent_path)
        self.modelo_sent = AutoModelForSequenceClassification.from_pretrained(sent_path).to(self.device)
        self.modelo_sent.eval()
        self.sentiment = hf_pipeline(
            "sentiment-analysis",
            model=self.modelo_sent,
            tokenizer=self.tokenizer_sent,
            device=PIPELINE_DEVICE
        )

        self.tokenizer_ner = AutoTokenizer.from_pretrained(ner_path)
        self.modelo_ner = AutoModelForTokenClassification.from_pretrained(ner_path).to(self.device)
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
            "rechazo_proyecto": "Este texto expresa rechazo, oposicion o desacuerdo explicito frente a un proyecto o iniciativa especifica, por parte de actores sociales, comunitarios o institucionales.",
            "deficit_derechos": "Este texto expresa reclamos urgentes o exigencias de derechos que estan siendo vulnerados o que no han sido garantizados a comunidades o grupos afectados.",
            "denuncia_violacion": "Este texto reporta una denuncia formal o explicita de violaciones de derechos humanos, abusos o incumplimientos graves de acuerdos, presentada por comunidades, organizaciones o defensores identificados.",
            "deficit_participacion_efectiva": "Este texto propone alternativas o soluciones diferentes porque los canales institucionales de participacion han fallado o son insuficientes para atender las necesidades de las comunidades.",
            "ruptura_dialogo": "Este texto hace un llamado urgente al dialogo o la negociacion porque existe un conflicto activo, una ruptura de acuerdos o una situacion de exclusion que las instituciones no han resuelto.",
            "reivindicacion_territorial": "Este texto expresa resistencia activa, conflictividad o reivindicacion del territorio, los recursos naturales o el medio ambiente frente a una amenaza concreta.",
            "exclusion_participacion": "Este texto exige participacion, consulta o inclusion porque las comunidades han sido excluidas de decisiones que las afectan directamente."
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

    # ------------------------------------------------------------------
    # Métodos batch (procesan N textos de una vez, ~30x más rápido)
    # ------------------------------------------------------------------

    def _nli_batch(self, textos: List[str], hipotesis: str, batch_size: int = 32) -> List[float]:
        """Calcula P(entailment) de N textos contra UNA hipótesis en chunks."""
        scores: List[float] = []
        for start in range(0, len(textos), batch_size):
            chunk = textos[start: start + batch_size]
            inputs = self.tokenizer_nli(
                chunk,
                [hipotesis] * len(chunk),
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="pt",
            ).to(self.device)
            with torch.no_grad():
                probs = torch.softmax(self.modelo_nli(**inputs).logits, dim=1)
            scores.extend(probs[:, self.label_ent].cpu().tolist())
        return scores

    def _sentimiento_batch(self, textos: List[str], batch_size: int = 32) -> Tuple[List[str], List[float]]:
        """Análisis de sentimiento en batch sobre todos los textos."""
        resultados = self.sentiment(
            [t[:512] for t in textos],
            batch_size=batch_size,
            truncation=True,
        )
        sentimientos: List[str] = []
        confianzas: List[float] = []
        for r in resultados:
            label = r["label"]
            if label == "POS":
                sentimientos.append("positivo")
            elif label == "NEG":
                sentimientos.append("negativo")
            else:
                sentimientos.append("neutral")
            confianzas.append(float(r["score"]))
        return sentimientos, confianzas

    def _ner_batch(self, textos: List[str], batch_size: int = 32) -> Dict[str, List[bool]]:
        """NER + keyword matching en batch. Devuelve dict cat -> lista de N bools."""
        N = len(textos)
        res: Dict[str, List[bool]] = {k: [False] * N for k in self.ref_entidades}

        # Keyword matching vectorizado (sin GPU, muy rápido)
        for idx, t in enumerate(textos):
            tl = t.lower()
            for cat, refs in self.ref_entidades.items():
                if any(ref in tl for ref in refs):
                    res[cat][idx] = True

        # NER model en batch
        try:
            ner_resultados = self.ner(
                [t[:3000] for t in textos],
                batch_size=batch_size,
                truncation=True,
            )
            for idx, ents in enumerate(ner_resultados):
                for e in ents:
                    w = str(e.get("word", "")).lower()
                    for cat, refs in self.ref_entidades.items():
                        if any(ref in w for ref in refs):
                            res[cat][idx] = True
        except Exception:
            pass

        return res

    # ------------------------------------------------------------------
    # procesar() — versión batch (~30x más rápida que el loop original)
    # ------------------------------------------------------------------

    def procesar(self, df: pd.DataFrame, batch_size: int = 32) -> pd.DataFrame:
        df = df.copy()
        textos = df["texto"].fillna("").astype(str).tolist()
        N = len(textos)

        # Inicializar columnas
        for col in (list(self.temas.keys()) + list(self.eventos.keys())
                    + list(self.posturas.keys()) + list(self.indicadores.keys())):
            if col not in df.columns:
                df[col] = 0.0
        if "sentimiento" not in df.columns:
            df["sentimiento"] = "neutral"
        if "sentimiento_confianza" not in df.columns:
            df["sentimiento_confianza"] = 0.0
        for c in self.ref_entidades.keys():
            if c not in df.columns:
                df[c] = False

        # 1. Sentimiento en batch
        sents, confs = self._sentimiento_batch(textos, batch_size)
        df["sentimiento"] = sents
        df["sentimiento_confianza"] = confs
        print(f"[batch] Sentimiento completado ({N} articulos)")

        # 2. NER en batch
        ner_res = self._ner_batch(textos, batch_size)
        for cat, vals in ner_res.items():
            df[cat] = vals
        print(f"[batch] NER completado")

        # 3. Zero-shot temas en batch (pipeline HF acepta lista directamente)
        labels = list(self.temas.values())
        claves_temas = list(self.temas.keys())
        zs_results = self.zero_shot(
            [t[:3000] for t in textos],
            candidate_labels=labels,
            multi_label=False,
            batch_size=batch_size,
        )
        for clave in claves_temas:
            df[clave] = 0.0
        if isinstance(zs_results, dict):
            zs_results = [zs_results]
        for idx, r in enumerate(zs_results):
            score_map = dict(zip(r["labels"], r["scores"]))
            for k, label in zip(claves_temas, labels):
                df.at[idx, k] = float(score_map.get(label, 0.0))
        print(f"[batch] Zero-shot temas completado")

        # 4. NLI en batch: eventos + posturas + indicadores (una hipotesis a la vez)
        todos = {**self.eventos, **self.posturas, **self.indicadores}
        n_hip = len(todos)
        for i_hip, (clave, hipotesis) in enumerate(todos.items(), 1):
            scores = self._nli_batch(textos, hipotesis, batch_size)
            df[clave] = scores
            if i_hip % 5 == 0 or i_hip == n_hip:
                print(f"[batch] NLI hipotesis {i_hip}/{n_hip} completada")

        self._crear_scores_dimension(df)
        print(f"[batch] Procesamiento completado: {N} articulos")
        return df

    def _crear_scores_dimension(self, df: pd.DataFrame) -> None:
        dim1 = ["transparencia_contractual","consulta_previa","exclusion_participacion","deficit_participacion_efectiva","participacion_comunitaria","audiencia_publica","taller_participativo","ruptura_dialogo"]
        dim2 = ["fortalecimiento_institucional"]
        dim3 = ["incentivos_economicos","protesta_social","rechazo_proyecto","equidad_inclusion","movimientos_sociales","grupos_poblacionales_afectados","participacion_economica_local"]
        dim4 = ["impactos_ambientales","conflictos_socioambientales","reasentamiento","conflicto_territorial","reivindicacion_territorial","respeto_territorios"]
        dim5 = ["desplazamiento_forzado","amenaza_intimidacion","denuncia_violacion","deficit_derechos","presencia_grupos_armados","desaparicion_lideres"]
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