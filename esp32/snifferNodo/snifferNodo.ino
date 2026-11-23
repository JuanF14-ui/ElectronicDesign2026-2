#include <WiFi.h>
#include <WiFiUdp.h>
#include "esp_wifi.h"
#include "secretos.h"   // WIFI_SSID, WIFI_PASS, IP_RASPBERRY, MACS_SISTEMA (ver secretos_ejemplo.h)

// CAMBIA ESTO EN CADA PLACA: "NODO_1" en la primera, "NODO_2" en la segunda
const char* NOMBRE_NODO = "NODO_1";
const int puertoUDP = 5005;

WiFiUDP udp;
uint8_t myMac[6];

struct Paquete {
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

// Corre en la tarea de Wi-Fi (no es una interrupción): se usa xQueueSend
void snifferCallback(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type == WIFI_PKT_CTRL) return;  // Tramas de control: sin MAC de origen

  const wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  if (!pkt || pkt->rx_ctrl.sig_len < 24) return;  // Cabecera 802.11 incompleta

  uint8_t fc0 = pkt->payload[0];  // Tipo y subtipo
  uint8_t fc1 = pkt->payload[1];  // Banderas (ToDS / FromDS)

  if (type == WIFI_PKT_MGMT && (fc0 == 0x80 || fc0 == 0x50)) return;  // Beacon y probe response: los envía un router
  if (type == WIFI_PKT_DATA && (fc1 & 0x02)) return;                  // FromDS: la transmite un router, no un celular

  const uint8_t* mac = pkt->payload + 10;  // Dirección del transmisor
  if (esDelSistema(mac)) return;           // No contar la Pi ni los nodos

  Paquete p;
  memcpy(p.mac, mac, 6);
  p.tipo = type;
  p.rssi = pkt->rx_ctrl.rssi;
  xQueueSend(colaPaquetes, &p, 0);
}

void setup() {
  Serial.begin(115200);
  colaPaquetes = xQueueCreate(50, sizeof(Paquete));

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // Mantiene la antena despierta todo el tiempo
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  esp_wifi_get_mac(WIFI_IF_STA, myMac);
  Serial.printf("\n%s conectado. MAC de esta placa: %02X:%02X:%02X:%02X:%02X:%02X\n",
                NOMBRE_NODO, myMac[0], myMac[1], myMac[2], myMac[3], myMac[4], myMac[5]);

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

    udp.beginPacket(IP_RASPBERRY, puertoUDP);
    udp.print(mensaje);
    udp.endPacket();
  }
}
