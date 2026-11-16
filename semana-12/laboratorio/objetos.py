"""Objetos remotos del chat; las reglas permanecen en dominio.py."""
import os
import threading
from Pyro5.api import behavior, expose
import dominio

MODO = os.environ.get("MODO", "single")
POR_VALOR = os.environ.get("POR_VALOR", "0") == "1"
_numero = 0
_lock = threading.Lock()


@expose
class Conversacion:
    """Borrador remoto entre dos usuarios; termina al confirmar o cancelar."""
    def __init__(self, origen, destino):
        self.origen, self.destino = origen, destino
        self.texto = ""
        self._cerrada = False
        self._lock = threading.RLock()

    def __getstate__(self):
        # El experimento por valor debe serializar datos, nunca el lock local.
        return {"origen": self.origen, "destino": self.destino, "texto": self.texto}

    def _activa(self):
        if self._cerrada:
            raise dominio.ErrorDominio("CONVERSACION_CERRADA")

    def agregar(self, texto):
        """Cambia el borrador sin enviar; reemplaza el texto anterior."""
        with self._lock:
            self._activa()
            if not isinstance(texto, str) or not texto.strip():
                raise dominio.ErrorParametros("texto vacío")
            self.texto = texto
            return self.ver()

    def ver(self):
        """Consulta una copia de participantes y borrador; no cambia estado."""
        with self._lock:
            self._activa()
            return {"participantes": [self.origen, self.destino], "texto": self.texto}

    def confirmar(self):
        """Cambia el buzón con un envío y desregistra esta conversación."""
        with self._lock:
            self._activa()
            resultado = dominio.enviar(self.origen, self.destino, self.texto)
            self._terminar()
            return resultado

    def cancelar(self):
        """Cambia el ciclo de vida: desregistra sin enviar."""
        with self._lock:
            self._activa()
            self._terminar()
            return "cancelada"

    def _terminar(self):
        self._cerrada = True
        self._pyroDaemon.unregister(self)


@expose
@behavior(instance_mode=MODO)
class Directorio:
    """Entrada al chat: operaciones del dominio y fábrica de conversaciones."""
    def __init__(self):
        global _numero
        with _lock:
            _numero += 1
            self.numero = _numero
        self.llamadas = 0
        self._lock = threading.Lock()

    def _contar(self):
        with self._lock:
            self.llamadas += 1
            return self.llamadas

    def usuarios(self):
        """Consulta usuarios; solo cambia el contador de telemetría."""
        self._contar()
        return dominio.usuarios()

    def registrar(self, usuario):
        """Cambia estado: crea un usuario con cero pendientes."""
        self._contar()
        return dominio.registrar(usuario)

    def enviar(self, origen, destino, texto):
        """Cambia estado: añade un mensaje y un pendiente al destino."""
        self._contar()
        return dominio.enviar(origen, destino, texto)

    def leer(self, usuario, cantidad):
        """Cambia estado: retira textos FIFO y descuenta pendientes."""
        self._contar()
        return dominio.leer(usuario, cantidad)

    def quien_soy(self):
        """Consulta identidad y cambia únicamente el contador de llamadas."""
        return {"modo": MODO, "instancia": self.numero, "llamadas": self._contar()}

    def conversaciones_vivas(self):
        """Consulta objetos vivos; solo cambia el contador de telemetría."""
        self._contar()
        return sum(isinstance(o, Conversacion) for o in list(self._pyroDaemon.objectsById.values()))

    def abrir_conversacion(self, origen, destino):
        """Cambia estado: crea un borrador devuelto por referencia."""
        self._contar()
        origen = dominio._usuario(origen, "origen")
        destino = dominio._usuario(destino, "destino")
        usuarios = dominio.usuarios()
        if origen not in usuarios or destino not in usuarios:
            raise dominio.ErrorDominio("USUARIO_NO_EXISTE")
        conversacion = Conversacion(origen, destino)
        if not POR_VALOR:
            self._pyroDaemon.register(conversacion)
        return conversacion
