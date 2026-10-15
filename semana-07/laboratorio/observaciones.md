# Observaciones de la Semana 7

Equipo: SD-Jaune-Asencio
Integrantes: Diego Jaune y Sebastián Asencio
Dominio del servicio: mensajería instantánea
Fecha: 14-10-2026

## Paso 1  diagrama de despliegue v1 (el sistema de la semana 6)

Archivo entregado en `diagramas/`
Cantidad de nodos, redes y puertos representados

## Paso 2  revisión por pares

Equipo que revisó nuestro diagrama
Ítems de la pauta marcados como NO (copiar el número y el comentario)
Qué vamos a corregir primero y por qué

Equipo cuyo diagrama revisamos
Los dos hallazgos más importantes que les dejamos

## Paso 3  una operación como servicio REST

Operación del protocolo de texto elegida: `ENVIAR ana beto hola semana 7`
Método y ruta HTTP: `POST /mensajes`, con JSON `{"origen":"ana","destino":"beto","texto":"hola semana 7"}`
Salida de la prueba contra api1: `201   0.03 s  {"destino":"beto","pendientes":101,"replica":"api1"}`
Salida de un caso de error y su código HTTP (`GET /usuarios/noexiste/bandeja` contra api1): `404   0.01 s  {"detail":{"error":"USUARIO_NO_EXISTE","detalle":"","replica":"api1"}}`

## Paso 4  dos réplicas detrás de Nginx

Comando: `docker compose exec cliente python cliente_http.py --repetir 4 GET /usuarios/beto/bandeja`
Salida de `cliente_http.py --repetir 4`:

```text
200   0.02 s  {"usuario":"beto","pendientes":101,"mensajes":"ana:hola semana 7","replica":"api1"}
200   0.01 s  {"usuario":"beto","pendientes":101,"mensajes":"ana:hola semana 7","replica":"api2"}
200   0.01 s  {"usuario":"beto","pendientes":101,"mensajes":"ana:hola semana 7","replica":"api1"}
200   0.00 s  {"usuario":"beto","pendientes":101,"mensajes":"ana:hola semana 7","replica":"api2"}
```

¿Qué réplica atendió cada petición? `api1`, `api2`, `api1`, `api2`.
¿El dato es el mismo sin importar la réplica? Sí. Ambas API consultan el mismo servidor TCP, que conserva el buzón y los pendientes; la API no guarda estado.

## Paso 5  falla provocada en dos tiempos

### Tiempo 1, cae una réplica de la API
Predicción escrita ANTES de ejecutar: Nginx detectará que api1 cayó y enviará las solicitudes a api2. Las cuatro respuestas deberían ser HTTP 200 y mostrar el mismo estado del buzón, porque el estado se guarda en el servidor TCP.
Comando usado: `docker compose kill api1`; luego `docker compose exec cliente python cliente_http.py --repetir 4 GET /usuarios/beto/bandeja`
Qué respondió el sistema:

```text
200   1.02 s  {"usuario":"beto","pendientes":101,"mensajes":"ana:hola semana 7","replica":"api2"}
200   0.00 s  {"usuario":"beto","pendientes":101,"mensajes":"ana:hola semana 7","replica":"api2"}
200   0.00 s  {"usuario":"beto","pendientes":101,"mensajes":"ana:hola semana 7","replica":"api2"}
200   0.00 s  {"usuario":"beto","pendientes":101,"mensajes":"ana:hola semana 7","replica":"api2"}
```

¿Cuánto tardó la primera petición después de la caída? 1,02 s; Nginx esperó el intento fallido contra `api1` y reintentó con `api2`.

### Tiempo 2, cae el servidor TCP
Predicción escrita ANTES de ejecutar: las API seguirán levantadas, pero no podrán conectarse al servidor TCP y devolverán HTTP 503. Al volver a levantarlo, se reiniciará su estado en memoria: desaparecerá el mensaje enviado y `beto` volverá a 100 pendientes.
Comando usado: `docker compose kill servidor`; luego `docker compose exec cliente python cliente_http.py --repetir 2 GET /usuarios`; recuperación con `docker compose up -d servidor` y comprobación con `docker compose exec cliente python cliente_http.py GET /usuarios/beto/bandeja`.
Qué respondió el sistema y con qué código HTTP:

```text
503   4.01 s  {"detail":{"error":"SERVIDOR_NO_DISPONIBLE","detalle":"gaierror","replica":"api1"}}
503   3.85 s  {"detail":{"error":"SERVIDOR_NO_DISPONIBLE","detalle":"gaierror","replica":"api2"}}
```

¿Qué se perdió al volver a levantar el servidor? Se perdió el mensaje `ana:hola semana 7` y el pendiente agregado a Beto. La consulta posterior respondió `200   0.02 s  {"usuario":"beto","pendientes":100,"mensajes":"","replica":"api1"}`: el servidor reinició su estado en memoria con los valores iniciales.

### Conclusión en tres líneas
Se pudo replicar el nivel de API: al caer `api1`, `api2` siguió respondiendo y ambas réplicas consultaban el mismo dato. El servidor TCP no se replicó; era la única copia del nivel que guardaba el estado en memoria. Al reiniciarlo, se perdieron los mensajes y los cambios realizados durante la ejecución.
