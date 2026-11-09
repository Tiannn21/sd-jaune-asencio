# Cuadro comparativo — RMI, CORBA, DCOM y JSON-RPC

**Equipo:** SD-Jaune-Asencio<br>
**Integrantes:** Diego Jaune y Sebastián Asencio<br>
**Semana 10, trabajo autónomo**

Comparación relacionada con nuestro servicio de mensajería instantánea y las operaciones `ENVIAR` y `LEER` de la semana 9.

| Criterio | Java RMI[^rmi] | CORBA[^corba] | DCOM[^dcom] | JSON-RPC 2.0[^jsonrpc] |
|---|---|---|---|---|
| Año y origen (quién lo creó y para qué) | Sun lo incorporó en JDK 1.1, en 1997, para invocar métodos entre objetos de distintas máquinas virtuales Java.[^historia-rmi] | El OMG publicó su primera versión en 1991 para comunicar objetos de distintos fabricantes, lenguajes y plataformas. | Microsoft lo distribuyó con Windows NT 4.0 en 1996 para extender COM a otras máquinas.[^historia-dcom] | El JSON-RPC Working Group publicó la especificación 2.0 en 2010, basada en una versión de 2009, para definir llamadas remotas sencillas con JSON. |
| Modelo (objetos remotos o procedimientos remotos) | Objetos remotos con identidad, métodos y posible estado. El cliente invoca un objeto mediante un representante local o stub. | Objetos distribuidos accesibles mediante un intermediario llamado ORB, que dirige las invocaciones. | Objetos COM remotos que exponen interfaces y pueden conservar estado entre llamadas. | Procedimientos identificados por nombre; no define sesiones ni objetos remotos. La aplicación sí puede conservar estado, como nuestros buzones. |
| Contrato o IDL (cómo se declara la interfaz) | Una interfaz Java extiende `java.rmi.Remote` y declara los métodos remotos y sus excepciones. | Un archivo OMG IDL describe operaciones y tipos, independientemente del lenguaje de implementación. | Interfaces descritas con IDL y compiladas con MIDL; también pueden generarse bibliotecas de tipos para Automation.[^midl] | No exige IDL. El equipo documenta los métodos, parámetros y resultados del servicio. |
| Transporte y formato de los mensajes | Habitualmente JRMP sobre TCP, con serialización binaria de objetos Java. | IIOP sobre TCP, basado en GIOP, con representación binaria CDR. | ORPC sobre la infraestructura RPC de Microsoft, por ejemplo sobre TCP; utiliza representación binaria NDR. | JSON textual sobre un transporte elegido por la aplicación; nuestro prototipo usa HTTP. |
| Lenguajes y plataformas que soporta | Orientado a Java; funciona entre sistemas operativos que tengan una JVM compatible. | Varios lenguajes, como C++, Java o Python, mediante sus correspondencias IDL y un ORB compatible. | Varios lenguajes capaces de utilizar COM, especialmente en Windows, como C++ y Visual Basic. | Cualquier lenguaje que procese JSON y utilice el transporte acordado. |
| Referencias remotas y estado (¿el servidor recuerda al cliente?) | El cliente conserva referencias a objetos del servidor y RMI incluye recolección de basura distribuida. El estado pertenece a los objetos, no necesariamente a una sesión por cliente. | El cliente usa referencias a objetos, que pueden mantener estado; su ciclo de vida depende de la aplicación y de los servicios del ORB. No presupone un recolector distribuido como el de Java RMI. | Mantiene referencias a interfaces remotas; utiliza conteo de referencias y mecanismos de ping para gestionar su vigencia. | No aplica la referencia remota de objetos ni su recolección distribuida. La aplicación administra sus datos. |
| Manejo de errores (cómo viaja un fallo al cliente) | Propaga excepciones de la aplicación y `RemoteException` para problemas de comunicación o ejecución remota. | Distingue excepciones del sistema y excepciones de usuario declaradas en IDL. | Devuelve códigos `HRESULT` y puede aportar información adicional del error; también pueden fallar las llamadas RPC.[^errores-com] | Devuelve `error` con `code`, `message` y `data` opcional; el éxito usa `result`. |
| Relación con las cinco decisiones de la semana 9 (enmarcado, versión, id, errores, tipos) | JRMP organiza los mensajes y su versión; el runtime asocia la respuesta con la llamada, propaga excepciones y serializa tipos Java. El programador decide la compatibilidad del contrato y los errores del negocio. | GIOP define límites, versión e identificador de solicitud; CDR e IDL definen los tipos y las excepciones. El equipo decide cómo evoluciona su interfaz y qué errores propios declara. | RPC aporta enmarcado, versión y correlación; IDL/NDR fija los tipos y COM/RPC comunica errores. El programador define las interfaces y sus reglas de negocio. | El transporte resuelve el enmarcado; `jsonrpc` indica versión, `id` correlaciona y `error` estructura fallos. JSON define tipos básicos; la aplicación valida sus parámetros y errores propios. |
| Estado actual (vigente, legado, reemplazado por qué) | Sigue disponible en Java y se usa en JMX. Para nuestro servicio Python, JSON-RPC o gRPC facilitarían trabajar entre lenguajes.[^jmx] | Tecnología histórica con especificaciones todavía publicadas por OMG, incluida CORBA 3.4 de 2021. Para un servicio nuevo como el nuestro, preferiríamos una API HTTP o gRPC por su integración con nuestras herramientas. | Sigue presente en Windows, por ejemplo en WMI remoto. Para servicios nuevos entre plataformas consideraríamos API HTTP o gRPC; Microsoft también documenta la migración de WCF a gRPC.[^wmi][^grpc] | Continúa en uso, por ejemplo en Ethereum. Resulta adecuado para interfaces de llamadas simples.[^ethereum] |
| Caso de uso típico, real o histórico | Administración y monitoreo remoto de aplicaciones Java mediante el conector RMI de JMX.[^jmx] | Integración de equipos y aplicaciones heterogéneas en ámbitos financieros y médicos, usos descritos por OMG en su FAQ.[^corba] | Consulta y administración remota de equipos Windows mediante WMI, cuyas conexiones utilizan configuración DCOM.[^wmi] | La API de nodos Ethereum permite consultar bloques y enviar transacciones mediante JSON-RPC.[^ethereum] |

## Conclusión del equipo (5 a 8 líneas)

JSON-RPC es la tecnología que más se parece a nuestro protocolo de mensajería de la semana 9.<br>
En ambos enviamos una operación con argumentos y recibimos un resultado o error asociado a un identificador.<br>
Ahora `method` y `params` reemplazan a `operacion` y `argumentos`, y HTTP resuelve el enmarcado que antes hacíamos con cuatro bytes de largo.<br>
La especificación fija el formato de los mensajes, mientras nosotros conservamos las reglas de `enviar`, `leer` y el estado del buzón.<br>
Entre las cuatro tecnologías, elegiríamos JSON-RPC para nuestro servicio interno por su sencillez y por adaptarse a Python y FastAPI.<br>
Para una API pública, entre estas opciones también elegiríamos JSON-RPC sobre HTTPS, con autenticación, parámetros documentados y límites de solicitudes.<br>
Si consideramos alternativas fuera del cuadro, evaluaríamos gRPC para contratos tipados internos y REST para una API pública organizada en recursos.[^grpc]

## Fuentes consultadas

Consulta: 6 de noviembre de 2026. «s. f.» indica que la página no presenta una fecha de publicación clara. Las elecciones para nuestro servicio son conclusiones del análisis, no afirmaciones de que las tecnologías anteriores hayan desaparecido.

[^rmi]: Oracle. (s. f., documentación de Java SE 25). *Java Remote Method Invocation*: [Distributed Object Model](https://docs.oracle.com/en/java/javase/25/docs/specs/rmi/objmodel.html), [RMI System Overview](https://docs.oracle.com/en/java/javase/25/docs/specs/rmi/arch.html) y [RMI Wire Protocol](https://docs.oracle.com/en/java/javase/25/docs/specs/rmi/protocol.html).

[^historia-rmi]: Oracle. (s. f., documentación de Java SE 7). [*Introducing the CORBA Programming Models*, sección histórica sobre RMI](https://docs.oracle.com/javase/7/docs/technotes/guides/idl/corba.html).

[^jmx]: Oracle. (s. f., documentación de Java SE 25). [*Module java.management.rmi*](https://docs.oracle.com/en/java/javase/25/docs/api/java.management.rmi/module-summary.html).

[^corba]: Object Management Group. (2021). [*CORBA Specification, versión 3.4*, documentos e historial de versiones](https://www.omg.org/spec/CORBA/). Véase también OMG. (s. f.). [*CORBA FAQ*](https://www.omg.org/gettingstarted/corbafaq.htm).

[^dcom]: Microsoft. (2024). *Distributed Component Object Model (DCOM) Remote Protocol*: [Overview](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-dcom/86b9cf84-df2e-4f0b-ac22-1b957627e1ca) y [Glossary](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-dcom/ba4c4d80-ef81-49b4-848f-9714d72b5c01).

[^historia-dcom]: Microsoft. (1996). [*Microsoft Delivers Preview of Windows NT Server 5.0 to 3,500 Developers*](https://news.microsoft.com/source/1996/11/04/microsoft-delivers-preview-of-windows-nt-server-5-0-to-3500-developers/). Confirma la distribución de DCOM con Windows NT Server 4.0 ese año.

[^midl]: Microsoft. (2021). [*Microsoft Interface Definition Language*](https://learn.microsoft.com/en-us/windows/win32/midl/midl-start-page).

[^errores-com]: Microsoft. (s. f.). [*Error Handling in COM*](https://learn.microsoft.com/en-us/windows/win32/com/error-handling-in-com).

[^wmi]: Microsoft. (2021). [*Connecting to WMI on a Remote Computer*](https://learn.microsoft.com/en-us/windows/win32/wmisdk/connecting-to-wmi-on-a-remote-computer).

[^jsonrpc]: JSON-RPC Working Group. (2010; actualización de 2013). [*JSON-RPC 2.0 Specification*](https://www.jsonrpc.org/specification).

[^ethereum]: Ethereum.org. (s. f.). [*JSON-RPC API*](https://ethereum.org/developers/docs/apis/json-rpc/).

[^grpc]: Microsoft. (2025). [*gRPC for Windows Communication Foundation (WCF) developers*](https://learn.microsoft.com/en-us/aspnet/core/grpc/why-migrate-wcf-to-dotnet-grpc?view=aspnetcore-10.0).
