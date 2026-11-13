# Contrato del servicio · trabajo autónomo semana 11

Plazo jueves 12-11-2026 a las 18.00, en `semana11/` del repositorio del equipo.

Equipo SD-Jaune-Asencio. Dominio: mensajería instantánea.
`Usuarios`, `Enviar` y `Leer` son las operaciones del dominio (semana 10, más la lectura).
`Registrar` es la operación nueva: crea un usuario con 0 pendientes y buzón vacío.

## Qué hay que hacer
1. Agregar al menos **una operación nueva** a `proto/servicio.proto` con sus mensajes, sin cambiar los números de campo existentes.
2. Implementarla en `dominio.py` y exponerla en `servidor_grpc.py` y en `cliente_grpc.py`.
3. Regenerar los stubs y probarla desde el contenedor cliente.
4. Completar este archivo.

## Operaciones

| Operación | Qué hace | Modifica estado | Idempotente | Lleva `id_solicitud` | Errores posibles (código gRPC) |
|---|---|---|---|---|---|
| `Usuarios` | Lista cada usuario y sus pendientes, ordenados por nombre | no | sí | no | — |
| `Enviar` | Guarda `origen:texto` en el buzón del destino y suma 1 pendiente | sí | no | sí | `INVALID_ARGUMENT` si falta `id_solicitud`, el nombre no es una palabra o el texto está vacío. `FAILED_PRECONDITION` si origen o destino no existen (`USUARIO_NO_EXISTE`) |
| `Leer` | Descuenta `cantidad` pendientes y entrega hasta esa cantidad de textos, en orden FIFO | sí | no | sí | `INVALID_ARGUMENT` si falta `id_solicitud`, el usuario no es una palabra o `cantidad` no es mayor que cero. `FAILED_PRECONDITION` si el usuario no existe (`USUARIO_NO_EXISTE`) o pide más pendientes de las que tiene (`SIN_MENSAJES`) |
| `Registrar` | Crea el usuario con 0 pendientes y buzón vacío. Operación nueva | sí | no | sí | `INVALID_ARGUMENT` si falta `id_solicitud` o el nombre no es una sola palabra. `FAILED_PRECONDITION` si ese nombre ya existe (`USUARIO_EXISTE`) |

## Mensajes y campos

| Mensaje | Campo | Número | Tipo | Significado |
|---|---|---|---|---|
| `UsuariosSolicitud` | — | — | — | No lleva campos |
| `Usuario` | `nombre` | 1 | `string` | Nombre del usuario, en minúsculas |
| `Usuario` | `pendientes` | 2 | `int32` | Notificaciones sin leer |
| `UsuariosRespuesta` | `usuarios` | 1 | `repeated Usuario` | Un elemento por usuario |
| `EnviarSolicitud` | `id_solicitud` | 1 | `string` | Lo genera el cliente y lo repite igual en cada reintento |
| `EnviarSolicitud` | `origen` | 2 | `string` | Quién envía |
| `EnviarSolicitud` | `destino` | 3 | `string` | Quién recibe |
| `EnviarSolicitud` | `texto` | 4 | `string` | Texto del mensaje; puede contener espacios |
| `EnviarRespuesta` | `destino` | 1 | `string` | Destino del envío |
| `EnviarRespuesta` | `pendientes` | 2 | `int32` | Pendientes del destino después de aplicar |
| `LeerSolicitud` | `id_solicitud` | 1 | `string` | Igual que en `Enviar` |
| `LeerSolicitud` | `usuario` | 2 | `string` | De quién se lee |
| `LeerSolicitud` | `cantidad` | 3 | `int32` | Cuántos pendientes descontar |
| `LeerRespuesta` | `usuario` | 1 | `string` | Usuario leído |
| `LeerRespuesta` | `pendientes` | 2 | `int32` | Pendientes que quedan |
| `LeerRespuesta` | `mensajes` | 3 | `repeated string` | Textos entregados, del más antiguo al más nuevo, como `origen:texto` |
| `RegistrarSolicitud` | `id_solicitud` | 1 | `string` | Igual que en `Enviar`. Mensaje nuevo, no reutiliza números de otro mensaje |
| `RegistrarSolicitud` | `usuario` | 2 | `string` | Nombre a crear, una sola palabra |
| `RegistrarRespuesta` | `usuario` | 1 | `string` | Nombre creado, en minúsculas |
| `RegistrarRespuesta` | `pendientes` | 2 | `int32` | Queda en 0 |

`Registrar` se agregó como rpc y mensajes nuevos. Los números de `Enviar`, `Leer` y `Usuarios` no se modificaron.

## Decisiones
- ¿Por qué la operación nueva es o no es idempotente?

`Registrar` no es idempotente. La primera llamada crea el usuario y responde OK con pendientes 0. Una segunda llamada, con otro `id_solicitud`, no crea un duplicado, pero responde `FAILED_PRECONDITION` `USUARIO_EXISTE` en lugar del mismo OK. Quien reintenta porque no vio la respuesta no distingue "el alta falló" de "el alta ya se había aplicado". Por eso lleva `id_solicitud`: con `DEDUP` el servidor devuelve el OK guardado y no vuelve a ejecutar el alta.

- ¿Qué pasaría si un cliente antiguo, que no conoce la operación nueva, sigue llamando al servidor? (pista, compatibilidad de Protocol Buffers)

Sigue funcionando. Ese cliente llama a `Usuarios`, `Enviar` y `Leer`, y esos métodos conservan sus mensajes y sus números de campo. En Protocol Buffers por la red viaja el número, no el nombre. Agregar un rpc y mensajes nuevos es compatible hacia atrás: el cliente antiguo simplemente no llama a `Registrar`, y si apareciera un campo con un número que no conoce lo ignora. Al revés, un servidor que todavía no tiene `Registrar` responde `UNIMPLEMENTED` cuando le llega esa llamada.

- Prueba realizada (comando y salida)

Stubs regenerados dentro del contenedor y prueba desde el cliente, con el servidor en `FALLA=no`:

```
docker compose run --rm --no-deps servidor sh generar.sh
docker compose up -d
docker compose exec cliente python cliente_grpc.py usuarios
docker compose exec cliente python cliente_grpc.py registrar carol
docker compose exec cliente python cliente_grpc.py usuarios
docker compose exec cliente python cliente_grpc.py enviar carol ana "hola semana 11"
docker compose exec cliente python cliente_grpc.py leer ana 1
docker compose exec cliente python cliente_grpc.py registrar carol
```

```
[cliente] intento 1, id_solicitud=-, deadline 2 s
[cliente]   ana=100, beto=100
[cliente] intento 1, id_solicitud=f8a171ed, deadline 2 s
[cliente]   OK carol pendientes=0
[cliente] intento 1, id_solicitud=-, deadline 2 s
[cliente]   ana=100, beto=100, carol=0
[cliente] intento 1, id_solicitud=38dc6cce, deadline 2 s
[cliente]   OK ana pendientes=101
[cliente] intento 1, id_solicitud=327bf13d, deadline 2 s
[cliente]   OK ana pendientes=100 mensajes=carol:hola semana 11
[cliente] intento 1, id_solicitud=c0f15c5c, deadline 2 s
[cliente]   FAILED_PRECONDITION, USUARIO_EXISTE
```
