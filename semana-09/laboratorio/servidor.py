"""Servidor TCP concurrente — Semana 9 (hilo por cliente, mensajes estructurados).

Dominio: mensajería instantánea (equipo SD-Jaune-Asencio).
El estado es el de la semana 7. Cambia la forma de leer y escribir: cada
mensaje va enmarcado y codificado con codec.py (JSON o binario según CODEC).
"""
import json
import os
import socket
import struct
import threading
import time

import codec
from mensajes import Solicitud, VERSION, ok, error

HOST = "0.0.0.0"
PUERTO = int(os.environ.get("SERVIDOR_PUERTO", "5000"))
TIMEOUT = float(os.environ.get("TIMEOUT_SERVIDOR", "30"))
SIN_LOCK = os.environ.get("SIN_LOCK", "0") == "1"

# pendientes: notificaciones sin leer. Arrancan en 100 para poder medir
# la carrera. buzon: textos entregados por ENVIAR, en orden de llegada.
estado = {
    "usuarios": {
        "ana": {"pendientes": 100},
        "beto": {"pendientes": 100},
    },
    "buzon": {"ana": [], "beto": []},
    "operaciones": 0,
}
lock = threading.Lock()


class SinLock:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def seccion_critica():
    return SinLock() if SIN_LOCK else lock


def log(*args):
    print(time.strftime("%H:%M:%S"), f"[{threading.current_thread().name}]", *args, flush=True)


def _texto_enviar(args):
    """ENVIAR origen destino texto. El texto puede traer espacios."""
    if len(args) < 3:
        return None
    origen, destino = args[0].lower(), args[1].lower()
    texto = args[2] if len(args) == 3 else " ".join(args[2:])
    if not origen or not destino or not texto.strip():
        return None
    return origen, destino, texto


# ---------------------------------------------------------------- dominio
def procesar(sol):
    """Recibe una Solicitud y devuelve una Respuesta."""
    op, args = sol.operacion.upper(), sol.argumentos
    if op == "HOLA":
        nombre = args[0] if args else "anonimo"
        return ok(sol, ["HOLA", nombre])
    if op == "SALIR":
        return ok(sol, ["CHAO"])
    if op not in ("USUARIOS", "BANDEJA", "REGISTRAR", "ENVIAR", "LEER", "ESPERA"):
        return error(sol.id, "COMANDO_DESCONOCIDO")

    with seccion_critica():
        estado["operaciones"] += 1

    if op == "USUARIOS":
        if args:
            return error(sol.id, "FORMATO USUARIOS")
        with seccion_critica():
            items = [
                f"{nombre}:{datos['pendientes']}"
                for nombre, datos in sorted(estado["usuarios"].items())
            ]
        return ok(sol, items)

    if op == "BANDEJA":
        if len(args) != 1 or not args[0].strip():
            return error(sol.id, "FORMATO BANDEJA <usuario>")
        usuario = args[0].lower()
        with seccion_critica():
            datos = estado["usuarios"].get(usuario)
            if datos is None:
                return error(sol.id, "USUARIO_NO_EXISTE")
            pendientes = datos["pendientes"]
            mensajes = list(estado["buzon"][usuario])
        return ok(sol, [usuario, str(pendientes), *mensajes])

    if op == "REGISTRAR":
        if len(args) != 1 or not args[0].strip():
            return error(sol.id, "FORMATO REGISTRAR <usuario>")
        usuario = args[0].lower()
        with seccion_critica():
            if usuario in estado["usuarios"]:
                return error(sol.id, "USUARIO_EXISTE")
            estado["usuarios"][usuario] = {"pendientes": 0}
            estado["buzon"][usuario] = []
        return ok(sol, [usuario, "0"])

    if op == "ENVIAR":
        partes = _texto_enviar(args)
        if partes is None:
            return error(sol.id, "FORMATO ENVIAR <origen> <destino> <texto>")
        origen, destino, texto = partes
        with seccion_critica():
            if origen not in estado["usuarios"] or destino not in estado["usuarios"]:
                return error(sol.id, "USUARIO_NO_EXISTE")
            actual = estado["usuarios"][destino]["pendientes"]
            time.sleep(0.001)
            estado["usuarios"][destino]["pendientes"] = actual + 1
            nuevo = estado["usuarios"][destino]["pendientes"]
            estado["buzon"][destino].append(f"{origen}:{texto}")
        return ok(sol, [destino, str(nuevo)])

    if op == "LEER":
        if len(args) != 2 or not args[1].isdigit() or int(args[1]) == 0:
            return error(sol.id, "FORMATO LEER <usuario> <cantidad>")
        usuario, cant = args[0].lower(), int(args[1])
        with seccion_critica():
            datos = estado["usuarios"].get(usuario)
            if datos is None:
                return error(sol.id, "USUARIO_NO_EXISTE")
            actual = datos["pendientes"]
            if actual < cant:
                return error(sol.id, f"SIN_MENSAJES {actual}")
            time.sleep(0.001)
            datos["pendientes"] = actual - cant
            nuevo = datos["pendientes"]
            entregados = estado["buzon"][usuario][:cant]
            estado["buzon"][usuario] = estado["buzon"][usuario][cant:]
        return ok(sol, [usuario, str(nuevo), *entregados])

    try:
        segundos = float(args[0]) if args else None
        if segundos is None or len(args) != 1:
            raise ValueError
    except (ValueError, IndexError):
        return error(sol.id, "FORMATO ESPERA <segundos>")
    time.sleep(segundos)
    return ok(sol, ["ESPERA", args[0]])


# ---------------------------------------------------------------- conexión
def atender(conn, addr):
    conn.settimeout(TIMEOUT)
    log("conectado", addr)
    try:
        while True:
            try:
                sol = codec.recibir(conn, Solicitud)
            except ConnectionError:
                break
            except (struct.error, json.JSONDecodeError, UnicodeDecodeError, ValueError, KeyError, IndexError) as e:
                nombre = "struct.error" if isinstance(e, struct.error) else type(e).__name__
                log("mensaje mal formado desde", addr, "->", nombre, e)
                codec.enviar(conn, error(0, f"mensaje mal formado ({nombre})"))
                break
            if sol.version != VERSION:
                log("versión no soportada", sol.version, "desde", addr)
                codec.enviar(conn, error(sol.id, f"versión {sol.version} no soportada, use {VERSION}"))
                continue
            log("solicitud", sol.id, sol.operacion, sol.argumentos)
            resp = procesar(sol)
            codec.enviar(conn, resp)
            if sol.operacion.upper() == "SALIR":
                break
    except socket.timeout:
        log("timeout de", addr, "sin mensajes completos en", TIMEOUT, "s")
    except OSError as e:
        log("cliente", addr, "se desconecto abruptamente", type(e).__name__)
    finally:
        conn.close()
        log("desconectado", addr, "| operaciones=", estado["operaciones"])


def main():
    log(f"mensajería v{VERSION} en {HOST}:{PUERTO}  codec={codec.CODEC}  SIN_LOCK={SIN_LOCK}")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PUERTO))
    srv.listen(64)
    n = 0
    while True:
        conn, addr = srv.accept()
        n += 1
        threading.Thread(target=atender, args=(conn, addr), name=f"cli-{n}", daemon=True).start()


if __name__ == "__main__":
    main()
