# Briefs de ejemplo

Lo que el **comprador** entrega al cerrar la entrevista, en la forma exacta que
`BriefEntrada` acepta. No son de nadie: los nombres están inventados.

| Fichero | Para qué |
| --- | --- |
| `brief-marta.json` | El caso normal. Es el de los tests y el del `README.md` |
| `brief-menor.json` | Un **destinatario menor de edad**, con `nivel_de_calor` en 0 |

## Estos ficheros se ejecutan

`src/backend/app/features/obra/tests/test_ejemplos.py` carga todos los
`brief-*.json` de aquí y **construye el modelo** con cada uno. No comprueba que
tengan los campos: los construye, que es lo único que dispara los tres
validadores de `BriefEntrada` —contenido adulto con menores, la edad contra la
fecha de nacimiento, y ningún veto chocando con el nombre del destinatario—.

**Y por eso existe este directorio.** El brief de ejemplo vivía dentro del
`README.md`, ponía los campos del destinatario al nivel de arriba en vez de
dentro de `destinatario`, y **no validaba**. Nadie lo notó porque un bloque de
código en un documento no falla nunca. Aquí sí.

## Por qué ninguno lleva `fecha_de_nacimiento`

El campo existe y es opcional, y la regla de dominio 13 lo comprueba contra
`edad`. Pero una fecha fija junto a una edad fija **caduca**: `brief-menor.json`
llegó a tener `2014-03-08` con `edad: 12`, cierto hoy y falso a partir de 2028,
y habría puesto la suite en rojo un día cualquiera por el paso del tiempo y no
por un cambio de nadie.

Un test que falla solo enseña a ignorar los fallos. La regla 13 se prueba donde
se puede fijar el reloj —`features/obra/tests/`, con fechas controladas—, y los
ejemplos se quedan con lo que un comprador escribiría de verdad.

## Cómo se usa uno

Con el backend levantado (`CLAUDE.md` §14):

```bash
ENT=$(curl -s -XPOST localhost:8000/entrevistas | python -c "import json,sys;print(json.load(sys.stdin)['id'])")
curl -s -XPOST localhost:8000/entrevistas/$ENT/respuestas \
  -H 'content-type: application/json' \
  -d "{\"respuestas\": $(cat ejemplos/brief-marta.json)}"
curl -s -XPOST localhost:8000/entrevistas/$ENT/cerrar
```
