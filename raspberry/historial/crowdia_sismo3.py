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
T_MIN = 2.0
CAL_S = 10

LIM = [1.7, 14, 39, 92, 180, 340, 650]
NOM = ["I", "II-III", "IV", "V", "VI", "VII", "VIII", "IX+"]

def intensidad(mg):
    for lim, nom in zip(LIM, NOM):
        if mg < lim: return nom
    return NOM[-1]

def barra(mg):
    k = int(25 * math.log10(max(mg, 1)) / math.log10(650))
    return "█" * min(k, 25)

def leer_g():
    d = bus.read_i2c_block_data(ADDR, 0x3B, 6)
    v = [(d[i] << 8) | d[i+1] for i in (0, 2, 4)]
    v = [x - 65536 if x > 32767 else x for x in v]
    return math.sqrt(sum((x / 16384) ** 2 for x in v))

print(f"Calibrando {CAL_S} s: no toques el sensor ni la mesa")
time.sleep(2)
m, t_fin = [], time.time() + CAL_S
while time.time() < t_fin:
    m.append(leer_g())
    print(f"\r  Faltan {t_fin - time.time():4.1f} s ", end="", flush=True)
    time.sleep(1 / FS)
base = sum(m) / len(m)
ruido = sum(abs(x - base) for x in m) / len(m)
fin = f"\nListo. Gravedad {base:.3f} g | Ruido {ruido*1000:.1f} mg"
print(fin + f" | {len(m) / CAL_S:.0f} Hz")

sta, lta, pico, pmax = ruido, ruido, 0.0, 0.0
evento, t0 = False, 0.0
n, t_sig = 0, time.time()

while True:
    a = abs(leer_g() - base)
    sta += (a - sta) / (STA_S * FS)
    if not evento: lta += (a - lta) / (LTA_S * FS)
    pico = max(pico * 0.995, a)
    r = sta / max(lta, 1e-4)
    if not evento and r >= ON: evento, t0, pmax = True, time.time(), 0.0
    if evento: pmax = max(pmax, a)
    dur = time.time() - t0 if evento else 0.0
    alerta = evento and dur >= T_MIN and pmax * 1000 >= ALERTA_MG
    if evento and r <= OFF:
        evento = False
        tipo = "golpe/impulso" if dur < T_MIN else "sostenido"
        res = f"\nEvento {tipo}: {dur:.1f} s | pico {pmax*1000:.0f} mg"
        res += f" | intensidad {intensidad(pmax*1000)}"
        res += " | ALERTA" if alerta else " | sin alerta"
        print(res, flush=True)
    n += 1
    if n % 5 == 0:
        estado = f"EVENTO {dur:3.1f}s" if evento else "Reposo"
        if alerta: estado = "ALERTA SISMO"
        ints = intensidad(pmax * 1000) if evento else "-"
        txt = f"\r{estado:<12} |{barra(sta*1000):<25}|"
        txt += f" Vib {sta*1000:5.1f} mg | Pico {pico*1000:5.1f} mg"
        txt += f" | R {r:4.1f} | Int {ints:<6}  "
        print(txt, end="", flush=True)
    t_sig += 1 / FS
    time.sleep(max(0, t_sig - time.time()))
