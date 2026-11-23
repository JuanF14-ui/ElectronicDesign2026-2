# CROWDIA - "integrado.py" (historico).
# Programa que genero el agente PicoClaw (por Telegram) y con el que se hicieron las primeras
# pruebas del sistema completo. El original esta en la Raspberry Pi en
# ~/.picoclaw/workspace/integrado.py; esta copia se transcribio de capturas de pantalla
# del 22/11/2026 para documentar la evolucion del codigo.
# Problemas encontrados (ver docs/03_codigos.md y docs/04_pruebas_y_resultados.md):
#  - STA y LTA arrancan en 0: al terminar la calibracion el estado queda en "EVENTO" para siempre.
#  - La alerta compara el promedio (STA) con 39 mg, no el pico, y no usa T_MIN.
#  - Mide |a| - g, que es casi ciego a las sacudidas horizontales.
#  - CSV_FILE esta definido pero nunca se escribe.
#  - El socket UDP se cierra y se vuelve a abrir cada 60 s (se pierden paquetes en el cambio).
# Reemplazado por raspberry/crowdia_integrado.py.
import socket
import time
import csv
import os
import smbus
import math
import threading
from collections import defaultdict

# --- Configuración sniffer ---
PUERTO = 5005
DURACION_SCAN = 60
UMBRAL_RSSI = -65
CSV_FILE = "memory/captura_dispositivos.csv"

# --- Configuración sismómetro ---
ADDR = 0x68
bus = smbus.SMBus(3)
bus.write_byte_data(ADDR, 0x6B, 0)
bus.write_byte_data(ADDR, 0x1A, 4)
FS = 50
STA_S, LTA_S = 0.5, 60
ON, OFF = 4.0, 2.5
ALERTA_MG = 39
T_MIN = 2.0
CAL_S = 10
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

def sniffer_thread():
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", PUERTO))
        sock.settimeout(1.0)
        dispositivos = {}
        tiempo_final = time.time() + DURACION_SCAN
        while time.time() < tiempo_final:
            try:
                datos, _ = sock.recvfrom(1024)
                mensaje = datos.decode("utf-8").strip()
                nodo, mac, tipo, rssi = mensaje.split(",")
                rssi = int(rssi)
                if rssi >= UMBRAL_RSSI and tipo != "ROUTER":
                    dispositivos[mac] = {"rssi": rssi}
            except: continue
        sock.close()
        print(f"\n[SCAN] Detectados {len(dispositivos)} dispositivos únicos.", flush=True)

def sismo_thread():
    print("Calibrando sismómetro...", flush=True)
    time.sleep(2)
    m, t_fin = [], time.time() + CAL_S
    while time.time() < t_fin:
        m.append(leer_g())
        time.sleep(1/FS)
    base = sum(m) / len(m)
    print(f"Calibración terminada. Base: {base:.4f}", flush=True)

    sta, lta, evento, t0 = 0.0, 0.0, False, 0.0
    t_sig = time.time()
    n = 0
    while True:
        a = abs(leer_g() - base)
        sta += (a - sta) / (STA_S * FS)
        if not evento: lta += (a - lta) / (LTA_S * FS)
        r = sta / max(lta, 1e-4)
        if not evento and r >= ON: evento, t0 = True, time.time()

        n += 1
        if n % 25 == 0:
            vib_mg = sta * 1000
            if evento and vib_mg >= ALERTA_MG:
                estado = "ALERTA SISMO"
            else:
                estado = "EVENTO" if evento else "Reposo"
            print(f"Estado: {estado} | Vib: {vib_mg:.1f} mg | R: {r:.1f}", flush=True)

        if evento and r <= OFF:
            evento = False
            print(f"\n[SISMO] Evento finalizado. Intensidad: {intensidad(sta*1000)}", flush=True)

        t_sig += 1 / FS
        time.sleep(max(0, t_sig - time.time()))

if __name__ == "__main__":
    threading.Thread(target=sismo_thread, daemon=True).start()
    time.sleep(12)
    threading.Thread(target=sniffer_thread, daemon=True).start()
    while True: time.sleep(1)
