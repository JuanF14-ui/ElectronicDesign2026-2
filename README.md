# CROWDIA · proyectoDiseno2026-2

Sistema para apoyar la búsqueda de personas tras un sismo: detecta el sismo con una IMU
y cuenta los celulares cercanos con sniffers Wi-Fi, sin internet y con baterías.

![Diagrama de bloques](docs/CROWDIA_diagrama_de_bloques.png)

## Estructura

| Carpeta / archivo | Qué contiene |
|---|---|
| `sniffer/` | ESP32 conectado a una red, captura en modo promiscuo y envía por UDP a la Raspberry Pi |
| `snifferNodo/` | Igual que `sniffer/`, para varios nodos (`NODO_1`, `NODO_2`, ...) |
| `snifferCable/` | ESP32 sin conectarse a ninguna red: salta por los canales 1–13 y envía por USB serie |
| `crowdia/crowdia_integrado.py` | **Programa principal** en la Raspberry Pi: sismómetro + conteo de dispositivos + buzzer + CSV |
| `crowdia/ver_macs.py` | Diagnóstico: lista las MAC que envía el ESP32 durante 60 s |
| `sismo/crowdia_sismo4.py` | Detector sísmico solo (versión anterior al integrado) |
| `sismo/mpu_test.py` | Prueba básica de lectura de la MPU6050 |
| `pruebaLCD.py` | Prueba de la LCD 16×2 (HD44780) |
| `simulaciones/` | Simulaciones LTspice |
| `docs/` | Diagrama de bloques (PNG y SVG) |
| `docs/bitacora/` | Bitácora de trabajo por fecha, con pruebas y resultados |
| `datos/` | Datos de las pruebas (MAC guardadas como hash) |

## Credenciales (antes de compilar los sketches)

Las claves Wi-Fi **no** se suben al repositorio. En `sniffer/` y `snifferNodo/`:

1. Copia `secretos_ejemplo.h` como `secretos.h` en la misma carpeta.
2. Pon el nombre de la red, la clave y la IP de la Raspberry Pi (`hostname -I` en la Pi).
3. `secretos.h` está en `.gitignore`, así que no se sube.

## Filtros de los sniffers

Para no contar equipos que no son celulares, los sketches descartan:

- Tramas de control (no traen la MAC de origen).
- Beacons (`0x80`) y probe responses (`0x50`): los envían los routers.
- Tramas de datos con la bandera FromDS: las transmite el router, no el celular.
- La MAC de la propia placa y las del sistema (`MACS_SISTEMA` en `secretos.h`).

## Pines de la Raspberry Pi Zero 2 W

| Elemento | GPIO (BCM) | Pin físico |
|---|---|---|
| MPU6050 SDA (I2C por software, bus 3) | 23 | 16 |
| MPU6050 SCL (I2C por software, bus 3) | 24 | 18 |
| MPU6050 VCC / GND / AD0 | 3,3 V / GND / GND | 1 / 6 / 14 |
| LCD RS / E | 15 / 10 | 10 / 19 |
| LCD D4 / D5 / D6 / D7 | 11 / 19 / 6 / 26 | 23 / 35 / 31 / 37 |
| Buzzer (base del transistor) | 17 (confirmar) | 11 |

El bus 3 se crea con esta línea en `/boot/firmware/config.txt`:

```
dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=23,i2c_gpio_scl=24
```
