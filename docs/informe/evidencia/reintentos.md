# Reintento de un envío en los tres mecanismos

Fecha: 20-11-2026. En cada caso el servidor parte del estado inicial (`ana=100`, `beto=100`) y el cliente manda dos veces la misma solicitud de envío, como lo haría un cliente que no recibió la primera respuesta y vuelve a intentar.

## gRPC (semana 11)

Resultado ya registrado en `semana-11/laboratorio/observaciones.md`, sección 4.

- Caso 3, `DEDUP=0`: tres intentos con el mismo `id_solicitud` (`8060e567`) dejaron `beto=103`.
- Caso 4, `DEDUP=1`: el reintento con el mismo `id_solicitud` (`dc2df37b`) recibió la respuesta guardada y `beto` quedó en 101.

## JSON-RPC (semana 11)

`rpc.py` servido con uvicorn dentro del contenedor `servidor`, en el puerto 8000. Script: `semana-11/laboratorio/reintento_jsonrpc.py`, que envía dos veces la misma solicitud con `"id": 1`.

```text
$ docker compose up -d
$ docker compose exec -d servidor uvicorn rpc:app --host 0.0.0.0 --port 8000
$ docker compose exec cliente python reintento_jsonrpc.py
usuarios antes    {'ana': 100, 'beto': 100}
intento 1, id=1   {'destino': 'beto', 'pendientes': 101}
intento 2, id=1   {'destino': 'beto', 'pendientes': 102}
usuarios despues  {'ana': 100, 'beto': 102}
leer beto 2       {'usuario': 'beto', 'pendientes': 100, 'mensajes': ['ana:hola', 'ana:hola']}
```

## Pyro5 (semana 12)

```text
$ docker compose up -d
$ docker compose exec cliente python cliente_pyro.py usuarios
usuarios {'ana': 100, 'beto': 100}
$ docker compose exec cliente python cliente_pyro.py enviar ana beto hola
enviar -> {'destino': 'beto', 'pendientes': 101}
$ docker compose exec cliente python cliente_pyro.py enviar ana beto hola
enviar -> {'destino': 'beto', 'pendientes': 102}
$ docker compose exec cliente python cliente_pyro.py usuarios
usuarios {'ana': 100, 'beto': 102}
$ docker compose exec cliente python cliente_pyro.py leer beto 2
leer -> {'usuario': 'beto', 'pendientes': 100, 'mensajes': ['ana:hola', 'ana:hola']}
```

## Resumen

| Mecanismo | Identificador en la solicitud | Resultado del reintento |
|---|---|---|
| gRPC sin `DEDUP` | `id_solicitud` | Se aplicó otra vez (`beto=103` con tres intentos) |
| gRPC con `DEDUP=1` | `id_solicitud` | No se aplicó otra vez (`beto=101`) |
| JSON-RPC | `id` | Se aplicó otra vez (`beto=102`, mensaje repetido en el buzón) |
| Pyro5 | Ninguno | Se aplicó otra vez (`beto=102`, mensaje repetido en el buzón) |
