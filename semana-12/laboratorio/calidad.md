# Lista de calidad antes del push (semana 12)

Marquen con una x lo que cumplen. Lo que quede sin marcar va como pendiente en la bitácora.

- [x] Cada clase expuesta tiene docstring que dice para qué sirve
- [x] Cada método expuesto tiene docstring que dice si cambia estado o no
- [x] `dominio.py` es el mismo de la semana 11, no se modificó para Pyro5
- [x] El cliente captura `CommunicationError` y `NamingError` y muestra un mensaje entendible
- [x] Las excepciones propias del dominio llegan al cliente con su nombre (registradas con `register_dict_to_class`)
- [x] El objeto con estado se desregistra al terminar su vida (confirmar o cancelar)
- [x] No hay direcciones IP escritas en el código, todo sale de variables de entorno
- [x] `README.md` de `semana-12/laboratorio/` explica cómo levantar y probar en tres comandos
- [x] `observaciones.md` tiene los cinco pasos completos

Verificación realizada el 13-11-2026 con Docker: pruebas_integracion.py, CLI, modos single/session y caídas controladas.
El SHA-256 de ambos dominio.py coincide: ABF684F0B4E97A2AD61FE3C17C603B72BD0C8A50A50A95A0892B6D28D6A7F435.
Las consultas no cambian el dominio; la telemetría sí incrementa llamadas, como indican los docstrings.
Los archivos originales de semanas anteriores y las plantillas permanecen intactos.
Aprobación docente y publicación remota son pendientes administrativos, no verificaciones técnicas completadas.
