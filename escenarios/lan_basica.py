#!/usr/bin/env python3
"""REDES101 lab 1: tres PC en una LAN para observar ARP e ICMP."""

from mininet.log import setLogLevel

try:
    from .comun import Escenario, ejecutar
except ImportError:  # ejecución directa: python3 escenarios/lan_basica.py
    from comun import Escenario, ejecutar


def construir(net):
    s1 = net.addSwitch("s1")
    for numero, ip in ((1, "192.168.1.10/24"), (2, "192.168.1.20/24"),
                       (3, "192.168.1.30/24")):
        pc = net.addHost("pc%d" % numero, ip=ip,
                         mac="02:00:00:00:01:%02x" % numero)
        net.addLink(pc, s1, intfName1="pc%d-eth0" % numero,
                    intfName2="s1-eth%d" % numero)


def crear_escenario():
    return Escenario("lan_basica", construir)


if __name__ == "__main__":
    setLogLevel("info")
    ejecutar(crear_escenario())
