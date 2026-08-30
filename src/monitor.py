"""
monitor.py — Estado del scraping por grupos

Muestra qué departamentos ya tienen pkl y cuáles faltan.

    python src/monitor.py
    python src/monitor.py datos/corpus/actualizados    # otra carpeta

Los grupos se leen de config_pipeline; antes estaban duplicados aquí y las dos
copias podían divergir.
"""
import os
import sys
import unicodedata
import time

DIR_SRC = os.path.dirname(os.path.abspath(__file__))
DIR_PROYECTO = os.path.dirname(DIR_SRC)   # raiz de desarrollo/
sys.path.insert(0, DIR_SRC)

import config_pipeline as cfg

DIRECTORIO = (sys.argv[1] if len(sys.argv) > 1
              else os.path.join(DIR_PROYECTO, cfg.RUTA_CORPUS_PKL))

GRUPOS = {i: g for i, g in enumerate(cfg.GRUPOS_DEPARTAMENTOS, 1)}

# Misma lógica de normalización que _nombre_archivo() en scrappers.py
def nombre_archivo(dep: str) -> str:
    normalizado = unicodedata.normalize("NFD", dep.lower())
    sin_tildes  = normalizado.encode("ascii", "ignore").decode("ascii")
    return f"df_corpus_{sin_tildes.replace(' ', '_')}.pkl"


def tamaño_mb(ruta: str) -> str:
    try:
        mb = os.path.getsize(ruta) / 1_048_576
        return f"{mb:.1f} MB"
    except OSError:
        return "?"


def tiempo_modificacion(ruta: str) -> str:
    try:
        ts = os.path.getmtime(ruta)
        return time.strftime("%d/%m %H:%M", time.localtime(ts))
    except OSError:
        return "?"


def main() -> None:
    total_deptos   = sum(len(v) for v in GRUPOS.values())
    total_completo = 0

    print(f"\n{'='*65}")
    print(f"  MONITOR DE SCRAPING — carpeta: {DIRECTORIO}/")
    print(f"{'='*65}")

    for g, deptos in GRUPOS.items():
        completados = []
        pendientes  = []

        for dep in deptos:
            ruta = os.path.join(DIRECTORIO, nombre_archivo(dep))
            if os.path.exists(ruta):
                completados.append((dep, ruta))
            else:
                pendientes.append(dep)

        total_completo += len(completados)
        estado = "✓ LISTO" if not pendientes else (
                 "▶ EN CURSO" if completados else "○ PENDIENTE")

        print(f"\nGrupo {g:2d}  [{len(completados)}/{len(deptos)}]  {estado}")

        for dep, ruta in completados:
            print(f"   ✓  {dep:<28} {tamaño_mb(ruta):>8}   {tiempo_modificacion(ruta)}")
        for dep in pendientes:
            print(f"   ○  {dep}")

    print(f"\n{'─'*65}")
    print(f"  Total: {total_completo}/{total_deptos} departamentos completados")

    # Listar pkls huérfanos (no reconocidos por ningún grupo)
    if os.path.isdir(DIRECTORIO):
        conocidos = {
            nombre_archivo(dep)
            for deptos in GRUPOS.values()
            for dep in deptos
        }
        huerfanos = [
            f for f in os.listdir(DIRECTORIO)
            if f.endswith(".pkl") and f not in conocidos
        ]
        if huerfanos:
            print(f"\n  Archivos no reconocidos en {DIRECTORIO}/:")
            for f in sorted(huerfanos):
                print(f"    {f}")

    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
