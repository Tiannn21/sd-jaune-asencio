"""
Dominio del servicio, sin nada de red. Semana 11.

Mensajería instantánea del equipo SD-Jaune-Asencio, las mismas reglas que
semana10/rpc.py (enviar y leer) más usuarios (lectura) y registrar, la
operación nueva del trabajo autónomo. Lo usan rpc.py y servidor_grpc.py.
"""
import threading

_lock = threading.Lock()
_estado = {
    "usuarios": {"ana": {"pendientes": 100}, "beto": {"pendientes": 100}},
    "buzon": {"ana": [], "beto": []},
}


class ErrorDominio(Exception):
    """Regla del negocio que no se cumple, por ejemplo usuario duplicado."""


class ErrorParametros(Exception):
    """Parámetros con valor inválido."""


def _usuario(valor, etiqueta):
    if not isinstance(valor, str) or not valor.strip() or any(c.isspace() for c in valor.strip()):
        raise ErrorParametros(f"{etiqueta} debe ser un texto de una sola palabra")
    return valor.strip().lower()


def usuarios():
    with _lock:
        return {nombre: datos["pendientes"] for nombre, datos in sorted(_estado["usuarios"].items())}


def enviar(origen, destino, texto):
    """Guarda el texto en el buzón del destino y suma un pendiente."""
    origen = _usuario(origen, "origen")
    destino = _usuario(destino, "destino")
    if not isinstance(texto, str) or not texto.strip():
        raise ErrorParametros("texto vacío")
    with _lock:
        if origen not in _estado["usuarios"] or destino not in _estado["usuarios"]:
            raise ErrorDominio("USUARIO_NO_EXISTE")
        _estado["usuarios"][destino]["pendientes"] += 1
        _estado["buzon"][destino].append(f"{origen}:{texto}")
        return {"destino": destino, "pendientes": _estado["usuarios"][destino]["pendientes"]}


def leer(usuario, cantidad):
    """Descuenta pendientes y retira hasta cantidad textos, en orden FIFO."""
    usuario = _usuario(usuario, "usuario")
    if type(cantidad) is not int or cantidad <= 0:
        raise ErrorParametros("cantidad debe ser un entero mayor que cero")
    with _lock:
        datos = _estado["usuarios"].get(usuario)
        if datos is None:
            raise ErrorDominio("USUARIO_NO_EXISTE")
        if datos["pendientes"] < cantidad:
            raise ErrorDominio(f"SIN_MENSAJES {datos['pendientes']}")
        datos["pendientes"] -= cantidad
        mensajes = _estado["buzon"][usuario][:cantidad]
        _estado["buzon"][usuario] = _estado["buzon"][usuario][cantidad:]
        return {"usuario": usuario, "pendientes": datos["pendientes"], "mensajes": mensajes}


def registrar(usuario):
    """Crea un usuario con 0 pendientes y buzón vacío. Falla si ya existe."""
    usuario = _usuario(usuario, "usuario")
    with _lock:
        if usuario in _estado["usuarios"]:
            raise ErrorDominio("USUARIO_EXISTE")
        _estado["usuarios"][usuario] = {"pendientes": 0}
        _estado["buzon"][usuario] = []
        return {"usuario": usuario, "pendientes": 0}
