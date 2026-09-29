"""Utilidades comunes de la F1 de la etapa 2 del pre-filtro (solo lectura; sin efectos al importar)."""
import ast
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_prefiltro_e2 as P  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
from hipotesis_5ind_max import normalizar  # noqa: E402

CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
SRC = "src/Transformer_optimo.py"


def prefiltro_produccion():
    """PREFILTRO_OBJETO literal de src/Transformer_optimo.py (sin importarlo)."""
    arbol = ast.parse(open(SRC, encoding="utf-8").read())
    for n in arbol.body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "PREFILTRO_OBJETO":
            return ast.literal_eval(n.value)
    raise RuntimeError("PREFILTRO_OBJETO no encontrado")


def premisa_visible_prod(textos, tokenizer, hipotesis, max_length=512):
    """Copia de src.Transformer_optimo.premisa_visible (recorta con UNA hipotesis)."""
    n = max_length - 3 - len(tokenizer(hipotesis, add_special_tokens=False)["input_ids"])
    ids = tokenizer([str(t) for t in textos], add_special_tokens=False)["input_ids"]
    return [tokenizer.decode(x[:n], skip_special_tokens=True) for x in ids]


def compuerta(premisas, rx):
    pat = re.compile(rx)
    return [1.0 if pat.search(normalizar(p)) else 0.0 for p in premisas]


def cargar_tokenizer():
    from transformers import AutoTokenizer
    from nli_core import MODELO_NLI, _ruta_modelo_local
    return AutoTokenizer.from_pretrained(_ruta_modelo_local(MODELO_NLI))
