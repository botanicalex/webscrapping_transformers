"""
Fase 4 del experimento del pre-filtro social bajo MAX (experimentos/PREREG_prefiltro_max.md §6),
rama NO REINTEGRAR: vuelve a correr los indicadores y el radar de los 4 lugares con `src/` tal cual
(hipotesis V2, sin pre-filtro, sesgo descontado, MAX, cortes 0.766/0.9233).

Por que un envoltorio y no `python src/pipeline_lugares.py`: ese main() llama a paso1_combinar(),
que REESCRIBE datos/corpus/df_corpus_5lugares.pkl (compartido con desarrollo/). Aqui el corpus
se lee tal como esta, sin regenerarlo, y se comprueba su sha256 antes y despues.

Pasos:
  1. sha256 y fecha del pkl del corpus.
  2. pd.read_pickle.
  3. PipelineTransformers().procesar(df)  (GPU, ~40-50 min: 1.647 x 30 hipotesis).
  4. Guarda el procesado y llama a paso4_tablas y paso5_resumen de pipeline_lugares, apuntando a la
     carpeta NUEVA resultados/tablas_lugares_max_2026-09-28/ (las rutas de salida del modulo se leen
     de sys.argv[1] al importar; se fija antes de importar y se comprueba despues).
  5. Comprueba que el sha256 del corpus no cambio.

Ejecutar desde la raiz del worktree, en segundo plano y con log:
  PYTHONIOENCODING=utf-8 python -u experimentos/exp_prefiltro_correr_lugares.py \
      > experimentos/resultados/exp_prefiltro_correr_lugares.log 2>&1
"""
import datetime
import hashlib
import json
import os
import sys
import time

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(RAIZ, "datos", "corpus", "df_corpus_5lugares.pkl")
SALIDA_REL = os.path.join("resultados", "tablas_lugares_max_2026-09-28")
SALIDA = os.path.join(RAIZ, SALIDA_REL)
PRODUCCION_1SEP = os.path.join(RAIZ, "resultados", "tablas_lugares_max")


def sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    t0 = time.time()
    if os.path.abspath(SALIDA) == os.path.abspath(PRODUCCION_1SEP):
        sys.exit("la carpeta de salida coincide con la de la corrida del 1-sep: no se sobrescribe")
    if os.path.isdir(SALIDA) and os.listdir(SALIDA):
        sys.exit(f"{SALIDA} ya tiene contenido: no se mezcla ni se sobrescribe")

    # 1. huella del corpus
    h0 = sha256(CORPUS)
    f0 = datetime.datetime.fromtimestamp(os.path.getmtime(CORPUS)).isoformat(timespec="seconds")
    print(f"[1] corpus {CORPUS}\n    sha256 {h0}\n    fecha  {f0}\n    tamano {os.path.getsize(CORPUS)} bytes")

    # Las rutas de salida de pipeline_lugares se leen de sys.argv[1] al importar el modulo.
    sys.argv = [sys.argv[0], SALIDA_REL]
    sys.path.insert(0, os.path.join(RAIZ, "src"))
    import pipeline_lugares as pl
    from Transformer_optimo import PipelineTransformers
    assert os.path.abspath(pl.DIR_SALIDA) == os.path.abspath(SALIDA), pl.DIR_SALIDA
    assert os.path.abspath(pl.PROCESADO_PKL).startswith(os.path.abspath(SALIDA)), pl.PROCESADO_PKL
    assert os.path.abspath(pl.RESUMEN_XLSX).startswith(os.path.abspath(SALIDA)), pl.RESUMEN_XLSX
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, "corpus_sha256.json"), "w", encoding="utf-8") as fh:
        json.dump({"archivo": "datos/corpus/df_corpus_5lugares.pkl", "sha256_antes": h0, "fecha_archivo": f0,
                   "inicio": datetime.datetime.now().isoformat(timespec="seconds")}, fh, indent=2)

    # 2. lectura tal cual (no se llama a paso1_combinar)
    df = pd.read_pickle(CORPUS)
    print(f"\n[2] leido: {df.shape} | lugares: {df['departamento'].value_counts().to_dict()}")

    # 3. produccion tal cual
    print("\n[3] PipelineTransformers().procesar(df) ...")
    df_proc = PipelineTransformers().procesar(df)
    print(f"    procesado en {(time.time() - t0) / 60:.1f} min (shape {df_proc.shape})")

    # 4. respaldo, tablas y resumen en la carpeta nueva
    df_proc.to_pickle(pl.PROCESADO_PKL)
    print(f"\n[4] respaldo -> {pl.PROCESADO_PKL}")
    pl.paso4_tablas(df_proc)
    pl.paso5_resumen(df_proc)

    # 5. el corpus no debe haber cambiado
    h1 = sha256(CORPUS)
    f1 = datetime.datetime.fromtimestamp(os.path.getmtime(CORPUS)).isoformat(timespec="seconds")
    ok = (h0 == h1) and (f0 == f1)
    print(f"\n[5] corpus despues: sha256 {'IGUAL' if h0 == h1 else 'DISTINTO'}, fecha {'IGUAL' if f0 == f1 else 'DISTINTA'}")
    with open(os.path.join(SALIDA, "corpus_sha256.json"), "w", encoding="utf-8") as fh:
        json.dump({"archivo": "datos/corpus/df_corpus_5lugares.pkl", "sha256_antes": h0, "sha256_despues": h1,
                   "fecha_archivo_antes": f0, "fecha_archivo_despues": f1, "sin_cambios": ok,
                   "fin": datetime.datetime.now().isoformat(timespec="seconds"),
                   "minutos": round((time.time() - t0) / 60, 1)}, fh, indent=2)
    if not ok:
        sys.exit("ATENCION: el corpus cambio durante la corrida")
    print(f"\nLISTO -> {SALIDA} ({(time.time() - t0) / 60:.1f} min)")


if __name__ == "__main__":
    main()
