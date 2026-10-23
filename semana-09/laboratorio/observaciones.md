# Observaciones — Semana 9, serialización explícita

**Equipo:** SD-JAUNE-ASENCIO**Integrantes:**Diego Jaune y Sebastian Asencio**Fecha:** 23-10-2026

## Paso 2 — Ida y vuelta de los codecs

Salida de `python codec.py`:

```
json  solicitud  81 bytes  b'{"operacion": "AGREGAR", "argumentos": ["tornillo", "25"], "id": 7, "version": 2}'
json  respuesta  64 bytes  b'{"id": 7, "estado": "OK", "datos": ["tornillo=25"], "error": ""}'
bin   solicitud  29 bytes  b'\x02\x00\x00\x00\x07\x00\x07AGREGAR\x02\x00\x08tornillo\x00\x0225'
bin   respuesta  21 bytes  b'\x00\x00\x00\x07\x00\x01\x00\x0btornillo=25\x00\x00'
ida y vuelta OK en los dos codecs
```

Tamaño de la misma solicitud en JSON \_**\_ bytes y en bin \_\_** bytes.

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

_(escribir)_

## Paso 4 — Integración

| Prueba                                                   | codec=json | codec=bin |
| -------------------------------------------------------- | ---------- | --------- |
| `HOLA`                                                   |            |           |
| `ENVIAR ana beto hola`                                   |            |           |
| `USUARIOS`                                               |            |           |
| Error del dominio (`USUARIO_NO_EXISTE` o `SIN_MENSAJES`) |            |           |

## Paso 5 — Falla provocada

| Modo de `cliente_malo.py` | Qué vio el cliente | Qué dice el log del servidor | ¿El servidor siguió atendiendo? |
| ------------------------- | ------------------ | ---------------------------- | ------------------------------- |
| `version`                 |                    |                              |                                 |
| `largo`                   |                    |                              |                                 |
| `basura` (codec json)     |                    |                              |                                 |
| `basura` (codec bin)      |                    |                              |                                 |
| `cruzado`                 |                    |                              |                                 |

¿Cuál de los dos codecs falló de forma más clara ante la basura y por qué?

_(escribir)_

## Para la semana autónoma

Una pregunta que nos quedó sobre serialización o protocolos:

_(escribir)_
