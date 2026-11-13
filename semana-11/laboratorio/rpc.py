"""
JSON-RPC 2.0 sobre FastAPI, semana 11.

Es el rpc.py de la semana 10 después del paso 1 del laboratorio. Las
funciones del dominio se fueron a dominio.py y este archivo solo traduce
entre JSON-RPC y el dominio. servidor_grpc.py hace lo mismo para gRPC.

Correr con  uvicorn rpc:app --host 0.0.0.0 --port 8000
"""
import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

import dominio

app = FastAPI()
METODOS = {
    "usuarios": dominio.usuarios,
    "enviar": dominio.enviar,
    "leer": dominio.leer,
    "registrar": dominio.registrar,
}


def error(code, message, id_, data=None):
    e = {"code": code, "message": message}
    if data is not None:
        e["data"] = data
    return {"jsonrpc": "2.0", "error": e, "id": id_}


def atender(req):
    if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or "method" not in req:
        return error(-32600, "Invalid Request", None)
    id_, params = req.get("id"), req.get("params", {})
    if req["method"] not in METODOS:
        return error(-32601, "Method not found", id_)
    try:
        f = METODOS[req["method"]]
        r = f(*params) if isinstance(params, list) else f(**params)
    except (TypeError, dominio.ErrorParametros) as e:
        return error(-32602, "Invalid params", id_, str(e))
    except dominio.ErrorDominio as e:
        return error(-32000, "Error del dominio", id_, str(e))
    return {"jsonrpc": "2.0", "result": r, "id": id_}


@app.post("/rpc")
async def rpc(request: Request):
    try:
        req = json.loads(await request.body())
    except ValueError:
        return JSONResponse(error(-32700, "Parse error", None))
    if isinstance(req, list):
        resps = [r for r in map(atender, req) if r.get("id") is not None]
        return JSONResponse(resps) if resps else Response(status_code=204)
    resp = atender(req)
    if isinstance(req, dict) and "id" not in req:
        return Response(status_code=204)
    return JSONResponse(resp)
