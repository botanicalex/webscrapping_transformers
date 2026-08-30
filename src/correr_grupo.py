"""
Corre el scraping de un grupo de departamentos.

Reemplaza a los antiguos grupo_01.py ... grupo_11.py, que eran 11 archivos
byte a byte identicos salvo el indice. Aquellos ademas ejecutaban al importarse
(no tenian guard __main__), asi que un `import grupo_01` disparaba scraping real.

Uso:
    python src/correr_grupo.py 5          # solo el grupo 5
    python src/correr_grupo.py 1 2 3      # varios, en secuencia
    python src/correr_grupo.py --todos    # los 11
    python src/correr_grupo.py --listar   # ver la composicion sin correr

La composicion de los grupos y el porque de cada agrupacion estan documentados
en config_pipeline.GRUPOS_DEPARTAMENTOS. No es arbitraria: evita que dos
departamentos que usan el mismo periodico compitan por el mismo servidor.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config_pipeline as cfg
from scrappers import scrape_multiples_departamentos

# Raiz del proyecto = padre de src/
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def listar():
    print(f"{len(cfg.GRUPOS_DEPARTAMENTOS)} grupos configurados:\n")
    for i, g in enumerate(cfg.GRUPOS_DEPARTAMENTOS, 1):
        print(f"  G{i:<3} ({len(g)}) {' | '.join(g)}")
    print("\nEl porque de cada agrupacion esta en config_pipeline.py")


def correr(n: int, salida: str) -> None:
    """n es 1-based, como en los nombres de los antiguos grupo_NN.py."""
    if not 1 <= n <= len(cfg.GRUPOS_DEPARTAMENTOS):
        sys.exit(f"ERROR: grupo {n} fuera de rango (1..{len(cfg.GRUPOS_DEPARTAMENTOS)})")

    deptos = cfg.GRUPOS_DEPARTAMENTOS[n - 1]
    os.makedirs(salida, exist_ok=True)
    print(f"\n{'='*70}\nGRUPO {n}: {' | '.join(deptos)}")
    print(f"Periodo: {cfg.FECHA_DESDE} -> {cfg.FECHA_HASTA}")
    print(f"Salida : {salida}\n{'='*70}")

    t0 = time.time()
    scrape_multiples_departamentos(
        departamentos=deptos,
        fecha_desde=cfg.FECHA_DESDE,
        fecha_hasta=cfg.FECHA_HASTA,
        min_menciones=None,      # se resuelve por depto en scrappers.py
        directorio_salida=salida,
        temas=None,              # None -> usa cfg.TEMAS_BUSQUEDA
    )
    print(f"\nGrupo {n} completado en {(time.time()-t0)/60:.1f} minutos")


def main():
    p = argparse.ArgumentParser(description="Scraping por grupo de departamentos")
    p.add_argument("grupos", nargs="*", type=int, help="numeros de grupo (1-based)")
    p.add_argument("--todos", action="store_true", help="correr los 11 grupos en secuencia")
    p.add_argument("--listar", action="store_true", help="mostrar la composicion y salir")
    p.add_argument("--salida", default=os.path.join(RAIZ, cfg.RUTA_CORPUS_PKL),
                   help="carpeta destino de los df_corpus_*.pkl")
    a = p.parse_args()

    if a.listar:
        listar()
        return
    objetivo = list(range(1, len(cfg.GRUPOS_DEPARTAMENTOS) + 1)) if a.todos else a.grupos
    if not objetivo:
        p.error("indica al menos un grupo, o usa --todos / --listar")

    for n in objetivo:
        correr(n, a.salida)


if __name__ == "__main__":
    main()
