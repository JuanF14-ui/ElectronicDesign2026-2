# Prueba de la LCD 16x2 (HD44780) en modo paralelo de 4 bits con la libreria luma.lcd.
# Muestra "hello, world!" y un contador de segundos.
#
# Instalar la libreria (una vez):  pip3 install luma.lcd --break-system-packages
# Ejecutar:                         python3 pruebaLCD.py   (Ctrl + C para salir)
#
# Conexiones (numeracion BCM -> pin fisico):
#   RS = GPIO17 (11)  E = GPIO18 (12)  D4 = GPIO27 (13)  D5 = GPIO22 (15)  D6 = GPIO23 (16)  D7 = GPIO24 (18)
# Ojo: bitbang_6800 esta en luma.core.interface.parallel (no en .serial).
import time
from luma.core.interface.parallel import bitbang_6800
from luma.lcd.device import hd44780

serial = bitbang_6800(RS=17, E=18, PINS=[27, 22, 23, 24])   # PINS = [D4, D5, D6, D7]
device = hd44780(serial, width=16, height=2)

inicio = time.time()

try:
    while True:
        segundos = int(time.time() - inicio)
        device.text = f"hello, world!\n{segundos}"
        time.sleep(0.5)
except KeyboardInterrupt:
    device.clear()
