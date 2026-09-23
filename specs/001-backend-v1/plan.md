---
id: 001-backend-v1
titulo: Plan de implementación — Backend, versión 1
estado: en-revision       # borrador | en-revision | aprobado | completado
aprobado_por: maujimenez4 # lo rellena una persona, nunca un agente
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

Cada paso cabe en un commit verificable por separado, empieza por un test que se ve fallar y dice dónde vive. Un paso que no quepa en un commit está mal cortado y se parte.

---

## Fases y pasos

**Dónde** es la ruta bajo `src/backend/app/`. La correspondencia pieza ↔ carpeta es la de `architecture.md` §3.9 y §5.1.

### Fase 0 · Cimientos (`commons/`)

| # | Test en rojo | Cambio mínimo | Dónde | Req. |
| --- | --- | --- | --- | --- |
| P-01 | `test_arranque_falla_si_falta_una_variable_obligatoria` | Ajustes Pydantic v2, sin valores mágicos | `commons/config/` | RI-21 |
| P-02 | `test_arranque_rechaza_plazo_de_paso_menor_que_timeout_de_turno` | Validador cruzado | `commons/config/` | RI-24, D-04 |
| P-03 | `test_ninguna_clave_se_lee_del_repositorio_ni_de_la_base_de_datos` | Claves solo de entorno | `commons/config/` | RI-15, RNF-SEG-03 |
| P-04 | `test_cada_excepcion_de_dominio_se_traduce_a_su_http` (una por caso) | Excepciones y handler central | `commons/errors/` | RI-11 |
| P-05 | `test_conexion_tiene_wal_foreign_keys_y_busy_timeout` | Fábrica de conexión | `commons/db/` | RI-16 |
| P-06 | `test_migracion_inicial_crea_el_esquema_declarado` | Revisión `0001_inicial` | `alembic/versions/` | RD-01 a RD-14 |
| P-07 | `test_migracion_funciona_sin_extension_vectorial` | La misma revisión, sin `vec0` | `alembic/versions/` | RD-08, RNF-FIA-03 |
| P-08 | `test_contador_de_tokens_es_local_y_no_estima_por_caracteres` | Contador inyectado | `commons/llm/` | RNF-TOK-02, D-07 |
| P-09 | `test_el_doble_de_modelo_sustituye_al_proveedor_en_toda_la_suite` | Cliente y reloj por `Depends()` | `commons/llm/` | RI-13 |
| P-10 | `test_vector_store_degrada_a_fuerza_bruta_si_la_extension_no_carga` | `VectorStore` + dos implementaciones | `commons/db/` | RI-17, RI-22 |
| P-11 | `test_embeddings_legibles_por_ambas_implementaciones` | Formato común, 1024 dimensiones | `commons/db/` | RD-07, D-02 |
| P-12 | `test_embeddings_no_cuentan_contra_ningun_presupuesto` | Interfaz propia de *embeddings* | `commons/llm/` | RI-20 |
| P-13 | `test_los_trabajos_corren_en_el_proceso_de_la_api` | Sin *worker* aparte: el turno es por proceso y repartirlo lo duplicaría | `commons/jobs/` | §2.2 r3, §10 |

### Fase 1 · Dominio y fronteras

| # | Test en rojo | Cambio mínimo | Dónde | Req. |
| --- | --- | --- | --- | --- |
| P-14 | `test_escena_exige_un_pov_y_un_giro_de_valor_no_nulo` | Modelos de dominio sin framework | `commons/domain/` | RG-08 |
| P-15 | `test_esquema_rechaza_contenido_romantico_con_menor_de_18` | Restricción en esquema, no en prompt | `commons/domain/` | RG-09, RNF-SEG-01 |
| P-16 | `lint_imports` falla con un import entre features, con `commons/` importando una feature, y con `commons/domain/` importando FastAPI o SQLAlchemy | Los seis contratos de `architecture.md` §5.2 | `pyproject.toml` | CA-9, §5.2 |
| P-17 | `test_toda_feature_expone_solo_su_init_y_tiene_los_segmentos_declarados` | Esqueleto de las ocho features con los nombres de §5.1 | `features/*/` | §5.1 |

### Fase 2 · `obra` y `outline`

| # | Test en rojo | Cambio mínimo | Dónde | Req. |
| --- | --- | --- | --- | --- |
| P-18 | `test_obra_hereda_persona_tiempo_verbal_pov_y_calor_a_sus_escenas` | Creación desde `Brief` | `features/obra/` | RF-OBR-01 |
| P-19 | `test_brief_que_empuja_contra_la_edad_o_el_calor_es_rechazado` | Validación adversaria | `features/obra/` | RNF-SEG-06 |
| P-20 | `test_cambiar_la_biblia_crea_version_nueva_y_no_reescribe_escenas` | `VersionDeObra` | `features/obra/` | RF-OBR-02, 03, RD-12 |
| P-21 | `test_el_prompt_se_carga_del_fichero_y_su_hash_coincide_con_el_registrado` | Prompts versionados como ficheros; los **carga el orquestador** | `features/*/prompts/` | §5.5, RI-14, CLAUDE §10 |
| P-22 | `test_outline_produce_parte_capitulo_escena` | Arquitecto + esquema de salida | `features/outline/` | RF-OUT-01 |
| P-23 | `test_cada_beat_obligatorio_cae_en_exactamente_una_escena` | Comprobación al generar | `features/outline/` | RF-OUT-02, RG-06 |
| P-24 | `test_ningun_hito_se_asigna_antes_que_el_que_lo_precede` | Comprobación de orden | `features/outline/` | RF-OUT-05 |

### Fase 3 · `escena`

| # | Test en rojo | Cambio mínimo | Dónde | Req. |
| --- | --- | --- | --- | --- |
| P-25 | `test_ficha_declara_las_restricciones_duras` | Planificador + `FichaDeEscena` | `features/escena/` | RF-ESC-01, 02 |
| P-26 | `test_editar_crea_version_nueva_y_marca_la_vigente` | `VersionDeTexto` inmutable | `features/escena/` | RF-ESC-03, 04 |
| P-27 | `test_tiempo_historia_y_orden_discurso_son_campos_distintos` | Dos relojes | `features/escena/` | RF-ESC-05, RD-04 |
| P-28 | `test_escena_registra_la_version_de_obra_con_la_que_se_escribio` | Referencia a `VersionDeObra` | `features/escena/` | RF-ESC-06 |

### Fase 4 · `canon` — la memoria de largo plazo

| # | Test en rojo | Cambio mínimo | Dónde | Req. |
| --- | --- | --- | --- | --- |
| P-29 | `test_ninguna_ruta_actualiza_ni_borra_un_evento_del_ledger` | Ledger *append-only* | `features/canon/` | RF-CAN-05 |
| P-30 | `test_estado_en_t_se_deriva_y_no_se_escribe_a_mano` | Vista derivada | `features/canon/` | RF-CAN-06 |
| P-31 | `test_snapshot_cada_cinco_escenas` | *Snapshots*, N = 5 | `features/canon/` | RF-CAN-06, D-01 |
| P-32 | `test_todo_hecho_de_canon_cita_su_escena_de_origen` | Extractor + grafo | `features/canon/` | RF-CAN-04 |
| P-33 | `test_corregir_un_hecho_registra_uno_nuevo_y_cita_al_anterior` | Sustitución sin edición | `features/canon/` | RF-CAN-07 |
| P-34 | `test_un_hecho_sustituido_invalida_los_snapshots_posteriores` | Recálculo desde el último válido | `features/canon/` | RF-CAN-13 |
| P-35 | `test_escena_rechazada_no_deja_rastro_en_canon_ledger_ni_indice` | Transacción por escena | `features/canon/` | RF-CAN-02, 03 |
| P-36 | `test_extrayendo_escribe_en_el_orden_declarado` | Canon → ledger → resumen → hilos → *embeddings*, en una transacción | `features/canon/` | §4.4, RF-CAN-03 |
| P-37 | `test_no_se_compactan_constitucional_hechos_de_canon_ni_ledger` | El olvido es de selección, no de destrucción | `features/canon/` | RF-CAN-09, §4.5 |
| P-38 | `test_el_conocimiento_se_deriva_de_los_testigos_del_evento` | Derivación de `sabe_desde` | `features/canon/` | RF-CAN-11 |
| P-39 | `test_resumen_de_escena_al_integrar_y_de_capitulo_al_cerrar` | Cascada de resúmenes | `features/canon/` | RF-CAN-08 |
| P-40 | `test_el_indice_vectorial_se_reconstruye_entero_desde_el_texto` | Reindexado | `features/canon/` | RF-CAN-12 |
| P-41 | `test_el_extractor_escribe_la_lista_negra_de_ngramas` | Tabla `ngrama_vetado`. **Nadie la lee en la v1**: su consumidor es el Editor de línea | `features/canon/` | RD-13, §4.3 |
| P-42 | `test_solo_el_extractor_escribe_memoria_de_largo_plazo` | Permisos de escritura | `features/canon/` | RF-CAN-01 |

### Fase 5 · `contexto` — el ensamblador

La fase con más riesgo y la única con **tests basados en propiedades**. Las cuatro propiedades mínimas de la spec son P-48, P-49, P-51 y P-52.

| # | Test en rojo | Cambio mínimo | Dónde | Req. |
| --- | --- | --- | --- | --- |
| P-43 | `test_nunca_se_llama_al_modelo_sin_contar_antes_los_tokens` | Contador obligatorio en el camino | `features/contexto/` | RNF-TOK-06 |
| P-44 | `test_ninguna_llamada_supera_los_cien_mil_tokens` | Tope duro | `features/contexto/` | RNF-TOK-01 |
| P-45 | `test_cada_capa_respeta_su_tope` | Ensamblado por capas | `features/contexto/` | RF-CTX-02 |
| P-46 | `test_cada_capa_sale_del_almacen_que_le_corresponde` | Correspondencia capa ↔ almacén | `features/contexto/` | §4.8 |
| P-47 | `test_continuidad_local_lleva_la_n_menos_1_integra_y_la_n_menos_2_resumida` | Ventana de trabajo | `features/contexto/` | §4.2 |
| P-48 | `prop_el_desglose_por_capa_suma_el_total_contado` | Desglose devuelto y persistido | `features/contexto/` | RF-CTX-06 |
| P-49 | `prop_recortar_una_capa_no_altera_las_demas` | Recorte por capa | `features/contexto/` | RF-CTX-03 |
| P-50 | `test_dentro_de_cada_capa_se_recorta_lo_declarado_primero` | Beats lejanos; mencionados no presentes; conocimientos ya usados; N-2 antes que N-1; menor puntuación | `features/contexto/` | §2.1, RF-CTX-03 |
| P-51 | `prop_constitucional_e_instruccion_nunca_encogen` | Capas protegidas | `features/contexto/` | RF-CTX-04 |
| P-52 | `prop_o_cabe_o_lanza_context_budget_exceeded` | Nunca truncar por el final | `features/contexto/` | RF-CTX-05 |
| P-53 | `test_una_capa_vacia_falla_antes_de_llamar_al_modelo` | Comprobación de origen por capa | `features/contexto/` | **RF-CTX-14** |
| P-54 | `test_la_reserva_del_diez_por_ciento_queda_libre` | Reserva para el reintento | `features/contexto/` | RF-CTX-11 |
| P-55 | `test_el_paquete_se_reconstruye_entero_en_cada_reintento` | Nada se arrastra | `features/contexto/` | RF-CTX-12 |
| P-56 | `prop_mismo_estado_y_misma_semilla_dan_el_mismo_paquete` | Determinismo | `features/contexto/` | RF-CTX-01 |
| P-57 | `test_recuperacion_filtra_luego_similitud_luego_recencia` | Orden híbrido | `features/contexto/` | RF-CTX-07 |
| P-58 | `test_se_inyecta_muestra_ancla_del_mismo_pov` | `MuestraAncla` | `features/contexto/` | RF-CTX-08 |
| P-59 | `test_lo_recuperado_entra_como_datos_delimitados_no_instrucciones` | Delimitación, casos adversarios | `features/contexto/` | RNF-SEG-05, CA-12 |

### Fase 6 · `calidad` — los validadores

| # | Test en rojo | Cambio mínimo | Dónde | Req. |
| --- | --- | --- | --- | --- |
| P-60 | `test_ficha_sin_giro_de_valor_es_rechazada` | EST-01 | `features/calidad/` | RF-CAL-01 |
| P-61 | `test_prosa_que_excede_el_nivel_de_calor_es_rechazada` | SEG-01, lista de términos | `features/calidad/` | RF-CAL-02, D-05 |
| P-62 | `test_desplazamiento_imposible_o_dos_lugares_a_la_vez` | CON-01 | `features/calidad/` | RF-CAL-04 |
| P-63 | `test_personaje_usa_informacion_sin_sabe_desde_anterior` | CON-03 | `features/calidad/` | RF-CAL-05 |
| P-64 | `test_contradiccion_de_canon_gana_el_de_menor_orden_discurso` | CAN-01 | `features/calidad/` | RF-CAL-06 |
| P-65 | `test_objeto_perdido_roto_o_destruido_no_se_usa` | CON-02 | `features/calidad/` | RF-CAL-07 |
| P-66 | `test_defecto_lleva_codigo_y_cita_con_desplazamiento_y_literal` | Emisión de `Defecto` | `features/calidad/` | RF-CAL-08, D-06 |
| P-67 | `test_defecto_mal_formado_no_bloquea_ni_consume_reintento` | Comprobación de forma | `features/calidad/` | RF-CAL-11 |
| P-68 | `test_prosa_en_persona_o_tiempo_verbal_distintos_es_rechazada` | **VOZ-03**, solo sobre narración | `features/calidad/` | **RF-CAL-12** |
| P-69 | `test_g1a_bloquea_y_g1b_no_se_implementa` | Puerta G1a | `features/calidad/` | RF-CAL-09 |
| P-70 | `test_defecto_de_calidad_produce_reparando_nunca_fallida` | Defecto ≠ fallo técnico | `features/calidad/` | RF-CAL-10 |

### Fase 7 · `escritura` — el orquestador

| # | Test en rojo | Cambio mínimo | Dónde | Req. |
| --- | --- | --- | --- | --- |
| P-71 | `test_los_diez_estados_y_ninguno_se_salta` | Máquina de estados explícita | `commons/jobs/` | RF-ORQ-03 |
| P-72 | `test_ningun_agente_invoca_a_otro` | Topología en estrella | `features/escritura/` | RF-ORQ-02, §3.1 |
| P-73 | `test_ningun_agente_accede_a_almacenes_ficheros_ni_red` | Permisos de §3.5; el Escritor solo ve el paquete | `features/escritura/` | RF-ORQ-16, §3.5 |
| P-74 | `test_el_estado_se_persiste_tras_cada_paso_y_se_vuelve_a_leer` | Persistir y releer, no encadenar objetos | `commons/jobs/` | RF-ORQ-04, 14 |
| P-75 | `test_un_paso_interrumpido_se_repite_entero_sin_duplicar` | Idempotencia por `run_id` | `commons/jobs/` | RF-ORQ-06, RNF-FIA-01 |
| P-76 | `test_al_arrancar_se_retoman_los_trabajos_no_terminales` | Reanudación | `commons/jobs/` | RF-ORQ-05, CA-3 |
| P-77 | `test_solo_una_llamada_al_modelo_en_vuelo` | Turno único | `commons/jobs/` | RNF-TOK-03, RF-ORQ-13 |
| P-78 | `test_sin_turno_la_llamada_espera_y_no_se_recorta_el_paquete` | Espera, no recorte | `commons/jobs/` | RNF-TOK-04, CA-8 |
| P-79 | `test_el_turno_se_libera_aunque_el_paso_lance_excepcion` | Liberación garantizada | `commons/jobs/` | RF-ORQ-13 |
| P-80 | `test_timeout_de_turno_deja_fallida_sin_coste` | 300 s | `commons/jobs/` | RNF-TOK-05, D-03 |
| P-81 | `test_plazo_por_tipo_de_paso` | 30 s código / 600 s modelo | `commons/jobs/` | RNF-FIA-04, D-04 |
| P-82 | `test_dos_obras_a_la_vez_serializan_sus_llamadas_al_modelo` | Paralelismo de trabajo, no de llamadas | `commons/jobs/` | §3.8 |
| P-83 | `test_dos_reparaciones_y_a_la_tercera_escalada` | Reparación dirigida con cita | `features/escritura/` | RF-ORQ-07, 08, CA-6 |
| P-84 | `test_escalada_editada_reentra_por_validando` | Reentrada | `features/escritura/` | RF-ORQ-17, D-08 |
| P-85 | `test_aceptar_con_defecto_registra_cual_se_anulo_y_quien` | Aceptación explícita | `features/escritura/` | RF-ORQ-18, CA-13 |
| P-86 | `test_salida_de_agente_que_no_valida_es_fallo_del_paso` | Contrato entre pasos | `features/escritura/` | RF-ORQ-15 |
| P-87 | `test_una_escena_en_vuelo_por_obra_con_cerrojo` | Cerrojo por obra, sin fiar en `busy_timeout` | `commons/jobs/` | RF-ORQ-11 |
| P-88 | `test_fallo_de_proveedor_reintenta_tres_veces_con_espera_creciente` | Espera creciente; el límite de tasa es fallo de proveedor | `commons/llm/` | RNF-FIA-02, §2.2 r4 |
| P-89 | `test_cancelacion_para_en_el_primer_punto_seguro` | Cancelación | `commons/jobs/` | RI-19 |

### Fase 8 · `manuscrito`, API y observabilidad

| # | Test en rojo | Cambio mínimo | Dónde | Req. |
| --- | --- | --- | --- | --- |
| P-90 | `test_manuscrito_ensambla_vigentes_en_orden_discurso` | Ensamblado y autoría | `features/manuscrito/` | RF-MAN-01, 02 |
| P-91 | `test_toda_operacion_larga_devuelve_trabajo_y_no_bloquea` | Routers que solo crean el trabajo | `features/*/router.py` | RI-01 a RI-09 |
| P-92 | `test_ningun_servicio_lanza_http_exception` | Errores por handler | `features/*/service.py` | RI-11, §5.2 r4 |
| P-93 | `test_toda_ruta_declara_su_modelo_de_respuesta` | OpenAPI como contrato; entrada ≠ salida | `features/*/` | RI-23, RI-12 |
| P-94 | `test_ejecucion_registra_el_conjunto_completo` | Fila por llamada | `commons/db/` | RI-14, RD-06 |
| P-95 | `test_trabajo_expone_estado_intento_causa_y_defectos_con_cita` | Respuesta de RI-09 | `features/escritura/` | RI-18 |
| P-96 | `test_la_traza_no_contiene_prompts_ni_fragmentos_de_manuscrito` | Traza estructural | `commons/config/` | RNF-OBS-03 |
| P-97 | `test_se_cuenta_la_tasa_de_defectos_mal_formados` | Es hoy la **única** señal que mide al Continuista (`verification.md` §6.3) | `commons/config/` | §9, RF-CAL-11 |
| P-98 | `test_se_miden_el_tiempo_de_espera_por_turno_y_las_esperas_vencidas` | Métricas de concurrencia | `commons/jobs/` | RNF-OBS-02, §9 |

### Fase 9 · Demostraciones y cierre

Los criterios marcados **D** en la spec: no los cubre `pytest` solo.

| # | Qué se demuestra | Req. |
| --- | --- | --- |
| P-99 | Un capítulo completo, todas las escenas `INTEGRADA` | CA-1, RF-OUT-04 |
| P-100 | Desde una fila de `ejecucion` se reconstruye el mismo paquete | CA-10, RF-CTX-13 |
| P-101 | Con la extensión **ausente del sistema**: arranca, avisa y escribe una escena | CA-11, RI-17 |
| P-102 | Se desactiva cada validación y su test **se ve fallar** | CA-4 |
| P-103 | Coste por escena, tokens medios por capa, defectos por código, latencia por fase | RNF-OBS-01 |
| P-104 | Firma de la inspección de prosa, por nombre y fecha en el Cierre | D-09 |

---

### Fase 10 · Cerrar lo que quedó abierto

El plan se dio por completado el 2026-09-22 y no lo estaba. Esta fase no añade
alcance: son los requisitos que la spec **ya pedía** y que las fases 5 a 8
dejaron sin cumplir, más la limpieza de lo que D-02 dejó muerto. Aprobada por
maujimenez4 el 2026-09-22.

| # | Test en rojo | Cambio mínimo | Dónde | Req. |
| --- | --- | --- | --- | --- |
| P-105 | `test_los_ajustes_declaran_exactamente_lo_que_pide_ri_21` | Fuera las tres credenciales y `dimension_embeddings` | `commons/config/` | RI-21 |
| P-106 | `test_el_modelo_del_cliente_sale_de_los_ajustes` | `ClienteDeClaudeCode` deja de fijar `"haiku"` a fuego | `commons/llm/` | RI-21, RI-13 |
| P-107 | `test_los_ajustes_no_declaran_ninguna_credencial` | Decisión (a): la credencial es la sesión del CLI y vive fuera | `commons/config/` | RI-15, RNF-SEG-03 |
| P-108 | `test_los_almacenes_leen_cada_capa_de_su_repositorio` | La clase que implementa `Almacenes` contra los repositorios | `features/contexto/repository.py` | §4.8, RF-CTX-02 |
| P-109 | `test_el_canon_de_la_escena_n_aparece_en_el_contexto_de_la_n_mas_1` | La prueba de que el bucle de memoria se cierra | `features/contexto/` | RF-CAN-01, §4.8 |
| P-110 | `test_ninguna_capa_con_origen_llega_vacia_con_almacenes_reales` | RF-CTX-14 contra la base de datos, no contra dobles | `features/contexto/` | RF-CTX-14 |
| P-111 | `test_el_ciclo_de_escena_vive_en_la_feature` | El bucle sale de `corrida.py` a `service.py` | `features/escritura/` | §3.9, RF-ORQ-02 |
| P-112 | `test_escribir_una_escena_encola_el_ciclo_y_el_trabajo_avanza` | El router encola en `EjecutorDeTrabajos` | `features/escritura/router.py` | RI-05, RF-ORQ-03 |
| P-113 | `test_al_arrancar_se_retoman_los_trabajos_no_terminales_de_verdad` | La reanudación, conectada al ejecutor real | `commons/jobs/` | RF-ORQ-05, CA-3 |
| P-114 | `test_crear_una_obra_desde_un_brief_devuelve_201` | `POST /obras` | `features/obra/router.py` | RI-01 |
| P-115 | `test_generar_la_biblia_devuelve_trabajo` | `POST /obras/{id}/biblia` | `features/obra/router.py` | RI-02 |
| P-116 | `test_generar_el_outline_devuelve_trabajo` | `POST /obras/{id}/outline` | `features/outline/router.py` | RI-03 |
| P-117 | `test_planificar_una_escena_devuelve_trabajo` | `POST /escenas/{id}/planificar` | `features/escena/router.py` | RI-04 |
| P-118 | `test_el_contexto_de_una_escena_expone_el_desglose_por_capa` | `GET /escenas/{id}/contexto` | `features/contexto/router.py` | RI-06 |
| P-119 | `test_las_versiones_salen_en_orden_con_la_vigente_marcada` | `GET /escenas/{id}/versiones` | `features/escena/router.py` | RI-07 |
| P-120 | `test_el_canon_se_consulta_con_su_escena_de_origen` | `GET /obras/{id}/canon` | `features/canon/router.py` | RI-08 |
| P-121 | `test_el_esquema_expone_los_nueve_endpoints_de_ri_01_a_ri_09` | Sustituye al `len(rutas) >= 3` | `tests/` | RI-23 |
| P-122 | — | `CLAUDE.md` §13 con el comando que arranca, y `sqlalchemy[asyncio]` | raíz | erratas |
| P-123 | — | Desviaciones, cobertura y Cierre al día | `specs/001-backend-v1/` | §3.1 |

---

## Cobertura de `architecture.md`

La razón de esta tabla: el plan se puede quedar corto respecto a la arquitectura **en silencio**, porque la spec cita la arquitectura pero no la agota. Cada sección con contenido implementable tiene aquí su paso.

| Sección | Qué manda | Pasos |
| --- | --- | --- |
| §2 Stack | WAL, Alembic, degradación vectorial, 100 k | P-05 a P-07, P-10, P-44 |
| §2.1 Presupuesto | Ocho topes, **y qué se recorta primero en cada capa** | P-45, P-48 a P-52 |
| §2.2 Concurrencia | 1 llamada, espera, *timeout*, por proceso, tasa del proveedor | P-13, P-77, P-78, P-80, P-88 |
| §3.1 Principios | Estrella, estado en SQLite, idempotencia, una escena, permiso mínimo | P-72 a P-76, P-87 |
| §3.2 Unidad de trabajo | Campos de `trabajo` | P-06, P-95 |
| §3.3 Estados | Diez estados, ninguno se salta | P-71 |
| §3.4 Contrato entre pasos | Pydantic, persistir y releer, desglose en la salida | P-74, P-86, P-94 |
| §3.5 Permisos por agente | Cada uno solo sus almacenes; el Escritor solo el paquete | P-42, P-73 |
| §3.6 Fallos | Cinco causas con su acción | P-52, P-80, P-81, P-83, P-88, P-89 |
| §3.7 Reanudación | Repetir el paso entero | P-75, P-76 |
| §3.8 Concurrencia | Varias obras, llamadas serializadas, cerrojo por obra | P-82, P-87 |
| §3.9 Dónde vive el código | `commons/jobs/`, `features/escritura/`, `commons/llm/`, `agents.py` | Columna **Dónde** |
| §4.2 Corto plazo | N-1 íntegra, N-2 resumida, ancla, hilos | P-47, P-58 |
| §4.3 Almacenes | Siete, con quién escribe cada uno | P-29 a P-42 |
| §4.4 Consolidación | Solo tras aprobar, en orden, en una transacción | P-35, P-36 |
| §4.5 Compactación | Cascada; **nunca** constitucional, canon ni ledger | P-37, P-39 |
| §4.6 Recuperación | Filtro → similitud → recencia | P-57 |
| §4.7 Corrección sin edición | Hecho nuevo; invalida *snapshots* | P-33, P-34 |
| §4.8 Memoria → paquete | Cada capa, su almacén; capa vacía es fallo | P-46, P-53 |
| §5.1 Estructura | Ocho features, segmentos con nombre fijo | P-17 |
| §5.2 Dependencias | Seis reglas, verificadas por build | P-16, P-92 |
| §5.4 Endpoints | Nueve de los diez; `/auditoria` queda fuera | P-91, P-93 |
| §5.5 Persistencia | Tablas, y prompts como ficheros con hash | P-06, P-21, P-94 |
| §8.3 Puertas | G1a bloquea, G1b no; comprobación de forma | P-67, P-69 |
| §9 Trazabilidad | Registro por llamada y ocho métricas | P-94, P-97, P-98, P-103 |
| §10 Despliegue | Local es el modo de referencia; trabajos en el proceso de la API | P-13, P-101 |
| §11 Seguridad | Esquema, logs, claves, autoría | P-03, P-15, P-90, P-96 |

**Secciones sin paso, a propósito:** §6 (frontend, fuera de alcance), §7 salvo permisos (catálogo descriptivo), §12 (decisiones ya tomadas), §13 (hoja de ruta), §14 (mantenimiento documental). §7.2 describe las skills del agente de código, no del producto.

---

## Fronteras implicadas (`CLAUDE.md` §5)

Features tocadas: las ocho de `architecture.md` §5.1 menos `auditoria`, que queda fuera de alcance, más `commons/`.

**Ningún paso de este plan cruza una frontera.** Lo compartido —configuración, errores, base de datos, cliente de modelo, contador, `VectorStore`, dominio y el motor de trabajos— nace en `commons/` porque lo usan tres o más features desde el primer día, no por anticipación.

El contrato de `import-linter` se declara en P-16, **antes** que ninguna feature, y cubre las seis reglas de §5.2 —incluida la tercera, que `commons/domain/` no importe FastAPI ni SQLAlchemy—, para que la primera violación rompa la build en vez de descubrirse al final.

Dos puntos donde la tentación de cruzar aparecerá:

- `calidad` necesita canon para contrastar (P-64). Entra por el `__init__.py` de `canon`, nunca por su `repository.py`.
- `escritura` orquesta a todas. Es la única que las conoce a todas, y solo por sus índices. El **motor** de la máquina de estados no vive ahí sino en `commons/jobs/` (§3.9): en `features/escritura/` viven los pasos.

---

## Esquema y migraciones

**Una sola revisión de Alembic**, `0001_inicial`, en P-06. No hay esquema previo que migrar.

Tablas de `architecture.md` §5.5 que entran desde el primer día: `serie`, `obra`, `version_obra`, `parte`, `capitulo`, `escena`, `version_texto`, `entidad`, `hecho_canon`, `evento`, `plantado`, `hilo_narrativo`, `defecto`, `ejecucion`, `trabajo`, `ngrama_vetado`.

Decisiones que la migración debe respetar, porque añadirlas después obliga a reescribir:

- `serie_id` en el canon (RD-11), aunque la v1 maneje una sola obra.
- `version_obra` (RD-12) y la referencia desde `Escena` (RF-ESC-06).
- `defecto` con `desplazamiento_inicio`, `desplazamiento_fin` y `hecho_canon_id` (RD-14).
- Nombres **exactamente** los de `definitions.md` (RD-02).

P-07 la ejecuta **sin** `sqlite-vec` cargado. Si la migración solo pasa con la extensión, el modo degradado no está verificado y la casilla de `verification.md` §7 sigue en parcial.

---

## Presupuesto de contexto

Este plan **no cambia ningún tope**: los implementa por primera vez, tal como están en `architecture.md` §2.1.

| Capa | Tope | Qué se recorta primero | Pasos |
| --- | --- | --- | --- |
| Constitucional | 5.000 | No se recorta | P-45, P-51 |
| Estructural | 10.000 | Detalle de beats lejanos | P-45, P-50 |
| Canon relevante | 20.000 | Personajes mencionados, no presentes | P-45, P-50 |
| Estado en T | 15.000 | Conocimientos antiguos ya usados | P-45, P-50 |
| Continuidad local | 20.000 | Escena N-2 antes que N-1 | P-47, P-50 |
| Memoria recuperada | 10.000 | Resultados de menor puntuación | P-50, P-57 |
| Instrucción | 10.000 | No se recorta | P-51 |
| Reserva | 10.000 | — | P-54 |

Total 100.000. El desglose se persiste en `ejecucion` (P-48, P-94).

---

## Riesgos

### Medido en la primera corrida real (2026-09-22)

D-07 prometía confirmar o sustituir los objetivos de rendimiento midiendo. Lo
medido, con Haiku y diez escenas:

| Qué | Objetivo | Medido |
| --- | --- | --- |
| Coste por escena | sin objetivo | 0,052 USD |
| Tokens del paquete | ≤ 90.000 + reserva | 537 a 2.781 |
| Escalados por cien escenas | sin umbral | 0 |
| Defectos por código | — | ninguno (solo 3 de 11 validadores en el bucle) |

**El reparto de §2.1 no se pone a prueba todavía.** La continuidad local se lleva
1.504 tokens de media y el resto de capas suman menos de 130: el canon aporta 36.
Es correcto por diseño —§4.2 pide la escena N-1 íntegra—, pero significa que los
topes por capa no han tenido ocasión de recortar nada. Se sabrá cuando los
almacenes estén cableados de verdad y el canon traiga contenido.

**El contador local frente al del proveedor.** El riesgo que este plan marcaba
como el peor sigue sin poder descartarse: los paquetes de esta corrida son tan
pequeños que ninguna diferencia de tokenización se notaría. Hace falta una escena
cerca del techo para saberlo.

---

**El contador local puede no coincidir con el del proveedor.** D-07 obliga a un contador local para cumplir RNF-REN-01. Si tokeniza distinto, RNF-TOK-01 se incumple *en silencio*: el paquete cabe según nosotros y no según quien factura. Mitigación en P-08: margen explícito y contraste periódico contra el recuento que devuelve el proveedor. **Es el riesgo con peor relación entre probabilidad y visibilidad de todo el plan.**

**VOZ-03 puede dar falsos positivos.** Detectar persona y tiempo verbal en castellano falla con el diálogo: un personaje habla en primera dentro de una narración en tercera. P-68 mide solo sobre narración, y el diálogo es un test propio.

**La extracción del Continuista es probabilística.** `verification.md` §6.2: G1a es mecánica en el contraste, no en la extracción. P-97 mide lo único medible hoy —los defectos mal formados—; los **falsos negativos siguen sin medirse**, y ningún paso de este plan los alcanza.

**Voyage añade proveedor y clave.** Sin red o sin clave, P-10 a P-12 y la fase 4 dependen de un doble. El arranque falla de inmediato si falta (P-01), que es lo correcto, pero la puesta en marcha necesita dos claves.

**El orden concentra el riesgo al final.** El orquestador es la fase 7 y es donde aparecen los fallos de integración. Mitigación: P-99 es el primer paso de la fase 9, no el último posible; si obliga a volver atrás, se vuelve.

---

## Qué queda fuera de este plan

Lo de «Fuera de alcance» de la spec, sin excepción: Crítico y G1b, métricas de prosa, validación de voz por muestras ancla, Editor de línea, auditoría de manuscrito y su endpoint, puertas G2 y G3, frontend, modo servidor multiusuario y tests de mutación.

Tampoco entra nada que la spec no pida. Si al implementar aparece algo necesario que no esté en la spec, **se para y se corrige la spec** (§3.4), no se añade un paso.

---

## Desviaciones

Se anotan **antes** de seguir, no al final.

| Fecha | Paso | Qué cambió y por qué |
| --- | --- | --- |
| 2026-09-22 | P-99 | **La corrida en seco no cubre lo que se creía.** Valida que las siete features encajan y que la máquina llega a `INTEGRADA` diez veces, pero `DobleDeModelo` **ignora el prompt** y devuelve texto fijo: ni el adaptador del proveedor ni el contrato de los prompts pasan por ella. Los cuatro fallos que mataron la primera corrida real —el `.cmd` de npm, el prompt como argumento, las vallas de markdown y los nombres de campo inventados— eran todos invisibles en seco. Un doble que ignora su entrada no puede validar lo que se le pide al modelo. |
| 2026-09-22 | P-88 | **RNF-FIA-02 estaba implementado y era inalcanzable.** El cliente lanzaba `FalloDeProveedor` directamente y `con_reintentos` trata esa excepción como ya agotada, así que un 5xx transitorio mataba la corrida en el primer intento. La primera corrida real integró 5 de 10 escenas por eso. Entra `ErrorTransitorioDeProveedor`, que sí se reintenta; `FalloDeProveedor` queda para cuando los tres intentos se agotan. El test de P-88 pasaba porque probaba la función aislada, no su conexión. |
| 2026-09-22 | P-43 a P-59 | **Añadido `extraer_json`.** Los prompts piden «solo JSON» y el modelo lo envuelve en vallas de markdown casi siempre. Recorta el envoltorio y **no repara**: si lo de dentro está roto, sigue siendo fallo del paso (RF-ORQ-15). Un extractor que arreglara JSON medio escrito convertiría una salida rota en una silenciosamente incompleta. |
| 2026-09-22 | P-21 | **Los prompts describían los campos en prosa y el modelo elegía otros nombres**: `que_ocurre` por `descripcion`, `distancia_psiquica` como número. Ahora llevan la plantilla exacta con tipos. Es la misma lección tres veces: un contrato de salida se declara, no se narra. |
| 2026-09-22 | P-99 | **Resultado de CA-1:** 10/10 escenas `INTEGRADA`, 10.236 palabras, 0,5233 USD con Haiku. Cero defectos, y eso **no** significa que el texto sea impecable: en esta corrida corren tres de los once validadores y el Continuista no está en el bucle. Cero defectos significa que nadie miró. |
| 2026-09-22 | P-56 | **Se retira.** Era `prop_mismo_estado_y_misma_semilla_dan_el_mismo_paquete`, es decir RF-CTX-01, que D-02 retiró al sustituir el índice vectorial por una ordenación semántica con varianza. La fase 5 pasa de cuatro propiedades mínimas a tres: el desglose suma (P-48), recortar una capa no altera las vecinas (P-49) y las capas protegidas nunca encogen (P-51). La cuarta —o cabe o lanza (P-52)— sigue. El plan pasa de 104 pasos a 103. |
| 2026-09-22 | P-43 a P-59 | `hypothesis` entra como dependencia de desarrollo para los tests de propiedades. `verification.md` §2 los exige por nombre y la spec marca cuatro requisitos como «**T**, propiedad»; escribirlos a mano daría menos cobertura y ningún contraejemplo mínimo. |
| 2026-09-22 | P-113 | **La reanudacion no la llamaba nadie.** `vivos()` existia y estaba probado desde la fase 7, pero ningun arranque lo leia: el estado se persistia con todo cuidado y una caida a mitad de escena dejaba el trabajo en su estado intermedio para siempre. Al conectarlo aparecio que la reanudacion corre **fuera de una peticion**, donde `Depends` no llega, asi que la fabrica de dependencias pasa a `crear_app` como parametro de composicion. Una sola fabrica para los dos caminos: dos serian dos caminos, y el que se prueba nunca es el que falla. |
| 2026-09-22 | P-112 | **El ejecutor no ejecutaba.** `EjecutorDeTrabajos` tenia cola y `drenar()`, pero `drenar()` solo corria en el apagado de la aplicacion: un sistema que procesa al morir no es asincrono, es una cola que nadie atiende. Entra un hilo unico -y uno, no un grupo: el turno de §2.2 admite una llamada a la vez, asi que varios hilos se pasarian la vida esperandolo con transacciones abiertas sobre el mismo SQLite-. De paso, el guard de RF-ORQ-16 detuvo que `router.py` calculara la ruta de los prompts con `Path(__file__)`: donde viven las cosas lo decide la composicion, asi que pasa a `main.py`. Y `Ajustes.modelo` tiene por fin lector, que era lo que P-106 dejo prometido. |
| 2026-09-22 | P-111c | **Cuatro eslabones mas que faltaban**, todos del mismo tipo: piezas construidas y probadas que nunca se habian conectado. La ficha del Planificador no se guardaba (P-111b). Las capas `estado_en_t` y `memoria_recuperada` tambien llegaban vacias en la primera escena, como el canon y la continuidad. `PaqueteDeContexto` **no exponia `ids_recuperados`**, que RI-14 exige persistir y del que depende CA-10: las piezas recuperadas se etiquetaban por posicion, asi que el identificador se perdia; ahora la etiqueta lo lleva y el paquete publica los que **sobrevivieron al recorte**, que es lo que de verdad viajo. Y `preparar_base` de `corrida.py` insertaba `biblia = '{}'`, que dejo de valer en cuanto la capa constitucional empezo a leerla de verdad. |
| 2026-09-22 | P-111 | **Ninguna obra podia empezar.** Al ir a enchufar el ciclo a los almacenes reales aparecio que la primera escena no se puede ensamblar: no tiene canon ni escena anterior, `ORIGEN` declara las dos capas como obligatorias y `ensamblar` lanza `CapaVacia`. RF-CTX-14 existe para detectar un almacen **roto**, no para prohibir el principio de una obra, asi que el adaptador declara la ausencia en voz alta -que ademas le dice algo al Escritor en vez de callarse- y **solo cuando es estructural**: si hay escena anterior y el canon viene vacio, el Extractor no esta escribiendo y RF-CTX-14 sigue disparando. En el mismo sitio se arreglo que la busqueda de la escena anterior fuera por capitulo y no por obra, que dejaba sin continuidad a la primera escena de cada capitulo. Los dos fallos solo se ven al conectar las piezas: por separado, cada mitad pasaba sus tests. |
| 2026-09-22 | P-16 | **Los contratos de frontera prohibian lo que §5.2 regla 1 permite.** Los seis de la regla 1 son de tipo `forbidden`, y `import-linter` cuenta ahi tambien los imports **indirectos**: como el `__init__.py` de una feature reexporta de sus ficheros por definicion, `contexto -> canon -> canon.service` contaba como violacion. El contrato hacia imposible entrar por el `__init__`, que es justo la unica puerta que la regla abre. Llevaba asi desde P-16 y **nadie lo noto porque ninguna feature habia importado a otra**; P-108 fue la primera que lo necesito. Se les anade `allow_indirect_imports`, y se comprobo que siguen detectando el import directo a las tripas metiendo uno a proposito. |
| 2026-09-22 | P-108 | **Se parte en cuatro.** El protocolo `Almacenes` recibe solo `escena_id`, y no habia forma de ir de una escena a su obra, ni de leer su ficha, ni de pedir los hechos de canon anteriores a ella. El adaptador no podia existir sin esas tres lecturas, asi que P-108a (`outline.ubicacion_de`), P-108b (`escena.ficha_de`) y P-108c (`canon.hechos_hasta`) entran antes, en un commit propio, y P-108 queda para el adaptador. Cada lectura vive en la feature **dueña** de esas tablas: `parte` y `capitulo` los escribe `outline`, asi que el camino de vuelta es suyo y no de `escena`. |
| 2026-09-22 | P-105 a P-107 | **La configuración exigía tres credenciales que nadie leía.** `proveedor_generacion_clave`, `proveedor_generacion_url` y `proveedor_embeddings_clave` eran obligatorias para arrancar y no las consumía una sola línea de código; `dimension_embeddings` tampoco. Sobrevivieron a D-02 y costaron una sesión entera de confusión: hacían creer que el sistema necesitaba una clave de API cuando el proveedor es el CLI de Claude Code y autentica con la sesión de la cuenta. Se borran las cuatro, y RI-15, RI-21 y RNF-SEG-03 se enmiendan: la aplicación **no guarda ninguna credencial**, que es una propiedad más fuerte que guardarla bien. P-105 y P-107 salen en un commit porque son la misma edición. El tope de candidatos que RI-21 pide **no** se añade todavía: sin consumidor sería el mismo fósil que estamos quitando, y entra en P-108. |
| 2026-09-22 | P-17 | **`agents.py` no existia en ninguna feature.** `CLAUDE.md` §5.1 lo declara como segmento y §9.3 dice que el codigo de cada agente narrativo vive ahi; el modelo se invocaba desde `service.py`, con el mismo bloque repetido cuatro veces. Se mueve a `agents.py` en las cuatro features que hablan con el modelo. De paso, los modelos de `canon` pasan de `service.py` a su `schemas.py`: estaban en el segmento equivocado y, ademas, dejarlos alli habria creado un ciclo con `agents.py`. **El test de P-17 omitia `agents.py` de su lista de segmentos**, es decir estaba escrito contra la implementacion y no contra §5.1. Se sustituye por una regla —ningun fichero que no sea `agents.py` invoca al modelo— que no obliga a crear cascarones vacios y que crece sola. |
| 2026-09-22 | P-06 | **Se parte en tres commits, dentro de una sola revisión de Alembic.** Dieciséis tablas no caben en un cambio verificable de una pieza: si el test falla, el fallo no se atribuye. Se mantiene `0001_inicial` como única revisión —lo que el plan exige— y lo que se parte es la entrega: (a) obra y manuscrito, (b) biblia y mundo, (c) canon, (d) orquestación y trazas. Cada commit añade sus tablas a la misma revisión con su test. **Ajustado el mismo día de tres a cuatro entregas:** al releer RD-01 aparecen `Personaje`, `PerfilDeVoz`, `Relacion`, `Lugar`, `Objeto` y `ReglaDeMundo`, que el corte de tres metía todas en (b). Son 21 tablas, no 16. |
