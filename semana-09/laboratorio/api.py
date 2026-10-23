"""API REST para el servicio de mensajería.

Traduce HTTP al mensaje estructurado de la semana 9. El estado sigue
viviendo en el servidor TCP. Cliente y servidor usan el mismo CODEC.
"""
import os
import socket

import codec
from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field

from mensajes import Respuesta, Solicitud

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


def pedir(operacion: str, argumentos: list[str] | None = None) -> Respuesta:
    """Envía una solicitud enmarcada al servidor TCP y devuelve la respuesta."""
    solicitud = Solicitud(operacion=operacion, argumentos=argumentos or [])
    try:
        with socket.create_connection(
            (SERVIDOR_HOST, SERVIDOR_PUERTO), timeout=TIMEOUT_SERVIDOR
        ) as conexion:
            codec.enviar(conexion, solicitud)
            return codec.recibir(conexion, Respuesta)
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
    except (ValueError, KeyError, UnicodeError) as error:
        raise HTTPException(
            502,
            {
                "error": "RESPUESTA_INVALIDA",
                "detalle": error.__class__.__name__,
                "replica": REPLICA,
            },
        )


def traducir(respuesta: Respuesta) -> list[str]:
    """Convierte la respuesta estructurada a datos o a un error HTTP."""
    if respuesta.estado == "OK":
        return respuesta.datos
    partes = respuesta.error.split()
    codigo = partes[0] if partes else "DESCONOCIDO"
    detalle = " ".join(partes[1:])
    raise HTTPException(
        ERRORES.get(codigo, 500),
        {"error": codigo, "detalle": detalle, "replica": REPLICA},
    )


def bandeja(respuesta: Respuesta) -> dict:
    """Lee BANDEJA: datos = [usuario, pendientes, mensaje, ...]."""
    if respuesta.estado != "OK":
        traducir(respuesta)
    if len(respuesta.datos) < 2:
        raise HTTPException(502, {"error": "RESPUESTA_INVALIDA", "replica": REPLICA})
    nombre, pendientes, *mensajes = respuesta.datos
    return {
        "usuario": nombre,
        "pendientes": int(pendientes),
        "mensajes": " | ".join(mensajes),
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
    return bandeja(pedir("BANDEJA", [usuario]))


@app.post("/usuarios", status_code=201)
def registrar_usuario(nuevo: UsuarioNuevo):
    nombre, pendientes = traducir(pedir("REGISTRAR", [nuevo.usuario]))
    return {"usuario": nombre, "pendientes": int(pendientes), "replica": REPLICA}


@app.post("/mensajes", status_code=201)
def enviar_mensaje(mensaje: MensajeNuevo):
    if not mensaje.texto.strip():
        raise HTTPException(422, {"error": "TEXTO_VACIO", "replica": REPLICA})
    destino, pendientes = traducir(
        pedir("ENVIAR", [mensaje.origen, mensaje.destino, mensaje.texto])
    )
    return {"destino": destino, "pendientes": int(pendientes), "replica": REPLICA}


@app.post("/usuarios/{usuario}/lecturas")
def leer_mensajes(cantidad: Lectura, usuario: str = USUARIO):
    datos = traducir(pedir("LEER", [usuario, str(cantidad.cantidad)]))
    if len(datos) < 2:
        raise HTTPException(502, {"error": "RESPUESTA_INVALIDA", "replica": REPLICA})
    nombre, pendientes, *mensajes = datos
    return {
        "usuario": nombre,
        "pendientes": int(pendientes),
        "mensajes": " | ".join(mensajes),
        "replica": REPLICA,
    }
