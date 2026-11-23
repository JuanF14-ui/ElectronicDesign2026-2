# 4. Pruebas y resultados

Registro cronológico de todas las pruebas: qué se hizo, qué salió, qué se concluyó y qué se cambió.
Los datos crudos están en [`datos/`](../datos/).

**Resumen de resultados (para el inciso 4):**

| Aspecto | Resultado | Prueba |
|---|---|---|
| Ruido del acelerómetro en reposo | 1,8–4,9 mg (≈ 3 mg con buena calibración) | P3, P4, P6 |
| Golpes aislados | 7 de 7 clasificados como golpe, sin alerta, con picos de hasta 924 mg | P13 |
| Sacudidas sostenidas | 2 de 3 con alerta en la prueba controlada; 2 de 2 en la sesión 1 | P11, P13 |
| Golpes repetidos | 2 de 2 dieron **falsa alerta** | P13 |
| Línea base de dispositivos (sin equipos activos) | 0 celulares falsos | P12, P13 |
| Sobreconteo por MAC aleatoria | Sin agrupar: hasta +7 sobre lo real (y hasta 21 MAC en un minuto). Con agrupación: +0 a +2 | P11–P13 |
| Vecinos (otra casa) | Llegan con −70 a −96 dBm; ninguno se contó con el umbral de −65 dBm | P11 |
| Saber en qué habitación está un equipo | **No es posible** con un receptor: el RSSI se superpone (−47 a −62 dBm afuera vs. −55 a −59 adentro) | P13 |

---

## P1. Arranque y diagnóstico de la Raspberry Pi (8–9 nov)

**Problema:** la Pi no se conectaba al hotspot y el LED verde quedaba fijo.
**Causa:** alimentación insuficiente desde el USB del PC. Con un **cargador de pared** en `PWR IN` se
conectó de inmediato.

**Diagnóstico del sistema** (por el Remote shell de Raspberry Pi Connect):

| Comando | Resultado | Lectura |
|---|---|---|
| `free -h` | 415 MiB en total, 207 MiB usados, 105 MiB de swap usados | La memoria anda justa; el escritorio gráfico ocupa buena parte |
| `df -h /` | 14 GB, 8,0 GB libres | Espacio de sobra para datos |
| `sudo dmesg \| grep brcmfmac` | Firmware BCM43430/1, versión 7.45.96.s1 | No está en la lista oficial de Nexmon → el modo monitor de la Pi es incierto; se decidió capturar con ESP32 |

## P2. Conexión del sensor por I2C (9 nov)

| Paso | Resultado |
|---|---|
| `i2cdetect -y 1` (bus normal, pines 3 y 5) | Tabla vacía: el sensor no respondía |
| Revisión física | Los pines 3, 7, 9 y 27 estaban **desoldados** |
| Bus I2C por software en GPIO23/24 (`dtoverlay=i2c-gpio,bus=3,...`) | `i2cdetect -y 3` mostró **0x68** ✅ |

## P3. Lectura del sensor con `mpu_test.py` (9–10 nov)

| Medida (sensor quieto) | Valor | Lectura |
|---|---|---|
| Aceleración X, Y, Z | +0,05 / +0,04 / +0,91 a +0,94 g | Z debería ser 1,00 g: desfase de −73 mg, dentro de lo que permite la hoja de datos (±80 mg) |
| Giroscopio | −1,0 / −2,2 / −0,7 °/s | Desfase normal en reposo |
| Temperatura | 24,6–25,1 °C | Temperatura interna del chip |

## P4. Sismómetro v1 (10 nov) — [`historial/crowdia_sismo.py`](../raspberry/historial/crowdia_sismo.py)

| Prueba | Vibración | Pico | STA/LTA | Estado |
|---|---|---|---|---|
| Quieto | 2,9 mg | 8,3 mg | 1,0 | Reposo |
| Golpes en la mesa | 14,1 mg | 62,2 mg | 1,7 | Vibración |
| Sacudida fuerte | 57,1 mg | 365,2 mg | 2,9 | **Vibración** (nunca llegó a "POSIBLE SISMO") |

- El ruido de 2,9 mg coincide con lo esperado por la hoja de datos (400 µg/√Hz con ~44 Hz de ancho
  de banda ≈ 3 mg; cálculo aproximado).
- **Fallo:** el LTA seguía creciendo durante la sacudida y la relación STA/LTA nunca llegaba a 3.
- **Cambio:** congelar el LTA durante el evento y usar los parámetros recomendados (→ v2).

## P5. Sismómetro v2 (17 nov) — [`historial/crowdia_sismo2.py`](../raspberry/historial/crowdia_sismo2.py)

| Evento | Duración | Pico | Intensidad | Alerta | ¿Correcto? |
|---|---|---|---|---|---|
| Sacudida | 6,6 s | 141 mg | VI | SÍ | ✅ |
| Golpe | 1,1 s | 44 mg | V | SÍ | ❌ falsa alarma |
| Golpe | 0,9 s | 61 mg | V | SÍ | ❌ falsa alarma |

- Ruido medido: 4,9 mg. La calibración duraba menos de 3 s y captaba la vibración de presionar Enter.
- **Cambio:** calibración de 10 s y **duración mínima de 2 s** para alertar (→ v3).

## P6. Sismómetro v3 (21 nov) — [`historial/crowdia_sismo3.py`](../raspberry/historial/crowdia_sismo3.py)

Calibración: gravedad 0,924 g, ruido 2,3 mg, 48 Hz. Se dieron **solo golpes** (suaves y duros):

| Evento | Resultado | ¿Correcto? |
|---|---|---|
| 7,3 s, pico 187 mg | sostenido, ALERTA | ❌ |
| 4,4 s, pico 223 mg | sostenido, ALERTA | ❌ |
| 0,9 s, pico 41 mg | golpe, sin alerta | ✅ |
| 4,3 s, pico 162 mg | sostenido, ALERTA | ❌ |
| 1,0 s, pico 38 mg | golpe, sin alerta | ✅ |
| 6,7 s, pico 203 mg | sostenido, ALERTA | ❌ |

- **Causa 1:** con los golpes fuertes el sensor se movía un poco; la referencia de gravedad quedaba
  desplazada unos mg y el evento no terminaba (STA ≈ 6 mg, justo sobre el umbral de fin). La
  "duración" medía cuánto tardaba en apagarse el promedio, no cuánto duraba la sacudida.
- **Causa 2:** |a| − g casi no ve las sacudidas horizontales.
- **Cambios** (→ v4): gravedad restada por eje, duración y fracción **sobre umbral**.

## P7. Puesta en marcha del ESP32 (22 nov)

| Paso | Resultado |
|---|---|
| Subir el sketch con la placa "Arduino Nano ESP32" | Error `No DFU capable USB device available` |
| Cambiar a **ESP32 Dev Module** | Subió bien (COM13). Chip ESP32-D0WD-V3, MAC 78:1C:3C:E3:E8:38 |
| Monitor serie | Conectado a `LuanFRed`, IP 10.171.170.211, enviando a 10.171.170.198:5005 |
| Receptor UDP de prueba en la Pi | Llegó `NODO_1,2C:CF:67:9B:6D:5C,DATA,-46` |

**Hallazgo:** el primer paquete capturado fue **la propia Raspberry Pi**. El sistema se cuenta a sí
mismo → se agregó la lista `MACS_SISTEMA`.

## P8. Programa `integrado.py` de PicoClaw (22 nov) — [`historial/integrado_picoclaw.py`](../raspberry/historial/integrado_picoclaw.py)

En el cuarto había: celular Redmi (hotspot), iPhone 17, PC Acer Nitro y tablet Redmi Pad Pro.

| Ventana | Dispositivos contados |
|---|---|
| 1 / 2 / 3 / 4 | 2 / 3 / 5 / 2 (incluyendo la Pi) |

- El sismómetro quedó en **"EVENTO" todo el tiempo** con STA/LTA de 60–70 (STA y LTA arrancaban en 0).
- Los conteos variaban mucho: el ESP32, conectado al hotspot, solo escucha un canal, y los equipos
  inactivos envían pocas tramas.

## P9. Identificación de MAC con `ver_macs.py` (22 nov)

| MAC | Paquetes | RSSI máx. | Lectura |
|---|---|---|---|
| 2C:CF:67:9B:6D:5C | 80 | −29 | Raspberry Pi |
| 52:A6:1A:…, 82:70:12:…, B2:2D:1F:… | 8–9 | −32 / −33 | MAC aleatorias muy cerca: búsquedas de celulares (pueden ser menos de 3 equipos) |
| 3C:AF:B7:75:51:CA | 11 | −51 | MAC fija: la tablet (se le quitó la MAC aleatoria) |
| 5 MAC más | 1–5 | −75 a −91 | Débiles: equipos de los vecinos |

Más tarde se identificó la MAC del PC (94:08:53:47:F4:A1): aparece muy poco porque el PC está
conectado al Wi-Fi de la casa, en otro canal. La MAC fija F8:43:EF:AA:25:E0 (−51 a −64 dBm) sigue sin
identificar.

## P10. Integrado v1 (22 nov, 14:57–15:04) — [`historial/crowdia_integrado_v1.py`](../raspberry/historial/crowdia_integrado_v1.py)

- Conteos por ventana: 2 en una primera corrida y luego 1, 2, 2, 2, 1, 2 en la segunda (filas de 8
  columnas en `sesion1_dispositivos.csv`; por eso la ventana 1 aparece dos veces).
- **Fallo:** después de sacudir la mesa, la alerta quedó **pegada** con vibraciones de 355–378 mg y de
  1570–1590 mg. Esos valores corresponden a que el sensor quedó **inclinado unos 20°** y luego **casi
  volteado**. La gravedad calibrada también cambió entre corridas (0,951 g y 0,898 g): el sensor no
  estaba fijo.
- **Cambio** (→ v2): filtro pasa-altos de la gravedad por eje, siempre activo.

## P11. Sesión 1 con integrado v2 + buzzer (22 nov, 16:22–16:34)

Datos: [`sesion1_dispositivos.csv`](../datos/2026-11-22/sesion1_dispositivos.csv) (filas de 9 columnas) y [`sesion1_sismos.csv`](../datos/2026-11-22/sesion1_sismos.csv).

**Sismos:**

| Hora | Tipo | Sobre umbral | Pico | Alerta | ¿Correcto? |
|---|---|---|---|---|---|
| 16:23:00 | sostenido | 4,2 s (64 %) | 1230 mg | SÍ | ✅ sacudida |
| 16:27:35 | golpe | 0,1 s (4 %) | 80 mg | no | ✅ |
| 16:33:25 | golpe | 0 s | 21 mg | no | ✅ |
| 16:33:41 | sostenido | 6,2 s (73 %) | 750 mg | SÍ | ✅ sacudida |

Ya no se quedó pegado. El buzzer funcionó.

**Dispositivos:**
- Los equipos de la casa vecina (presentes en **todas** las ventanas, −70 a −96 dBm) **no se contaron**.
- Desde las 16:24 aparecieron 2 a 6 MAC aleatorias "de un solo uso" por ventana (1–6 paquetes, señal
  parecida). En la ventana 6, seis MAC distintas llegaron con −55 dBm: casi seguro un solo equipo.
- Con ~4 equipos reales el sistema contó **hasta 9**.
- Reprocesando estos datos con la lógica de la v3, el conteo pasa a 3, 3, 3, 4, 3, 2, 2, 3, 2, 2, 2, 2, 5.
- **Cambio** (→ v3): persistencia y agrupación de MAC aleatorias.

## P12. Sesión 2 con integrado v3 (22 nov, 17:07–17:26, sin protocolo)

Datos: [`sesion2_resumen_v3.csv`](../datos/2026-11-22/sesion2_resumen_v3.csv) y [`sesion2_sismos_v3.csv`](../datos/2026-11-22/sesion2_sismos_v3.csv).

| Medida | Sin agrupar | Estimado (v3) |
|---|---|---|
| Promedio por ventana | 4,2 | 2,2 |
| Máximo | 21 (17:14) | 4 (17:18) |

- Ventanas 2–6: **0 celulares**, con los celulares aparentemente en modo avión.
- Ventana 8 (17:14): **28 MAC vistas y 21 sin agrupar** → estimado 2. Al salir del modo avión, un
  celular busca redes de forma intensa cambiando de MAC en cada búsqueda.
- Sismo a las 17:15:47: sostenido (4,6 s sobre umbral) pero **sin alerta**, porque solo el 15 % del
  tiempo superó 39 mg (mínimo 20 %).
- No se anotaron las horas de cada acción, así que no se pudo armar la tabla de verdad → P13.

## P13. Prueba controlada (22 nov, 21:03–21:22)

Datos: [`prueba_controlada_resumen_v3.csv`](../datos/2026-11-22/prueba_controlada_resumen_v3.csv), [`prueba_controlada_sismos_v3.csv`](../datos/2026-11-22/prueba_controlada_sismos_v3.csv) y [`prueba_controlada_tablet_estable.csv`](../datos/2026-11-22/prueba_controlada_tablet_estable.csv).

**Montaje:** ESP32, Pi y sensor fijos. En el cuarto: tablet Redmi Pad Pro y el celular Redmi
(hotspot, que el sistema no cuenta por ser el router). En la habitación de al lado: dos celulares y un
Smart TV. Cada fase dura 3 ventanas de 60 s; los cambios se hicieron al aparecer el `[SCAN]` indicado.

**Protocolo y resultados de dispositivos:**

| Fase | Ventanas | Tablet | Real* | Sin agrupar | Estimado | Celulares estimados |
|---|---|---|---|---|---|---|
| 1. Línea base | 1–3 | Modo avión | 1 | 1, 1, 1 | 1, 1, 1 | **0, 0, 0** |
| 2. Activa (MAC fija) | 4–6 | En uso, en ajustes de Wi-Fi | 2 | 6, 7, 9 | 2, 3, 2 | 1, 3, 2 |
| 3. En reposo | 7–9 | Pantalla apagada | 2 | 4, 4, 3 | 3, 3, 2 | 2, 3, 2 |
| 4. MAC aleatoria | 10–12 | En uso | 2 | 4, 3, 4 | 3, 3, 4 | 2, 2, 2 |
| 5. Otra habitación | 13–15 | En el cuarto de al lado | 1 | 4, 3, 5 | 1, 3, 3 | 1, 2, 2 |
| 6. Sismos | 16–18 | Modo avión | 1 | 4, 3, 1 | 3, 3, 1 | 2, 2, 0 |

\*Real = 1 equipo fijo de fondo (el que aparece en la línea base) más la tablet cuando está en el cuarto.

**RSSI de la tablet** (MAC aleatoria `f3aee4932c0b`, conectada al hotspot):

| Ventana | Fase | Dónde | Paquetes | RSSI |
|---|---|---|---|---|
| 11 | 4 | En el cuarto | 140 | −59 |
| 12 | 4 | En el cuarto | 79 | −55 |
| 13 | 5 | Al lado | 191 | −53 |
| 14 | 5 | Al lado | 285 | **−47** |
| 15 | 5 | Al lado | 41 | −62 |

**Sismos** (en las fases 3 y 4 se dieron golpes seguidos "al azar"; en la fase 6, sacudidas y golpes):

| Hora | Fase | Tipo | Sobre umbral | Fracción | Pico | Alerta | ¿Correcto? |
|---|---|---|---|---|---|---|---|
| 21:04:06 | 1 | golpe | 0,2 s | 6 % | 142 mg | no | ✅ |
| 21:11:26 | 3 | sostenido | 5,2 s | 41 % | 252 mg | SÍ | ❌ golpes repetidos |
| 21:14:46 | 4 | sostenido | 5,9 s | 50 % | 462 mg | SÍ | ❌ golpes repetidos |
| 21:15:02 | 4 | golpe | 0 s | 0 % | 25 mg | no | ✅ |
| 21:20:30 | 6 | sostenido | 6,3 s | 21 % | 77 mg | SÍ | ✅ sacudida |
| 21:20:43 | 6 | golpe | 0,4 s | 14 % | 679 mg | no | ✅ |
| 21:20:47 | 6 | golpe | 0,4 s | 14 % | 386 mg | no | ✅ |
| 21:20:54 | 6 | golpe | 0,4 s | 14 % | 924 mg | no | ✅ |
| 21:21:26 | 6 | golpe | 0,3 s | 12 % | 732 mg | no | ❓ posiblemente una sacudida muy corta |
| 21:21:50 | 6 | sostenido | 7,1 s | 41 % | 110 mg | SÍ | ✅ sacudida |

**Conclusiones de la prueba controlada:**
1. **Línea base limpia:** sin dispositivos activos, 0 celulares estimados.
2. **La agrupación funciona:** sin agrupar el error llegó a +7; agrupado, +0 a +2 sobre lo real.
3. **"MAC fija" en Android no cambia lo que ve el sniffer:** al buscar redes, la tablet usa MAC
   aleatoria igual. La opción solo afecta la conexión a la red.
4. **No se pueden separar habitaciones con un receptor:** en el cuarto de al lado la tablet llegó con
   igual o más señal que dentro. Los 1–2 celulares de más en las fases 3 y 6 probablemente son los de
   la habitación vecina. El sistema mide "personas en la zona", no "en este cuarto". Para ubicar se
   necesitan nodos satélite (trilateración).
5. **Golpes aislados:** bien clasificados aunque tengan picos enormes (hasta 924 mg).
6. **Golpes repetidos:** la regla de duración no los distingue de un sismo → es el caso que debe
   resolver el **Agente IA 1**.
7. La intensidad de las sacudidas a mano sale muy alta (hasta IX+) porque una mesa sacudida no es el
   suelo: la escala de Wald se aplica a la aceleración del terreno.

## Pruebas pendientes

- Repetir la prueba controlada con **dos o más celulares** propios en el cuarto.
- Línea base larga (≥ 30 min) para caracterizar el fondo de la vecindad.
- Medir el consumo de corriente de la Pi y del ESP32 (para dimensionar las baterías).
- Grabar la señal cruda de cada evento sísmico (fase A del Agente IA 1).
