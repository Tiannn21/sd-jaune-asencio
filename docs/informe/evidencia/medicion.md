# Procedimiento para reproducir la medición

Este documento describe cómo repetir la consulta con el código disponible. No registra una ejecución nueva ni completa datos ausentes de la corrida original.

## Evidencia existente

| Archivo | Resultados conservados |
|---|---|
| `semana-11/laboratorio/mediciones.csv` | Una fila gRPC y una JSON-RPC, ambas con `usuarios` y n=200 |
| `semana-12/laboratorio/mediciones.csv` | Una fila Pyro5 con `usuarios` y n=200 |

Los CSV originales no identifican hardware, carga del anfitrión, hora de ejecución ni todas las variables del entorno. No permiten demostrar repetibilidad entre corridas. Conservarlos sin sustituir sus filas por resultados nuevos.

## Condiciones de reproducción

Ejecutar los bloques siguientes desde PowerShell, partiendo de la raíz del repositorio. Requieren Docker Compose disponible. La recreación de los contenedores reinicia su estado en memoria; usar el laboratorio sin trabajo pendiente. S11 y S12 comparten nombres de contenedores y de red, por lo que deben levantarse por separado.

Para una nueva comparación, mantener el mismo equipo, evitar carga concurrente y registrar fecha, sistema, CPU, memoria, versión de Docker y configuración. Los comandos escriben `mediciones_reproduccion.csv`, separado de la evidencia original. Estas condiciones son propuestas para la reproducción; no se atribuyen a la corrida histórica.

### gRPC y JSON-RPC

```powershell
Set-Location semana-11/laboratorio
$env:FALLA = 'no'
$env:DEMORA = '3'
$env:DEDUP = '0'
$env:REINTENTOS = '0'
docker compose up -d --build --force-recreate
docker compose exec cliente python medir.py grpc --metodo usuarios --n 200 --csv mediciones_reproduccion.csv
docker compose exec -d servidor uvicorn rpc:app --host 0.0.0.0 --port 8000
# Esperar el inicio de uvicorn antes de medir JSON-RPC.
docker compose exec cliente python medir.py jsonrpc --url http://servidor:8000/rpc --metodo usuarios --n 200 --csv mediciones_reproduccion.csv
docker compose down
Set-Location ../..
```

En S11 el volumen `.:/app` conserva el CSV en el directorio del laboratorio. Cada servidor usa su propio estado inicial en memoria; el servicio JSON-RPC está en otro proceso dentro del contenedor `servidor`. El adaptador gRPC invoca `Usuarios` y usa un timeout de 5 segundos; `--metodo usuarios` identifica correctamente la fila. JSON-RPC usa también un timeout de 5 segundos en `urllib.request.urlopen`.

### Pyro5

```powershell
Set-Location semana-12/laboratorio
$env:EQUIPO = 'jaune-asencio'
$env:MODO = 'single'
$env:POR_VALOR = '0'
$env:REREGISTRO = '0'
docker compose up -d --build --force-recreate
# Esperar que el servidor registre su nombre; comprobarlo con:
docker compose exec cliente python cliente_pyro.py uri
docker compose exec cliente python medir.py pyro --nombre sd.jaune-asencio.directorio --metodo usuarios --n 200 --csv mediciones_reproduccion.csv
docker compose cp cliente:/app/mediciones_reproduccion.csv ./mediciones_reproduccion.csv
docker compose down
Set-Location ../..
```

S12 no monta el directorio de trabajo como volumen: copiar el CSV antes de retirar los contenedores. Usar explícitamente `--nombre sd.jaune-asencio.directorio`, porque el nombre predeterminado del script termina en `inventario`. No usar el adaptador gRPC sin adaptar de la copia de `medir.py` de S12: la medición gRPC corresponde al script de S11.

## Qué mide el script

Cada adaptador hace una consulta inicial para calcular el tamaño. Después se ejecutan diez llamadas de calentamiento y 200 llamadas medidas en serie, con `time.perf_counter()`. Se calculan p50, p95, media y máximo de los tiempos de llamada observados por el cliente.

`respuesta_bytes` significa `ByteSize()` del mensaje para gRPC, longitud del cuerpo HTTP para JSON-RPC y longitud de `serpent.dumps(resultado)` para Pyro5. No equivale al tráfico completo en la red. El contador interno de telemetría de Pyro5 cambia, pero la consulta no modifica usuarios, buzones ni pendientes. No hay medición separada de deduplicación, de cada capa del transporte ni de concurrencia.
