"""
Motor NLI mínimo para los experimentos — sin dependencias del pipeline de produccion.

Transformer_optimo.py importa `scrappers` (playwright, aiohttp, ...) y
`config_pipeline`, lo que hace pesado importarlo solo para puntuar hipotesis.
Este modulo replica EXACTAMENTE la logica de scoring de produccion
(`_resolver_labels_nli` y `_nli_batch`) sin esa cadena de imports.

Diferencias intencionales respecto a produccion, necesarias para los experimentos:
  - `max_length` es configurable (produccion lo fija en 512).
  - `score()` puede devolver las TRES probabilidades, no solo entailment.
  - La premisa se pasa como lista de strings ya construida, para poder probar
    variantes (cuerpo / titular / titular+lede).

Verificacion obligatoria antes de usarlo: `verificar_contra_produccion()` debe
reproducir los scores del pkl de baseline. Si no coincide, este modulo se
desvio de produccion y los experimentos no serian comparables.
"""
from typing import Dict, List, Tuple

import os

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODELO_NLI = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
HF_HUB_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")


def _ruta_modelo_local(nombre_modelo: str) -> str:
    """Idéntica a la de Transformer_optimo.py: usa el snapshot local si existe."""
    carpeta = "models--" + nombre_modelo.replace("/", "--")
    refs_main = os.path.join(HF_HUB_CACHE, carpeta, "refs", "main")
    if os.path.isfile(refs_main):
        with open(refs_main) as f:
            commit = f.read().strip()
        ruta = os.path.join(HF_HUB_CACHE, carpeta, "snapshots", commit)
        if os.path.isdir(ruta):
            return ruta
    return nombre_modelo


class NLIScorer:
    def __init__(self, modelo: str = MODELO_NLI, verbose: bool = True):
        ruta = _ruta_modelo_local(modelo)
        self.device = DEVICE
        self.tokenizer = AutoTokenizer.from_pretrained(ruta)
        self.modelo = AutoModelForSequenceClassification.from_pretrained(ruta).to(self.device)
        self.modelo.eval()
        self.label_ent, self.label_neu, self.label_con = self._resolver_labels()
        if verbose:
            print(f"NLI cargado | device={self.device}")
            print(f"  id2label   : {self.modelo.config.id2label}")
            print(f"  entailment={self.label_ent}  neutral={self.label_neu}  contradiction={self.label_con}")

    def _resolver_labels(self) -> Tuple[int, int, int]:
        """Copia literal de Transformer_optimo._resolver_labels_nli()."""
        id2label = self.modelo.config.id2label
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

    def score(
        self,
        premisas: List[str],
        hipotesis: str,
        batch_size: int = 32,
        max_length: int = 512,
        devolver_todo: bool = False,
    ):
        """
        P(entailment) de cada premisa contra UNA hipotesis.

        Con max_length=512 y premisas = df['texto'], reproduce exactamente
        `PipelineTransformers._nli_batch`.

        devolver_todo=True -> dict con las tres probabilidades (para diagnostico).
        """
        ent, neu, con = [], [], []
        for start in range(0, len(premisas), batch_size):
            chunk = [str(p) for p in premisas[start: start + batch_size]]
            inputs = self.tokenizer(
                chunk,
                [hipotesis] * len(chunk),
                truncation=True,
                max_length=max_length,
                padding=True,
                return_tensors="pt",
            ).to(self.device)
            with torch.no_grad():
                probs = torch.softmax(self.modelo(**inputs).logits, dim=1)
            ent.extend(probs[:, self.label_ent].cpu().tolist())
            if devolver_todo:
                neu.extend(probs[:, self.label_neu].cpu().tolist())
                con.extend(probs[:, self.label_con].cpu().tolist())

        if devolver_todo:
            return {"entailment": ent, "neutral": neu, "contradiction": con}
        return ent


# ── Construccion de premisas (eje 4 del experimento) ─────────────────────────

def premisa_cuerpo(df) -> List[str]:
    """Produccion actual: solo el cuerpo, el titular NO entra."""
    return df["texto"].fillna("").astype(str).tolist()


def premisa_titular(df) -> List[str]:
    return df["titulo"].fillna("").astype(str).tolist()


def premisa_titular_lede(df, n_chars: int = 400) -> List[str]:
    tit = df["titulo"].fillna("").astype(str)
    cuerpo = df["texto"].fillna("").astype(str).str[:n_chars]
    return (tit + ". " + cuerpo).tolist()


def premisa_primeras_frases(df, n: int = 2) -> List[str]:
    import re
    out = []
    for t in df["texto"].fillna("").astype(str):
        frases = re.split(r"(?<=[.!?])\s+", t.strip())
        out.append(" ".join(frases[:n]))
    return out


PREMISAS = {
    "cuerpo": premisa_cuerpo,             # produccion
    "titular": premisa_titular,
    "titular_lede": premisa_titular_lede,
    "primeras_frases": premisa_primeras_frases,
}


# ── Verificacion contra produccion ───────────────────────────────────────────

def verificar_contra_produccion(scorer: "NLIScorer", ruta_baseline: str, indicador: str,
                                hipotesis: str, tol: float = 1e-4) -> bool:
    """
    Recalcula UN indicador sobre los articulos relevantes del baseline y lo compara
    con los valores guardados. Debe coincidir dentro de `tol`.
    """
    import pandas as pd
    df = pd.read_pickle(ruta_baseline)
    rel = df["score_social"] >= 0.65
    sub = df[rel]
    nuevos = scorer.score(sub["texto"].fillna("").astype(str).tolist(), hipotesis)
    dif = np.abs(np.array(nuevos) - sub[indicador].astype(float).values)
    ok = bool(dif.max() < tol)
    print(f"Verificacion '{indicador}': max|dif| = {dif.max():.2e} -> {'OK' if ok else 'DESVIACION'}")
    return ok
