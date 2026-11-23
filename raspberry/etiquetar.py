# CROWDIA - Etiquetado de eventos (Agente IA 1, fase B)
# Recorre los eventos grabados por crowdia_integrado.py y permite ponerles o corregirles la etiqueta.
#
# Uso:
#   python3 etiquetar.py            -> etiqueta los eventos que no tienen etiqueta
#   python3 etiquetar.py --todas    -> revisa todos (para corregir)
#   python3 etiquetar.py --resumen  -> solo muestra cuantos eventos hay por etiqueta
import csv, os, argparse
from collections import Counter

CARPETA_EVT = os.path.expanduser("~/crowdia/eventos")
INDICE = os.path.join(CARPETA_EVT, "indice.csv")
ETIQUETAS = ["sacudida", "golpe", "golpes_repetidos", "caminar", "puerta",
             "objeto_cae", "sensor_movido", "otro"]

ap = argparse.ArgumentParser()
ap.add_argument("--todas", action="store_true", help="revisar todos los eventos")
ap.add_argument("--resumen", action="store_true", help="solo mostrar el conteo por etiqueta")
args = ap.parse_args()

if not os.path.exists(INDICE):
    print(f"No hay eventos todavia ({INDICE} no existe).")
    raise SystemExit

with open(INDICE, newline="") as f:
    lector = csv.DictReader(f)
    columnas = lector.fieldnames
    filas = list(lector)

def resumen():
    c = Counter(fila["etiqueta"] or "(sin etiqueta)" for fila in filas)
    print(f"\nEventos grabados: {len(filas)}")
    for etiqueta, n in sorted(c.items(), key=lambda x: -x[1]):
        print(f"  {etiqueta:<18} {n}")

if args.resumen:
    resumen()
    raise SystemExit

pendientes = filas if args.todas else [fila for fila in filas if not fila["etiqueta"]]
print(f"{len(pendientes)} eventos por revisar.")

try:
    for fila in pendientes:
        frac = float(fila["fraccion"] or 0) * 100
        print(f"\n{fila['archivo']} | {fila['fecha']} | regla: {fila['regla_tipo']}"
              f" | {fila['duracion_s']} s | sobre umbral {fila['sobre_umbral_s']} s ({frac:.0f}%)"
              f" | pico {fila['pico_mg']} mg | etiqueta actual: {fila['etiqueta'] or '-'}")
        for i, e in enumerate(ETIQUETAS, 1):
            print(f"  {i}. {e}")
        r = input("Numero de la etiqueta (Enter = dejar igual, q = salir): ").strip().lower()
        if r == "q":
            break
        if r.isdigit() and 1 <= int(r) <= len(ETIQUETAS):
            fila["etiqueta"] = ETIQUETAS[int(r) - 1]
except (KeyboardInterrupt, EOFError):
    print()

with open(INDICE, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=columnas)
    w.writeheader()
    w.writerows(filas)
print("Etiquetas guardadas.")
resumen()
