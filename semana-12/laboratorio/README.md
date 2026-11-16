# Semana 12: mensajería instantánea con Pyro5

Equipo SD-Jaune-Asencio: Diego Jaune y Sebastián Asencio.

Esta es la entrega del PDF. La carpeta semana-12/demo
conserva el material de referencia. El dominio se copió exactamente desde
semana-11/laboratorio/dominio.py: usuarios, registrar, enviar y leer.

## Levantar y probar en tres comandos

Desde esta carpeta, con Docker Desktop activo y sin contenedores de otras semanas:

```powershell
docker compose up -d --build
docker compose exec cliente python cliente_pyro.py conversacion ana beto "hola semana 12"
docker compose exec cliente python cliente_pyro.py leer beto 1
```

Si el servidor aún se está registrando, esperar dos segundos y repetir la consulta.
Antes de levantar, bajar el demo desde la raíz:
`docker compose -f semana-12/demo/docker-compose.yml down`.
Los nombres sd_servidor, sd_cliente y sd_nombres son compartidos entre ejercicios.

## Cómo funciona

1. Directorio se publica como sd.jaune-asencio.directorio.
2. El cliente consulta nombres:9090 y conecta con servidor:9100.
3. abrir_conversacion crea un objeto con participantes y borrador en el servidor.
4. El cliente recibe un Proxy. agregar reemplaza el borrador, sin enviar.
5. ver devuelve un diccionario por valor: cambiar esa copia no cambia el servidor.
6. confirmar llama dominio.enviar una vez y desregistra el objeto; cancelar lo
   desregistra sin enviar. La referencia anterior deja de ser válida.

La conversación del taller representa un intercambio con un único mensaje en borrador.
No es aún una sala de chat permanente. No hay interfaz gráfica ni autenticación.

## Comandos

```powershell
function c { docker compose exec cliente @args }
c python cliente_pyro.py uri
c python cliente_pyro.py usuarios
c python cliente_pyro.py registrar carol
c python cliente_pyro.py enviar ana carol "mensaje directo"
c python cliente_pyro.py leer carol 1
c python cliente_pyro.py conversacion ana beto "prueba" --probar-colgante
c python cliente_pyro.py conversacion ana beto "descartar" --cancelar
c python cliente_pyro.py vivos
c python cliente_pyro.py quien --veces 2
c python pruebas_integracion.py
```

--probar-colgante produce un error intencional DESPUÉS del envío exitoso.
Sin esa opción, enviar una conversación termina normalmente.

## Experimentos de configuración

Editar .env y ejecutar `docker compose up -d servidor`; esperar dos segundos.
Restaurar cada variable al terminar. Cambiar Python exige reconstruir con --build.

| Variable | Valor inicial | Experimento |
|---|---|---|
| EQUIPO | jaune-asencio | Nombre lógico del equipo |
| MODO | single | Comparar quien --veces 2 con session |
| POR_VALOR | 0 | Con 1, abrir una conversación falla al deserializar objetos.Conversacion |
| REREGISTRO | 0 | Con 5, vuelve a publicar el nombre cada cinco segundos |

En PowerShell también sirve `$env:MODO='session'` antes de compose.
Esa variable tiene prioridad sobre .env: quitarla con
`Remove-Item Env:MODO` al terminar si se usó esta alternativa.

## Falla en tres terminales

Todas deben estar en esta carpeta. Configuración single, POR_VALOR=0, REREGISTRO=0.

Terminal 2:
```powershell
docker compose exec cliente python cliente_pyro.py vigilar
```

Terminal 3:
```powershell
docker compose exec cliente python cliente_pyro.py conversacion ana beto "pendiente" --esperar 30
```

Terminal 1, mientras espera:
```powershell
docker compose kill servidor
docker compose exec cliente python cliente_pyro.py usuarios
docker compose start servidor
```

Esperar a que el observador recupere conexión y termine la conversación pendiente.
Esta última puede recibir desconexión o unknown object según cuándo se confirme.
No se reintentan escrituras automáticamente: sin deduplicación durable, una
respuesta perdida no permite asegurar si el envío ocurrió.

Luego, terminal 1:
```powershell
docker compose kill nombres
docker compose exec cliente python cliente_pyro.py usuarios
docker compose start nombres
# Esperar dos segundos.
docker compose exec cliente python cliente_pyro.py usuarios
docker compose restart servidor
# Esperar dos segundos.
docker compose exec cliente python cliente_pyro.py usuarios
```

El observador conectado sigue sin nombres. El cliente nuevo necesita resolver.
Al arrancar nombres, el registro está vacío; reiniciar servidor lo repone.
Terminar vigilar con Ctrl+C. Limpiar al finalizar con `docker compose down`.

## Límites heredados y decisiones

Ana y Beto empiezan con 100 pendientes y buzones vacíos: son contadores heredados,
no cien textos reales. Para pruebas realistas usar registrar, que parte de cero.
El estado se comparte en dominio.py, independientemente del modo de instancia.
Reiniciar servidor restaura ana=100 y beto=100 y pierde usuarios nuevos y textos.
Una conversación abandonada queda viva mientras el proceso siga activo: no hay TTL.
Un fallo de dominio permite corregir o cancelar mediante la misma referencia.
No se transportó la deduplicación de gRPC; queda como trabajo del integrador.
