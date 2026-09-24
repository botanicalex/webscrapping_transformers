# 12 — Relevo: prueba de un modelo NLI alternativo (rama de prueba, 2026-09-23)

> **CERRADO (2026-09-23).** Modelo rechazado en la etapa 2 (informe 07); revisión final de
> `orquesta-lead` aprobada. La rama y el worktree se borraron; su historial queda en la etiqueta
> `prueba-modelo-nli-rechazado` y su documentación y resultados en `hipotesis-5ind-max`. Este
> relevo se conserva solo como registro.

Documento de traspaso. **Leerlo entero antes de actuar.** El detalle está en los archivos que
cita; el contexto previo está en `contexto/11_relevo_5ind_MAX.md` (plan 5ind MAX, cerrado).

## 1. Dónde estamos

- **Worktree** `C:\Users\Usuario\Documents\REPOSITORIOS\Web_scrapping_2026\prueba_modelo_nli`,
  rama **`prueba-modelo-nli`** (desde `hipotesis-5ind-max`, 9b14489). **Temporal y solo para
  pruebas**: no se fusiona y `src/` no se toca. Sin push.
- **Pre-registro `experimentos/PREREG_modelo_nli.md` CONGELADO** (710c7be) tras la revisión única
  de `orquesta-lead`: se adoptaron las 12 correcciones. Manda sobre todo lo demás.
- **Modelo descargado y verificado** (autorizado): 5 archivos de la revisión 85981da en
  `~/.cache/huggingface/hub/models--vicgalle--xlm-roberta-large-xnli-anli/snapshots/85981da…/`
  (SHA256 OK). `sentencepiece` 0.2.2 instalado.
- **Chequeos §1–§2 superados:** etiquetas (2, 1, 0) y pares de control; lote 16 (dif 1.9e-06);
  sanidad del script con el modelo de producción (dif 1.0e-05); cobertura sin pérdida.
- **Etapa 1 HECHA** (25 min de GPU): **conflicto pasa el filtro**; rechazo y desplazamiento no;
  grupos armados entra a la etapa 2 por la regla de §4; exclusión solo se reporta. El sesgo del
  modelo nuevo es más alto (media 0.475 frente a 0.364). Tabla en el log [2026-09-23] «etapa 1» e
  informe `informes/06_informe_modelo_nli_etapa1.md`.
- **Etapa 2 HECHA → MODELO RECHAZADO (§5).** Jueces sobre los 62 artículos (22 nuevos + 40 de
  control, acuerdo del control 0.97–1.00). Ni conflicto (M2 0.07, igual que el actual) ni grupos
  armados (M2 0.35 frente a 0.17; M6 0.877) cumplen 1–5: fallan c1, c2 y c4 (absurdo total en
  Antioquia 0.5052 > 0.4287, un solo artículo). Exclusión 0 SÍ/SÍ en 962. No hay etapa 3. Tablas
  en `experimentos/RESULTADOS_modelo_nli.md`, log [2026-09-23] «etapa 2» e informe
  `informes/07_informe_modelo_nli_etapa2.md`.

## 2. Innegociables (del usuario)

- **El modelo nuevo es solo para pruebas.** Nada a `src/`, ninguna promoción, sin fusionar la
  rama. Al final hay un informe y decide el usuario.
- Agregación MAX. **Regla 15:** hipótesis vigentes con su texto idéntico, fórmula y sesgo de
  producción, sin columnas nuevas.
- Producción = solo NLI. El LLM solo juzga, en local. Referencia = SÍ/SÍ de `juez-a` (sonnet) y
  `juez-b` (opus), ciegos.
- No se retira ningún indicador. Sin push ni merge sin aprobación. Todo al log
  (`contexto/08_log_decisiones.md` de esta rama).
- **No proponer consultar a la profesora** (rechazado por el usuario el 2026-09-23).
- Economía de tokens: el orquestador escribe los scripts; subagentes solo `orquesta-lead` (queda
  la revisión final) y los jueces. Nada de Explore ni general-purpose. Resúmenes ≤ 40 líneas.
  GPU una sola vez por corpus y modelo.
- **Contexto:** una conversación por iteración. Al llegar a ~20–23 % de contexto, cerrar en un
  punto limpio (commit, informe si corresponde, este relevo) y entregar el prompt siguiente.
- Informes para el jefe o la profesora en `informes/`: el siguiente es el **08**.

## 3. Pendiente del usuario (fuera de esta prueba)

- `exclusion_beneficios_economicos` «no medible»: qué hacer.
- Fusión de `hipotesis-5ind-max` a `radar-max_Septiembre` (¿entra `experimentos/`?) y push.

## 4. Detalles operativos (no redescubrir)

- **Entorno:** Python 3.11, torch 2.6 cu124, transformers 4.57.3, RTX 4050 (6 GB). Scripts desde
  la raíz del worktree con `PYTHONIOENCODING=utf-8`. Python no valida el certificado de
  huggingface.co (curl sí). El aviso de transformers sobre el «regex de Mistral» al cargar el
  tokenizador es espurio (verificado, ver log).
- **Scripts de esta prueba:**
  - `experimentos/exp_modelo_nli_etapa1.py` `etiquetas|lote|sanidad|cobertura|gpu|filtro`, ya
    corrido. Salidas en `experimentos/resultados/modelo_nli/`; el pkl de scores no se versiona.
  - `experimentos/exp_modelo_nli_etapa2.py` `lotes|consolidar|metricas`, los tres ya corridos
    (logs `etapa2_*.log` en `juicio_modelo_nli/`). `metricas` compara la vigente con el modelo nuevo y con el actual (criterios 1–5 de
    §5, M5 no se calcula) y escribe `experimentos/RESULTADOS_modelo_nli.md` y
    `…/juicio_modelo_nli/metricas_modelo_nli.xlsx`. Comprueba la base contra `candidatas_r2.pkl`
    y M6 = 0.788.
- **Jueces:** Agent tool, `subagent_type: "claude"`, `model` sonnet (juez-a) u opus (juez-b),
  `run_in_background: true`. Prompt: «Eres el agente definido en
  <worktree>/.claude/agents/<juez>.md; léelo primero y síguelo», más la ruta del lote
  (`experimentos/resultados/juicio_modelo_nli/lotes/lote_NN.jsonl`) y la carpeta de salida
  (`experimentos/resultados/juicio_modelo_nli/etiquetas_a` o `etiquetas_b`, mismo nombre de
  archivo). Con 2 lotes: 2 instancias por juez (4 en total), una por lote, en paralelo. Si una se
  corta, retomarla con `SendMessage` a su id. No abrir `mapa_ids.csv` en el prompt de los jueces.
- **Referencia de 940 juzgados:** `juicio_5ind/referencia.csv`,
  `juicio_5ind_holdout/referencia.csv` y `juicio_5ind_r2/referencia.csv` (sin los `control`);
  la carga `exp_modelo_nli_etapa1.referencia()`.
- **Etapa 3 (solo con visto bueno):** 36 hipótesis × 11.439. Según lo medido en la etapa 1, unas
  ~11 min por hipótesis, ~6.7 h (estimado, no medido a escala nacional). Plantilla de cortes:
  `exp_5ind_max_cortes.py`.

## 5. Siguiente paso exacto

La prueba terminó con el rechazo del modelo. Lo que queda depende del usuario:

1. Leer `CLAUDE.md`, este relevo, `experimentos/RESULTADOS_modelo_nli.md` y la entrada
   [2026-09-23] «etapa 2» del log.
2. Con su visto bueno: revisión final única de `orquesta-lead` sobre la prueba completa
   (pre-registro, scripts, etapas 1–2, informes 06–07). Aplicar o registrar como rechazo cada
   corrección y hacer commit. Sin push.
3. Limpieza (§7.6), solo cuando el usuario lo diga. Antes, decidir con él qué se conserva, porque
   la rama no se fusiona: llevar a `hipotesis-5ind-max` solo documentación (entradas del log de la
   prueba, informes 06–07, `PREREG_modelo_nli.md`, `RESULTADOS_modelo_nli.md`), sin `src/`, o
   dejar una etiqueta en la rama antes de borrarla. Luego `git worktree remove
   ../prueba_modelo_nli`, borrar la rama y la caché del modelo (2.24 GB).
