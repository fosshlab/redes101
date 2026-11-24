#!/usr/bin/env python3
"""REDES101 lab 3: enlaces con retardo, ancho de banda y pérdida usando TCLink."""

import argparse

from mininet.link import TCLink
from mininet.log import setLogLevel

try:
    from .comun import Escenario, ejecutar
except ImportError:  # ejecución directa: python3 escenarios/rendimiento_tcp.py
    from comun import Escenario, ejecutar


def construir_topologia(bw=10, delay="10ms", loss=0):
    """Devuelve una función constructora de topología linear,2 con parámetros tc."""

    def construir(net):
        s1 = net.addSwitch("s1")
        s2 = net.addSwitch("s2")
        h1 = net.addHost("h1", ip="192.168.10.10/24", mac="02:00:00:00:0a:01")
        h2 = net.addHost("h2", ip="192.168.10.20/24", mac="02:00:00:00:0a:02")
        params_enlace = {"bw": bw, "delay": delay}
        if loss and float(loss) > 0:
            params_enlace["loss"] = float(loss)
        net.addLink(h1, s1, intfName1="h1-eth0", intfName2="s1-eth1", **params_enlace)
        net.addLink(s1, s2, intfName1="s1-eth2", intfName2="s2-eth2", **params_enlace)
        net.addLink(h2, s2, intfName1="h2-eth0", intfName2="s2-eth1", **params_enlace)

    return construir


def crear_escenario(bw=10, delay="10ms", loss=0):
    return Escenario(
        "rendimiento_tcp",
        construir_topologia(bw=bw, delay=delay, loss=loss),
        link=TCLink,
        permite_fallas=False,
    )


def main():
    parser = argparse.ArgumentParser(description="REDES101 Lab 3: latencia y rendimiento TCP con TCLink")
    parser.add_argument("--bw", type=float, default=10, help="Ancho de banda por enlace en Mb/s (defecto: 10)")
    parser.add_argument("--delay", default="10ms", help="Retardo unidireccional por enlace (defecto: 10ms)")
    parser.add_argument("--loss", type=float, default=0, help="Pérdida porcentual por enlace (defecto: 0)")
    args = parser.parse_args()
    setLogLevel("info")
    ejecutar(crear_escenario(bw=args.bw, delay=args.delay, loss=args.loss))


if __name__ == "__main__":
    main()
