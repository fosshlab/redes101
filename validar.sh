#!/usr/bin/env bash
# Comprueba con root que los cuatro laboratorios de REDES101 funcionan en esta VM.
# Uso: sudo bash validar.sh   (los PCAP quedan en MINIRED_PCAP_DIR o en /tmp)
set -euo pipefail

cd "$(dirname "$0")"
if [ "$(id -u)" -ne 0 ]; then
    echo "Ejecutar con root dentro de la VM: sudo bash validar.sh" >&2
    exit 1
fi
for programa in ovs-vsctl ovs-appctl ip ping tcpdump tshark iperf traceroute; do
    if ! command -v "$programa" >/dev/null 2>&1; then
        echo "Falta $programa en la VM" >&2
        exit 1
    fi
done
export MINIRED_PCAP_DIR="${MINIRED_PCAP_DIR:-/tmp/minired-validacion-$$}"
mkdir -p "$MINIRED_PCAP_DIR"

python3 - <<'PY'
import json
import os
import re
import subprocess
from pathlib import Path

from escenarios.dos_redes import crear_escenario as router
from escenarios.lan_basica import crear_escenario as lan
from escenarios.red_rota import crear_escenario as broken
from escenarios.rendimiento_tcp import crear_escenario as perf

pcaps = Path(os.environ["MINIRED_PCAP_DIR"])


def verificar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)
    print("OK:", mensaje)


def nodo(n, *orden):
    proceso = n.popen(list(orden), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    salida, error = proceso.communicate(timeout=20)
    return proceso.returncode, salida.decode(errors="replace"), error.decode(errors="replace")


def ip_json(n, *orden):
    rc, salida, error = nodo(n, "ip", "-j", *orden)
    if rc != 0:
        raise AssertionError("ip -j %s: %s" % (" ".join(orden), error.strip()))
    return json.loads(salida)


def responde(n, destino):
    return nodo(n, "ping", "-c", "2", "-W", "2", destino)[0] == 0


def tramas(archivo, filtro, campo="frame.number"):
    proceso = subprocess.run(
        ["tshark", "-r", str(archivo), "-Y", filtro, "-T", "fields", "-e", campo],
        capture_output=True, text=True, timeout=20, check=True,
    )
    return [x for x in proceso.stdout.splitlines() if x.strip()]


def captura(escenario, subdir, cantidad):
    archivos = escenario.capturar(pcaps / subdir)
    verificar(len(archivos) == cantidad and all(p.poll() is None for p, _ in escenario.capturas),
              "%s: tcpdump escuchando en los %d extremos de enlace" % (subdir, cantidad))
    return archivos


def cerrar_captura(escenario, archivos, subdir):
    escenario.detener_captura()
    verificar(all(a.is_file() and a.stat().st_size > 24 for a in archivos),
              "%s: PCAP cerrados y con tramas" % subdir)


def direccion(n, interfaz, ip, mac):
    enlace = ip_json(n, "link", "show", interfaz)[0]
    direcciones = ip_json(n, "addr", "show", interfaz)[0]["addr_info"]
    verificar(enlace["address"].lower() == mac and any(x.get("local") == ip for x in direcciones),
              "%s tiene %s y %s" % (interfaz, ip, mac))


def rutas(n):
    return ip_json(n, "route", "show")


esc = lan()
try:
    red = esc.start()
    verificar(len(red.links) == 3 and not red.controllers, "lab 1: tres enlaces, switch sin controlador")
    direccion(red.get("pc1"), "pc1-eth0", "192.168.1.10", "02:00:00:00:01:01")
    direccion(red.get("pc2"), "pc2-eth0", "192.168.1.20", "02:00:00:00:01:02")
    direccion(red.get("pc3"), "pc3-eth0", "192.168.1.30", "02:00:00:00:01:03")
    archivos = captura(esc, "lan", 6)
    verificar(responde(red.get("pc1"), "192.168.1.20"), "lab 1: PC1 llega a PC2")
    cerrar_captura(esc, archivos, "lan")
    arp = "arp.opcode == 1 && arp.src.proto_ipv4 == 192.168.1.10"
    icmp = "icmp.type == 8 && ip.src == 192.168.1.10 && ip.dst == 192.168.1.20"
    verificar(tramas(pcaps / "lan/02_s1-eth2.pcap", arp) and tramas(pcaps / "lan/03_s1-eth3.pcap", arp)
              and tramas(pcaps / "lan/02_s1-eth2.pcap", icmp) and not tramas(pcaps / "lan/03_s1-eth3.pcap", icmp),
              "lab 1: las capturas de s1-eth2 y s1-eth3 coinciden con la guía")
    fdb = subprocess.run(["ovs-appctl", "fdb/show", "s1"], capture_output=True, text=True, check=True).stdout
    verificar(all(m in fdb.lower() for m in ("02:00:00:00:01:01", "02:00:00:00:01:02")),
              "lab 1: la FDB de s1 coincide con la guía")
    verificar(any(x.get("dst") == "192.168.1.20" for x in ip_json(red.get("pc1"), "neigh", "show")),
              "lab 1: la tabla de vecinos de PC1 coincide con la guía")

    esc.falla("interfaz_down")
    verificar(not responde(esc.net.get("pc1"), "192.168.1.20"), "lab 1: falla interfaz_down aplicada")
    esc.restaurar()
    verificar(responde(esc.net.get("pc1"), "192.168.1.20"), "lab 1: restaurar recupera la red")
    esc.falla("ip_fuera_de_red")
    verificar(not responde(esc.net.get("pc1"), "192.168.1.20"), "lab 1: falla ip_fuera_de_red aplicada")
    esc.reset()
    direccion(esc.net.get("pc2"), "pc2-eth0", "192.168.1.20", "02:00:00:00:01:02")
    verificar(not ip_json(esc.net.get("pc1"), "neigh", "show"), "lab 1: reset vacía la tabla de vecinos")
finally:
    esc.stop()

esc = router()
try:
    red = esc.start()
    verificar(len(red.links) == 4 and not red.controllers, "lab 2: cuatro enlaces, switches sin controlador")
    direccion(red.get("pc1"), "pc1-eth0", "192.168.1.10", "02:00:00:00:01:0a")
    direccion(red.get("pc2"), "pc2-eth0", "192.168.2.10", "02:00:00:00:02:0a")
    direccion(red.get("r1"), "r1-eth0", "192.168.1.1", "02:00:00:00:01:01")
    direccion(red.get("r1"), "r1-eth1", "192.168.2.1", "02:00:00:00:02:01")
    tabla = rutas(red.get("r1"))
    verificar(all(any(x.get("dst") == prefijo and x.get("dev") == interfaz and "gateway" not in x for x in tabla)
                  for prefijo, interfaz in (("192.168.1.0/24", "r1-eth0"), ("192.168.2.0/24", "r1-eth1"))),
              "lab 2: la tabla de rutas de r1 coincide con la guía")
    verificar(any(x.get("dst") == "default" and x.get("gateway") == "192.168.1.1" for x in rutas(red.get("pc1"))),
              "lab 2: PC1 usa 192.168.1.1 como puerta de enlace")
    rc, salida, _ = nodo(red.get("r1"), "sysctl", "-n", "net.ipv4.ip_forward")
    verificar(rc == 0 and salida.strip() == "1", "lab 2: r1 reenvía IPv4")
    archivos = captura(esc, "router", 8)
    verificar(responde(red.get("pc1"), "192.168.2.10"), "lab 2: PC1 llega a PC2 a través de r1")
    cerrar_captura(esc, archivos, "router")
    eco = "icmp.type == 8 && ip.src == 192.168.1.10 && ip.dst == 192.168.2.10"
    verificar("64" in tramas(pcaps / "router/03_r1-eth0.pcap", eco, "ip.ttl")
              and "63" in tramas(pcaps / "router/04_r1-eth1.pcap", eco, "ip.ttl"),
              "lab 2: el TTL de las capturas de r1 coincide con la guía")

    esc.falla("sin_gateway")
    pc1 = esc.net.get("pc1")
    verificar(responde(pc1, "192.168.1.1") and not responde(pc1, "192.168.2.10"),
              "lab 2: falla sin_gateway aplicada")
    esc.restaurar()
    verificar(responde(esc.net.get("pc1"), "192.168.2.10"), "lab 2: restaurar recupera la red")

    esc.falla("interfaz_down")
    verificar(not any(x.get("dev") == "r1-eth1" for x in rutas(esc.net.get("r1")))
              and not responde(esc.net.get("pc1"), "192.168.2.10"),
              "lab 2: falla interfaz_down aplicada")
    esc.restaurar()
    verificar(responde(esc.net.get("pc1"), "192.168.2.10"), "lab 2: restaurar recupera la red")

    esc.falla("ip_fuera_de_red")
    verificar(not responde(esc.net.get("pc1"), "192.168.2.10"), "lab 2: falla ip_fuera_de_red aplicada")
    esc.restaurar()
    direccion(esc.net.get("pc2"), "pc2-eth0", "192.168.2.10", "02:00:00:00:02:0a")
finally:
    esc.stop()

esc = perf(bw=10, delay="10ms")
try:
    red = esc.start()
    verificar(len(red.links) == 3, "lab 3: tres enlaces TCLink en serie")
    h1, h2 = red.get("h1"), red.get("h2")
    direccion(h1, "h1-eth0", "192.168.10.10", "02:00:00:00:0a:01")
    direccion(h2, "h2-eth0", "192.168.10.20", "02:00:00:00:0a:02")
    rc, ping_out, _ = nodo(h1, "ping", "-c", "4", "-W", "2", "192.168.10.20")
    verificar(rc == 0, "lab 3: h1 llega a h2 sobre enlaces tc")
    rtts = [float(m.group(1)) for m in re.finditer(r"icmp_seq=(?:[234]) .*?time=([0-9.]+)", ping_out)]
    verificar(len(rtts) == 3 and all(55.0 <= t <= 85.0 for t in rtts),
              f"lab 3: RTT estable en [55, 85] ms para 3x10ms ida+vuelta ({rtts})")
    archivos = captura(esc, "perf", 6)
    srv = h2.popen(["iperf", "-s"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        rc_c, out_c, _ = nodo(h1, "iperf", "-c", "192.168.10.20", "-t", "2")
        verificar(rc_c == 0 and "Mbits/sec" in out_c, "lab 3: iperf TCP completo sobre enlaces de 10 Mb/s")
    finally:
        srv.terminate()
        srv.wait(timeout=5)
    cerrar_captura(esc, archivos, "perf")
    verificar(bool(tramas(pcaps / "perf/01_h1-eth0.pcap", "tcp.flags.syn == 1")),
              "lab 3: PCAP de h1 captura handshake SYN/SYN-ACK TCP")
finally:
    esc.stop()

esc = broken()
try:
    red = esc.start()
    verificar(len(red.links) == 4, "lab 4: cuatro enlaces iniciados en red_rota")
    pc1, pc2 = red.get("pc1"), red.get("pc2")
    direccion(pc1, "pc1-eth0", "192.168.10.10", "02:00:00:00:0a:0a")
    direccion(pc2, "pc2-eth0", "192.168.20.10", "02:00:00:00:14:0a")
    verificar(not responde(pc1, "192.168.20.10"), "lab 4: red_rota inicia aislada entre subredes como se diseñó")
finally:
    esc.stop()

print("OK: los cuatro laboratorios funcionan en esta VM. PCAP en", pcaps)
PY
