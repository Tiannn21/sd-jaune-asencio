# Observaciones: objetos distribuidos con Pyro5

Equipo SD-Jaune-Asencio. Integrantes del equipo: Diego Jaune y Sebastián Asencio.
Fecha de ejecución: 13-11-2026. Asistencia presencial: por confirmar por el equipo.
Pruebas ejecutadas con Docker en semana-12/laboratorio/. Se omiten las horas UTC de los logs.

## Paso 1: nombres y servidor arriba

Comando: `docker compose exec cliente python cliente_pyro.py uri`.

```text
sd.jaune-asencio.directorio -> PYRO:directorio@servidor:9100
nombres registrados ['Pyro.NameServer', 'sd.jaune-asencio.directorio']
```

PYRO es el protocolo, directorio el identificador, servidor el nodo de Docker
y 9100 el puerto del daemon. sd.jaune-asencio.directorio es el nombre lógico.
El servidor anuncia servidor, no localhost: localhost desde cliente sería
el contenedor cliente, donde no corre el daemon.

## Paso 2: nuestro dominio como objeto remoto

Se copió dominio.py de semana-11/laboratorio sin modificarlo; hashes SHA-256
idénticos. Se conservan registrar, enviar, leer y usuarios. Las semanas anteriores
trabajaron mensajería por TCP/serialización, JSON-RPC y gRPC; ahora cambia el
transporte y se incorpora identidad y ciclo de vida de objetos remotos.

| Clase | Método | ¿Cambia estado? |
|---|---|---|
| Directorio | usuarios | No el dominio; sí contador de telemetría |
| Directorio | registrar | Sí, crea usuario |
| Directorio | enviar | Sí, texto y pendiente del destinatario |
| Directorio | leer | Sí, retira textos FIFO y pendientes |
| Directorio | abrir_conversacion | Sí, crea objeto remoto |
| Directorio | quien_soy | Sí, contador de instancia |
| Directorio | conversaciones_vivas | Solo contador de telemetría |
| Conversacion | agregar | Sí, reemplaza borrador, aún no envía |
| Conversacion | ver | No, devuelve copia de datos |
| Conversacion | confirmar | Sí, envía y desregistra |
| Conversacion | cancelar | Sí, desregistra sin enviar |

Prueba reproducible: `docker compose exec cliente python pruebas_integracion.py`.
Resultado real:

```text
ErrorDominio USUARIO_EXISTE
ErrorParametros cantidad debe ser un entero mayor que cero
ErrorDominio USUARIO_NO_EXISTE
ErrorDominio SIN_MENSAJES 0
DaemonError unknown object
DaemonError unknown object
ErrorParametros texto vacío
OK: registro, errores, FIFO, copia, referencia, confirmar, cancelar y limpieza
```

Las excepciones llegan con su clase porque el cliente registra ErrorDominio y
ErrorParametros con register_dict_to_class. Las pruebas crean un usuario nuevo,
envían dos mensajes y verifican su lectura en el orden de envío.
Ana y Beto conservan 100 pendientes iniciales aunque sus buzones estén vacíos;
es una particularidad heredada, no cien mensajes reales.

## Paso 3: paso por referencia

Comando ejecutado:
`docker compose exec cliente python cliente_pyro.py conversacion ana beto "hola semana 12" --probar-colgante`.

```text
recibí Proxy, referencia PYRO:obj_917bc8c4eef8449891fdcf0d975d7ea0@servidor:9100
estado en el servidor {'participantes': ['ana', 'beto'], 'texto': 'hola semana 12'}
confirmar -> {'destino': 'beto', 'pendientes': 101}
uso la referencia después de terminar
ERROR del daemon. La referencia apunta a un objeto que ya no existe. unknown object
```

Luego `leer beto 1` devolvió:
```text
{'usuario': 'beto', 'pendientes': 100, 'mensajes': ['ana:hola semana 12']}
```

El mensaje se envió correctamente. El error ocurre al consultar después de
desregistrar la conversación. Cancelar también desregistra, sin enviar.
ver devuelve un diccionario por valor; la prueba modificó esa copia y comprobó
que el borrador del servidor no cambió.

Con POR_VALOR=1, recreando servidor, se obtuvo:
```text
ERROR de serialización. El servidor intentó enviar un objeto por valor. unsupported serialized class: objetos.Conversacion
```

Sin registrar el objeto, Pyro intenta transportarlo por valor. El cliente no tiene
registrado un convertidor autorizado para reconstruir objetos.Conversacion.
No habilitamos esa reconstrucción: el taller busca transportar una referencia.
__getstate__ excluye el RLock local del experimento; de otro modo se producía
antes un TypeError al serializar el bloqueo. Se restauró POR_VALOR=0.

La conversación es un borrador de un solo envío. Si confirmar falla por texto
vacío, permanece viva y puede corregirse o cancelarse. Si se abandona sin terminar,
permanece registrada hasta el reinicio; no hay recolector distribuido ni TTL.

## Paso 4: modo de instancia

Se recreó servidor antes de cada `quien --veces 2`.

| Modo | Proxy A: instancia / llamadas | Proxy B: instancia / llamadas | ¿Comparten contador? |
|---|---|---|---|
| single | 1/1, 1/2 | 1/3, 1/4 | Sí |
| session | 1/1, 1/2 | 2/1, 2/2 | No |

Para estado asociado a una conexión usaríamos session. Para una conversación
identificable preferimos un objeto explícito con referencia y ciclo de vida.
En single se comparte Directorio; en session cambia la instancia y su contador.
Usuarios, buzones y pendientes están en el módulo dominio.py y se comparten en
el proceso en ambos modos. Recrear el proceso sí reinicia ese estado.
Se restauró MODO=single.

## Paso 5: falla en tres tiempos

Se ejecutó vigilar, se envió un mensaje (beto=101) y se abrió una conversación
con --esperar 12. Durante la espera se detuvo servidor; después se inició otra vez.
Con REREGISTRO=0 se detuvo y arrancó nombres y finalmente se reinició servidor.

| Tiempo | Qué hicimos | Qué vio vigilar | Qué vio un cliente nuevo | Estado |
|---|---|---|---|---|
| 1. servidor muerto | kill servidor | FALLA de comunicación ConnectionClosedError; no pudo reconectar en el primer intento | CommunicationError cannot connect, Name or service not known | Inaccesible; memoria del proceso perdida |
| 2. servidor vuelve | start servidor | Volvió a ok, ana=100 y beto=100 | usuarios respondió con el estado inicial | Se perdió el mensaje previo y el usuario de prueba |
| 3a. nombres muerto | kill nombres | Siguió mostrando ok | Failed to locate the nameserver | El estado del servidor no cambió |
| 3b. nombres vuelve | start nombres | Continuó ok por la conexión existente | unknown name: sd.jaune-asencio.directorio | Registro de nombres vacío |
| 3c. recuperación | restart servidor | Se restablece el servicio; luego se cerró el observador | uri y usuarios responden | Se vuelve a registrar; estado inicial |

La conversación pendiente imprimió:
```text
recibí Proxy, referencia PYRO:obj_b3da465cec814ba4a01374bbc412d91a@servidor:9100
estado en el servidor {'participantes': ['ana', 'beto'], 'texto': 'pendiente'}
espero 12.0 s antes de confirmar
ERROR de comunicación. ConnectionClosedError receiving: not enough data
```

En esta ejecución la primera confirmación encontró la conexión anterior cerrada.
No se reintentó automáticamente. El error unknown object se verificó por separado
después de confirmar/cancelar en el paso 3; no se afirma que haya sido la salida
de esta llamada durante la caída. Reiniciar no reconstruye el objeto pendiente.

**Puntos únicos de falla:** servidor para operaciones y estado; nombres para nuevas
resoluciones. Una conexión ya abierta no necesita consultar nombres en cada llamada.
Persistir buzones en almacenamiento con volumen permitiría sobrevivir al reinicio;
alta disponibilidad exige además replicación/failover del servicio y de nombres.

**REREGISTRO=5:** según servidor_pyro.py, inicia un hilo que publica la URI cada cinco
segundos. Tras recuperar nombres restablece el registro sin reiniciar servidor.
Cuesta llamadas periódicas y hay una ventana sin registro; no replica datos ni
reconstruye conversaciones. Este mecanismo se analizó en código, no se midió en
el experimento, que mantuvo REREGISTRO=0.

**Semántica:** no reintentamos enviar/leer/registrar/confirmar tras error de red.
La pérdida de respuesta puede ocultar una operación aplicada. El integrador
propone id de mensaje y deduplicación persistida, retomando la lección de S11.

**Estado final:** configuración single, POR_VALOR=0 y REREGISTRO=0;
servicios recuperados, ana=100, beto=100 y cero conversaciones vivas.
