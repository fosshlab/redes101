# Laboratorio 2: dos redes unidas por un router

Dos LAN distintas y un router Linux entre ellas. Vas a ver qué necesita una PC
para salir de su red, cómo decide el router por dónde reenviar y qué pasa
cuando algo se rompe.

```text
   Red A: 192.168.1.0/24                Red B: 192.168.2.0/24

   pc1 ---- s1 ---- [ r1 ] ---- s2 ---- pc2
  .1.10         .1.1     .2.1          .2.10
```

| Equipo | Interfaz | IP / máscara | MAC | Puerta de enlace |
|---|---|---|---|---|
| PC1 | `pc1-eth0` | 192.168.1.10/24 | 02:00:00:00:01:0a | 192.168.1.1 |
| r1 | `r1-eth0` | 192.168.1.1/24 | 02:00:00:00:01:01 | — |
| r1 | `r1-eth1` | 192.168.2.1/24 | 02:00:00:00:02:01 | — |
| PC2 | `pc2-eth0` | 192.168.2.10/24 | 02:00:00:00:02:0a | 192.168.2.1 |

`r1` es un host Linux con el reenvío IPv4 activado (`net.ipv4.ip_forward=1`).
No se configura ninguna ruta a mano.

## 1. Armar la red

```console
sudo python3 escenarios/dos_redes.py
```

## 2. Comprobar

```console
minired> r1 ip -br addr
minired> r1 ip route
minired> pc1 ip route
minired> pc1 ping -c 3 -W 2 192.168.2.10
```

- La tabla de `r1` tiene una ruta por cada red, aunque nadie las agregó.
  ¿De dónde salen? ¿Qué te dice la palabra `scope` de cada una?
- ¿Qué ruta de PC1 se usa para llegar a 192.168.2.10?
- ¿Qué TTL tienen las respuestas del ping? ¿Por qué no es 64?

Si el primer eco tarda más, es ARP resolviendo direcciones en cada red.

## 3. Ver el salto del router en paquetes reales

```console
minired> reset
minired> capturar /tmp/lab2
minired> pc1 ping -c 1 -W 2 192.168.2.10
minired> detener_captura
```

En otra terminal:

```console
tshark -r /tmp/lab2/03_r1-eth0.pcap -Y icmp -T fields -e eth.src -e eth.dst -e ip.src -e ip.dst -e ip.ttl
tshark -r /tmp/lab2/04_r1-eth1.pcap -Y icmp -T fields -e eth.src -e eth.dst -e ip.src -e ip.dst -e ip.ttl
```

- ¿Qué cambia entre una captura y la otra: las IP, las MAC o ambas?
- ¿Cuánto cambió el TTL al cruzar el router?

## 4. Romper para entender

Aplicá **una falla por vez**. Después de observarla, usá `restaurar` para
recrear la red antes de la siguiente.

```console
minired> falla sin_gateway
minired> pc1 ip route
minired> pc1 ping -c 1 -W 2 192.168.2.10
minired> pc1 ping -c 1 -W 2 192.168.1.1
minired> restaurar
```

- ¿A cuál de los dos destinos llega PC1? ¿Por qué uno sí y el otro no?

```console
minired> falla interfaz_down
minired> r1 ip -j link show r1-eth1
minired> r1 ip -j link show r1-eth0
minired> r1 ip route
minired> restaurar
```

- `interfaz_down` apaga administrativamente `r1-eth1`. Compará la lista
  `flags` de las dos interfaces de r1: ¿qué indicador cambió?
- ¿Qué le pasó a la ruta hacia 192.168.2.0/24?
- Antes de `restaurar`, buscá con `ip link help` cómo volver a activar la
  interfaz desde r1 y comprobalo con un ping.

```console
minired> falla ip_fuera_de_red
minired> pc2 ip -br addr
minired> pc1 ping -c 1 -W 2 192.168.2.10
minired> restaurar
```

- PC2 quedó con una IP de la Red A, pero sigue conectada a `s2`. ¿Por qué no
  se comunica ni con PC1 ni con el router?

## 5. Salir

```console
minired> stop
```
