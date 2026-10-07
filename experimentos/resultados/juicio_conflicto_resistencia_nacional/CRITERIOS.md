# Criterios para jueces (fijados antes de etiquetar)

Para cada artículo (solo el texto que ves; no supongas lo que no dice) responde dos preguntas con SI, NO o DUDOSO,
más una cita literal corta (≤ 20 palabras) del texto que justifique la respuesta (o "" si NO).

## conflicto
¿El texto informa de una **disputa entre dos o más actores identificables** (personas, familias, comunidades,
empresas, grupos armados, Estado/autoridades) **por el control, el uso o la propiedad de tierra o territorio**
(predios, fincas, lotes, baldíos, resguardos, territorios colectivos, zonas bajo control armado)?
- SI: invasión/ocupación de predios con reclamo del dueño o desalojo; litigio o reclamo por propiedad/linderos;
  restitución o despojo de tierras; grupos armados que se disputan el control de una zona; comunidad y empresa o
  Estado en disputa por el uso de un territorio.
- NO: conflictos que no son por tierra/territorio (políticos, laborales, de tránsito, riñas); ocupación del espacio
  público urbano por vendedores; crimen sin disputa territorial; obras o proyectos sin disputa.
- DUDOSO: solo si el texto es ambiguo de verdad.

## resistencia
¿El texto informa de que **una comunidad o grupo de habitantes actúa colectivamente** (protesta, bloqueo, plantón,
minga, marcha, acción legal, consulta, rechazo público organizado) **para defender su territorio, su ambiente o su
comunidad frente a algo externo** (un proyecto, una empresa, una intervención o decisión del Estado o de terceros)?
- SI: comunidad bloquea una vía contra una minera; habitantes protestan contra un relleno sanitario, una
  hidroeléctrica, una erradicación o un desalojo; indígenas exigen consulta previa ante un proyecto.
- NO: protestas por salarios, servicios públicos o inseguridad sin defensa del territorio frente a algo externo;
  acciones de autoridades o empresas (no de la comunidad); campañas institucionales; hechos individuales.
- DUDOSO: solo si el texto es ambiguo de verdad.

Formato de salida: un archivo JSONL por lote, una línea por artículo, mismo `id` del lote:
{"id": "a0000", "conflicto": ["NO", ""], "resistencia": ["SI", "cita literal"]}
