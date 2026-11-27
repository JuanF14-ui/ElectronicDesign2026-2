# Recolección fase A del Agente IA 1 (22 nov 2026, 23:39–23:55)

Eventos de la IMU grabados por `raspberry/crowdia_integrado.py` (v4) para entrenar el modelo que
distingue un sismo de la actividad humana. La prueba está explicada en
[P14](../../docs/04_pruebas_y_resultados.md).

## Qué hay

| Archivo | Contenido |
|---|---|
| `indice.csv` | Una fila por evento: lo que decidió la regla actual y la etiqueta |
| `evt_AAAAMMDD_HHMMSS.csv` | La señal de un evento (nombre = fecha y hora del disparo) |

**Columnas de `indice.csv`:**

| Columna | Significado |
|---|---|
| `archivo` | Archivo con la señal |
| `fecha` | Fecha y hora del disparo STA/LTA |
| `fs_hz` | Muestras por segundo (50) |
| `regla_tipo` | Lo que dijo la regla: `sostenido` o `golpe/impulso` |
| `duracion_s` | Duración del evento según STA/LTA |
| `sobre_umbral_s` | Tiempo entre la primera y la última vez que se pasó de 39 mg (duración acotada, Bolt 1973) |
| `fraccion` | Parte de ese tiempo que de verdad estuvo por encima de 39 mg |
| `pico_mg` | Vibración máxima, en milésimas de g |
| `alerta_regla` | `True` si la regla habría dado alarma de sismo |
| `etiqueta` | Lo que realmente se hizo (`sacudida`, `golpe`, ...) |

**Columnas de cada `evt_*.csv`:**

| Columna | Significado |
|---|---|
| `t_s` | Tiempo en segundos respecto al disparo (negativo = los 5 s previos) |
| `ax_g`, `ay_g`, `az_g` | Aceleración de cada eje, en g, ya calibrada |
| `vib_mg` | Vibración sin gravedad (filtro pasa-altos por eje), en mg |

## Resumen

| Etiqueta | Eventos | Nota |
|---|---|---|
| `sacudida` | 15 | 23:41:47–23:47:41 |
| `golpe` | 22 | 23:48:59–23:55:21, **más 2 dudosos a las 23:39** (ver abajo) |

**Por revisar antes de entrenar:**
- `evt_20261122_233921.csv` y `evt_20261122_233957.csv`: etiquetados `golpe`, pero duran 16–18 s y
  se comportan como sacudidas. Probablemente son sacudidas de prueba hechas antes de cambiar de sesión.
- `evt_20261122_235030.csv`: golpe de solo 15,6 mg de pico, casi al nivel del ruido.

Las etiquetas se corrigen en la Pi con `python3 ~/crowdia/etiquetar.py --todas` y luego se vuelve a
subir `indice.csv`.
