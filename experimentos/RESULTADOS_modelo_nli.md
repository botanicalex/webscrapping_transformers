# Resultados — prueba del modelo NLI alternativo, etapa 2 (4 lugares, SOLO PRUEBAS)

Generado por `experimentos/exp_modelo_nli_etapa2.py metricas`; detalle en `experimentos/resultados/juicio_modelo_nli/metricas_modelo_nli.xlsx`. Pre-registro `experimentos/PREREG_modelo_nli.md` (congelado). Etapa 1: `experimentos/resultados/modelo_nli/etapa1_filtro.log`.

Una sola variable: el modelo. **Nuevo** = `vicgalle/xlm-roberta-large-xnli-anli` (85981da); **actual** = `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` (producción). Misma frase vigente, misma fórmula, sesgo de cada modelo, MAX por lugar.

Referencia: 962 artículos juzgados (940 de las rondas 1–2 + 22 nuevos del pool de esta etapa). Los 40 de control conservan su etiqueta anterior.

M2 = precisión@10 media en los 4 lugares (A/M/O/P = Antioquia/Maicao/Oicatá/Paraguachón); M2+ = solo lugares con positivos; M3 = violaciones de coherencia del MAX; gemela = frase con «osos polares»; absurdo total = «colonias de osos polares».

## `conflicto_territorial` — kappa 0.88 — positivos 11/8/0/3 — no cumple los criterios 1–5

| modelo | M2 | M2+ | M1 (de 4) | M3 viol | máx (A/M/O/P) | máx gemela (A/M/O/P) | absurdo total (A/M/O/P) | M6 |
|---|---|---|---|---|---|---|---|---|
| nuevo | 0.07 | 0.10 | 0 | 1 | 0.94/1.00/0.99/0.98 | 0.47/0.68/0.26/0.43 | 0.51/0.11/0.03/0.00 | — |
| actual | 0.07 | 0.10 | 1 | 1 | 1.00/0.99/0.90/0.99 | 0.95/0.99/0.89/0.72 | 0.38/0.57/0.43/0.21 | — |

M4 (proporción de artículos con gemela > 0.766, A/M/O/P): nuevo 0.000/0.000/0.000/0.000; actual 0.024/0.015/0.062/0.000 (solo reporte).

Criterios (modelo nuevo frente al actual): c1 no, c2 no, c3 sí, c4 no, c5 sí, kappa ≥ 0.4 sí.

Artículo que fija el MAX, actual → nuevo:
- Antioquia: «Nueva asonada en Antioquia: comunidad sacó a 80 militares de Briceño» (1.00, positivo) → «La Agencia Nacional de Tierras está buscando a 10.000 solicitantes de tierra en Antioquia» (0.94, negativo)
- Maicao: «Comunidad bloquea la vía Maicao – Paradero por falta de agua potable y servicio eléctrico» (0.99, negativo) → «“Nace una nueva fuerza de poder en La Guajira”: Katia Ospino durante evento político en Maicao» (1.00, negativo)
- Oicata: «Peaje gratis anoche en la caseta de Tuta #Tolditos7Días» (0.90, negativo) → «Peaje gratis anoche en la caseta de Tuta #Tolditos7Días» (0.99, negativo)
- Paraguachon: «Tensión del lado venezolano por caso judicial afecta comercio binacional» (0.99, negativo) → «Capturan a hombre que conducía vehículo reportado como hurtado en Paraguachón» (0.98, negativo)

## `presencia_grupos_armados` — kappa 0.95 — positivos 45/46/0/5 — no cumple los criterios 1–5

| modelo | M2 | M2+ | M1 (de 4) | M3 viol | máx (A/M/O/P) | máx gemela (A/M/O/P) | absurdo total (A/M/O/P) | M6 |
|---|---|---|---|---|---|---|---|---|
| nuevo | 0.35 | 0.47 | 1 | 0 | 0.96/1.00/0.62/1.00 | 0.60/0.24/0.15/0.16 | 0.51/0.11/0.03/0.00 | 0.877 |
| actual | 0.17 | 0.23 | 2 | 0 | 1.00/0.98/0.65/0.99 | 0.67/0.69/0.65/0.36 | 0.38/0.57/0.43/0.21 | 0.788 |

M4 (proporción de artículos con gemela > 0.766, A/M/O/P): nuevo 0.000/0.000/0.000/0.000; actual 0.000/0.000/0.000/0.000 (solo reporte).

Criterios (modelo nuevo frente al actual): c1 no, c2 no, c3 sí, c4 no, c5 sí, kappa ≥ 0.4 sí.

Artículo que fija el MAX, actual → nuevo:
- Antioquia: «Nueva asonada en Antioquia: comunidad sacó a 80 militares de Briceño» (1.00, positivo) → «Con plantones rechazarán violencia en Bajo Cauca y Nordeste debido al paro minero» (0.96, positivo)
- Maicao: «Maicao fortalece su seguridad con inteligencia y presencia especializada contra el crimen» (0.98, negativo) → «Se reabre frontera y se normaliza paso por Paraguachón en La Guajira» (1.00, negativo)
- Oicata: «Capturan a presunto responsable de millonario hurto en zona rural de Cómbita» (0.65, negativo) → «Capturaron a tres presuntos integrantes de banda dedicada al hurto de viviendas en Boyacá» (0.62, negativo)
- Paraguachon: «Secuestro en La Guajira: voces policiales explican causas, cifras y retos» (0.99, positivo) → «Se reabre frontera y se normaliza paso por Paraguachón en La Guajira» (1.00, negativo)

## Criterio 4: absurdo total por lugar (común a los dos indicadores)

| lugar | máx actual | tope (actual + 0.05) | máx nuevo | artículos nuevos > tope | artículo que fija el máx nuevo |
|---|---|---|---|---|---|
| Antioquia | 0.3787 | 0.4287 | 0.5052 | 1 de 494 | «Celsia sembró más de 13 millones de árboles nativos» |
| Maicao | 0.5705 | 0.6205 | 0.1071 | 0 de 1101 | «Solo tres guajiros fueron becados por Ecopetrol en el 2026» |
| Oicata | 0.4279 | 0.4779 | 0.0253 | 0 de 32 | «En lo que va de diciembre, en Boyacá se han presentado 27 incendios» |
| Paraguachon | 0.2098 | 0.2598 | 0.0000 | 0 de 77 | «En La Guajira reportan normalidad tras cierre preventivo de frontera con Venezuela» |

## Exclusión de beneficios económicos (solo reporte, §4)

SÍ/SÍ en total: **0** (sigue no medible).

## Control entre rondas (40 artículos ya juzgados, solo reporte)

| indicador | acuerdo SI/SI | SI/SI antes | SI/SI ahora |
|---|---|---|---|
| `exclusion_beneficios_economicos` | 1.00 | 0 | 0 |
| `rechazo_proyecto` | 0.97 | 0 | 1 |
| `desplazamiento_forzado` | 1.00 | 1 | 1 |
| `conflicto_territorial` | 0.97 | 2 | 1 |
| `presencia_grupos_armados` | 0.97 | 2 | 3 |
