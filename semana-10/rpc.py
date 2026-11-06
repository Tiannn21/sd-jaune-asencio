"""JSON-RPC 2.0 para la mensajería de SD-Jaune-Asencio (Semana 10).

Operaciones ENVIAR y LEER adaptadas de semana-09/laboratorio/servidor.py.
Desde semana-10/: uvicorn rpc:app --host 0.0.0.0 --port 8000
"""
import json
from fastapi import FastAPI, Request, Response

app = FastAPI(title="JSON-RPC 2.0 - mensajería SD-Jaune-Asencio")

# ---------------------------------------------------------------- dominio
# Mismos usuarios, pendientes y buzones iniciales de la semana 9.
estado = {
    "usuarios": {"ana": {"pendientes": 100}, "beto": {"pendientes": 100}},
    "buzon": {"ana": [], "beto": []},
}


def enviar(origen: str, destino: str, texto: str):
    """ENVIAR: guarda el texto en el buzón y suma un pendiente al destino."""
    if not all(isinstance(v, str) and v.strip() for v in (origen, destino, texto)):
        raise TypeError("origen, destino y texto deben ser textos no vacíos")
    origen, destino = origen.lower(), destino.lower()
    if origen not in estado["usuarios"] or destino not in estado["usuarios"]:
        raise ValueError("USUARIO_NO_EXISTE")
    estado["usuarios"][destino]["pendientes"] += 1
    estado["buzon"][destino].append(f"{origen}:{texto}")
    return {"destino": destino, "pendientes": estado["usuarios"][destino]["pendientes"]}


def leer(usuario: str, cantidad: int):
    """LEER: descuenta pendientes y retira hasta cantidad textos en orden FIFO."""
    if not isinstance(usuario, str) or not usuario.strip():
        raise TypeError("usuario debe ser un texto no vacío")
    if type(cantidad) is not int or cantidad <= 0:
        raise TypeError("cantidad debe ser un entero positivo")
    usuario = usuario.lower()
    if usuario not in estado["usuarios"]:
        raise ValueError("USUARIO_NO_EXISTE")
    datos = estado["usuarios"][usuario]
    if datos["pendientes"] < cantidad:
        raise ValueError(f"SIN_MENSAJES {datos['pendientes']}")
    datos["pendientes"] -= cantidad
    mensajes = estado["buzon"][usuario][:cantidad]
    estado["buzon"][usuario] = estado["buzon"][usuario][cantidad:]
    return {"usuario": usuario, "pendientes": datos["pendientes"], "mensajes": mensajes}


METODOS = {"enviar": enviar, "leer": leer}

# ---------------------------------------------------------------- JSON-RPC
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL = -32603
SERVER_ERROR = -32000


def error(id_, codigo, mensaje, datos=None):
    detalle = {"code": codigo, "message": mensaje}
    if datos is not None:
        detalle["data"] = datos
    return {"jsonrpc": "2.0", "error": detalle, "id": id_}


def atender(req):
    """Procesa una solicitud y devuelve None si es una notificación."""
    if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
        return error(req.get("id") if isinstance(req, dict) else None, INVALID_REQUEST, "Invalid Request")
    id_ = req.get("id")
    es_notificacion = "id" not in req
    metodo = METODOS.get(req["method"])
    if metodo is None:
        return None if es_notificacion else error(id_, METHOD_NOT_FOUND, "Method not found")
    params = req.get("params", [])
    try:
        if not isinstance(params, (list, dict)):
            raise TypeError("params debe ser una lista o un objeto")
        resultado = metodo(**params) if isinstance(params, dict) else metodo(*params)
    except TypeError as exc:
        return None if es_notificacion else error(id_, INVALID_PARAMS, "Invalid params", str(exc))
    except ValueError as exc:
        return None if es_notificacion else error(id_, SERVER_ERROR, "Error del dominio", str(exc))
    except Exception:
        return None if es_notificacion else error(id_, INTERNAL, "Internal error")
    return None if es_notificacion else {"jsonrpc": "2.0", "result": resultado, "id": id_}


@app.post("/rpc")
async def rpc(request: Request):
    cuerpo = await request.body()
    try:
        datos = json.loads(cuerpo)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error(None, PARSE_ERROR, "Parse error")
    if isinstance(datos, list):
        if not datos:
            return error(None, INVALID_REQUEST, "Invalid Request")
        respuestas = [r for r in (atender(x) for x in datos) if r is not None]
        return respuestas if respuestas else Response(status_code=204)
    respuesta = atender(datos)
    return respuesta if respuesta is not None else Response(status_code=204)
