# Protocolo de aplicación — versión 2

Servidor de mensajería instantánea del equipo SD-Jaune-Asencio.
Otro equipo debe poder escribir un cliente compatible leyendo solo este documento.

## 1. Identificación

| Campo                               | Valor                                                        |
| ----------------------------------- | ------------------------------------------------------------ |
| Equipo                              | SD-Jaune-Asencio (Diego Jaune y Sebastián Asencio)           |
| Dominio del servicio                | Mensajería instantánea                                       |
| Versión del protocolo               | 2.0                                                          |
| Transporte                          | TCP, puerto 5000                                             |
| Codificación                        | UTF-8, un mensaje por línea, terminador `\n`                 |
| Modelo de concurrencia del servidor | hilo por cliente                                             |
| Timeout de inactividad              | 60 s (el servidor cierra la conexión)                        |

## 2. Formato general

- Petición: `COMANDO [argumentos separados por espacio]\n`
- Respuesta correcta: `OK [datos]\n`
- Respuesta de error: `ERROR CODIGO [detalle]\n`
- El servidor responde exactamente una línea por cada línea recibida.
- Los comandos no distinguen mayúsculas. Los nombres de usuario tampoco: se guardan en minúsculas.
- El texto de un mensaje sí distingue mayúsculas y puede contener espacios. No puede contener `\n`, porque el salto de línea cierra el mensaje.
- Los nombres de usuario son una sola palabra, sin espacios.

## 3. Secuencia de una sesión

```
cliente                          servidor
   |--- HOLA <nombre> ------------->|
   |<-- OK HOLA <nombre> -----------|
   |--- <operaciones...> ---------->|
   |<-- OK ... / ERROR ... ---------|
   |--- SALIR --------------------->|
   |<-- OK CHAO --------------------|   (el servidor cierra)
```

`HOLA` no es obligatorio. Si no se envía, el servidor igual acepta el resto de los comandos. Si se envía sin nombre, responde `OK HOLA anonimo`. `HOLA` no registra al usuario ni cambia el estado compartido: para existir en el servicio hay que usar `REGISTRAR`, o ser uno de los usuarios iniciales (`ana`, `beto`).

## 4. Operaciones

| Comando   | Argumentos                    | Respuesta OK                                      | Errores posibles                                      | ¿Modifica estado compartido? |
| --------- | ----------------------------- | ------------------------------------------------- | ----------------------------------------------------- | ---------------------------- |
| HOLA      | nombre (opcional)             | `OK HOLA nombre`                                  | —                                                     | no                           |
| USUARIOS  | —                             | `OK usuario:pendientes usuario:pendientes …`      | `ERROR FORMATO USUARIOS`                              | no                           |
| BANDEJA   | usuario                       | `OK usuario pendientes:N [origen:texto \| …]`     | `ERROR FORMATO …`, `ERROR USUARIO_NO_EXISTE`          | no                           |
| REGISTRAR | usuario                       | `OK usuario 0`                                    | `ERROR FORMATO …`, `ERROR USUARIO_EXISTE`             | sí                           |
| ENVIAR    | origen destino texto          | `OK destino nuevo_total`                          | `ERROR FORMATO …`, `ERROR USUARIO_NO_EXISTE`          | sí                           |
| LEER      | usuario cantidad              | `OK usuario nuevo_total [origen:texto \| …]`      | `ERROR FORMATO …`, `ERROR USUARIO_NO_EXISTE`, `ERROR SIN_MENSAJES actual` | sí |
| ESPERA    | segundos                      | `OK ESPERA seg`                                   | `ERROR FORMATO ESPERA <segundos>`                     | no                           |
| SALIR     | —                             | `OK CHAO`                                         | —                                                     | no                           |

Detalle de cada operación del dominio:

- `USUARIOS` lista todos los usuarios y cuántas notificaciones pendientes tiene cada uno, ordenados por nombre. Ejemplo: `OK ana:100 beto:100`.
- `BANDEJA ana` no consume nada. Si no hay textos guardados responde `OK ana pendientes:100`. Si hay textos, los agrega separados por ` | `, del más antiguo al más nuevo: `OK ana pendientes:101 beto:hola`.
- `REGISTRAR carol` crea el usuario con 0 pendientes y buzón vacío. Responde `OK carol 0`.
- `ENVIAR beto ana hola equipo` guarda el texto `hola equipo` en el buzón de `ana`, suma 1 a sus pendientes y responde `OK ana 101`. Origen y destino tienen que existir. El texto es todo lo que sigue al destino, incluidos los espacios.
- `LEER ana 1` descuenta esa cantidad de pendientes. Si el buzón tiene textos, entrega hasta esa cantidad (FIFO) y los saca del buzón. Los 100 pendientes iniciales no tienen texto: `LEER ana 1` sobre el estado inicial responde `OK ana 99`. `cantidad` es un entero mayor que 0.
- `ESPERA` espera los segundos indicados (número entero o decimal) y no toca el estado. Sirve para medir concurrencia. No usa el candado.

Estado inicial: usuarios `ana` y `beto`, cada uno con 100 pendientes y buzón vacío.

## 5. Códigos de error

| Código              | Cuándo se produce                                                        |
| ------------------- | ------------------------------------------------------------------------ |
| COMANDO_DESCONOCIDO | el comando no está en la tabla, o la línea llega vacía                   |
| FORMATO             | faltan o sobran argumentos, o el tipo es incorrecto                      |
| USUARIO_NO_EXISTE   | el usuario no está registrado                                            |
| USUARIO_EXISTE      | `REGISTRAR` con un nombre que ya existe                                  |
| SIN_MENSAJES        | `LEER` pide más pendientes de las que el usuario tiene; el detalle es el total actual |

Un error no modifica el estado. La conexión sigue abierta.

## 6. Comportamiento ante situaciones anómalas

| Situación                                      | Qué hace el servidor                                                                                      |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Línea vacía                                    | responde `ERROR COMANDO_DESCONOCIDO`                                                                      |
| Cliente inactivo 60 s                          | cierra la conexión sin mensaje                                                                            |
| Cliente se desconecta a mitad de una operación | registra `se desconecto abruptamente` y sigue atendiendo a los demás                                      |
| Dos clientes modifican el mismo dato a la vez  | `ENVIAR` y `LEER` se serializan con un Lock; el resultado es el mismo que si hubieran llegado una tras otra |
| Bytes no decodificables en UTF-8               | se reemplazan por U+FFFD y la línea se procesa igual; la conexión no se cierra                            |

## 7. Estado compartido

| Dato        | Tipo                         | Valor inicial              | Quién lo modifica        |
| ----------- | ---------------------------- | -------------------------- | ------------------------ |
| usuarios    | dict usuario → pendientes    | ana 100, beto 100          | REGISTRAR, ENVIAR, LEER  |
| buzon       | dict usuario → lista de textos | ana [], beto []          | ENVIAR (agrega), LEER (saca) |
| operaciones | int                          | 0                          | toda operación del dominio, incluida ESPERA |

`HOLA` y `SALIR` no incrementan `operaciones`.

## 8. Historial de cambios

| Versión | Fecha      | Cambio                                                                                          |
| ------- | ---------- | ----------------------------------------------------------------------------------------------- |
| 1.0     | semana 4   | protocolo inicial de la semana 4 (HOLA, ECO, CONTAR, HORA, SUMA, SALIR), servidor secuencial   |
| 2.0     | 05-10-2026 | dominio de mensajería, servidor concurrente con Lock, errores y timeout documentados           |
