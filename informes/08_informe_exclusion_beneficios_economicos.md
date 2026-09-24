# Informe 08 — Exclusión de beneficios económicos: por qué no se ha podido medir y qué pasa con ella

Fecha: 2026-09-24 · Rama `hipotesis-5ind-max` (local, sin fusionar) · Reúne lo que los informes
01, 04, 05 y 07 dicen por partes sobre este indicador, más un diagnóstico nuevo sin GPU
(`experimentos/exp_exclusion_diagnostico.py`, salida en
`experimentos/resultados/exclusion/diagnostico_exclusion.log`).

## 1. Resumen

- **Qué es.** Uno de los 26 indicadores del radar. Su frase es «Una comunidad quedó excluida de
  los beneficios económicos de un proyecto.» Pesa 1/26 del índice de cada departamento.
- **Por qué no se ha podido medir.** Para saber si un indicador funciona hacen falta casos reales
  con los que comparar. En los 962 artículos juzgados no hay **ningún** caso en que los dos jueces
  coincidan, ni lo hubo en 102 artículos de Antioquia leídos a mano. Se buscó incluso a propósito,
  en todos los artículos que mencionan regalías, compensaciones o consulta previa.
- **Qué hace hoy en el radar.** El modelo le dice que sí a casi todo: vale entre 0.950 y 0.998 en
  los 32 departamentos, y el artículo que fija su valor suele ser de otro tema. En Maicao, por
  ejemplo, es «Unidad de Búsqueda recupera 25 cuerpos en cementerio de Riohacha». Funciona como
  una constante.
- **Efecto medido.** Si se quita, no cambia la clase de ningún departamento: la clasificación
  sigue en 6 Bajo / 19 Medio / 7 Alto, y la concordancia con el DANE queda igual.
- **Situación.** Sigue en el radar con su frase de siempre, porque la decisión del 2026-09-22 fue
  no retirar ningún indicador. Qué hacer con él lo decide el responsable (§7).

## 2. Qué intenta medir

- Frase que evalúa el modelo NLI en cada artículo (`src/Transformer_optimo.py:144`): «Una
  comunidad quedó excluida de los beneficios económicos de un proyecto.»
- Definición que aplican los jueces (`.claude/agents/juez-a.md:34`): *una comunidad no recibe
  regalías, compensaciones o beneficios económicos de un proyecto concreto*. No cuentan la falta
  de servicios, las deportaciones, el hallazgo de cuerpos ni la pobreza en general. El artículo
  tiene que **reportar** el hecho, no basta con que mencione la palabra.
- En el radar, el índice de un departamento es la media simple de los máximos de los 26
  indicadores (`src/radar.py:66-71`). Este indicador aporta 1/26.

## 3. Qué quiere decir «no se ha podido medir»

Con agregación MAX, el valor de un indicador en un lugar lo fija **un solo artículo**, el de
puntaje más alto. Por eso la prueba de si un indicador funciona es si los artículos que pone
arriba reportan de verdad el hecho. Para comprobarlo hacen falta casos reales, confirmados por la
referencia: dos jueces LLM que leen sin saber de dónde viene el artículo y que tienen que decir SÍ
los dos.

El pre-registro de la segunda ronda (`experimentos/PREREG_5ind_MAX_r2.md` §5) fijó de antemano
que con menos de 5 casos confirmados el indicador se declara **«no medible con este corpus»**. En
ese caso no se puede calcular su precisión ni elegir una frase mejor.

«No medible» no significa que la exclusión de beneficios no ocurra en Colombia. Significa que la
prensa regional que tenemos no la reporta de forma que dos lectores independientes coincidan.

## 4. Cómo se buscaron casos: cinco intentos, cero casos confirmados

| Fecha | Búsqueda | Artículos | Casos confirmados | Fuente |
|---|---|---|---|---|
| 2026-09-08 | Lectura manual de una muestra de Antioquia (candidatos por palabras clave más negativos al azar) | 102 | 0 | log [2026-09-08] |
| 2026-09-22 | Ronda 1: los 15 artículos de mayor puntaje por lugar para 12 frases de cada indicador, incluidas las de exclusión | 565 | 0 (juez A: 1 SÍ; juez B: 2 SÍ) | informe 01 |
| 2026-09-22 | Cauca, Chocó y Cundinamarca, con los 15 que la propia frase de exclusión pone arriba en cada uno | 94 | 0 (ningún SÍ de ningún juez) | log [2026-09-22] F7 |
| 2026-09-23 | Ronda 2: **todos** los artículos que mencionan regalías, compensación, consulta previa, indemnización o «no han recibido» (237; 206 sin juzgar), más el resto del pool | 281 | 0 (juez A: 4 SÍ; juez B: 1 SÍ) | informe 04 |
| 2026-09-23 | Prueba de otro modelo NLI: artículos nuevos que ese modelo pone arriba | 22 | 0 | informe 07 |
| **Total juzgado** | | **962** | **0** | `diagnostico_exclusion.log` §1 |

En los 962 artículos, el juez A dijo SÍ 5 veces y el juez B 3 veces, **nunca en el mismo
artículo**. Hay 18 artículos con al menos un SÍ o un DUDOSO
(`experimentos/resultados/exclusion/casos_dudosos.csv`).

## 5. Por qué no aparecen casos

**1. La prensa casi no lo cuenta así.** El concepto exige tres cosas a la vez: un proyecto
concreto, una comunidad y la afirmación de que esa comunidad no recibe sus beneficios. Los 18
casos dudosos son otra cosa:

- columnas de opinión sobre regalías que «no llegan» a La Guajira;
- municipios que pierden regalías porque se va una petrolera (Caquetá);
- comunidades que *reclaman* compensaciones en un peaje (Tuta) o en un relleno sanitario;
- familias que no recibieron un pago de un programa de sustitución de cultivos (Nariño).

**2. Los jueces no coinciden en esos casos grises.** Que alguien *reclame* no confirma que haya
sido excluido. Que un municipio pierda ingresos porque se fue una empresa no es excluir a una
comunidad. Una columna de opinión no es un reporte de hechos. El acuerdo entre jueces es nulo
(kappa −0.00 en las dos rondas, `experimentos/RESULTADOS_5ind_MAX_r2.md`). Ni siquiera la
referencia es estable para este concepto.

**3. El modelo NLI confirma la forma de la frase, no su contenido.** En los 4 lugares de trabajo
(`diagnostico_exclusion.log` §2):

| Lugar | Artículos | Con puntaje > 0.766 | Artículo que fija el valor | Frase con «osos polares» |
|---|---|---|---|---|
| Antioquia | 494 | 122 | «Disidencias de las Farc impusieron "manual de convivencia" en 14 municipios de Antioquia» (0.996) | 0.993 |
| Maicao | 1.101 | 223 | «Unidad de Búsqueda recupera 25 cuerpos en cementerio de Riohacha» (0.996) | 0.994 |
| Oicatá | 32 | 5 | «La Unidad de Búsqueda de Personas recuperó diez cuerpos en el cementerio de Oicatá» (0.989) | 0.900 |
| Paraguachón | 77 | 25 | «Paraguachón, frontera cerrada: así se vive en La Guajira el bloqueo del paso…» (0.994) | 0.984 |

La última columna es el control absurdo: la misma frase con «un criadero de osos polares» en
lugar de «un proyecto». Puntúa casi igual que la real, así que el modelo responde a la *forma* de
la frase («una comunidad quedó excluida de algo»), no a su objeto. Es el mismo defecto hallado en
los otros cuatro indicadores del plan (informe 05, §6). A escala nacional, el 20.3 % de los 11.439
artículos pasa de 0.766 (`diagnostico_exclusion.log` §3).

**4. Cambiar la frase no lo arregla, y sin casos tampoco se puede comprobar.**
- 2026-09-08: una reescritura más concreta empeoró el control absurdo de 2.2 % a 25.8 % y se
  rechazó (log [2026-09-08]).
- Ronda 2: tres frases nuevas y dos paráfrasis sobre regalías y compensaciones dieron precisión
  0.00 (informe 04).
- El otro modelo NLI bajó el control absurdo (0.73/0.97/0.48/0.57), pero sin casos no se puede
  saber si acierta (informe 07).

**Límite adicional:** el modelo y los jueces leen solo el comienzo del artículo, 512 tokens, que
no alcanzan a cubrir el 77 % de los textos (informe 01). Una mención a beneficios al final de una
nota larga se pierde.

## 6. Qué pasa hoy con el indicador

- **Sigue en el radar con su frase vigente.** El 2026-09-22 se recomendó retirarlo y el usuario
  lo revocó: no se retira ningún indicador y el radar sigue con 26. Primero se intenta corregir
  los problemáticos y después se discuten los retiros (log [2026-09-22], «Corrección»).
- **Aporta casi una constante** (`diagnostico_exclusion.log` §3):
  - Su valor va de 0.950 (La Guajira) a 0.998, con mediana 0.994.
  - Su variación entre departamentos es la segunda más baja de los 26: desviación estándar 0.0125.
  - Suma casi lo mismo a todos los departamentos y no ayuda a distinguirlos.
- **Quitarlo no cambiaría el resultado actual.** Se midió el radar con 25 indicadores:
  - el orden de los departamentos es el mismo (Spearman 1.0000 con el de 26);
  - el índice baja 0.0055 en promedio, y como mucho 0.0199;
  - con los cortes vigentes (0.766 / 0.9233) ningún departamento cambia de clase;
  - la accuracy frente al DANE sigue en 0.344 y el Spearman en −0.1653.

## 7. Opciones (decisión del responsable)

| Opción | Qué implica | Costo | Efecto |
|---|---|---|---|
| **A. Mantenerlo como está** (estado actual) | Nada | Ninguno | No cambia la clasificación y el indicador no aporta información |
| **B. Retirarlo del radar** (25 indicadores) | Decisión explícita del responsable. Por la regla de recalibración hay que volver a fijar los cortes y documentarlo | Minutos, sin GPU | Medido: 0 cambios de clase con los cortes actuales. Falta la recalibración formal |
| **C. Fusionarlo con «incentivos económicos inequitativos»** | Se descartó el 2026-09-22 | — | Con MAX, su valor casi fijo (≈ 0.99) taparía a «incentivos», que sí varía entre departamentos (desviación 0.113) |
| **D. Buscar casos en otra fuente** | Scraping dirigido (regalías, compensaciones, consulta previa, empleo local) o lectura humana. Después, evaluar la frase con el mismo método | Días | Solo con ≥ 5 casos se puede saber si la frase funciona. Riesgo: que vuelvan a salir casi ninguno |
| **E. Redefinir el concepto** hacia lo que la prensa sí cuenta, por ejemplo reclamos de comunidades por compensaciones o regalías | Solo se cambia la frase, que la regla permite, pero cambia lo que el indicador significa | Horas de GPU y de jueces | Igual que D: sin casos confirmados no se puede evaluar |

**Recomendación técnica:** mantenerlo (A) mientras se decide, porque hoy no altera la
clasificación. La decisión de fondo es de negocio:
- si el concepto es importante para el proyecto, hay que conseguir casos (D) antes de tocar la
  frase, porque sin casos ninguna frase se puede evaluar;
- si no lo es, retirarlo (B) no cambia ninguna clase y solo exige la recalibración formal de los
  cortes.

## 8. Limitaciones

- La referencia son jueces LLM, no humanos, y para este concepto ni siquiera coinciden entre sí.
- El corpus es prensa regional (11.439 artículos) y se lee solo su comienzo.
- El efecto en el radar se midió con los puntajes de producción ya calculados
  (`datos/scores/scores_v2_32deptos.pkl`), no con un nuevo cálculo en GPU.

## Trazabilidad

| Dato | Dónde |
|---|---|
| Frase, definición y fórmula del radar | `src/Transformer_optimo.py:144`, `.claude/agents/juez-a.md:34`, `src/radar.py:66-71` |
| Búsquedas y recuentos de SÍ | `experimentos/resultados/exclusion/diagnostico_exclusion.log` §1 y `casos_dudosos.csv`; informes 01, 04 y 07 |
| Artículos que fijan el valor y control absurdo | `diagnostico_exclusion.log` §2 (desde `experimentos/resultados/juicio_5ind_r2/candidatas_r2.pkl`) |
| Rango nacional y efecto de quitarlo | `diagnostico_exclusion.log` §3 |
| Decisiones (no retirar, no fusionar, «no medible») | `contexto/08_log_decisiones.md` [2026-09-22] y [2026-09-23] |
