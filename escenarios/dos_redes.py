#!/usr/bin/env python3
"""REDES101 lab 2: dos redes unidas por un router Linux."""

from mininet.log import setLogLevel
from mininet.node import Node

try:
    from .comun import Escenario, ejecutar
except ImportError:  # ejecución directa: python3 escenarios/dos_redes.py
    from comun import Escenario, ejecutar


class Router(Node):
    """Host Linux con reenvío IPv4 dentro de su namespace."""

    def config(self, **params):
        super().config(**params)
        self.cmd("sysctl -w net.ipv4.ip_forward=1")

    def terminate(self):
        self.cmd("sysctl -w net.ipv4.ip_forward=0")
        super().terminate()


def construir(net):
    r1 = net.addHost("r1", cls=Router, ip=None)
    s1 = net.addSwitch("s1")
    s2 = net.addSwitch("s2")
    pc1 = net.addHost("pc1", ip="192.168.1.10/24",
                      mac="02:00:00:00:01:0a", defaultRoute="via 192.168.1.1")
    pc2 = net.addHost("pc2", ip="192.168.2.10/24",
                      mac="02:00:00:00:02:0a", defaultRoute="via 192.168.2.1")
    net.addLink(pc1, s1, intfName1="pc1-eth0", intfName2="s1-eth1")
    net.addLink(pc2, s2, intfName1="pc2-eth0", intfName2="s2-eth1")
    net.addLink(r1, s1, intfName1="r1-eth0", intfName2="s1-eth2",
                addr1="02:00:00:00:01:01", params1={"ip": "192.168.1.1/24"})
    net.addLink(r1, s2, intfName1="r1-eth1", intfName2="s2-eth2",
                addr1="02:00:00:00:02:01", params1={"ip": "192.168.2.1/24"})


def crear_escenario():
    return Escenario("dos_redes", construir, dos_redes=True)


if __name__ == "__main__":
    setLogLevel("info")
    ejecutar(crear_escenario())
