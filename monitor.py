"""
monitor.py — Estado del scraping por grupos

Muestra qué departamentos ya tienen pkl en resultados/ y cuáles faltan.
Ejecutar desde la misma carpeta que scrappers.py:

    python monitor.py
"""
import os
import unicodedata
import time

DIRECTORIO = "resultados"

GRUPOS = {
    1:  ["Antioquia",           "Chocó",      "Vichada"],
    2:  ["Valle del Cauca",     "Arauca",      "Atlántico"],
    3:  ["Caldas",              "Meta",        "Bolívar"],
    4:  ["Risaralda",           "Caquetá",     "Putumayo"],
    5:  ["Quindío",             "Guaviare",    "Amazonas"],
    6:  ["Santander",           "Cesar",       "Boyacá"],
    7:  ["Norte de Santander",  "Magdalena",   "Guainía"],
    8:  ["Cundinamarca",        "La Guajira",  "Cauca"],
    9:  ["Córdoba",             "Nariño",      "Vaupés"],
    10: ["Sucre",               "Huila",       "San Andrés y Providencia"],
    11: ["Casanare",            "Tolima"],
}

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
