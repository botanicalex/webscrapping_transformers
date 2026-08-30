"""
Estandar de plata por palabras clave + metricas de discriminacion.

Etiquetado automatico para los dos indicadores con marcadores lexicos fiables.
NO es verdad absoluta: sirve para comparar variantes de hipotesis ENTRE SI.

Reglas de etiquetado (sobre titulo + texto, insensible a tildes):
  positivo  -> >= 2 coincidencias de keyword
  negativo  -> 0 coincidencias
  descartado-> exactamente 1 (zona ambigua)

Se descarta la zona ambigua a proposito: para medir si una variante ORDENA
mejor, conviene un contraste limpio entre extremos.

Metrica principal: AUC-ROC, libre de umbral. Responde "¿ordena bien?" sin
mezclarlo con "¿donde cortamos?" ni con la agregacion (MAX/TOP3), que son
decisiones separadas.
"""
import re
import unicodedata
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


def _sin_tildes(txt: str) -> str:
    return unicodedata.normalize("NFKD", str(txt).lower()).encode("ascii", "ignore").decode("ascii")


def _patron(keywords) -> re.Pattern:
    """
    Frontera de palabra al inicio, libre al final: asi 'indigena' captura
    'indigenas' y 'resguardo' captura 'resguardos'. El NER original usaba \\b a
    ambos lados y se perdia todos los plurales.
    """
    kws = sorted((_sin_tildes(k) for k in keywords), key=len, reverse=True)
    return re.compile("|".join(r"\b" + re.escape(k) for k in kws))


def etiquetar(df: pd.DataFrame, keywords, min_pos: int = 2) -> pd.DataFrame:
    """Devuelve el df con columnas n_kw y label (1 / 0 / NaN=descartado)."""
    pat = _patron(keywords)
    campo = (df["titulo"].fillna("").astype(str) + " . " + df["texto"].fillna("").astype(str))
    n_kw = campo.map(lambda t: len(pat.findall(_sin_tildes(t))))

    label = pd.Series(np.nan, index=df.index, dtype="float")
    label[n_kw >= min_pos] = 1.0
    label[n_kw == 0] = 0.0

    out = df.copy()
    out["n_kw"] = n_kw
    out["label"] = label
    return out


def auc(scores, labels) -> float:
    """
    AUC-ROC via rangos (Mann-Whitney U). Maneja empates con rango promedio.
    Devuelve NaN si falta alguna de las dos clases.
    """
    s = pd.Series(np.asarray(scores, dtype=float))
    y = np.asarray(labels, dtype=float)
    m = ~np.isnan(y)
    s, y = s[m], y[m]
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    r = s.rank(method="average").values
    return float((r[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def evaluar(scores, labels) -> Dict[str, float]:
    """AUC + separacion entre clases, para una variante."""
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=float)
    m = ~np.isnan(y)
    s, y = s[m], y[m]
    pos, neg = s[y == 1], s[y == 0]
    return {
        "auc": auc(s, y),
        "media_pos": float(pos.mean()) if len(pos) else float("nan"),
        "media_neg": float(neg.mean()) if len(neg) else float("nan"),
        "separacion": float(pos.mean() - neg.mean()) if len(pos) and len(neg) else float("nan"),
        "n_pos": int(len(pos)),
        "n_neg": int(len(neg)),
    }
