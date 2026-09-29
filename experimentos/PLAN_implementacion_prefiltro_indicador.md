# Plan de implementación en `src/` — pre-filtro por indicador (grupos armados + desplazamiento)

Fecha: 2026-09-29 · Rama: `hipotesis-5ind-max` · Base: la del commit de resultados de la etapa 1 ·
Pre-registro: `experimentos/PREREG_prefiltro_indicador.md` (12c494c) · Resultados:
`experimentos/RESULTADOS_prefiltro_indicador.md` · Log: `contexto/08_log_decisiones.md` [2026-09-29].

**Este plan NO se ha ejecutado: `src/` está intacto.** El veredicto de la etapa 1 es ADOPTAR el mecanismo con dos listas
(`presencia_grupos_armados` y `desplazamiento_forzado`); implementarlo exige la aprobación explícita del usuario (regla 9 y
regla 15, ver «Decisiones que necesito» al final).

## 1. Qué se implementa

Un mecanismo único, dentro de `PipelineTransformers.procesar()`, aplicado antes de puntuar y **sin columnas nuevas**:

- Un diccionario `indicador → regex` con las dos listas congeladas (copias literales de `REGEX_F5` de
  `experimentos/hipotesis_5ind_max.py`, huella `74b2dd699dd0eb35a44efb3215bb8093d46fbebc`; `src/` no importa de `experimentos/`).
- Para cada indicador del diccionario: la **premisa visible con la hipótesis de ese indicador** (el cuerpo recortado a
  `512 − 3 − tokens(hipótesis)`), normalizada (minúsculas, sin tildes); si la regex aparece, el score corregido se conserva; si
  no, se multiplica por 0. Los otros 24 indicadores pasan sin filtro.
- Cortes del radar `0.766/0.9233 → 0.7572/0.9233` (`elegir_cortes` sobre el radar sin redondear, regla 2). La clasificación de
  los 32 departamentos no cambia (6/19/7).

## 2. Cambios por archivo

**`src/Transformer_optimo.py`** (plantilla: el bloque que la F8 añadió tras `_ruta_modelo_local`,
`git show base-26ind-f8-compuerta:src/Transformer_optimo.py`)
1. `import unicodedata`.
2. A nivel de módulo, antes de `class CargadorCorpus`: `PREFILTRO_OBJETO` (el diccionario), sus regex compiladas
   (`_RE_PREFILTRO`), `normalizar()`, `premisa_visible(textos, tokenizer, hipotesis, max_length=512)` y
   `compuerta(premisas, regex)` (devuelve un `np.ndarray` de 1.0/0.0).
3. En `procesar()`, tras calcular `sesgo` y antes del bucle NLI (`# 2. NLI en batch…`): construir `todos` una vez y
   `compuertas = {ind: compuerta(premisa_visible(textos, self.tokenizer_nli, todos[ind]), _RE_PREFILTRO[ind]) for ind in PREFILTRO_OBJETO}`.
   Ojo: `desplazamiento_forzado` vive en `self.eventos` y `presencia_grupos_armados` en `self.indicadores`; por eso se usa `todos[ind]`
   y no `self.indicadores[...]` como hacía la F8.
4. Dentro del bucle, tras el `np.clip` del score corregido: `if clave in compuertas: corregido = corregido * compuertas[clave]`.
   **No** se guarda la compuerta en `df` (a diferencia de la F8, que añadía `compuerta_grupos_armados`): la salida tiene las mismas
   columnas que hoy.
5. Comentario de las líneas 168–175: añadir que el pre-filtro social general sigue retirado (log [2026-08-31] y [2026-09-28]) y que
   existe un pre-filtro por indicador con estas dos listas (log [2026-09-29]).

**`src/config_pipeline.py`** (líneas 90–91): `CORTE_BAJO_MEDIO_RADAR = 0.7572` (`CORTE_MEDIO_ALTO_RADAR` sigue en 0.9233) y el comentario
de origen (huecos naturales del radar con el mecanismo, sin mirar el oficial, 0 anclas rotas).

**`src/test_integracion.py`** — clase nueva `TestPrefiltroPorIndicador`, con las ayudas de la F8 (`_TokenizadorPalabras`,
`object.__new__(tf.PipelineTransformers)` y `_nli_batch` simulado):
- `test_11` los dos textos de regex coinciden con los literales esperados (protege contra deriva de las listas congeladas).
- `test_12` cada compuerta abre con ejemplos positivos y cierra con negativos (grupos armados: ELN, disidencias, Clan del Golfo,
  «frente 36», autodefensas abren; combo, banda, porte ilegal, sicarios, Tren de Aragua no. Desplazamiento: «desplazamiento
  forzado», «familias huyeron», «éxodo», «abandonaron sus hogares» abren; un texto sin esas palabras no).
- `test_13` la compuerta solo mira la premisa visible (un término después del punto de corte no la abre) y esa premisa es la del par
  que arma `_nli_batch`.
- `test_14` `procesar()` con NLI simulado multiplica solo esos dos indicadores; los otros 24 quedan idénticos.
- `test_15` sin columnas nuevas: `set(df_out.columns)` es igual al de hoy (columnas base + 26 indicadores + `sesgo` + 5 dimensiones); el radar y
  los exportadores (`CalculadorRadar`, `COLUMNAS_BINARIAS`) no cambian.
- `test_16` los cortes son 0.7572/0.9233 y un radar sintético se clasifica con ellos. Total esperado: 16 tests (hoy 10).

## 3. Verificación (antes de dar nada por promovido)

1. `python src/test_integracion.py`: 16/16, sin GPU.
2. Equivalencia offline (script nuevo `experimentos/exp_prefiltro_indicador_equivalencia.py`, calco de `exp_5ind_max_f8_equivalencia.py`,
   con el corpus nacional y `scores_v2_32deptos.pkl`): la compuerta de `src/` (truncación de producción) frente a la del experimento
   (esperado: 16 artículos distintos en grupos armados y 4 en desplazamiento, ningún MAX departamental distinto); MAX por departamento
   y `radar_propio` de `CalculadorRadar` iguales al del experimento (`max|dif|` 0); clasificación 6/19/7; `elegir_cortes` devuelve
   0.7572/0.9233 sin romper las 12 anclas.
3. Opcional, con GPU (32 min): volver a correr los 4 lugares con `experimentos/exp_prefiltro_correr_lugares.py` (adaptando la carpeta de
   salida) y comparar con `resultados/tablas_lugares_max_2026-09-28/`. Esperado: solo cambian los MAX de grupos armados y
   desplazamiento; radares Antioquia (2023) 0.9354, Maicao 0.9623, Oicatá 0.6239 y Paraguachón 0.6523, todos en su clase.

## 4. Documentación a actualizar al promover

`CLAUDE.md` (regla 15 con la excepción y su alcance; «Estado técnico»: dos listas y los cortes nuevos), `README.md`,
`explicacion_alexa.md`, `ESTADO_DEL_PROYECTO.md`, `contexto/00_estado_actual.md` y `contexto/11_relevo_5ind_MAX.md`; una entrada de
promoción en `contexto/08_log_decisiones.md`; y el **informe 12**, que se escribe después de la aprobación.

## 5. Orden y reversión

Etiqueta local previa (`base-26ind-prefiltro-indicador-pre`), un commit por bloque (código y cortes; tests; equivalencia; documentación).
Revertir = `git revert` de esos commits; nada de esto toca `datos/`. Sin push ni merge.

## 6. Decisiones que necesito del usuario

1. **Confirmar la excepción a la regla 15** para listas de palabras por indicador calculadas por dentro y sin columnas nuevas (el
   encargo la da por aprobada; conviene que quede confirmada antes de tocar `src/`).
2. **Qué configuración implementar.** (A) grupos armados + desplazamiento (veredicto pre-registrado). (B) solo grupos armados: es la
   F8 sin columna auxiliar, también pasa los tres criterios del radar (Spearman −0.1173; tamaño +0.8695; cortes 0.7574/0.9233) y es
   la opción más conservadora si preocupa la salvedad siguiente.
3. **Aceptar la salvedad del control absurdo de desplazamiento:** su gemela («…por los osos polares») sigue con MAX 0.86–0.99 con y sin filtro;
   pasa el criterio pre-registrado por no empeorar, no por mejorar. Su M2 (0.35 en lugares, 0.567 en holdout) tampoco cumple los
   criterios absolutos de la ronda 1.
4. Si se corre la verificación con GPU (32 min) como parte de la promoción.

## 7. Esfuerzo estimado

Código y cortes, unos 30 minutos; tests, una hora; equivalencia y documentación, una hora; GPU opcional, 32 minutos.
