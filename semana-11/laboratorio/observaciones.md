# Observaciones semana 11 · Migración a gRPC

Equipo SD-Jaune-Asencio · Dominio mensajería instantánea · Fecha 13-11-2026

Integrantes: Diego Jaune y Sebastián Asencio.

El estado inicial es ana y beto, cada uno con 100 pendientes y el buzón vacío. En la sección 4 la llamada que modifica estado es `enviar ana beto hola`, y el servidor se recreó antes de cada caso.

## 1. Contrato
- Archivo `proto/servicio.proto` con 4 operaciones: `Usuarios`, `Enviar`, `Leer` y `Registrar`.
- Operaciones que modifican estado y llevan `id_solicitud`: `Enviar`, `Leer` y `Registrar`.
- Operaciones idempotentes (se pueden repetir sin efecto extra): solo `Usuarios`. `Enviar` agrega otro texto y otro pendiente cada vez que se aplica. `Leer` descuenta pendientes y saca textos del buzón. `Registrar` responde `USUARIO_EXISTE` si el nombre ya está.

## 2. Stubs generados
- Clase del stub en el cliente: `MensajeriaStub` (en `servicio_pb2_grpc.py`)
- Clase base del servidor: `MensajeriaServicer`
- Qué hace el stub cuando llamamos `stub.Enviar(...)`: serializa la solicitud con Protocol Buffers y la manda por HTTP/2 al método `/mensajeria.v1.Mensajeria/Enviar`. Cuando vuelve la respuesta la convierte en `EnviarRespuesta`, y si el estado no es OK lanza `RpcError` con el código gRPC.

## 3. Equivalencia de errores JSON-RPC → gRPC

| Caso | JSON-RPC (semana 10) | gRPC (hoy) | Comando usado |
|---|---|---|---|
| Método inexistente | -32601 | UNIMPLEMENTED | `docker compose exec cliente python -c "import grpc; grpc.insecure_channel('servidor:50051').unary_unary('/mensajeria.v1.Mensajeria/Borrar')(b'', timeout=2)"` → `status = StatusCode.UNIMPLEMENTED`, `Method not found!` |
| Parámetros inválidos | -32602 | INVALID_ARGUMENT | `docker compose exec cliente python cliente_grpc.py leer beto 0` → `INVALID_ARGUMENT, cantidad debe ser un entero mayor que cero` |
| Error del dominio | -32000 | FAILED_PRECONDITION | `docker compose exec cliente python cliente_grpc.py leer ana 200` → `FAILED_PRECONDITION, SIN_MENSAJES 100` |
| Servidor caído | sin conexión | UNAVAILABLE | Con `FALLA=siempre` y `DEMORA=8`, `enviar ana beto hola --timeout 20` y, a los 2 s, `docker compose kill servidor` → `UNAVAILABLE, Socket closed` |
| Respuesta lenta | timeout del cliente | DEADLINE_EXCEEDED | `FALLA=siempre`, `DEMORA=3`, deadline 2 s: `docker compose exec cliente python cliente_grpc.py enviar ana beto hola` → `DEADLINE_EXCEEDED, Deadline Exceeded` |

Una llamada nueva, iniciada con el contenedor ya detenido, no devolvió `UNAVAILABLE`: esperó los 2 s del deadline y respondió `DEADLINE_EXCEEDED`. El `UNAVAILABLE` apareció al cortar la conexión de una llamada que ya estaba en curso.

## 4. Falla intermedia · semántica teórica frente a la observada

| # | Configuración | Qué vio el cliente | Pendientes finales con `usuarios` | Semántica observada |
|---|---|---|---|---|
| 1 | `FALLA=no`, sin reintentos | `OK beto pendientes=101` | ana=100, beto=101 | aplicada una vez y confirmada |
| 2 | `FALLA=siempre`, sin reintentos | `DEADLINE_EXCEEDED` y estado DESCONOCIDO | ana=100, beto=101 | maybe: se aplicó y el cliente no lo sabe |
| 3 | `FALLA=siempre`, `--reintentos 2`, sin `DEDUP` | tres `DEADLINE_EXCEEDED` con el mismo id `8060e567`, y estado DESCONOCIDO | ana=100, beto=103 | at-least-once: el mismo envío se aplicó tres veces |
| 4 | `FALLA=siempre DEDUP=1`, `--reintentos 2` | primer intento `DEADLINE_EXCEEDED`; el segundo, con el mismo id `dc2df37b`, `OK beto pendientes=101` | ana=100, beto=101 | at-most-once: el reintento no volvió a sumar |
| 5 | `docker compose kill servidor` durante una llamada | `UNAVAILABLE, Socket closed` y estado DESCONOCIDO | al reiniciar, ana=100, beto=100 | maybe: el estado vive en memoria y se perdió con el proceso |

Pegar aquí las líneas relevantes de `docker compose logs servidor` de los casos 3 y 4.

```
# caso 3, DEDUP=0, el mismo id se aplica tres veces
[servidor] gRPC escuchando en 50051 con FALLA=siempre DEMORA=3 DEDUP=0
[servidor] Enviar id=8060e567 -> {'destino': 'beto', 'pendientes': 101}
[servidor] FALLA=siempre, cambio YA aplicado, demoro la respuesta 3 s
[servidor] Enviar id=8060e567 -> {'destino': 'beto', 'pendientes': 102}
[servidor] FALLA=siempre, cambio YA aplicado, demoro la respuesta 3 s
[servidor] Enviar id=8060e567 -> {'destino': 'beto', 'pendientes': 103}
[servidor] FALLA=siempre, cambio YA aplicado, demoro la respuesta 3 s
[servidor] Usuarios -> 2 usuarios

# caso 4, DEDUP=1, el reintento devuelve lo guardado
[servidor] gRPC escuchando en 50051 con FALLA=siempre DEMORA=3 DEDUP=1
[servidor] Enviar id=dc2df37b -> {'destino': 'beto', 'pendientes': 101}
[servidor] FALLA=siempre, cambio YA aplicado, demoro la respuesta 3 s
[servidor] Enviar id=dc2df37b repetido, devuelvo lo guardado SIN aplicar de nuevo
[servidor] Usuarios -> 2 usuarios
```

## 5. Conclusión (cinco líneas como máximo)
`Enviar`, `Leer` y `Registrar` serían peligrosas de reintentar sin `id_solicitud`.
`Enviar` duplicaría el texto y las notificaciones: en un chat real la otra persona vería el mismo mensaje varias veces.
`Leer` descontaría pendientes de más y sacaría textos que el cliente ya tenía, así que esos mensajes se perderían del buzón.
`Registrar`, en el reintento, respondería `USUARIO_EXISTE` aunque el alta sí se hubiera aplicado, y el cliente creería que el registro falló.
Con `id_solicitud` y `DEDUP` el servidor devuelve la respuesta guardada y no modifica el estado otra vez.
