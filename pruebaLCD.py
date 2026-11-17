import time
from luma.core.interface.serial import bitbang_6800
from luma.lcd.device import hd44780

# Configurar los pines GPIO (numeracion BCM)
serial = bitbang_6800(RS=15, E=10, PINS=[11, 19, 6, 24])
device = hd44780(serial, width=16, height=2)

inicio = time.time()

try:
    while True:
        segundos = int(time.time() - inicio)
        device.text = f"hello, world!\n{segundos}"
        time.sleep(0.5)
except KeyboardInterrupt:
    device.clear()
