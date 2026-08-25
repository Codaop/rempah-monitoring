#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include <max6675.h>
#include <ESP32Servo.h>
#include "HX711.h"
#include "esp_timer.h"

// =================================================
// PIN RELAY & ENUM BUZZER
// Harus paling awal — dipakai callback hardware timer
// (pematikTimerCallback) yang tidak mendapat auto-prototype
// dari Arduino IDE.
// =================================================
#define RELAY_POMPA    1
#define RELAY_SOLENOID 2
#define RELAY_PEMATIK  9

enum ModeBuzzer {
  BUZZER_TIDAK_AKTIF,
  BUZZER_AIR_HABIS,
  BUZZER_PEMATIK,
  BUZZER_SISTEM_MATI
};

ModeBuzzer modeBuzzer = BUZZER_TIDAK_AKTIF;

// =================================================
// WIFI
// =================================================
const char* WIFI_SSID = "tahubulat";
const char* WIFI_PASSWORD = "bay12345";


// =================================================
// MQTT HIVEMQ CLOUD
// =================================================
const char* MQTT_BROKER =
  "bde4a0fdcf30401db2125620c5950fa9.s1.eu.hivemq.cloud";

const int MQTT_PORT = 8883;

const char* MQTT_USERNAME =
  "rempah_hivemq";

const char* MQTT_PASSWORD =
  "@rempah1234";


// =================================================
// DEVICE
// =================================================
const char* DEVICE_ID =
  "dc9b3ba4-1985-458e-94d4-d8f8c69c1d95";

const char* MQTT_CLIENT_ID =
  "client-dc9b3ba4-1985-458e-94d4-d8f8c69c1d95";


// =================================================
// MQTT TOPICS
// =================================================
String topicTelemetry =
  "rempah/" + String(DEVICE_ID) + "/telemetry";

String topicState =
  "rempah/" + String(DEVICE_ID) + "/state";

String topicCommand =
  "rempah/" + String(DEVICE_ID) + "/command";


// =================================================
// MQTT CLIENT
// =================================================
WiFiClientSecure secureClient;
PubSubClient mqttClient(secureClient);


// =================================================
// TIMER MQTT
// =================================================
unsigned long waktuTelemetryTerakhir = 0;

const unsigned long INTERVAL_TELEMETRY = 5000;

// TIMER RECONNECT MQTT (NON-BLOCKING)
unsigned long waktuMQTTTerakhir = 0;
const unsigned long INTERVAL_MQTT = 10000;

unsigned long tetesanTerakhirTelemetry = 0;


// =================================================
// MODE DEVICE
// =================================================
String modeDevice = "IDLE";

// =================================================
// MAX6675 SENSOR 1 - BOILER
// =================================================
#define SCK_PIN_1 12
#define SO_PIN_1  13
#define CS_PIN_1  14

MAX6675 thermocouple1(SCK_PIN_1, CS_PIN_1, SO_PIN_1);


// =================================================
// MAX6675 SENSOR 2 - PENDINGIN
// =================================================
#define SCK_PIN_2 4
#define CS_PIN_2  5
#define SO_PIN_2  6

MAX6675 thermocouple2(SCK_PIN_2, CS_PIN_2, SO_PIN_2);


// =================================================
// HX711 LOAD CELL
// =================================================
#define HX711_DT_PIN  17
#define HX711_SCK_PIN 15

HX711 scale;

const long RAW_KOSONG = 31168;
const long RAW_BEBAN  = 113800;
const float BERAT_REFERENSI = 6.05;

long rawLoadCell = 0;
float beratKg = 0;
float beratGram = 0;
bool loadCellValid = false;

unsigned long waktuLoadCellTerakhir = 0;
const unsigned long INTERVAL_LOAD_CELL = 1000;


// Timer hardware: paksa relay pematik OFF tepat setelah DURASI_PEMATIK.
// Callback berjalan di task terpisah — blokir di loop() TIDAK menahannya.
esp_timer_handle_t pematikTimer = nullptr;
volatile bool pematikHardOff = false;   // true = yang mematikan adalah timer

// Dipanggil esp_timer dari task prioritas tinggi — DIJAMIN jalan walau
// loop() sedang diblokir (baca HX711, reconnect MQTT, dsb.).
void IRAM_ATTR pematikTimerCallback(void* arg) {
  gpio_set_level((gpio_num_t)RELAY_PEMATIK, 0);  // paksa relay OFF
  pematikHardOff = true;
}


// =================================================
// SENSOR INFRARED - PENGHITUNG TETESAN
// =================================================
#define IR_PIN 7

unsigned long jumlahTetesan = 0;

int statusIRSebelumnya = HIGH;

unsigned long waktuTetesTerakhir = 0;

const unsigned long DEBOUNCE_TETES = 500;


// =================================================
// FLOAT SWITCH
// =================================================
#define FLOAT_PIN 3

bool kondisiAirSebelumnya = false;


// =================================================
// BUZZER
// =================================================
#define BUZZER_PIN 38

bool buzzerAktif = false;

unsigned long waktuBuzzerMulai = 0;

const unsigned long INTERVAL_BEEP = 300;

// (enum ModeBuzzer didefinisikan di bagian atas file)

const unsigned long DURASI_BUZZER_AIR = 5000;
const unsigned long DURASI_BUZZER_PEMATIK = 5000;
const unsigned long DURASI_BUZZER_MATI = 3000;


// =================================================
// LED INDIKATOR
// =================================================
#define LED_SISTEM_ON 40
#define LED_SISTEM_OFF 39


// =================================================
// SERVO KOMPOR
// =================================================
#define SERVO_PIN 11

Servo servoKompor;

const int SERVO_BUKA_MAKSIMAL = 0;

// Bukaan minimal kompor agar api tidak mati
const int SERVO_BUKA_MINIMAL = 130;

const int SERVO_TUTUP_TOTAL = 180;

int sudutServo = SERVO_TUTUP_TOTAL;


// =================================================
// RELAY ACTIVE HIGH
// (pin RELAY_* didefinisikan di bagian atas file)
// =================================================
bool pompaAktif = false;
bool solenoidAktif = false;
bool pematikAktif = false;


// =================================================
// SENSOR FLAME ANALOG
// =================================================
#define FLAME_PIN 10

int nilaiFlame = 0;

// SESUAIKAN DENGAN HASIL PEMBACAAN SENSOR
const int FLAME_THRESHOLD = 2000;


// =================================================
// SISTEM PEMATIK API
// =================================================
const unsigned long JEDA_SERVO_PEMATIK = 1000;

const unsigned long DURASI_PEMATIK = 300;

const unsigned long WAKTU_CEK_API = 8000;

bool prosesPematik = false;

bool menungguCekApi = false;

bool apiMenyala = false;

bool pidSudahAktif = false;

unsigned long waktuServoBuka = 0;

unsigned long waktuPematikMulai = 0;

unsigned long waktuPematikSelesai = 0;


// =================================================
// PID BOILER
// =================================================
const float SETPOINT = 100.0;

float Kp = 3.0;
float Ki = 0.02;
float Kd = 1.0;

float errorPID = 0;

float errorSebelumnya = 0;

float integral = 0;

unsigned long waktuPIDTerakhir = 0;

const unsigned long INTERVAL_PID = 500;


// =================================================
// KALIBRASI SENSOR SUHU
// =================================================
const float KAL_M1 = 1.0;
const float KAL_OFFSET1 = 0.0;

const float KAL_M2 = 1.0;
const float KAL_OFFSET2 = 0.0;


// =================================================
// FILTER MOVING AVERAGE
// =================================================
const int JUMLAH_SAMPEL = 10;

float dataSuhu1[JUMLAH_SAMPEL];
int indexSuhu1 = 0;
bool dataPenuh1 = false;

float dataSuhu2[JUMLAH_SAMPEL];
int indexSuhu2 = 0;
bool dataPenuh2 = false;


// =================================================
// HASIL SENSOR
// =================================================
float suhu1 = 0;
float suhu2 = 0;

float raw1 = 0;
float raw2 = 0;

bool sensor1Valid = false;
bool sensor2Valid = false;


// =================================================
// STATUS SISTEM
// =================================================
bool sistemBerjalan = false;

unsigned long waktuSistemMulai = 0;


// =================================================
// TIMER
// =================================================
unsigned long waktuBacaSuhuTerakhir = 0;

const unsigned long INTERVAL_BACA_SUHU = 500;

unsigned long waktuSerialTerakhir = 0;

const unsigned long INTERVAL_SERIAL = 1000;


// =================================================
// SISTEM PENDINGIN
// =================================================

// Pendingin aktif jika suhu sensor 2 >= 33°C
const float BATAS_SUHU_PENDINGIN = 33.0;

// Solenoid ON 20 detik
const unsigned long DURASI_SOLENOID = 20000;

// Pompa ON total 40 detik
const unsigned long DURASI_POMPA = 40000;

// Pendinginan otomatis setiap 30 menit
const unsigned long INTERVAL_PENDINGIN_TIMER =
  30UL * 60UL * 1000UL;

// Jika pendinginan dipicu suhu,
// tunggu 8 menit sebelum mengecek lagi
const unsigned long INTERVAL_CEK_SUHU =
  8UL * 60UL * 1000UL;


// Status pendingin
bool pendinginAktif = false;

// 0 = OFF
// 1 = TIMER 30 MENIT
// 2 = SUHU >= 33
int modePendingin = 0;

unsigned long waktuPendinginMulai = 0;

unsigned long waktuPendinginTimerTerakhir = 0;

unsigned long waktuCekSuhuBerikutnya = 0;


// =================================================
// FORMAT WAKTU
// =================================================
String formatWaktu(unsigned long waktuMs) {

  unsigned long totalDetik = waktuMs / 1000;

  unsigned long jam = totalDetik / 3600;

  unsigned long menit =
    (totalDetik % 3600) / 60;

  unsigned long detik =
    totalDetik % 60;

  char buffer[20];

  sprintf(
    buffer,
    "%02lu:%02lu:%02lu",
    jam,
    menit,
    detik
  );

  return String(buffer);
}


// =================================================
// CONNECT WIFI
// =================================================
void connectWiFi() {

  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.println();
  Serial.println("========================================");
  Serial.println("MENGHUBUNGKAN WIFI");
  Serial.println("========================================");

  WiFi.begin(
    WIFI_SSID,
    WIFI_PASSWORD);

  unsigned long waktuMulai = millis();

  while (
    WiFi.status() != WL_CONNECTED && millis() - waktuMulai < 20000) {

    delay(500);

    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {

    Serial.println("WIFI TERHUBUNG!");

    Serial.print("IP ADDRESS: ");

    Serial.println(
      WiFi.localIP());

  } else {

    Serial.println(
      "GAGAL TERHUBUNG WIFI");
  }
}


// =================================================
// PUBLISH STATE
// =================================================
void publishState(
  String mode,
  String cause,
  String commandId = "") {

  if (!mqttClient.connected()) {

    Serial.println(
      "MQTT BELUM TERHUBUNG - STATE TIDAK DIKIRIM");

    return;
  }

  StaticJsonDocument<512> doc;

  doc["device_id"] = DEVICE_ID;

  doc["mode"] = mode;

  doc["cause"] = cause;

  if (commandId.length() > 0) {

    doc["command_id"] = commandId;
  }

  doc["ts"] = String(millis());

  char payload[512];

  serializeJson(
    doc,
    payload);

  bool berhasil =
    mqttClient.publish(
      topicState.c_str(),
      payload,
      true);

  if (berhasil) {

    Serial.println(
      "STATE BERHASIL DIKIRIM:");

    serializeJson(
      doc,
      Serial);

    Serial.println();

  } else {

    Serial.println(
      "GAGAL MENGIRIM STATE");
  }
}


// =================================================
// PUBLISH TELEMETRY
// =================================================
void publishTelemetry() {

  if (!mqttClient.connected()) {
    return;
  }

  bool airKosong =
    digitalRead(FLOAT_PIN) == LOW;

  float waterLevel =
    airKosong ? 0.0 : 100.0;


  unsigned long dripInterval =
    jumlahTetesan - tetesanTerakhirTelemetry;

  tetesanTerakhirTelemetry =
    jumlahTetesan;


  StaticJsonDocument<512> doc;

  doc["ts"] =
    String(millis());


  if (sensor1Valid) {

    doc["boiler_temp_c"] =
      suhu1;

  } else {

    doc["boiler_temp_c"] =
      nullptr;
  }


  if (sensor2Valid) {

    doc["cooling_temp_c"] =
      suhu2;

  } else {

    doc["cooling_temp_c"] =
      nullptr;
  }


  if (loadCellValid) {

    doc["gas_mass_kg"] =
      beratKg;

  } else {

    doc["gas_mass_kg"] =
      nullptr;
  }


  doc["water_level"] =
    waterLevel;

  doc["drip_count"] =
    dripInterval;

  doc["flame_lit"] =
    apiMenyala;


  char payload[512];

  serializeJson(
    doc,
    payload);


  bool berhasil =
    mqttClient.publish(
      topicTelemetry.c_str(),
      payload);


  if (berhasil) {

    Serial.println(
      "TELEMETRY DIKIRIM:");

    serializeJson(
      doc,
      Serial);

    Serial.println();

  } else {

    Serial.println(
      "GAGAL MENGIRIM TELEMETRY");
  }
}


// ===============================================
// MQTT CALLBACK
// ===============================================
void mqttCallback(
  char* topic,
  byte* payload,
  unsigned int length) {

  String message = "";

  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.println("COMMAND MQTT DITERIMA:");
  Serial.println(message);

  StaticJsonDocument<512> doc;

  DeserializationError error = deserializeJson(doc, message);

  if (error) {
    Serial.println("ERROR PARSE JSON!");
    return;
  }

  String command = doc["action"] | "";

  Serial.print("COMMAND: ");
  Serial.println(command);


  // PERINTAH ASLI: mulai
  if (command == "mulai") {

    if (!sistemBerjalan) {
      mulaiSistem();
    } else {
      Serial.println("SISTEM SUDAH BERJALAN");
    }
  }


  // PERINTAH ASLI: mati
  else if (command == "mati") {

    matikanSistem();
  }


  // PERINTAH TIDAK DIKENAL
  else {

    Serial.println("PERINTAH TIDAK DIKENAL");
  }
}


// =================================================
// CONNECT MQTT (NON-BLOCKING)
// =================================================
void connectMQTT() {

  // Tidak memakai while() agar program tidak berhenti
  // dan sensor tetap berjalan walaupun MQTT gagal.

  if (mqttClient.connected()) {
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WIFI BELUM TERHUBUNG - MQTT DILEWATI");
    return;
  }

  Serial.println();
  Serial.println("MENGHUBUNGKAN MQTT...");

  bool connected =
    mqttClient.connect(
      MQTT_CLIENT_ID,
      MQTT_USERNAME,
      MQTT_PASSWORD);

  if (connected) {

    Serial.println("MQTT BERHASIL TERHUBUNG!");

    Serial.print("SUBSCRIBE: ");
    Serial.println(topicCommand);

    mqttClient.subscribe(
      topicCommand.c_str(),
      1);

    publishState(
      modeDevice,
      "detected");

  } else {

    Serial.print("MQTT GAGAL. STATE: ");
    Serial.println(mqttClient.state());

    Serial.println(
      "SISTEM TETAP LANJUT MEMBACA SENSOR");
  }
}


// =================================================
// FILTER SUHU
// =================================================
float filterSuhu(
  float suhuBaru,
  float data[],
  int &index,
  bool &penuh
) {

  data[index] = suhuBaru;

  index++;

  if (index >= JUMLAH_SAMPEL) {
    index = 0;
    penuh = true;
  }

  int jumlahData;

  if (penuh) {
    jumlahData = JUMLAH_SAMPEL;
  } else {
    jumlahData = index;
  }

  float total = 0;

  for (int i = 0; i < jumlahData; i++) {
    total += data[i];
  }

  return total / jumlahData;
}


// =================================================
// BACA SENSOR SUHU
// =================================================
void bacaSuhu() {

  raw1 = thermocouple1.readCelsius();

  if (!isnan(raw1)) {

    float kalibrasi1 =
      (raw1 * KAL_M1) + KAL_OFFSET1;

    suhu1 = filterSuhu(
      kalibrasi1,
      dataSuhu1,
      indexSuhu1,
      dataPenuh1
    );

    sensor1Valid = true;

  } else {

    sensor1Valid = false;
  }


  raw2 = thermocouple2.readCelsius();

  if (!isnan(raw2)) {

    float kalibrasi2 =
      (raw2 * KAL_M2) + KAL_OFFSET2;

    suhu2 = filterSuhu(
      kalibrasi2,
      dataSuhu2,
      indexSuhu2,
      dataPenuh2
    );

    sensor2Valid = true;

  } else {

    sensor2Valid = false;
  }
}


// =================================================
// BACA LOAD CELL (non-blocking)
// =================================================
// read_average(15) memblokir loop ±1.5 detik (HX711 @10SPS = ~100ms/sampel)
// dan membuat relay pematik/PID/telemetry telat. Kini: 1 sampel per panggilan,
// dirata-ratakan lintas loop.
const int JUMLAH_SAMPEL_LOADCELL = 5;
long totalSampelLoadCell = 0;
int jumlahSampelLoadCell = 0;

void bacaLoadCell() {

  if (scale.is_ready()) {

    // 1 sampel per panggilan (~100ms @10SPS) — loop tidak diblokir lama
    totalSampelLoadCell += scale.read();
    jumlahSampelLoadCell++;

    if (jumlahSampelLoadCell >= JUMLAH_SAMPEL_LOADCELL) {

      rawLoadCell =
        totalSampelLoadCell / jumlahSampelLoadCell;

      totalSampelLoadCell = 0;

      jumlahSampelLoadCell = 0;

      beratKg =
        ((float)(rawLoadCell - RAW_KOSONG) /
        (RAW_BEBAN - RAW_KOSONG))
        * BERAT_REFERENSI;

      if (beratKg < 0.02) {
        beratKg = 0;
      }

      if (beratKg < 0) {
        beratKg = 0;
      }

      beratGram =
        beratKg * 1000.0;

      loadCellValid = true;
    }

  } else {

    loadCellValid = false;
  }
}


// =================================================
// KONTROL RELAY
// =================================================
void setPompa(bool status) {

  pompaAktif = status;

  digitalWrite(
    RELAY_POMPA,
    status ? HIGH : LOW
  );
}


void setSolenoid(bool status) {

  solenoidAktif = status;

  digitalWrite(
    RELAY_SOLENOID,
    status ? HIGH : LOW
  );
}


void setPematik(bool status) {

  pematikAktif = status;

  digitalWrite(
    RELAY_PEMATIK,
    status ? HIGH : LOW
  );
}


// =================================================
// BUZZER
// =================================================
void mulaiBuzzer(ModeBuzzer mode) {

  buzzerAktif = true;

  modeBuzzer = mode;

  waktuBuzzerMulai = millis();
}


void updateBuzzer() {

  if (!buzzerAktif) {

    digitalWrite(BUZZER_PIN, LOW);

    return;
  }

  unsigned long durasi = 0;

  if (modeBuzzer == BUZZER_AIR_HABIS) {

    durasi = DURASI_BUZZER_AIR;

  }

  else if (modeBuzzer == BUZZER_PEMATIK) {

    durasi = DURASI_BUZZER_PEMATIK;

  }

  else if (modeBuzzer == BUZZER_SISTEM_MATI) {

    durasi = DURASI_BUZZER_MATI;
  }


  if (
    millis() - waktuBuzzerMulai >= durasi
  ) {

    buzzerAktif = false;

    modeBuzzer =
      BUZZER_TIDAK_AKTIF;

    digitalWrite(
      BUZZER_PIN,
      LOW
    );

    return;
  }


  if (
    (millis() / INTERVAL_BEEP) % 2 == 0
  ) {

    digitalWrite(
      BUZZER_PIN,
      HIGH
    );

  } else {

    digitalWrite(
      BUZZER_PIN,
      LOW
    );
  }
}


// =================================================
// CEK AIR
// =================================================
void cekAir() {

  bool airKosong =
    digitalRead(FLOAT_PIN) == LOW;


  if (
    airKosong &&
    !kondisiAirSebelumnya
  ) {

    mulaiBuzzer(
      BUZZER_AIR_HABIS
    );

    Serial.println(
      "!!! AIR HABIS !!!"
    );
  }


  kondisiAirSebelumnya =
    airKosong;
}


// =================================================
// CEK API
// =================================================
bool cekApi() {

  nilaiFlame =
    analogRead(FLAME_PIN);

  if (
    nilaiFlame < FLAME_THRESHOLD
  ) {

    return true;

  } else {

    return false;
  }
}


// =================================================
// HITUNG PID
// =================================================
int hitungPID(
  float suhuSekarang
) {

  unsigned long sekarang =
    millis();

  float dt =
    (sekarang - waktuPIDTerakhir)
    / 1000.0;


  if (dt <= 0) {
    return sudutServo;
  }


  float error =
    SETPOINT - suhuSekarang;


  integral +=
    error * dt;


  integral =
    constrain(
      integral,
      -100,
      100
    );


  float derivative =
    (error - errorSebelumnya)
    / dt;


  float outputPID =
    (Kp * error) +
    (Ki * integral) +
    (Kd * derivative);


  int hasilServo =
    SERVO_BUKA_MINIMAL -
    outputPID;


  hasilServo =
    constrain(
      hasilServo,
      SERVO_BUKA_MAKSIMAL,
      SERVO_BUKA_MINIMAL
    );


  errorSebelumnya =
    error;

  waktuPIDTerakhir =
    sekarang;


  return hasilServo;
}


// =================================================
// MULAI PENDINGIN
// =================================================
void mulaiPendingin(
  int mode
) {

  pendinginAktif = true;

  modePendingin = mode;

  waktuPendinginMulai =
    millis();


  // Awal:
  // Solenoid ON
  // Pompa ON
  setSolenoid(true);

  setPompa(true);


  Serial.println();

  Serial.println(
    "================================"
  );

  Serial.println(
    "PENDINGIN DIMULAI"
  );


  if (mode == 1) {

    Serial.println(
      "MODE: TIMER 30 MENIT"
    );

  }

  else if (mode == 2) {

    Serial.println(
      "MODE: SUHU >= 33 C"
    );
  }


  Serial.println(
    "SOLENOID ON 20 DETIK"
  );

  Serial.println(
    "POMPA ON TOTAL 40 DETIK"
  );

  Serial.println(
    "================================"
  );
}


// =================================================
// UPDATE PENDINGIN
// =================================================
void updatePendingin() {

  if (!pendinginAktif) {
    return;
  }


  unsigned long waktuBerjalan =
    millis() -
    waktuPendinginMulai;


  // ===============================================
  // SETELAH 20 DETIK
  // SOLENOID OFF
  // POMPA TETAP ON
  // ===============================================
  if (
    waktuBerjalan >= DURASI_SOLENOID &&
    solenoidAktif
  ) {

    setSolenoid(false);

    Serial.println(
      "SOLENOID OFF"
    );

    Serial.println(
      "POMPA TETAP ON"
    );
  }


  // ===============================================
  // SETELAH 40 DETIK
  // SEMUA MATI
  // ===============================================
  if (
    waktuBerjalan >= DURASI_POMPA
  ) {

    setPompa(false);

    setSolenoid(false);

    pendinginAktif = false;


    Serial.println(
      "PENDINGIN SELESAI"
    );


    // Jika pendingin aktif
    // karena suhu >= 33°C
    if (modePendingin == 2) {

      waktuCekSuhuBerikutnya =
        millis() +
        INTERVAL_CEK_SUHU;


      Serial.println(
        "MENUNGGU 8 MENIT UNTUK CEK SUHU LAGI"
      );
    }


    modePendingin = 0;
  }
}


// =================================================
// KONTROL PENDINGIN
// =================================================
void kontrolPendingin() {

  if (!sistemBerjalan) {
    return;
  }


  // Update proses pendinginan
  updatePendingin();


  // Jika masih pendinginan,
  // jangan mulai pendinginan baru
  if (pendinginAktif) {
    return;
  }


  unsigned long sekarang =
    millis();


  // ===============================================
  // PRIORITAS 1
  // SETIAP 30 MENIT
  // ===============================================
  if (
    sekarang -
    waktuPendinginTimerTerakhir >=
    INTERVAL_PENDINGIN_TIMER
  ) {

    waktuPendinginTimerTerakhir =
      sekarang;

    mulaiPendingin(1);

    return;
  }


  // ===============================================
  // PRIORITAS 2
  // SUHU >= 33°C
  // ===============================================
  if (
    sensor2Valid &&
    suhu2 >=
    BATAS_SUHU_PENDINGIN
  ) {

    if (
      waktuCekSuhuBerikutnya == 0 ||
      sekarang >=
      waktuCekSuhuBerikutnya
    ) {

      mulaiPendingin(2);

      return;
    }
  }
}


// =================================================
// MULAI SISTEM
// =================================================
void mulaiSistem() {

  sistemBerjalan = true;

  waktuSistemMulai =
    millis();

  apiMenyala = false;

  pidSudahAktif = false;

  prosesPematik = true;

  pematikAktif = false;

  menungguCekApi = false;

  pendinginAktif = false;

  modePendingin = 0;


  // Timer pendinginan 30 menit
  waktuPendinginTimerTerakhir =
    millis();


  // Reset timer suhu
  waktuCekSuhuBerikutnya = 0;


  integral = 0;

  errorPID = 0;

  errorSebelumnya = 0;


  digitalWrite(
    LED_SISTEM_ON,
    HIGH
  );

  digitalWrite(
    LED_SISTEM_OFF,
    LOW
  );


  // Servo buka maksimal
  sudutServo =
    SERVO_BUKA_MAKSIMAL;

  servoKompor.write(
    sudutServo
  );


  waktuServoBuka =
    millis();


  modeDevice =
    "PREHEAT";

  publishState(
    modeDevice,
    "detected"
  );


  Serial.println();

  Serial.println(
    "================================"
  );

  Serial.println(
    "SISTEM DIMULAI"
  );

  Serial.println(
    "KOMPOR MENYALA"
  );

  Serial.println(
    "PID SETPOINT 100 C"
  );

  Serial.println(
    "PENDINGIN TIMER: 30 MENIT"
  );

  Serial.println(
    "PENDINGIN SUHU: >= 33 C"
  );

  Serial.println(
    "CEK ULANG SUHU: 8 MENIT"
  );

  Serial.println(
    "================================"
  );
}


// =================================================
// PROSES MENYALAKAN API
// =================================================
void prosesNyalakanApi() {

  // Tunggu servo membuka
  if (
    prosesPematik &&
    !pematikAktif &&
    !menungguCekApi &&
    millis() -
    waktuServoBuka >=
    JEDA_SERVO_PEMATIK
  ) {

    setPematik(true);

    waktuPematikMulai =
      millis();

    // Jaminan keras: OFF dipicu hardware timer di DURASI_PEMATIK,
    // tidak bergantung pada loop() yang bisa diblokir.
    pematikHardOff = false;
    esp_timer_start_once(pematikTimer, (uint64_t)DURASI_PEMATIK * 1000);

    mulaiBuzzer(
      BUZZER_PEMATIK
    );

    Serial.println(
      "PEMATIK API ON"
    );
  }


  // Pematik ON 0,3 detik — dipicu loop ATAU hardware timer (pematikHardOff)
  if (
    pematikAktif &&
    (millis() -
    waktuPematikMulai >=
    DURASI_PEMATIK || pematikHardOff)
  ) {

    if (pematikTimer) esp_timer_stop(pematikTimer);  // batalkan sisa timer

    setPematik(false);

    pematikHardOff = false;

    menungguCekApi = true;

    waktuPematikSelesai =
      millis();

    Serial.println(
      "PEMATIK API OFF"
    );
  }


  // Tunggu 8 detik
  // lalu cek apakah api menyala
  if (
    menungguCekApi &&
    millis() -
    waktuPematikSelesai >=
    WAKTU_CEK_API
  ) {

    bool hasilApi =
      cekApi();


    if (hasilApi) {

      apiMenyala = true;

      menungguCekApi = false;

      prosesPematik = false;

      pidSudahAktif = true;

      waktuPIDTerakhir =
        millis();


      modeDevice =
        "DISTILLING";

      publishState(
        modeDevice,
        "detected"
      );


      Serial.println(
        "API TERDETEKSI"
      );

      Serial.println(
        "PID DIAKTIFKAN"
      );

    }

    else {

      Serial.println(
        "API BELUM MENYALA - ULANGI PEMATIK"
      );


      menungguCekApi = false;

      prosesPematik = true;

      waktuServoBuka =
        millis() -
        JEDA_SERVO_PEMATIK;
    }
  }
}


// =================================================
// MATIKAN SISTEM
// =================================================
void matikanSistem() {

  sistemBerjalan = false;

  prosesPematik = false;

  menungguCekApi = false;

  apiMenyala = false;

  pidSudahAktif = false;

  pendinginAktif = false;

  modePendingin = 0;


  // Bersihkan timer pematik dan paksa relay OFF tanpa syarat
  if (pematikTimer) esp_timer_stop(pematikTimer);

  gpio_set_level((gpio_num_t)RELAY_PEMATIK, 0);

  pematikHardOff = false;

  setPematik(false);

  setPompa(false);

  setSolenoid(false);


  sudutServo =
    SERVO_TUTUP_TOTAL;

  servoKompor.write(
    sudutServo
  );


  digitalWrite(
    LED_SISTEM_ON,
    LOW
  );

  digitalWrite(
    LED_SISTEM_OFF,
    HIGH
  );


  integral = 0;

  errorPID = 0;

  errorSebelumnya = 0;


  mulaiBuzzer(
    BUZZER_SISTEM_MATI
  );


  if (
    modeDevice != "ESTOP"
  ) {

    modeDevice =
      "IDLE";
  }

  publishState(
    modeDevice,
    "detected"
  );


  Serial.println();

  Serial.println(
    "================================"
  );

  Serial.println(
    "SISTEM DIMATIKAN"
  );

  Serial.println(
    "KOMPOR DITUTUP"
  );

  Serial.println(
    "POMPA OFF"
  );

  Serial.println(
    "SOLENOID OFF"
  );

  Serial.println(
    "================================"
  );
}


// =================================================
// BACA PERINTAH SERIAL
// =================================================
void bacaPerintahSerial() {

  if (Serial.available()) {

    String perintah =
      Serial.readStringUntil('\n');

    perintah.trim();

    perintah.toLowerCase();


    if (perintah == "mulai") {

      if (!sistemBerjalan) {

        mulaiSistem();

      } else {

        Serial.println(
          "SISTEM SUDAH BERJALAN"
        );
      }
    }


    else if (
      perintah == "mati"
    ) {

      matikanSistem();
    }
  }
}


// =================================================
// SETUP
// =================================================
void setup() {

  Serial.begin(115200);

  delay(2000);


  Serial.println(
    "========================================"
  );

  Serial.println(
    "SISTEM DISTILASI OTOMATIS"
  );

  Serial.println(
    "========================================"
  );


  // ===============================================
  // WIFI (blocking hanya saat boot)
  // ===============================================
  connectWiFi();


  // ===============================================
  // TLS
  // ===============================================
  secureClient.setInsecure();


  // ===============================================
  // MQTT — tidak dihubungkan di setup agar boot
  // tidak tertahan; dicoba tiap 10 detik di loop().
  // ===============================================
  mqttClient.setServer(
    MQTT_BROKER,
    MQTT_PORT
  );

  mqttClient.setCallback(
    mqttCallback
  );

  mqttClient.setBufferSize(
    1024
  );


  // Sensor IR
  pinMode(
    IR_PIN,
    INPUT
  );

  statusIRSebelumnya =
    digitalRead(IR_PIN);


  // Float switch
  pinMode(
    FLOAT_PIN,
    INPUT_PULLUP
  );

  kondisiAirSebelumnya =
    digitalRead(FLOAT_PIN) == LOW;


  // Flame sensor
  pinMode(
    FLAME_PIN,
    INPUT
  );


  // Buzzer
  pinMode(
    BUZZER_PIN,
    OUTPUT
  );

  digitalWrite(
    BUZZER_PIN,
    LOW
  );


  // LED
  pinMode(
    LED_SISTEM_ON,
    OUTPUT
  );

  pinMode(
    LED_SISTEM_OFF,
    OUTPUT
  );

  digitalWrite(
    LED_SISTEM_ON,
    LOW
  );

  digitalWrite(
    LED_SISTEM_OFF,
    HIGH
  );


  // Relay
  pinMode(
    RELAY_POMPA,
    OUTPUT
  );

  pinMode(
    RELAY_SOLENOID,
    OUTPUT
  );

  pinMode(
    RELAY_PEMATIK,
    OUTPUT
  );

  setPompa(false);

  setSolenoid(false);

  setPematik(false);


  // Timer hardware pematik — jaminan keras OFF di DURASI_PEMATIK
  esp_timer_create_args_t argsTimer = {};
  argsTimer.callback = &pematikTimerCallback;
  argsTimer.name = "pematik";
  esp_timer_create(&argsTimer, &pematikTimer);


  // Servo
  servoKompor.attach(
    SERVO_PIN
  );

  servoKompor.write(
    SERVO_TUTUP_TOTAL
  );


  // HX711
  scale.begin(
    HX711_DT_PIN,
    HX711_SCK_PIN
  );


  // Inisialisasi filter suhu
  for (
    int i = 0;
    i < JUMLAH_SAMPEL;
    i++
  ) {

    dataSuhu1[i] = 0;

    dataSuhu2[i] = 0;
  }


  Serial.println();

  Serial.println(
    "Ketik 'mulai' untuk menjalankan sistem"
  );

  Serial.println(
    "Ketik 'mati' untuk menghentikan sistem"
  );
}


// =================================================
// LOOP
// =================================================
void loop() {

  // ===============================================
  // JAGA WIFI
  // ===============================================
  if (
    WiFi.status() != WL_CONNECTED
  ) {

    connectWiFi();
  }


  // ===============================================
  // JAGA MQTT (reconnect non-blocking, tiap 10 detik)
  // ===============================================
  if (
    !mqttClient.connected()
  ) {

    if (
      millis() - waktuMQTTTerakhir >= INTERVAL_MQTT
    ) {

      waktuMQTTTerakhir =
        millis();

      Serial.println();
      Serial.println(
        "MENCOBA KONEKSI MQTT..."
      );

      connectMQTT();
    }
  }


  // ===============================================
  // PROSES PESAN MQTT
  // ===============================================
  mqttClient.loop();


  // ===============================================
  // BACA PERINTAH SERIAL
  // ===============================================
  bacaPerintahSerial();


  // ===============================================
  // UPDATE BUZZER
  // ===============================================
  updateBuzzer();


  // ===============================================
  // CEK AIR
  // ===============================================
  cekAir();


  // ===============================================
  // BACA SENSOR SUHU
  // ===============================================
  if (
    millis() -
    waktuBacaSuhuTerakhir >=
    INTERVAL_BACA_SUHU
  ) {

    waktuBacaSuhuTerakhir =
      millis();

    bacaSuhu();
  }


  // ===============================================
  // BACA LOAD CELL
  // ===============================================
  if (
    millis() -
    waktuLoadCellTerakhir >=
    INTERVAL_LOAD_CELL
  ) {

    waktuLoadCellTerakhir =
      millis();

    bacaLoadCell();
  }


  // ===============================================
  // SISTEM BERJALAN
  // ===============================================
  if (sistemBerjalan) {

    // =============================================
    // PROSES PEMATIK API
    // =============================================
    if (
      prosesPematik ||
      menungguCekApi
    ) {

      prosesNyalakanApi();
    }


    // =============================================
    // PID KOMPOR
    // =============================================
    if (
      pidSudahAktif &&
      sensor1Valid &&
      millis() -
      waktuPIDTerakhir >=
      INTERVAL_PID
    ) {

      sudutServo =
        hitungPID(
          suhu1
        );

      servoKompor.write(
        sudutServo
      );
    }


    // =============================================
    // SENSOR INFRARED
    // PENGHITUNG TETESAN
    // =============================================
    int statusSekarang =
      digitalRead(IR_PIN);


    if (
      statusSekarang == LOW &&
      statusIRSebelumnya == HIGH
    ) {

      if (
        millis() -
        waktuTetesTerakhir >=
        DEBOUNCE_TETES
      ) {

        jumlahTetesan++;

        waktuTetesTerakhir =
          millis();


        Serial.print(
          "TETESAN TERDETEKSI! TOTAL = "
        );

        Serial.println(
          jumlahTetesan
        );
      }
    }


    statusIRSebelumnya =
      statusSekarang;


    // =============================================
    // KONTROL PENDINGIN
    // =============================================
    kontrolPendingin();
  }


  // ===============================================
  // PUBLISH TELEMETRY SETIAP 5 DETIK
  // ===============================================
  if (
    millis() - waktuTelemetryTerakhir >= INTERVAL_TELEMETRY
  ) {

    waktuTelemetryTerakhir =
      millis();

    publishTelemetry();
  }


  // ===============================================
  // TAMPILKAN SERIAL MONITOR
  // ===============================================
  if (
    millis() -
    waktuSerialTerakhir >=
    INTERVAL_SERIAL
  ) {

    waktuSerialTerakhir =
      millis();


    nilaiFlame =
      analogRead(
        FLAME_PIN
      );


    bool airKosong =
      digitalRead(FLOAT_PIN) == LOW;


    Serial.println();

    Serial.println(
      "========================================"
    );


    // STATUS SISTEM
    Serial.print(
      "STATUS SISTEM     : "
    );

    Serial.println(
      sistemBerjalan ?
      "BERJALAN" :
      "MATI"
    );


    // STOPWATCH DISTILASI
    if (sistemBerjalan) {

      unsigned long waktuBerjalan =
        millis() -
        waktuSistemMulai;


      Serial.print(
        "WAKTU DISTILASI   : "
      );

      Serial.println(
        formatWaktu(
          waktuBerjalan
        )
      );

    } else {

      Serial.println(
        "WAKTU DISTILASI   : 00:00:00"
      );
    }


    // SENSOR 1
    Serial.print(
      "SUHU BOILER       : "
    );

    if (sensor1Valid) {

      Serial.print(
        suhu1,
        2
      );

      Serial.println(
        " C"
      );

    } else {

      Serial.println(
        "ERROR"
      );
    }


    // SENSOR 2
    Serial.print(
      "SUHU PENDINGIN    : "
    );

    if (sensor2Valid) {

      Serial.print(
        suhu2,
        2
      );

      Serial.println(
        " C"
      );

    } else {

      Serial.println(
        "ERROR"
      );
    }


    // SETPOINT
    Serial.print(
      "SETPOINT BOILER   : "
    );

    Serial.print(
      SETPOINT
    );

    Serial.println(
      " C"
    );


    // BATAS PENDINGIN
    Serial.print(
      "BATAS PENDINGIN   : "
    );

    Serial.print(
      BATAS_SUHU_PENDINGIN
    );

    Serial.println(
      " C"
    );


    // SERVO
    Serial.print(
      "SUDUT SERVO       : "
    );

    Serial.print(
      sudutServo
    );

    Serial.println(
      " derajat"
    );


    // TETESAN
    Serial.print(
      "TOTAL TETESAN     : "
    );

    Serial.println(
      jumlahTetesan
    );


    // LOAD CELL
    if (loadCellValid) {

      Serial.print(
        "BERAT             : "
      );

      Serial.print(
        beratKg,
        3
      );

      Serial.println(
        " kg"
      );
    }


    // AIR
    Serial.print(
      "STATUS AIR        : "
    );

    Serial.println(
      airKosong ?
      "KOSONG" :
      "TERDETEKSI"
    );


    // FLAME
    Serial.print(
      "FLAME ANALOG      : "
    );

    Serial.println(
      nilaiFlame
    );


    // POMPA
    Serial.print(
      "RELAY POMPA       : "
    );

    Serial.println(
      pompaAktif ?
      "ON" :
      "OFF"
    );


    // SOLENOID
    Serial.print(
      "RELAY SOLENOID    : "
    );

    Serial.println(
      solenoidAktif ?
      "ON" :
      "OFF"
    );


    // MODE PENDINGIN
    Serial.print(
      "MODE PENDINGIN    : "
    );


    if (pendinginAktif) {

      if (modePendingin == 1) {

        Serial.println(
          "TIMER 30 MENIT"
        );

      }

      else if (modePendingin == 2) {

        Serial.println(
          "SUHU >= 33 C"
        );
      }

    } else {

      Serial.println(
        "OFF"
      );
    }


    // STOPWATCH PENDINGIN
    if (pendinginAktif) {

      unsigned long waktuPendingin =
        millis() -
        waktuPendinginMulai;


      Serial.print(
        "WAKTU PENDINGIN   : "
      );

      Serial.print(
        formatWaktu(
          waktuPendingin
        )
      );

      Serial.println(
        " / 00:00:40"
      );

    } else {

      Serial.println(
        "WAKTU PENDINGIN   : OFF"
      );
    }


    // PEMATIK
    Serial.print(
      "PEMATIK API       : "
    );

    Serial.println(
      pematikAktif ?
      "ON" :
      "OFF"
    );


    Serial.println(
      "========================================"
    );
  }
}