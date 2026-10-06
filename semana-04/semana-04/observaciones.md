# Observaciones — fallas provocadas · semana 4 · Equipo **SD-Jaune-Asencio**

Los tiempos están expresados con unidad y corresponden a las pruebas ejecutadas.

## Falla 1 — servidor muerto con el cliente conectado

Comando usado: `docker compose kill servidor`

| Pregunta                                                                              | Respuesta |
| ------------------------------------------------------------------------------------- | --------- |
| ¿Qué mensaje mostró el cliente?                                                       | `CONEXIÓN PERDIDA: ConnectionError: el servidor cerró la conexión sin responder` |
| ¿Cuánto tardó en aparecer desde que enviaron el comando? (ms o s)                     | 0,2 ms en la prueba; el kernel avisó el cierre inmediatamente. |
| ¿El cliente supo que el servidor estaba muerto o solo que la conexión se cerró?       | Solo supo que la conexión se cerró; no pudo determinar por sí mismo la causa. |
| Al levantar el servidor de nuevo, ¿se recuperó la sesión anterior (nombre, contador)? | No. La sesión anterior se perdió y el contador comenzó nuevamente en `1` al enviar el primer comando. |

## Falla 2 — cliente sin red con el servidor vivo

Comando usado: `docker network disconnect sd_net cliente`

| Pregunta                                                                             | Respuesta |
| ------------------------------------------------------------------------------------ | --------- |
| ¿Qué mensaje mostró el cliente?                                                      | `TIMEOUT: el servidor no respondió en 5 s. ¿Caído, sin red o lento? No se puede saber.` |
| ¿Cuánto tardó en aparecer?                                                           | 5,0 s, que es el valor de `TIMEOUT` del cliente. |
| ¿Qué mostró el log del servidor en ese momento?                                      | No mostró un comando nuevo: el servidor siguió esperando en la conexión. |
| Desde el punto de vista del cliente, ¿en qué se diferencia esta falla de la falla 1? | En la falla 1 el cierre se detectó en milisegundos; aquí no hubo aviso y el cliente esperó el timeout. |

## Segundo cliente mientras el primero está conectado (paso 3)

| Pregunta                                                               | Respuesta |
| ---------------------------------------------------------------------- | --------- |
| ¿El segundo cliente logró conectarse (`connect`)?                      | Sí, fue exitoso desde `172.18.0.3:48336`; la conexión quedó pendiente. |
| ¿Recibió respuesta a su primer comando? ¿Qué mostró?                   | No mientras el primero siguió conectado; mostró `TIMEOUT` después de 5 s. |
| ¿Qué mostró el log del servidor cuando el primer cliente hizo `SALIR`? | Registró `SALIR`, respondió `ADIOS`, cerró la primera conexión y luego atendió la conexión pendiente del segundo cliente. |

## Conclusión del equipo (3 a 5 líneas)

Un programador que solo probara el camino feliz asumiría que la red es confiable y que
la ausencia de respuesta significa una única causa. El cliente no puede distinguir
entre servidor caído, servidor ocupado y red cortada porque en los dos últimos casos
nadie le avisa qué ocurrió: solo deja de recibir datos. El timeout permite detectar
que pasó demasiado tiempo, pero no identifica la causa. Cuando el servidor muere,
en cambio, el sistema operativo cierra el socket y el cliente recibe el aviso casi
de inmediato.
