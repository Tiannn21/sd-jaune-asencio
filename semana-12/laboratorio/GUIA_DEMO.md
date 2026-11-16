# Guía para demostrar la actividad al profesor

Todos los comandos se ejecutan desde `semana-12/laboratorio/`.
Desde la raíz del repositorio, abrir PowerShell y ejecutar:

```powershell
cd semana-12/laboratorio
function c { docker compose exec cliente @args }
docker compose up -d --build
```

Esperar dos segundos. En cada terminal adicional, ubicarse en esa misma carpeta
 y definir la misma función `c`. No ejecutar otros demos simultáneamente.
Los reinicios siguientes borran los mensajes y usuarios creados durante la prueba.

## Paso 1: localizar el servicio

```powershell
docker compose ps
docker compose logs servidor
c python cliente_pyro.py uri
c python cliente_pyro.py usuarios
```

Mostrar los tres servicios activos: nombres, servidor y cliente.
La URI debe ser `PYRO:directorio@servidor:9100` y el nombre lógico
`sd.jaune-asencio.directorio`. Puede haber usuarios de pruebas anteriores.

Explicar: «El cliente consulta al servidor de nombres para localizar Directorio.
Después llama al objeto en servidor:9100. localhost apuntaría al propio contenedor».
Señalar las cuatro partes de la URI: protocolo, objeto, nodo y puerto.

## Paso 2: demostrar la mensajería del equipo

Para comenzar con un estado conocido:

```powershell
docker compose restart servidor
Start-Sleep -Seconds 2
c python cliente_pyro.py registrar carol
c python cliente_pyro.py enviar ana carol "hola carol"
c python cliente_pyro.py usuarios
c python cliente_pyro.py leer carol 1
c python cliente_pyro.py usuarios
```

Mostrar: carol comienza con 0 pendientes, sube a 1 y vuelve a 0 al leer.
La lectura contiene `ana:hola carol`.

Mostrar `objetos.py`: Directorio delega registrar/enviar/leer/usuarios en dominio.py.
Explicar: «Conservamos el dominio de semana 11; cambiamos la forma de exponerlo».
Ana y Beto tienen 100 pendientes heredados pero no cien textos reales.
Por eso usamos Carol para mostrar el ciclo completo desde cero.

Probar un error de negocio:

```powershell
c python cliente_pyro.py leer carol 1
```

Esperado: `ErrorDominio SIN_MENSAJES 0`. Es correcto: el buzón ya fue leído.

## Paso 3: conversación por referencia y ciclo de vida

```powershell
c python cliente_pyro.py conversacion ana carol "mensaje remoto" --probar-colgante
c python cliente_pyro.py leer carol 1
c python cliente_pyro.py vivos
```

Mostrar `recibí Proxy`, una URI `obj_...`, el borrador y la confirmación.
Luego aparece `unknown object`: la compra del demo original aquí equivale al envío.
El mensaje sí fue enviado, pero la conversación ya se desregistró y la prueba intenta
consultarla otra vez. Leer confirma el texto y vivos muestra cero.

Explicar: «El objeto vive en el servidor; recibo una referencia, no una copia.
ver devuelve una copia de datos. confirmar envía el texto y termina el objeto».

```powershell
c python cliente_pyro.py conversacion ana carol "no enviar" --cancelar
c python cliente_pyro.py usuarios
```

Mostrar que cancelar termina el borrador sin incrementar los pendientes de Carol.

Abrir `.env`, cambiar `POR_VALOR=0` a `POR_VALOR=1`, guardar y ejecutar:

```powershell
docker compose up -d servidor
Start-Sleep -Seconds 2
c python cliente_pyro.py conversacion ana beto "prueba por valor"
```

Esperado: `unsupported serialized class: objetos.Conversacion`.
Explicar: «Sin registrarlo, intenta enviar el objeto por valor; el cliente no tiene
un convertidor habilitado para reconstruir esa clase».

Restaurar `POR_VALOR=0` en `.env`, guardar y repetir `docker compose up -d servidor`.
Usamos Beto porque recrear el servidor elimina a Carol.

## Paso 4: comparar single y session

Con `MODO=single` en `.env`:

```powershell
docker compose restart servidor
Start-Sleep -Seconds 2
c python cliente_pyro.py quien --veces 2
```

Mostrar: A y B comparten instancia 1; llamadas 1, 2, 3, 4.
Cambiar a `MODO=session` en `.env`, guardar:

```powershell
docker compose up -d servidor
Start-Sleep -Seconds 2
c python cliente_pyro.py quien --veces 2
```

Mostrar: A usa instancia 1 con llamadas 1 y 2; B usa instancia 2 con llamadas 1 y 2.
Explicar: «single comparte la instancia; session crea una por conexión.
El contador pertenece a Directorio; los buzones pertenecen al módulo dominio.py
compartido en el proceso. El modo no crea un buzón independiente por cliente».

Restaurar `MODO=single`, guardar, ejecutar `docker compose up -d servidor`
y esperar dos segundos antes del paso siguiente.

## Paso 5: provocar las fallas

Verificar `.env`: MODO=single, POR_VALOR=0, REREGISTRO=0.
Abrir tres terminales en laboratorio y definir `c` en cada una.

Terminal 1:

```powershell
c python cliente_pyro.py enviar ana beto "antes de caer"
```

Terminal 2:

```powershell
c python cliente_pyro.py vigilar
```

Mostrar Beto con 101 pendientes. Terminal 3:

```powershell
c python cliente_pyro.py conversacion ana beto "pendiente" --esperar 40
```

Cuando aparezca «espero», en terminal 1, antes de que pasen los 40 segundos:

```powershell
docker compose kill servidor
c python cliente_pyro.py usuarios
docker compose start servidor
```

Mostrar en terminal 2 la falla y posterior recuperación. Tras reiniciar, Beto vuelve
a 100: el estado estaba en memoria. La conversación pendiente falla al confirmar;
puede mostrar desconexión por su conexión anterior o referencia inexistente.
Este cliente no reintenta escrituras automáticamente.

Explicar: «Reiniciar el servicio no reconstruye las conversaciones anteriores.
Perder una respuesta tampoco permite saber siempre si una operación se aplicó».

Esperar a que vigilar vuelva a responder. En terminal 1:

```powershell
docker compose kill nombres
c python cliente_pyro.py usuarios
docker compose start nombres
Start-Sleep -Seconds 2
c python cliente_pyro.py usuarios
```

Mostrar: vigilar sigue funcionando por su conexión existente; el cliente nuevo
falla primero con `Failed to locate the nameserver` y después con `unknown name`.
Nombres volvió, pero perdió su registro. Recuperar:

```powershell
docker compose restart servidor
Start-Sleep -Seconds 2
c python cliente_pyro.py uri
c python cliente_pyro.py usuarios
```

Explicar: «Servidor vuelve a publicar su nombre al arrancar. REREGISTRO=5 permitiría
republicarlo periódicamente, con llamadas extra y una ventana de indisponibilidad.
Eso no guarda los mensajes: necesitamos persistencia para conservarlos».
Detener vigilar con Ctrl+C en terminal 2.

## Documentación que se muestra al cerrar

- `observaciones.md`: cinco pasos, resultados reales y explicación de fallas.
- `calidad.md`: lista técnica verificada.
- `pruebas_integracion.py`: pruebas de FIFO, excepciones, referencias y cancelación.
- `../../proyecto/ALCANCE.md`: propuesta de Directorio, Conversacion y Buzon en nodos
  distintos, RabbitMQ con dos workers y coordinación. Es trabajo futuro del integrador.
- `../../proyecto/bitacora.md`: decisiones, problemas y próximos pasos.

Pedir al profesor revisar el alcance y registrar su decisión real. La aprobación
está pendiente; no presentarla como ya concedida. Confirmar asistencia y responsables
propuestos en la bitácora antes de entregarla.

Para mostrar la verificación automática:

```powershell
c python pruebas_integracion.py
```

Debe terminar con `OK: registro, errores, FIFO, copia, referencia, confirmar, cancelar y limpieza`.
Los errores que aparecen antes son los casos negativos esperados por las pruebas.
Para apagar al terminar: `docker compose down`.
