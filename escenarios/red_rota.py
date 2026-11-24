#!/usr/bin/env python3
"""REDES101 lab 4: dos redes con tres fallas iniciales para diagnóstico forense."""

from mininet.log import setLogLevel
from mininet.node import Node

try:
    from .comun import Escenario, ejecutar
except ImportError:  # ejecución directa: python3 escenarios/red_rota.py
    from comun import Escenario, ejecutar


class RouterDeshabilitado(Node):
    """Host Linux cuyo reenvío IPv4 arranca deshabilitado a propósito."""

    def config(self, **params):
        super().config(**params)
        self.cmd("sysctl -w net.ipv4.ip_forward=0")


def construir(net):
    r1 = net.addHost("r1", cls=RouterDeshabilitado, ip=None)
    s1 = net.addSwitch("s1")
    s2 = net.addSwitch("s2")
    # Red A: 192.168.10.0/24  |  Red B: 192.168.20.0/24
    pc1 = net.addHost(
        "pc1",
        ip="192.168.10.10/24",
        mac="02:00:00:00:0a:0a",
        defaultRoute="via 192.168.10.254",
    )
    pc2 = net.addHost(
        "pc2",
        ip="192.168.20.10/24",
        mac="02:00:00:00:14:0a",
    )
    net.addLink(pc1, s1, intfName1="pc1-eth0", intfName2="s1-eth1")
    net.addLink(pc2, s2, intfName1="pc2-eth0", intfName2="s2-eth1")
    net.addLink(
        r1,
        s1,
        intfName1="r1-eth0",
        intfName2="s1-eth2",
        addr1="02:00:00:00:0a:01",
        params1={"ip": "192.168.10.1/24"},
    )
    net.addLink(
        r1,
        s2,
        intfName1="r1-eth1",
        intfName2="s2-eth2",
        addr1="02:00:00:00:14:01",
        params1={"ip": "192.168.20.1/24"},
    )


def crear_escenario():
    return Escenario("red_rota", construir, permite_fallas=False)


if __name__ == "__main__":
    setLogLevel("info")
    ejecutar(crear_escenario())
