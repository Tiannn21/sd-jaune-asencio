"""
Cliente gRPC del servicio, semana 11.

Uso
  python cliente_grpc.py usuarios
  python cliente_grpc.py enviar ana beto hola semana 11
  python cliente_grpc.py leer beto 1 --reintentos 2
  python cliente_grpc.py registrar carol

Variables
  SERVIDOR_HOST    (servidor)   SERVIDOR_PUERTO (50051)
  TIMEOUT_CLIENTE  (2)          deadline de cada intento, en segundos
  REINTENTOS       (0)          intentos extra ante DEADLINE_EXCEEDED o UNAVAILABLE

Cada reintento manda el MISMO id_solicitud.
"""
import argparse
import os
import uuid

import grpc

import servicio_pb2 as pb
import servicio_pb2_grpc as pb_grpc

HOST = os.getenv("SERVIDOR_HOST", "servidor")
PUERTO = os.getenv("SERVIDOR_PUERTO", "50051")
REINTENTABLES = {grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.UNAVAILABLE}


def _solicitud(metodo, resto):
    ids = uuid.uuid4().hex[:8]
    if metodo == "usuarios":
        if resto:
            raise SystemExit("usuarios no lleva argumentos")
        return pb.UsuariosSolicitud()
    if metodo == "registrar":
        usuario = resto[0] if resto else ""
        return pb.RegistrarSolicitud(id_solicitud=ids, usuario=usuario)
    if metodo == "leer":
        usuario = resto[0] if resto else ""
        try:
            cantidad = int(resto[1]) if len(resto) > 1 else 0
        except ValueError:
            raise SystemExit("cantidad debe ser un entero")
        return pb.LeerSolicitud(id_solicitud=ids, usuario=usuario, cantidad=cantidad)
    origen = resto[0] if resto else ""
    destino = resto[1] if len(resto) > 1 else ""
    texto = " ".join(resto[2:]) if len(resto) > 2 else ""
    return pb.EnviarSolicitud(id_solicitud=ids, origen=origen, destino=destino, texto=texto)


def _mostrar(metodo, resp):
    if metodo == "usuarios":
        texto = ", ".join(f"{u.nombre}={u.pendientes}" for u in resp.usuarios) or "(vacío)"
        print("[cliente]   " + texto)
    elif metodo == "leer":
        msgs = ", ".join(resp.mensajes) or "(sin textos)"
        print(f"[cliente]   OK {resp.usuario} pendientes={resp.pendientes} mensajes={msgs}")
    elif metodo == "registrar":
        print(f"[cliente]   OK {resp.usuario} pendientes={resp.pendientes}")
    else:
        print(f"[cliente]   OK {resp.destino} pendientes={resp.pendientes}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("metodo", choices=["usuarios", "enviar", "leer", "registrar"])
    ap.add_argument("resto", nargs="*")
    ap.add_argument("--reintentos", type=int, default=int(os.getenv("REINTENTOS", "0")))
    ap.add_argument("--timeout", type=float, default=float(os.getenv("TIMEOUT_CLIENTE", "2")))
    a = ap.parse_args()

    canal = grpc.insecure_channel(f"{HOST}:{PUERTO}")
    stub = pb_grpc.MensajeriaStub(canal)        # el stub, generado desde el .proto
    llamadas = {
        "usuarios": stub.Usuarios,
        "enviar": stub.Enviar,
        "leer": stub.Leer,
        "registrar": stub.Registrar,
    }
    solicitud = _solicitud(a.metodo, a.resto)
    llamada = llamadas[a.metodo]

    for intento in range(1, a.reintentos + 2):
        ids = getattr(solicitud, "id_solicitud", "-")
        print(f"[cliente] intento {intento}, id_solicitud={ids}, deadline {a.timeout:.0f} s")
        try:
            resp = llamada(solicitud, timeout=a.timeout)
        except grpc.RpcError as e:
            print(f"[cliente]   {e.code().name}, {e.details()}")
            if e.code() in REINTENTABLES:
                continue
            return 1
        _mostrar(a.metodo, resp)
        return 0
    if a.metodo == "usuarios":
        print("[cliente] me rendí, sin respuesta del servidor")
    else:
        print("[cliente] me rendí, la operación quedó en estado DESCONOCIDO")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
