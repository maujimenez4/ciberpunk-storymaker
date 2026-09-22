---
id: 001-backend-v1
titulo: Plan de implementación — Backend, versión 1
estado: borrador          # borrador | en-revision | aprobado | completado
aprobado_por:             # lo rellena una persona, nunca un agente
fecha: 2026-09-22
spec: spec.md             # aprobada en e4afc47
---

# Plan 001-backend-v1

Cómo se llega desde un repositorio sin código hasta el ciclo completo de una escena, paso a paso y test a test. **Aquí no se decide qué debe hacer el sistema:** eso es la spec, y está cerrada.

---

## Enfoque

Tres ideas gobiernan el orden de todo lo que sigue.

**De abajo arriba, porque el ensamblador es el cuello.** La feature `contexto` es el corazón de la v1 y el único componente cuyo fallo es silencioso. Necesita que existan antes los almacenes que la surten, así que el canon y el ledger van delante. Invertir el orden obligaría a probar el ensamblador contra dobles, que es exactamente donde un fallo de ensamblado se esconde.

**El orquestador, al final.** Es código determinista que coordina piezas que ya funcionan. Escribirlo antes significaría escribir una máquina de estados contra pasos que todavía no existen.

**Una capa horizontal antes que nada.** Configuración, errores, base de datos, migración inicial e inyección de dependencias son de `commons/` y las necesitan todas las features. Sin ellas no hay ni primer test.

Cada paso cabe en un commit verificable por separado, empieza por un test que se ve fallar y nombra los ficheros que toca. Un paso que no quepa en un commit está mal cortado y se parte.

---

## Fases y pasos

Notación: cada paso lleva **el test que falla primero**, el cambio mínimo que lo pone en verde y la feature donde vive. Los requisitos entre paréntesis son los de la spec.

### Fase 0 · Cimientos (`commons/`)

| # | Test en rojo | Cambio mínimo | Requisitos |
| --- | --- | --- | --- |
| P-01 | `test_arranque_falla_si_falta_una_variable_obligatoria` | `commons/config/`: ajustes Pydantic v2, sin valores mágicos | RI-21 |
| P-02 | `test_arranque_rechaza_plazo_de_paso_menor_que_timeout_de_turno` | Validador cruzado en los ajustes | RI-24, D-04 |
| P-03 | `test_context_budget_exceeded_se_traduce_a_422_con_la_capa` (uno por caso) | `commons/errors/`: excepciones de dominio y handler central | RI-11 |
| P-04 | `test_conexion_tiene_wal_foreign_keys_y_busy_timeout` | `commons/db/`: fábrica de conexión | RI-16 |
| P-05 | `test_migracion_inicial_crea_el_esquema_declarado` | Revisión Alembic `0001_inicial` | RD-01 a RD-14 |
| P-06 | `test_migracion_funciona_sin_extension_vectorial` | La misma revisión, sin `vec0` | RD-08, RNF-FIA-03 |
| P-07 | `test_contador_de_tokens_es_local_y_no_estima_por_caracteres` | `commons/llm/`: contador inyectado | RNF-TOK-02, D-07 |
| P-08 | `test_el_doble_de_modelo_sustituye_al_proveedor_en_toda_la_suite` | Cliente de modelo y reloj por `Depends()` | RI-13 |
| P-09 | `test_vector_store_degrada_a_fuerza_bruta_si_la_extension_no_carga` | `VectorStore` + `SqliteVecStore` + `BruteForceStore` | RI-17, RI-22 |
| P-10 | `test_embeddings_legibles_por_ambas_implementaciones` | Formato común, 1024 dimensiones | RD-07, D-02 |
| P-11 | `test_proveedor_de_embeddings_no_cuenta_contra_el_presupuesto` | Interfaz propia de *embeddings* | RI-20 |

### Fase 1 · Dominio puro (`commons/domain/`)

| # | Test en rojo | Cambio mínimo | Requisitos |
| --- | --- | --- | --- |
| P-12 | `test_escena_exige_un_pov_y_un_giro_de_valor_no_nulo` | Modelos de dominio sin framework | RG-08 |
| P-13 | `test_esquema_rechaza_contenido_romantico_con_menor_de_18` | Restricción en el esquema, no en el prompt | RG-09, RNF-SEG-01 |
| P-14 | `lint_imports` falla con un import entre features | Contratos de `import-linter` en `pyproject.toml` | CA-9, §5.1 |

### Fase 2 · `obra` y `outline`

| # | Test en rojo | Cambio mínimo | Requisitos |
| --- | --- | --- | --- |
| P-15 | `test_obra_hereda_persona_tiempo_verbal_pov_y_calor_a_sus_escenas` | Servicio de creación desde `Brief` | RF-OBR-01 |
| P-16 | `test_brief_que_empuja_contra_la_edad_o_el_calor_es_rechazado` | Validación adversaria en esquema | RNF-SEG-06 |
| P-17 | `test_cambiar_la_biblia_crea_version_nueva_y_no_reescribe_escenas` | `VersionDeObra` | RF-OBR-02, 03, RD-12 |
| P-18 | `test_outline_produce_parte_capitulo_escena` | Agente Arquitecto + esquema de salida | RF-OUT-01 |
| P-19 | `test_cada_beat_obligatorio_cae_en_exactamente_una_escena` | Comprobación al generar | RF-OUT-02, RG-06 |
| P-20 | `test_ningun_hito_se_asigna_antes_que_el_que_lo_precede` | Comprobación de orden | RF-OUT-05 |

### Fase 3 · `escena`

| # | Test en rojo | Cambio mínimo | Requisitos |
| --- | --- | --- | --- |
| P-21 | `test_ficha_declara_las_restricciones_duras` | Planificador + `FichaDeEscena` | RF-ESC-01, 02 |
| P-22 | `test_editar_crea_version_nueva_y_marca_la_vigente` | `VersionDeTexto` inmutable | RF-ESC-03, 04 |
| P-23 | `test_tiempo_historia_y_orden_discurso_son_campos_distintos` | Dos relojes | RF-ESC-05, RD-04 |
| P-24 | `test_escena_registra_la_version_de_obra_con_la_que_se_escribio` | Referencia a `VersionDeObra` | RF-ESC-06 |

### Fase 4 · `canon` — la memoria de largo plazo

| # | Test en rojo | Cambio mínimo | Requisitos |
| --- | --- | --- | --- |
| P-25 | `test_ninguna_ruta_actualiza_ni_borra_un_evento_del_ledger` | Ledger *append-only* | RF-CAN-05 |
| P-26 | `test_estado_en_t_se_deriva_y_no_se_escribe_a_mano` | Vista derivada | RF-CAN-06 |
| P-27 | `test_snapshot_cada_cinco_escenas` | *Snapshots* con N = 5 | RF-CAN-06, D-01 |
| P-28 | `test_todo_hecho_de_canon_cita_su_escena_de_origen` | Extractor + grafo | RF-CAN-04 |
| P-29 | `test_corregir_un_hecho_registra_uno_nuevo_y_cita_al_anterior` | Sustitución sin edición | RF-CAN-07 |
| P-30 | `test_un_hecho_sustituido_invalida_los_snapshots_posteriores` | Recálculo desde el último válido | RF-CAN-13 |
| P-31 | `test_escena_rechazada_no_deja_rastro_en_canon_ledger_ni_indice` | Transacción por escena | RF-CAN-02, 03 |
| P-32 | `test_el_conocimiento_se_deriva_de_los_testigos_del_evento` | Derivación de `sabe_desde` | RF-CAN-11 |
| P-33 | `test_resumen_de_escena_al_integrar_y_de_capitulo_al_cerrar` | Cascada de resúmenes | RF-CAN-08 |
| P-34 | `test_el_indice_vectorial_se_reconstruye_entero_desde_el_texto` | Reindexado | RF-CAN-12 |
| P-35 | `test_solo_el_extractor_escribe_memoria_de_largo_plazo` | Permisos por agente | RF-CAN-01 |

### Fase 5 · `contexto` — el ensamblador

Es la fase con más riesgo y la única con **tests basados en propiedades**. Las cuatro propiedades mínimas de la spec son P-39 a P-42.

| # | Test en rojo | Cambio mínimo | Requisitos |
| --- | --- | --- | --- |
| P-36 | `test_nunca_se_llama_al_modelo_sin_contar_antes_los_tokens` | Contador obligatorio en el camino | RNF-TOK-06 |
| P-37 | `test_ninguna_llamada_supera_los_cien_mil_tokens` | Tope duro | RNF-TOK-01 |
| P-38 | `test_cada_capa_respeta_su_tope` | Ensamblado por capas | RF-CTX-02 |
| P-39 | `prop_el_desglose_por_capa_suma_el_total_contado` | Desglose devuelto y persistido | RF-CTX-06 |
| P-40 | `prop_recortar_una_capa_no_altera_las_demas` | Recorte por capa, en el orden declarado | RF-CTX-03 |
| P-41 | `prop_constitucional_e_instruccion_nunca_encogen` | Capas protegidas | RF-CTX-04 |
| P-42 | `prop_o_cabe_o_lanza_context_budget_exceeded` | Nunca truncar por el final | RF-CTX-05 |
| P-43 | `test_una_capa_vacia_falla_antes_de_llamar_al_modelo` | Comprobación de origen por capa | **RF-CTX-14** |
| P-44 | `test_la_reserva_del_diez_por_ciento_queda_libre` | Reserva para el reintento | RF-CTX-11 |
| P-45 | `test_el_paquete_se_reconstruye_entero_en_cada_reintento` | Nada se arrastra | RF-CTX-12 |
| P-46 | `prop_mismo_estado_y_misma_semilla_dan_el_mismo_paquete` | Determinismo | RF-CTX-01 |
| P-47 | `test_recuperacion_filtra_luego_similitud_luego_recencia` | Orden híbrido | RF-CTX-07 |
| P-48 | `test_se_inyecta_muestra_ancla_del_mismo_pov` | `MuestraAncla` | RF-CTX-08 |
| P-49 | `test_lo_recuperado_entra_como_datos_delimitados_no_instrucciones` | Delimitación, con casos adversarios | RNF-SEG-05, CA-12 |

### Fase 6 · `calidad` — los validadores

| # | Test en rojo | Cambio mínimo | Requisitos |
| --- | --- | --- | --- |
| P-50 | `test_ficha_sin_giro_de_valor_es_rechazada` | EST-01 | RF-CAL-01 |
| P-51 | `test_prosa_que_excede_el_nivel_de_calor_es_rechazada` | SEG-01, lista de términos | RF-CAL-02, D-05 |
| P-52 | `test_desplazamiento_imposible_o_dos_lugares_a_la_vez` | CON-01 | RF-CAL-04 |
| P-53 | `test_personaje_usa_informacion_sin_sabe_desde_anterior` | CON-03 | RF-CAL-05 |
| P-54 | `test_contradiccion_de_canon_gana_el_de_menor_orden_discurso` | CAN-01 | RF-CAL-06 |
| P-55 | `test_objeto_perdido_roto_o_destruido_no_se_usa` | CON-02 | RF-CAL-07 |
| P-56 | `test_defecto_lleva_codigo_y_cita_con_desplazamiento_y_literal` | Emisión de `Defecto` | RF-CAL-08, D-06 |
| P-57 | `test_defecto_mal_formado_no_bloquea_ni_consume_reintento` | Comprobación de forma | RF-CAL-11 |
| P-58 | `test_prosa_en_persona_o_tiempo_verbal_distintos_es_rechazada` | **VOZ-03** | **RF-CAL-12** |
| P-59 | `test_g1a_bloquea_y_g1b_no_se_implementa` | Puerta G1a | RF-CAL-09 |
| P-60 | `test_defecto_de_calidad_produce_reparando_nunca_fallida` | Separación defecto/fallo | RF-CAL-10 |

### Fase 7 · `escritura` — el orquestador

| # | Test en rojo | Cambio mínimo | Requisitos |
| --- | --- | --- | --- |
| P-61 | `test_los_diez_estados_y_ninguno_se_salta` | Máquina de estados explícita | RF-ORQ-03 |
| P-62 | `test_el_estado_se_persiste_tras_cada_paso` | Persistir y releer | RF-ORQ-04, 14 |
| P-63 | `test_un_paso_interrumpido_se_repite_entero_sin_duplicar` | Idempotencia por `run_id` | RF-ORQ-06, RNF-FIA-01 |
| P-64 | `test_al_arrancar_se_retoman_los_trabajos_no_terminales` | Reanudación | RF-ORQ-05, CA-3 |
| P-65 | `test_solo_una_llamada_al_modelo_en_vuelo` | Turno único | RNF-TOK-03, RF-ORQ-13 |
| P-66 | `test_sin_turno_la_llamada_espera_y_no_se_recorta_el_paquete` | Espera, no recorte | RNF-TOK-04, CA-8 |
| P-67 | `test_el_turno_se_libera_aunque_el_paso_lance_excepcion` | `finally` en el turno | RF-ORQ-13 |
| P-68 | `test_timeout_de_turno_deja_fallida_sin_coste` | 300 s | RNF-TOK-05, D-03 |
| P-69 | `test_plazo_por_tipo_de_paso` | 30 s / 600 s | RNF-FIA-04, D-04 |
| P-70 | `test_dos_reparaciones_y_a_la_tercera_escalada` | Reparación dirigida | RF-ORQ-07, CA-6 |
| P-71 | `test_escalada_editada_reentra_por_validando` | Reentrada | RF-ORQ-17, D-08 |
| P-72 | `test_aceptar_con_defecto_registra_cual_se_anulo_y_quien` | Aceptación explícita | RF-ORQ-18, CA-13 |
| P-73 | `test_salida_de_agente_que_no_valida_es_fallo_del_paso` | Contrato entre pasos | RF-ORQ-15 |
| P-74 | `test_una_escena_en_vuelo_por_obra_con_cerrojo` | Cerrojo por obra | RF-ORQ-11 |
| P-75 | `test_fallo_de_proveedor_reintenta_tres_veces_con_espera_creciente` | Espera creciente | RNF-FIA-02 |
| P-76 | `test_cancelacion_para_en_el_primer_punto_seguro` | Cancelación | RI-19 |

### Fase 8 · `manuscrito` y la API

| # | Test en rojo | Cambio mínimo | Requisitos |
| --- | --- | --- | --- |
| P-77 | `test_manuscrito_ensambla_vigentes_en_orden_discurso` | Ensamblado | RF-MAN-01, 02 |
| P-78 | `test_toda_operacion_larga_devuelve_trabajo_y_no_bloquea` | Routers y trabajos | RI-01 a RI-09 |
| P-79 | `test_ningun_servicio_lanza_http_exception` | Errores por handler | RI-11 |
| P-80 | `test_toda_ruta_declara_su_modelo_de_respuesta` | OpenAPI como contrato | RI-23, RI-12 |
| P-81 | `test_ejecucion_registra_el_conjunto_completo` | Fila de `ejecucion` | RI-14, RD-06 |
| P-82 | `test_trabajo_expone_estado_intento_causa_y_defectos_con_cita` | Respuesta de RI-09 | RI-18 |
| P-83 | `test_la_traza_no_contiene_prompts_ni_fragmentos_de_manuscrito` | Traza estructural | RNF-OBS-03 |

### Fase 9 · Demostraciones y cierre

Son los criterios marcados **D** en la spec: no los cubre `pytest` solo.

| # | Qué se demuestra | Requisitos |
| --- | --- | --- |
| P-84 | Un capítulo completo, todas las escenas `INTEGRADA` | CA-1, RF-OUT-04 |
| P-85 | Desde una fila de `ejecucion` se reconstruye el mismo paquete | CA-10, RF-CTX-13 |
| P-86 | Con la extensión **ausente del sistema**: arranca, avisa y escribe una escena | CA-11, RI-17 |
| P-87 | Se desactiva cada validación y su test **se ve fallar** | CA-4 |
| P-88 | Métricas de coste, tokens por capa, defectos y latencia | RNF-OBS-01, 02 |
| P-89 | Firma de la inspección de prosa, por nombre y fecha en el Cierre | D-09 |

---

## Fronteras implicadas (`CLAUDE.md` §5)

Features tocadas: `obra`, `outline`, `escena`, `contexto`, `escritura`, `calidad`, `canon`, `manuscrito`, más `commons/`.

**Ningún paso de este plan cruza una frontera.** Todo lo compartido —configuración, errores, base de datos, cliente de modelo, contador, `VectorStore`, modelos de dominio— nace en `commons/` porque lo usan tres o más features desde el primer día, no por anticipación. Lo que una feature necesite de otra entra por su `__init__.py`.

El contrato de `import-linter` se declara en P-14, **antes** que cualquier feature, para que la primera violación rompa la build en vez de descubrirse al final.

Dos puntos donde la tentación de cruzar aparecerá:

- `calidad` necesita canon para contrastar (RF-CAL-06). Entra por el `__init__.py` de `canon`, nunca por su `repository.py`.
- `escritura` orquesta a todas. Es la única que las conoce a todas, y solo por sus índices.

---

## Esquema y migraciones

**Una sola revisión de Alembic**, `0001_inicial`, en P-05. No hay esquema previo que migrar.

Decisiones que la migración debe respetar desde el primer día, porque añadirlas después obliga a reescribir:

- `serie_id` en el canon (RD-11), aunque la v1 maneje una sola obra.
- `version_obra` (RD-12) y la referencia desde `Escena` (RF-ESC-06).
- Tabla `defecto` con `desplazamiento_inicio`, `desplazamiento_fin` y `hecho_canon_id` (RD-14).
- `trabajo` (RD-05), `ejecucion` (RD-06) y `ngrama_vetado` (RD-13).
- Nombres **exactamente** los de `definitions.md` (RD-02).

P-06 la ejecuta **sin** `sqlite-vec` cargado. Si la migración solo pasa con la extensión, el modo degradado no está verificado y la casilla de `verification.md` §7 sigue en parcial.

---

## Presupuesto de contexto

Este plan **no cambia ningún tope**: los implementa por primera vez, tal como están en `CLAUDE.md` §4.1.

| Capa | Tope | Paso que lo prueba |
| --- | --- | --- |
| Constitucional | 5.000 | P-38, P-41 |
| Estructural | 10.000 | P-38 |
| Canon relevante | 20.000 | P-38, P-40 |
| Estado en T | 15.000 | P-38 |
| Continuidad local | 20.000 | P-38 |
| Memoria recuperada | 10.000 | P-38, P-47 |
| Instrucción | 10.000 | P-41 |
| Reserva | 10.000 | P-44 |

Total 100.000. El desglose se persiste en `ejecucion` (P-39, P-81).

---

## Riesgos

**El contador local puede no coincidir con el del proveedor.** D-07 obliga a un contador local para cumplir RNF-REN-01. Si tokeniza distinto que el proveedor, RNF-TOK-01 se puede incumplir *en silencio*: el paquete cabe según nosotros y no según quien factura. Mitigación en P-07: margen explícito y una comprobación periódica contra el recuento que devuelve el proveedor en la respuesta. **Es el riesgo con peor relación entre probabilidad y visibilidad de todo el plan.**

**VOZ-03 puede dar falsos positivos.** Detectar persona y tiempo verbal en castellano por morfología falla con diálogo —un personaje puede hablar en primera persona dentro de una narración en tercera—. Si el validador no excluye lo entrecomillado, bloqueará escenas correctas. Mitigación en P-58: se mide solo sobre narración, y el caso del diálogo es un test propio.

**La extracción del Continuista es probabilística.** `verification.md` §6.2: G1a es mecánica en el contraste, no en la extracción. Ningún paso de este plan mide sus falsos negativos, porque no hay conjunto etiquetado. Queda como está, declarado.

**Voyage añade proveedor y clave.** Si no hay red o falta la clave, P-09 a P-11 y toda la fase 4 dependen de un doble. El arranque falla de inmediato si falta (RI-21), que es lo correcto, pero hace que la puesta en marcha necesite dos claves.

**El orden de las fases concentra el riesgo al final.** El orquestador es la fase 7 y es donde aparecen los fallos de integración. Mitigación: P-84 (capítulo completo) no es el último paso posible sino el primero de la fase 9, y si obliga a volver atrás, se vuelve.

---

## Qué queda fuera de este plan

Lo de «Fuera de alcance» de la spec, sin excepción: Crítico y G1b, métricas de prosa, validación de voz por muestras ancla, Editor de línea, auditoría de manuscrito, puertas G2 y G3, frontend, modo servidor y tests de mutación.

Tampoco entra aquí nada que la spec no pida. Si al implementar aparece algo necesario que no esté en la spec, **se para y se corrige la spec** (§3.4), no se añade un paso.

---

## Desviaciones

Se anotan **antes** de seguir, no al final.

| Fecha | Paso | Qué cambió y por qué |
| --- | --- | --- |
| — | — | — |
