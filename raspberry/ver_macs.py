import socket, time
PI_MAC = "2C:CF:67:9B:6D:5C"
UMBRAL = -65
DURACION = 60
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", 5005))
s.settimeout(1.0)
vistos = {}
fin = time.time() + DURACION
print(f"Escuchando {DURACION} s...")
while time.time() < fin:
    try:
        datos, _ = s.recvfrom(1024)
        nodo, mac, tipo, rssi = datos.decode().strip().split(",")
        rssi = int(rssi)
    except (socket.timeout, ValueError):
        continue
    d = vistos.setdefault(mac, {"n": 0, "max": -200, "tipos": set()})
    d["n"] += 1
    d["max"] = max(d["max"], rssi)
    d["tipos"].add(tipo)
print(f"\n{'MAC':<18} {'paquetes':>8} {'RSSI max':>8}  {'tipo':<9} nota")
for mac, d in sorted(vistos.items(), key=lambda x: -x[1]["max"]):
    nota = []
    if mac == PI_MAC: nota.append("Raspberry Pi")
    if int(mac[1], 16) & 2: nota.append("MAC aleatoria")
    if d["max"] < UMBRAL: nota.append("debil: integrado la ignora")
    tipos = "/".join(sorted(d["tipos"]))
    print(f"{mac:<18} {d['n']:>8} {d['max']:>8}  {tipos:<9} {', '.join(nota)}")
print(f"\nTotal: {len(vistos)} MAC distintas")
