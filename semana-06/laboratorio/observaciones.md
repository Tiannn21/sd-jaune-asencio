# Observaciones — Semana 6

Equipo: SD-Jaune-Asencio
Integrantes: Diego Jaune y Sebastián Asencio
Dominio del servicio: mensajería instantánea
Fecha de las mediciones: 05-10-2026
Entorno: Windows 11, Docker Desktop 29.7.2, red `sd_net`, puerto 5000

El servidor secuencial es el de la semana 4, con `ESPERA` agregado porque ese protocolo no tenía una operación lenta. El servidor concurrente reemplaza el inventario de ejemplo por usuarios, buzón y pendientes.

## Paso 1 — servidor secuencial bajo carga

Comando ejecutado:

```bash
docker compose exec -d cliente python servidor_secuencial.py
docker compose exec -e SERVIDOR_HOST=cliente carga python cliente_carga.py --clientes 5 --comando "ESPERA 2"
```

Tiempo por cliente:

```
  cliente   en fila   operacion      total   ultima respuesta
        0    0.02 s    2.00 s    2.02 s   OK ESPERA 2
        2    2.02 s    2.00 s    4.02 s   OK ESPERA 2
        3    4.02 s    2.00 s    6.02 s   OK ESPERA 2
        4    6.02 s    2.00 s    8.02 s   OK ESPERA 2
        1    8.02 s    2.00 s   10.02 s   OK ESPERA 2
TOTAL: 10.02 s
```

TOTAL: 10.02 s

¿Qué esperaban? ¿Qué observaron?

Esperábamos cerca de 10 s: cinco clientes con `ESPERA 2` y un servidor que atiende a uno por vez. Observamos 10.02 s. Cada operación duró 2.00 s. La columna «en fila» creció de 0.02 s a 8.02 s.

El último cliente (el 1) pasó 8.02 s en fila. Ese tiempo va desde `connect()` hasta la respuesta de `HOLA`. El servidor secuencial no vuelve a `accept()` hasta terminar el cliente actual, así que el último estuvo en la cola de conexiones mientras los cuatro anteriores completaban su `ESPERA 2`. Su propia espera de 2 s empezó recién cuando el servidor lo aceptó.

## Paso 2 — hilo por cliente bajo carga

Comando ejecutado:

```bash
docker compose up -d --force-recreate servidor
docker compose exec carga python cliente_carga.py --clientes 5 --comando "ESPERA 2"
```

```
  cliente   en fila   operacion      total   ultima respuesta
        2    0.00 s    2.00 s    2.01 s   OK ESPERA 2
        4    0.01 s    2.00 s    2.01 s   OK ESPERA 2
        1    0.01 s    2.00 s    2.01 s   OK ESPERA 2
        3    0.01 s    2.00 s    2.01 s   OK ESPERA 2
        0    0.01 s    2.00 s    2.01 s   OK ESPERA 2
TOTAL: 2.01 s
```

TOTAL: 2.01 s

Diferencia respecto al Paso 1 y explicación:

El total bajó de 10.02 s a 2.01 s. La fila quedó en 0.00–0.01 s para los cinco. Cada cliente tuvo su hilo (`cli-52320`, `cli-52338`, `cli-52322`, `cli-52314`, `cli-52340`) y los cinco `ESPERA 2` corrieron juntos. El log arrancó con `SIN_LOCK=False` y, al cerrar, los cinco hilos vieron `operaciones=5`.

## Paso 3 — condición de carrera

Operación que modifica estado compartido usada: `LEER ana 1`, 20 clientes, 4 repeticiones cada uno (80 descuentos de 1 sobre los 100 pendientes iniciales).

Valor esperado: `ana:20` (`100 - 80`). `beto` queda en 100.

Valor observado SIN Lock:

| Corrida | `USUARIOS` después de la carga |
| ------- | ------------------------------ |
| 1       | `OK ana:86 beto:100`           |
| 2       | `OK ana:85 beto:100`           |

Se perdieron actualizaciones: varios hilos leyeron el mismo valor de `pendientes`, durmieron 1 ms y escribieron el mismo resultado. Las dos corridas dieron valores distintos, ambos lejos de 20. El log de esas corridas dice `SIN_LOCK=True`.

Valor observado CON Lock:

| Corrida | `USUARIOS` después de la carga |
| ------- | ------------------------------ |
| 1       | `OK ana:20 beto:100`           |
| 2       | `OK ana:20 beto:100`           |
| 3       | `OK ana:20 beto:100`           |

Tres corridas seguidas, cada una con el servidor recreado para volver a 100. El log dice `SIN_LOCK=False`.

¿Dónde exactamente está la sección crítica en su código?

Hay un solo `threading.Lock()` global, creado al cargar el módulo. `seccion_critica()` devuelve ese Lock, o un candado vacío si `SIN_LOCK=1`.

La sección crítica de la carrera es el leer-modificar-escribir de `pendientes` dentro de `op_leer` y `op_enviar`: leen el número, duermen 1 ms (ventana para ver la carrera) y escriben el nuevo valor. `op_registrar` también entra al Lock para crear un usuario. `op_usuarios` y `op_bandeja` lo usan solo para leer. `op_espera` duerme fuera del Lock.

Comprobación de que el Lock no envuelve la espera: con Lock activo, `ESPERA 2` y 5 clientes volvió a dar TOTAL 2.01 s y fila 0.00–0.00 s. Si el Lock hubiera cubierto el `sleep` de `ESPERA`, el total habría vuelto a unos 10 s.

## Paso 4 — despliegue con docker compose

`docker compose config` terminó sin errores (código 0).

Salida de `docker compose ps`:

```
NAME          IMAGE                  COMMAND                SERVICE    CREATED          STATUS                  PORTS
sd_carga      laboratorio-carga      "sleep infinity"       carga      2 minutes ago    Up Less than a second
sd_cliente    laboratorio-cliente    "sleep infinity"       cliente    2 minutes ago    Up About a minute
sd_servidor   laboratorio-servidor   "python servidor.py"   servidor   55 seconds ago   Up 51 seconds           0.0.0.0:5000->5000/tcp
```

La red se llama `sd_net`. Los tres contenedores están conectados a ella. Al levantar, Compose avisó que `sd_net` ya existía (la crea también el compose de la semana 2) y aun así enganchó estos contenedores a esa red.

IP del host: `192.168.18.126` (Wi-Fi), puerto 5000.

`ipconfig | findstr IPv4` también mostró `172.23.224.1`, que es el adaptador vEthernet de WSL, y varias direcciones link-local `169.254.*`. La dirección de la red local es la de Wi-Fi.

Prueba desde el contenedor `cliente` usando esa IP, no el nombre `servidor`:

```bash
docker compose exec -e SERVIDOR_HOST=192.168.18.126 cliente python cliente.py
```

```
conectado a 192.168.18.126:5000
<< OK HOLA equipo
<< OK ana:20 beto:100
<< OK CHAO
```

`ana:20` es el estado que dejó la tercera corrida con Lock. El puerto publicado en el host responde.
