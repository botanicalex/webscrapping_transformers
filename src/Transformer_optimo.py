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
# scrappers NO se importa a nivel de modulo: arrastra playwright/aiohttp a
# cualquier proceso que solo quiera puntuar con GPU. Se importa dentro de
# correr_scraping(), la unica funcion que lo necesita.
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
        # sent_path = _ruta_modelo_local(self.modelo_sent_nombre)
        # ner_path  = _ruta_modelo_local(self.modelo_ner_nombre)
        print(f"NLI: {nli_path}")

        self.tokenizer_nli = AutoTokenizer.from_pretrained(nli_path)
        self.modelo_nli = AutoModelForSequenceClassification.from_pretrained(nli_path).to(self.device)
        self.modelo_nli.eval()
        self.label_ent, self.label_neu, self.label_con = self._resolver_labels_nli()

        # --- Sentimiento desactivado (2026-06-25): no alimenta indicadores ni radar ---
        # self.tokenizer_sent = AutoTokenizer.from_pretrained(sent_path)
        # self.modelo_sent = AutoModelForSequenceClassification.from_pretrained(sent_path).to(self.device)
        # self.modelo_sent.eval()
        # self.sentiment = hf_pipeline(
        #     "sentiment-analysis",
        #     model=self.modelo_sent,
        #     tokenizer=self.tokenizer_sent,
        #     device=PIPELINE_DEVICE
        # )

        # --- NER desactivado (2026-06-24): grupos_etnicos_existentes migrado a NLI,
        #     grupos_armados_existentes eliminado (presencia_grupos_armados lo cubre) ---
        # self.tokenizer_ner = AutoTokenizer.from_pretrained(ner_path)
        # self.modelo_ner = AutoModelForTokenClassification.from_pretrained(ner_path).to(self.device)
        # self.modelo_ner.eval()
        # self.ner = hf_pipeline(
        #     "ner",
        #     model=self.modelo_ner,
        #     tokenizer=self.tokenizer_ner,
        #     aggregation_strategy="simple",
        #     device=PIPELINE_DEVICE
        # )

        self.eventos = {
            "desplazamiento_forzado": "Este texto reporta que OCURRIÓ un desplazamiento forzado, expulsión o éxodo de comunidades",
            "reasentamiento": "Este texto reporta que SE REALIZÓ un reasentamiento, reubicación o traslado planificado de población",
            "protesta_social": "Este texto reporta que OCURRIÓ una protesta social, manifestación, bloqueo, movilización o paro",
            "amenaza_intimidacion": "Este texto reporta que OCURRIERON amenazas, intimidación, hostigamiento o violencia contra personas",
            "conflicto_territorial": "Este texto reporta una disputa activa y documentada por el control, uso o propiedad de un territorio o tierras específicas, con comunidades, grupos o actores plenamente identificados en conflicto directo entre sí por ese territorio.",
        }

        self.posturas = {
            "rechazo_proyecto": "Este artículo reporta oposición explícita de comunidades, organizaciones o autoridades frente a un proyecto energético, minero, vial, ambiental o de infraestructura.",
            "derechos_vulnerados": "Este artículo afirma explícitamente que se vulneraron derechos humanos, territoriales, colectivos, ambientales, étnicos o sociales de una comunidad o grupo poblacional identificado e identifica el derecho o la afectación denunciada.",
            "conflicto_activo": "Este artículo reporta un conflicto activo con hechos recientes como protestas, bloqueos, enfrentamientos, amenazas, denuncias o disputas territoriales.",
            "resistencia_territorial": "Este texto expresa resistencia activa, conflictividad o reivindicacion del territorio, los recursos naturales o el medio ambiente frente a una amenaza concreta.",
            "exclusion_comunidades": "Este texto exige participacion, consulta o inclusion porque las comunidades han sido excluidas de decisiones que las afectan directamente.",
        }

        self.indicadores = {
            # Ex zero-shot: convertidos a NLI (indicador) para detectar el tema
            # aunque no sea el tema dominante del artículo
            "deficit_participacion_comunitaria": "Este artículo denuncia explícitamente que comunidades, ciudadanos, veedurías u organizaciones sociales fueron excluidos de procesos de participación, consulta, socialización o toma de decisiones sobre un proyecto, obra, política pública o intervención territorial específica que la afecta.",
            "incentivos_economicos_inequitativos": "Este artículo reporta explícitamente una distribución inequitativa de compensaciones, regalías, pagos o beneficios económicos de un proyecto, identificando a una comunidad o población perjudicada.",
            "debilidad_institucional": "Este texto evidencia una debilidad institucional grave y documentada: entidades con déficit de recursos o incapacidad demostrada para cumplir su mandato.",
            "danos_ambientales": "Este articulo reporta danos ambientales verificables, contaminacion, perdida de biodiversidad o degradacion de ecosistemas.",
            "conflictos_socioambientales": "Este artículo reporta disputas entre comunidades, empresas o instituciones relacionadas explícitamente con daños ambientales, uso del territorio, minería, agua, energía o infraestructura.",
            # NLI indicadores originales
            "violacion_derechos_humanos": "Este texto reporta una denuncia formal o explicita de violaciones de derechos humanos, abusos o incumplimientos graves de acuerdos, presentada por comunidades, organizaciones o defensores identificados.",
            "exclusion_servicios_derechos": "Este texto describe brechas concretas de exclusión en acceso a servicios, derechos u oportunidades",
            "grupos_etnicos_existentes": "Este artículo menciona explícitamente comunidades étnicas, pueblos indígenas, comunidades afrodescendientes, raizales, palenqueras o grupos étnicos que tienen presencia o participación relevante en el territorio.",
            "movimientos_sociales": "Este texto reporta movilizaciones, protestas, paros, plantones o acciones colectivas convocadas por movimientos sociales, organizaciones comunitarias o plataformas ciudadanas en defensa de derechos, territorio o condiciones de vida.",
            "poblacion_afectada": "Este artículo reporta explícitamente comunidades, familias o grupos poblacionales afectados negativamente por violencia, conflicto, desastre, proyecto o decisión institucional.",
            "exclusion_beneficios_economicos": "Este artículo reporta explícitamente que una comunidad o población identificada fue excluida de compensaciones, regalías, empleo, pagos u otros beneficios económicos generados por un proyecto o actividad productiva específica.",
            "irregularidad_contractual": "Este texto reporta irregularidades, sobreprecios, corrupción, desvío de fondos, favoritismos o incumplimientos detectados en contratos, compras o adjudicaciones públicas de obras, servicios o proyectos financiados por el Estado.",
            "zonas_proteccion_alimentaria": "Este texto menciona cultivos, tierras de siembra, parcelas agrícolas, producción de alimentos, acceso a comida, soberanía alimentaria o seguridad alimentaria de familias o comunidades rurales.",
            "dano_territorios": "Este texto reporta destrucción, ocupación ilegal, contaminación o despojo de territorios, tierras o recursos naturales pertenecientes a comunidades o pueblos identificados, causado por actores externos, actividades extractivas o proyectos específicos.",
            "presencia_grupos_armados": "Este artículo menciona explícitamente la presencia, acción, control o intervención de grupos armados ilegales en un territorio.",
            "amenaza_lideres": "Este texto reporta amenazas directas, hostigamiento, asesinato, desaparición o agresión física contra líderes sociales, defensores de derechos humanos o líderes comunitarios identificados por nombre o cargo.",
        }

        # ------------------------------------------------------------------
        # Pre-filtro de relevancia social (NLI).
        # score_social = P(entailment) del articulo contra esta hipotesis.
        # Los articulos con score_social < umbral_social NO aportan señal a
        # los 26 indicadores NLI (ver procesar()).
        # ------------------------------------------------------------------
        self.umbral_social = 0.65
        self.hipotesis_social = (
            "Este texto reporta conflictos, afectaciones, riesgos, protestas, vulneraciones de derechos, tensiones comunitarias, impactos territoriales o problemas institucionales que afectan a comunidades o poblaciones."
        )

        # --- NER/entidades desactivado (2026-06-24) ---
        # self.ref_entidades = {
        #     "grupos_etnicos_existentes": {"indígena", "indigena", "afrodescendiente", "afrocolombiano", "raizal", "palenquero", "resguardo", "cabildo"},
        #     "grupos_armados_existentes": {"eln", "farc", "disidencias", "epl", "auc", "agc", "clan del golfo", "guerrilla", "paramilitar"},
        # }
        # self._re_entidades: Dict[str, re.Pattern] = {
        #     cat: re.compile(
        #         '|'.join(r'\b' + re.escape(ref) + r'\b' for ref in sorted(refs, key=len, reverse=True)),
        #         re.IGNORECASE | re.UNICODE,
        #     )
        #     for cat, refs in self.ref_entidades.items()
        # }

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

    # --- _entidades_booleanas desactivado (2026-06-24) ---
    # def _entidades_booleanas(self, texto: str) -> Dict[str, bool]:
    #     res = {k: False for k in self.ref_entidades.keys()}
    #     for cat, pat in self._re_entidades.items():
    #         if pat.search(texto):
    #             res[cat] = True
    #     try:
    #         with torch.no_grad():
    #             ents = self.ner(texto[:3000])
    #         for e in ents:
    #             w = str(e.get("word", ""))
    #             for cat, pat in self._re_entidades.items():
    #                 if pat.search(w):
    #                     res[cat] = True
    #     except Exception:
    #         pass
    #     return res

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

    # --- _ner_batch desactivado (2026-06-24) ---
    # def _ner_batch(self, textos: List[str], batch_size: int = 32) -> Dict[str, List[bool]]:
    #     """NER + keyword matching en batch. Devuelve dict cat -> lista de N bools."""
    #     N = len(textos)
    #     res: Dict[str, List[bool]] = {k: [False] * N for k in self.ref_entidades}
    #     for idx, t in enumerate(textos):
    #         for cat, pat in self._re_entidades.items():
    #             if pat.search(t):
    #                 res[cat][idx] = True
    #     try:
    #         ner_resultados = self.ner(
    #             [t[:3000] for t in textos],
    #             batch_size=batch_size,
    #             truncation=True,
    #         )
    #         for idx, ents in enumerate(ner_resultados):
    #             for e in ents:
    #                 w = str(e.get("word", ""))
    #                 for cat, pat in self._re_entidades.items():
    #                     if pat.search(w):
    #                         res[cat][idx] = True
    #     except Exception:
    #         pass
    #     return res

    # ------------------------------------------------------------------
    # procesar() — versión batch (~30x más rápida que el loop original)
    # ------------------------------------------------------------------

    def procesar(self, df: pd.DataFrame, batch_size: int = 32) -> pd.DataFrame:
        df = df.copy()
        textos = df["texto"].fillna("").astype(str).tolist()
        N = len(textos)

        # Inicializar columnas a 0
        cols_nli = list(self.eventos) + list(self.posturas) + list(self.indicadores)
        for col in cols_nli:
            if col not in df.columns:
                df[col] = 0.0

        # 1. Pre-filtro de relevancia social (ANTES de los indicadores)
        score_social = self._nli_batch(textos, self.hipotesis_social, batch_size)
        df["score_social"] = [round(float(s), 6) for s in score_social]
        relevante = df["score_social"] >= self.umbral_social
        n_rel = int(relevante.sum())
        print(f"[batch] Pre-filtro social: {n_rel}/{N} relevantes (>= {self.umbral_social}); "
              f"{N - n_rel} articulos descartados (no se procesan)")

        # 2. NLI en batch: solo sobre articulos relevantes
        textos_rel = [t for t, r in zip(textos, relevante) if r]
        idx_rel = df.index[relevante].tolist()
        todos = {**self.eventos, **self.posturas, **self.indicadores}
        n_hip = len(todos)
        for i_hip, (clave, hipotesis) in enumerate(todos.items(), 1):
            scores = self._nli_batch(textos_rel, hipotesis, batch_size)
            df.loc[idx_rel, clave] = scores
            if i_hip % 5 == 0 or i_hip == n_hip:
                print(f"[batch] NLI hipotesis {i_hip}/{n_hip} completada ({len(textos_rel)} articulos)")

        self._crear_scores_dimension(df)
        print(f"[batch] Procesamiento completado: {N} articulos ({n_rel} procesados, {N - n_rel} descartados)")
        return df

    def _crear_scores_dimension(self, df: pd.DataFrame) -> None:
        dim1 = ["irregularidad_contractual","exclusion_comunidades","deficit_participacion_comunitaria","conflicto_activo"]
        dim2 = ["debilidad_institucional"]
        dim3 = ["incentivos_economicos_inequitativos","protesta_social","rechazo_proyecto","exclusion_servicios_derechos","movimientos_sociales","poblacion_afectada","exclusion_beneficios_economicos"]
        dim4 = ["danos_ambientales","conflictos_socioambientales","reasentamiento","conflicto_territorial","resistencia_territorial","dano_territorios"]
        dim5 = ["desplazamiento_forzado","amenaza_intimidacion","violacion_derechos_humanos","derechos_vulnerados","presencia_grupos_armados","amenaza_lideres"]
        for c in dim1 + dim2 + dim3 + dim4 + dim5:
            if c not in df.columns:
                df[c] = 0.0
        df["score_dim1_gobernanza"] = df[dim1].astype(float).mean(axis=1).round(4)
        df["score_dim2_capacidad_institucional"] = df[dim2].astype(float).mean(axis=1).round(4)
        df["score_dim3_vulneracion_socioeconomica"] = df[dim3].astype(float).mean(axis=1).round(4)
        df["score_dim4_vulnerabilidad_territorial"] = df[dim4].astype(float).mean(axis=1).round(4)
        df["score_dim5_derechos_humanos_conflicto"] = df[dim5].astype(float).mean(axis=1).round(4)

def correr_scraping(fecha_desde: str, fecha_hasta: str, salida: str, temas: List[str] = None):
    # Import diferido: scrappers arrastra playwright/aiohttp/nest_asyncio y esta
    # es la unica funcion del modulo que lo necesita. Importarlo arriba obligaba
    # a cargarlo tambien en los procesos que solo puntuan con GPU.
    import scrappers as sc

    os.makedirs(salida, exist_ok=True)
    for i, grupo in enumerate(cfg.GRUPOS_DEPARTAMENTOS, 1):
        print(f"\nGrupo {i}/{len(cfg.GRUPOS_DEPARTAMENTOS)}: {grupo}")
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


def exportar_indicadores_transformers_por_departamento(df_procesado: pd.DataFrame, salida: str) -> Tuple[str, str]:
    """
    Agrega los indicadores por departamento usando el VALOR MAXIMO entre todos
    los articulos del departamento (no el promedio): un promedio diluiria/anularia
    señales reales que solo aparecen en uno o pocos articulos.

    Para cada indicador y departamento, ademas del valor maximo, se registra el
    articulo que produjo ese maximo (titulo, url, periodico, fecha) en un CSV
    separado de "fuentes" para permitir la verificacion manual de que el
    indicador refleja algo real en el articulo de origen.

    Retorna (ruta_indicadores_csv, ruta_fuentes_csv).
    """
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

    # Columnas de identificacion del articulo, para trazabilidad del valor maximo
    cols_identificacion = [c for c in ['titulo', 'url', 'periodico', 'fecha'] if c in df.columns]

    filas_valores: List[dict] = []
    filas_fuentes: List[dict] = []
    for depto, grupo in df.groupby('departamento'):
        fila_valores = {'departamento': depto}
        for c in cols:
            idx_max = grupo[c].idxmax()
            valor_max = grupo.loc[idx_max, c]
            fila_valores[c] = valor_max

            fila_fuente = {
                'departamento': depto,
                'indicador': c,
                'valor_maximo': valor_max,
            }
            for ci in cols_identificacion:
                fila_fuente[ci] = grupo.loc[idx_max, ci]
            filas_fuentes.append(fila_fuente)
        filas_valores.append(fila_valores)

    df_indicadores = pd.DataFrame(filas_valores)
    ruta_indicadores_csv = os.path.join(salida, "indicadores_transformers_departamento.csv")
    df_indicadores.to_csv(ruta_indicadores_csv, index=False)

    df_fuentes = pd.DataFrame(filas_fuentes)
    ruta_fuentes_csv = os.path.join(salida, "indicadores_transformers_departamento_fuentes.csv")
    df_fuentes.to_csv(ruta_fuentes_csv, index=False)

    return ruta_indicadores_csv, ruta_fuentes_csv


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

    ruta_indicadores_csv, ruta_fuentes_csv = exportar_indicadores_transformers_por_departamento(df_procesado, salida)
    ruta_radar_pkl, ruta_radar_csv = exportar_radar_base_por_departamento(df_procesado, salida)

    ValidadorPrecondiciones.etapa_salida_no_vacia(ruta_radar_pkl, "radar_base")

    print(f"\nGuardado:\n- {ruta_procesado_pkl}\n- {ruta_procesado_csv}\n- {ruta_indicadores_csv}\n- {ruta_fuentes_csv}\n- {ruta_radar_pkl}\n- {ruta_radar_csv}")

    return ruta_procesado_pkl, ruta_radar_pkl

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha-desde", default=cfg.FECHA_DESDE)
    parser.add_argument("--fecha-hasta", default=cfg.FECHA_HASTA)
    parser.add_argument("--ruta-pkl", default=cfg.RUTA_CORPUS_PKL)
    parser.add_argument("--salida", default=cfg.RUTA_SALIDA_PIPELINE)
    parser.add_argument("--skip-scraping", action="store_true")
    args = parser.parse_args()

    if not args.skip_scraping:
        correr_scraping(args.fecha_desde, args.fecha_hasta, args.ruta_pkl, temas=None)

    run_pipeline_transformers(args.ruta_pkl, args.salida)

if __name__ == "__main__":
    main()