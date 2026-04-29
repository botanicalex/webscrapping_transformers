#!/usr/bin/env python3
"""
prueba_rapida.py — Prueba rápida de un solo departamento
Proyecto FNCE — UPB

Uso: python prueba_rapida.py
"""

import time
from scrappers import scrape_departamento

def main():
    """Prueba rápida con un departamento pequeño."""
    print("🧪 PRUEBA RÁPIDA - Scraping de un departamento")
    print("📍 Departamento: Antioquia (limitado a 5 artículos)")
    print("📅 Fechas: 2023-01-01 a 2023-01-31")
    print("🔍 Temas: conflicto, comunidades")
    print()

    inicio = time.time()

    try:
        # Prueba con un departamento pequeño y fechas limitadas
        df = scrape_departamento(
            departamento="Antioquia",
            fecha_desde="2023-01-01",
            fecha_hasta="2023-01-31",
            temas=["conflicto", "comunidades"],
            min_articulos=5  # Limitar para prueba rápida
        )

        duracion = time.time() - inicio

        print()
        print("✅ PRUEBA EXITOSA")
        print(f"⏱️  Tiempo: {duracion:.1f} segundos")
        print(f"📊 Artículos obtenidos: {len(df)}")
        print()
        print("📋 Primeros resultados:")
        print(df[['periodico', 'titulo', 'fecha']].head())
        print()
        print("🎉 ¡El sistema está funcionando correctamente!")
        print("💡 Ahora puedes ejecutar todos los grupos con:")
        print("   python ejecutar_todos_los_grupos.py")

    except Exception as e:
        print(f"❌ ERROR en la prueba: {e}")
        print("🔧 Revisa la configuración y dependencias")

if __name__ == "__main__":
    main()