import smbus, time, math

bus = smbus.SMBus(3)
ADDR = 0x68
bus.write_byte_data(ADDR, 0x6B, 0)
bus.write_byte_data(ADDR, 0x1A, 4)

FS = 50
STA_S = 0.5
LTA_S = 60
ON = 4.0
OFF = 2.5
ALERTA_MG = 39

LIM = [1.7, 14, 39, 92, 180, 340, 650]
NOM = ["I", "II-III", "IV", "V", "VI", "VII", "VIII", "IX+"]

def intensidad(mg):
    for lim, nom in zip(LIM, NOM):
        if mg < lim: return nom
    return NOM[-1]

def leer_g():
    d = bus.read_i2c_block_data(ADDR, 0x3B, 6)
    v = [(d[i] << 8) | d[i+1] for i in (0, 2, 4)]
    v = [x - 65536 if x > 32767 else x for x in v]
    return math.sqrt(sum((x / 16384) ** 2 for x in v))

print("Calibrando: deja el sensor quieto 3 s...")
m = [leer_g() for _ in range(150)]
base = sum(m) / len(m)
ruido = sum(abs(x - base) for x in m) / len(m)
print(f"Listo. Gravedad: {base:.3f} g | Ruido: {ruido*1000:.1f} mg")

sta, lta, pico, pmax = ruido, ruido, 0.0, 0.0
evento, t0 = False, 0.0
n, t_ini, t_sig = 0, time.time(), time.time()

while True:
    a = abs(leer_g() - base)
    sta += (a - sta) / (STA_S * FS)
    if not evento: lta += (a - lta) / (LTA_S * FS)
    pico = max(pico * 0.995, a)
    r = sta / max(lta, 1e-4)
    if not evento and r >= ON: evento, t0, pmax = True, time.time(), 0.0
    if evento: pmax = max(pmax, a)
    if evento and r <= OFF:
        evento = False
        dur = time.time() - t0
        alerta = "SI" if pmax * 1000 >= ALERTA_MG else "no"
        res = f"\nEvento: {dur:.1f} s | pico {pmax*1000:.0f} mg"
        res += f" | intensidad {intensidad(pmax*1000)} | alerta: {alerta}"
        print(res, flush=True)
    n += 1
    if n % 5 == 0:
        hz = n / (time.time() - t_ini)
        estado = "EVENTO" if evento else "Reposo"
        if evento and pmax * 1000 >= ALERTA_MG: estado = "ALERTA SISMO"
        txt = f"\r{estado:<12} STA/LTA {r:4.1f}"
        txt += f" | Vib {sta*1000:5.1f} mg | Pico {pico*1000:6.1f} mg"
        ints = intensidad(pmax * 1000) if evento else "-"
        txt += f" | Int {ints:<6} | {hz:4.1f} Hz"
        print(txt, end="", flush=True)
    t_sig += 1 / FS
    time.sleep(max(0, t_sig - time.time()))
