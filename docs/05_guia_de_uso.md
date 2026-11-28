# 5. Guía para reproducir el sistema

Paso a paso para que cualquier integrante del equipo pueda montar y correr CROWDIA.

## 5.1 Preparar la Raspberry Pi (una sola vez)

1. **Alimentación:** cargador de pared de 5 V (≥ 2 A) en el puerto **`PWR IN`**. Con el USB del PC no
   arranca bien.
2. **Entrar a la Pi:** en connect.raspberrypi.com → el dispositivo → *Connect via* → **Remote shell**.
3. **Crear el bus I2C 3** en los pines 29 y 31 (el pin 3 está desoldado). Abrir
   `sudo nano /boot/firmware/config.txt`, borrar cualquier línea anterior con `i2c-gpio` y dejar
   solo esta al final:
   ```
   dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=5,i2c_gpio_scl=6
   ```
   Guardar y reiniciar con `sudo reboot`.
4. **Instalar herramientas:**
   ```
   sudo apt update
   sudo apt install -y i2c-tools python3-smbus python3-gpiozero
   pip3 install luma.lcd --break-system-packages
   ```
   - `i2c-tools` y `python3-smbus`: hablar con la MPU6050.
   - `python3-gpiozero`: manejar el buzzer.
   - `luma.lcd`: manejar la LCD. Con `pip` en Raspberry Pi OS hace falta `--break-system-packages`.
5. **Conectar los periféricos** según el diagrama de
   [02_hardware_y_conexiones.md](02_hardware_y_conexiones.md#22-conexiones-a-la-raspberry-pi-actualizado-el-26-de-noviembre).
6. **Descargar los programas** del repositorio a la Pi:
   ```
   mkdir -p ~/crowdia/pruebas && cd ~/crowdia
   R=https://raw.githubusercontent.com/JuanF14-ui/ElectronicDesign2026-2/main/raspberry
   wget -N $R/crowdia_integrado.py $R/ver_macs.py $R/etiquetar.py
   cd pruebas && wget -N $R/pruebas/mpu_test.py $R/pruebas/prueba_buzzer.py $R/pruebas/pruebaLCD.py
   ```
   `wget -N` descarga el archivo solo si en GitHub hay una versión más nueva.
7. **Probar cada periférico por separado** con la tabla de
   [02_hardware_y_conexiones.md, sección 2.3](02_hardware_y_conexiones.md#23-cómo-probar-cada-periférico).

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
   En la LCD:

   | Línea | Muestra | Ejemplo |
   |---|---|---|
   | 1 | Estado del sismómetro | `Reposo 3 mg` · `Evento 4s 120mg` · `ALERTA SISMO VI` |
   | 2 | Conteo del último minuto | `Cel:2 Eq:3 S5` (celulares estimados, equipos en total, número de scan) · `Sin ESP32  S5` |
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
| `i2cdetect -y 3` vacío | Cableado o falta el overlay | Revisar pines 29/31 y `config.txt` |
| `IndentationError` en Python | Espacios mal copiados | `cat -A archivo.py` para ver Tabs (`^I`); usar 4 espacios |
| `No DFU capable USB device` al subir al ESP32 | Placa equivocada | **ESP32 Dev Module** |
| El ESP32 se queda en `....` | Clave o hotspot en 5 GHz | Revisar la clave; hotspot en 2,4 GHz |
| `[SCAN]` dice "no llegó ningún paquete" o la LCD dice `Sin ESP32` | IP de la Pi cambió, o el ESP32 perdió el hotspot | `hostname -I` y comparar con `secretos.h`; revisar el monitor serie del ESP32 |
| `AVISO: LCD desactivada (No module named 'luma')` | Falta la librería | `pip3 install luma.lcd --break-system-packages` |
| La LCD enciende pero no muestra letras | Contraste | Girar el potenciómetro de V0 |
| `Remote I/O error` al arrancar | La MPU6050 no responde | `i2cdetect -y 3`; revisar pines 29/31 y la línea `dtoverlay` |
| `hostname -I` muestra dos IP `10.x` | Una es la del modo USB | Usar la que está en la misma red que el ESP32 (`ip -4 addr`, interfaz `wlan0`) |
| `Address already in use` | Otro programa usa el puerto 5005 | Cerrar `ver_macs.py` u otro integrado |
| La alerta no se apaga | El sensor se movió | Fijar el sensor (la v3 ya se recupera sola en 1–2 s) |
| `ssh` no resuelve `RaspberryGR7.local` | Windows no resuelve nombres `.local` | Usar la IP |
