#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"
#include <PubSubClient.h>

#include <WiFi.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Configurações FIWARE
const char* SSID = "Rodrigues";
const char* PASSWORD = "kaua1309";
const char* BROKER_MQTT = "20.55.28.240";
const int BROKER_PORT = 1883;
const char* ID_MQTT = "bpm_030";
const char* TOPICO_PUBLISH = "/TEF/bpm032/attrs";

WiFiClient espClient;
PubSubClient MQTT(espClient);

void conectarWiFi() {
  Serial.print("Conectando ao Wi-Fi ");
  WiFi.begin(SSID, PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void conectarMQTT() {
  while (!MQTT.connected()) {
    Serial.print("Conectando ao MQTT... ");
    if (MQTT.connect(ID_MQTT)) {
      Serial.println("conectado!");
    } else {
      Serial.print("falha, rc=");
      Serial.print(MQTT.state());
      Serial.println(" tentando novamente em 2 segundos");
      delay(2000);
    }
  }
}

// Dimensões do display
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display1(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

MAX30105 particleSensor;

const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute;
int beatAvg;

unsigned long lastTempRead = 0;
float temperatureC = 0.0;

unsigned long lastSendTime = 0;
const long sendInterval = 3000;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("Sensor MAX30105 não encontrado. Verifique as conexões.");
    delay(2000);
  }

  particleSensor.setup();
  particleSensor.enableDIETEMPRDY();
  particleSensor.setPulseAmplitudeRed(0x0A);

  if (!display1.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("Erro ao iniciar display OLED");
    while (true);
  }

  display1.clearDisplay();
  display1.setTextSize(4);
  display1.setTextColor(SSD1306_WHITE);

  // Corrigido: Inicializa Wi-Fi e MQTT
  conectarWiFi();
  MQTT.setServer(BROKER_MQTT, BROKER_PORT);
  conectarMQTT();
}

void loop() {
  if (beatAvg > 0) {
    display1.setTextSize(2.9);
    display1.clearDisplay();
    display1.setCursor(0, 0);
    display1.print("BPM: ");
    display1.println(beatAvg);
    display1.print("Temp: ");
    display1.print(temperatureC, 1);
    display1.display();
  } else {
    display1.setTextSize(3);
    display1.clearDisplay();
    display1.setCursor(0, 0);
    display1.print("Coloqueo");
    display1.println(" dedo");
    display1.display();
    temperatureC = 0;
  }

  long irValue = particleSensor.getIR();

  if (irValue > 7000) {
    if (checkForBeat(irValue)) {
      long delta = millis() - lastBeat;
      lastBeat = millis();

      beatsPerMinute = 60 / (delta / 1000.0);

      if (beatsPerMinute < 255 && beatsPerMinute > 20) {
        rates[rateSpot++] = (byte)beatsPerMinute;
        rateSpot %= RATE_SIZE;

        beatAvg = 0;
        for (byte x = 0; x < RATE_SIZE; x++) {
          beatAvg += rates[x];
        }
        beatAvg /= RATE_SIZE;
      }

      Serial.print(beatAvg);
      Serial.println(" BPM");
    }
  } else {
    beatAvg = 0;
  }

  if (millis() - lastTempRead > 5000) {
    temperatureC = particleSensor.readTemperature();
    lastTempRead = millis();
    Serial.print(" | Temp (C): ");
    Serial.println(temperatureC, 1);
  }

  // Corrigido: MQTT com reconexão e envio protegido
  if (!MQTT.connected()) {
    conectarMQTT();
  }

  MQTT.loop();

  if (MQTT.connected() && (millis() - lastSendTime >= sendInterval)) {
    lastSendTime = millis();
    String payload = "b|" + String(beatAvg) + "|t|" + String(temperatureC, 1);
    MQTT.publish(TOPICO_PUBLISH, payload.c_str());
    Serial.println("Dados enviados ao FIWARE:");
    Serial.println(payload);
  }
}
