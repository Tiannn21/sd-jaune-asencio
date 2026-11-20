# Reporte de Servicios Cliente-Servidor

**Equipo**
**Integrantes**
**Dominio**
**Repositorio**
**Fecha** 20-11-2026

## 1. El servicio y su dominio

(media página. Qué problema resuelve el servicio, quién lo usa y cuáles son sus operaciones principales)

## 2. Arquitectura y topología

(diagrama hecho en draw.io, exportado como imagen en `docs/informe/img/`. Nodos como contenedores, red, puertos y protocolo en cada flecha. Debajo, una explicación de qué hace cada nodo)

## 3. Evolución del contrato

(cómo cambió la forma de pedirle cosas al servicio. Muestren el mismo ejemplo de operación en cada etapa)

| Etapa | Semana | Dónde está el contrato | Ejemplo de la misma operación |
|---|---|---|---|
| Protocolo de texto sobre TCP | 4 y 6 | `protocolo.md` | |
| REST | 7 | | |
| Mensajes estructurados | 9 | `protocolo.md` v3 | |
| JSON-RPC | 10 | `rpc.py` | |
| gRPC | 11 | `.proto` y `contrato.md` | |
| Objetos remotos | 12 | `objetos.py` | |

¿Qué ganaron y qué perdieron en cada cambio?

## 4. Mecanismo elegido y justificación

(con qué mecanismo se quedan para la presentación del 4-12 y por qué. Compárenlo con al menos dos alternativas usando los criterios de su cuadro de la semana 10 y las necesidades de SU dominio. Una justificación que serviría para cualquier dominio no es una justificación)

| Criterio | Mecanismo elegido | Alternativa 1 | Alternativa 2 |
|---|---|---|---|
| | | | |

## 5. Evidencia de funcionamiento y medición

(capturas o salidas de terminal que muestren el servicio funcionando entre contenedores distintos)

Medición con `medir.py`, la misma operación de consulta sobre el mecanismo elegido y sobre una alternativa

| Mecanismo | Operación | n | p50 ms | p95 ms | media ms | máx ms | respuesta bytes |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
| | | | | | | | |

¿Qué explica la diferencia? ¿Importa esa diferencia para su dominio?

## 6. Análisis de fallos

(lo que la teoría dice que debería pasar frente a lo que observaron. Usen sus `observaciones.md` de las semanas 11 y 12)

| Falla provocada | Qué esperaban según la teoría | Qué observaron | Qué harían para tolerarla |
|---|---|---|---|
| Servidor cae a mitad de una llamada (semana 11) | | | |
| Servidor cae y vuelve (semana 12) | | | |
| Servidor de nombres cae (semana 12) | | | |

¿Qué semántica de fallo (como máximo una vez, al menos una vez) ofrece hoy su servicio? ¿Cuál necesita su dominio?

## 7. Referencias

(mínimo tres, con al menos una de la bibliografía del curso. Formato autor, año, título, y capítulo o enlace)
