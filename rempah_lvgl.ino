// ============================================================
//   REMPAH — Kontrol Distilasi
//   Port ke LVGL v9 + TFT_eSPI
//   Hardware : ESP32 + ST7789 240x320 + XPT2046
//   Touch cal: { 632, 3042, 551, 2825, 7 }  (untuk rotasi 1)
// ============================================================

#include <lvgl.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// ============================================================
//   WiFi & MQTT
// ============================================================
const char* ssid         = "tahubulat";
const char* password     = "bay12345";
const char* mqtt_server  = "bde4a0fdcf30401db2125620c5950fa9.s1.eu.hivemq.cloud";
const int   mqtt_port    = 8883;
const char* mqtt_user    = "rempah_hivemq";
const char* mqtt_pass    = "@rempah1234";
const char* DEVICE_ID    = "dc9b3ba4-1985-458e-94d4-d8f8c69c1d95";
const char* MQTT_TELEM   = "rempah/dc9b3ba4-1985-458e-94d4-d8f8c69c1d95/telemetry";
const char* MQTT_STATE   = "rempah/dc9b3ba4-1985-458e-94d4-d8f8c69c1d95/state";
const char* MQTT_CMD     = "rempah/dc9b3ba4-1985-458e-94d4-d8f8c69c1d95/command";
const char* MQTT_SUB_WILD= "rempah/dc9b3ba4-1985-458e-94d4-d8f8c69c1d95/+";

// ============================================================
//   DISPLAY & TOUCH
// ============================================================
TFT_eSPI tft = TFT_eSPI();
uint16_t calData[5] = { 632, 3042, 551, 2825, 7 };

#define TFT_HOR_RES  320
#define TFT_VER_RES  240
#define DRAW_BUF_SIZE (TFT_HOR_RES * TFT_VER_RES / 20 * (LV_COLOR_DEPTH / 8))
uint32_t draw_buf[DRAW_BUF_SIZE / 4];

// ============================================================
//   PALETTE
// ============================================================
#define C_BG        lv_color_hex(0xC8D4DC)
#define C_CARD      lv_color_hex(0xFFFFFF)
#define C_BORDER    lv_color_hex(0xB0BEC5)
#define C_LABEL     lv_color_hex(0x546E7A)
#define C_VALUE     lv_color_hex(0x000000)
#define C_NAV       lv_color_hex(0x37474F)
#define C_RED       lv_color_hex(0xE53935)
#define C_DARK      lv_color_hex(0x2C3E50)
#define C_BLUE      lv_color_hex(0x5B9BD5)
#define C_CHART     lv_color_hex(0xF5A623)
#define C_GREEN     lv_color_hex(0x2E7D32)
#define C_WHITE     lv_color_hex(0xFFFFFF)
#define C_TEXT_MUTE lv_color_hex(0x90A4AE)

// Status sensor
#define ST_OFF  0
#define ST_ON   1
#define ST_KAL  2
#define ST_SOON 3   // Coming soon — sensor belum terpasang

// ============================================================
//   STATE
// ============================================================
typedef enum {
    SCR_NOTIF_WAIT = 0,
    SCR_NOTIF_OK,
    SCR_NOTIF_FAIL,
    SCR_WELCOME,
    SCR_WEIGHT,
    SCR_DASHBOARD,
    SCR_PAGE2,
    SCR_SENSORS,
    SCR_DETAIL,
    SCR_SHUTDOWN
} ScreenState;

ScreenState screenState     = SCR_NOTIF_WAIT;
ScreenState prevScreenState = SCR_DASHBOARD;
int         detailCardIdx   = 0;

// ============================================================
//   DATA SENSOR
// ============================================================
float suhuBoiler    = 0.0f;
float suhuPendingin = 0.0f;
float beratGas      = 0.0f;
float estHasil      = 0.0f;
float beratMuatan   = 1.0f;   // kg, step 0.5

#define CHART_POINTS 20
static lv_chart_series_t* chart_ser[4];
static float chartRaw[4][CHART_POINTS];
static int   chartCount = 0;

// Status 4 device di Page2 — SEMUA MATI sebagai default (akan di-update via MQTT)
bool device_status[4] = {false, false, false, false};
static lv_obj_t* dev_status_lbl[4] = {nullptr, nullptr, nullptr, nullptr};
static const char* dev_ids[4]   = {"SENSOR_API", "PEMANTIK", "POMPA_PENDINGIN", "POMPA_BOILER"};
static const char* dev_names[4] = {"SENSOR API", "PEMANTIK API", "POMPA PENDINGIN", "POMPA BOILER"};

// ============================================================
//   LVGL OBJECTS
// ============================================================
static lv_obj_t* scr_notif    = nullptr;
static lv_obj_t* scr_welcome  = nullptr;
static lv_obj_t* scr_weight   = nullptr;
static lv_obj_t* scr_dash     = nullptr;
static lv_obj_t* scr_page2    = nullptr;
static lv_obj_t* scr_sensors  = nullptr;
static lv_obj_t* scr_detail   = nullptr;
static lv_obj_t* scr_shutdown = nullptr;

static lv_obj_t* lbl_boiler     = nullptr;
static lv_obj_t* lbl_pendingin  = nullptr;
static lv_obj_t* lbl_gas        = nullptr;
static lv_obj_t* lbl_hasil      = nullptr;
static lv_obj_t* lbl_weight_val = nullptr;
static lv_obj_t* lbl_detail_val  = nullptr;
static lv_obj_t* lbl_detail_name = nullptr;
static lv_obj_t* chart_obj       = nullptr;
static lv_chart_series_t* detail_ser = nullptr;
static lv_obj_t* lbl_notif_msg = nullptr;

// ============================================================
//   WIFI INDICATOR — array label (1 per screen yang punya header)
// ============================================================
#define MAX_WIFI_LBL 10
static lv_obj_t* wifi_lbls[MAX_WIFI_LBL] = {nullptr};
static int wifi_lbl_count = 0;

// ============================================================
//   TIMER & CONNECTION
// ============================================================
WiFiClientSecure secureClient;
PubSubClient     mqttClient(secureClient);

unsigned long wifiStartTime    = 0;
const unsigned long wifiTimeout = 15000;
unsigned long notifOkTimer     = 0;

unsigned long lastMqttMsg            = 0;
const unsigned long SENSOR_OFF_TIMEOUT = 10000;  // 10 dtk tanpa data = OFF

unsigned long lastUiCheck            = 0;
unsigned long lastWifiUpdate         = 0;
const unsigned long WIFI_UPDATE_INTERVAL = 2000; // cek RSSI tiap 2 detik

// ============================================================
//   FORWARD DECLARATIONS
// ============================================================
static void show_screen(ScreenState next);
static void update_detail_chart();
static void build_all_screens();
static void publishCommand(const char* cmd, const char* device = nullptr, int val = -1);
static void publishAction(const char* action);
static void update_wifi_indicator();

// ============================================================
//   SENSOR CARD STRUCT + STATUS
// ============================================================
#define ST_OFF 0
#define ST_ON  1
#define ST_KAL 2

struct SensorCard {
    lv_obj_t* card;
    lv_obj_t* lbl_title;
    lv_obj_t* lbl_value;
    lv_obj_t* lbl_unit;
    lv_obj_t* lbl_status;
};

static SensorCard sensor_cards[4];
static int        sensor_status[4] = { ST_OFF, ST_OFF, ST_OFF, ST_OFF };
static float*     sensor_val[4] = { &suhuBoiler, &suhuPendingin, &beratGas, &estHasil };
// true = sensor ini belum ada, paksa ST_SOON permanen
static const bool sensor_coming_soon[4] = {
    false,  // [0] SUHU BOILER    — aktif
    true,   // [1] SUHU PENDINGIN — coming soon
    false,  // [2] BERAT GAS      — aktif
    false,  // [3] EST. HASIL     — aktif (drip_count)
};

// ============================================================
//   LVGL DRIVER CALLBACKS
// ============================================================
void my_disp_flush(lv_display_t* disp, const lv_area_t* area, uint8_t* px_map) {
    uint32_t w = area->x2 - area->x1 + 1;
    uint32_t h = area->y2 - area->y1 + 1;
    tft.startWrite();
    tft.setAddrWindow(area->x1, area->y1, w, h);
    tft.pushColors((uint16_t*)px_map, w * h, true);
    tft.endWrite();
    lv_display_flush_ready(disp);
}

void my_touchpad_read(lv_indev_t* indev, lv_indev_data_t* data) {
    uint16_t x, y;
    if (tft.getTouch(&x, &y, 1600)) {
        data->state   = LV_INDEV_STATE_PRESSED;
        data->point.x = x;
        data->point.y = y;
    } else {
        data->state = LV_INDEV_STATE_RELEASED;
    }
}

static uint32_t my_tick() { return millis(); }

// ============================================================
//   STYLE HELPERS
// ============================================================
static void apply_card_style(lv_obj_t* obj) {
    lv_obj_set_style_bg_color(obj,     C_CARD,   0);
    lv_obj_set_style_bg_opa(obj,       LV_OPA_COVER, 0);
    lv_obj_set_style_border_color(obj, C_BORDER, 0);
    lv_obj_set_style_border_width(obj, 1,        0);
    lv_obj_set_style_radius(obj,       10,       0);
    lv_obj_set_style_pad_all(obj,      10,       0);
    lv_obj_clear_flag(obj, LV_OBJ_FLAG_SCROLLABLE);
}

static void apply_dark_btn_style(lv_obj_t* btn) {
    lv_obj_set_style_bg_color(btn,   C_DARK, 0);
    lv_obj_set_style_bg_opa(btn,     LV_OPA_COVER, 0);
    lv_obj_set_style_radius(btn,     10, 0);
    lv_obj_set_style_border_width(btn, 0, 0);
    lv_obj_set_style_shadow_width(btn, 0, 0);
}

static void apply_outline_btn_style(lv_obj_t* btn) {
    lv_obj_set_style_bg_color(btn,     C_WHITE,  0);
    lv_obj_set_style_bg_opa(btn,       LV_OPA_COVER, 0);
    lv_obj_set_style_border_color(btn, C_BORDER, 0);
    lv_obj_set_style_border_width(btn, 1,        0);
    lv_obj_set_style_radius(btn,       10,       0);
    lv_obj_set_style_shadow_width(btn, 0,        0);
}

static void apply_red_btn_style(lv_obj_t* btn) {
    lv_obj_set_style_bg_color(btn,   C_RED, 0);
    lv_obj_set_style_bg_opa(btn,     LV_OPA_COVER, 0);
    lv_obj_set_style_radius(btn,     10, 0);
    lv_obj_set_style_border_width(btn, 0, 0);
    lv_obj_set_style_shadow_width(btn, 0, 0);
}

// ============================================================
//   WIFI INDICATOR — update SEMUA label di array
// ============================================================
static void update_wifi_indicator() {
    if (wifi_lbl_count == 0) return;

    char buf[32];
    lv_color_t color;

    if (WiFi.status() != WL_CONNECTED) {
        snprintf(buf, sizeof(buf), LV_SYMBOL_WIFI " No Signal");
        color = C_RED;
    } else {
        long rssi = WiFi.RSSI();
        if (rssi >= -60)      color = C_GREEN;
        else if (rssi >= -70) color = lv_color_hex(0xFFC107);
        else                  color = C_RED;
        snprintf(buf, sizeof(buf), LV_SYMBOL_WIFI " %d dBm", (int)rssi);
    }

    for (int i = 0; i < wifi_lbl_count; i++) {
        if (wifi_lbls[i]) {
            lv_label_set_text(wifi_lbls[i], buf);
            lv_obj_set_style_text_color(wifi_lbls[i], color, 0);
        }
    }
}

// ============================================================
//   HEADER — otomatis daftarkan WiFi label ke array
// ============================================================
static void make_header(lv_obj_t* parent,
                        bool show_power    = false,
                        bool show_nav_r    = false,
                        bool show_nav_l    = false,
                        bool show_back     = false,
                        bool show_close    = false) {
    lv_obj_t* hdr = lv_obj_create(parent);
    lv_obj_set_size(hdr, TFT_HOR_RES, 38);
    lv_obj_set_pos(hdr, 0, 0);
    lv_obj_set_style_bg_color(hdr,     C_DARK, 0);
    lv_obj_set_style_bg_opa(hdr,       LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(hdr, 0, 0);
    lv_obj_set_style_radius(hdr,       0, 0);
    lv_obj_set_style_pad_all(hdr,      0, 0);
    lv_obj_clear_flag(hdr, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t* lbl_r = lv_label_create(hdr);
    lv_label_set_text(lbl_r, "REMPAH");
    lv_obj_set_style_text_color(lbl_r, C_WHITE, 0);
    lv_obj_set_style_text_font(lbl_r, &lv_font_montserrat_16, 0);
    lv_obj_set_pos(lbl_r, 12, 4);

    lv_obj_t* lbl_s = lv_label_create(hdr);
    lv_label_set_text(lbl_s, "Kontrol Distilasi");
    lv_obj_set_style_text_color(lbl_s, C_TEXT_MUTE, 0);
    lv_obj_set_style_text_font(lbl_s, &lv_font_montserrat_10, 0);
    lv_obj_set_pos(lbl_s, 12, 23);

    // --- WiFi Indicator: daftarkan ke array ---
    if (wifi_lbl_count < MAX_WIFI_LBL) {
        lv_obj_t* wl = lv_label_create(hdr);
        lv_label_set_text(wl, LV_SYMBOL_WIFI " --");
        lv_obj_set_style_text_color(wl, C_TEXT_MUTE, 0);
        lv_obj_set_style_text_font(wl, &lv_font_montserrat_10, 0);
        lv_obj_align(wl, LV_ALIGN_RIGHT_MID, -140, 0);
        wifi_lbls[wifi_lbl_count++] = wl;
    }

    if (show_power) {
        lv_obj_t* pwr = lv_button_create(hdr);
        lv_obj_set_size(pwr, 28, 28);
        lv_obj_align(pwr, LV_ALIGN_RIGHT_MID, -52, 0);
        lv_obj_set_style_bg_color(pwr,   C_RED, 0);
        lv_obj_set_style_radius(pwr,     14,    0);
        lv_obj_set_style_border_width(pwr, 0,   0);
        lv_obj_set_style_shadow_width(pwr, 0,   0);
        lv_obj_t* lbl_p = lv_label_create(pwr);
        lv_label_set_text(lbl_p, LV_SYMBOL_POWER);
        lv_obj_set_style_text_color(lbl_p, C_WHITE, 0);
        lv_obj_center(lbl_p);
        lv_obj_add_event_cb(pwr, [](lv_event_t* e) {
            prevScreenState = screenState;
            show_screen(SCR_SHUTDOWN);
        }, LV_EVENT_CLICKED, nullptr);
    }

    if (show_nav_r) {
        lv_obj_t* btn = lv_button_create(hdr);
        lv_obj_set_size(btn, 36, 28);
        lv_obj_align(btn, LV_ALIGN_RIGHT_MID, -8, 0);
        lv_obj_set_style_bg_color(btn,   C_NAV, 0);
        lv_obj_set_style_radius(btn,     6,     0);
        lv_obj_set_style_border_width(btn, 0,   0);
        lv_obj_set_style_shadow_width(btn, 0,   0);
        lv_obj_t* lbl = lv_label_create(btn);
        lv_label_set_text(lbl, LV_SYMBOL_RIGHT);
        lv_obj_set_style_text_color(lbl, C_WHITE, 0);
        lv_obj_center(lbl);
        lv_obj_add_event_cb(btn, [](lv_event_t* e) {
            show_screen(SCR_PAGE2);
        }, LV_EVENT_CLICKED, nullptr);
    }

    if (show_nav_l) {
        lv_obj_t* btn = lv_button_create(hdr);
        lv_obj_set_size(btn, 36, 28);
        lv_obj_align(btn, LV_ALIGN_RIGHT_MID, -8, 0);
        lv_obj_set_style_bg_color(btn,   C_NAV, 0);
        lv_obj_set_style_radius(btn,     6,     0);
        lv_obj_set_style_border_width(btn, 0,   0);
        lv_obj_set_style_shadow_width(btn, 0,   0);
        lv_obj_t* lbl = lv_label_create(btn);
        lv_label_set_text(lbl, LV_SYMBOL_LEFT);
        lv_obj_set_style_text_color(lbl, C_WHITE, 0);
        lv_obj_center(lbl);
        lv_obj_add_event_cb(btn, [](lv_event_t* e) {
            show_screen(SCR_DASHBOARD);
        }, LV_EVENT_CLICKED, nullptr);
    }

    if (show_back) {
        lv_obj_t* btn = lv_button_create(hdr);
        lv_obj_set_size(btn, 60, 28);
        lv_obj_align(btn, LV_ALIGN_RIGHT_MID, -8, 0);
        lv_obj_set_style_bg_color(btn,   C_NAV, 0);
        lv_obj_set_style_radius(btn,     6,     0);
        lv_obj_set_style_border_width(btn, 0,   0);
        lv_obj_set_style_shadow_width(btn, 0,   0);
        lv_obj_t* lbl = lv_label_create(btn);
        lv_label_set_text(lbl, LV_SYMBOL_LEFT " Kembali");
        lv_obj_set_style_text_color(lbl, C_WHITE, 0);
        lv_obj_set_style_text_font(lbl, &lv_font_montserrat_10, 0);
        lv_obj_center(lbl);
        lv_obj_add_event_cb(btn, [](lv_event_t* e) {
            show_screen(SCR_DASHBOARD);
        }, LV_EVENT_CLICKED, nullptr);
    }

    if (show_close) {
        lv_obj_t* btn = lv_button_create(hdr);
        lv_obj_set_size(btn, 60, 28);
        lv_obj_align(btn, LV_ALIGN_RIGHT_MID, -8, 0);
        apply_outline_btn_style(btn);
        lv_obj_t* lbl = lv_label_create(btn);
        lv_label_set_text(lbl, "Tutup");
        lv_obj_set_style_text_color(lbl, C_DARK, 0);
        lv_obj_set_style_text_font(lbl, &lv_font_montserrat_10, 0);
        lv_obj_center(lbl);
        lv_obj_add_event_cb(btn, [](lv_event_t* e) {
            show_screen(SCR_WELCOME);
        }, LV_EVENT_CLICKED, nullptr);
    }
}

// ============================================================
//   SENSOR CARD FUNCTION
// ============================================================
static SensorCard make_sensor_card(lv_obj_t* parent,
                                   int x, int y, int w, int h,
                                   const char* title,
                                   const char* unit) {
    SensorCard sc;
    sc.card = lv_obj_create(parent);
    lv_obj_set_size(sc.card, w, h);
    lv_obj_set_pos(sc.card, x, y);
    apply_card_style(sc.card);
    lv_obj_set_style_pad_all(sc.card, 8, 0);

    sc.lbl_title = lv_label_create(sc.card);
    lv_label_set_text(sc.lbl_title, title);
    lv_obj_set_style_text_color(sc.lbl_title, C_LABEL, 0);
    lv_obj_set_style_text_font(sc.lbl_title, &lv_font_montserrat_10, 0);
    lv_obj_set_width(sc.lbl_title, w - 50);
    lv_obj_align(sc.lbl_title, LV_ALIGN_TOP_LEFT, 0, 0);

    sc.lbl_status = lv_label_create(sc.card);
    lv_label_set_text(sc.lbl_status, "OFF");
    lv_obj_set_style_text_color(sc.lbl_status, C_RED, 0);
    lv_obj_set_style_text_font(sc.lbl_status, &lv_font_montserrat_10, 0);
    lv_obj_align(sc.lbl_status, LV_ALIGN_TOP_RIGHT, 0, 0);

    sc.lbl_value = lv_label_create(sc.card);
    lv_label_set_text(sc.lbl_value, "---");
    lv_obj_set_style_text_color(sc.lbl_value, C_VALUE, 0);
    lv_obj_set_style_text_font(sc.lbl_value, &lv_font_montserrat_22, 0);
    lv_obj_align(sc.lbl_value, LV_ALIGN_CENTER, 0, 4);

    sc.lbl_unit = lv_label_create(sc.card);
    lv_label_set_text(sc.lbl_unit, unit);
    lv_obj_set_style_text_color(sc.lbl_unit, C_LABEL, 0);
    lv_obj_set_style_text_font(sc.lbl_unit, &lv_font_montserrat_10, 0);
    lv_obj_align(sc.lbl_unit, LV_ALIGN_BOTTOM_MID, 0, 0);

    return sc;
}

// ============================================================
//   STATUS CARD (Page2)
// ============================================================
static lv_obj_t* make_status_card(lv_obj_t* parent,
                                  int x, int y, int w, int h,
                                  int dev_idx,
                                  bool status) {
    lv_obj_t* card = lv_obj_create(parent);
    lv_obj_set_size(card, w, h);
    lv_obj_set_pos(card, x, y);
    apply_card_style(card);
    lv_obj_set_style_pad_all(card, 8, 0);

    lv_obj_t* lbl_t = lv_label_create(card);
    lv_label_set_text(lbl_t, dev_names[dev_idx]);
    lv_obj_set_style_text_color(lbl_t, C_LABEL, 0);
    lv_obj_set_style_text_font(lbl_t, &lv_font_montserrat_10, 0);
    lv_obj_set_width(lbl_t, w - 16);
    lv_obj_align(lbl_t, LV_ALIGN_TOP_MID, 0, 0);

    lv_obj_t* lbl_s = lv_label_create(card);
    lv_label_set_text(lbl_s, status ? "NYALA" : "MATI");
    lv_obj_set_style_text_color(lbl_s, status ? C_GREEN : C_RED, 0);
    lv_obj_set_style_text_font(lbl_s, &lv_font_montserrat_22, 0);
    lv_obj_align(lbl_s, LV_ALIGN_CENTER, 0, 4);

    dev_status_lbl[dev_idx] = lbl_s;

    return card;
}

// ============================================================
//   FORMAT HELPER
// ============================================================
static void fmt_float(char* buf, size_t sz, float v) {
    snprintf(buf, sz, "%.2f", v);
}

// ============================================================
//   REFRESH FUNCTIONS
// ============================================================
static void update_sensor_labels() {
    char buf[16];
    if (lbl_boiler)    { fmt_float(buf, sizeof(buf), suhuBoiler);    lv_label_set_text(lbl_boiler, buf); }
    if (lbl_pendingin) { fmt_float(buf, sizeof(buf), suhuPendingin); lv_label_set_text(lbl_pendingin, buf); }
    if (lbl_gas)       { fmt_float(buf, sizeof(buf), beratGas);      lv_label_set_text(lbl_gas, buf); }
    if (lbl_hasil)     { fmt_float(buf, sizeof(buf), estHasil);      lv_label_set_text(lbl_hasil, buf); }
}

static void refresh_dashboard_cards() {
    bool linkOff = (millis() - lastMqttMsg) > SENSOR_OFF_TIMEOUT;

    for (int i = 0; i < 4; i++) {
        if (!sensor_cards[i].card) continue;

        // Coming soon override — tidak peduli koneksi
        if (sensor_coming_soon[i]) {
            lv_label_set_text(sensor_cards[i].lbl_status, "OFF");
            lv_obj_set_style_text_color(sensor_cards[i].lbl_status, C_BORDER, 0);
            lv_label_set_text(sensor_cards[i].lbl_value, "---");
            lv_obj_set_style_text_font(sensor_cards[i].lbl_value, &lv_font_montserrat_22, 0);
            lv_obj_set_style_text_color(sensor_cards[i].lbl_value, C_TEXT_MUTE, 0);
            continue;  // skip logika normal
        }

        int st = linkOff ? ST_OFF : sensor_status[i];
        SensorCard &sc = sensor_cards[i];

        if (st == ST_ON) {
            lv_label_set_text(sc.lbl_status, "ON");
            lv_obj_set_style_text_color(sc.lbl_status, C_GREEN, 0);
        } else if (st == ST_KAL) {
            lv_label_set_text(sc.lbl_status, "KAL");
            lv_obj_set_style_text_color(sc.lbl_status, C_CHART, 0);
        } else {
            lv_label_set_text(sc.lbl_status, "OFF");
            lv_obj_set_style_text_color(sc.lbl_status, C_RED, 0);
        }

        if (st == ST_KAL) {
            lv_label_set_text(sc.lbl_value, "KALIBRASI");
            lv_obj_set_style_text_font(sc.lbl_value, &lv_font_montserrat_14, 0);
            lv_obj_set_style_text_color(sc.lbl_value, C_CHART, 0);
        } else if (st == ST_OFF) {
            lv_label_set_text(sc.lbl_value, "---");
            lv_obj_set_style_text_font(sc.lbl_value, &lv_font_montserrat_22, 0);
            lv_obj_set_style_text_color(sc.lbl_value, C_VALUE, 0);
        } else {
            char buf[16];
            fmt_float(buf, sizeof(buf), *sensor_val[i]);
            lv_label_set_text(sc.lbl_value, buf);
            lv_obj_set_style_text_font(sc.lbl_value, &lv_font_montserrat_22, 0);
            lv_obj_set_style_text_color(sc.lbl_value, C_VALUE, 0);
        }
    }
}

static void refresh_page2_cards() {
    for (int i = 0; i < 4; i++) {
        if (!dev_status_lbl[i]) continue;
        bool on = device_status[i];
        lv_label_set_text(dev_status_lbl[i], on ? "NYALA" : "MATI");
        lv_obj_set_style_text_color(dev_status_lbl[i], on ? C_GREEN : C_RED, 0);
    }
}

static void update_weight_label() {
    if (!lbl_weight_val) return;
    char buf[12];
    snprintf(buf, sizeof(buf), "%.1f KG", beratMuatan);
    lv_label_set_text(lbl_weight_val, buf);
}

// ============================================================
//   BUILD SCREENS
// ============================================================
static void build_notif_screen() {
    scr_notif = lv_obj_create(nullptr);
    lv_obj_set_size(scr_notif, TFT_HOR_RES, TFT_VER_RES);
    lv_obj_set_style_bg_color(scr_notif, C_BG, 0);
    lv_obj_set_style_bg_opa(scr_notif, LV_OPA_COVER, 0);
    lv_obj_clear_flag(scr_notif, LV_OBJ_FLAG_SCROLLABLE);

    make_header(scr_notif, false, false, false, false, true);

    lv_obj_t* card = lv_obj_create(scr_notif);
    lv_obj_set_size(card, TFT_HOR_RES - 24, TFT_VER_RES - 38 - 16);
    lv_obj_set_pos(card, 12, 38 + 8);
    apply_card_style(card);

    lbl_notif_msg = lv_label_create(card);
    lv_label_set_text(lbl_notif_msg, "MENUNGGU JARINGAN...");
    lv_obj_set_style_text_color(lbl_notif_msg, C_VALUE, 0);
    lv_obj_set_style_text_font(lbl_notif_msg, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_align(lbl_notif_msg, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_width(lbl_notif_msg, TFT_HOR_RES - 24 - 20);
    lv_obj_align(lbl_notif_msg, LV_ALIGN_CENTER, 0, 0);
}

static void build_welcome_screen() {
    scr_welcome = lv_obj_create(nullptr);
    lv_obj_set_size(scr_welcome, TFT_HOR_RES, TFT_VER_RES);
    lv_obj_set_style_bg_color(scr_welcome, C_BG, 0);
    lv_obj_set_style_bg_opa(scr_welcome, LV_OPA_COVER, 0);
    lv_obj_clear_flag(scr_welcome, LV_OBJ_FLAG_SCROLLABLE);

    make_header(scr_welcome);

    lv_obj_t* lbl_m = lv_label_create(scr_welcome);
    lv_label_set_text(lbl_m, "unit_kapulaga_1");
    lv_obj_set_style_text_color(lbl_m, C_DARK, 0);
    lv_obj_set_style_text_font(lbl_m, &lv_font_montserrat_20, 0);
    lv_obj_align(lbl_m, LV_ALIGN_TOP_MID, 0, 56);

    lv_obj_t* btn = lv_button_create(scr_welcome);
    lv_obj_set_size(btn, 230, 46);
    lv_obj_align(btn, LV_ALIGN_TOP_MID, 0, 96);
    apply_dark_btn_style(btn);

    lv_obj_t* lbl_b = lv_label_create(btn);
    lv_label_set_text(lbl_b, LV_SYMBOL_PLUS "  Mulai Batch Baru");
    lv_obj_set_style_text_color(lbl_b, C_WHITE, 0);
    lv_obj_set_style_text_font(lbl_b, &lv_font_montserrat_14, 0);
    lv_obj_center(lbl_b);

    lv_obj_add_event_cb(btn, [](lv_event_t* e) {
        beratMuatan = 1.0f;
        update_weight_label();
        show_screen(SCR_WEIGHT);
    }, LV_EVENT_CLICKED, nullptr);
}

static void build_weight_screen() {
    scr_weight = lv_obj_create(nullptr);
    lv_obj_set_size(scr_weight, TFT_HOR_RES, TFT_VER_RES);
    lv_obj_set_style_bg_color(scr_weight, C_BG, 0);
    lv_obj_set_style_bg_opa(scr_weight, LV_OPA_COVER, 0);
    lv_obj_clear_flag(scr_weight, LV_OBJ_FLAG_SCROLLABLE);

    make_header(scr_weight);

    // ── Satu card: tombol +/- , nilai berat, dan tombol aksi ──
    lv_obj_t* card = lv_obj_create(scr_weight);
    lv_obj_set_size(card, TFT_HOR_RES - 24, 156);
    lv_obj_set_pos(card, 12, 46);
    apply_card_style(card);

    lv_obj_t* lbl_title = lv_label_create(card);
    lv_label_set_text(lbl_title, "BERAT MUATAN");
    lv_obj_set_style_text_color(lbl_title, C_LABEL, 0);
    lv_obj_set_style_text_font(lbl_title, &lv_font_montserrat_10, 0);
    lv_obj_align(lbl_title, LV_ALIGN_TOP_MID, 0, 0);

    // Tombol kurang (-) — step 0,5 kg
    lv_obj_t* btn_dec = lv_button_create(card);
    lv_obj_set_size(btn_dec, 44, 44);
    lv_obj_align(btn_dec, LV_ALIGN_TOP_MID, -64, 18);
    lv_obj_set_style_bg_color(btn_dec,   C_BLUE, 0);
    lv_obj_set_style_radius(btn_dec,     22,     0);
    lv_obj_set_style_border_width(btn_dec, 0,    0);
    lv_obj_set_style_shadow_width(btn_dec, 0,    0);
    lv_obj_t* lbl_dec = lv_label_create(btn_dec);
    lv_label_set_text(lbl_dec, LV_SYMBOL_LEFT);
    lv_obj_set_style_text_color(lbl_dec, C_WHITE, 0);
    lv_obj_center(lbl_dec);
    lv_obj_add_event_cb(btn_dec, [](lv_event_t* e) {
        if (beratMuatan > 0.5f) { beratMuatan -= 0.5f; update_weight_label(); }
    }, LV_EVENT_CLICKED, nullptr);

    // Nilai berat di tengah
    lbl_weight_val = lv_label_create(card);
    lv_label_set_text(lbl_weight_val, "1.0 KG");
    lv_obj_set_style_text_color(lbl_weight_val, C_DARK, 0);
    lv_obj_set_style_text_font(lbl_weight_val, &lv_font_montserrat_28, 0);
    lv_obj_align(lbl_weight_val, LV_ALIGN_TOP_MID, 0, 20);

    // Tombol tambah (+) — step 0,5 kg
    lv_obj_t* btn_inc = lv_button_create(card);
    lv_obj_set_size(btn_inc, 44, 44);
    lv_obj_align(btn_inc, LV_ALIGN_TOP_MID, 64, 18);
    lv_obj_set_style_bg_color(btn_inc,   C_BLUE, 0);
    lv_obj_set_style_radius(btn_inc,     22,     0);
    lv_obj_set_style_border_width(btn_inc, 0,    0);
    lv_obj_set_style_shadow_width(btn_inc, 0,    0);
    lv_obj_t* lbl_inc = lv_label_create(btn_inc);
    lv_label_set_text(lbl_inc, LV_SYMBOL_RIGHT);
    lv_obj_set_style_text_color(lbl_inc, C_WHITE, 0);
    lv_obj_center(lbl_inc);
    lv_obj_add_event_cb(btn_inc, [](lv_event_t* e) {
        if (beratMuatan < 99.0f) { beratMuatan += 0.5f; update_weight_label(); }
    }, LV_EVENT_CLICKED, nullptr);

    // ── Baris tombol aksi (masih dalam card yang sama) ──
    int btn_y = 78;
    int btn_w = (TFT_HOR_RES - 24 - 24 - 8) / 2;

    lv_obj_t* btn_cancel = lv_button_create(card);
    lv_obj_set_size(btn_cancel, btn_w, 38);
    lv_obj_set_pos(btn_cancel, 12, btn_y);
    apply_outline_btn_style(btn_cancel);
    lv_obj_t* lbl_c = lv_label_create(btn_cancel);
    lv_label_set_text(lbl_c, "Batalkan");
    lv_obj_set_style_text_color(lbl_c, C_DARK, 0);
    lv_obj_set_style_text_font(lbl_c, &lv_font_montserrat_14, 0);
    lv_obj_center(lbl_c);
    lv_obj_add_event_cb(btn_cancel, [](lv_event_t* e) {
        show_screen(SCR_WELCOME);
    }, LV_EVENT_CLICKED, nullptr);

    // Tombol "Selanjutnya" = mulai sistem (POWER_ON) → kirim command MQTT
    lv_obj_t* btn_next = lv_button_create(card);
    lv_obj_set_size(btn_next, btn_w, 38);
    lv_obj_set_pos(btn_next, 12 + btn_w + 8, btn_y);
    apply_dark_btn_style(btn_next);
    lv_obj_t* lbl_n = lv_label_create(btn_next);
    lv_label_set_text(lbl_n, "Selanjutnya");
    lv_obj_set_style_text_color(lbl_n, C_WHITE, 0);
    lv_obj_set_style_text_font(lbl_n, &lv_font_montserrat_14, 0);
    lv_obj_center(lbl_n);
    lv_obj_add_event_cb(btn_next, [](lv_event_t* e) {
        // POWER_ON (dari PowerPanel) → bahasa firmware "mulai"
        publishAction("mulai");
        show_screen(SCR_DASHBOARD);
    }, LV_EVENT_CLICKED, nullptr);
}

static void build_dashboard() {
    scr_dash = lv_obj_create(nullptr);
    lv_obj_set_size(scr_dash, TFT_HOR_RES, TFT_VER_RES);
    lv_obj_set_style_bg_color(scr_dash, C_BG, 0);
    lv_obj_set_style_bg_opa(scr_dash, LV_OPA_COVER, 0);
    lv_obj_clear_flag(scr_dash, LV_OBJ_FLAG_SCROLLABLE);

    make_header(scr_dash, true, true);

    const int cw = 148, ch = 88, gap = 8;
    const int x1 = 8,  x2 = 8 + cw + gap;
    const int y1 = 46, y2 = 46 + ch + gap;

    sensor_cards[0] = make_sensor_card(scr_dash, x1, y1, cw, ch, "SUHU BOILER",    "\xC2\xB0" "C");
    sensor_cards[1] = make_sensor_card(scr_dash, x2, y1, cw, ch, "SUHU PENDINGIN", "\xC2\xB0" "C");
    sensor_cards[2] = make_sensor_card(scr_dash, x1, y2, cw, ch, "BERAT GAS",      "kg");
    sensor_cards[3] = make_sensor_card(scr_dash, x2, y2, cw, ch, "EST. HASIL",     "% vol");

    lbl_boiler    = sensor_cards[0].lbl_value;
    lbl_pendingin = sensor_cards[1].lbl_value;
    lbl_gas       = sensor_cards[2].lbl_value;
    lbl_hasil     = sensor_cards[3].lbl_value;

    lv_obj_add_event_cb(sensor_cards[0].card, [](lv_event_t* e) {
        detailCardIdx = 0; show_screen(SCR_DETAIL);
    }, LV_EVENT_CLICKED, nullptr);
    lv_obj_add_event_cb(sensor_cards[1].card, [](lv_event_t* e) {
        detailCardIdx = 1; show_screen(SCR_DETAIL);
    }, LV_EVENT_CLICKED, nullptr);
    lv_obj_add_event_cb(sensor_cards[2].card, [](lv_event_t* e) {
        detailCardIdx = 2; show_screen(SCR_DETAIL);
    }, LV_EVENT_CLICKED, nullptr);
    lv_obj_add_event_cb(sensor_cards[3].card, [](lv_event_t* e) {
        detailCardIdx = 3; show_screen(SCR_DETAIL);
    }, LV_EVENT_CLICKED, nullptr);

    lv_obj_add_event_cb(scr_dash, [](lv_event_t* e) {
        lv_dir_t dir = lv_indev_get_gesture_dir(lv_indev_get_act());
        if (dir == LV_DIR_LEFT) show_screen(SCR_PAGE2);
    }, LV_EVENT_GESTURE, nullptr);
}

static void build_page2() {
    scr_page2 = lv_obj_create(nullptr);
    lv_obj_set_size(scr_page2, TFT_HOR_RES, TFT_VER_RES);
    lv_obj_set_style_bg_color(scr_page2, C_BG, 0);
    lv_obj_set_style_bg_opa(scr_page2, LV_OPA_COVER, 0);
    lv_obj_clear_flag(scr_page2, LV_OBJ_FLAG_SCROLLABLE);

    make_header(scr_page2, true, false, true);

    const int cw = 148, ch = 88, gap = 8;
    const int x1 = 8,  x2 = 8 + cw + gap;
    const int y1 = 46, y2 = 46 + ch + gap;

    make_status_card(scr_page2, x1, y1, cw, ch, 0, device_status[0]);
    make_status_card(scr_page2, x2, y1, cw, ch, 1, device_status[1]);
    make_status_card(scr_page2, x1, y2, cw, ch, 2, device_status[2]);
    make_status_card(scr_page2, x2, y2, cw, ch, 3, device_status[3]);

    lv_obj_add_event_cb(scr_page2, [](lv_event_t* e) {
        lv_dir_t dir = lv_indev_get_gesture_dir(lv_indev_get_act());
        if (dir == LV_DIR_RIGHT) show_screen(SCR_DASHBOARD);
        if (dir == LV_DIR_LEFT)  show_screen(SCR_SENSORS);
    }, LV_EVENT_GESTURE, nullptr);
}

static void build_sensors_screen() {
    scr_sensors = lv_obj_create(nullptr);
    lv_obj_set_size(scr_sensors, TFT_HOR_RES, TFT_VER_RES);
    lv_obj_set_style_bg_color(scr_sensors, C_BG, 0);
    lv_obj_set_style_bg_opa(scr_sensors, LV_OPA_COVER, 0);
    lv_obj_clear_flag(scr_sensors, LV_OBJ_FLAG_SCROLLABLE);

    make_header(scr_sensors);

    lv_obj_t* btn_back = lv_button_create(scr_sensors);
    lv_obj_set_size(btn_back, 36, 28);
    lv_obj_align(btn_back, LV_ALIGN_TOP_RIGHT, -8, 5);
    lv_obj_set_style_bg_color(btn_back, C_NAV, 0);
    lv_obj_set_style_radius(btn_back, 6, 0);
    lv_obj_set_style_border_width(btn_back, 0, 0);
    lv_obj_set_style_shadow_width(btn_back, 0, 0);
    lv_obj_t* lbl_b = lv_label_create(btn_back);
    lv_label_set_text(lbl_b, LV_SYMBOL_LEFT);
    lv_obj_set_style_text_color(lbl_b, C_WHITE, 0);
    lv_obj_center(lbl_b);
    lv_obj_add_event_cb(btn_back, [](lv_event_t* e) {
        show_screen(SCR_PAGE2);
    }, LV_EVENT_CLICKED, nullptr);

    const int cw = 148, ch = 88, gap = 8;
    const int x1 = 8,  x2 = 8 + cw + gap;
    const int y1 = 46, y2 = 46 + ch + gap;

    make_status_card(scr_sensors, x1, y1, cw, ch, 0, true);
    make_status_card(scr_sensors, x2, y1, cw, ch, 1, true);
    make_status_card(scr_sensors, x1, y2, cw, ch, 2, true);
    make_status_card(scr_sensors, x2, y2, cw, ch, 3, false);

    lv_obj_add_event_cb(scr_sensors, [](lv_event_t* e) {
        lv_dir_t dir = lv_indev_get_gesture_dir(lv_indev_get_act());
        if (dir == LV_DIR_RIGHT) show_screen(SCR_PAGE2);
    }, LV_EVENT_GESTURE, nullptr);
}

static const char* detail_names[] = {
    "SUHU BOILER", "SUHU PENDINGIN AIR", "BERAT GAS", "EST. HASIL"
};
static const char* detail_units[] = { "\xC2\xB0" "C", "\xC2\xB0" "C", "bar", "% vol" };

static void build_detail_screen() {
    scr_detail = lv_obj_create(nullptr);
    lv_obj_set_size(scr_detail, TFT_HOR_RES, TFT_VER_RES);
    lv_obj_set_style_bg_color(scr_detail, C_BG, 0);
    lv_obj_set_style_bg_opa(scr_detail, LV_OPA_COVER, 0);
    lv_obj_clear_flag(scr_detail, LV_OBJ_FLAG_SCROLLABLE);

    make_header(scr_detail, false, false, false, true);

    const int card_w = TFT_HOR_RES - 24;
    const int card_h = TFT_VER_RES - 38 - 16;
    lv_obj_t* card = lv_obj_create(scr_detail);
    lv_obj_set_size(card, card_w, card_h);
    lv_obj_set_pos(card, 12, 46);
    apply_card_style(card);
    lv_obj_set_style_pad_all(card, 10, 0);

    lbl_detail_name = lv_label_create(card);
    lv_label_set_text(lbl_detail_name, "SUHU BOILER");
    lv_obj_set_style_text_color(lbl_detail_name, C_LABEL, 0);
    lv_obj_set_style_text_font(lbl_detail_name, &lv_font_montserrat_10, 0);
    lv_obj_align(lbl_detail_name, LV_ALIGN_TOP_LEFT, 0, 0);

    lbl_detail_val = lv_label_create(card);
    lv_label_set_text(lbl_detail_val, "0.00");
    lv_obj_set_style_text_color(lbl_detail_val, C_VALUE, 0);
    lv_obj_set_style_text_font(lbl_detail_val, &lv_font_montserrat_20, 0);
    lv_obj_align(lbl_detail_val, LV_ALIGN_TOP_RIGHT, 0, 0);

    lv_obj_t* line = lv_line_create(card);
    static lv_point_precise_t pts[2] = {{0,0},{card_w - 20, 0}};
    lv_line_set_points(line, pts, 2);
    lv_obj_set_style_line_color(line, C_BORDER, 0);
    lv_obj_set_style_line_width(line, 1, 0);
    lv_obj_align(line, LV_ALIGN_TOP_LEFT, 0, 24);

    chart_obj = lv_chart_create(card);
    lv_obj_set_size(chart_obj, card_w - 20, (card_h - 20) - 32);
    lv_obj_align(chart_obj, LV_ALIGN_BOTTOM_MID, 0, 0);
    lv_chart_set_type(chart_obj, LV_CHART_TYPE_LINE);
    lv_chart_set_point_count(chart_obj, CHART_POINTS);
    lv_chart_set_div_line_count(chart_obj, 3, 5);
    lv_obj_set_style_bg_color(chart_obj, C_CARD, 0);
    lv_obj_set_style_border_width(chart_obj, 0, 0);
    lv_obj_set_style_line_color(chart_obj, C_BORDER, LV_PART_MAIN);
    lv_obj_clear_flag(chart_obj, LV_OBJ_FLAG_SCROLLABLE);

    detail_ser = lv_chart_add_series(chart_obj, C_CHART, LV_CHART_AXIS_PRIMARY_Y);

    lv_obj_set_style_size(chart_obj, 0, 0, LV_PART_INDICATOR);
}

static void update_detail_chart() {
    if (!scr_detail || !chart_obj) return;

    lv_label_set_text(lbl_detail_name, detail_names[detailCardIdx]);

    bool linkOff = (millis() - lastMqttMsg) > SENSOR_OFF_TIMEOUT;
    int st = linkOff ? ST_OFF : sensor_status[detailCardIdx];

    char buf[32];
    if (st == ST_KAL) {
        snprintf(buf, sizeof(buf), "KALIBRASI");
        lv_obj_set_style_text_color(lbl_detail_val, C_CHART, 0);
        lv_obj_set_style_text_font(lbl_detail_val, &lv_font_montserrat_14, 0);
    } else if (st == ST_OFF) {
        snprintf(buf, sizeof(buf), "--- (OFFLINE)");
        lv_obj_set_style_text_color(lbl_detail_val, C_RED, 0);
        lv_obj_set_style_text_font(lbl_detail_val, &lv_font_montserrat_14, 0);
    } else {
        float v = *sensor_val[detailCardIdx];
        snprintf(buf, sizeof(buf), "%.2f %s", v, detail_units[detailCardIdx]);
        lv_obj_set_style_text_color(lbl_detail_val, C_VALUE, 0);
        lv_obj_set_style_text_font(lbl_detail_val, &lv_font_montserrat_20, 0);
    }
    lv_label_set_text(lbl_detail_val, buf);

    lv_chart_set_all_value(chart_obj, detail_ser, LV_CHART_POINT_NONE);
    if (st == ST_ON) {
        for (int i = 0; i < chartCount; i++) {
            lv_chart_set_next_value(chart_obj, detail_ser,
                                    (int32_t)(chartRaw[detailCardIdx][i] * 10));
        }
        lv_chart_set_series_color(chart_obj, detail_ser, C_CHART);
    } else if (st == ST_KAL) {
        lv_chart_set_series_color(chart_obj, detail_ser, lv_color_hex(0xFFC107));
    } else {
        lv_chart_set_series_color(chart_obj, detail_ser, C_BORDER);
    }
    lv_chart_refresh(chart_obj);
}

static void build_shutdown_screen() {
    scr_shutdown = lv_obj_create(nullptr);
    lv_obj_set_size(scr_shutdown, TFT_HOR_RES, TFT_VER_RES);
    lv_obj_set_style_bg_color(scr_shutdown, C_BG, 0);
    lv_obj_set_style_bg_opa(scr_shutdown, LV_OPA_COVER, 0);
    lv_obj_clear_flag(scr_shutdown, LV_OBJ_FLAG_SCROLLABLE);

    make_header(scr_shutdown);

    lv_obj_t* card = lv_obj_create(scr_shutdown);
    lv_obj_set_size(card, TFT_HOR_RES - 24, TFT_VER_RES - 38 - 16);
    lv_obj_set_pos(card, 12, 46);
    apply_card_style(card);

    lv_obj_t* lbl_q = lv_label_create(card);
    lv_label_set_text(lbl_q, "Apakah Anda yakin menjalankan");
    lv_obj_set_style_text_color(lbl_q, C_LABEL, 0);
    lv_obj_set_style_text_font(lbl_q, &lv_font_montserrat_12, 0);
    lv_obj_set_style_text_align(lbl_q, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_width(lbl_q, TFT_HOR_RES - 24 - 20);
    lv_obj_align(lbl_q, LV_ALIGN_TOP_MID, 0, 14);

    lv_obj_t* lbl_e = lv_label_create(card);
    lv_label_set_text(lbl_e, "EMERGENCY STOP?");
    lv_obj_set_style_text_color(lbl_e, C_RED, 0);
    lv_obj_set_style_text_font(lbl_e, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_align(lbl_e, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_width(lbl_e, TFT_HOR_RES - 24 - 20);
    lv_obj_align(lbl_e, LV_ALIGN_TOP_MID, 0, 36);

    int btn_w = (TFT_HOR_RES - 24 - 20 - 8) / 2;

    lv_obj_t* btn_back = lv_button_create(card);
    lv_obj_set_size(btn_back, btn_w, 40);
    lv_obj_align(btn_back, LV_ALIGN_BOTTOM_LEFT, 0, 0);
    apply_outline_btn_style(btn_back);
    lv_obj_t* lbl_bk = lv_label_create(btn_back);
    lv_label_set_text(lbl_bk, "Kembali");
    lv_obj_set_style_text_color(lbl_bk, C_DARK, 0);
    lv_obj_set_style_text_font(lbl_bk, &lv_font_montserrat_14, 0);
    lv_obj_center(lbl_bk);
    lv_obj_add_event_cb(btn_back, [](lv_event_t* e) {
        show_screen(prevScreenState);
    }, LV_EVENT_CLICKED, nullptr);

    lv_obj_t* btn_kill = lv_button_create(card);
    lv_obj_set_size(btn_kill, btn_w, 40);
    lv_obj_align(btn_kill, LV_ALIGN_BOTTOM_RIGHT, 0, 0);
    apply_red_btn_style(btn_kill);
    lv_obj_t* lbl_k = lv_label_create(btn_kill);
    lv_label_set_text(lbl_k, "Matikan");
    lv_obj_set_style_text_color(lbl_k, C_WHITE, 0);
    lv_obj_set_style_text_font(lbl_k, &lv_font_montserrat_14, 0);
    lv_obj_center(lbl_k);
    lv_obj_add_event_cb(btn_kill, [](lv_event_t* e) {
        Serial.println("EMERGENCY STOP dieksekusi");
        publishAction("mati");
        show_screen(SCR_WELCOME);
    }, LV_EVENT_CLICKED, nullptr);
}

// ============================================================
//   BUILD ALL
// ============================================================
static void build_all_screens() {
    build_notif_screen();
    build_welcome_screen();
    build_weight_screen();
    build_dashboard();
    build_page2();
    build_sensors_screen();
    build_detail_screen();
    build_shutdown_screen();
}

// ============================================================
//   SHOW SCREEN
// ============================================================
static lv_obj_t* get_screen_obj(ScreenState s) {
    switch (s) {
        case SCR_NOTIF_WAIT:
        case SCR_NOTIF_OK:
        case SCR_NOTIF_FAIL: return scr_notif;
        case SCR_WELCOME:    return scr_welcome;
        case SCR_WEIGHT:     return scr_weight;
        case SCR_DASHBOARD:  return scr_dash;
        case SCR_PAGE2:      return scr_page2;
        case SCR_SENSORS:    return scr_sensors;
        case SCR_DETAIL:     return scr_detail;
        case SCR_SHUTDOWN:   return scr_shutdown;
        default:             return scr_notif;
    }
}

static void show_screen(ScreenState next) {
    if (next == SCR_NOTIF_WAIT && lbl_notif_msg)
        lv_label_set_text(lbl_notif_msg, "MENUNGGU JARINGAN...");
    if (next == SCR_NOTIF_OK && lbl_notif_msg)
        lv_label_set_text(lbl_notif_msg, "BERHASIL TERHUBUNG.");
    if (next == SCR_NOTIF_FAIL && lbl_notif_msg)
        lv_label_set_text(lbl_notif_msg, "TERPUTUS DARI JARINGAN");

    if (next == SCR_DETAIL)    update_detail_chart();
    if (next == SCR_DASHBOARD) refresh_dashboard_cards();
    if (next == SCR_PAGE2)     refresh_page2_cards();

    screenState = next;
    lv_obj_t* target = get_screen_obj(next);
    if (!target) return;

    if (next == SCR_NOTIF_WAIT || next == SCR_NOTIF_OK || next == SCR_NOTIF_FAIL) {
        lv_screen_load_anim(target, LV_SCR_LOAD_ANIM_FADE_IN, 150, 0, false);
    } else if (next == SCR_PAGE2) {
        lv_screen_load_anim(target, LV_SCR_LOAD_ANIM_MOVE_LEFT, 200, 0, false);
    } else if (next == SCR_DASHBOARD && prevScreenState == SCR_PAGE2) {
        lv_screen_load_anim(target, LV_SCR_LOAD_ANIM_MOVE_RIGHT, 200, 0, false);
    } else {
        lv_screen_load_anim(target, LV_SCR_LOAD_ANIM_FADE_IN, 200, 0, false);
    }
}

// ============================================================
//   MQTT CALLBACK
// ============================================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String msg = "";
    for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
    lastMqttMsg = millis();

    // ── TELEMETRY ──────────────────────────────────────────────────────
    if (strcmp(topic, MQTT_TELEM) == 0) {

        // Parse JSON sederhana tanpa library tambahan
        auto getFloat = [&](const char* key) -> float {
            String search = "\"" + String(key) + "\":";
            int idx = msg.indexOf(search);
            if (idx < 0) return 0.0f;
            return msg.substring(idx + search.length()).toFloat();
        };

        auto getBool = [&](const char* key) -> bool {
            String search = "\"" + String(key) + "\":";
            int idx = msg.indexOf(search);
            if (idx < 0) return false;
            return msg.substring(idx + search.length()).startsWith("true");
        };

        // ── Mapping field JSON ke variabel ─────────────────────────────
        suhuBoiler    = getFloat("boiler_temp_c");  // aktif
        // suhuPendingin — coming soon, tidak di-update dari JSON
        beratGas      = getFloat("gas_mass_kg");    // aktif
        estHasil      = getFloat("drip_count");     // aktif (sementara)

        // ── flame_lit → device_status[1] (PEMANTIK API) ───────────────
        bool flameOn      = getBool("flame_lit");
        device_status[1]  = flameOn;
        if (screenState == SCR_PAGE2) refresh_page2_cards();

        // ── Update sensor_status, hormati coming soon ──────────────────
        float vals[4] = { suhuBoiler, suhuPendingin, beratGas, estHasil };
        for (int i = 0; i < 4; i++) {
            if (sensor_coming_soon[i]) {
                sensor_status[i] = ST_OFF;   // paksa OFF permanen
            } else {
                sensor_status[i] = (vals[i] < 0) ? ST_KAL : ST_ON;
            }
        }

        // ── Update chart (hanya sensor aktif) ─────────────────────────
        float chartVals[4] = { suhuBoiler, 0.0f, beratGas, estHasil };
        // index 1 (pendingin) diisi 0 karena coming soon

        if (chartCount < CHART_POINTS) {
            int idx = chartCount++;
            for (int i = 0; i < 4; i++) chartRaw[i][idx] = chartVals[i];
        } else {
            for (int i = 0; i < CHART_POINTS - 1; i++) {
                chartRaw[0][i] = chartRaw[0][i+1];
                chartRaw[1][i] = chartRaw[1][i+1];
                chartRaw[2][i] = chartRaw[2][i+1];
                chartRaw[3][i] = chartRaw[3][i+1];
            }
            for (int i = 0; i < 4; i++)
                chartRaw[i][CHART_POINTS-1] = chartVals[i];
        }

        if (screenState == SCR_DASHBOARD) refresh_dashboard_cards();
        if (screenState == SCR_DETAIL)    update_detail_chart();
    }

    // ── STATE (tidak berubah) ──────────────────────────────────────────
    else if (strcmp(topic, MQTT_STATE) == 0) {
        int s[4] = {0, 0, 0, 0};
        int a = msg.indexOf(',');
        int b = (a > 0) ? msg.indexOf(',', a + 1) : -1;
        int c = (b > 0) ? msg.indexOf(',', b + 1) : -1;
        if (a > 0 && b > 0 && c > 0) {
            s[0] = msg.substring(0, a).toInt();
            s[1] = msg.substring(a+1, b).toInt();
            s[2] = msg.substring(b+1, c).toInt();
            s[3] = msg.substring(c+1).toInt();
            for (int i = 0; i < 4; i++) device_status[i] = (s[i] != 0);
            if (screenState == SCR_PAGE2) refresh_page2_cards();
        }
    }
}

// ============================================================
//   MQTT RECONNECT
// ============================================================
void reconnectMQTT() {
    int attempts = 0;
    while (!mqttClient.connected() && attempts < 3) {
        Serial.print("Menghubungkan MQTT...");
        if (mqttClient.connect("ESP32_REMPAH", mqtt_user, mqtt_pass)) {
            Serial.println("OK");
            mqttClient.subscribe(MQTT_SUB_WILD);
            Serial.printf("Subscribed to %s\n", MQTT_SUB_WILD);
        } else {
            Serial.printf("Gagal (%d)\n", mqttClient.state());
            delay(3000);
        }
        attempts++;
    }
}

// ============================================================
//   MQTT COMMAND PUBLISHER
// ============================================================
static void publishCommand(const char* cmd, const char* device, int val) {
    if (!mqttClient.connected()) {
        Serial.println("MQTT belum terkoneksi, command ditunda");
        return;
    }
    char payload[128];
    if (device == nullptr) {
        snprintf(payload, sizeof(payload), "{\"cmd\":\"%s\"}", cmd);
    } else {
        snprintf(payload, sizeof(payload),
                 "{\"cmd\":\"%s\",\"dev\":\"%s\",\"val\":%d}", cmd, device, val);
    }
    mqttClient.publish(MQTT_CMD, payload);
    Serial.printf("CMD >> %s : %s\n", MQTT_CMD, payload);
}

// ============================================================
//   MQTT ACTION PUBLISHER — kontrak firmware (ticket 50)
//   Mengirim action bahasa firmware: "mulai" / "mati".
//   Dipakai tombol "Selanjutnya" (POWER_ON) dan shutdown (mati).
// ============================================================
static void publishAction(const char* action) {
    if (!mqttClient.connected()) {
        Serial.println("MQTT belum terkoneksi, command ditunda");
        return;
    }
    char payload[96];
    snprintf(payload, sizeof(payload), "{\"action\":\"%s\"}", action);
    mqttClient.publish(MQTT_CMD, payload);
    Serial.printf("CMD >> %s : %s\n", MQTT_CMD, payload);
}

// ============================================================
//   SETUP
// ============================================================
void setup() {
    Serial.begin(115200);

    tft.init();
    tft.setRotation(1);
    tft.invertDisplay(false);
    tft.fillScreen(TFT_BLACK);
    tft.setTouch(calData);

    lv_init();
    lv_tick_set_cb(my_tick);

    lv_display_t* disp = lv_display_create(TFT_HOR_RES, TFT_VER_RES);
    lv_display_set_flush_cb(disp, my_disp_flush);
    lv_display_set_buffers(disp, draw_buf, NULL, sizeof(draw_buf),
                           LV_DISPLAY_RENDER_MODE_PARTIAL);

    lv_indev_t* indev = lv_indev_create();
    lv_indev_set_type(indev, LV_INDEV_TYPE_POINTER);
    lv_indev_set_read_cb(indev, my_touchpad_read);

    build_all_screens();
    show_screen(SCR_NOTIF_WAIT);

    WiFi.begin(ssid, password);
    wifiStartTime = millis();
}

// ============================================================
//   LOOP
// ============================================================
void loop() {
    lv_timer_handler();

    // Update WiFi indicator — jalan di SEMUA state
    if (millis() - lastWifiUpdate > WIFI_UPDATE_INTERVAL) {
        lastWifiUpdate = millis();
        update_wifi_indicator();
    }

    // Refresh UI dashboard/detail/page2 tiap 500ms
    if (millis() - lastUiCheck > 500) {
        lastUiCheck = millis();
        if (screenState == SCR_DASHBOARD) refresh_dashboard_cards();
        if (screenState == SCR_DETAIL)    update_detail_chart();
        if (screenState == SCR_PAGE2)     refresh_page2_cards();
    }

    // --- WIFI WAIT ---
    if (screenState == SCR_NOTIF_WAIT) {
        if (WiFi.status() == WL_CONNECTED) {
            Serial.println("WiFi OK");
            secureClient.setInsecure();
            mqttClient.setServer(mqtt_server, mqtt_port);
            mqttClient.setCallback(mqttCallback);
            screenState = SCR_NOTIF_OK;
            show_screen(SCR_NOTIF_OK);
            notifOkTimer = millis();
        } else if (millis() - wifiStartTime > wifiTimeout) {
            show_screen(SCR_NOTIF_FAIL);
            Serial.println("WiFi gagal");
        }
        delay(50);
        return;
    }

    // --- AUTO-TUTUP NOTIF OK ---
    if (screenState == SCR_NOTIF_OK) {
        if (millis() - notifOkTimer > 2000) show_screen(SCR_WELCOME);
        delay(50);
        return;
    }

    // --- CEK WIFI PUTUS ---
    if (screenState == SCR_DASHBOARD || screenState == SCR_PAGE2 ||
        screenState == SCR_DETAIL    || screenState == SCR_SHUTDOWN ||
        screenState == SCR_SENSORS) {
        if (WiFi.status() != WL_CONNECTED) {
            show_screen(SCR_NOTIF_FAIL);
            Serial.println("WiFi terputus!");
            delay(100);
            return;
        }
    }

    // --- MQTT LOOP ---
    if (screenState == SCR_DASHBOARD || screenState == SCR_PAGE2 ||
        screenState == SCR_DETAIL    || screenState == SCR_SENSORS) {
        if (!mqttClient.connected()) reconnectMQTT();
        mqttClient.loop();
    }

    delay(5);
}