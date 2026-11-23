import time
from luma.core.interface.serial import bitbang_6800
from luma.lcd.device import hd44780

# Configurar los pines GPIO (numeracion BCM)
# PINS = [D4, D5, D6, D7]. D7 pasa de GPIO24 a GPIO26 (pin fisico 37) porque
# GPIO23/24 (pines 16 y 18) los usa el I2C por software de la MPU6050 (bus 3).
serial = bitbang_6800(RS=15, E=10, PINS=[11, 19, 6, 26])
device = hd44780(serial, width=16, height=2)

inicio = time.time()

try:
    while True:
        segundos = int(time.time() - inicio)
        device.text = f"hello, world!\n{segundos}"
        time.sleep(0.5)
except KeyboardInterrupt:
    device.clear()
