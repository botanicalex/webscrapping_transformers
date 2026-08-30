# -*- coding: utf-8 -*-
"""
Prueba de integración controlada del pipeline radar de prensa.
Cubre 3 departamentos sintéticos (Antioquia, Caldas, Chocó) sin cargar modelos ML.

Checklist de aceptación:
  [1] df_corpus_*.pkl generado y no vacío con columnas requeridas
  [2] df_procesado.pkl presente, no vacío y con columnas de señal
  [3] radar_departamentos.csv/pkl con columnas departamento, radar_propio, categoria_riesgo, n_articulos
  [4] comparacion_radares.xlsx contiene columna experimento_integracion rellena
  [5] resultado_comparacion_radares_<timestamp>.xlsx generado con hojas resumen/
      detalle_por_clase/matrices_confusion/clasificacion_departamentos
  [6] Campos comparacion, accuracy, f1_macro, cohen_kappa, n_departamentos en métricas
  [7] Resumen JSON con claves n_departamentos, articulos_por_departamento, metricas, artefactos
  [8] ValidadorPrecondiciones.etapa_corpus acepta el corpus sintético
  [9] ValidadorPrecondiciones.etapa_salida_no_vacia acepta df_procesado y radar
  [10] evaluar_criterio_parada ejecuta y retorna bool sin excepción

Restricciones de versión respetadas:
  pandas==2.3.3, numpy==2.3.4, openpyxl==3.1.5, matplotlib==3.10.7,
  seaborn==0.13.2, scikit-learn==1.7.2, torch==2.8.0, Python 3.10+
"""

# Fijar backend no-interactivo antes de cualquier import de pyplot
import matplotlib
matplotlib.use("Agg")

import glob
import json
import os
import sys
import tempfile
import unittest
from typing import Any, Dict

import numpy as np
import pandas as pd

import Transformer_optimo as tf
import metricas_y_calculo_de_error as mc
import orquestador_pipeline as orq


# ---------------------------------------------------------------------------
# Constantes de prueba
# ---------------------------------------------------------------------------

DEPARTAMENTOS_TEST = ["Antioquia", "Caldas", "Chocó"]
N_ART_POR_DEPTO = 3
NOMBRE_EXPERIMENTO = "experimento_integracion"

# procesar_metricas_multi_experimento exige al menos 3 departamentos con dato
# valido para calcular metricas (src/metricas_y_calculo_de_error.py); con 2
# la corrida entera se descarta como "sin datos suficientes".
_MIN_DEPARTAMENTOS_METRICAS = 3
assert len(DEPARTAMENTOS_TEST) >= _MIN_DEPARTAMENTOS_METRICAS, (
    "El pipeline de metricas exige minimo "
    f"{_MIN_DEPARTAMENTOS_METRICAS} departamentos con dato valido"
)

# Señales diferenciadas por departamento para que CalculadorRadar produzca
# radar_propio distintos (necesario para que scipy.stats.pearsonr no reciba
# serie constante y pueda calcular).
_SEÑAL = {"Antioquia": 0.8, "Caldas": 0.2, "Chocó": 0.5}


# ---------------------------------------------------------------------------
# Helpers de construcción de datos sintéticos
# ---------------------------------------------------------------------------

def _corpus_sintetico() -> pd.DataFrame:
    filas = []
    for dep in DEPARTAMENTOS_TEST:
        periodico = "El Colombiano" if dep == "Antioquia" else "BC Noticias"
        for i in range(N_ART_POR_DEPTO):
            filas.append(
                {
                    "periodico": periodico,
                    "titulo": f"Artículo {i + 1} de {dep}",
                    "fecha": "2023-06-15",
                    "texto": (
                        f"Texto de prueba sobre conflicto y comunidades en {dep}. "
                        f"Artículo número {i + 1}. Presencia de grupos armados documentada."
                    ),
                    "url": f"http://test-integracion.co/{dep.lower()}/{i + 1}",
                    "departamento": dep,
                    "terminos_encontrado": "conflicto",
                }
            )
    return pd.DataFrame(filas)


def _df_procesado_stub(df_corpus: pd.DataFrame) -> pd.DataFrame:
    """
    Construye un df_procesado válido sin cargar modelos ML.
    Rellena todas las COLUMNAS_BINARIAS con señales distintas por departamento
    para que CalculadorRadar produzca valores diferenciados.
    """
    df = df_corpus.copy()
    for col in tf.CalculadorRadar.COLUMNAS_BINARIAS:
        df[col] = df["departamento"].map(_SEÑAL).astype(float)
    for dim in [
        "score_dim1_gobernanza",
        "score_dim2_capacidad_institucional",
        "score_dim3_vulneracion_socioeconomica",
        "score_dim4_vulnerabilidad_territorial",
        "score_dim5_derechos_humanos_conflicto",
    ]:
        df[dim] = df["departamento"].map(_SEÑAL).astype(float)
    df["sentimiento"] = "neutral"
    df["sentimiento_confianza"] = 0.5
    return df


def _excel_comparacion_sintetico(ruta: str) -> None:
    df = pd.DataFrame(
        {
            "departamento": DEPARTAMENTOS_TEST,
            "radar_oficial_promedio": [40.0, 55.0, 70.0][: len(DEPARTAMENTOS_TEST)],
        }
    )
    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")


# ---------------------------------------------------------------------------
# Caso de prueba de integración
# ---------------------------------------------------------------------------

class TestIntegracionPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        base = cls.tmp.name

        cls.dir_corpus = os.path.join(base, "resultados")
        cls.dir_pipeline = os.path.join(base, "resultados_pipeline")
        cls.dir_metricas = os.path.join(base, "metricas")
        cls.ruta_excel = os.path.join(base, "comparacion_radares.xlsx")

        os.makedirs(cls.dir_corpus, exist_ok=True)
        os.makedirs(cls.dir_pipeline, exist_ok=True)
        os.makedirs(cls.dir_metricas, exist_ok=True)

        # -- [A] Corpus sintético -------------------------------------------------
        df_corpus = _corpus_sintetico()
        df_corpus.to_pickle(os.path.join(cls.dir_corpus, "df_corpus_integracion.pkl"))

        # -- [B] Excel de comparación mínimo -------------------------------------
        _excel_comparacion_sintetico(cls.ruta_excel)

        # -- [C] Validar precondición corpus (componente real) -------------------
        tf.ValidadorPrecondiciones.etapa_corpus(cls.dir_corpus)

        # -- [D] CargadorCorpus (componente real) --------------------------------
        df_cargado = tf.CargadorCorpus(cls.dir_corpus).cargar()

        # -- [E] Stub de PipelineTransformers ------------------------------------
        df_procesado = _df_procesado_stub(df_cargado)
        cls.ruta_procesado_pkl = os.path.join(cls.dir_pipeline, "df_procesado.pkl")
        cls.ruta_procesado_csv = os.path.join(cls.dir_pipeline, "df_procesado.csv")
        df_procesado.to_pickle(cls.ruta_procesado_pkl)
        df_procesado.to_csv(cls.ruta_procesado_csv, index=False)

        # -- [F] Validar salida NLP (componente real) ----------------------------
        tf.ValidadorPrecondiciones.etapa_salida_no_vacia(cls.ruta_procesado_pkl, "NLP")

        # -- [G] CalculadorRadar (componente real) --------------------------------
        df_radar = tf.CalculadorRadar().calcular(df_procesado)
        cls.ruta_radar_pkl = os.path.join(cls.dir_pipeline, "radar_departamentos.pkl")
        cls.ruta_radar_csv = os.path.join(cls.dir_pipeline, "radar_departamentos.csv")
        df_radar.to_pickle(cls.ruta_radar_pkl)
        df_radar.to_csv(cls.ruta_radar_csv, index=False)

        # -- [H] Validar salida radar (componente real) --------------------------
        tf.ValidadorPrecondiciones.etapa_salida_no_vacia(cls.ruta_radar_pkl, "radar")

        # -- [I] Puente radar → Excel (componente real) --------------------------
        orq.actualizar_excel_experimento(
            cls.ruta_excel, cls.ruta_radar_csv, NOMBRE_EXPERIMENTO
        )

        # -- [J] Calcular métricas (componente real) -----------------------------
        cls.resultado_metricas = mc.calcular_metricas(cls.ruta_excel, cls.dir_metricas)

        # -- [K] Resumen final (componente real) ---------------------------------
        cls.resumen = orq.generar_resumen(
            ruta_radar_csv=cls.ruta_radar_csv,
            ruta_procesado_pkl=cls.ruta_procesado_pkl,
            ruta_radar_pkl=cls.ruta_radar_pkl,
            excel_comparacion=cls.ruta_excel,
            resultado_metricas=cls.resultado_metricas,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    # -------------------------------------------------------------------------
    # [1] Corpus
    # -------------------------------------------------------------------------

    def test_01_corpus_pkl_existe_columnas_y_cardinalidad(self) -> None:
        archivos = glob.glob(os.path.join(self.dir_corpus, "df_corpus_*.pkl"))
        self.assertGreaterEqual(len(archivos), 1, "Debe existir al menos un df_corpus_*.pkl")
        df = pd.read_pickle(archivos[0])
        self.assertFalse(df.empty, "El corpus no debe estar vacío")
        self.assertEqual(
            len(df),
            len(DEPARTAMENTOS_TEST) * N_ART_POR_DEPTO,
            f"El corpus debe tener {len(DEPARTAMENTOS_TEST) * N_ART_POR_DEPTO} artículos",
        )
        for col in ["periodico", "titulo", "fecha", "texto", "url", "departamento"]:
            self.assertIn(col, df.columns, f"Corpus debe tener columna '{col}'")

    # -------------------------------------------------------------------------
    # [2] df_procesado
    # -------------------------------------------------------------------------

    def test_02_df_procesado_pkl_no_vacio_y_columnas_señal(self) -> None:
        self.assertTrue(
            os.path.isfile(self.ruta_procesado_pkl), "df_procesado.pkl debe existir"
        )
        self.assertGreater(
            os.path.getsize(self.ruta_procesado_pkl), 0, "df_procesado.pkl no debe tener 0 bytes"
        )
        df = pd.read_pickle(self.ruta_procesado_pkl)
        self.assertFalse(df.empty, "df_procesado no debe estar vacío")
        for col in ["departamento", "texto", "url"]:
            self.assertIn(col, df.columns, f"df_procesado debe tener columna '{col}'")
        presente = [c for c in tf.CalculadorRadar.COLUMNAS_BINARIAS if c in df.columns]
        self.assertGreater(
            len(presente), 0, "df_procesado debe contener al menos una columna de señal"
        )

    # -------------------------------------------------------------------------
    # [3] Radar
    # -------------------------------------------------------------------------

    def test_03_radar_csv_y_pkl_con_columnas_requeridas(self) -> None:
        self.assertTrue(
            os.path.isfile(self.ruta_radar_csv), "radar_departamentos.csv debe existir"
        )
        self.assertTrue(
            os.path.isfile(self.ruta_radar_pkl), "radar_departamentos.pkl debe existir"
        )
        df = pd.read_csv(self.ruta_radar_csv)
        for col in ["departamento", "radar_propio", "categoria_riesgo", "n_articulos"]:
            self.assertIn(col, df.columns, f"Radar debe tener columna '{col}'")
        self.assertEqual(
            set(df["departamento"].tolist()),
            set(DEPARTAMENTOS_TEST),
            "Radar debe contener exactamente los departamentos de prueba",
        )
        self.assertFalse(
            df["radar_propio"].isna().any(), "radar_propio no debe tener NaN"
        )
        n_art = df.set_index("departamento")["n_articulos"]
        for dep in DEPARTAMENTOS_TEST:
            self.assertEqual(
                int(n_art[dep]),
                N_ART_POR_DEPTO,
                f"n_articulos de {dep} debe ser {N_ART_POR_DEPTO}",
            )

    # -------------------------------------------------------------------------
    # [4] Columna experimento en Excel
    # -------------------------------------------------------------------------

    def test_04_excel_tiene_columna_experimento_rellena(self) -> None:
        with pd.ExcelFile(self.ruta_excel, engine="openpyxl") as xl:
            df = xl.parse(xl.sheet_names[0])
        self.assertIn(
            NOMBRE_EXPERIMENTO,
            df.columns,
            f"El Excel debe tener la columna '{NOMBRE_EXPERIMENTO}'",
        )
        n_rellenos = int(df[NOMBRE_EXPERIMENTO].notna().sum())
        self.assertEqual(
            n_rellenos,
            len(DEPARTAMENTOS_TEST),
            "Todos los departamentos de prueba deben tener valor en la columna experimento",
        )

    # -------------------------------------------------------------------------
    # [5] Excel de métricas timestamped
    # -------------------------------------------------------------------------

    def test_05_metricas_excel_timestamped_con_hojas_de_clasificacion(self) -> None:
        # Métrica oficial actual: accuracy de clasificación en terciles (ver CLAUDE.md).
        # MAE/RMSE/Pearson quedaron obsoletos; las hojas correspondientes también.
        excel_salida = self.resultado_metricas.get("excel_salida", "")
        self.assertTrue(
            os.path.isfile(excel_salida),
            f"Excel de métricas timestamped debe existir en '{excel_salida}'",
        )
        self.assertGreater(
            os.path.getsize(excel_salida), 0, "Excel de métricas no debe tener 0 bytes"
        )
        with pd.ExcelFile(excel_salida, engine="openpyxl") as xl:
            for hoja in ("resumen", "detalle_por_clase", "matrices_confusion",
                         "clasificacion_departamentos"):
                self.assertIn(hoja, xl.sheet_names, f"Hoja '{hoja}' debe existir en métricas")

    # -------------------------------------------------------------------------
    # [6] Campos clave en métricas
    # -------------------------------------------------------------------------

    def test_06_metricas_contienen_campos_clave(self) -> None:
        metricas = self.resultado_metricas.get("metricas", [])
        self.assertGreaterEqual(len(metricas), 1, "Debe calcularse al menos un experimento")
        m = metricas[0]
        for campo in ("comparacion", "n_departamentos", "accuracy", "f1_macro", "cohen_kappa"):
            self.assertIn(campo, m, f"Métricas deben incluir el campo '{campo}'")
        self.assertEqual(
            m["n_departamentos"],
            len(DEPARTAMENTOS_TEST),
            "n_departamentos debe coincidir con el número de departamentos de prueba",
        )
        self.assertIsInstance(m["accuracy"], float, "accuracy debe ser float")
        self.assertIsInstance(m["f1_macro"], float, "f1_macro debe ser float")
        self.assertIn(
            "best_accuracy",
            self.resultado_metricas,
            "resultado_metricas debe incluir 'best_accuracy'",
        )

    # -------------------------------------------------------------------------
    # [7] Estructura del resumen JSON
    # -------------------------------------------------------------------------

    def test_07_resumen_json_estructura_correcta(self) -> None:
        for clave in ("n_departamentos", "articulos_por_departamento", "metricas", "artefactos"):
            self.assertIn(clave, self.resumen, f"Resumen debe incluir la clave '{clave}'")
        self.assertEqual(
            self.resumen["n_departamentos"],
            len(DEPARTAMENTOS_TEST),
            "n_departamentos en resumen debe coincidir con departamentos de prueba",
        )
        art = self.resumen["articulos_por_departamento"]
        for dep in DEPARTAMENTOS_TEST:
            self.assertIn(dep, art, f"articulos_por_departamento debe incluir '{dep}'")
            self.assertEqual(int(art[dep]), N_ART_POR_DEPTO)
        artefactos = self.resumen["artefactos"]
        for clave_art in (
            "df_procesado_pkl",
            "radar_pkl",
            "radar_csv",
            "excel_comparacion",
            "excel_resultado",
            "graficos_dir",
        ):
            self.assertIn(clave_art, artefactos, f"Artefactos deben incluir '{clave_art}'")
        try:
            json.dumps(self.resumen, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            self.fail(f"El resumen no es serializable a JSON: {exc}")

    # -------------------------------------------------------------------------
    # [8] ValidadorPrecondiciones — corpus
    # -------------------------------------------------------------------------

    def test_08_validador_precondiciones_corpus_acepta_sintetico(self) -> None:
        try:
            tf.ValidadorPrecondiciones.etapa_corpus(self.dir_corpus)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            self.fail(f"ValidadorPrecondiciones.etapa_corpus falló inesperadamente: {exc}")

    # -------------------------------------------------------------------------
    # [9] ValidadorPrecondiciones — salidas de pipeline
    # -------------------------------------------------------------------------

    def test_09_validador_precondiciones_salidas_pipeline_aceptadas(self) -> None:
        for ruta, etapa in (
            (self.ruta_procesado_pkl, "NLP"),
            (self.ruta_radar_pkl, "radar"),
        ):
            with self.subTest(etapa=etapa):
                try:
                    tf.ValidadorPrecondiciones.etapa_salida_no_vacia(ruta, etapa)
                except (FileNotFoundError, ValueError, RuntimeError) as exc:
                    self.fail(
                        f"ValidadorPrecondiciones.etapa_salida_no_vacia falló para '{etapa}': {exc}"
                    )

    # -------------------------------------------------------------------------
    # [10] Criterio de parada
    # -------------------------------------------------------------------------

    def test_10_criterio_parada_ejecuta_y_retorna_bool(self) -> None:
        try:
            resultado = orq.evaluar_criterio_parada(
                self.resultado_metricas,
                umbral_mape=23.0,
                umbral_error_max=40.0,
            )
        except Exception as exc:
            self.fail(f"evaluar_criterio_parada lanzó excepción inesperada: {exc}")
        self.assertIsInstance(resultado, bool, "evaluar_criterio_parada debe retornar bool")


# ---------------------------------------------------------------------------
# Checklist de aceptación impresa al final
# ---------------------------------------------------------------------------

_CHECKLIST = [
    ("df_corpus_*.pkl generado, no vacío, columnas requeridas", "test_01"),
    ("df_procesado.pkl presente, no vacío, columnas de señal",  "test_02"),
    ("radar_departamentos.csv/pkl con columnas clave",          "test_03"),
    ("Excel contiene columna experimento_integracion rellena",  "test_04"),
    ("Métricas Excel timestamped generado con 4 hojas",         "test_05"),
    ("Campos comparacion/accuracy/f1_macro/cohen_kappa presentes","test_06"),
    ("Resumen JSON con estructura correcta y serializable",     "test_07"),
    ("ValidadorPrecondiciones corpus OK",                       "test_08"),
    ("ValidadorPrecondiciones salidas NLP y radar OK",          "test_09"),
    ("evaluar_criterio_parada retorna bool sin excepción",      "test_10"),
]


def _imprimir_checklist(resultado: unittest.TestResult) -> None:
    fallos: Dict[str, str] = {
        str(t): msg for t, msg in resultado.failures + resultado.errors
    }
    linea = "=" * 64
    print(f"\n{linea}")
    print("  CHECKLIST DE ACEPTACIÓN — INTEGRACIÓN CONTROLADA (3 DEPTOS)")
    print(linea)
    for descripcion, prefijo in _CHECKLIST:
        paso = not any(prefijo in k for k in fallos)
        marca = "PASS" if paso else "FAIL"
        print(f"  [{marca}]  {descripcion}")
    total_fallos = len(resultado.failures) + len(resultado.errors)
    print("-" * 64)
    print(
        f"  Tests ejecutados: {resultado.testsRun}  |  "
        f"Fallos/Errores: {total_fallos}"
    )
    print(linea)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestIntegracionPipeline)
    runner = unittest.TextTestRunner(verbosity=2)
    resultado = runner.run(suite)
    _imprimir_checklist(resultado)
    if resultado.failures or resultado.errors:
        sys.exit(1)
