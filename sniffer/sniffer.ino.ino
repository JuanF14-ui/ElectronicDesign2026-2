#include <WiFi.h>
#include <esp_wifi.h>
#include <WiFiUdp.h>

const char* ssid = "lab_control";
const char* password = "lab_control";

const char* rpi_ip = "192.168.43.198"; 
const int rpi_port = 5005;

WiFiUDP udp;
uint8_t myMac[6];

struct DatosPaquete {
  uint8_t mac[6];
  uint8_t tipo;
  int8_t rssi;
};

QueueHandle_t colaPaquetes;

void snifferCallback(void* buf, wifi_promiscuous_pkt_type_t type) {
  const wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  if (!pkt || pkt->rx_ctrl.sig_len < 16) return;

  if (type == WIFI_PKT_CTRL) return;

  if (memcmp(pkt->payload + 10, myMac, 6) == 0) return;

  DatosPaquete datos;
  memcpy(datos.mac, pkt->payload + 10, 6);
  datos.tipo = (uint8_t)type;
  datos.rssi = pkt->rx_ctrl.rssi;

  xQueueSend(colaPaquetes, &datos, 0);
}

void setup() {
  Serial.begin(115200);
  colaPaquetes = xQueueCreate(100, sizeof(DatosPaquete));

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  esp_wifi_get_mac(WIFI_IF_STA, myMac);
  Serial.println("\nConectado. Enviando paquetes por UDP...");

  // Activar modo promiscuo
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&snifferCallback);
}

void loop() {
  DatosPaquete datos;

  // Si hay paquetes en la cola, enviarlos por Wi-Fi a la Raspberry Pi
  while (xQueueReceive(colaPaquetes, &datos, 0) == pdTRUE) {
    char macStr[18];
    sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X",
            datos.mac[0], datos.mac[1], datos.mac[2],
            datos.mac[3], datos.mac[4], datos.mac[5]);

    const char* tipoStr = (datos.tipo == WIFI_PKT_MGMT) ? "MGMT" : "DATA";

    udp.beginPacket(rpi_ip, rpi_port);
    udp.printf("%s,%s,%d", macStr, tipoStr, datos.rssi);
    udp.endPacket();
  }
}