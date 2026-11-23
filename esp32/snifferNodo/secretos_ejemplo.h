// Copia este archivo como "secretos.h" en esta misma carpeta y pon tus datos.
// "secretos.h" está en .gitignore: no se sube al repositorio.
#pragma once

#define WIFI_SSID     "nombre_de_la_red"
#define WIFI_PASS     "clave_de_la_red"
#define IP_RASPBERRY  "192.168.0.100"   // Verificar en la Pi con: hostname -I

// MAC de los equipos del propio sistema (Pi y otros nodos) para no contarlos
// como celulares. Se ven en el monitor serie al arrancar cada placa.
// Si aún no las conoces, deja solo la fila de ceros.
static const uint8_t MACS_SISTEMA[][6] = {
  {0x00, 0x00, 0x00, 0x00, 0x00, 0x00},
};
