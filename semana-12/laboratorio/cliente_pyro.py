"""CLI del chat: uri, usuarios/listar, registrar, enviar, leer, conversacion,
quien, vivos y vigilar. No reintenta escrituras: una respuesta perdida puede
corresponder a un mensaje ya enviado. Usar --help para ver argumentos.
"""
import argparse
import os
import sys
import time

from Pyro5.api import Proxy, locate_ns, register_dict_to_class
from Pyro5.errors import (CommunicationError, DaemonError, NamingError,
                          SerializeError, get_pyro_traceback)

NS_HOST = os.environ.get("NOMBRES_HOST", "nombres")
NS_PUERTO = int(os.environ.get("NOMBRES_PUERTO", "9090"))
EQUIPO = os.environ.get("EQUIPO", "referencia")
NOMBRE = f"sd.{EQUIPO}.directorio"


# Las excepciones también viajan serializadas (por valor). Pyro5 solo sabe
# reconstruir las de Python. Las propias del dominio hay que enseñárselas.
import dominio  # noqa: E402


def _a_excepcion(nombre_clase, datos):
    clase = getattr(dominio, nombre_clase.split(".")[-1])
    return clase(*datos.get("args", ()))


for _nombre in ("ErrorDominio", "ErrorParametros"):
    register_dict_to_class(f"dominio.{_nombre}", _a_excepcion)


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def directorio():
    """Proxy al Directorio. La URI se resuelve en el servidor de nombres."""
    proxy = Proxy(f"PYRONAME:{NOMBRE}@{NS_HOST}:{NS_PUERTO}")
    proxy._pyroTimeout = 5
    return proxy


def cmd_uri(_):
    with locate_ns(host=NS_HOST, port=NS_PUERTO) as ns:
        log(f"{NOMBRE} -> {ns.lookup(NOMBRE)}")
        log(f"nombres registrados {sorted(ns.list().keys())}")


def cmd_listar(_):
    with directorio() as inv:
        log(f"usuarios {inv.usuarios()}")


def cmd_registrar(a):
    with directorio() as inv:
        log(f"registrar -> {inv.registrar(a.usuario)}")


def cmd_enviar(a):
    with directorio() as inv:
        log(f"enviar -> {inv.enviar(a.origen, a.destino, a.texto)}")


def cmd_leer(a):
    with directorio() as inv:
        log(f"leer -> {inv.leer(a.usuario, a.cantidad)}")


def cmd_quien(a):
    """Mismo proxy varias veces y después un proxy nuevo. Muestra el modo."""
    for etiqueta in ("proxy A", "proxy B"):
        with directorio() as inv:
            for _ in range(a.veces):
                log(f"{etiqueta} -> {inv.quien_soy()}")


def cmd_vivos(_):
    with directorio() as inv:
        log(f"conversaciones vivas en el servidor {inv.conversaciones_vivas()}")


def cmd_conversacion(a):
    with directorio() as inv:
        conversacion = inv.abrir_conversacion(a.origen, a.destino)
        with conversacion:
            conversacion._pyroTimeout = 5
            log(f"recibí {type(conversacion).__name__}, referencia {conversacion._pyroUri}")
            conversacion.agregar(a.texto)
            log(f"estado en el servidor {conversacion.ver()}")
            if a.esperar:
                log(f"espero {a.esperar} s antes de confirmar")
                time.sleep(a.esperar)
            if a.cancelar:
                log(f"cancelar -> {conversacion.cancelar()}")
            else:
                log(f"confirmar -> {conversacion.confirmar()}")
            if a.probar_colgante:
                log("uso la referencia después de terminar")
                conversacion.ver()


def cmd_vigilar(a):
    """Llama listar() cada a.cada segundos con el MISMO proxy y reporta fallas."""
    inv = directorio()
    while True:
        try:
            log(f"ok, usuarios {inv.usuarios()}  [{inv._pyroUri}]")
        except CommunicationError as e:
            log(f"FALLA de comunicación {type(e).__name__} {e}")
            try:
                inv._pyroReconnect(tries=1)
                log("reconectado")
            except (CommunicationError, NamingError) as e2:
                log(f"no pude reconectar {type(e2).__name__}")
        except NamingError as e:
            log(f"FALLA de nombres {e}")
        time.sleep(a.cada)


def main():
    p = argparse.ArgumentParser(description="Cliente Pyro5, semana 12")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("uri").set_defaults(f=cmd_uri)
    sub.add_parser("listar").set_defaults(f=cmd_listar)
    sub.add_parser("usuarios").set_defaults(f=cmd_listar)
    s = sub.add_parser("registrar")
    s.add_argument("usuario")
    s.set_defaults(f=cmd_registrar)
    s = sub.add_parser("enviar")
    s.add_argument("origen")
    s.add_argument("destino")
    s.add_argument("texto")
    s.set_defaults(f=cmd_enviar)
    s = sub.add_parser("leer")
    s.add_argument("usuario")
    s.add_argument("cantidad", type=int)
    s.set_defaults(f=cmd_leer)
    sub.add_parser("vivos").set_defaults(f=cmd_vivos)
    s = sub.add_parser("quien")
    s.add_argument("--veces", type=int, default=3)
    s.set_defaults(f=cmd_quien)
    s = sub.add_parser("conversacion")
    s.add_argument("origen")
    s.add_argument("destino")
    s.add_argument("texto")
    s.add_argument("--esperar", type=float, default=0)
    s.add_argument("--cancelar", action="store_true")
    s.add_argument("--probar-colgante", action="store_true")
    s.set_defaults(f=cmd_conversacion)
    s = sub.add_parser("vigilar")
    s.add_argument("--cada", type=float, default=1)
    s.set_defaults(f=cmd_vigilar)
    a = p.parse_args()
    try:
        a.f(a)
    except KeyboardInterrupt:
        pass
    except NamingError as e:
        log(f"ERROR de nombres. No encuentro {NOMBRE}. {e}")
        sys.exit(2)
    except DaemonError as e:
        log(f"ERROR del daemon. La referencia apunta a un objeto que ya no existe. {e}")
        sys.exit(3)
    except SerializeError as e:
        log(f"ERROR de serialización. El servidor intentó enviar un objeto por valor. {e}")
        sys.exit(4)
    except CommunicationError as e:
        if "unknown object" in str(e):
            log("ERROR. El servidor responde, pero el objeto de esa referencia "
                f"ya no existe (referencia colgante). {e}")
            sys.exit(3)
        log(f"ERROR de comunicación. {type(e).__name__} {e}")
        sys.exit(5)
    except Exception as e:  # error del dominio que viene desde el servidor
        log(f"ERROR remoto {type(e).__name__} {e}")
        if os.environ.get("TRAZA") == "1":
            print("".join(get_pyro_traceback()))
        sys.exit(6)


if __name__ == "__main__":
    main()
