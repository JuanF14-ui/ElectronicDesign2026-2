# 6. Agentes de IA y próximos pasos

## 6.1 Los dos agentes del proyecto

| Agente | Tarea | Estado |
|---|---|---|
| **Agente IA 1: vigía sísmico** | Decidir si un evento de la IMU es un sismo o actividad humana (golpes, pasos, puertas) | Hoy funciona con reglas (STA/LTA + duración sobre umbral). Falta el modelo entrenado |
| **Agente IA 2: conteo de dispositivos** | Estimar cuántos celulares distintos hay, aunque cambien de MAC | Hoy funciona con reglas (persistencia + agrupación por RSSI). Falta la huella de Information Elements |

Cuando los dos funcionen por separado, se unen en el nodo sniffer.

Lo que convierte a cada uno en un **agente** es el ciclo percibir → decidir → actuar:

| Etapa | Agente 1 (sismo) | Agente 2 (dispositivos) |
|---|---|---|
| Percibe | IMU a 50 Hz | Tramas Wi-Fi del ESP32 |
| Decide | Modelo: sismo / no sismo | Agrupa MAC y estima el número de equipos |
| Actúa | Alarma (buzzer), guarda el evento y, a futuro, envía los datos al gateway | Pitido por celular nuevo, guarda el conteo |
| Aprende | Cada evento etiquetado alimenta el reentrenamiento | Se ajustan umbrales con las pruebas |

## 6.2 Decisión sobre el Agente IA 1

| Opción | ¿Sirve? | Motivo |
|---|---|---|
| SeisBench / EQTransformer / PhaseNet | ❌ Solo como referencia | Entrenados con sismómetros profesionales (ruido miles de veces menor que el MEMS), ventanas de 30–60 s a 100 Hz y PyTorch, demasiado pesado para 512 MB |
| **Método MyShake** (Kong et al., 2016) | ✅ Base del agente | Resolvió el mismo problema con acelerómetros de celulares: rasgos simples y una red neuronal diminuta (3-5-1) |
| **Modelo pequeño propio** (árbol de decisión o regresión logística) | ✅ Lo más seguro | Se entrena en el PC con scikit-learn y en la Pi queda como reglas o pesos, sin librerías pesadas |
| PicoClaw como detector | ❌ | Depende de Gemini (internet); con modelos locales no alcanzan los 512 MB (estimado); proyecto en etapa temprana |

**Rasgos que calculará el modelo:**

| Rasgo | Origen | Qué distingue |
|---|---|---|
| IQR de la aceleración | MyShake | Amplitud típica |
| Cruces por cero por segundo | MyShake | Frecuencia: golpes vs. vaivén |
| CAV (velocidad absoluta acumulada) | MyShake | Energía total |
| Duración y fracción sobre umbral | Ya implementado | Golpe aislado vs. sostenido |
| Factor de cresta (pico ÷ RMS) | Propuesto | Golpes repetidos: picos aislados muy altos |
| Número de picos separados | Propuesto | Golpes seguidos (hoy dan falsa alerta) |

**Plan de trabajo:**

| Fase | Trabajo | Dónde |
|---|---|---|
| A. Grabar | Guardar la señal cruda de cada evento (5 s antes del disparo hasta 2 s después del final) | Pi |
| B. Etiquetar | Clases: sacudida, golpe, golpes repetidos, caminar, puerta, objeto que cae, sensor movido. Unos 20–30 ejemplos por clase (estimado) | Pi o Telegram |
| C. Entrenar | Calcular rasgos, entrenar 2–3 modelos pequeños, validación cruzada y matriz de confusión | PC |
| D. Integrar | Copiar el modelo elegido al programa de la Pi | Pi |

## 6.3 Papel de PicoClaw

PicoClaw es un asistente de IA (Gemini) instalado en la Pi, con el que se habla por Telegram. Puede
leer y escribir archivos, ejecutar comandos y programar tareas
([documentación](https://pkg.go.dev/github.com/sipeed/picoclaw@v0.2.3)).

| Uso | ¿Necesita internet? |
|---|---|
| Asistente de desarrollo (crear y ejecutar scripts) | Sí |
| Etiquetar eventos por Telegram durante las pruebas | Sí (solo en pruebas) |
| Resumir los datos guardados | Sí |
| Avisar a rescatistas si en campo hubiera internet | Sí; el sistema debe funcionar igual sin él |

**Seguridad:** su documentación reporta vulnerabilidades (entre ellas inyección de comandos en la
herramienta `exec`) y la consola web no tiene contraseña. Por eso: mantener `allow_from` solo con el
ID de Telegram autorizado, dejar `restrict_to_workspace` activado, no exponer la consola web y
**nunca** darle control de la alarma.

## 6.4 Pendientes

| Pendiente | Prioridad |
|---|---|
| Agente IA 1, fase A: grabar la señal cruda de los eventos | Alta |
| Agente IA 2: huella de Information Elements en el ESP32 | Media |
| Cambiar el enlace UDP/hotspot por **ESP-NOW** (sin router) y construir el gateway (ESP32 + microSD) | Media |
| Envío por broadcast o IP fija, para no reprogramar el ESP32 cada vez que cambia la IP | Media |
| Nodos satélite (3+ ESP32) para trilateración | Baja |
| Etapa de potencia con baterías y medición de consumo | Media |
| BOM con referencias, precios y proveedores | Media |
| Confirmar el pin del buzzer y si es activo o pasivo | Baja |
| Recablear D7 de la LCD al pin 37 | Baja |
| Identificar el equipo con MAC fija F8:43:EF:AA:25:E0 | Baja |
| Subir al repo los scripts que quedaron en `~/.picoclaw/workspace/` | Baja |
| **Cambiar las claves Wi-Fi** que quedaron en el historial público del repositorio | Alta |
| Red por cable USB (modo gadget) para tener acceso sin Wi-Fi | Baja |
| Verificar con el SGC los datos del sismo del 10-ago-2026 usado como motivación | Media |

## Referencias

- Allen, R. (1978). Automatic earthquake recognition and timing from single traces. *BSSA*.
- Kong, Q., Allen, R. M., Schreier, L. y Kwon, Y.-W. (2016). MyShake: A smartphone seismic network for earthquake early warning and beyond. *Science Advances*.
- Trnkoczy, A. Understanding and parameter setting of STA/LTA trigger algorithm. *New Manual of Seismological Observatory Practice (NMSOP)*.
- Wald, D. J. et al. (1999). Relationships between peak ground acceleration, peak ground velocity, and Modified Mercalli Intensity in California. *Earthquake Spectra*.
- Zhu, W. y Beroza, G. C. (2019). PhaseNet: a deep-neural-network-based seismic arrival-time picking method. *Geophysical Journal International*, 216(1), 261–273.
- Mousavi, S. M. et al. (2019). STanford EArthquake Dataset (STEAD). *IEEE Access*.
- Fuentes del proyecto sobre detección de víctimas y conteo por Wi-Fi/BLE: ver el planteamiento inicial (BLESeis, MDPI Sensors 22(19):7502 y 22(21):8433, de-randomización de MAC en *Computer Networks*).
