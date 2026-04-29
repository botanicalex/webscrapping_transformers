import os
import glob
import argparse
from typing import Dict, List, Tuple
import re
import pandas as pd
import numpy as np
import torch
from transformers import pipeline as hf_pipeline
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import scrappers as sc
import config_pipeline as cfg

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
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer_nli = AutoTokenizer.from_pretrained(self.modelo_nli_nombre)
        self.modelo_nli = AutoModelForSequenceClassification.from_pretrained(self.modelo_nli_nombre).to(self.device)
        self.modelo_nli.eval()
        self.label_ent, self.label_neu, self.label_con = self._resolver_labels_nli()
        self.zero_shot = hf_pipeline("zero-shot-classification", model=self.modelo_nli_nombre, device=0 if torch.cuda.is_available() else -1)
        self.sentiment = hf_pipeline("sentiment-analysis", model=self.modelo_sent_nombre, device=0 if torch.cuda.is_available() else -1)
        self.ner = hf_pipeline("ner", model=self.modelo_ner_nombre, aggregation_strategy="simple", device=0 if torch.cuda.is_available() else -1)

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
        resultado = self.zero_shot(texto[:3000], candidate_labels=labels, multi_label=False)
        score_por_label = {l: s for l, s in zip(resultado["labels"], resultado["scores"])}
        return {k: float(score_por_label.get(v, 0.0)) for k, v in zip(claves, labels)}

    def _detectar_por_nli(self, texto: str, diccionario: Dict[str, str]) -> Dict[str, float]:
        out = {}
        for k, h in diccionario.items():
            out[k] = self._nli_probs(texto, h)["entailment"]
        return out

    def _analizar_sentimiento(self, texto: str) -> Tuple[str, float]:
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

class CalculadorRadar:
    MAPEO_PERIODICO_DEPARTAMENTO = {
        'El Colombiano': 'Antioquia', 'El Diario': 'Risaralda', 'BC Noticias': 'Caldas', 'El Quindiano': 'Quindío',
        'El País Cali': 'Valle del Cauca', 'Diario Occidente': 'Valle del Cauca', 'Diario del Sur': 'Nariño',
        'Diario del Cauca': 'Cauca', 'Chocó 7 Días': 'Chocó', 'Llano al Mundo': 'Meta', 'Diario de Casanare': 'Casanare',
        'La Voz del Cinaruco': 'Arauca', 'El Morichal': 'Vichada', 'Mi Putumayo': 'Putumayo', 'El Tiempo': 'Cundinamarca',
        'La República': 'Cundinamarca', 'Portafolio': 'Cundinamarca', 'Publimetro': 'Cundinamarca', 'Las2Orillas': 'Cundinamarca',
        'El Heraldo': 'Atlántico', 'El Universal': 'Bolívar', 'El Pilón': 'Cesar', 'El Meridiano': 'Córdoba',
        'Vanguardia': 'Santander', 'Trochando Sin Fronteras': 'Arauca', 'Enlace Television': 'Santander', 'Corrillos': 'Santander'
    }

    BLOQUES_PCA = {
        'bloque_A': ['denuncia_violacion','transparencia_contractual','conflicto_territorial','actores_economicos_entidades'],
        'bloque_B': ['presencia_grupos_armados','desaparicion_lideres','amenaza_intimidacion','grupos_armados_entidades','conflictos_socioambientales'],
        'bloque_C': ['fortalecimiento_institucional','llamado_dialogo','instituciones_entidades','propuesta_alternativa','incentivos_economicos'],
        'bloque_D': ['desplazamiento_forzado','grupos_etnicos','grupos_poblacionales_afectados','zonas_proteccion_alimentaria','respeto_territorios','equidad_inclusion','grupos_etnicos_entidades'],
        'bloque_E': ['participacion_comunitaria','consulta_previa','audiencia_publica','taller_participativo','exigencia_participacion','movimientos_sociales','organizaciones_entidades','lideres_entidades','nivel_acuerdo_proyecto']
    }

    VARS_INVERTIR = {
        'fortalecimiento_institucional','llamado_dialogo','consulta_previa','audiencia_publica',
        'taller_participativo','participacion_comunitaria','nivel_acuerdo_proyecto','propuesta_alternativa',
        'incentivos_economicos','participacion_economica_local','instituciones_entidades'
    }

    COLUMNAS_BINARIAS = [
        'participacion_comunitaria','incentivos_economicos','fortalecimiento_institucional','impactos_ambientales','conflictos_socioambientales',
        'desplazamiento_forzado','reasentamiento','protesta_social','amenaza_intimidacion','consulta_previa','audiencia_publica','taller_participativo','conflicto_territorial',
        'nivel_acuerdo_proyecto','demanda_derechos','denuncia_violacion','propuesta_alternativa','llamado_dialogo','defensa_territorio','exigencia_participacion',
        'equidad_inclusion','grupos_etnicos','movimientos_sociales','grupos_poblacionales_afectados','participacion_economica_local','transparencia_contractual',
        'zonas_proteccion_alimentaria','respeto_territorios','presencia_grupos_armados','desaparicion_lideres',
        'grupos_etnicos_entidades','grupos_armados_entidades','organizaciones_entidades','lideres_entidades','instituciones_entidades','actores_economicos_entidades'
    ]

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if 'departamento' not in df.columns or not df['departamento'].notna().any():
            df['departamento'] = df['periodico'].map(self.MAPEO_PERIODICO_DEPARTAMENTO)
            df = df.dropna(subset=['departamento'])
        cols = [c for c in self.COLUMNAS_BINARIAS if c in df.columns]
        for c in cols:
            if df[c].dtype == bool:
                df[c] = df[c].astype(float)
            else:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
        df_tasas = df.groupby('departamento')[cols].mean()
        df_tasas['n_articulos'] = df.groupby('departamento').size()
        for c in [c for c in cols if c in self.VARS_INVERTIR]:
            df_tasas[c] = 1 - df_tasas[c]

        df_bloques = pd.DataFrame(index=df_tasas.index)
        n_depts = len(df_tasas)
        for b, variables in self.BLOQUES_PCA.items():
            v = [x for x in variables if x in df_tasas.columns]
            if not v:
                df_bloques[b] = 0.0
                continue
            X = df_tasas[v].values
            if n_depts < len(v):
                scores = X.mean(axis=1)
            else:
                try:
                    Xs = StandardScaler().fit_transform(X)
                    scores = PCA(n_components=1).fit_transform(Xs)[:, 0]
                except Exception:
                    scores = X.mean(axis=1)
            smin, smax = scores.min(), scores.max()
            if smax > smin:
                sn = (scores - smin) / (smax - smin) * 100
            elif n_depts == 1:
                sn = np.clip(scores, 0, 1) * 100
            else:
                sn = np.full_like(scores, 50.0, dtype=float)
            df_bloques[b] = sn

        df_bloques['n_articulos'] = df_tasas['n_articulos']
        df_sub = df_bloques.copy()
        corr_raw = 0.80 * df_sub['bloque_B'] + 0.35 * df_sub['bloque_A'] - 0.15 * df_sub['bloque_C']
        vul_raw = 0.50 * df_sub['bloque_D'] + 0.50 * df_sub['bloque_E']
        df_sub['corrupcion_score'] = self._minmax(corr_raw)
        df_sub['vulneracion_score'] = self._minmax(vul_raw)
        radar_raw = 0.60 * df_sub['corrupcion_score'] + 0.40 * df_sub['vulneracion_score']
        df_sub['radar_propio'] = self._minmax(radar_raw)
        p25 = df_sub['radar_propio'].quantile(0.25)
        p75 = df_sub['radar_propio'].quantile(0.75)
        def cat(x):
            if x <= p25:
                return "bajo"
            if x >= p75:
                return "alto"
            return "medio"
        df_sub['categoria_riesgo'] = df_sub['radar_propio'].apply(cat)
        out = df_sub.reset_index().rename(columns={'index': 'departamento'})
        return out[['departamento','n_articulos','bloque_A','bloque_B','bloque_C','bloque_D','bloque_E','corrupcion_score','vulneracion_score','radar_propio','categoria_riesgo']].sort_values('radar_propio', ascending=False)

    @staticmethod
    def _minmax(s: pd.Series) -> pd.Series:
        smin, smax = s.min(), s.max()
        if smax > smin:
            return (s - smin) / (smax - smin) * 100
        return pd.Series([50.0] * len(s), index=s.index)

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha-desde", default=sc.FECHA_DESDE)
    parser.add_argument("--fecha-hasta", default=sc.FECHA_HASTA)
    parser.add_argument("--ruta-pkl", default=cfg.RUTA_CORPUS_PKL)
    parser.add_argument("--salida", default=cfg.RUTA_SALIDA_PIPELINE)
    parser.add_argument("--skip-scraping", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.salida, exist_ok=True)

    if not args.skip_scraping:
        correr_scraping(args.fecha_desde, args.fecha_hasta, args.ruta_pkl, temas=None)

    df_corpus = CargadorCorpus(args.ruta_pkl).cargar()
    print(f"Corpus cargado: {len(df_corpus)} artículos")

    pipeline = PipelineTransformers()
    df_procesado = pipeline.procesar(df_corpus)
    ruta_procesado_pkl = os.path.join(args.salida, "df_procesado.pkl")
    ruta_procesado_csv = os.path.join(args.salida, "df_procesado.csv")
    df_procesado.to_pickle(ruta_procesado_pkl)
    df_procesado.to_csv(ruta_procesado_csv, index=False)

    radar = CalculadorRadar()
    df_radar = radar.calcular(df_procesado)
    ruta_radar_pkl = os.path.join(args.salida, "radar_departamentos.pkl")
    ruta_radar_csv = os.path.join(args.salida, "radar_departamentos.csv")
    df_radar.to_pickle(ruta_radar_pkl)
    df_radar.to_csv(ruta_radar_csv, index=False)

    print("\nRadar final:")
    print(df_radar.to_string(index=False))
    print(f"\nGuardado:\n- {ruta_procesado_pkl}\n- {ruta_procesado_csv}\n- {ruta_radar_pkl}\n- {ruta_radar_csv}")

if __name__ == "__main__":
    main()