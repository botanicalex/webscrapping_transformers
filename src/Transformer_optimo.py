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

        # ------------------------------------------------------------------
        # V2 (promovido 2026-08-31, ver contexto/08_log_decisiones.md).
        # V0 usaba un marco metalinguistico ("Este texto reporta que X") que
        # inflaba los scores: el 78% de las noticias "implicaba" una hipotesis
        # de contenido imposible (control absurdo con pinguinos emperador,
        # ver contexto/04_hallazgos_revision_nli.md). V2 describe el
        # territorio o el hecho directamente, sin ese marco. Las 26 claves son
        # identicas a V0 -- solo cambia el texto de la hipotesis.
        # ------------------------------------------------------------------
        self.eventos = {
            "desplazamiento_forzado": "Hubo un desplazamiento forzado o éxodo de comunidades.",
            "reasentamiento": "Se realizó un reasentamiento o reubicación de población.",
            "protesta_social": "Hubo una protesta, manifestación, bloqueo o paro.",
            "amenaza_intimidacion": "Hubo amenazas, intimidación u hostigamiento contra personas.",
            "conflicto_territorial": "Hay una disputa por el control, el uso o la propiedad de un territorio.",
        }

        self.posturas = {
            "rechazo_proyecto": "Hay oposición de comunidades o autoridades a un proyecto.",
            "derechos_vulnerados": "Se vulneraron los derechos de una comunidad.",
            "conflicto_activo": "Hay un conflicto activo en este territorio.",
            "resistencia_territorial": "Hay resistencia comunitaria en defensa del territorio o el medio ambiente.",
            # EXIGENCIA de inclusión (se diferencia de deficit_participacion_comunitaria)
            "exclusion_comunidades": "Las comunidades exigen ser consultadas o incluidas en las decisiones.",
        }

        self.indicadores = {
            # AUSENCIA de proceso participativo
            "deficit_participacion_comunitaria": "No hubo consulta ni participación de la comunidad en un proyecto o decisión.",
            "incentivos_economicos_inequitativos": "El reparto de compensaciones o regalías de un proyecto fue desigual.",
            "debilidad_institucional": "Las instituciones carecen de recursos o de capacidad para cumplir su función.",
            "danos_ambientales": "Hubo daños ambientales, contaminación o pérdida de biodiversidad.",
            "conflictos_socioambientales": "Hay un conflicto por el uso del territorio, el agua o los recursos naturales.",
            "violacion_derechos_humanos": "Se denunciaron violaciones de derechos humanos.",
            "exclusion_servicios_derechos": "Hay población sin acceso a servicios básicos o a sus derechos.",
            "grupos_etnicos_existentes": "En este territorio hay comunidades étnicas o pueblos indígenas.",
            "movimientos_sociales": "Hay movilizaciones u organizaciones sociales activas.",
            "poblacion_afectada": "Hay comunidades o familias afectadas.",
            "exclusion_beneficios_economicos": "Una comunidad quedó excluida de los beneficios económicos de un proyecto.",
            "irregularidad_contractual": "Hubo irregularidades o corrupción en contratos públicos.",
            "zonas_proteccion_alimentaria": "Hay cultivos, tierras de siembra o producción de alimentos.",
            "dano_territorios": "Hubo destrucción, ocupación ilegal o despojo de territorios.",
            "presencia_grupos_armados": "En este territorio hay presencia de grupos armados ilegales.",
            "amenaza_lideres": "Hubo amenazas o agresiones contra líderes sociales.",
        }

        # ------------------------------------------------------------------
        # Calibracion del sesgo "si-decidor" por articulo (V2). Hay artículos
        # que puntúan alto contra CUALQUIER hipótesis, incluidas las
        # imposibles (contexto/04_hallazgos_revision_nli.md). Se estima ese
        # sesgo con 4 hipótesis nulas de dominios variados y se descuenta de
        # los 26 indicadores reales (ver procesar()). Una 5ª nula
        # ("hay colonias de osos polares") queda reservada para evaluar el
        # control absurdo honestamente y NUNCA entra aquí (regla del proyecto).
        # ------------------------------------------------------------------
        self.nulas_calibracion = [
            "En este territorio hay presencia de pingüinos emperador.",
            "En este territorio hay yacimientos de helio-3 lunar.",
            "En este territorio se practica la caligrafía medieval japonesa.",
            "En este territorio hay glaciares de metano líquido.",
        ]

        # ------------------------------------------------------------------
        # Pre-filtro de relevancia social: RETIRADO (2026-08-31).
        # Costaba AUC de forma clara y estadísticamente significativa en los
        # 2 indicadores con estándar de plata (-0.053 y -0.027, IC95% excluye
        # cero) sin que el control absurdo lo explicara — ver
        # contexto/08_log_decisiones.md [2026-08-31]. Los 26 indicadores se
        # puntúan sobre TODOS los artículos, sin descartar ninguno antes.
        # ------------------------------------------------------------------

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

    def _nli_batch(
        self, textos: List[str], hipotesis: str, batch_size: int = 32,
        devolver_neutral: bool = False,
    ):
        """
        Calcula P(entailment) de N textos contra UNA hipótesis en chunks.
        Con devolver_neutral=True devuelve (ent, neu) -- necesario para la
        fórmula corregida V2: clip(clip(ent-sesgo,0)*(1-neu),0,1).
        """
        ent: List[float] = []
        neu: List[float] = []
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
            ent.extend(probs[:, self.label_ent].cpu().tolist())
            if devolver_neutral:
                neu.extend(probs[:, self.label_neu].cpu().tolist())
        if devolver_neutral:
            return ent, neu
        return ent

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

        # 1. Sesgo "si-decidor" por articulo: media de las 4 nulas de
        #    calibracion (V2, ver __init__). Se descuenta de los 26
        #    indicadores reales mas abajo -- nunca se usa la nula reservada.
        print(f"[batch] Calibrando sesgo por articulo (4 nulas)...")
        sesgo_nulas = [self._nli_batch(textos, h, batch_size) for h in self.nulas_calibracion]
        sesgo = np.mean(sesgo_nulas, axis=0)
        df["sesgo"] = np.round(sesgo, 6)

        # 2. NLI en batch sobre TODOS los articulos (sin pre-filtro, ver
        #    __init__), aplicando la formula corregida V2:
        #    clip(clip(ent - sesgo, 0) * (1 - neu), 0, 1)
        todos = {**self.eventos, **self.posturas, **self.indicadores}
        n_hip = len(todos)
        for i_hip, (clave, hipotesis) in enumerate(todos.items(), 1):
            ent, neu = self._nli_batch(textos, hipotesis, batch_size, devolver_neutral=True)
            ent = np.asarray(ent, dtype=float)
            neu = np.asarray(neu, dtype=float)
            corregido = np.clip(np.clip(ent - sesgo, 0, None) * (1 - neu), 0, 1)
            df[clave] = np.round(corregido, 6)
            if i_hip % 5 == 0 or i_hip == n_hip:
                print(f"[batch] NLI hipotesis {i_hip}/{n_hip} completada ({N} articulos)")

        self._crear_scores_dimension(df)
        print(f"[batch] Procesamiento completado: {N} articulos")
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
    Agrega los indicadores por departamento usando el MAXIMO entre todos los
    articulos del departamento (decision de esta rama, requisito de negocio).
    El MAX esta dominado por el tamaño del corpus: un departamento con mas
    articulos tiene mas oportunidades de que algo puntue alto, con
    independencia del riesgo real (razon señal/artefacto 0.91 medida en
    contexto/04_hallazgos_revision_nli.md). La decision tecnica del historial
    del proyecto era el PERCENTIL 75 (razon 49.0, ver
    contexto/08_log_decisiones.md) — esta rama vuelve al MAX de V0 a pedido
    explicito, con esa limitacion conocida.

    El valor resultante es siempre el de un articulo real, así que se
    conserva la trazabilidad — para cada indicador y departamento se
    registra el artículo que produjo ese valor (titulo, url, periodico,
    fecha) en un CSV separado de "fuentes", para permitir la verificacion
    manual de que el indicador refleja algo real en el articulo de origen.

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

    # Columnas de identificacion del articulo, para trazabilidad del MAX
    cols_identificacion = [c for c in ['titulo', 'url', 'periodico', 'fecha'] if c in df.columns]

    filas_valores: List[dict] = []
    filas_fuentes: List[dict] = []
    for depto, grupo in df.groupby('departamento'):
        fila_valores = {'departamento': depto}
        for c in cols:
            valor = grupo[c].max()
            idx = grupo[c].idxmax()
            fila_valores[c] = valor

            fila_fuente = {
                'departamento': depto,
                'indicador': c,
                'valor_max': valor,
            }
            for ci in cols_identificacion:
                fila_fuente[ci] = grupo.loc[idx, ci]
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