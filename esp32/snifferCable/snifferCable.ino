#include <WiFi.h>
#include "esp_wifi.h"

struct Paquete {
  uint8_t mac[6];
  uint8_t tipo;
  uint8_t subtipo;
  int8_t rssi;
};

QueueHandle_t colaPaquetes;
int canalActual = 1;
unsigned long ultimoCambioCanal = 0;

// Corre en la tarea de Wi-Fi (no es una interrupción): se usa xQueueSend
void snifferCallback(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type == WIFI_PKT_CTRL) return; // Ignorar tramas de control sin MAC origen

  wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  if (!pkt || pkt->rx_ctrl.sig_len < 24) return; // Cabecera 802.11 incompleta
  if (type == WIFI_PKT_DATA && (pkt->payload[1] & 0x02)) return; // FromDS: la transmite un router
  Paquete p;
  memcpy(p.mac, pkt->payload + 10, 6); // Dirección MAC del transmisor
  p.tipo = type;
  p.subtipo = pkt->payload[0];
  p.rssi = pkt->rx_ctrl.rssi;

  xQueueSend(colaPaquetes, &p, 0);
}

void setup() {
  Serial.begin(115200);
  colaPaquetes = xQueueCreate(50, sizeof(Paquete));

  WiFi.mode(WIFI_STA);
  WiFi.disconnect(); // No se conecta a ninguna red, queda libre para escanear
  delay(100);

  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&snifferCallback);
  esp_wifi_set_channel(canalActual, WIFI_SECOND_CHAN_NONE);
}

void loop() {
  // Saltar de canal cada 250 ms para cubrir todo el espectro 2.4 GHz
  if (millis() - ultimoCambioCanal >= 250) {
    ultimoCambioCanal = millis();
    canalActual = (canalActual % 13) + 1;
    esp_wifi_set_channel(canalActual, WIFI_SECOND_CHAN_NONE);
  }

  // Leer paquetes de la cola y enviarlos por USB
  Paquete p;
  while (xQueueReceive(colaPaquetes, &p, 0) == pdTRUE) {
    const char* tipoStr = "DATA";
    if (p.tipo == WIFI_PKT_MGMT) {
      if (p.subtipo == 0x80) tipoStr = "ROUTER";
      else if (p.subtipo == 0x40) tipoStr = "SONDEO";
      else tipoStr = "MGMT";
    }

    char macStr[18];
    snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
             p.mac[0], p.mac[1], p.mac[2], p.mac[3], p.mac[4], p.mac[5]);

    Serial.printf("%s,%s,%d\n", macStr, tipoStr, p.rssi);
  }
}