"""Ciclo de vida, fallas y capturas de los escenarios REDES101."""

from pathlib import Path
from shutil import which
from signal import SIGHUP, SIGINT, SIGTERM, signal
from subprocess import DEVNULL, TimeoutExpired
from time import monotonic, sleep

from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import OVSBridge


class Escenario:
    """Una sesión Mininet con reinicio completo y capturas por cada puerto."""

    def __init__(self, nombre, construir, dos_redes=False):
        self.nombre = nombre
        self.construir = construir
        self.dos_redes = dos_redes
        self.net = None
        self.capturas = []
        self.falla_activa = None

    def start(self):
        if self.net is not None:
            return self.net
        # Bridges OVS sin controlador: aprenden MAC como un switch común.
        net = Mininet(controller=None, switch=OVSBridge, build=False)
        try:
            self.construir(net)
            net.build()
            net.start()
        except BaseException:
            net.stop()
            raise
        self.net = net
        self.falla_activa = None
        return net

    def stop(self):
        self.detener_captura()
        if self.net is not None:
            net, self.net = self.net, None
            net.stop()
        self.falla_activa = None

    def reset(self):
        """Recrear hosts y OVS; recupera IP, rutas, ARP y aprendizaje MAC."""
        self.stop()
        return self.start()

    def falla(self, nombre):
        if self.net is None:
            raise RuntimeError("Primero iniciá el escenario")
        if self.falla_activa:
            raise RuntimeError("Restaurá o reiniciá antes de aplicar otra falla")
        pc2 = self.net.get("pc2")
        if nombre == "sin_gateway" and not self.dos_redes:
            raise ValueError("sin_gateway solo existe en dos_redes: esta LAN no usa puerta de enlace")
        if nombre == "sin_gateway":
            self.net.get("pc1").cmd("ip route del default")
        elif nombre == "interfaz_down":
            nodo, interfaz = (self.net.get("r1"), "r1-eth1") if self.dos_redes else (pc2, "pc2-eth0")
            nodo.cmd("ip link set dev %s down" % interfaz)
        elif nombre == "ip_fuera_de_red":
            pc2.cmd("ip addr flush dev pc2-eth0")
            ip = "192.168.1.20/24" if self.dos_redes else "192.168.2.20/24"
            pc2.cmd("ip addr add %s dev pc2-eth0" % ip)
        else:
            raise ValueError("Falla no disponible: %s" % nombre)
        self.falla_activa = nombre

    def restaurar(self):
        """Restaurar la configuración y el estado inicial del switch."""
        return self.reset()

    def capturar(self, directorio):
        """Abrir un PCAP por extremo de cada enlace, sin filtrar protocolos."""
        if self.net is None:
            raise RuntimeError("Primero iniciá el escenario")
        if self.capturas:
            raise RuntimeError("Ya hay una captura activa; usá detener_captura")
        if which("tcpdump") is None:
            raise RuntimeError("Falta tcpdump en la VM")
        destino = Path(directorio).expanduser().resolve()
        destino.mkdir(parents=True, exist_ok=True)
        try:
            for numero, enlace in enumerate(self.net.links, 1):
                for interfaz in (enlace.intf1, enlace.intf2):
                    archivo = destino / ("%02d_%s.pcap" % (numero, interfaz.name))
                    # Un log por proceso: si compartieran archivo, las líneas se mezclan.
                    with archivo.with_suffix(".log").open("wb") as registro:
                        # OVSBridge corre en el namespace raíz; Node.popen lo respeta.
                        proceso = interfaz.node.popen(
                            ["tcpdump", "--immediate-mode", "-Z", "root", "-i", interfaz.name,
                             "-U", "-s", "0", "-w", str(archivo)],
                            stdout=DEVNULL, stderr=registro,
                        )
                    self.capturas.append((proceso, archivo))
            self._esperar_tcpdump()
        except BaseException:
            self.detener_captura()
            raise
        return [archivo for _, archivo in self.capturas]

    def _esperar_tcpdump(self, limite=10):
        """No volver hasta que cada tcpdump abrió su interfaz."""
        fin = monotonic() + limite
        while True:
            faltan = [archivo for _, archivo in self.capturas
                      if b"listening on" not in archivo.with_suffix(".log").read_bytes()]
            if not faltan:
                return
            muertos = [a for p, a in self.capturas if p.poll() is not None]
            if muertos or monotonic() > fin:
                raise RuntimeError("tcpdump no arrancó; revisá %s"
                                   % ", ".join(str(a.with_suffix(".log")) for a in muertos or faltan))
            sleep(0.05)

    def detener_captura(self):
        archivos = [archivo for _, archivo in self.capturas]
        for proceso, _ in self.capturas:
            if proceso.poll() is None:
                proceso.send_signal(SIGINT)
                try:
                    proceso.wait(timeout=3)
                except TimeoutExpired:
                    proceso.kill()
                    proceso.wait()
        self.capturas.clear()
        return archivos


class Consola(CLI):
    """Consola Mininet con fallas y captura para los laboratorios."""

    prompt = "minired> "

    def __init__(self, escenario):
        self.escenario = escenario
        super().__init__(escenario.net)

    def _sincronizar(self):
        self.mn = self.escenario.net
        self.locals = {"net": self.mn}

    def do_falla(self, linea):
        "falla NOMBRE: sin_gateway (solo dos_redes), interfaz_down, ip_fuera_de_red"
        try:
            self.escenario.falla(linea.strip())
            print("Falla aplicada:", linea.strip())
        except (ValueError, RuntimeError) as error:
            print(error)

    def do_restaurar(self, linea):
        "restaurar: reconstruir el escenario y quitar la falla"
        self.escenario.restaurar()
        self._sincronizar()
        print("Escenario restaurado")

    def do_reset(self, linea):
        "reset: reiniciar toda la topología y vaciar su estado"
        self.escenario.reset()
        self._sincronizar()
        print("Escenario reiniciado")

    def do_capturar(self, linea):
        "capturar DIRECTORIO: guardar todos los puertos en archivos PCAP"
        try:
            archivos = self.escenario.capturar(linea.strip() or "/tmp/minired-pcaps")
            print("Capturando %d puertos; usá detener_captura antes de abrir los PCAP" % len(archivos))
            for archivo in archivos:
                print(archivo)
        except (OSError, RuntimeError) as error:
            print(error)

    def do_detener_captura(self, linea):
        "detener_captura: cerrar todos los archivos PCAP"
        archivos = self.escenario.detener_captura()
        print("Capturas cerradas:", len(archivos))

    def do_stop(self, linea):
        "stop: salir; el programa detiene la red y libera los recursos"
        return True


def _terminar(numero, _marco):
    raise SystemExit(128 + numero)


def ejecutar(escenario):
    """start automático, consola interactiva, stop garantizado al salir."""
    # Cerrar la terminal o un kill también deben limpiar puentes y veth.
    signal(SIGTERM, _terminar)
    signal(SIGHUP, _terminar)
    escenario.start()
    try:
        print("Red lista. Comandos extra: falla, restaurar, reset, capturar, detener_captura, stop")
        Consola(escenario)
    finally:
        escenario.stop()
