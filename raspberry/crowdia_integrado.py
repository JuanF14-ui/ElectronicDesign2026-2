# CROWDIA - Programa integrado v5 (nodo sniffer en la Raspberry Pi Zero 2 W)
# Sismometro (MPU6050) + conteo de dispositivos (ESP32 por UDP) + buzzer + LCD 16x2 + CSV
# Conexiones (ver docs/02_hardware_y_conexiones.md):
#   MPU6050: I2C por software bus 3, SDA = GPIO5 (pin 29), SCL = GPIO6 (pin 31)
#   Buzzer:  GPIO26 (pin 37) a la base del transistor
#   LCD:     RS = GPIO17, E = GPIO18, D4..D7 = GPIO27, 22, 23, 24
import socket, time, math, threading, csv, os, hashlib, argparse
from collections import deque
import smbus

# ============ ARGUMENTOS ============
# Uso normal:        python3 crowdia_integrado.py
# Recoleccion datos: python3 crowdia_integrado.py --etiqueta golpe
#   (todos los eventos grabados en esa sesion quedan con esa etiqueta provisional)
ETIQUETAS = ["sacudida", "golpe", "golpes_repetidos", "caminar", "puerta",
             "objeto_cae", "sensor_movido", "otro"]
_ap = argparse.ArgumentParser(description="CROWDIA: sismometro + dispositivos")
_ap.add_argument("--etiqueta", choices=ETIQUETAS, default="",
                 help="etiqueta provisional para los eventos de esta sesion")
ARGS = _ap.parse_args()

# ============ CONFIGURACION GENERAL ============
CARPETA = os.path.expanduser("~/crowdia/datos")
os.makedirs(CARPETA, exist_ok=True)
CSV_DISP = os.path.join(CARPETA, "dispositivos_v3.csv")
CSV_RESUMEN = os.path.join(CARPETA, "resumen_v3.csv")
CSV_SISMO = os.path.join(CARPETA, "sismos_v3.csv")
CARPETA_EVT = os.path.expanduser("~/crowdia/eventos")
os.makedirs(CARPETA_EVT, exist_ok=True)
CSV_INDICE = os.path.join(CARPETA_EVT, "indice.csv")
candado = threading.Lock()
listo = threading.Event()

def decir(texto, fin="\n"):
    with candado:
        print(texto, end=fin, flush=True)

def guardar(archivo, encabezado, fila):
    nuevo = not os.path.exists(archivo)
    with open(archivo, "a", newline="") as f:
        w = csv.writer(f)
        if nuevo: w.writerow(encabezado)
        w.writerow(fila)

# ============ PANTALLA LCD 16x2 ============
LCD_RS, LCD_E = 17, 18           # GPIO (BCM) de RS y E
LCD_D = [27, 22, 23, 24]         # GPIO (BCM) de D4, D5, D6, D7
LCD_COLS = 16                    # caracteres por linea
pantalla = {"l1": "CROWDIA", "l2": "Calibrando..."}   # linea 1: sismo | linea 2: celulares
try:
    from luma.core.interface.parallel import bitbang_6800
    from luma.lcd.device import hd44780
    _lcd = hd44780(bitbang_6800(RS=LCD_RS, E=LCD_E, PINS=LCD_D), width=LCD_COLS, height=2)
except Exception as e:
    _lcd = None
    print(f"AVISO: LCD desactivada ({e})")

def lcd_bucle():
    # Hilo aparte: refresca la LCD cada 0,5 s solo si cambio algo (no frena el sensor)
    anterior = None
    while True:
        txt = pantalla["l1"][:LCD_COLS].ljust(LCD_COLS) + "\n" + pantalla["l2"][:LCD_COLS].ljust(LCD_COLS)
        if _lcd and txt != anterior:
            try:
                _lcd.text = txt
                anterior = txt
            except Exception:
                pass
        time.sleep(0.5)

# ============ BUZZER ============
BUZZER_PIN = 26          # GPIO (BCM) donde va la base del transistor
BUZZER_ACTIVO = True     # True: buzzer activo (suena con DC). False: pasivo (necesita tono)
FREQ_TONO = 2000         # Hz, solo para buzzer pasivo
BUZZER_MG = 92           # Sismo "fuerte": pico >= 92 mg (intensidad VI de Wald)

try:
    from gpiozero import PWMOutputDevice
    _dev = PWMOutputDevice(BUZZER_PIN, frequency=FREQ_TONO, initial_value=0)
except Exception as e:
    _dev = None
    print(f"AVISO: buzzer desactivado ({e})")

class Buzzer:
    def __init__(self):
        self.alarma = False
        self.pendientes = 0
        self.lock = threading.Lock()
        threading.Thread(target=self._bucle, daemon=True).start()

    def _sonar(self, encendido):
        if _dev: _dev.value = (1.0 if BUZZER_ACTIVO else 0.5) if encendido else 0

    def pitidos(self, n):
        with self.lock:
            self.pendientes += n

    def _bucle(self):
        while True:
            if self.alarma:
                self._sonar(True); time.sleep(0.15)
                self._sonar(False); time.sleep(0.15)
            elif self.pendientes > 0:
                with self.lock: self.pendientes -= 1
                self._sonar(True); time.sleep(0.08)
                self._sonar(False); time.sleep(0.25)
            else:
                time.sleep(0.05)

zumbador = Buzzer()

# ============ SNIFFER ============
PUERTO = 5005
DURACION_SCAN = 60
UMBRAL_RSSI = -65
SAL = "crowdia-2026"
MACS_SISTEMA = {
    "2C:CF:67:9B:6D:5C": "Raspberry Pi",
    "78:1C:3C:E3:E8:38": "ESP32 NODO_1",
}

def hash_mac(mac):
    return hashlib.sha256((SAL + mac).encode()).hexdigest()[:12]

def es_aleatoria(mac):
    return (int(mac[1], 16) & 2) != 0

PAQ_MIN = 10        # Paquetes en una ventana para confirmar una MAC aleatoria
AGRUPAR_DB = 4      # MAC efimeras con RSSI a +-4 dB se cuentan como un solo equipo

def clasificar(ventana, vistos, historial):
    # fija: MAC de fabrica | estable: aleatoria confirmada (>= PAQ_MIN paquetes o
    # vista en la ventana anterior) | efimera: aleatoria de un solo uso
    est = {}
    for mac, d in vistos.items():
        if mac in MACS_SISTEMA: est[mac] = "sistema"
        elif d["max"] < UMBRAL_RSSI: est[mac] = "debil"
        elif not es_aleatoria(mac): est[mac] = "fija"
        elif d["n"] >= PAQ_MIN or historial.get(mac) == ventana - 1: est[mac] = "estable"
        else: est[mac] = "efimera"
    ref = [vistos[m]["max"] for m in est if est[m] == "estable"]
    efim = sorted((m for m in est if est[m] == "efimera"), key=lambda m: -vistos[m]["max"])
    grupos, g, ultimo = {}, 0, None
    for m in efim:
        r = vistos[m]["max"]
        if any(abs(r - x) <= AGRUPAR_DB for x in ref):
            grupos[m] = "=estable"
            continue
        if ultimo is None or ultimo - r > AGRUPAR_DB:
            g += 1
        grupos[m] = f"G{g}"
        ultimo = r
    return est, grupos, g

def reportar(ventana, vistos, historial):
    est, grupos, ng = clasificar(ventana, vistos, historial)
    fecha = time.strftime("%Y-%m-%d %H:%M:%S")
    crudo = sum(1 for m in est if est[m] in ("fija", "estable", "efimera"))
    fijas = sum(1 for m in est if est[m] == "fija")
    estables = sum(1 for m in est if est[m] == "estable")
    estimado = fijas + estables + ng
    celulares = estables + ng
    filas = []
    for mac, d in sorted(vistos.items(), key=lambda x: -x[1]["max"]):
        tipos = "/".join(sorted(d["tipos"]))
        nota = MACS_SISTEMA.get(mac, "")
        filas.append(f"{mac:<18} {d['n']:>8} {d['max']:>8}  {tipos:<9} {est[mac]:<8} {grupos.get(mac, ''):<8} {nota}")
        guardar(CSV_DISP,
                ["fecha", "ventana", "id_hash", "aleatoria", "paquetes", "rssi_max", "tipos", "estado", "grupo"],
                [fecha, ventana, hash_mac(mac), es_aleatoria(mac), d["n"], d["max"], tipos,
                 est[mac], grupos.get(mac, "")])
    guardar(CSV_RESUMEN,
            ["fecha", "ventana", "mac_vistas", "contados_crudo", "fijas", "estables", "grupos_efimeros", "estimado", "celulares_est"],
            [fecha, ventana, len(vistos), crudo, fijas, estables, ng, estimado, celulares])
    txt = f"\n\n[SCAN {ventana}] {fecha[11:]} | Estimado {estimado} dispositivos"
    txt += f" ({fijas} fijos + {estables} aleatorios estables + {ng} grupos efimeros)"
    txt += f" | sin agrupar habria contado {crudo}\n"
    txt += f"{'MAC':<18} {'paquetes':>8} {'RSSI max':>8}  {'tipo':<9} {'estado':<8} {'grupo':<8} nota\n"
    txt += "\n".join(filas) if filas else "(no llego ningun paquete del ESP32)"
    decir(txt + "\n")
    pantalla["l2"] = f"Cel:{celulares} Eq:{estimado} S{ventana}" if filas else f"Sin ESP32  S{ventana}"
    return celulares

def sniffer():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PUERTO))
    sock.settimeout(1.0)
    ventana, historial, cel_antes = 0, {}, 0
    while True:
        ventana += 1
        vistos = {}
        fin = time.time() + DURACION_SCAN
        while time.time() < fin:
            try:
                datos, _ = sock.recvfrom(1024)
                nodo, mac, tipo, rssi = datos.decode().strip().split(",")
                rssi = int(rssi)
            except (socket.timeout, ValueError, UnicodeDecodeError):
                continue
            d = vistos.setdefault(mac, {"n": 0, "max": -200, "tipos": set()})
            d["n"] += 1
            d["max"] = max(d["max"], rssi)
            d["tipos"].add(tipo)
        celulares = reportar(ventana, vistos, historial)
        for mac in vistos: historial[mac] = ventana
        if celulares > cel_antes:
            zumbador.pitidos(min(celulares - cel_antes, 3))
        cel_antes = celulares

# ============ SISMOMETRO ============
# MPU6050 en I2C por software, bus 3: SDA = GPIO5 (pin 29), SCL = GPIO6 (pin 31)
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
FRAC_MIN = 0.2
CAL_S = 10
HP_S = 0.5

LIM = [1.7, 14, 39, 92, 180, 340, 650]
NOM = ["I", "II-III", "IV", "V", "VI", "VII", "VIII", "IX+"]

def intensidad(mg):
    for lim, nom in zip(LIM, NOM):
        if mg < lim: return nom
    return NOM[-1]

def barra(mg):
    k = int(25 * math.log10(max(mg, 1)) / math.log10(650))
    return "█" * min(k, 25)

def leer():
    d = bus.read_i2c_block_data(ADDR, 0x3B, 6)
    v = [(d[i] << 8) | d[i+1] for i in (0, 2, 4)]
    return [(x - 65536 if x > 32767 else x) / 16384 for x in v]

# ============ GRABADOR DE EVENTOS (Agente IA 1, fase A) ============
PRE_S = 5        # Segundos guardados ANTES del disparo
POST_S = 2       # Segundos guardados DESPUES del fin del evento
MAX_S = 60       # Duracion maxima de una grabacion

def guardar_evento(muestras, meta):
    # Un archivo por evento con la senal cruda (g) de los 3 ejes y la vibracion (mg)
    nombre = "evt_" + time.strftime("%Y%m%d_%H%M%S", time.localtime(meta["t0"])) + ".csv"
    ruta = os.path.join(CARPETA_EVT, nombre)
    with open(ruta, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "ax_g", "ay_g", "az_g", "vib_mg"])
        for t, x, y, z, a in muestras:
            w.writerow([round(t - meta["t0"], 3), round(x, 5), round(y, 5), round(z, 5), round(a * 1000, 2)])
    guardar(CSV_INDICE,
            ["archivo", "fecha", "fs_hz", "regla_tipo", "duracion_s", "sobre_umbral_s",
             "fraccion", "pico_mg", "alerta_regla", "etiqueta"],
            [nombre, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(meta["t0"])), FS,
             meta["tipo"], meta["dur"], meta["dsig"], meta["frac"], meta["pico"],
             meta["alerta"], ARGS.etiqueta])
    decir(f"[GRABADO] {nombre} ({len(muestras)} muestras, etiqueta: {ARGS.etiqueta or 'sin etiqueta'})")

def sismo():
    decir(f"Calibrando {CAL_S} s: no toques el sensor ni la mesa")
    time.sleep(2)
    m, t_fin = [], time.time() + CAL_S
    while time.time() < t_fin:
        m.append(leer())
        time.sleep(1 / FS)
    b = [sum(s[i] for s in m) / len(m) for i in range(3)]
    ruido = sum(math.dist(s, b) for s in m) / len(m)
    g = math.sqrt(sum(x * x for x in b))
    pantalla["l1"] = "Listo"
    decir(f"Listo. Gravedad {g:.3f} g | Ruido {ruido*1000:.1f} mg | {len(m) / CAL_S:.0f} Hz")
    decir(f"Escaneando dispositivos en ventanas de {DURACION_SCAN} s...")
    decir(f"Eventos se graban en {CARPETA_EVT} | etiqueta de la sesion: {ARGS.etiqueta or 'ninguna'}\n")
    listo.set()

    sta, lta, pico, pmax = ruido, ruido, 0.0, 0.0
    evento, t0, t1, t2, exc, tot = False, 0.0, 0.0, 0.0, 0, 0
    n, t_sig = 0, time.time()
    previo = deque(maxlen=PRE_S * FS)   # ultimos 5 s, siempre disponibles
    captura = None                       # grabacion en curso
    while True:
        try:
            s = leer()
        except OSError:
            time.sleep(1 / FS)
            continue
        b = [b[i] + (s[i] - b[i]) / (HP_S * FS) for i in range(3)]
        a = math.dist(s, b)
        ahora = time.time()
        muestra = (ahora, s[0], s[1], s[2], a)
        if captura is not None:
            captura["datos"].append(muestra)
            fin_post = captura["fin"] is not None and ahora >= captura["fin"] + POST_S
            if captura["meta"] is None and ahora - captura["t0"] > MAX_S:
                captura["meta"] = {"t0": captura["t0"], "tipo": "largo", "dur": round(ahora - captura["t0"], 2),
                                   "dsig": 0, "frac": 0, "pico": round(pmax * 1000, 1), "alerta": False}
            if fin_post or ahora - captura["t0"] > MAX_S:
                threading.Thread(target=guardar_evento, args=(captura["datos"], captura["meta"]), daemon=True).start()
                captura = None
        previo.append(muestra)
        sta += (a - sta) / (STA_S * FS)
        if not evento: lta += (a - lta) / (LTA_S * FS)
        pico = max(pico * 0.995, a)
        r = sta / max(lta, 1e-4)
        if not evento and r >= ON:
            evento, t0, pmax, t1, t2, exc, tot = True, ahora, 0.0, 0.0, 0.0, 0, 0
            if captura is not None:   # habia una grabacion en su tramo final: se guarda ya
                threading.Thread(target=guardar_evento, args=(captura["datos"], captura["meta"]), daemon=True).start()
            captura = {"t0": ahora, "fin": None, "datos": list(previo), "meta": None}
        if evento:
            pmax = max(pmax, a)
            if a * 1000 >= ALERTA_MG:
                if exc == 0: t1 = ahora
                t2, exc = ahora, exc + 1
            if exc > 0: tot += 1
        dur = ahora - t0 if evento else 0.0
        dsig = t2 - t1 if exc > 1 else 0.0
        frac = exc / tot if tot > 0 else 0.0
        alerta = evento and dsig >= T_MIN and frac >= FRAC_MIN
        zumbador.alarma = alerta and pmax * 1000 >= BUZZER_MG
        if evento and r <= OFF:
            evento = False
            zumbador.alarma = False
            tipo = "golpe/impulso" if dsig < T_MIN else "sostenido"
            res = f"\n[SISMO] {time.strftime('%H:%M:%S')} Evento {tipo}: {dur:.1f} s"
            res += f" | sobre umbral {dsig:.1f} s ({frac*100:.0f}%) | pico {pmax*1000:.0f} mg"
            res += f" | int {intensidad(pmax*1000)}"
            res += " | ALERTA" if alerta else " | sin alerta"
            decir(res)
            guardar(CSV_SISMO,
                    ["fecha", "tipo", "duracion_s", "sobre_umbral_s", "fraccion", "pico_mg", "intensidad", "alerta"],
                    [time.strftime("%Y-%m-%d %H:%M:%S"), tipo, round(dur, 2), round(dsig, 2),
                     round(frac, 2), round(pmax * 1000, 1), intensidad(pmax * 1000), alerta])
            if captura is not None:
                captura["fin"] = ahora
                captura["meta"] = {"t0": t0, "tipo": tipo, "dur": round(dur, 2), "dsig": round(dsig, 2),
                                   "frac": round(frac, 2), "pico": round(pmax * 1000, 1), "alerta": alerta}
        n += 1
        if n % 5 == 0:
            estado = f"EVENTO {dur:3.1f}s" if evento else "Reposo"
            if alerta: estado = "ALERTA SISMO"
            ints = intensidad(pmax * 1000) if evento else "-"
            if alerta: pantalla["l1"] = f"ALERTA SISMO {ints}"
            elif evento: pantalla["l1"] = f"Evento {dur:.0f}s {pmax*1000:.0f}mg"
            else: pantalla["l1"] = f"Reposo {sta*1000:.0f} mg"
            txt = f"\r{estado:<12} |{barra(sta*1000):<25}|"
            txt += f" Vib {sta*1000:5.1f} mg | Pico {pico*1000:5.1f} mg"
            txt += f" | R {r:4.1f} | Int {ints:<6}  "
            decir(txt, fin="")
        t_sig += 1 / FS
        time.sleep(max(0, t_sig - time.time()))

# ============ ARRANQUE ============
if __name__ == "__main__":
    threading.Thread(target=lcd_bucle, daemon=True).start()
    threading.Thread(target=sismo, daemon=True).start()
    listo.wait()
    threading.Thread(target=sniffer, daemon=True).start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        zumbador.alarma = False
        if _dev: _dev.off()
        if _lcd: _lcd.clear()
        decir(f"\nDetenido. Datos guardados en {CARPETA}")
