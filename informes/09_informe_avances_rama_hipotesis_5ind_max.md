# Informe 09 — Avances de la rama `hipotesis-5ind-max`: qué se consiguió y qué hay que decidir

Fecha: 2026-09-24 · Rama `hipotesis-5ind-max`, local y sin fusionar, derivada de
`radar-max_Septiembre` (71072a1) · Se presenta al responsable **antes** de decidir la fusión.
Resume los informes 01 a 08, que tienen el detalle.

## 1. En una página

**El problema de partida.** El radar desplegado (agregación MAX, 26 indicadores) coincide con el
radar oficial del DANE lo mismo que responder siempre «Bajo»: accuracy 0.344 y Spearman −0.165.
Además, una auditoría de los Excel de Maicao, Oicatá y Paraguachón mostró que varios indicadores
tomaban su valor de artículos de otro tema.

**Lo que se consiguió en esta rama:**
1. **Una forma de medir si un indicador lee lo que debe**, que el proyecto no tenía. Son 962
   artículos juzgados por dos jueces LLM independientes y ciegos, que coinciden mucho entre sí en
   los indicadores de violencia (kappa 0.87–0.95).
2. **La causa del problema, medida:** el modelo NLI confirma la *forma* de la frase y no su
   *objeto*. Con «osos polares» en lugar del objeto real puntúa casi igual.
3. **Una mejora real para grupos armados, validada en departamentos nuevos:** la precisión sube de
   0.17 a 0.93, y de 0.47 a 0.77 fuera de los lugares de diseño. No está en producción porque
   usa palabras clave, algo que la regla vigente no permite. Queda guardada y lista.
4. **Más de 80 alternativas y un segundo modelo NLI descartados con evidencia**, registrados
   para no repetirlos.
5. **Producción intacta y verificada**, con cada paso documentado en 9 informes y un registro de
   decisiones.

**Lo que no se consiguió.** Ningún indicador cambió en producción y la concordancia con el DANE
sigue igual. Exclusión de beneficios económicos resultó imposible de medir con este corpus
(informe 08).

**Qué se pide decidir:** la fusión, qué hacer con exclusión y la línea de trabajo siguiente (§5).

## 2. Punto de partida

- El radar clasifica los 32 departamentos en Bajo / Medio / Alto a partir de prensa regional. Un
  modelo NLI evalúa 26 frases («hipótesis») en cada artículo. El valor de cada indicador en un
  lugar es el **máximo** entre sus artículos, y el índice es la media de los 26 máximos
  (`src/radar.py:66-71`).
- Con MAX, un solo artículo fija el indicador. La auditoría encontró, por ejemplo:
  - «hombre asesinado a tiros» como máximo de *presencia de grupos armados*;
  - «Unidad de Búsqueda recuperó diez cuerpos» como máximo de *exclusión de beneficios*
    (informe 01, §1).
- Frente al DANE, la versión desplegada da accuracy 0.344, igual que decir siempre «Bajo», y
  Spearman −0.165 (informe 01, §7; recalculado en
  `experimentos/resultados/exclusion/diagnostico_exclusion.log`).

## 3. Avances, uno por uno

### 3.1 Un sistema de evaluación que antes no existía

- **Antes:** la única referencia de calidad era un «estándar de plata» por palabras clave, que
  cubre 2 de los 26 indicadores. Todas las conclusiones de calidad descansaban en esos dos.
- **Ahora:** hay 962 artículos juzgados para 5 indicadores
  (`diagnostico_exclusion.log` §1). El método tiene cuatro piezas:
  - **Dos jueces LLM ciegos** (Claude Sonnet y Claude Opus). No saben qué sistema eligió cada
    artículo y un caso solo cuenta si los dos dicen SÍ. Coinciden mucho en grupos armados,
    conflicto y desplazamiento (kappa 0.87–0.95), moderadamente en rechazo (0.44) y nada en
    exclusión (`experimentos/RESULTADOS_5ind_MAX_r2.md`, `RESULTADOS_modelo_nli.md`). Son
    estables: al rejuzgar 40 artículos ya etiquetados coinciden en el 97–100 % (informes 04 y 07).
  - **Criterios fijados antes de medir** (pre-registro congelado), con una revisión independiente
    al cerrar cada ronda.
  - **Control absurdo:** la misma frase con «osos polares». Detecta cuándo el modelo dice que sí
    sin mirar el contenido.
  - **Comprobación en departamentos no usados para diseñar** (Cauca, Chocó, Cundinamarca).
- **Por qué importa:** cualquier cambio futuro (una frase, un modelo, una regla) se puede evaluar
  en horas con la misma vara, reutilizando lo ya juzgado. La prueba del segundo modelo solo
  necesitó juzgar 22 artículos nuevos (informe 07).

### 3.2 La causa del problema, medida

- Si en la frase se cambia el objeto por algo absurdo, el modelo actual casi no cambia su
  respuesta. «Desplazadas por los osos polares» puntúa como «por la violencia», con máximos de
  1.00/0.98 frente a 0.99/0.98 en Antioquia y Maicao (informe 04, §6). En rechazo, desplazamiento
  y conflicto, la frase absurda supera el corte del radar (0.766) en al menos 3 de los 4 lugares
  y llega a 0.99 (`experimentos/PREREG_modelo_nli.md` §3).
- Esto explica lo que vio la auditoría. El modelo confirma frases del tipo «alguien se opone a
  algo» o «una comunidad fue excluida de algo», y con MAX basta un artículo así para disparar el
  indicador.
- **Por qué importa:** muestra que reescribir las frases no alcanza, y dos rondas lo confirman.
  El problema está en cómo lee el modelo, amplificado por el MAX. Eso ahorra trabajo futuro en
  la dirección equivocada.

### 3.3 Una mejora real, validada y lista, fuera de producción por la regla vigente

- Para *presencia de grupos armados* se probó la frase vigente combinada con una **compuerta de
  palabras clave**: el indicador solo cuenta si el texto nombra un grupo armado (ELN,
  disidencias, Clan del Golfo…).
  - Precisión en los 4 lugares: de 0.17 a **0.93**. En los 4 lugares el máximo queda bien
    puesto: lo fija un caso real o, en Oicatá, que no tiene casos, queda en cero. Antes eso
    ocurría en 2 de 4.
  - En departamentos nuevos: de 0.47 a **0.77**.
  - Nunca subió el control absurdo (log [2026-09-22], fases 5 y 7).
- Con esa mejora se recalibraron los cortes (0.7574 / 0.9233). La clasificación quedó igual (6 /
  19 / 7) y se respetaron las 12 referencias fijas (log [2026-09-22], fase 7).
- Llegó a producción (informe 02) y **se revirtió** el 2026-09-23, cuando se fijó que de cada
  indicador solo se cambia la frase (informe 03). Está guardada en la etiqueta
  `base-26ind-f8-compuerta`.
- **Por qué importa:** es la única forma medida de hacer preciso un indicador bajo MAX. Si algún
  día se revisa la regla, no hay que repetir el trabajo.

### 3.4 Lo que se descartó, con evidencia

| Qué se probó | Resultado | Informe |
|---|---|---|
| Reescritura de 3 indicadores (2026-09-08) | El control absurdo empeora (hasta 2.2 % → 47.8 %): rechazada | log [2026-09-08] |
| Ronda 1: 11 alternativas por indicador, 55 en total (frases, paráfrasis, combinaciones y reglas) | Solo pasa la compuerta de grupos armados | 01 |
| Ronda 2: 25 frases nuevas, solo cambiando la hipótesis | Ninguna llega a 0.60; la mejor da 0.38 y 20 de 25 fallan el control absurdo | 04 |
| Un modelo NLI más grande (`xlm-roberta-large-xnli-anli`, 24 capas frente a 12) | Grupos armados mejora (0.17 → 0.35) pero no llega; conflicto no mejora; rechazado | 06, 07 |

**Por qué importa:** cada intento cuesta horas de GPU y de juicio. Con la evidencia registrada
(`contexto/08_log_decisiones.md`) nadie los repite sin un dato nuevo.

### 3.5 Producción intacta, verificada y trazable

- `src/` es idéntico al de `radar-max_Septiembre`: 26 indicadores, MAX, cortes 0.766 / 0.9233 y
  clasificación 6 / 19 / 7. Las pruebas de integración pasan 10 de 10 (log [2026-09-23], cierre de
  la prueba del modelo).
- Cada paso quedó registrado con su evidencia, incluidos los que se promovieron y se revirtieron.
  Cada estado tiene su etiqueta en git.

### 3.6 Exclusión de beneficios económicos: diagnóstico completo

En 962 artículos juzgados no hay ningún caso confirmado. El modelo le da casi el máximo a todos
los departamentos (0.950–0.998), así que el indicador funciona como una constante. Quitarlo no
cambiaría la clase de ningún departamento. Sigue en el radar a la espera de decisión (informe 08).

## 4. Lo que no se consiguió, y por qué

- **Ningún indicador mejoró en producción.** Con la regla de cambiar solo la frase no se
  encontró ninguna mejora (§3.2), y la única que funcionó está fuera de la regla (§3.3).
- **La concordancia con el DANE no se movió** (0.344 / −0.165). Los 5 indicadores trabajados son
  5 de 26 y cada uno pesa 1/26. Hay además límites que no dependen de las frases:
  - con MAX, el valor de un departamento tiende a subir con su número de artículos (medido con la
    versión anterior de los indicadores, `contexto/09_riesgos_y_limites.md`);
  - una hipótesis registrada pero no medida: los temas de búsqueda del scraping tiran hacia
    conflicto, mientras que el índice oficial parece medir más bien déficit
    (`contexto/07_backlog.md`, punto 3b).
- **Hay fenómenos que la prensa casi no reporta:** rechazo a proyecto tiene 4 casos en los 4
  lugares y exclusión ninguno. Sin casos no se puede medir ni mejorar.

## 5. Qué se pide decidir

1. **Fusión de esta rama en `radar-max_Septiembre`.**
   - No cambia producción: `src/` es idéntico.
   - Añade `experimentos/` (scripts y resultados), `informes/` (01 a 09) y el registro de
     decisiones.
   - Al fusionar hay que ajustar dos reglas de `CLAUDE.md` de esa rama, que dicen que no existe
     `experimentos/`.
2. **Exclusión de beneficios económicos** (opciones en el informe 08): mantenerla (recomendado
   mientras se decide), retirarla o buscar casos en otra fuente.
3. **Si se mantiene la regla de cambiar solo la frase.** Con ella no queda ninguna mejora
   disponible para estos 5 indicadores. La única medida (§3.3) usa palabras clave.
4. **Línea de trabajo siguiente.** Opciones, todas por aprobar:
   - aplicar el método de jueces a los otros 21 indicadores, para saber cuáles fallan bajo MAX.
     Antes hay que escribir la definición de cada indicador para los jueces; el costo son horas
     de jueces (no medido);
   - revisar los temas de búsqueda del scraping (backlog 3b; días de re-scraping);
   - diseñar indicadores de déficit estructural (backlog 3c).

## 6. Limitaciones

- La referencia es de jueces LLM, no humana. Su alto acuerdo la hace creíble, no infalible.
- Los lugares de diseño son 4, dos de ellos pequeños (Oicatá 32 artículos, Paraguachón 77). El
  modelo solo lee el comienzo del artículo, que en el 77 % de los casos no llega al final.
- Con 32 departamentos, diferencias de accuracy menores a ~15 puntos no se distinguen del ruido.

## 7. Cómo revisar la rama

- Leer primero este informe, luego el 05 (consolidado del plan), el 08 (exclusión) y el 07 (prueba
  del modelo). Los informes 01 a 04 tienen el detalle de cada ronda. Todos están en `informes/`,
  con su índice en `informes/README.md`.
- Las decisiones, con su evidencia, están en `contexto/08_log_decisiones.md`. Las tablas, en
  `experimentos/RESULTADOS_*.md`.
- Etiquetas de git:
  - `base-26ind-radar-max`: producción de partida;
  - `base-26ind-f8-compuerta`: versión con la compuerta de grupos armados;
  - `prueba-modelo-nli-rechazado`: historial de la prueba del segundo modelo.

## Trazabilidad

| Dato | Dónde |
|---|---|
| Accuracy 0.344 y Spearman −0.165 | informe 01 §7; `experimentos/resultados/exclusion/diagnostico_exclusion.log` §3 |
| 962 juzgados y acuerdo de los jueces | `diagnostico_exclusion.log` §1; `experimentos/RESULTADOS_5ind_MAX_r2.md`; `experimentos/RESULTADOS_modelo_nli.md` |
| Compuerta de grupos armados (0.17 → 0.93; 0.47 → 0.77; cortes) | `contexto/08_log_decisiones.md` [2026-09-22] fases 5 y 7; informes 01–03 |
| Ronda 2 y modelo NLI | informes 04, 06 y 07 |
| Exclusión | informe 08 |
| `src/` idéntico a `radar-max_Septiembre` | `git diff radar-max_Septiembre hipotesis-5ind-max -- src/` (vacío) |
