# 2. Hardware y conexiones

## 2.1 Componentes en uso

| Componente | Modelo | Función | Notas |
|---|---|---|---|
| Placa principal | **Raspberry Pi Zero 2 W** (FCC ID 2ABCB-RPIZ2) | Procesa la IMU, cuenta dispositivos, corre los agentes y guarda los datos | BCM2710A1, 4 núcleos Cortex-A53 a 1 GHz, **512 MB** de RAM, Wi-Fi 2,4 GHz b/g/n, Bluetooth 4.2/BLE. Sistema: Raspberry Pi OS 13 (Trixie), 64 bits |
| Sniffer Wi-Fi | **ESP32-WROOM-32U** en placa de desarrollo | Captura las tramas Wi-Fi en modo promiscuo | Antena externa por conector IPEX. Chip ESP32-D0WD-V3 (rev. 3.1); puente USB CP210x. MAC: `78:1C:3C:E3:E8:38` |
| IMU | **MPU6050** (módulo GY-521) | Acelerómetro de 3 ejes para detectar sismos | I2C, dirección 0x68. Ruido medido: 2–5 mg |
| Pantalla | LCD 16×2 **HD44780** | Mostrar estado | Conexión en paralelo de 4 bits. Solo probada con `pruebaLCD.py` |
| Alarma | Buzzer con transistor y resistencia | Avisar sismos fuertes y celulares detectados | Probado y funcionando con `crowdia_integrado.py` |
| Alimentación de la Pi | Cargador de pared USB (se usó uno de 33 W) | 5 V en el puerto `PWR IN` | **Con el USB del PC la Pi no arrancaba bien**; con el cargador sí |

## 2.2 Conexiones a la Raspberry Pi

| Elemento | Señal | GPIO (BCM) | Pin físico |
|---|---|---|---|
| MPU6050 | VCC | 3,3 V | 1 |
| MPU6050 | GND | GND | 6 |
| MPU6050 | AD0 (fija la dirección 0x68) | GND | 14 |
| MPU6050 | SDA (I2C por software, bus 3) | 23 | 16 |
| MPU6050 | SCL (I2C por software, bus 3) | 24 | 18 |
| Buzzer | Base del transistor (por la resistencia) | 17 | 11 |
| LCD | RS / E | 15 / 10 | 10 / 19 |
| LCD | D4 / D5 / D6 / D7 | 11 / 19 / 6 / **26** | 23 / 35 / 31 / **37** |

> **Pendiente de confirmar:** el pin real del buzzer (el código usa GPIO17 por defecto) y si el
> buzzer es activo o pasivo.

### ¿Por qué el I2C va en los pines 16 y 18 y no en el 3 y el 5?
Los pines **3, 7, 9 y 27 se desoldaron** de la placa. El pin 3 es el SDA del I2C normal (bus 1), así
que el sensor no respondía (`i2cdetect -y 1` no mostraba nada). La solución fue crear un **bus I2C por
software (bus 3)** en otros dos pines, agregando esta línea a `/boot/firmware/config.txt`:

```
dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=23,i2c_gpio_scl=24
```

Con eso `i2cdetect -y 3` muestra el sensor en la dirección `68`.

### Conflicto de la LCD con el I2C
El código original de la LCD usaba **GPIO24** para D7, el mismo pin que el SCL del bus 3. Se cambió a
**GPIO26 (pin 37)** en `raspberry/pruebas/pruebaLCD.py`. **Hay que mover el cable** del pin 18 al 37.

## 2.3 Conexiones del ESP32

El ESP32 solo necesita la antena IPEX (conectarla **antes** de energizarlo) y un cable USB de datos.
En el IDE de Arduino se programa como **ESP32 Dev Module** (no como "Arduino Nano ESP32").

## 2.4 Red de laboratorio

| Equipo | Red | Dirección |
|---|---|---|
| Hotspot (celular Redmi) | `LuanFRed`, 2,4 GHz | — |
| Raspberry Pi | Wi-Fi del hotspot | IP variable (vistas: 10.26.70.198 y 10.171.170.198). MAC `2C:CF:67:9B:6D:5C` |
| ESP32 | Wi-Fi del hotspot | IP vista: 10.171.170.211 |

**La IP de la Pi cambia cada vez que se reinicia el hotspot.** Antes de programar el ESP32 hay que
consultarla en la Pi con `hostname -I`.

## 2.5 Acceso a la Raspberry Pi

| Método | Estado |
|---|---|
| **Raspberry Pi Connect** (connect.raspberrypi.com → Remote shell) | ✅ Es el método que se usa. Requiere que la Pi tenga internet |
| SSH por Wi-Fi | Funciona si el PC está en la misma red que la Pi |
| SSH por cable USB (modo "gadget") | ⚠️ Se instaló `rpi-usb-gadget`, pero Windows solo ve el **puerto serie** (COMxx), no la red. Pendiente |
| PicoClaw por Telegram | Asistente con IA (Gemini) instalado en la Pi. Ver [06_proximos_pasos.md](06_proximos_pasos.md) |

## 2.6 Lecciones de hardware

| Problema | Solución |
|---|---|
| La Pi no se conectaba al Wi-Fi y el LED quedaba verde fijo | Era la **alimentación**: con cargador de pared en `PWR IN` arrancó de inmediato |
| El puerto USB de datos de la Pi es el del **centro**; `PWR IN` es solo energía | — |
| `i2cdetect` vacío | Pines desoldados → I2C por software en el bus 3 |
| El sensor se movía al sacudir la mesa y daba alertas falsas | **Fijar la MPU6050** a la superficie (cinta doble faz o tornillo) |
| En la Pi Zero el LED verde queda **encendido** en reposo y se apaga con la actividad | Es normal (al revés que en otros modelos) |
