# Reporte de Servicios Cliente-Servidor

**Equipo** SD-Jaune-Asencio
**Integrantes** Diego Jaune y Sebastián Asencio
**Dominio** Mensajería instantánea
**Repositorio** https://github.com/Tiannn21/sd-jaune-asencio
**Fecha** 20-11-2026

Para la presentación elegimos gRPC. En un chat lo más grave es que un mensaje llegue repetido o se pierda. La evidencia muestra envíos duplicados con JSON-RPC, gRPC y Pyro5 cuando no se deduplican las solicitudes. Nuestra implementación gRPC incorpora una protección ya probada: un identificador de solicitud declarado en el contrato y una tabla de respuestas, además de plazos y códigos de error para orientar los reintentos. Esa protección sigue limitada a la memoria del proceso.

## 1. El servicio y su dominio

El servicio permite que usuarios registrados se manden mensajes de texto. Cada usuario tiene un buzón donde se van guardando los mensajes que recibe, en el orden en que llegan, y un contador de pendientes que baja a medida que los lee (`proyecto/ALCANCE.md`).

Las reglas del dominio están en `semana-11/laboratorio/dominio.py`, que no tiene nada de red. Esto nos permitió usar el mismo archivo con gRPC, JSON-RPC y Pyro5 sin modificarlo.

| Operación | Qué hace | ¿Cambia el estado? |
|---|---|---|
| `usuarios` | Lista a cada usuario con sus pendientes | No |
| `registrar` | Crea un usuario con cero pendientes y buzón vacío | Sí |
| `enviar` | Deja `origen:texto` en el buzón del destino y le suma un pendiente | Sí |
| `leer` | Descuenta pendientes y entrega los mensajes más antiguos primero | Sí |

El servicio parte con dos usuarios, `ana` y `beto`, con 100 pendientes cada uno. Esos 100 vienen de la semana 6 y son solo un contador, no mensajes reales. Todo el estado está en memoria, en un diccionario protegido por un `threading.Lock`. En la semana 6 comprobamos por qué hace falta: veinte clientes descontaron 80 pendientes al mismo tiempo y, sin el candado, `ana` terminó con 86 y 85 en dos corridas, cuando tenía que quedar en 20 (`semana-06/laboratorio/observaciones.md`).

`enviar` y `leer` son las operaciones delicadas, porque cambian el estado y no son idempotentes. Si se aplican dos veces, el destinatario ve el mensaje repetido o pierde mensajes de su buzón.

## 2. Arquitectura y topología

![Arquitectura del servicio con gRPC](img/arquitectura.png)

*Figura 1. Despliegue del servicio con gRPC (`semana-11/laboratorio/docker-compose.yml`).*

El despliegue tiene dos contenedores conectados a la red Docker `sd_net`, los dos construidos con la imagen `sd_grpc:semana11`.

El **`servidor`** (`sd_servidor`) escucha en el puerto 50051, que también está publicado en el anfitrión como `50051 -> 50051`. Atiende las llamadas con un pool de diez hilos (`ThreadPoolExecutor(max_workers=10)`) y es el único nodo que guarda estado: los usuarios y buzones de `dominio.py` y, cuando se activa `DEDUP=1`, la tabla `_vistas`, donde registra cada `id_solicitud` atendido junto con la respuesta que entregó. Con las variables `FALLA`, `DEMORA` y `DEDUP` se cambia su comportamiento ante fallas sin tocar el código.

El **`cliente`** (`sd_cliente`) hace todas las llamadas con el stub `MensajeriaStub`, generado desde el contrato. Encuentra al servidor por su nombre (`servidor:50051`) gracias al DNS de Docker, por lo que no hay IP escritas en el código. Cada llamada tiene un plazo de 2 segundos (`TIMEOUT_CLIENTE`). En las operaciones que cambian el estado, el cliente genera un `id_solicitud` y repite ese mismo valor si tiene que reintentar.

Entre los dos nodos hay una comunicación gRPC, es decir, Protocol Buffers sobre HTTP/2, por TCP en el puerto 50051, hacia los métodos `Usuarios`, `Enviar`, `Leer` y `Registrar` del servicio `mensajeria.v1.Mensajeria`. El cliente se conecta al puerto interno del servidor; no necesita pasar por el puerto publicado en el anfitrión.

Sin sobrescribir variables, Compose inicia con `FALLA=no`, `DEMORA=3`, `DEDUP=0` y `REINTENTOS=0`. Por tanto, la configuración predeterminada no activa la deduplicación ni los reintentos automáticos. El plazo de 2 segundos corresponde a `cliente_grpc.py`; el adaptador gRPC de `medir.py` usa 5 segundos.

## 3. Evolución del contrato

La operación que seguimos es enviar un mensaje, disponible desde la semana 6. La semana 4 es el antecedente del transporte: su contrato contiene `MAYUS hola` y responde `OK HOLA`, pero todavía no tiene usuarios, buzones ni `ENVIAR`. Por eso no presentamos esa llamada como equivalente a un envío ni afirmamos haber ejecutado mensajería en S4. Esta es una limitación de la comparación histórica respecto de seguir la misma operación desde el inicio.

La tabla muestra los ejemplos documentados en cada etapa, conservando sus argumentos originales. Todos los ejemplos desde S6 representan la misma operación del dominio: guardar un texto en el buzón del destinatario y sumar un pendiente.

| Etapa | Semana | Dónde está el contrato | Ejemplo de la misma operación |
|---|---|---|---|
| Antecedente: texto sobre TCP | 4 | `semana-04/semana-04/protocolo.md` | `MAYUS hola` → `OK HOLA`. Todavía no existe la operación de envío. |
| Mensajería sobre TCP | 6 | `semana-06/laboratorio/protocolo.md` | `ENVIAR beto ana hola equipo` → `OK ana 101` |
| REST | 7 | `semana-07/laboratorio/interfaz_http.md` | `POST /mensajes` con `{"origen":"beto","destino":"ana","texto":"hola equipo"}` → `201 {"destino":"ana","pendientes":101,"replica":"api1"}` |
| Mensajes estructurados | 9 | `semana-09/laboratorio/protocolo.md` v3 | 4 bytes de largo + `{"operacion":"ENVIAR","argumentos":["ana","beto","hola semana 9"],"id":7,"version":2}` |
| JSON-RPC | 10 | `semana-10/rpc.py` | `{"jsonrpc":"2.0","method":"enviar","params":{"origen":"ana","destino":"beto","texto":"hola"},"id":1}` → `{"jsonrpc":"2.0","result":{"destino":"beto","pendientes":101},"id":1}` |
| gRPC | 11 | `semana-11/laboratorio/proto/servicio.proto` y `contrato.md` | `stub.Enviar(EnviarSolicitud(id_solicitud="38dc6cce", origen="carol", destino="ana", texto="hola semana 11"))` → `OK ana pendientes=101` |
| Objetos remotos | 12 | `semana-12/laboratorio/objetos.py` | `conv = directorio.abrir_conversacion("ana","beto")`, luego `conv.agregar("hola semana 12")` y `conv.confirmar()` → `{'destino': 'beto', 'pendientes': 101}` |

**De la semana 4 a la 6.** Pasamos de un protocolo de prueba a uno con las operaciones del chat, errores con nombre (`USUARIO_NO_EXISTE`, `FORMATO`) y un servidor que atiende a varios clientes a la vez. El formato seguía siendo frágil: como cada mensaje termina en un salto de línea, el texto no puede tener `\n`, y como los argumentos se separan por espacios, el servidor asume que el texto es todo lo que viene después del destino. Tampoco había versión ni identificador de solicitud.

**REST (semana 7).** Los datos pasaron a tener nombre dentro de un JSON y las rutas pasaron a representar cosas del dominio (`/mensajes`, `/usuarios/{u}/bandeja`). Con eso llegaron los códigos HTTP (404, 409, 503, 504), la validación en la entrada con 422 y dos réplicas detrás de Nginx: cuando apagamos `api1`, `api2` siguió respondiendo. El costo fue un salto más en cada petición, porque la API abría una conexión TCP nueva hacia el servidor cada vez. Además, `POST /mensajes` no llevaba identificador, así que el servidor no tenía cómo reconocer un reintento.

**Mensajes estructurados (semana 9).** Al enmarcar cada mensaje con su largo dejamos de depender del salto de línea, y el texto pasó a ser un argumento propio. Agregamos `version` e `id`. El codec binario usó un 68% menos de bytes que JSON en las solicitudes (26 contra 80) y un 65% menos en las respuestas (`semana-09/laboratorio/observaciones.md`). Lo malo es que el binario no se puede leer y los dos lados tienen que coincidir exactamente: con el servidor en `bin` y el cliente en JSON, la llamada terminó en `struct.error`.

**JSON-RPC (semana 10).** Reemplazamos nuestro formato por uno estándar. `method` y `params` ocuparon el lugar de `operacion` y `argumentos`, HTTP se encargó del enmarcado y los errores usaron códigos conocidos: `-32601` para un método que no existe, `-32602` para parámetros inválidos y `-32000` para errores del dominio. No incorporamos un IDL ni validación generada: tuvimos que validar a mano que `cantidad` fuera entero. El `id` permite asociar cada respuesta con su solicitud; nuestra implementación no lo usa para deduplicar.

**gRPC (semana 11).** El contrato quedó en un archivo `.proto`, y desde él se generan el cliente y el servidor. Los tipos se verifican solos (`int32 cantidad`) y el contrato puede crecer sin romper clientes: agregamos `Registrar` sin cambiar los números de campo que ya existían, así que un cliente que no conoce esa operación puede seguir usando las demás (`contrato.md`). Cada llamada tiene un plazo y los errores llegan clasificados (`INVALID_ARGUMENT`, `FAILED_PRECONDITION`, `UNAVAILABLE`, `DEADLINE_EXCEEDED`). El cambio más importante fue que las operaciones que modifican el estado exigen un `id_solicitud`, y con él el servidor puede reconocer un reintento. Del otro lado, el mensaje volvió a ser binario, hay que regenerar los stubs con `generar.sh` cada vez que cambia el `.proto` y un navegador no puede llamar a gRPC directamente.

**Objetos remotos (semana 12).** Pyro5 trajo algo que no tenía ningún mecanismo anterior: objetos con identidad y ciclo de vida. Una `Conversacion` se crea, se edita y después se confirma o se cancela, y el cliente la usa a través de una referencia (`PYRO:obj_...@servidor:9100`). También ganamos el servicio de nombres y que las excepciones del dominio lleguen al cliente con su clase. Pero el contrato volvió a ser una clase de Python, todo tiene que estar escrito en Python y no llevamos a esta etapa la deduplicación de la semana 11 (`semana-12/laboratorio/README.md`). Aparecieron, además, las referencias a objetos que ya no existen (`unknown object`) y un nuevo punto único de falla en el servicio de nombres.

Las etapas muestran distintas soluciones para las cinco decisiones de la semana 9: enmarcado, versión, identificador, errores y tipos. En nuestra implementación gRPC se combinan HTTP/2, el servicio `mensajeria.v1`, `id_solicitud`, códigos de estado y tipos declarados en Protocol Buffers. Entre las tres implementaciones del servicio comparadas aquí, solo la de gRPC incorpora la deduplicación probada en la semana 11; es una función de nuestra aplicación, no una garantía automática del transporte.

## 4. Mecanismo elegido y justificación

Elegimos gRPC y lo comparamos con JSON-RPC 2.0 y Pyro5. Las primeras filas usan los criterios de ese cuadro (`semana-10/cuadro_comparativo.md`). Las cuatro últimas son lo que necesita nuestro chat.

| Criterio | gRPC (elegido) | JSON-RPC 2.0 | Pyro5 |
|---|---|---|---|
| Modelo | Procedimientos remotos agrupados en un servicio | Procedimientos remotos identificados por nombre | Objetos remotos con identidad y estado propio |
| Contrato | `servicio.proto`, del que se generan los stubs | Sin IDL; el contrato está en la documentación | La clase Python marcada con `@expose` |
| Transporte y formato | HTTP/2 con Protocol Buffers binario | HTTP con JSON en texto | Protocolo propio de Pyro5 sobre TCP |
| Lenguajes | Varios, por la generación de código | Cualquiera que procese JSON | Solo Python |
| Manejo de errores | Códigos de estado gRPC | `error.code` estándar (`-32xxx`) | Excepciones de Python con su clase |
| Reintentar un envío sin duplicarlo | Sin `DEDUP` el reintento se aplicó otra vez (`beto=103`). Con `DEDUP=1`, que usa el `id_solicitud` del contrato, quedó en 101 | La misma solicitud con el mismo `id` se aplicó dos veces (`beto=102`). El `id` sirve para asociar la respuesta, no para detectar reintentos | La misma llamada se aplicó dos veces (`beto=102`). Las llamadas no llevan ningún identificador |
| Limitar la espera y manejar errores | Plazo en cada llamada y códigos `DEADLINE_EXCEEDED` o `UNAVAILABLE`; no permiten distinguir siempre lentitud de caída | Depende del timeout del cliente HTTP | Excepciones de comunicación; el plazo se configura aparte y no lo usamos |
| Saber si conviene reintentar | `INVALID_ARGUMENT` no se reintenta; `UNAVAILABLE` sí | Separa parámetros (`-32602`) y dominio (`-32000`); la especificación no cubre fallos de red | `ErrorParametros` y `ErrorDominio` llegan con su clase; la red, como `CommunicationError` |
| Evolución del contrato | `Registrar` se añadió conservando métodos y números de campo anteriores; compatibilidad prevista por el contrato | Se puede añadir un método; nuestra aplicación valida los parámetros | Añadir un método no obliga por sí solo a cambiar clientes; modificar una firma usada sí puede romperlos |

Lo que más pesa en la decisión es la fila de los reintentos. La evidencia reúne dos envíos iguales en JSON-RPC y Pyro5, y tres intentos con el mismo identificador en gRPC sin deduplicación (`docs/informe/evidencia/reintentos.md`). JSON-RPC y Pyro5 dejaron `beto=102` con `ana:hola` repetido; gRPC sin deduplicación dejó `beto=103` (`semana-11/laboratorio/observaciones.md`, caso 3). Es una comparación del efecto de repetir un envío, no un experimento con igual número de intentos ni idéntica inyección de fallos. Ningún mecanismo evita la duplicación por sí solo: esa protección pertenece a la aplicación.

La diferencia práctica está en el trabajo ya realizado en nuestro servicio. En gRPC, `id_solicitud` es un campo del contrato en cada operación que cambia el estado, y el servidor rechaza con `INVALID_ARGUMENT` las solicitudes que no lo traen. Con `DEDUP=1`, el reintento recibió la respuesta guardada y `beto` quedó en 101 (caso 4). El cliente reintenta `UNAVAILABLE` y `DEADLINE_EXCEEDED` hasta su límite configurado; esos códigos no prueban que la operación haya quedado sin ejecutar. En JSON-RPC también podríamos acordar una clave estable y deduplicar; el `id` actual solo correlaciona respuestas, y una solicitud sin `id` se trata como notificación. En Pyro5 podríamos añadir un identificador a los métodos que modifican estado. Elegimos gRPC porque esa protección ya está implementada y probada en nuestro servicio, junto con el contrato tipado y los plazos, aunque todavía falta persistir el estado y la deduplicación.

## 5. Evidencia de funcionamiento y medición

Estas llamadas se hicieron desde el contenedor `sd_cliente` hacia `sd_servidor`, usando `servidor:50051` dentro de la red `sd_net` (`semana-11/laboratorio/contrato.md`):

```text
$ docker compose exec cliente python cliente_grpc.py registrar carol
[cliente] intento 1, id_solicitud=f8a171ed, deadline 2 s
[cliente]   OK carol pendientes=0
$ docker compose exec cliente python cliente_grpc.py enviar carol ana "hola semana 11"
[cliente] intento 1, id_solicitud=38dc6cce, deadline 2 s
[cliente]   OK ana pendientes=101
$ docker compose exec cliente python cliente_grpc.py leer ana 1
[cliente] intento 1, id_solicitud=327bf13d, deadline 2 s
[cliente]   OK ana pendientes=100 mensajes=carol:hola semana 11
```

`carol` se registró, le envió un mensaje a `ana` y `ana` lo leyó desde su buzón. Desde el mismo cliente, una llamada a un método inexistente respondió `StatusCode.UNIMPLEMENTED`.

Para la medición usamos la consulta `usuarios`, con 200 llamadas en cada mecanismo. No modifica usuarios, buzones ni pendientes. En los tres casos termina en `dominio.usuarios()`; los archivos de dominio de S11 y S12 son iguales. Los adaptadores sí difieren: Pyro5 incrementa además un contador de telemetría. Por eso comparamos estas implementaciones completas, sin atribuir toda diferencia exclusivamente al protocolo.

`medir.py` hace una consulta para obtener el tamaño, diez llamadas de calentamiento y luego las 200 llamadas medidas, en serie, con `time.perf_counter()`. gRPC y JSON-RPC se miden con el script de `semana-11/laboratorio`; Pyro5, con el de `semana-12/laboratorio`. El detalle y los comandos para repetir el procedimiento están en `docs/informe/evidencia/medicion.md`. Son instrucciones de reproducción, no nuevas ejecuciones.

| Mecanismo | Operación | n | p50 ms | p95 ms | media ms | máx ms | respuesta bytes |
|---|---|---|---|---|---|---|---|
| grpc | usuarios | 200 | 1.42 | 2.17 | 1.5 | 2.71 | 19 |
| jsonrpc | usuarios | 200 | 1.11 | 1.46 | 1.12 | 2.96 | 56 |
| pyro | usuarios | 200 | 0.46 | 0.62 | 0.49 | 1.41 | 48 |

Los resultados están en `semana-11/laboratorio/mediciones.csv` y `semana-12/laboratorio/mediciones.csv`. Esos archivos contienen una corrida por mecanismo; no se presenta una segunda corrida ni se afirma repetibilidad entre ejecuciones. Los CSV no registran hardware, carga del anfitrión ni todas las variables del entorno, lo que limita la comparación y su reproducción exacta.

En esta corrida, gRPC tuvo la mayor media (1,50 ms), seguido por JSON-RPC (1,12 ms) y Pyro5 (0,49 ms). La media de gRPC fue aproximadamente 3,06 veces la de Pyro5. El formato binario, por sí solo, no predijo la menor latencia. El procesamiento HTTP/2, la asignación al pool de hilos, la serialización, el manejo de conexiones y la carga del anfitrión son posibles explicaciones. No medimos cada componente por separado, por lo que estas son hipótesis y no causas demostradas por la tabla.

En tamaño, el valor registrado para gRPC fue 19 bytes, contra 48 de Pyro5 y 56 de JSON-RPC. El script usa `ByteSize()` para el mensaje Protocol Buffers, el largo del cuerpo HTTP para JSON-RPC y una serialización local con `serpent.dumps()` del resultado para Pyro5. Son tamaños de representación de la respuesta, no tráfico total capturado en la red; no incluyen todos los encabezados ni el enmarcado. La distancia relativa entre p95 y p50 fue aproximadamente 53% en gRPC, 32% en JSON-RPC y 35% en Pyro5, sin que eso mida variabilidad entre corridas.

Para nuestro prototipo, priorizamos evitar mensajes repetidos frente a una diferencia media de aproximadamente un milisegundo en esta consulta. La medición no cambia la elección de gRPC, pero tampoco demuestra que su deduplicación tenga ese costo: `Usuarios` no pasa por la ruta que deduplica los envíos. Para evaluar capacidad y costo de esa protección harían falta pruebas concurrentes y mediciones de operaciones que modifican estado, con y sin deduplicación. Esas pruebas no forman parte de la evidencia disponible.

## 6. Análisis de fallos

Usamos tres semánticas de invocación (Tanenbaum y Van Steen, 2017, cap. 8). En *maybe*, una falla puede dejar al cliente sin saber si la operación se ejecutó. *At-least-once* busca obtener al menos una ejecución mediante reintentos, con riesgo de duplicados; no asegura progreso frente a una indisponibilidad permanente. *At-most-once* evita aplicar más de una vez una misma solicitud, pero no garantiza que llegue a ejecutarse ni que el cliente reciba la respuesta.

Las observaciones provienen de `semana-11/laboratorio/observaciones.md`, secciones 3 y 4, y `semana-12/laboratorio/observaciones.md`, paso 5. En S11 se distingue la demora después de aplicar el cambio (`FALLA=siempre`) de matar realmente el proceso durante la llamada.

| Falla provocada | Qué esperaban según la teoría | Qué observaron | Qué harían para tolerarla |
|---|---|---|---|
| Servidor cae a mitad de una llamada (S11), y ensayo relacionado de respuesta demorada | Si el cambio se aplica y no llega la respuesta, el cliente queda en incertidumbre (*maybe*). Reintentar sin deduplicar puede repetir el cambio | Al matar el proceso: `UNAVAILABLE, Socket closed`; al reiniciar, `ana=100` y `beto=100`. En el ensayo de demora, sin reinicio: un intento dejó `beto=101`; tres intentos sin deduplicar, 103; con `DEDUP=1`, 101 | Conservar el mismo `id_solicitud` y activar `DEDUP`. Persistir juntos el cambio del dominio y su resultado deduplicado, en una transacción, para sobrevivir a reinicios |
| Servidor cae y vuelve (semana 12) | Con el estado solo en memoria y sin réplica, se pierde todo lo hecho | El observador recibió `ConnectionClosedError` y un cliente nuevo no pudo conectarse. Al volver, `ana=100` y `beto=100`: se perdieron el mensaje y el usuario de prueba, y la conversación pendiente terminó con error | Guardar buzones y usuarios en un volumen (SQLite, como en `ALCANCE.md`) y, para alta disponibilidad, replicar el servidor |
| Servidor de nombres cae (semana 12) | El servicio de nombres solo se usa para resolver, así que una conexión abierta debería seguir funcionando | El observador conectado siguió funcionando y un cliente nuevo falló con `Failed to locate the nameserver`. Al volver, el registro estaba vacío (`unknown name`) hasta que reiniciamos el servidor | Volver a registrar el nombre cada cierto tiempo (`REREGISTRO=5`) o resolver por el DNS de Docker, como hacemos con gRPC |

Las observaciones son consistentes con la incertidumbre ante una respuesta perdida y con la pérdida del estado en memoria. En S11, una llamada iniciada con el contenedor ya apagado esperó 2 segundos y respondió `DEADLINE_EXCEEDED`; al cortar una conexión activa apareció `UNAVAILABLE`. Por eso un código aislado no distingue siempre un servidor lento de uno caído. El timeout solo acota la espera, como en el ensayo sin red de S4 (`semana-04/semana-04/observaciones.md`). En Pyro5, nombres volvió vacío: es una dependencia adicional para clientes nuevos, ausente como contenedor separado en nuestro despliegue gRPC. Este último sigue dependiendo del servidor y de la resolución de Docker. `REREGISTRO=5` es una mitigación analizada en el código de S12, no medida en el ensayo, que usó `REREGISTRO=0`.

**Semántica actual.** Con los valores predeterminados de Compose (`REINTENTOS=0`, `DEDUP=0`), una falla de red en `enviar`, `leer` o `registrar` deja al cliente en *maybe*. Con reintentos y sin deduplicación se observaron ejecuciones repetidas, como en una estrategia *at-least-once*, pero el cliente limita los intentos y puede agotarlos sin obtener confirmación: no garantiza una ejecución ante cualquier falla. Con `DEDUP=1`, la prueba mostró *at-most-once* para reintentos con el mismo identificador durante la vida del proceso. La tabla `_vistas` está en memoria y no protege después de reiniciar. `usuarios` no cambia el dominio y puede reintentarse sin duplicar mensajes.

**Semántica necesaria.** El chat necesita evitar mensajes duplicados y conservar los envíos confirmados después de un reinicio. El objetivo es un efecto único y durable por solicitud, con recuperación de su resultado cuando vuelve la conectividad. Para alcanzarlo faltan almacenamiento persistente, deduplicación persistida de forma atómica con el cambio y una política de recuperación de solicitudes pendientes en el cliente. Guardar solamente la tabla de identificadores no basta si se pierde el buzón. La entrega exactamente una vez de extremo a extremo no está demostrada por estas pruebas. Elegimos gRPC como base porque ya integra contrato tipado, plazos y deduplicación local comprobada, no porque por sí solo garantice ese objetivo.

## 7. Referencias

Tanenbaum, A. S., y Van Steen, M. (2017). *Distributed Systems* (3.ª ed.). Maarten van Steen. Capítulo 4, "Communication", y capítulo 8, "Fault tolerance".

gRPC Authors. (s. f.). *Core concepts, architecture and lifecycle*. https://grpc.io/docs/what-is-grpc/core-concepts/

JSON-RPC Working Group. (2013). *JSON-RPC 2.0 Specification*. https://www.jsonrpc.org/specification

de Jong, I. (s. f.). *Pyro5 documentation*. https://pyro5.readthedocs.io/
