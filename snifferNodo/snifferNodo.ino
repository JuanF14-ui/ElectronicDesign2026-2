#include <WiFi.h>
#include <WiFiUdp.h>
#include "esp_wifi.h"

// CAMBIA ESTO EN CADA PLACA: "NODO_1" en la primera, "NODO_2" en la segunda
const char* NOMBRE_NODO = "NODO_2"; 

const char* ssid = "LuanFRed";
const char* password = "123456789"; // Pon la clave de tu hotspot
const char* ipRaspberry = "10.171.170.198"; // Verifica que siga siendo la IP de tu Pi
const int puertoUDP = 5005;

WiFiUDP udp;

struct Paquete {
  uint8_t mac[6];
  uint8_t tipo;
  int8_t rssi;
};

QueueHandle_t colaPaquetes;

void IRAM_ATTR snifferCallback(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type == WIFI_PKT_CTRL) return;

  wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  Paquete p;
  memcpy(p.mac, pkt->payload + 10, 6);
  p.tipo = type;
  p.rssi = pkt->rx_ctrl.rssi;

  xQueueSendFromISR(colaPaquetes, &p, NULL);
}

void setup() {
  Serial.begin(115200);
  colaPaquetes = xQueueCreate(50, sizeof(Paquete));

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false); // Mantiene la antena despierta todo el tiempo
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&snifferCallback);
}

void loop() {
  Paquete p;
  while (xQueueReceive(colaPaquetes, &p, 0) == pdTRUE) {
    const char* tipoStr = (p.tipo == WIFI_PKT_MGMT) ? "MGMT" : "DATA";

    char mensaje[64];
    snprintf(mensaje, sizeof(mensaje), "%s,%02X:%02X:%02X:%02X:%02X:%02X,%s,%d",
             NOMBRE_NODO,
             p.mac[0], p.mac[1], p.mac[2], p.mac[3], p.mac[4], p.mac[5],
             tipoStr, p.rssi);

    udp.beginPacket(ipRaspberry, puertoUDP);
    udp.print(mensaje);
    udp.endPacket();
  }
}