"""Pruebas contra los contenedores reales. Ejecutar con el servidor recién iniciado."""
from uuid import uuid4
from Pyro5.api import Proxy
from Pyro5.errors import DaemonError, CommunicationError
from cliente_pyro import directorio
import dominio

def error(clase, accion):
    try:
        accion()
    except clase as exc:
        print(type(exc).__name__, str(exc), flush=True)
    else:
        raise AssertionError("Faltó el error esperado")

with directorio() as d:
    nombre = "prueba_" + uuid4().hex[:8]
    assert d.registrar(nombre) == {"usuario": nombre, "pendientes": 0}
    error(dominio.ErrorDominio, lambda: d.registrar(nombre))
    error(dominio.ErrorParametros, lambda: d.leer(nombre, 0))
    error(dominio.ErrorDominio, lambda: d.enviar("inexistente", nombre, "hola"))
    assert d.enviar("ana", nombre, "primero")["pendientes"] == 1
    assert d.enviar("beto", nombre, "segundo")["pendientes"] == 2
    assert d.leer(nombre, 2)["mensajes"] == ["ana:primero", "beto:segundo"]
    error(dominio.ErrorDominio, lambda: d.leer(nombre, 1))
    with d.abrir_conversacion("ana", nombre) as c:
        assert isinstance(c, Proxy)
        print("REFERENCIA", c._pyroUri, flush=True)
        c.agregar("borrador")
        copia = c.ver()
        copia["texto"] = "copia modificada"
        assert c.ver()["texto"] == "borrador"
        assert d.usuarios()[nombre] == 0
        assert c.confirmar()["pendientes"] == 1
        error((DaemonError, CommunicationError), c.ver)
    assert d.leer(nombre, 1)["mensajes"] == ["ana:borrador"]
    with d.abrir_conversacion("ana", nombre) as c:
        c.agregar("no enviar")
        assert c.cancelar() == "cancelada"
        error((DaemonError, CommunicationError), c.ver)
    assert d.usuarios()[nombre] == 0
    with d.abrir_conversacion("ana", nombre) as c:
        error(dominio.ErrorParametros, c.confirmar)
        assert d.conversaciones_vivas() == 1
        c.cancelar()
    assert d.conversaciones_vivas() == 0
print("OK: registro, errores, FIFO, copia, referencia, confirmar, cancelar y limpieza", flush=True)

