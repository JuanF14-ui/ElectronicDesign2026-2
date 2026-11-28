# Prueba del buzzer: 3 pitidos cortos y uno largo.
# Conexion: GPIO26 (pin 37) -> resistencia -> base del transistor NPN.
# Ejecutar: python3 prueba_buzzer.py
import time
from gpiozero import PWMOutputDevice

BUZZER_PIN = 26          # GPIO (BCM)
BUZZER_ACTIVO = True     # False si el buzzer es pasivo (necesita un tono)

b = PWMOutputDevice(BUZZER_PIN, frequency=2000, initial_value=0)
nivel = 1.0 if BUZZER_ACTIVO else 0.5

for duracion in (0.1, 0.1, 0.1, 0.6):
    b.value = nivel
    time.sleep(duracion)
    b.value = 0
    time.sleep(0.25)
b.off()
print("Listo: debieron sonar 3 pitidos cortos y uno largo.")
