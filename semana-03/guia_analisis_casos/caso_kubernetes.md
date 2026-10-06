# Análisis de caso: Kubernetes

**Equipo:** Diego Jaune y Sebastián Asencio · **Fecha:** 04-09-2026

## 1. Modelo dominante

**cluster**

Justificación con las preguntas de la matriz (marcar la que más pesó):

- ¿Quién manda?: **Esta es la que más pesó.** El plano de control (API server + scheduler + etcd) es el maestro y el dueño del cluster: decide en qué worker corre cada contenedor, cuántas réplicas debe haber y cuáles se reponen. Los workers no se coordinan entre sí; obedecen el estado deseado que declara el plano. Eso es «un maestro, un dueño», no «el proveedor» ni «nadie».
- ¿Los nodos son parecidos?: Sí. Los workers son homogéneos y se gestionan como una sola máquina: cualquiera puede recibir un pod. Encaja con «idénticos» del cluster, no con «muy distintos» del grid ni con «sensores» del ubicuo.
- ¿Qué tan lejos están?: Conviven en un mismo centro de datos (o en zonas cercanas de una región). La latencia entre nodos es baja, como «un rack». Que el cluster _corra_ en AWS (EKS) no lo convierte en cloud: la nube es _dónde_ corre; el modelo es _cómo se organiza_.
- ¿Qué pasa si uno desaparece?: Si cae un worker, el plano detecta la pérdida y reagenda los pods en otro. Si cae el maestro (sobre todo etcd), el cluster deja de decidir: no hay despliegues nuevos ni autorreparación. Encaja con «mal si cae el maestro».

Modelos secundarios presentes (si los hay) y por qué no dominan:

- **Cloud:** Kubernetes suele correr sobre un proveedor (EKS, GKE, AKS). Eso explica el _hosting_, no la organización. El proveedor no decide en qué worker va cada pod; lo decide el plano de control. Por eso cloud no domina.
- **Grid:** No aplica. No hay muchos dueños ni nodos heterogéneos repartidos entre países aportando cómputo distinto. Los workers son del mismo dueño y del mismo tipo.

## 2. Nodos y roles

| Nodo                            | Rol                                                                                                  | ¿Cuántos?                                       | ¿Estado o sin estado?                                                                                                     |
| ------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| API server                      | Punto de entrada del cluster. Recibe el estado deseado (`kubectl apply`, YAML) y lo expone al resto. | 1, o 2–3 si hay alta disponibilidad             | Sin estado: no guarda el cluster; solo habla con etcd                                                                     |
| Scheduler                       | Elige en qué worker corre cada pod nuevo                                                             | 1 activo (puede haber réplicas en espera)       | Sin estado: lee el API y escribe la asignación                                                                            |
| etcd                            | Guarda el estado del cluster (deseado y observado): deployments, pods, nodos, secretos               | 1 en un lab; 3 o 5 en producción (quórum impar) | **Con estado.** Es el único nodo que no se puede perder sin perder el cluster                                             |
| Worker (kubelet + contenedores) | Ejecuta los pods que el plano le asignó y reporta lo que realmente está corriendo                    | N (varios, homogéneos)                          | El nodo es reemplazable. Los pods sin volumen son sin estado; si montan un disco persistente, _esa_ carga sí tiene estado |

## 3. Diagrama de interacciones

Cajas = nodos. Flechas etiquetadas con el protocolo o el tipo de mensaje.
La flecha de **estado deseado** baja del operador al API y de ahí a etcd.
La flecha de **estado observado** sube del kubelet al API y se persiste en etcd.

```
                    kubectl / CI / operador
                              |
                              | HTTPS (REST)
                              | estado deseado
                              | (YAML: "quiero 3 réplicas")
                              v
                   +----------------------+
                   |     API server       |
                   +----------+-----------+
                         |    ^
                    gRPC |    | gRPC
          persistir      |    | leer
          estado         v    |
                   +----------+-----------+
                   |        etcd          |
                   |  fuente de verdad    |
                   +----------------------+
                         ^
                         | watch / HTTPS
           +-------------+-------------+
           |                           |
           | HTTPS                     | HTTPS
           | "asigna pod → nodo"       | estado observado
           |                           | (nodo vivo, pods corriendo)
           v                           v
    +-------------+            +---------------+     CRI
    |  scheduler  |            | kubelet       |-------------> contenedores
    +-------------+            | worker_1      |
                               +---------------+
                               | kubelet       |
                               | worker_2      |
                               +---------------+
                               | kubelet       |
                               | worker_3      |
                               +---------------+
```

Ciclo de reconciliación: el plano compara _lo que debería haber_ (etcd) con _lo que hay_ (reportes del kubelet). Si un contenedor muere, el scheduler / controlador pide otro pod y el kubelet lo levanta.

## 4. Desafío dominante

**tolerancia a fallos**

Kubernetes existe para que un contenedor o un worker puedan morir sin que el servicio desaparezca. El operador declara «quiero 3 réplicas»; el plano vigila que esa cantidad se cumpla y reemplaza las que mueren. Un worker caído se marca como NoReady y sus pods se reprograman en otro worker.

Si el sistema no hiciera eso, estaría asumiendo la falacia de la Semana 2 **«la red es fiable»** (y, de cerca, **«la topología no cambia»**): que los nodos no se caen, que el enlace no se corta y que el conjunto de máquinas es fijo. El laboratorio del ping/pérdida de paquetes ya mostró que esa suposición es falsa. Kubernetes la trata como el caso normal, no como una excepción.

Los otros desafíos existen (escalar workers, muchos controladores concurrentes, RBAC), pero el que _define_ el caso es reponer lo que se cae.

## 5. ¿Qué pasa si cae X?

El nodo cuya caída más duele es **etcd** (el cerebro del plano de control). Un worker duele poco: el plano reagenda. Sin etcd no hay estado del cluster.

- Qué siguen viendo los usuarios: las aplicaciones que _ya estaban corriendo_ en los workers siguen atendiendo. Un usuario de Mercado Libre puede seguir navegando y comprando mientras esos pods no mueran. El kubelet no necesita al API para mantener un contenedor que ya levantó.
- Qué deja de funcionar: no se puede hacer `kubectl apply`, no se despliegan versiones nuevas, no se escala y **no se reponen pods que mueran**. El cluster queda «vivo pero sin cerebro»: el cuerpo camina, pero ya no se adapta. Si en ese mismo rato cae un worker, esas réplicas no vuelven.
- ¿El sistema elige responder (AP) o no equivocarse (CP)?: **etcd elige CP.** Usa consenso (Raft) y necesita mayoría. Ante una partición no inventa un segundo estado: deja de aceptar escrituras (y en modo estricto tampoco lecturas dudosas), igual que la demo del jueves en `MODO=CP` devolvía 503 en vez de un dato que podría divergir. Por eso etcd guarda el estado del cluster: hay una sola verdad. El plano de datos (pods ya en ejecución) se comporta más cerca de AP —sigue respondiendo—, pero la pregunta de este caso es por el estado del cluster, y ese estado es CP.

## 6. La desventaja que vamos a defender

El modelo cluster depende de un maestro. En Kubernetes esa desventaja es concreta: **si etcd (o el plano de control sin réplicas) se cae, el cluster deja de autorrepararse aunque las aplicaciones sigan en pie.**

Ejemplo: un cluster de Mercado Libre con un solo etcd. Un viernes, en un peak, se llena el disco de esa máquina y etcd deja de escribir. Las tiendas que ya están arriba siguen vendiendo. Minutos después se apaga un worker. Esas réplicas **no se reponen**, porque nadie puede leer ni escribir el estado deseado. Tampoco se puede subir réplicas extra para el peak. Replicar el plano (3 o 5 etcd) mitiga el golpe, pero no lo elimina: cuesta consenso, y si se pierde la mayoría el efecto es el mismo.

Eso es lo que la matriz ya advertía: cluster = «mal si cae el maestro». No es que Kubernetes «pueda fallar» en abstracto; es que eligió un dueño único del estado, y ese dueño es el punto que más duele.
