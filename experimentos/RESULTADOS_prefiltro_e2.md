# Resultados — pre-filtro por indicador, etapa 2 (tramo 1)

Generado por `experimentos/exp_prefiltro_e2.py`; tablas completas en `experimentos/resultados/exp_prefiltro_e2.xlsx`. Pre-registro: `experimentos/PREREG_prefiltro_indicador_e2.md`. Referencia: SÍ de `juez-c` y `juez-d` (`juicio_prefiltro_e2/etiquetas.csv`).

**Veredicto: NO ADOPTAR.** ninguna lista nueva cumple (a)–(d) (§0 i); gana el statu quo. Listas nuevas que cumplen (a)–(d): ninguna; admitidas por el tope: ninguna; configuración final: ninguna (producción actual, cortes 0.7572/0.9233).

## Método

`score' = s × 1[lista ∈ premisa visible]`, V01 = sin compuerta, V08 = con ella; gemela y absurdo total con la misma compuerta. Medibles: los 4 con ≥ 5 SÍ/SÍ; `reasentamiento` y `danos_ambientales` pasan sin filtro (solo trazabilidad). Desarrollo: 4 lugares; holdout: Cauca, Chocó, Cundinamarca. M3 con corte 0.7572 (0.766 en columnas aparte).

## Inclusión (a)–(d) (hojas `I_inclusion`, `I_holdout_b`, `I_control_c`, `M_metricas`)

| indicador | M2 lug. V01 | M2 lug. V08 | (a) Δ | (a) | (b) Δ holdout | cobertura mín. | (b) | (c) | M3 nuevas | (d) | entra |
|---|---|---|---|---|---|---|---|---|---|---|---|
| amenaza_lideres | 0.0250 | 0.0750 | 0.0500 | no | 0.1000 | 1.0000 | sí | no | 0 | sí | no |
| amenaza_intimidacion | 0.2750 | 0.7000 | 0.4250 | sí | 0.2667 | 1.0000 | sí | no | 0 | sí | no |
| protesta_social | 0.7393 | 0.7768 | 0.0375 | no | 0.2000 | 1.0000 | sí | sí | 1 | no | no |
| violacion_derechos_humanos | 0.0500 | 0.1750 | 0.1250 | no | 0.0000 | 1.0000 | no | no | 1 | no | no |

(c): diferencia de la brecha media «MAX real − MAX control» (con − sin máscara); exigido ≥ −5e-5 en las cuatro:

| indicador | gemela, lugares | total, lugares | gemela, holdout | total, holdout | (c) |
|---|---|---|---|---|---|
| amenaza_lideres | -0.03515 | 0.08585 | 0.18113 | 0.09288 | no |
| amenaza_intimidacion | -0.11386 | 0.01020 | 0.06461 | 0.16896 | no |
| protesta_social | 0.00000 | 0.15250 | 0.06937 | 0.28841 | sí |
| violacion_derechos_humanos | 0.15500 | -0.03488 | 0.02038 | 0.32134 | no |

Violaciones de M3 (sin → con filtro) en los 7 lugares: amenaza_lideres 2→1; amenaza_intimidacion 0→0; protesta_social 0→1; violacion_derechos_humanos 0→1.

## Tope (§5) y radar combinado (§6) (hojas `T_tope`, `R_base`, `R_configs`, `R_cadena`)

Ninguna lista cumple (a)–(d): no hay nada que topar ni combinar.

Producción actual (base): cortes 0.7572/0.9233, Spearman DANE -0.0913, tamaño +0.8640, 0 anclas rotas, clases 6/19/7. Cada lista sola y la cadena de retirada (solo la cadena decide):

| paso | nuevas | cortes | anclas_rotas | Spearman DANE | Spearman tamaño | clases_B/M/A | 0 anclas | DANE ≥ −0.0913 | tamaño ≤ 0.8640 | pasa | máx |Δ radar| |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sola | amenaza_lideres | 0.7450/0.9233 | 0 | -0.1085 | 0.8702 | 6/19/7 | sí | no | no | no | 0.0173 |
| sola | amenaza_intimidacion | 0.7572/0.9230 | 0 | -0.1015 | 0.8666 | 6/19/7 | sí | no | no | no | 0.0272 |
| sola | protesta_social | 0.7559/0.9093 | 0 | -0.0960 | 0.8666 | 6/18/8 | sí | no | no | no | 0.0114 |
| sola | violacion_derechos_humanos | 0.7541/0.9233 | 0 | -0.0872 | 0.8658 | 6/19/7 | sí | sí | no | no | 0.0074 |

## Impacto (hojas `F_*`)

Sin lista nueva admitida no se calcula impacto (radar y lugares idénticos a producción).

## Trazabilidad del MAX (§7) (hojas `Z_trazabilidad`, `Z_resumen`)

MAX fijado por un artículo con referencia SÍ, en 7 lugares por indicador (M1 = el artículo del MAX es positivo):

| indicador | medible | SÍ sin | NO sin | MAX=0 sin | M1 sin | SÍ con | NO con | MAX=0 con | M1 con |
|---|---|---|---|---|---|---|---|---|---|
| reasentamiento | no | 0 | 7 | 0 | 0 | 1 | 3 | 3 | 4 |
| amenaza_lideres | sí | 2 | 5 | 0 | 2 | 2 | 5 | 0 | 2 |
| amenaza_intimidacion | sí | 2 | 5 | 0 | 2 | 4 | 2 | 1 | 5 |
| protesta_social | sí | 4 | 3 | 0 | 4 | 5 | 2 | 0 | 5 |
| violacion_derechos_humanos | sí | 0 | 7 | 0 | 0 | 1 | 5 | 1 | 1 |
| danos_ambientales | no | 0 | 6 | 1 | 1 | 1 | 4 | 2 | 3 |

Total 6 indicadores × 7 lugares = 42 MAX: fijados por artículo SÍ 8 sin filtro y 14 con filtro. En los 4 medibles (28): 8 → 12.

## Salvedades y desviaciones

- Referencia = SÍ de los dos jueces sobre el pool (top-10 de V01 ∪ V08); un artículo fuera del pool cuenta como no juzgado y como negativo en M1/M2 (cota superior en el xlsx). Cobertura de los top-k: 100 %.
- (a) y (b) se recalculan con la referencia de este pool (no hay valores congelados previos para estos indicadores).
- Se evalúan (a)–(d) en los 4 medibles aunque alguno falle antes; `entra` exige las cuatro. Si un top-k tiene k = 0 no entra en la cobertura mínima (nada que juzgar).
- La compuerta se calcula con `premisa_visible_prod` (hipótesis de cada indicador) para las 2 listas de producción y las 6 nuevas; `PREFILTRO_OBJETO` leído de `src/` sin importarlo.
- Desigualdades de §6 a 4 decimales frente a −0.0913 y 0.8640; «sin cortes válidos» cuenta como fallo del criterio 1.
- M1 en la trazabilidad sigue la definición de M1: con MAX = 0 es verdadero si el lugar no tiene positivos (por eso `con filtro` puede subir M1 sin que el radar muestre un artículo).
- Las configuraciones «sola» del radar son informativas: no se evaluaron con (a)–(d) como decisión y la cadena solo corre con listas admitidas.
- n = 32 en el radar; con solo 3 departamentos de holdout y pocos positivos por celda, un pase de (b) es débil (PREREG §11).
- Desviaciones del pre-registro: ninguna de fondo. Orden de retirada en empates: menor ganancia en lugares y luego el último alfabéticamente (lectura conservadora de «desempate como en §5»).

## Sanidad (hoja `S_sanidad`)

11 de 11 chequeos OK.
