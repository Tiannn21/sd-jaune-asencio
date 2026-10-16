# Guion de la demostración, Evaluación 3 (viernes 16-10)

Equipo SD-Jaune-Asencio. Dominio: mensajería instantánea.
Tiempo total: 9 minutos de demostración más 3 de preguntas.
Diego lleva la arquitectura y la predicción de la falla. Sebastián opera la terminal. Los dos hablan.

Antes de entrar, en `semana-07/laboratorio`, dejar la pila recién levantada y no volver a hacer `docker compose down` durante la demo: el buzón vive en memoria.

```powershell
docker compose down
docker compose up -d --build
docker compose ps
```

Deben verse `sd_servidor`, `sd_api1`, `sd_api2`, `sd_nginx` y `sd_cliente`. Solo Nginx publica puerto (`8080->80`).

| Minuto | Qué mostramos | Quién habla | Comando o archivo en pantalla |
| ------ | ------------- | ----------- | ----------------------------- |
| 0 a 2  | Tres niveles en `despliegue_v2`: entrada, puerta sin estado y servidor con estado | Diego | `diagramas/despliegue_v2.png` |
| 2 a 4  | `ENVIAR` traducido a `POST /mensajes` (201) y `USUARIO_NO_EXISTE` traducido a 404 | Sebastián | `protocolo.md`, `interfaz_http.md` y `cliente_http.py` |
| 4 a 5  | Cinco contenedores en `sd_net`. Solo Nginx publica puerto | Sebastián | `docker compose up -d` y `docker compose ps` |
| 5 a 6  | 20 clientes leen a la vez. El Lock deja a ana en 20 y la API ve ese mismo dato | Sebastián | `cliente_carga.py` y `GET /usuarios` |
| 6 a 9  | Cae `api1` y sigue `api2`. Cae el servidor y las API responden 503. Al volver, el mensaje se perdió | Diego predice; Sebastián ejecuta | `docker compose kill` y `docker compose up -d servidor` |

## Minuto 0 a 2

Abrir `diagramas/despliegue_v2.png` y recorrerlo de izquierda a derecha.

- Entrada: el navegador o el cliente llegan a `nginx` / `sd_nginx` por el puerto publicado `HTTP 8080 -> 80`.
- Puerta sin estado: Nginx reparte por `HTTP 8000` entre `api1` / `sd_api1` y `api2` / `sd_api2`. Ninguna guarda usuarios ni buzón.
- Servidor con estado: las dos API hablan `TCP 5000` con `servidor` / `sd_servidor`, un hilo por cliente. Ahí están ana y beto, los pendientes y el buzón, en memoria y con Lock.

Cierre: si cae una API, sigue la otra. Si cae Nginx, no hay entrada. Si cae el servidor, las API responden 503 y el estado se pierde.

## Minuto 2 a 4

Mostrar en `semana-06/laboratorio/protocolo.md` el comando `ENVIAR` y en `interfaz_http.md` la fila `POST /mensajes`.

Operación correcta:

```powershell
docker compose exec cliente python cliente_http.py POST /mensajes origen=ana destino=beto "texto=hola semana 7"
```

Esperado, como en el ensayo del 14-10: `201` y `{"destino":"beto","pendientes":101,"replica":"api1"}`.

Error documentado:

```powershell
docker compose exec cliente python cliente_http.py GET /usuarios/noexiste/bandeja
```

Esperado: `404` y `{"detail":{"error":"USUARIO_NO_EXISTE","detalle":"","replica":"api1"}}`. Decir que la API traduce `ERROR USUARIO_NO_EXISTE` del protocolo de texto.

## Minuto 4 a 5

No bajar la pila: el mensaje de beto tiene que seguir ahí para la falla.

```powershell
docker compose up -d
docker compose ps
```

Señalar los cinco contenedores y que la única línea de puertos es `0.0.0.0:8080->80/tcp`. El 5000 y el 8000 se quedan dentro de `sd_net`.

## Minuto 5 a 6

`LEER` se hace sobre ana para no consumir el mensaje de beto. Son 20 clientes por 4 repeticiones, 80 lecturas concurrentes. Con Lock, ana pasa de 100 a 20.

```powershell
docker compose exec cliente python cliente_carga.py --clientes 20 --comando "LEER ana 1" --repeticiones 4
docker compose exec cliente python cliente_http.py GET /usuarios
```

Frase: el total no es 80 veces el tiempo de una lectura, porque el servidor atiende con un hilo por cliente. `GET /usuarios` muestra `ana: 20` venga de `api1` o de `api2`, porque ninguna réplica tiene copia propia. En la semana 6 este ensayo dejó `ana:20`; anotar aquí el `TOTAL` del ensayo de hoy.

## Minuto 6 a 9

Decir la predicción antes de cada comando.

### Tiempo 1, cae api1

Predicción: Nginx deja fuera a `api1` y atiende con `api2`. La primera petición tarda cerca de 1 s. El buzón de beto no cambia, porque el estado está en el servidor.

```powershell
docker compose kill api1
docker compose exec cliente python cliente_http.py --repetir 4 GET /usuarios/beto/bandeja
```

Ensayo del 14-10: la primera línea fue `200` en 1,02 s, `replica: api2`, `pendientes: 101`, `mensajes: ana:hola semana 7`. Las otras tres también fueron `api2`.

### Tiempo 2, cae el servidor

Predicción: `api1` y `api2` siguen vivas, pero no pueden hablar con el servidor y responden 503. Al crearlo de nuevo, beto vuelve a 100 pendientes y el mensaje desaparece.

```powershell
docker compose kill servidor
docker compose exec cliente python cliente_http.py --repetir 2 GET /usuarios
docker compose up -d servidor
docker compose exec cliente python cliente_http.py GET /usuarios/beto/bandeja
```

Ensayo del 14-10: `503` con `SERVIDOR_NO_DISPONIBLE` (detalle `gaierror`), cerca de 4 s, una vez por cada réplica. Después del `up`, `200` con `pendientes: 100` y `mensajes` vacío.

Cierre: se pudo replicar la puerta HTTP. No se pudo replicar el servidor, porque era la única copia del buzón y esa copia estaba en memoria.

## Falla que vamos a provocar

Qué componente cae: primero `api1` (`sd_api1`) y después `servidor` (`sd_servidor`).

Qué predecimos que pasa ANTES de ejecutar: al caer `api1`, Nginx usa `api2` y el buzón de beto sigue en 101 pendientes con el texto `ana:hola semana 7`. Al caer el servidor, las dos API responden 503. Al levantarlo, el mensaje y el pendiente nuevo se pierden.

Qué pasó en el ensayo: la primera bandeja después de matar `api1` tardó 1,02 s y respondió 200 solo por `api2`. Después de matar el servidor, dos respuestas 503 `SERVIDOR_NO_DISPONIBLE`. Al volver a levantarlo, `GET /usuarios/beto/bandeja` dio `pendientes: 100` y `mensajes` vacío.

Qué haríamos para que el sistema lo tolere mejor: sacar el buzón de la memoria de ese proceso y guardarlo en un almacenamiento compartido. Tener dos réplicas de la API no duplica el estado.

## Plan B si algo no levanta

Si Docker no parte, no improvisar la corrida. Mostrar `diagramas/despliegue_v2.png`, `interfaz_http.md` y las salidas ya copiadas en `observaciones.md` (el 201, el 404, el reparto `api1`/`api2`, el 1,02 s y los 503).

## Preguntas probables

- 503 lo responde la API cuando no llega al servidor. 502 lo responde Nginx cuando no queda ninguna réplica.
- La primera petición tras caer `api1` tarda cerca de 1 s por el `proxy_connect_timeout` de Nginx.
- `HOLA`, `SALIR` y `ESPERA` no están en la API: las dos primeras son de la sesión TCP, y `ESPERA` solo duerme un hilo.
