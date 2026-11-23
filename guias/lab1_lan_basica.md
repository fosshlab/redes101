# Laboratorio 1: LAN básica

Tres PC conectadas a un mismo switch. Vas a ver cómo el switch aprende en qué
puerto está cada MAC y cómo ARP resuelve la dirección de la otra PC antes del
primer ping.

```text
  PC1 192.168.1.10/24 ----+
                          |  s1 (switch)
  PC2 192.168.1.20/24 ----+
                          |
  PC3 192.168.1.30/24 ----+
```

| Equipo | Interfaz | IP / máscara | MAC | Puerto de s1 |
|---|---|---|---|---|
| PC1 | `pc1-eth0` | 192.168.1.10/24 | 02:00:00:00:01:01 | `s1-eth1` |
| PC2 | `pc2-eth0` | 192.168.1.20/24 | 02:00:00:00:01:02 | `s1-eth2` |
| PC3 | `pc3-eth0` | 192.168.1.30/24 | 02:00:00:00:01:03 | `s1-eth3` |

`s1` es un switch de Open vSwitch sin controlador: se comporta como un switch
común que aprende direcciones MAC. PC3 no participa del ping; está para que
puedas comparar qué tráfico le llega y cuál no.

## 1. Armar la red

Dentro de la VM, desde la carpeta del repositorio:

```console
sudo python3 escenarios/lan_basica.py
```

Queda abierta la consola `minired>`. Mirá cómo quedó conectado todo:

```console
minired> net
```

## 2. Probar

```console
minired> pc1 ping -c 2 -W 2 192.168.1.20
minired> pc1 ip neigh show
minired> sh ovs-appctl fdb/show s1
```

`sh` ejecuta un comando en la VM, fuera de las PC emuladas.

- ¿Qué MAC aparece en la tabla de vecinos de PC1? ¿De qué equipo es?
- En la FDB de `s1`, ¿qué MAC hay en cada puerto? Compará con la tabla de arriba.
- Nadie configuró esa FDB. ¿Cómo la completó el switch?

## 3. Capturar paquetes reales

Para ver el ARP desde el principio, la red tiene que empezar vacía: `reset` la
recrea y borra lo aprendido. Después capturá un solo ping:

```console
minired> reset
minired> capturar /tmp/lab1
minired> pc1 ping -c 1 -W 2 192.168.1.20
minired> detener_captura
```

En otra terminal de la VM, compará lo que salió por el puerto de PC2 con lo
que salió por el puerto de PC3:

```console
tshark -r /tmp/lab1/02_s1-eth2.pcap -Y 'arp or icmp'
tshark -r /tmp/lab1/03_s1-eth3.pcap -Y 'arp or icmp'
wireshark /tmp/lab1/02_s1-eth2.pcap
```

- ¿Qué mensajes llegan a PC3? ¿Por qué esos sí y los demás no?
- ¿A qué dirección MAC de destino va la solicitud ARP? ¿Y la respuesta?
- En Wireshark, desplegá Ethernet, ARP, IPv4 e ICMP en una trama de eco y
  ubicá las MAC y las IP de la tabla.

Puede aparecer tráfico ICMPv6 que Linux genera solo; el filtro `arp or icmp`
lo deja afuera.

## 4. Romper para entender

Aplicá una falla por vez y usá `restaurar` antes de la siguiente:

```console
minired> falla interfaz_down
minired> pc2 ip -br link
minired> pc1 ping -c 1 -W 2 192.168.1.20
minired> restaurar
minired> falla ip_fuera_de_red
minired> pc2 ip -br addr
minired> pc1 ping -c 1 -W 2 192.168.1.20
minired> restaurar
```

- `interfaz_down` apaga administrativamente la interfaz de PC2. ¿Qué cambia en
  la salida de `ip -br link`?
- `ip_fuera_de_red` le pone a PC2 una IP de otra red sin moverla del switch.
  ¿Por qué PC1 deja de alcanzarla si el cable sigue conectado?

`sin_gateway` no existe en este laboratorio: en una sola LAN nadie necesita
puerta de enlace.

## 5. Salir

```console
minired> stop
```

La red, los puertos del switch y las capturas activas se cierran. Los PCAP ya
guardados quedan en disco.
