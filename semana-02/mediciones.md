# Mediciones — Laboratorio N°1 (Semana 2)

**Equipo:** **\*\***\_\_\_**\*\*** **Integrantes:** **\*\***\_\_\_**\*\*** / **\*\***\_\_\_**\*\***
**Fecha:** 28-08-2026 **Entorno:** Docker Desktop (Windows) / otro: **\_\_\_\_**

## Paso 1 — Línea base

| Métrica             | Valor          |
| ------------------- | -------------- |
| RTT ping (promedio) | = 0.062/ms     |
| Throughput iperf3   | 22.7 Gbits/sec |

## Pasos 2 y 3 — Latencia inyectada (100 llamadas)

| Latencia `tc` | Total (s) | Promedio (ms) | Máx (ms) | ¿Esperado? (sí/no, por qué)               |
| ------------- | --------- | ------------- | -------- | ----------------------------------------- |
| 0 ms (base)   | 0.011s    | 0.1ms         | 0.6ms    | Si, porque no hay latencia                |
| 50 ms         | 5.052s    | 50.5ms        | 51.2ms   | Si, porque le agregamos 50ms de latencia  |
| 200 ms        | 20.051s   | 200.5ms       | 200.9ms  | Si, porque le agregamos 200ms de latencia |
| 500 ms        | 50.053s   | 500.5ms       | 501.1ms  | Si, porque le agregamos 500ms de latencia |

## Paso 4 — Pérdida de paquetes

| Pérdida `tc`           | Throughput iperf3 | Total cliente (s) | Observación                               |
| ---------------------- | ----------------- | ----------------- | ----------------------------------------- |
| 1%                     |                   |                   |                                           |
| 5%                     |                   |                   |                                           |
| 20%                    |                   |                   |                                           |
| 100% (falla provocada) | —                 |                   | ¿Qué hizo el cliente? ¿Y con TIMEOUT_S=3? |

## Falacia que asumimos sin advertirlo

---
