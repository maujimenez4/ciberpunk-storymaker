# Qué da hoy `manuscrito` para los seis endpoints de la 002

Inventario pedido por la sesión orquestadora antes de escribir la spec de backend,
para no declarar como inexistente lo que ya está. Medido sobre `88d898a` el
2026-09-23. **Es análisis: no se ha escrito ni una línea de `router.py` ni de
`schemas.py`** (§3.4, sin spec ni plan aprobados no hay código).

## Lo que existe hoy en la feature

`features/manuscrito/` tiene el `repository.py` y el `service.py` llenos, y
`router.py` y `schemas.py` en cuatro líneas cada uno:

| Pieza | Qué hace | Público |
| --- | --- | --- |
| `RepositorioDeManuscrito.ensamblar(obra_id)` | Versiones **vigentes** en `orden_discurso`, con autoría por fragmento | sí |
| `Manuscrito.texto` | Los fragmentos unidos | sí |
| `Manuscrito.autorias()` | Cuántos fragmentos de cada procedencia (RF-MAN-02) | sí |
| `a_markdown(manuscrito, titulo)` | El manuscrito en Markdown, con título y cortes de escena | sí |
| `a_pdf(manuscrito, titulo)` | PDF 1.4 paginado, sin dependencias | sí |
| `exportar(manuscrito, carpeta, nombre, titulo)` | Deja `.md` y `.pdf` juntos | sí |

## La respuesta a la pregunta concreta

> ¿Sirve `ensamblar(obra_id)` tal cual para montar una `VersionPublicada`?

**No, y el motivo no es que le falten campos: es que responde a otra pregunta.**

`ensamblar` filtra por `v.vigente = 1` **en el momento de la consulta**. Devuelve
«el manuscrito ahora», no «el manuscrito que se entregó el día 3». Dos llamadas
separadas por una regeneración devuelven textos distintos para el mismo
`obra_id`, y ninguna de las dos es recuperable después: al marcarse vigente otra
versión, la anterior deja de salir.

Una `VersionPublicada` es lo contrario: un conjunto **inmutable** de
`VersionDeTexto` concretas, que tiene que seguir devolviendo lo mismo dentro de
un año aunque el manuscrito haya cambiado diez veces. Eso obliga a **fijar los
`version_texto_id`** en el momento de publicar, no a recalcular por `vigente`.

Lo aprovechable de `ensamblar` es su orden y su regla de autoría, que no cambian.
Lo que hay que añadir es un segundo camino de lectura —dado un
`version_publicada_id`, devolver sus `version_texto` fijadas— y `ensamblar` se
queda para lo que ya hace: mirar el presente.

Con `a_pdf` no pasa nada de esto: recibe un `Manuscrito` ya montado y no sabe de
dónde salió. Sirve igual para el vigente y para uno publicado.

## Los seis, uno a uno

| Endpoint | Qué existe ya | Qué falta de repositorio | Qué falta de esquema |
| --- | --- | --- | --- |
| `GET /versiones` | Nada | Listar publicaciones de una obra y sus capítulos cambiados | **Tabla `version_publicada`** (`numero`, `publicada_en`, `sucede_a`, `capitulos_cambiados`) |
| `GET /versiones/{v}` | El **orden** y la **autoría** de `ensamblar`; nada del contenido congelado | Leer por `version_publicada_id`, no por `vigente` | `version_publicada` + **tabla puente** a `version_texto`. Portada y dedicatoria **no tienen dónde vivir**: `obra` no tiene `destinatario_id` ni dedicatoria |
| `GET /versiones/{v}/ficha` | Nada. El canon da `entidad`/`atributo`/`valor` pero no en qué capítulos aparece cada uno | Derivar la ficha **al publicar** y guardarla | **Tabla `ficha_de_lectura`**. Y su parte más cara: hoy **no se puede saber en qué capítulos aparece un personaje**, porque `ejecucion.ids_recuperados` solo registra la capa de memoria recuperada y la de canon etiqueta por posición sin el `hc_id` (DEP-01) |
| `GET /versiones/{v}/pdf` | **`a_pdf` completo.** Bytes listos: el endpoint solo los devuelve | El mismo camino de lectura del anterior | Ninguno propio |
| `POST /peticiones` | La tabla `trabajo` ya existe y sirve para devolver un trabajo consultable | Crear la petición y encolar | **Tabla `peticion_de_cambio`**. El canon ya soporta la corrección sin edición: `hecho_canon` tiene `sustituye_a` |
| `POST /versiones/{v}/revertir` | Nada | Marcar vigentes las `version_texto` de la publicación anterior | `version_publicada.sucede_a`, que es de dónde sale «la anterior» |

## Tres cosas que conviene que la spec diga

1. **Nada de la capa de entrega existe en el esquema.** De las 27 tablas de
   `0001_inicial`, ninguna es `version_publicada`, `peticion_de_cambio`,
   `ficha_de_lectura`, `destinatario`, `dedicatoria` ni `comprador`. El
   vocabulario entró en `definitions.md` v1.4; las tablas, no. Son varias tablas
   nuevas, o sea §3 punto 7.

2. **La dedicatoria no puede vivir en el manuscrito.** `definitions.md` dice que
   está fuera del manuscrito y fuera del canon —ni la ve el Escritor ni la extrae
   el Extractor—, así que no puede ser un fragmento más: `ensamblar` la incluiría
   y acabaría en el `.md`, en el `.pdf` y en la lista negra de n-gramas.

3. **`GET /versiones/{v}` arrastra un problema que ya tiene el manuscrito de
   hoy.** Lo que se entrega sale de `version_texto` vigente sin mirar si la escena
   pasó la puerta: en la corrida real, es8 escaló por SEG-01 y sus 2.038 palabras
   están en el entregable. Si la versión publicada se monta con el mismo criterio,
   hereda el problema. RF-MAN-01 dice «vigentes», no «aprobadas», y eso es una
   decisión de requisito, no un fallo de código.
