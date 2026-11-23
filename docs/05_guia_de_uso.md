# 5. Guía para reproducir el sistema

Paso a paso para que cualquier integrante del equipo pueda montar y correr CROWDIA.

## 5.1 Preparar la Raspberry Pi (una sola vez)

1. **Alimentación:** cargador de pared de 5 V (≥ 2 A) en el puerto **`PWR IN`**. Con el USB del PC no
   arranca bien.
2. **Entrar a la Pi:** en connect.raspberrypi.com → el dispositivo → *Connect via* → **Remote shell**.
3. **Crear el bus I2C 3** en los pines 16 y 18 (los pines 3 y 5 están desoldados):
   ```
   echo 'dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=23,i2c_gpio_scl=24' | sudo tee -a /boot/firmware/config.txt
   sudo reboot
   ```
4. **Instalar herramientas:**
   ```
   sudo apt update
   sudo apt install -y i2c-tools python3-smbus
   ```
   `gpiozero` (para el buzzer) viene en Raspberry Pi OS; si al correr el programa aparece
   `AVISO: buzzer desactivado`, instalarlo con `sudo apt install -y python3-gpiozero`.
5. **Conectar la MPU6050** según [02_hardware_y_conexiones.md](02_hardware_y_conexiones.md) y
   comprobar que aparece en la dirección 68:
   ```
   i2cdetect -y 3
   ```
6. **Copiar el programa** a la Pi en `~/crowdia/crowdia_integrado.py`. Formas que funcionaron:
   - Pegarlo en `nano ~/crowdia/crowdia_integrado.py` desde el Remote shell.
   - Descargarlo del repositorio con `wget` (archivo *raw* de GitHub).

## 5.2 Programar el ESP32 (cada vez que cambie la IP de la Pi)

1. Consultar la IP actual de la Pi: `hostname -I`.
2. En el IDE de Arduino: *File → Preferences → Additional boards manager URLs*:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`, e instalar
   **esp32 by Espressif Systems** en el *Boards Manager*.
3. Abrir `esp32/snifferNodo/snifferNodo.ino`, copiar `secretos_ejemplo.h` como `secretos.h` en la
   misma carpeta y poner la red, la clave y la IP de la Pi.
4. Conectar la **antena IPEX antes** de energizar.
5. *Tools → Board →* **ESP32 Dev Module**; elegir el puerto COM.
6. *Upload*. Si se queda en `Connecting...`, mantener presionado **BOOT**.
7. *Serial Monitor* a 115200: debe mostrar la conexión, la IP del ESP32, su MAC y "Enviando a…".

## 5.3 Correr el sistema

1. Encender el hotspot (2,4 GHz) y verificar que la Pi y el ESP32 estén conectados.
2. **Sensor fijo** a la mesa y quieto.
3. Comprobar que el puerto 5005 está libre (no debe salir nada):
   ```
   ss -ulpn | grep 5005
   ```
4. Ejecutar:
   ```
   python3 ~/crowdia/crowdia_integrado.py
   ```
5. No tocar la mesa durante la calibración (12 s). Luego aparecen la línea de estado del sismómetro y,
   cada 60 s, la tabla `[SCAN n]`.
6. Detener con `Ctrl + C`.

**Antes de una prueba nueva**, mover los datos viejos para empezar con archivos limpios:
```
mkdir -p ~/crowdia/datos/sesionN
mv ~/crowdia/datos/*_v3.csv ~/crowdia/datos/sesionN/
```

## 5.4 Sacar los datos

| Método | Comando |
|---|---|
| Ver el resumen y copiarlo desde el navegador | `cat ~/crowdia/datos/resumen_v3.csv` |
| Ver solo desde una hora | `awk -F, '$1 >= "2026-11-22 17:00"' ~/crowdia/datos/dispositivos_v3.csv` |
| Copiar la carpeta al PC (PC en la misma red, en PowerShell) | `scp -r gruposiete@IP_DE_LA_PI:~/crowdia/datos $HOME\Downloads\crowdia_datos` |

## 5.5 Cómo hacer una prueba controlada

Usar las ventanas `[SCAN n]` como reloj: cada fase dura 3 ventanas y el cambio se hace justo después
de que aparece el encabezado. Anotar en una tabla qué se hizo en cada fase. El protocolo usado está en
[04_pruebas_y_resultados.md](04_pruebas_y_resultados.md#p13-prueba-controlada-22-nov-21032122).

**No poner en modo avión el celular del hotspot:** si se apaga, la Pi y el ESP32 pierden la red.

Para simular un sismo: **empujar la mesa de lado a lado de forma continua durante 3–5 s**. Un golpe
no es un sismo.

## 5.6 Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| La Pi no aparece en el hotspot | Alimentación | Cargador de pared en `PWR IN` |
| `i2cdetect -y 3` vacío | Cableado o falta el overlay | Revisar pines 16/18 y `config.txt` |
| `IndentationError` en Python | Espacios mal copiados | `cat -A archivo.py` para ver Tabs (`^I`); usar 4 espacios |
| `No DFU capable USB device` al subir al ESP32 | Placa equivocada | **ESP32 Dev Module** |
| El ESP32 se queda en `....` | Clave o hotspot en 5 GHz | Revisar la clave; hotspot en 2,4 GHz |
| `[SCAN]` dice "no llegó ningún paquete" | IP de la Pi cambió | `hostname -I` y reprogramar el ESP32 |
| `Address already in use` | Otro programa usa el puerto 5005 | Cerrar `ver_macs.py` u otro integrado |
| La alerta no se apaga | El sensor se movió | Fijar el sensor (la v3 ya se recupera sola en 1–2 s) |
| `ssh` no resuelve `RaspberryGR7.local` | Windows no resuelve nombres `.local` | Usar la IP |
