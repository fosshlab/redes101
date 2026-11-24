# Laboratorio 3: topologías `mn`, latencia, ancho de banda TCP y captura de handshake

En este laboratorio combinás la creación rápida de redes con el comando `mn` y
un escenario reproducible con enlaces limitados por `tc` (`TCLink` + NetEm/TBF)
para medir cómo impactan los retardos, el cuello de botella y la pérdida de
paquetes sobre `ping`, `iperf` y TCP.

```text
   h1 (192.168.10.10/24) ---- s1 ---- s2 ---- h2 (192.168.10.20/24)
       [bw=10 Mb/s, delay=10 ms por enlace — 3 enlaces en serie]
```

| Equipo | Interfaz | IP / máscara | MAC |
|---|---|---|---|
| `h1` | `h1-eth0` | `192.168.10.10/24` | `02:00:00:00:0a:01` |
| `h2` | `h2-eth0` | `192.168.10.20/24` | `02:00:00:00:0a:02` |

## 1. Explorar topologías rápidas con `mn`

Dentro de la VM, lanzá una red de un switch y tres hosts con MAC legibles:

```console
sudo mn --topo single,3 --mac
```

En la consola `mininet>`, revisá enlaces, direcciones y tablas ARP/MAC:

```console
mininet> net
mininet> h1 ip -br addr
mininet> pingall
mininet> h1 ip neigh show
mininet> link s1 h3 down
mininet> pingall
mininet> link s1 h3 up
mininet> exit
```

- Cuando cortás el enlace entre `s1` y `h3`, ¿qué pares de hosts siguen comunicándose en `pingall`?
- En la versión de Mininet de la VM también podés usar `arps` y `macs` para inspeccionar todas las tablas a la vez.

## 2. Escenario de rendimiento TCP con `TCLink`

Desde la carpeta `redes101` en la VM:

```console
sudo python3 escenarios/rendimiento_tcp.py --bw 10 --delay 10ms
```

Queda abierta la consola `minired>` con 3 enlaces limitados a `10 Mb/s` y `10 ms` de retardo unidireccional cada uno.

### Medir latencia (RTT) y observar el primer ping

```console
minired> reset
minired> h1 ping -c 5 192.168.10.20
```

- Cada sentido atraviesa **3 enlaces** de `10 ms` (`30 ms` de ida y `30 ms` de vuelta). ¿Coinciden los paquetes 2 a 5 con ese cálculo?
- ¿Por qué el primer `icmp_seq=1` demora aproximadamente el doble que los siguientes?

### Medir throughput útil con `iperf` y capturar el handshake TCP

```console
minired> capturar /tmp/lab3
minired> iperf h1 h2
minired> detener_captura
```

En otra terminal de la VM, inspeccioná el *3-way handshake* TCP en la captura:

```console
tshark -r /tmp/lab3/01_h1-eth0.pcap -Y "tcp.flags.syn == 1"
```

- Con un límite físico de `10 Mb/s`, `iperf` suele informar alrededor de `9.3–9.5 Mb/s` en el servidor. ¿Dónde queda el resto de la capacidad del enlace?
- En el filtro de `tshark`, verificá la secuencia `[SYN]`, `[SYN, ACK]` y los segmentos posteriores con distinto valor de `Seq` y `Ack`.

## 3. Experimentos de sensibilidad (`bw`, `delay`, `loss`)

Salí con `stop` y probá variantes desde línea de comandos:

```console
sudo python3 escenarios/rendimiento_tcp.py --bw 1 --delay 25ms
sudo python3 escenarios/rendimiento_tcp.py --bw 10 --delay 10ms --loss 2
```

- Antes de correr `ping` o `iperf`, calculá en papel el RTT esperado para `--delay 25ms` y el producto ancho de banda-retardo ($\text{BDP} = R \times \text{RTT}$).
- Observá cuánto cae el caudal TCP en `iperf` cuando agregás un `2 %` de pérdida aleatoria por enlace.
- Salí siempre con `minired> stop` (o limpiá restos tras una caída con `sudo mn -c`).
