# Dossier de investigación — neon-smoke

Modo dossier (RES0). Búsquedas gastadas: 2/2. Alcance: solo los dos ejes pedidos.
Fuera de alcance por brief: detalle criptográfico de esquemas de sellado de tiempo,
derecho procesal de jurisdicciones reales.

## 1. Sincronización horaria y sellado de tiempo

### Un sello de tiempo confiable certifica que un dato existía en un momento dado sin depender del reloj del propio dispositivo que lo generó

- **Fuente:** OriginStamp — https://originstamp.com/en/blog/reader/trusted-timestamping-explained
- **Consultado:** 2026-09-17
- **Confianza:** media
- **Matiz:** Explicación divulgativa de proveedor comercial del sector, no un texto normativo primario. Sirve como descripción de concepto, no como cita de estándar.

### El proceso técnico habitual envía a la autoridad de sellado solo un resumen criptográfico (hash) del documento, no el documento en sí

- **Fuente:** OriginStamp — https://originstamp.com/en/blog/reader/trusted-timestamping-explained
- **Consultado:** 2026-09-17
- **Confianza:** media
- **Matiz:** Es descripción de mecanismo general de la industria, no el detalle criptográfico exacto (que el brief marca fuera de alcance).

### Los marcos de referencia habituales para el sellado de tiempo confiable son RFC 3161 y el estándar ANSI ASC X9.95, que exigen una autoridad central de sellado que emite y valida las marcas de tiempo

- **Fuente:** OriginStamp — https://originstamp.com/en/blog/reader/trusted-timestamping-explained
- **Consultado:** 2026-09-17
- **Confianza:** media
- **Matiz:** Confirma que existe una autoridad central como pieza estructural del modelo (relevante para el worldbuilding de un "consorcio" que vende el sello de tiempo), sin entrar en su implementación.

### El reloj local de un dispositivo es una fuente de tiempo intrínsecamente poco fiable: puede ser manipulado por el usuario, desincronizado por latencia de red, o suplantado alterando las respuestas de protocolos de sincronización de red

- **Fuente:** resumen agregado de motor de búsqueda sobre literatura técnica de sincronización de tiempo (papers académicos indexados en arXiv sobre infraestructuras de reloj de red)
- **Consultado:** 2026-09-17
- **Confianza:** baja
- **Matiz:** El buscador devolvió esta afirmación sin ligarla de forma inequívoca a una URL concreta de la lista de resultados; no pude verificar la fuente primaria exacta en esta ronda. Útil como concepto general, no citable como hecho verificado a una publicación específica.

### Existen infraestructuras redundantes de distribución horaria (por ejemplo, redes de miles de servidores sincronizados entre sí) precisamente para mitigar el fallo de una única fuente de referencia

- **Fuente:** PMC (National Center for Biotechnology Information) — artículo "Accurate, Traceable, and Verifiable Time Synchronization for World Financial Markets" — https://pmc.ncbi.nlm.nih.gov/articles/PMC7339776/
- **Consultado:** 2026-09-17
- **Confianza:** media
- **Matiz:** El artículo trata sincronización para mercados financieros (precisión de microsegundos, trazabilidad a un instituto de metrología nacional), no para sellado judicial; se usa aquí solo para el concepto de "referencia distribuida y trazable", no para cifras trasladables sin más a la novela.

### Lo que hace verificable un sello de tiempo no es la precisión del reloj en sí, sino que el origen del tiempo sea auditable hasta una fuente confiable y que nadie pueda alterar o recrear esa marca a posteriori

- **Fuente:** OriginStamp — https://originstamp.com/en/blog/reader/trusted-timestamping-explained
- **Consultado:** 2026-09-17
- **Confianza:** media
- **Matiz:** Este es el principio que sostiene la premisa de la novela (el archivo es válido, la referencia no lo es); la fuente lo enuncia como criterio de diseño de sistemas de sellado, no como doctrina judicial.

### HUECO: qué ocurre formalmente, en términos generales de fiabilidad de sistemas (no de derecho procesal), cuando una fuente de tiempo certificada se demuestra retroactivamente errónea después de haber sido usada para sellar muchos registros

- **Buscado:** en las dos búsquedas realizadas, junto con la reversión retroactiva de admisibilidad forense (ver eje 2).
- **Resultado:** sin fuente utilizable que trate específicamente el escenario de invalidación retroactiva de una referencia horaria compartida por muchos sellos ya emitidos.

## 2. Prueba forense digital y cadena de custodia

### Un elemento de prueba digital se considera admisible cuando se puede demostrar que es auténtico, fiable, completo y que ha mantenido una cadena de custodia íntegra

- **Fuente:** Champlain College Online — "Digital Forensics and the Chain of Custody: How Is Electronic Evidence Collected and Safeguarded?" — https://online.champlain.edu/blog/chain-custody-digital-forensics
- **Consultado:** 2026-09-17
- **Confianza:** media
- **Matiz:** Fuente divulgativa educativa, no un texto normativo; sirve para el criterio general, no para el umbral exacto que aplicaría un tribunal real (fuera de alcance por brief).

### El proceso forense estándar consta de identificación, preservación, recolección con métodos forenses sólidos, examen manteniendo la cadena de custodia, análisis y presentación admisible ante el tribunal

- **Fuente:** Champlain College Online — https://online.champlain.edu/blog/chain-custody-digital-forensics
- **Consultado:** 2026-09-17
- **Confianza:** media
- **Matiz:** Descripción de proceso general de la disciplina, no de un procedimiento judicial de una jurisdicción concreta.

### Entre las debilidades más comunes que comprometen una prueba digital están la falta de bloqueo de escritura sobre el original, la falta de documentación de las herramientas y versiones usadas para copiar la evidencia, y la falta de verificación por resumen criptográfico (hash) de las copias

- **Fuente:** Cornerstone Discovery — "Maintaining Chain of Custody in Digital Forensics: What You Should Know" — https://cornerstonediscovery.com/maintaining-chain-of-custody-in-digital-forensics-what-you-should-know/
- **Consultado:** 2026-09-17
- **Confianza:** media
- **Matiz:** Lista de buenas prácticas de un proveedor de servicios forenses; describe fallas típicas del oficio, no un catálogo legal cerrado de causas de exclusión.

### Los tribunales no suelen exigir una documentación perfecta de la cadena de custodia: los huecos menores afectan al peso que se le da a la prueba, no necesariamente a su admisibilidad; en cambio, un periodo completo sin que ningún custodio autorizado pueda explicar dónde estuvo o en qué estado la evidencia sí puede llevar a su exclusión

- **Fuente:** Prudential Associates — "Chain of Custody: Legal Guide for Evidence Management" — https://prudentialassociates.com/feeds/blog/chain-custody-evidence
- **Consultado:** 2026-09-17
- **Confianza:** media
- **Matiz:** Es una guía general orientada a la práctica forense/legal en EE. UU., no doctrina de una jurisdicción concreta; el brief pide una ciudad inventada, así que esto se usa solo como principio de distinción (hueco menor vs. ruptura sustancial), no como regla trasladable literalmente.

### HUECO: qué sucede formalmente con condenas ya firmes cuando, después de la sentencia, se invalida el método o la fuente que sostenía la prueba usada para condenar (revisión retroactiva de casos ya cerrados)

- **Buscado:** impugnación retroactiva de prueba forense, invalidación de método tras condena firme, estadísticas de exoneraciones ligadas a fallos de método forense.
- **Resultado:** el buscador devolvió una cifra agregada (relacionada con un registro de exoneraciones y un porcentaje de casos con prueba forense cuestionada) pero sin una URL específica y verificable dentro de los resultados de esta ronda que yo pueda citar con confianza razonable. Se descarta en vez de citarse sin respaldo verificable.

## Huecos

- Efecto formal de la invalidación retroactiva de una referencia horaria compartida sobre sellos ya emitidos (eje 1): sin fuente utilizable encontrada.
- Estadísticas concretas de exoneraciones o revisiones de condena atribuibles a fallos de método forense (eje 2): el buscador sugirió una cifra, pero no hay URL verificable asociada dentro del presupuesto de búsqueda disponible; se declara hueco en vez de citarse sin respaldo.
- Atribución exacta a una publicación primaria (más allá del resumen agregado del buscador) de la afirmación sobre la facilidad de suplantar servidores de sincronización horaria: no verificada a nivel de URL individual.
- Cualquier plazo, cifra o protocolo legal específico de jurisdicción real: fuera de alcance por brief, no buscado.
