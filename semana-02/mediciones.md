# Mediciones — Laboratorio N°1 (Semana 2)

**Equipo:** _______________   **Integrantes:** _______________ / _______________
**Fecha:** 28-08-2026   **Entorno:** Docker Desktop (Windows) / otro: ________

## Paso 1 — Línea base
| Métrica | Valor |
|---|---|
| RTT ping (promedio) | ___ ms |
| Throughput iperf3 | ___ Gbit/s |

## Pasos 2 y 3 — Latencia inyectada (100 llamadas)
| Latencia `tc` | Total (s) | Promedio (ms) | Máx (ms) | ¿Esperado? (sí/no, por qué) |
|---|---|---|---|---|
| 0 ms (base) | | | | |
| 50 ms | | | | |
| 200 ms | | | | |
| 500 ms | | | | |

## Paso 4 — Pérdida de paquetes
| Pérdida `tc` | Throughput iperf3 | Total cliente (s) | Observación |
|---|---|---|---|
| 1% | | | |
| 5% | | | |
| 20% | | | |
| 100% (falla provocada) | — | | ¿Qué hizo el cliente? ¿Y con TIMEOUT_S=3? |

## Falacia que asumimos sin advertirlo
_______________________________________________________________
