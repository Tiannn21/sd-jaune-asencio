# Evaluación 4, Reporte de Servicios Cliente-Servidor

| Archivo | Para qué |
|---|---|
| `docs/informe/informe.md` | Plantilla del informe. Cópienla en su repositorio como `docs/informe/informe.md` |
| `medir.py` | Script de medición. No hay que programar, solo ejecutarlo una vez por mecanismo |

## Entrega

Viernes 20-11-2026 a las 14.00, en el repositorio del equipo, `docs/informe/informe.md` más `docs/informe/informe.pdf`.
Vale la hora del commit.

## Cómo medir

Copien `medir.py` en la carpeta de la semana del mecanismo que van a medir, levanten ese compose y ejecuten
dentro del contenedor cliente. Elijan una operación de **consulta** (que no cambie estado) y usen la misma en ambos mecanismos.

```bash
# Pyro5, dentro de semana12/
docker compose up -d --build
docker compose exec cliente python medir.py pyro --metodo listar

# JSON-RPC, dentro de semana10/ (ajusten la URL a su servicio)
docker compose exec cliente python medir.py jsonrpc --url http://servidor:8000/rpc --metodo listar

# gRPC, dentro de semana11/ (antes editen las tres líneas marcadas EDITAR en adaptador_grpc)
docker compose exec cliente python medir.py grpc
```

Si su método se llama distinto o lleva parámetros, usen `--metodo saldo --params '{"cuenta": "c1"}'`.
En Pyro5, si su objeto no se llama `sd.<EQUIPO>.inventario`, usen `--nombre sd.pagos.pasarela`.

Cada ejecución imprime una fila en formato Markdown para pegar en la sección 5 y la agrega a `mediciones.csv`.
Los tiempos dependen de su notebook. Sirven para comparar mecanismos entre sí, no como cifras absolutas.

Para el PDF pueden usar la vista previa de Markdown de VS Code e imprimir a PDF, o `pandoc informe.md -o informe.pdf`.
