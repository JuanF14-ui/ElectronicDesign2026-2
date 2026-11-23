#include <WiFi.h>
#include <esp_wifi.h>
#include <WiFiUdp.h>
#include "secretos.h"   // WIFI_SSID, WIFI_PASS, IP_RASPBERRY, MACS_SISTEMA (ver secretos_ejemplo.h)

const int rpi_port = 5005;

WiFiUDP udp;
uint8_t myMac[6];

struct DatosPaquete {
  uint8_t mac[6];
  uint8_t tipo;
  int8_t rssi;
};

QueueHandle_t colaPaquetes;

// Devuelve true si la MAC es de esta placa o de otro equipo del sistema
bool esDelSistema(const uint8_t* mac) {
  if (memcmp(mac, myMac, 6) == 0) return true;
  for (size_t i = 0; i < sizeof(MACS_SISTEMA) / 6; i++) {
    if (memcmp(mac, MACS_SISTEMA[i], 6) == 0) return true;
  }
  return false;
}

void snifferCallback(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type == WIFI_PKT_CTRL) return;

  const wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  if (!pkt || pkt->rx_ctrl.sig_len < 24) return;

  uint8_t fc0 = pkt->payload[0];
  uint8_t fc1 = pkt->payload[1];

  if (type == WIFI_PKT_MGMT && (fc0 == 0x80 || fc0 == 0x50)) return;  // Beacon / probe response de routers
  if (type == WIFI_PKT_DATA && (fc1 & 0x02)) return;                  // FromDS: la transmite un router

  const uint8_t* mac = pkt->payload + 10;
  if (esDelSistema(mac)) return;

  DatosPaquete datos;
  memcpy(datos.mac, mac, 6);
  datos.tipo = (uint8_t)type;
  datos.rssi = pkt->rx_ctrl.rssi;

  xQueueSend(colaPaquetes, &datos, 0);
}

void setup() {
  Serial.begin(115200);
  colaPaquetes = xQueueCreate(100, sizeof(DatosPaquete));

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  esp_wifi_get_mac(WIFI_IF_STA, myMac);
  Serial.printf("\nConectado. MAC de esta placa: %02X:%02X:%02X:%02X:%02X:%02X\n",
                myMac[0], myMac[1], myMac[2], myMac[3], myMac[4], myMac[5]);
  Serial.println("Enviando paquetes por UDP...");

  // Activar modo promiscuo
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&snifferCallback);
}

void loop() {
  DatosPaquete datos;

  // Si hay paquetes en la cola, enviarlos por Wi-Fi a la Raspberry Pi
  while (xQueueReceive(colaPaquetes, &datos, 0) == pdTRUE) {
    char macStr[18];
    snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
             datos.mac[0], datos.mac[1], datos.mac[2],
             datos.mac[3], datos.mac[4], datos.mac[5]);

    const char* tipoStr = (datos.tipo == WIFI_PKT_MGMT) ? "MGMT" : "DATA";

    udp.beginPacket(IP_RASPBERRY, rpi_port);
    udp.printf("%s,%s,%d", macStr, tipoStr, datos.rssi);
    udp.endPacket();
  }
}
