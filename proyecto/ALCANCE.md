# Alcance del proyecto integrador

**Equipo:** SD-Jaune-Asencio  
**Integrantes:** Diego Jaune y Sebastián Asencio  
**Dominio:** mensajería instantánea  
**Estado:** propuesta técnica preparada; pendiente de aprobación docente.

## 1. Problema

Permitir que usuarios registrados intercambien mensajes y consulten sus pendientes.
Separar la recepción de mensajes y su entrega para tolerar la caída temporal de
un trabajador, sin mostrar mensajes duplicados cuando se reintenta una entrega.

## 2. Objetos remotos propuestos

| Clase | Nodo | Estado propio | Métodos |
|---|---|---|---|
| Directorio | servidor | Usuarios y registro de conversaciones | usuarios, registrar, abrir_conversacion |
| Conversacion | servidor | Participantes, borrador, estado, id de mensaje | agregar, ver, confirmar, cancelar |
| Buzon | buzones | Mensajes persistidos y claves de deduplicación | entregar, leer, pendientes |

Directorio y Buzon vivirán en nodos distintos. Directorio consultará
Buzon.pendientes mediante un Proxy resuelto por nombres; los workers invocarán
Buzon.entregar. Así habrá llamadas objeto a objeto entre nodos.

Conversacion se crea en Directorio.abrir_conversacion, se devuelve por referencia,
se edita y consulta; confirmar acepta el envío en la cola y desregistra el borrador.
Cancelar lo desregistra sin publicar. Se distinguirá aceptado de entregado.
En semana 12 el envío es síncrono; la cola y Buzon separado son trabajo futuro.

## 3. Nodos previstos

| Servicio compose | Rol | Comunicación |
|---|---|---|
| nombres | Directorio de referencias Pyro5 | servidor, buzones, cliente, workers |
| servidor | Directorio y Conversacion | nombres, buzones, rabbitmq |
| buzones | Objeto Buzon, almacenamiento SQLite en volumen | nombres, servidor, workers, cliente |
| rabbitmq | Cola durable de entregas | servidor, worker1, worker2 |
| worker1 / worker2 | Consumidores competidores | rabbitmq, nombres, buzones |
| coordinacion | Servicio de leases/bloqueos distribuido (propuesta: etcd) | workers |
| cliente | CLI de usuarios y mensajes | nombres, servidor, buzones |

Red sd_net. Hosts y puertos por variables de entorno; sin IP fijas.

## 4. Cola y coordinación

Semana 13: una cola durable de entregas reparte mensajes entre dos workers.
Cada envío llevará id_mensaje, publicación confirmada y ACK manual después de
persistir en Buzon. Índice único por id_mensaje evitará duplicados por redelivery.
La transacción de Buzon verificará deduplicación y guardará el mensaje conjuntamente.

Semana 16: bloqueo distribuido por destinatario con lease para serializar entregas
concurrentes entre workers. Evaluar etcd y un token de fencing validado por Buzon;
si vence el lease, el worker deja de escribir y no confirma el trabajo.
Esto coordina workers; el lock de Python de S12 solo coordina hilos de un proceso.
El bloqueo no garantiza por sí solo orden FIFO de publicaciones concurrentes:
si se requiere orden global, habrá que añadir secuencias por destinatario.

## 5. Falla del 18-12

Detener worker1 después de persistir un mensaje y antes de su ACK.
El emisor verá aceptado; el destino recibirá una sola copia.
RabbitMQ reentregará el trabajo a worker2; Buzon reconocerá id_mensaje y no duplicará
el texto. Reiniciar worker1 permitirá volver al reparto entre ambos.
Evidencia prevista: id en logs, redelivery, dos workers y una única fila en Buzon.
El volumen de buzones conservará datos al reiniciar su contenedor.
La arquitectura inicial no promete alta disponibilidad ante pérdida del host.

## 6. Fuera de alcance

Audio/video, archivos adjuntos, aplicaciones móviles, grupos masivos, cifrado
extremo a extremo, autenticación de producción, federación y despliegue público.
CLI y mensajes de texto entre usuarios de prueba dentro de Docker.

## 7. Riesgos

| Riesgo | Respuesta |
|---|---|
| Entrega duplicada tras perder ACK | id_mensaje e índice único persistido |
| Pérdida de datos al reiniciar | SQLite con volumen y prueba de recuperación |
| Servicio de nombres vacío tras reinicio | Re-registro periódico y reconexión |
| Conversaciones abandonadas | Cancelación explícita; evaluar TTL con limpieza |
| Lease vencido o caída de coordinación | Fallar sin escribir y validar fencing |
| Exceso de alcance | Priorizar CLI, dos workers y una falla reproducible |

## 8. Correspondencia con los ocho mínimos

Tres o más nodos: sección 3. Dos clases en nodos distintos y llamada remota:
sección 2. Referencia con ciclo de vida: Conversacion. Localización: nombres.
Cola y dos workers: sección 4. Coordinación: sección 4.
Falla documentada: sección 5. README, diagrama draw.io y bitácora se mantendrán
durante la implementación; el diagrama definitivo es pendiente del integrador.

---

**Aprobación docente:** pendiente de revisión en la mesa.  
**Fecha de aprobación:** pendiente.  
**Observaciones del docente:** por completar por el docente; no se presume aprobación.
