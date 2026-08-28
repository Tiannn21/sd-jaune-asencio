# Mediciones — Laboratorio N°1 (Semana 2)

**Equipo:** **\*\***SD-Jaune-Asencio_**\*\*** **Integrantes:** **Sebastian Edgardo Asencio ***Diego Fernando Jaune**\*\*** / **\*\***\_\_\_**\*\***
**Fecha:** 28-08-2026 **Entorno:** Docker Desktop (Windows) / otro: **\_\_\_\_**

## Paso 1 — Línea base

| Métrica             | Valor          |
| ------------------- | -------------- |
| RTT ping (promedio) | = 0.062/ms     | 
| Throughput iperf3   | 22.7 Gbits/sec |

## Pasos 2 y 3 — Latencia inyectada (100 llamadas)

| Latencia `tc` | Total (s) | Promedio (ms) | Máx (ms) | ¿Esperado? (sí/no, por qué)               |
| ------------- | --------- | ------------- | -------- | ----------------------------------------- |
| 0 ms (base)   | 0.011s    | 0.1ms         | 0.6ms    | Si, 100x0 = 0       |
| 50 ms         | 5.052s    | 50.5ms        | 51.2ms   | Si, 100x50 = 5s     |
| 200 ms        | 20.051s   | 200.5ms       | 200.9ms  | Si, 100x200 = 20s   |
| 500 ms        | 50.053s   | 500.5ms       | 501.1ms  | Si, 100x500 = 50s   |

## Paso 4 — Pérdida de paquetes

| Pérdida `tc`           | Throughput iperf3 | Total cliente (s) | Observación                               |
| ---------------------- | ----------------- | ----------------- | ----------------------------------------- |
| 1%                     |   10.9Gbits/sec   |     0.216s        |  La pérdida es baja y el sistema sigue funcionando con normalidad|
| 5%                     |   283 Mbits/sec   |     0.421s        |  El throughput disminuye considerablemente|
| 20%                    |   5.24 Mbits/sec  |     9.641s        |  El throughput cae a solo 5.24 Mbit/s  |
| 100% (falla provocada) | [cliente] error de red: [Errno 113] No route to host|  No route to host | El cliente no pudo comunicarse con el servidor y terminó mostrando el error No route to host|

## Falacia que asumimos sin advertirlo

--- Pese a trabajar localmente existe un poco de latencia.
