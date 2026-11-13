# Observaciones, taller semana 12 (objetos distribuidos con Pyro5)

Equipo
Integrantes presentes
Fecha 13-11-2026

## Paso 1, nombres y servidor arriba

URI que entregó el servidor de nombres para `sd.<equipo>.inventario`
(pegar la salida de `python cliente_pyro.py uri`)

```
```

¿Qué partes de la URI reconocen? (protocolo, identificador del objeto, nodo, puerto)

## Paso 2, su dominio como objeto remoto

Operaciones que expusieron y en qué clase quedó cada una

| Clase | Método | ¿Cambia estado? |
|---|---|---|
| | | |

## Paso 3, paso por referencia

Referencia que recibió el cliente al abrir el objeto con estado (`pedido` o el suyo)

```
```

¿Qué pasó con `POR_VALOR=1`? ¿Por qué el cliente rechaza el objeto?

¿Qué pasó al usar la referencia después de confirmar?

## Paso 4, modo de instancia

| Modo | Instancia del proxy A | Instancia del proxy B | ¿Comparten el contador? |
|---|---|---|---|
| single | | | |
| session | | | |

¿En cuál de los dos modos guardarían estado de un cliente? ¿Por qué el stock no cambia entre modos?

## Paso 5, falla en tres tiempos

| Tiempo | Qué hicimos | Qué vio `vigilar` | Qué vio un cliente nuevo | Qué pasó con el estado |
|---|---|---|---|---|
| 1. servidor muerto | | | | |
| 2. servidor vuelve | | | | |
| 3. nombres muerto y de vuelta | | | | |

¿Qué nodo es punto único de falla en esta arquitectura? ¿Cómo lo resolverían?
