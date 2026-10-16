# Guion demo 2 — solo comandos

Directorio: `semana-07/laboratorio`

## Antes de entrar

```powershell
docker compose down
docker compose up -d --build
docker compose ps
```

## Minuto 0 a 2

```powershell
diagramas/despliegue_v2.png
```

## Minuto 2 a 4

```powershell
docker compose exec cliente python cliente_http.py POST /mensajes origen=ana destino=beto "texto=hola semana 7"
docker compose exec cliente python cliente_http.py GET /usuarios/noexiste/bandeja
```

## Minuto 4 a 5

```powershell
docker compose up -d
docker compose ps
```

## Minuto 5 a 6

```powershell
docker compose exec cliente python cliente_carga.py --clientes 20 --comando "LEER ana 1" --repeticiones 4
docker compose exec cliente python cliente_http.py GET /usuarios
```

## Minuto 6 a 9 — cae api1

```powershell
docker compose kill api1
docker compose exec cliente python cliente_http.py --repetir 4 GET /usuarios/beto/bandeja
```

## Minuto 6 a 9 — cae el servidor

```powershell
docker compose kill servidor
docker compose exec cliente python cliente_http.py --repetir 2 GET /usuarios
docker compose up -d servidor
docker compose exec cliente python cliente_http.py GET /usuarios/beto/bandeja
```
