# Interfaz HTTP del servicio (anexo de protocolo.md)

Esta sección describe la puerta HTTP que traduce esas operaciones.
Otro equipo debe poder usar la API leyendo solo este anexo y el protocolo v3.

Equipo SD-Jaune-Asencio (Diego Jaune y Sebastián Asencio). Dominio: mensajería instantánea.

## 9.1 Identificación

| Campo                     | Valor                                                                    |
| ------------------------- | ------------------------------------------------------------------------ |
| Equipo                    | SD-Jaune-Asencio (Diego Jaune y Sebastián Asencio)                       |
| Dominio                   | Mensajería instantánea                                                   |
| Entrada única             | `http://localhost:8080` (Nginx)                                          |
| Formato                   | JSON, UTF-8                                                              |
| Documentación interactiva | `http://localhost:8080/docs`                                             |
| Réplicas de la API        | api1, api2. El campo `replica` de cada respuesta dice cuál atendió       |
| Dónde vive el estado      | En el servidor TCP (usuarios, pendientes y buzón). La API no guarda nada |

Cada petición HTTP abre su propia conexión TCP al servidor, envía un mensaje enmarcado (`codec.enviar` / `codec.recibir`, el mismo `CODEC` que el servidor) y la cierra. No hay sesión HTTP: `HOLA` y `SALIR` no se usan por esta puerta.

Estado inicial, el de la sección 7: `ana` y `beto`, cada uno con 100 pendientes y buzón vacío. Los nombres de usuario son una palabra de 1 a 30 caracteres (letras, dígitos o `_`). El servidor los guarda en minúsculas. El texto del mensaje conserva mayúsculas y puede llevar espacios.

## 9.2 Tabla de traducción, operación por operación

| Operación                    | Método y ruta HTTP            | Cuerpo JSON                                                    | Respuesta correcta                                                         | Código |
| ------------------------------ | ----------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------- | ------ |
| (no llama al servidor)         | `GET /salud`                  | (sin cuerpo)                                                   | `{"estado": "ok", "replica": "api1"}`                                      | 200    |
| `USUARIOS`                     | `GET /usuarios`               | (sin cuerpo)                                                   | `{"usuarios": {"ana": 100, "beto": 100}, "replica": "api1"}`               | 200    |
| `BANDEJA ana`                  | `GET /usuarios/ana/bandeja`   | (sin cuerpo)                                                   | `{"usuario": "ana", "pendientes": 100, "mensajes": "", "replica": "api2"}` | 200    |
| `REGISTRAR carol`              | `POST /usuarios`              | `{"usuario": "carol"}`                                         | `{"usuario": "carol", "pendientes": 0, "replica": "api1"}`                 | 201    |
| `ENVIAR beto ana hola equipo`  | `POST /mensajes`              | `{"origen": "beto", "destino": "ana", "texto": "hola equipo"}` | `{"destino": "ana", "pendientes": 101, "replica": "api1"}`                 | 201    |
| `LEER ana 1`                   | `POST /usuarios/ana/lecturas` | `{"cantidad": 1}`                                              | `{"usuario": "ana", "pendientes": 99, "mensajes": "", "replica": "api2"}`  | 201    |

`GET /salud` solo dice que esa réplica está viva. No mira el servidor TCP: puede responder 200 aunque el servidor esté caído.

`BANDEJA` no consume mensajes. Si hay textos, `mensajes` los trae del más antiguo al más nuevo, separados por `|`, como en la sección 4. Ejemplo: `"beto:hola equipo"`.

`ENVIAR` exige que origen y destino ya existan. Suma 1 a los pendientes del destino y agrega el texto a su buzón.

`LEER` descuenta `cantidad` pendientes y, si el buzón tiene textos, los saca en orden FIFO y los devuelve en `mensajes`. Los 100 pendientes iniciales no tienen texto, así que `mensajes` llega vacío.

## 9.3 Tabla de errores

| Situación                                                  | Error del servidor           | Código HTTP | Quién responde            |
| ---------------------------------------------------------- | -------------------------------- | ----------- | ------------------------- |
| El usuario no existe                                       | `ERROR USUARIO_NO_EXISTE`        | 404         | la API                    |
| `REGISTRAR` con un nombre que ya existe                    | `ERROR USUARIO_EXISTE`           | 409         | la API                    |
| `LEER` pide más pendientes de las que hay                  | `ERROR SIN_MENSAJES <actual>`    | 409         | la API                    |
| El servidor rechaza el formato de la operación             | `ERROR FORMATO …`                | 400         | la API                    |
| El servidor no implementa el comando                       | `ERROR COMANDO_DESCONOCIDO`      | 501         | la API                    |
| Ruta, usuario o cuerpo mal formados, o texto vacío         | (no llega al servidor)           | 422         | la API, antes de traducir |
| El servidor TCP no está disponible, o cierra sin responder | (sin respuesta)                  | 503         | la API                    |
| El servidor TCP no responde en 3 s                         | (sin respuesta)                  | 504         | la API                    |
| La API no logra interpretar una respuesta `OK`             | (respuesta ilegible)             | 502         | la API                    |
| No queda ninguna réplica de la API                         | (sin respuesta de la API)        | 502         | Nginx                     |

El cuerpo de error de la API es JSON, con `error`, a veces `detalle`, y `replica`. Un 422 de validación usa el formato de error de FastAPI. Ningún error modifica el estado del servidor.

## 9.4 Decisiones de diseño

- Los recursos son los sustantivos del dominio, no los verbos del protocolo. `/usuarios` es la colección de cuentas. `/usuarios/{usuario}/bandeja` es el buzón de una cuenta y solo se lee. `/mensajes` es el recurso que se crea al enviar. `/usuarios/{usuario}/lecturas` es la lectura que descuenta pendientes de esa cuenta. Así un cliente HTTP no tiene que conocer `ENVIAR` ni `LEER` para saber qué está modificando.
- No se expusieron `HOLA`, `SALIR` ni `ESPERA`. `HOLA` y `SALIR` abren y cierran una sesión TCP; cada petición HTTP ya es una conexión aparte, de una sola línea, así que no hay sesión que saludar ni que cerrar. `ESPERA` no cambia el estado: duerme un hilo del servidor para medir concurrencia. Publicarla permitiría bloquear hilos a propósito.
- Antes de traducir, la API exige un usuario de 1 a 30 caracteres (`letras`, dígitos o `_`), un texto que no esté vacío y una `cantidad` mayor que 0. Si no lo hiciera, un nombre con espacio partiría la línea TCP en argumentos de más y el servidor respondería `ERROR FORMATO`, o un texto vacío llegaría igual al estado compartido. El 422 corta eso en la puerta, sin depender de cuál réplica hable con el servidor.
