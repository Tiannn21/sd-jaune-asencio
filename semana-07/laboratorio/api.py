"""API REST para el servicio de mensajería de la Semana 6.

La API traduce solicitudes HTTP a líneas del protocolo TCP. El estado sigue
viviendo en el servidor, así que api1 y api2 comparten usuarios y mensajes.
"""
import os
import re
import socket

from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field

SERVIDOR_HOST = os.environ.get("SERVIDOR_HOST", "servidor")
SERVIDOR_PUERTO = int(os.environ.get("SERVIDOR_PUERTO", "5000"))
TIMEOUT_SERVIDOR = float(os.environ.get("TIMEOUT_SERVIDOR", "3"))
REPLICA = os.environ.get("REPLICA", socket.gethostname())

app = FastAPI(
    title="API de mensajería",
    version="1.0",
    description="Puerta HTTP del servicio TCP de mensajería de SD-Jaune-Asencio.",
)

USUARIO = Path(pattern=r"^[a-zA-Z0-9_]{1,30}$", description="nombre de usuario")
ERRORES = {
    "USUARIO_NO_EXISTE": 404,
    "USUARIO_EXISTE": 409,
    "SIN_MENSAJES": 409,
    "FORMATO": 400,
    "COMANDO_DESCONOCIDO": 501,
}


class UsuarioNuevo(BaseModel):
    usuario: str = Field(pattern=r"^[a-zA-Z0-9_]{1,30}$")


class MensajeNuevo(BaseModel):
    origen: str = Field(pattern=r"^[a-zA-Z0-9_]{1,30}$")
    destino: str = Field(pattern=r"^[a-zA-Z0-9_]{1,30}$")
    texto: str = Field(min_length=1)


class Lectura(BaseModel):
    cantidad: int = Field(gt=0)


def pedir(linea: str) -> str:
    """Envía una operación al servidor TCP y devuelve su respuesta."""
    try:
        with socket.create_connection(
            (SERVIDOR_HOST, SERVIDOR_PUERTO), timeout=TIMEOUT_SERVIDOR
        ) as conexion:
            conexion.sendall((linea + "\n").encode("utf-8"))
            respuesta = conexion.makefile("r", encoding="utf-8").readline().strip()
    except socket.timeout:
        raise HTTPException(
            504, {"error": "SERVIDOR_NO_RESPONDE", "replica": REPLICA}
        )
    except OSError as error:
        raise HTTPException(
            503,
            {
                "error": "SERVIDOR_NO_DISPONIBLE",
                "detalle": error.__class__.__name__,
                "replica": REPLICA,
            },
        )
    if not respuesta:
        raise HTTPException(
            503, {"error": "SERVIDOR_CERRO_LA_CONEXION", "replica": REPLICA}
        )
    return respuesta


def traducir(respuesta: str) -> list[str]:
    """Convierte las respuestas del protocolo de texto a datos o errores HTTP."""
    partes = respuesta.split()
    if partes and partes[0] == "OK":
        return partes[1:]
    codigo = partes[1] if len(partes) > 1 else "DESCONOCIDO"
    detalle = " ".join(partes[2:])
    raise HTTPException(
        ERRORES.get(codigo, 500),
        {"error": codigo, "detalle": detalle, "replica": REPLICA},
    )


def bandeja(respuesta: str) -> dict:
    """Lee la respuesta BANDEJA conservando el texto de los mensajes."""
    if not respuesta.startswith("OK "):
        traducir(respuesta)
    coincidencia = re.fullmatch(
        r"OK ([^ ]+) pendientes:(\d+)(?: (.*))?", respuesta
    )
    if coincidencia is None:
        raise HTTPException(502, {"error": "RESPUESTA_INVALIDA", "replica": REPLICA})
    nombre, pendientes, mensajes = coincidencia.groups()
    return {
        "usuario": nombre,
        "pendientes": int(pendientes),
        "mensajes": mensajes or "",
        "replica": REPLICA,
    }


@app.get("/salud")
def salud():
    return {"estado": "ok", "replica": REPLICA}


@app.get("/usuarios")
def listar_usuarios():
    usuarios = {}
    for par in traducir(pedir("USUARIOS")):
        nombre, pendientes = par.split(":", 1)
        usuarios[nombre] = int(pendientes)
    return {"usuarios": usuarios, "replica": REPLICA}


@app.get("/usuarios/{usuario}/bandeja")
def ver_bandeja(usuario: str = USUARIO):
    return bandeja(pedir(f"BANDEJA {usuario}"))


@app.post("/usuarios", status_code=201)
def registrar_usuario(nuevo: UsuarioNuevo):
    nombre, pendientes = traducir(pedir(f"REGISTRAR {nuevo.usuario}"))
    return {"usuario": nombre, "pendientes": int(pendientes), "replica": REPLICA}


@app.post("/mensajes", status_code=201)
def enviar_mensaje(mensaje: MensajeNuevo):
    if not mensaje.texto.strip():
        raise HTTPException(422, {"error": "TEXTO_VACIO", "replica": REPLICA})
    destino, pendientes = traducir(
        pedir(f"ENVIAR {mensaje.origen} {mensaje.destino} {mensaje.texto}")
    )
    return {"destino": destino, "pendientes": int(pendientes), "replica": REPLICA}


@app.post("/usuarios/{usuario}/lecturas")
def leer_mensajes(cantidad: Lectura, usuario: str = USUARIO):
    respuesta = pedir(f"LEER {usuario} {cantidad.cantidad}")
    partes = traducir(respuesta)
    if len(partes) < 2:
        raise HTTPException(502, {"error": "RESPUESTA_INVALIDA", "replica": REPLICA})
    mensajes = respuesta.split(" ", 3)[3] if len(respuesta.split(" ", 3)) == 4 else ""
    return {
        "usuario": partes[0],
        "pendientes": int(partes[1]),
        "mensajes": mensajes,
        "replica": REPLICA,
    }
