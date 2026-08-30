"""
Calculo del radar de riesgo por departamento.

Flujo (version produccion):
- COLUMNAS_BINARIAS: 31 indicadores extraidos por Transformer_optimo.py
  (NLI + NER/regex), agregados por MAXIMO entre articulos por departamento
  (ver exportar_indicadores_transformers_por_departamento en
  Transformer_optimo.py).
- indicador_riesgo = promedio simple de los 31 indicadores, en escala [0,1].
- categoria_riesgo = clasificacion por umbrales fijos sobre indicador_riesgo:
    < 1/3        -> "Bajo"
    1/3 .. 2/3   -> "Medio"
    > 2/3        -> "Alto"

Esta es la unica salida que necesita ver el usuario final: el indicador de
riesgo y su clasificacion por departamento.
"""

from typing import Optional

import numpy as np
import pandas as pd


class CalculadorRadar:
    # Mapeo de periodico -> departamento, usado como respaldo cuando el
    # corpus no trae la columna 'departamento' poblada.
    MAPEO_PERIODICO_DEPARTAMENTO = {
        'El Colombiano': 'Antioquia', 'El Diario': 'Risaralda', 'BC Noticias': 'Caldas', 'El Quindiano': 'Quindío',
        'El País Cali': 'Valle del Cauca', 'Diario Occidente': 'Valle del Cauca', 'Diario del Sur': 'Nariño',
        'Diario del Cauca': 'Cauca', 'Chocó 7 Días': 'Chocó', 'Llano al Mundo': 'Meta', 'Diario de Casanare': 'Casanare',
        'La Voz del Cinaruco': 'Arauca', 'El Morichal': 'Vichada', 'Mi Putumayo': 'Putumayo', 'El Tiempo': 'Cundinamarca',
        'La República': 'Cundinamarca', 'Portafolio': 'Cundinamarca', 'Publimetro': 'Cundinamarca', 'Las2Orillas': 'Cundinamarca',
        'El Heraldo': 'Atlántico', 'El Universal': 'Bolívar', 'El Pilón': 'Cesar', 'El Meridiano': 'Córdoba',
        'Vanguardia': 'Santander', 'Trochando Sin Fronteras': 'Arauca', 'Enlace Television': 'Santander', 'Corrillos': 'Santander'
    }

    # Indicadores cuyo sentido habria que invertir (1 - valor) antes de
    # promediar. Hoy ninguno requiere inversion: las 31 hipotesis estan
    # redactadas como "deficit/riesgo" (a mayor score, mayor riesgo).
    VARS_INVERTIR: set = set()

    # Los 31 indicadores del pipeline v4.2 (8 eventos + 5 posturas +
    # 16 indicadores NLI + 2 NER/regex de ref_entidades).
    COLUMNAS_BINARIAS = [
        'deficit_participacion_comunitaria', 'incentivos_economicos_inequitativos', 'debilidad_institucional', 'danos_ambientales', 'conflictos_socioambientales',
        'desplazamiento_forzado', 'reasentamiento', 'protesta_social', 'amenaza_intimidacion', 'consulta_previa_omitida', 'audiencia_publica_omitida', 'taller_participativo_omitido', 'conflicto_territorial',
        'rechazo_proyecto', 'derechos_vulnerados', 'violacion_derechos_humanos', 'conflicto_activo', 'resistencia_territorial', 'exclusion_comunidades',
        'exclusion_servicios_derechos', 'existencia_grupos_etnicos', 'movimientos_sociales', 'poblacion_afectada', 'exclusion_beneficios_economicos', 'irregularidad_contractual',
        'zonas_proteccion_alimentaria', 'dano_territorios', 'presencia_grupos_armados', 'amenaza_lideres',
        'grupos_etnicos_existentes', 'grupos_armados_existentes',
    ]

    # Umbrales fijos de clasificacion sobre indicador_riesgo (escala [0,1]).
    UMBRAL_BAJO = 1 / 3
    UMBRAL_ALTO = 2 / 3

    def _preparar_tasas_indicadores(self, df_indicadores: pd.DataFrame) -> pd.DataFrame:
        """Agrupa por departamento y promedia cada una de las 31 columnas.

        df_indicadores ya trae 1 fila por departamento (salida de
        exportar_indicadores_transformers_por_departamento, agregada por
        maximo entre articulos), por lo que el groupby().mean() es un
        passthrough; se mantiene por robustez si en el futuro llega mas de
        una fila por departamento.
        """
        if 'departamento' not in df_indicadores.columns:
            raise ValueError("El archivo de indicadores debe contener la columna 'departamento'")
        df = df_indicadores.copy()
        df['departamento'] = df['departamento'].astype(str).str.strip()
        df = df[df['departamento'] != ""]
        for c in self.COLUMNAS_BINARIAS:
            if c not in df.columns:
                df[c] = np.nan
            df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.groupby('departamento')[self.COLUMNAS_BINARIAS].mean().fillna(0.0)

    def _resolver_n_articulos(self, df_radar_base: Optional[pd.DataFrame], index_departamentos: pd.Index) -> pd.Series:
        """Recupera n_articulos por departamento desde df_radar_base, si se provee."""
        n_articulos = pd.Series([np.nan] * len(index_departamentos), index=index_departamentos, dtype=float)
        if df_radar_base is None or df_radar_base.empty:
            return n_articulos
        if 'departamento' not in df_radar_base.columns or 'n_articulos' not in df_radar_base.columns:
            return n_articulos
        base = df_radar_base[['departamento', 'n_articulos']].copy()
        base['departamento'] = base['departamento'].astype(str).str.strip()
        base['n_articulos'] = pd.to_numeric(base['n_articulos'], errors='coerce')
        mapa = base.dropna(subset=['departamento']).drop_duplicates(subset=['departamento']).set_index('departamento')['n_articulos']
        valores = index_departamentos.to_series().map(mapa)
        return valores.astype(float)

    @classmethod
    def _categoria_absoluta(cls, valor: float) -> Optional[str]:
        """Clasificacion por umbrales fijos absolutos sobre indicador_riesgo."""
        if pd.isna(valor):
            return None
        if valor < cls.UMBRAL_BAJO:
            return "Bajo"
        if valor <= cls.UMBRAL_ALTO:
            return "Medio"
        return "Alto"

    def calcular_radar_final(self, df_indicadores: pd.DataFrame, df_radar_base: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Calcula el indicador de riesgo final y su clasificacion por departamento.

        Args:
            df_indicadores: salida de exportar_indicadores_transformers_por_departamento
                (1 fila por departamento, cada columna ya agregada por MAXIMO
                entre articulos; escala [0,1]).
            df_radar_base: opcional, DataFrame con columnas ['departamento',
                'n_articulos'] para anexar el tamano de muestra al reporte.

        Returns:
            DataFrame[departamento, n_articulos, indicador_riesgo, categoria_riesgo]
        """
        df_tasas = self._preparar_tasas_indicadores(df_indicadores)
        cols = [c for c in self.COLUMNAS_BINARIAS if c in df_tasas.columns]

        for c in [c for c in cols if c in self.VARS_INVERTIR]:
            df_tasas[c] = 1 - df_tasas[c]

        indicador_riesgo = df_tasas[cols].mean(axis=1)
        n_articulos = self._resolver_n_articulos(df_radar_base, df_tasas.index)

        out = pd.DataFrame({
            'departamento': df_tasas.index,
            'n_articulos': n_articulos.values,
            'indicador_riesgo': indicador_riesgo.round(4).values,
        })
        out['categoria_riesgo'] = out['indicador_riesgo'].apply(self._categoria_absoluta)
        return out.reset_index(drop=True)
