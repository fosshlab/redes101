# REDES101: laboratorios de redes de datos

Laboratorios del curso **REDES101: Introducción a Redes de Datos** de
**IPTA — Instituto Politécnico de Tecnologías Abiertas** / FOSSHLab
([campus.fosshlab.org](https://campus.fosshlab.org)).

Las redes se emulan con [Mininet](https://github.com/mininet/mininet) y Open vSwitch:
los hosts, switches y routers son procesos y namespaces reales del kernel de Linux,
así que las tramas que capturás con tcpdump o Wireshark son paquetes de verdad.

| Laboratorio | Qué se observa | Guía |
|---|---|---|
| 1. LAN básica | Aprendizaje MAC en el switch, ARP e ICMP en capturas PCAP | [guias/lab1_lan_basica.md](guias/lab1_lan_basica.md) |
| 2. Dos redes con un router | Puerta de enlace, rutas, reenvío y TTL; tres fallas para diagnosticar | [guias/lab2_dos_redes.md](guias/lab2_dos_redes.md) |

## Requisitos

- Ubuntu 24.04 (la VM del curso ya trae todo).
- El [fork de Mininet del curso](https://github.com/mendezgarabetti/mininet), con Open vSwitch.
- `iproute2`, `ping`, `tcpdump`, `tshark` y, para mirar las capturas, Wireshark.

Mininet necesita root para crear namespaces, interfaces virtuales y switches:
ejecutá los laboratorios **dentro de la VM**, nunca en tu equipo personal.
Los escenarios no instalan nada ni modifican configuraciones permanentes.

## Uso

```console
git clone https://github.com/fosshlab/redes101.git
cd redes101
sudo python3 escenarios/lan_basica.py
```

Se abre la consola `minired>`, que acepta todos los comandos de la consola de
Mininet (`net`, `pingall`, `pc1 ping ...`, `sh ...`) y además:

| Comando | Qué hace |
|---|---|
| `falla NOMBRE` | Aplica una falla: `sin_gateway` (solo lab 2), `interfaz_down` o `ip_fuera_de_red` |
| `restaurar` | Quita la falla recreando toda la red |
| `reset` | Recrea la red desde cero: vacía tablas ARP y la FDB del switch |
| `capturar DIRECTORIO` | Guarda un PCAP por cada extremo de cada enlace |
| `detener_captura` | Cierra los PCAP para poder abrirlos |
| `stop` o `exit` | Sale y limpia switches, interfaces y capturas |

Las capturas se nombran por enlace y extremo: `01_pc1-eth0.pcap`,
`01_s1-eth1.pcap`, y así. Cada PCAP tiene al lado un `.log` con la salida de
tcpdump por si algo no arranca.

Si una sesión terminó de forma abrupta (por ejemplo, se apagó la VM),
`sudo mn -c` limpia cualquier resto de Mininet.

## Comprobar la instalación

```console
sudo bash validar.sh
```

Recorre ambos laboratorios de punta a punta (direcciones, rutas, capturas,
fallas y restauración) y termina con
`OK: ambos laboratorios funcionan en esta VM`. Tarda menos de medio minuto.

## Licencia

Código y guías bajo [BSD-3-Clause](LICENSE). Mininet es un proyecto aparte, con
su [propia licencia](https://github.com/mininet/mininet/blob/master/LICENSE).
