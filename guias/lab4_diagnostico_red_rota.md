# Laboratorio 4: diagnóstico forense de una red rota

En operación real casi nunca configurás una red limpia desde cero: lo habitual
es recibir una red caída y aislar fallas en capas L1, L2 y L3 siguiendo el
camino completo de ida y de regreso del tráfico.

```text
   Red A: 192.168.10.0/24               Red B: 192.168.20.0/24

   pc1 ---- s1 ---- [ r1 ] ---- s2 ---- pc2
 .10.10         .10.1   .20.1         .20.10
```

| Equipo | Interfaz | IP / máscara esperada | MAC |
|---|---|---|---|
| `pc1` | `pc1-eth0` | `192.168.10.10/24` | `02:00:00:00:0a:0a` |
| `r1` | `r1-eth0` | `192.168.10.1/24` | `02:00:00:00:0a:01` |
| `r1` | `r1-eth1` | `192.168.20.1/24` | `02:00:00:00:14:01` |
| `pc2` | `pc2-eth0` | `192.168.20.10/24` | `02:00:00:00:14:0a` |

El escenario arranca con **tres fallas de configuración** distintas entre la Red A y la Red B. Tu objetivo es descubrir las tres y lograr que `pc1` llegue a `pc2` sin reiniciar la red.

## 1. Levantar el escenario y verificar el síntoma

Desde la carpeta `redes101` en la VM:

```console
sudo python3 escenarios/red_rota.py
```

Comprobá que la conectividad entre redes falla desde el inicio (y probá opcionalmente llegar primero al enlace local):

```console
minired> pc1 ping -c 1 -W 1 192.168.20.10
minired> pc1 ping -c 1 -W 1 192.168.10.1
```

## 2. Checklist metódico de inspección (de punta a punta)

Antes de modificar nada, capturá evidencia de cada tramo. Opcionalmente iniciá `capturar /tmp/lab4` para ver hasta dónde avanza realmente el paquete antes y después de cada corrección.

### Tramo 1: el origen (`pc1`)

```console
minired> pc1 ip -br link
minired> pc1 ip -br addr
minired> pc1 ip route
```

- Contrastá la ruta por defecto de `pc1` contra la IP real de `r1-eth0` en la Red A.
- Si encontrás una discrepancia, consultá `minired> pc1 ip route help` y corregila.

### Tramo 2: el router (`r1`)

```console
minired> r1 ip -br link
minired> r1 ip -br addr
minired> r1 ip route
minired> r1 sysctl net.ipv4.ip_forward
```

- ¿Conoce `r1` ambas subredes (`192.168.10.0/24` y `192.168.20.0/24`) con `scope link`?
- ¿Tiene habilitado en el kernel el reenvío de paquetes entre interfaces? Si está desactivado, corregilo con `sysctl -w ...` y volvé a probar `pc1 ping -c 1 -W 1 192.168.20.10`.

### Tramo 3: el destino y el camino de retorno (`pc2`)

Si después de corregir origen y router el ping sigue fallando, inspeccioná los contadores o una captura en `r1-eth1` y revisá la configuración de `pc2`:

```console
minired> r1 tcpdump -c 4 -nn -i r1-eth1 icmp
minired> pc2 ip -br addr
minired> pc2 ip route
```

- ¿El paquete `ICMP Echo Request` llega hasta `pc2`?
- ¿Sabe `pc2` hacia qué dirección reenviar la respuesta destinada a `192.168.10.10`? Agregale la ruta faltante usando `ip route ...`.

## 3. Verificación final

Cuando hayas reparado las tres fallas en memoria, confirmá la conectividad, el decremento de TTL y la cantidad exacta de saltos:

```console
minired> pc1 ping -c 3 192.168.20.10
minired> pc1 traceroute -n 192.168.20.10
```

Si querés volver a practicar desde el estado inicial roto, ejecutá `minired> reset`. Para terminar y limpiar la topología usá `minired> stop`.
