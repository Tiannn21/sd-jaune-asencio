"""Servidor TCP concurrente — Semana 6 (hilo por cliente).

Dominio: MENSAJERÍA INSTANTÁNEA (equipo SD-Jaune-Asencio).
  - un hilo por cliente
  - estado compartido protegido por un Lock
  - manejo explícito de errores y desconexión abrupta
  - logging con identificador del cliente en cada línea

Protocolo por líneas, UTF-8, terminador "\n". Ver protocolo.md.
"""
import logging
import os
import socket
import threading
import time

HOST = os.environ.get("HOST", "0.0.0.0")
PUERTO = int(os.environ.get("PUERTO", "5000"))
SIN_LOCK = os.environ.get("SIN_LOCK", "0") == "1"
TIMEOUT_CLIENTE = int(os.environ.get("TIMEOUT_CLIENTE", "60"))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [servidor] %(threadName)s %(message)s")

# ----------------------------------------------------------------- estado compartido
# pendientes: notificaciones sin leer. Arrancan en 100 para poder medir
# la carrera (mismo papel que el stock del molde de inventario).
# buzon: textos entregados por ENVIAR, en orden de llegada.
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


# ----------------------------------------------------------------- operaciones del dominio
def op_usuarios(arg):
    if arg.strip():
        return "ERROR FORMATO USUARIOS"
    with seccion_critica():
        items = " ".join(
            f"{nombre}:{datos['pendientes']}"
            for nombre, datos in sorted(estado["usuarios"].items())
        )
    return f"OK {items}"


def op_bandeja(arg):
    usuario = arg.strip().lower()
    if not usuario or " " in usuario:
        return "ERROR FORMATO BANDEJA <usuario>"
    with seccion_critica():
        datos = estado["usuarios"].get(usuario)
        if datos is None:
            return "ERROR USUARIO_NO_EXISTE"
        pendientes = datos["pendientes"]
        mensajes = list(estado["buzon"][usuario])
    if mensajes:
        return f"OK {usuario} pendientes:{pendientes} " + " | ".join(mensajes)
    return f"OK {usuario} pendientes:{pendientes}"


def op_registrar(arg):
    usuario = arg.strip().lower()
    if not usuario or " " in usuario:
        return "ERROR FORMATO REGISTRAR <usuario>"
    with seccion_critica():
        if usuario in estado["usuarios"]:
            return "ERROR USUARIO_EXISTE"
        estado["usuarios"][usuario] = {"pendientes": 0}
        estado["buzon"][usuario] = []
    return f"OK {usuario} 0"


def op_enviar(arg):
    partes = arg.split(maxsplit=2)
    if len(partes) != 3:
        return "ERROR FORMATO ENVIAR <origen> <destino> <texto>"
    origen, destino, texto = partes[0].lower(), partes[1].lower(), partes[2]
    if not origen or not destino or not texto.strip():
        return "ERROR FORMATO ENVIAR <origen> <destino> <texto>"
    with seccion_critica():
        if origen not in estado["usuarios"] or destino not in estado["usuarios"]:
            return "ERROR USUARIO_NO_EXISTE"
        actual = estado["usuarios"][destino]["pendientes"]
        time.sleep(0.001)                      # ventana para observar la carrera sin Lock
        estado["usuarios"][destino]["pendientes"] = actual + 1
        nuevo = estado["usuarios"][destino]["pendientes"]
        estado["buzon"][destino].append(f"{origen}:{texto}")
    return f"OK {destino} {nuevo}"


def op_leer(arg):
    partes = arg.split()
    if len(partes) != 2 or not partes[1].isdigit() or int(partes[1]) == 0:
        return "ERROR FORMATO LEER <usuario> <cantidad>"
    usuario, cant = partes[0].lower(), int(partes[1])
    with seccion_critica():
        datos = estado["usuarios"].get(usuario)
        if datos is None:
            return "ERROR USUARIO_NO_EXISTE"
        actual = datos["pendientes"]
        if actual < cant:
            return f"ERROR SIN_MENSAJES {actual}"
        time.sleep(0.001)                      # ventana para observar la carrera sin Lock
        datos["pendientes"] = actual - cant
        nuevo = datos["pendientes"]
        entregados = estado["buzon"][usuario][:cant]
        estado["buzon"][usuario] = estado["buzon"][usuario][cant:]
    if entregados:
        return f"OK {usuario} {nuevo} " + " | ".join(entregados)
    return f"OK {usuario} {nuevo}"


def op_espera(arg):
    try:
        seg = float(arg)
    except ValueError:
        return "ERROR FORMATO ESPERA <segundos>"
    time.sleep(seg)                            # operación lenta, NO toma el Lock
    return f"OK ESPERA {arg}"


OPERACIONES = {
    "USUARIOS": op_usuarios,
    "BANDEJA": op_bandeja,
    "REGISTRAR": op_registrar,
    "ENVIAR": op_enviar,
    "LEER": op_leer,
    "ESPERA": op_espera,
}


def procesar(linea):
    """Devuelve (respuesta, seguir)."""
    partes = linea.strip().split(" ", 1)
    cmd = partes[0].upper() if partes and partes[0] else ""
    arg = partes[1] if len(partes) > 1 else ""
    if cmd == "HOLA":
        return f"OK HOLA {arg or 'anonimo'}", True
    if cmd == "SALIR":
        return "OK CHAO", False
    if cmd in OPERACIONES:
        with seccion_critica():
            estado["operaciones"] += 1
        return OPERACIONES[cmd](arg), True
    return "ERROR COMANDO_DESCONOCIDO", True


# ----------------------------------------------------------------- atención de un cliente
def atender(conn, addr):
    logging.info("conexion de %s", addr)
    conn.settimeout(TIMEOUT_CLIENTE)
    try:
        with conn, conn.makefile("r", encoding="utf-8", errors="replace") as entrada:
            for linea in entrada:
                respuesta, seguir = procesar(linea)
                conn.sendall((respuesta + "\n").encode("utf-8"))
                if not seguir:
                    break
    except (ConnectionResetError, BrokenPipeError) as e:
        logging.warning("cliente %s se desconecto abruptamente (%s)", addr, e.__class__.__name__)
    except socket.timeout:
        logging.warning("cliente %s inactivo %ss, cerrando", addr, TIMEOUT_CLIENTE)
    except Exception as e:  # noqa: BLE001  — un cliente nunca puede botar el servidor
        logging.error("error inesperado con %s: %r", addr, e)
    finally:
        logging.info("cierre de %s | operaciones=%s", addr, estado["operaciones"])


def main():
    logging.info("SIN_LOCK=%s timeout=%ss", SIN_LOCK, TIMEOUT_CLIENTE)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PUERTO))
        srv.listen(64)
        logging.info("escuchando en %s:%s", HOST, PUERTO)
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=atender, args=(conn, addr),
                             name=f"cli-{addr[1]}", daemon=True).start()


if __name__ == "__main__":
    main()
