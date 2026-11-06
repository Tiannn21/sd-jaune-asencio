# Observaciones — Semana 9, serialización explícita

**Equipo:** SD-JAUNE-ASENCIO
**Integrantes:** Diego Jaune y Sebastian Asencio
**Fecha:** 23-10-2026

## Paso 2 — Ida y vuelta de los codecs

Salida de `python codec.py`:

```
json  solicitud  81 bytes  b'{"operacion": "AGREGAR", "argumentos": ["tornillo", "25"], "id": 7, "version": 2}'
json  respuesta  64 bytes  b'{"id": 7, "estado": "OK", "datos": ["tornillo=25"], "error": ""}'
bin   solicitud  29 bytes  b'\x02\x00\x00\x00\x07\x00\x07AGREGAR\x02\x00\x08tornillo\x00\x0225'
bin   respuesta  21 bytes  b'\x00\x00\x00\x07\x00\x01\x00\x0btornillo=25\x00\x00'
ida y vuelta OK en los dos codecs
```

Tamaño de la misma solicitud en JSON **81** bytes y en bin **29** bytes.

## Paso 3 — Medición

Salida de `python bench_codec.py 10000`:

```
N = 10000 solicitudes y 10000 respuestas del dominio

| Mensaje   | Codec | Bytes promedio | Bytes totales | Codificar (ms) | Decodificar (ms) |
|-----------|-------|---------------:|--------------:|---------------:|-----------------:|
| Solicitud | json  |           80.1 |        800798 |           45.6 |             21.8 |
| Solicitud | bin   |           26.0 |        259748 |           40.4 |             13.5 |
| Respuesta | json  |           74.2 |        742117 |           44.4 |             23.0 |
| Respuesta | bin   |           26.3 |        263227 |           11.3 |             13.3 |

Solicitud: el binario ocupa 68% menos bytes que JSON (JSON 80 B vs bin 26 B por mensaje)
Respuesta: el binario ocupa 65% menos bytes que JSON (JSON 74 B vs bin 26 B por mensaje)

Ejemplo de una misma solicitud en cada codec
  json  106 B  b'{"operacion": "ENVIAR", "argumentos": ["carol", "carol", "semana 9 semana 9 hola"], "id": 0, "version": 2}'
  bin    52 B  b'\x02\x00\x00\x00\x00\x00\x06ENVIAR\x03\x00\x05carol\x00\x05carol\x00\x16semana 9 semana 9 hola'
```

Conclusión en dos líneas (cuánto ahorra el binario, cuál es más rápido, qué sacrificamos a cambio):

El binario ocupa 68% menos en la solicitud (80 B contra 26 B) y 65% menos en la respuesta (74 B contra 26 B). También fue más rápido: codificar una respuesta bajó de 44,4 ms a 11,3 ms, y decodificar de 23,0 ms a 13,3 ms, en 10000 mensajes.

A cambio el mensaje deja de leerse: no trae los nombres de los campos y solo se entiende si los dos lados usan el mismo orden y los mismos largos. Un byte corrido desplaza todo lo que sigue.

## Paso 4 — Integración

| Prueba                                                   | codec=json | codec=bin |
| -------------------------------------------------------- | ---------- | --------- |
| `HOLA`                                                   | `OK HOLA \| anonimo`      | `OK HOLA \| anonimo`      |
| `ENVIAR ana beto hola`                                   | `OK beto \| 101`          | `OK beto \| 101`          |
| `USUARIOS`                                               | `OK ana:100 \| beto:101`  | `OK ana:100 \| beto:101`  |
| Error del dominio (`USUARIO_NO_EXISTE` o `SIN_MENSAJES`) | `ERROR USUARIO_NO_EXISTE` | `ERROR USUARIO_NO_EXISTE` |

## Paso 5 — Falla provocada

| Modo de `cliente_malo.py` | Qué vio el cliente | Qué dice el log del servidor | ¿El servidor siguió atendiendo? |
| ------------------------- | ------------------ | ---------------------------- | ------------------------------- |
| `version`                 | `ERROR versión 1 no soportada, use 2` (id 1) | `versión no soportada 1` y cierra cuando el cliente cierra | Sí. El `HOLA` siguiente respondió OK |
| `largo`                   | `sin respuesta en 5.0 s` | Conectó y se desconectó a los 5 s, sin llegar a leer una solicitud. No apareció el timeout de 30 s: el cliente cerró el socket antes | Sí. Un `HOLA` en paralelo respondió OK |
| `basura` (codec json)     | `ERROR mensaje mal formado (UnicodeDecodeError)` | `'utf-8' codec can't decode byte 0xb8 in position 1: invalid start byte`. Cerró solo esa conexión | Sí. El `HOLA` siguiente respondió OK |
| `basura` (codec bin)      | `ERROR mensaje mal formado (UnicodeDecodeError)` | `'utf-8' codec can't decode byte 0xbe in position 1: invalid start byte`. Cerró solo esa conexión | Sí. El `HOLA` siguiente respondió OK |
| `cruzado`                 | Servidor en `bin`, cliente codificó en JSON. `ERROR mensaje mal formado (struct.error)` | `unpack_from requires a buffer of at least 29289 bytes` y el buffer real era de 85. Cerró solo esa conexión | Sí. El `HOLA` siguiente respondió OK |

¿Cuál de los dos codecs falló de forma más clara ante la basura y por qué?

Con 24 bytes al azar los dos fallaron igual, en UTF-8, antes de interpretar el formato: el error nombra el byte y la posición. La diferencia apareció cuando el cuerpo sí era texto válido pero del otro codec. Ahí el binario fue más claro: `struct.error` dijo cuántos bytes pedía el largo prefijado (29289) y cuántos habían llegado (85). El JSON, si llega a parsear, solo dice que el texto no es JSON.

## Para la semana autónoma

Una pregunta que nos quedó sobre serialización o protocolos:

¿Cómo se agrega un campo al formato binario sin que un cliente que todavía usa el layout anterior deje de poder decodificar, o crea que leyó bien un mensaje que ya no entiende?
