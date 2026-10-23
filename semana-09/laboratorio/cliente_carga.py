"""Cliente de carga: abre N conexiones simultáneas y mide cuánto tarda cada una.

Habla el mensaje enmarcado de la semana 9 (codec.py). El codec sale de CODEC
y tiene que coincidir con el del servidor.

Uso:
  python cliente_carga.py --clientes 5 --comando "ESPERA 2"
  python cliente_carga.py --clientes 20 --comando "LEER ana 1" --repeticiones 4
"""
import argparse
import os
import socket
import threading
import time

import codec
from mensajes import Respuesta, Solicitud

HOST = os.environ.get("SERVIDOR_HOST", "servidor")
PUERTO = int(os.environ.get("SERVIDOR_PUERTO", "5000"))


def _argumentos(linea):
    partes = linea.split()
    if not partes:
        return "", []
    op, args = partes[0], partes[1:]
    if op.upper() == "ENVIAR" and len(args) >= 3:
        args = [args[0], args[1], " ".join(args[2:])]
    return op, args


def _texto(resp):
    if resp.estado == "OK":
        return "OK " + " ".join(resp.datos)
    return "ERROR " + resp.error


def un_cliente(i, comando, repeticiones, resultados, saludo, cierre):
    inicio = time.perf_counter()
    ultima = ""
    en_fila = 0.0
    operacion = 0.0
    correlativo = 0
    try:
        with socket.create_connection((HOST, PUERTO), timeout=120) as s:
            def llamar(linea):
                nonlocal correlativo
                op, args = _argumentos(linea)
                correlativo += 1
                codec.enviar(s, Solicitud(operacion=op, argumentos=args, id=correlativo))
                return codec.recibir(s, Respuesta)

            if saludo:
                llamar(saludo.replace("{i}", str(i)))
                en_fila = time.perf_counter() - inicio
            t_op = time.perf_counter()
            for _ in range(repeticiones):
                ultima = _texto(llamar(comando))
            operacion = time.perf_counter() - t_op
            if cierre:
                llamar(cierre)
    except Exception as e:  # noqa: BLE001
        ultima = f"ERROR_CLIENTE {e.__class__.__name__}"
    resultados[i] = (time.perf_counter() - inicio, en_fila, operacion, ultima)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clientes", type=int, default=5)
    ap.add_argument("--comando", default="ESPERA 2")
    ap.add_argument("--repeticiones", type=int, default=1)
    ap.add_argument("--saludo", default="HOLA carga{i}", help="mensaje inicial ('' para omitir)")
    ap.add_argument("--cierre", default="SALIR", help="mensaje final ('' para omitir)")
    args = ap.parse_args()

    resultados = {}
    hilos = [threading.Thread(target=un_cliente, args=(i, args.comando, args.repeticiones, resultados, args.saludo, args.cierre))
             for i in range(args.clientes)]
    t0 = time.perf_counter()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    total = time.perf_counter() - t0

    print(f"servidor={HOST}:{PUERTO} codec={codec.CODEC} clientes={args.clientes} comando='{args.comando}' repeticiones={args.repeticiones}")
    print("  cliente   en fila   operacion      total   ultima respuesta")
    for i in sorted(resultados, key=lambda k: resultados[k][0]):
        dur, en_fila, operacion, ultima = resultados[i]
        print(f"  {i:7d}  {en_fila:6.2f} s  {operacion:6.2f} s  {dur:6.2f} s   {ultima}")
    print(f"TOTAL: {total:.2f} s")


if __name__ == "__main__":
    main()
