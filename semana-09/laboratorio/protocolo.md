# Protocolo del servicio — versión 3 (Semana 9)

Servidor de mensajería instantánea del equipo SD-Jaune-Asencio.
Otro equipo debe poder escribir un cliente compatible leyendo solo este documento.

Reemplaza al protocolo v2 de la semana 6. Cambia el formato del mensaje
(ya no es una línea de texto) y se agregan las secciones 7 y 8.

## 1. Identificación

| Campo                  | Valor                                                   |
| ---------------------- | ------------------------------------------------------- |
| Equipo                 | SD-Jaune-Asencio (Diego Jaune y Sebastián Asencio)      |
| Dominio                | Mensajería instantánea                                  |
| Versión del protocolo  | 2 (campo `version` del mensaje)                         |
| Versión del documento  | 3                                                       |
| Transporte             | TCP, puerto 5000 dentro de `sd_net`                     |
| Modelo de concurrencia | hilo por cliente                                        |
| Timeout del servidor   | 30 s esperando un mensaje completo (`TIMEOUT_SERVIDOR`) |

## 2. Formato del mensaje

Cada mensaje viaja enmarcado: 4 bytes con el largo (entero sin signo, big-endian) seguidos del cuerpo.

```
+------------+------------------------+
| largo (4B) | cuerpo (largo bytes)   |
+------------+------------------------+
```

El cuerpo se codifica con uno de dos codecs, elegido por la variable `CODEC`. Cliente y servidor deben usar el mismo.

Los nombres de usuario no distinguen mayúsculas: se guardan en minúsculas. El texto de un mensaje sí distingue mayúsculas y puede contener espacios. Los nombres de usuario son una sola palabra, sin espacios.

### 2.1 Solicitud (cliente → servidor)

| Campo        | Tipo            | Descripción                                                   |
| ------------ | --------------- | ------------------------------------------------------------- |
| `version`    | entero          | Versión del protocolo. El servidor rechaza las distintas de 2 |
| `id`         | entero          | Correlativo del cliente. La respuesta trae el mismo id        |
| `operacion`  | texto           | Nombre de la operación en mayúsculas                          |
| `argumentos` | lista de textos | Argumentos de la operación, puede ser vacía                   |

### 2.2 Respuesta (servidor → cliente)

| Campo    | Tipo            | Descripción                                                  |
| -------- | --------------- | ------------------------------------------------------------ |
| `id`     | entero          | Mismo id de la solicitud (0 si no se pudo leer la solicitud) |
| `estado` | `OK` o `ERROR`  | Resultado                                                    |
| `datos`  | lista de textos | Resultado cuando estado es OK                                |
| `error`  | texto           | Código y detalle cuando estado es ERROR                      |

### 2.3 Codec `json`

Cuerpo en JSON UTF-8 con los campos anteriores como claves.

```json
{
  "operacion": "ENVIAR",
  "argumentos": ["ana", "beto", "hola semana 9"],
  "id": 7,
  "version": 2
}
```

### 2.4 Codec `bin`

Cuerpo binario con `struct`, big-endian. Los textos van con largo prefijado de 2 bytes y las listas con cantidad prefijada de 1 byte.

```
Solicitud: version(1B) id(4B) operacion(2B+texto) n_args(1B) [arg(2B+texto)]*
Respuesta: id(4B) estado(1B: 0=OK 1=ERROR) n_datos(1B) [dato(2B+texto)]* error(2B+texto)
```

## 3. Operaciones

`HOLA` no es obligatorio y no registra al usuario. Para existir en el servicio hay que usar `REGISTRAR`, o ser uno de los usuarios iniciales (`ana`, `beto`).

| Operación   | Argumentos             | Respuesta OK (`datos`)                                    | Errores posibles                                                                |
| ----------- | ---------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `HOLA`      | nombre (opcional)      | `HOLA`, nombre                                            | —                                                                               |
| `USUARIOS`  | —                      | un `usuario:pendientes` por usuario, ordenados por nombre | `FORMATO USUARIOS`                                                              |
| `BANDEJA`   | usuario                | usuario, pendientes, y cada texto del buzón               | `FORMATO BANDEJA <usuario>`, `USUARIO_NO_EXISTE`                                |
| `REGISTRAR` | usuario                | usuario, `0`                                              | `FORMATO REGISTRAR <usuario>`, `USUARIO_EXISTE`                                 |
| `ENVIAR`    | origen, destino, texto | destino, pendientes nuevos                                | `FORMATO ENVIAR <origen> <destino> <texto>`, `USUARIO_NO_EXISTE`                |
| `LEER`      | usuario, cantidad      | usuario, pendientes nuevos, y los textos entregados       | `FORMATO LEER <usuario> <cantidad>`, `USUARIO_NO_EXISTE`, `SIN_MENSAJES actual` |
| `ESPERA`    | segundos               | `ESPERA`, segundos                                        | `FORMATO ESPERA <segundos>`                                                     |
| `SALIR`     | —                      | `CHAO`. Cierra la conexión                                | —                                                                               |

- `USUARIOS` lista todos los usuarios y cuántas notificaciones pendientes tiene cada uno. Ejemplo de `datos`: `ana:100`, `beto:100`.
- `BANDEJA` no consume nada. Los textos van del más antiguo al más nuevo, cada uno como un elemento de `datos` (`origen:texto`).
- `REGISTRAR carol` crea el usuario con 0 pendientes y buzón vacío.
- `ENVIAR ana beto hola semana 9` guarda `ana:hola semana 9` en el buzón de `beto` y suma 1 a sus pendientes. Origen y destino tienen que existir. El texto es un solo argumento y puede llevar espacios.
- `LEER ana 1` descuenta esa cantidad de pendientes. Si el buzón tiene textos, entrega hasta esa cantidad (FIFO) y los saca. Los 100 pendientes iniciales no tienen texto. `cantidad` es un entero mayor que 0.
- `ESPERA` espera los segundos indicados y no toca el estado. No usa el candado.

Estado inicial: usuarios `ana` y `beto`, cada uno con 100 pendientes y buzón vacío.

`HOLA` y `SALIR` no incrementan el contador `operaciones`. El resto de las operaciones sí, aunque después respondan error de formato.

## 4. Errores de protocolo

| Situación                          | Reacción del servidor                                                                |
| ---------------------------------- | ------------------------------------------------------------------------------------ |
| `version` distinta de 2            | Responde `ERROR` con el texto `versión X no soportada, use 2` y mantiene la conexión |
| Cuerpo que no se puede decodificar | Responde `ERROR mensaje mal formado (...)` con id 0 y cierra esa conexión            |
| Largo anunciado mayor a 1 MB       | Responde `ERROR` y cierra esa conexión                                               |
| Largo anunciado mayor a lo enviado | Espera hasta `TIMEOUT_SERVIDOR` (30 s) y cierra esa conexión                         |
| Operación desconocida              | Responde `ERROR COMANDO_DESCONOCIDO`                                                 |

Un error de dominio no modifica usuarios, pendientes ni buzón. La conexión sigue abierta.

| Código                | Cuándo se produce                                                                     |
| --------------------- | ------------------------------------------------------------------------------------- |
| `COMANDO_DESCONOCIDO` | la operación no está en la tabla                                                      |
| `FORMATO`             | faltan o sobran argumentos, o el tipo es incorrecto                                   |
| `USUARIO_NO_EXISTE`   | el usuario no está registrado                                                         |
| `USUARIO_EXISTE`      | `REGISTRAR` con un nombre que ya existe                                               |
| `SIN_MENSAJES`        | `LEER` pide más pendientes de las que el usuario tiene; el detalle es el total actual |

## 5. Concurrencia

Un hilo por cliente. El diccionario `estado` es compartido y lo protege un `Lock`: `USUARIOS`, `BANDEJA`, `REGISTRAR`, el leer-sumar-escribir de `ENVIAR`, el leer-restar-sacar de `LEER` y el contador `operaciones`. `ESPERA` duerme fuera del `Lock`.

| Dato        | Tipo                           | Valor inicial     | Quién lo modifica                             |
| ----------- | ------------------------------ | ----------------- | --------------------------------------------- |
| usuarios    | dict usuario → pendientes      | ana 100, beto 100 | `REGISTRAR`, `ENVIAR`, `LEER`                 |
| buzon       | dict usuario → lista de textos | ana [], beto []   | `ENVIAR` agrega, `LEER` saca                  |
| operaciones | int                            | 0                 | toda operación del dominio, incluida `ESPERA` |

Si el cliente se desconecta a mitad de un mensaje, ese hilo cierra solo esa conexión. Los demás siguen.

## 6. Ejemplo de sesión

```
> HOLA ana                         ->  OK HOLA | ana
> ENVIAR ana beto hola semana 9   ->  OK beto | 101
> BANDEJA beto                    ->  OK beto | 101 | ana:hola semana 9
> LEER beto 1                     ->  OK beto | 100 | ana:hola semana 9
> LEER beto 200                   ->  ERROR SIN_MENSAJES 100
> SALIR                           ->  OK CHAO
```

## 7. Medición de codecs

Pendiente: pegar aquí la tabla que imprime `bench_codec.py` y una conclusión de dos líneas.

## 8. Historial de cambios

| Versión doc | Fecha    | Cambio                                                                              |
| ----------- | -------- | ----------------------------------------------------------------------------------- |
| 1           | semana 4 | Protocolo de texto por líneas                                                       |
| 2           | semana 6 | Concurrencia, errores, operaciones de mensajería                                    |
| 3           | semana 9 | Mensaje estructurado, enmarcado por largo, codecs json y bin, versión en el mensaje |
