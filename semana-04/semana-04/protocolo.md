# Protocolo de aplicación — Equipo **SD-Jaune-Asencio**

Versión 0.1 · semana 4 · Este archivo evoluciona cada semana junto con el servicio.

## 1. Transporte

- Protocolo de transporte: TCP
- Puerto del servidor: 5000
- Codificación: UTF-8
- Delimitador de mensaje: una línea terminada en `\n`
- Quién inicia: el cliente. El servidor solo responde.

## 2. Mensajes

| Comando (cliente → servidor) | Argumentos          | Respuesta (servidor → cliente) | ¿Cambia el estado de la conexión? |
| ---------------------------- | ------------------- | ------------------------------ | --------------------------------- |
| `HOLA <nombre>`              | nombre, texto libre | `OK hola <nombre>`             | Sí, guarda el nombre              |
| `ECO <texto>`                | texto libre         | `ECO <texto>`                  | Sí, incrementa el contador       |
| `CONTAR`                     | ninguno             | `OK <n>`                       | Sí, incrementa el contador       |
| `SALIR`                      | ninguno             | `ADIOS`                        | Sí, termina la conexión         |
| `MAYUS <texto>` (propia)     | texto libre         | `OK <TEXTO EN MAYÚSCULAS>`     | Sí, incrementa el contador       |
| (cualquier otro)             | texto libre         | `ERROR comando desconocido`    | Sí, incrementa el contador       |

## 3. Estado

- ¿Qué recuerda el servidor de cada conexión? **El nombre enviado en `HOLA` y la cantidad de mensajes recibidos en esa conexión.**
- ¿Qué pasa con ese estado cuando el cliente se desconecta? **Se elimina al cerrar el socket; no se conserva para otra conexión.**
- Si el servidor se reinicia mientras un cliente está conectado, ¿qué pierde el cliente? **Pierde la sesión y el estado anterior; al reconectar, el nombre queda vacío y el contador comienza en cero.**

## 4. Secuencia típica

Dibujen o describan una sesión completa, desde `connect` hasta `ADIOS`.

```
cliente                servidor
   |---- connect --------->|
   |---- HOLA equipo ----->|
   |<--- OK hola equipo ---|
   |         ...           |
   |---- SALIR ----------->|
   |<--- ADIOS ------------|
   |         (cierre)      |
```

La sesión comienza con `connect`. El cliente envía una línea por vez y espera la
respuesta correspondiente. Después de recibir `ADIOS`, ambos lados cierran el
socket; si el cliente se corta sin `SALIR`, el servidor detecta el fin de la
entrada y cierra la conexión.

## 5. Errores

| Situación                          | Qué ve el cliente           | Qué ve el servidor |
| ---------------------------------- | --------------------------- | ------------------ |
| Comando desconocido                | `ERROR comando desconocido` | log con el comando |
| Servidor caído durante la sesión   | `CONEXIÓN PERDIDA: ConnectionError: el servidor cerró la conexión sin responder` al enviar el siguiente comando | El proceso termina; no registra el comando posterior |
| Cliente sin red durante la sesión  | `TIMEOUT: el servidor no respondió en 5 s. ¿Caído, sin red o lento? No se puede saber.` | No aparece un nuevo comando en el log; el servidor queda esperando en esa conexión |
| Cliente corta sin `SALIR` (Ctrl+C) | `corte abrupto desde el cliente (sin SALIR)` | cierre de la conexión al detectar EOF, con el contador de mensajes recibidos |
