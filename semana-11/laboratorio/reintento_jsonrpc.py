"""Envía dos veces la misma solicitud JSON-RPC 'enviar' (con el mismo id) y muestra el resultado.

Simula un cliente que no recibió la primera respuesta y reintenta con una
solicitud idéntica. Se ejecuta dentro del contenedor cliente, con rpc.py
servido en servidor:8000.
"""
import json
import urllib.request

URL = "http://servidor:8000/rpc"


def call(body):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


envio = {"jsonrpc": "2.0", "id": 1, "method": "enviar",
         "params": {"origen": "ana", "destino": "beto", "texto": "hola"}}

print("usuarios antes   ", call({"jsonrpc": "2.0", "id": 0, "method": "usuarios"})["result"])
print("intento 1, id=1  ", call(envio)["result"])
print("intento 2, id=1  ", call(envio)["result"])
print("usuarios despues ", call({"jsonrpc": "2.0", "id": 0, "method": "usuarios"})["result"])
print("leer beto 2      ", call({"jsonrpc": "2.0", "id": 2, "method": "leer",
                                 "params": {"usuario": "beto", "cantidad": 2}})["result"])
