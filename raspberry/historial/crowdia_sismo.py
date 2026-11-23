# CROWDIA - Sismometro, version 1 (historica).
# Primera version con STA/LTA. Se conserva para documentar la evolucion del codigo.
# Problemas encontrados en pruebas (ver docs/04_pruebas_y_resultados.md):
#  - El LTA seguia actualizandose durante la sacudida y "se comia" la relacion STA/LTA,
#    por eso una sacudida fuerte se quedaba en "Vibracion" y nunca llegaba a "POSIBLE SISMO".
#  - Los umbrales de 5 mg y 10 mg no tenian respaldo en ninguna fuente.
import smbus, time, math

bus = smbus.SMBus(3)
ADDR = 0x68
bus.write_byte_data(ADDR, 0x6B, 0)
bus.write_byte_data(ADDR, 0x1A, 3)
FS = 50

def leer_g():
    d = bus.read_i2c_block_data(ADDR, 0x3B, 6)
    v = [(d[i] << 8) | d[i+1] for i in (0, 2, 4)]
    v = [x - 65536 if x > 32767 else x for x in v]
    return math.sqrt(sum((x / 16384) ** 2 for x in v))

print("Calibrando: deja el sensor quieto 3 s...")
base = sum(leer_g() for _ in range(150)) / 150
print(f"Listo. Gravedad medida: {base:.3f} g")
sta, lta, pico, n = 0.0, 0.0, 0.0, 0

while True:
    a = abs(leer_g() - base)
    sta += (a - sta) / (0.5 * FS)
    lta += (a - lta) / (10 * FS)
    pico = max(pico * 0.995, a)
    r = sta / lta if lta > 1e-6 else 0
    n += 1
    if n < 10 * FS: estado = "Aprendiendo ruido"
    elif r > 3 and sta > 0.01: estado = "POSIBLE SISMO"
    elif sta > 0.005: estado = "Vibración"
    else: estado = "Reposo"
    if n % 5 == 0:
        barra = "█" * min(int(sta * 500), 25)
        print(f"\rVibración {sta*1000:6.1f} mg |{barra:<25}| Pico {pico*1000:6.1f} mg  STA/LTA {r:4.1f}  {estado:<18}", end="", flush=True)
    time.sleep(1 / FS)
