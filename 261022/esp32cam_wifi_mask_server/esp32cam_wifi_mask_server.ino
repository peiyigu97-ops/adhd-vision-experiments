/*
  ESP32CAM WiFi + OLED mask server
  ================================
  261022 -- 独立于 261003/260919/260918 那几份旧文档，这是新的一轮联调固件，
  目的是替换掉 esp32_camera2_OLED_object_detection.ino 里"本地Edge Impulse
  推理+本地OLED显示"的闭环逻辑，改成"PC做检测+融合判断，ESP32CAM只负责
  采集画面(WiFi推给PC)和接收PC的遮挡指令(画到OLED)"这条新链路。

  这个版本不跑任何本地推理，Edge Impulse模型本次不用。

  硬件引脚复用自已验证可用的两份旧文件（261003/），没有改动、没有冲突：
    - 摄像头引脚：261003/esp32_camera2_OLED_object_detection/*.ino (AI-Thinker)
    - OLED接线：  261003/OLED_test_ESP32CAM/*.ino (SDA=13, SCL=14, I2C 0x3C)

  提供的HTTP接口（给PC侧Python脚本调用）：
    GET  /capture
      返回当前一帧JPEG图像（单张抓拍，不是MJPEG连续流）。
      PC侧用轮询的方式反复调用这个接口来做"准实时"外部场景采集，
      不是真正的视频流，这是本阶段为了先打通链路做的简化。

    GET  /mask?x=<int>&y=<int>&w=<int>&h=<int>&on=<0|1>
      在OLED(128x64)上，于(x,y)到(x+w,y+h)这个矩形区域画/清除密集文字遮挡。
      on=1 画遮挡（重复填充字符'/'模拟密集文字遮挡效果）
      on=0 清除该区域（实际做法是整屏清空重画，因为SSD1306不支持局部脏区域重绘）
      注意：这个阶段OLED屏幕本身就代表"人眼能看到的范围"（用户暂未安装透镜，
      不需要考虑光学反射），所以PC侧传来的(x,y,w,h)直接就是OLED像素坐标，
      不需要做场景摄像头→OLED的几何映射转换。等正式上透镜后，这一步要换成
      经过标定矩阵换算后的坐标，再传过来。

    GET  /status
      返回简单的JSON状态（WiFi连接情况、摄像头是否正常初始化），用于PC侧
      启动时的健康检查。

  已知缺口（如实记录，不在本次范围内）：
    - /capture是单帧轮询，不是真正的MJPEG流，帧率取决于PC侧轮询频率和
      WiFi延迟，没有做实时性优化。
    - 没有做任何鉴权，纯局域网内部测试用，不能暴露在公网。
    - /mask的on=0清除逻辑是整屏重画，如果后续要支持多个遮挡区域同时存在，
      需要在服务端维护一个"当前所有遮挡区域"的列表，而不是单区域覆盖。
    - WiFi SSID/密码是占位符，烧录前必须改成实际值。
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ============================================================
// WiFi 配置 -- 烧录前必须改成你实际要连的热点/路由器信息
// ============================================================
const char* WIFI_SSID     = "AidaGu";
const char* WIFI_PASSWORD = "yiyi060423";

// ============================================================
// OLED 配置（照搬 261003/OLED_test_ESP32CAM，已验证可用）
// ============================================================
#define OLED_SDA 13
#define OLED_SCL 14
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
bool oled_ok = false;

// ============================================================
// 摄像头引脚（照搬 261003/esp32_camera2_OLED_object_detection，AI-Thinker）
// ============================================================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5

#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

bool camera_ok = false;

WebServer server(80);

// ============================================================
// 摄像头初始化
// ============================================================
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_QVGA;   // 320x240, 带宽和延迟的折中值
  config.jpeg_quality  = 12;
  config.fb_count      = 1;
  config.fb_location   = CAMERA_FB_IN_PSRAM;
  config.grab_mode     = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return false;
  }

  sensor_t *s = esp_camera_sensor_get();
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);
    s->set_brightness(s, 1);
    s->set_saturation(s, 0);
  }

  return true;
}

// ============================================================
// OLED 初始化
// ============================================================
bool initOLED() {
  Wire.begin(OLED_SDA, OLED_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed at 0x3C");
    return false;
  }
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("261022 mask server");
  display.setCursor(0, 20);
  display.println("waiting for PC...");
  display.display();
  return true;
}

// ============================================================
// 在OLED上用密集文字("/"重复填充)渲染一个矩形遮挡区域
// 这是261010路线图里提过的"密集文字遮挡"思路的最简实现：
// 用等间距重复打印字符，制造视觉上的密度掩蔽效果。
// ============================================================
void drawTextMask(int x, int y, int w, int h) {
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  const int charStepX = 6;   // 单个字符大致宽度(像素)，用于控制密度
  const int charStepY = 8;   // 单个字符大致高度(像素)
  for (int yy = y; yy < y + h; yy += charStepY) {
    for (int xx = x; xx < x + w; xx += charStepX) {
      display.setCursor(xx, yy);
      display.print("/");
    }
  }
}

// ============================================================
// HTTP: GET /capture  -- 返回单帧JPEG
// ============================================================
void handleCapture() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    server.send(500, "text/plain", "capture failed");
    return;
  }
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

// ============================================================
// HTTP: GET /mask?x=&y=&w=&h=&on=
// ============================================================
void handleMask() {
  if (!oled_ok) {
    server.send(500, "text/plain", "oled not initialized");
    return;
  }

  int x = server.hasArg("x") ? server.arg("x").toInt() : 0;
  int y = server.hasArg("y") ? server.arg("y").toInt() : 0;
  int w = server.hasArg("w") ? server.arg("w").toInt() : 20;
  int h = server.hasArg("h") ? server.arg("h").toInt() : 20;
  int on = server.hasArg("on") ? server.arg("on").toInt() : 1;

  // 边界保护，避免越界坐标把Adafruit_GFX画崩
  if (x < 0) x = 0;
  if (y < 0) y = 0;
  if (x + w > SCREEN_WIDTH)  w = SCREEN_WIDTH - x;
  if (y + h > SCREEN_HEIGHT) h = SCREEN_HEIGHT - y;

  if (on == 1) {
    drawTextMask(x, y, w, h);
  } else {
    // SSD1306 不支持局部脏区域重绘，清除目前用整屏清空代替。
    // 已知缺口：多区域同时存在时，这会把其他区域也清掉，
    // 下一版需要维护一个服务端侧的"当前遮挡列表"。
    display.clearDisplay();
  }
  display.display();

  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", "ok");
}

// ============================================================
// HTTP: GET /status
// ============================================================
void handleStatus() {
  String json = "{";
  json += "\"wifi_connected\":" + String(WiFi.status() == WL_CONNECTED ? "true" : "false") + ",";
  json += "\"camera_ok\":" + String(camera_ok ? "true" : "false") + ",";
  json += "\"oled_ok\":" + String(oled_ok ? "true" : "false") + ",";
  json += "\"ip\":\"" + WiFi.localIP().toString() + "\"";
  json += "}";
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
}

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("==== 261022 ESP32CAM WiFi + OLED mask server ====");

  oled_ok = initOLED();
  camera_ok = initCamera();

  if (!camera_ok) {
    Serial.println("WARNING: camera init failed, /capture will not work");
  }

  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true);
  delay(500);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  int wifi_wait_count = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    wifi_wait_count++;
    if (wifi_wait_count % 20 == 0) {
      // Every ~10s, print the raw status code instead of an undifferentiated
      // wall of dots -- this tells apart "wrong password" (WL_CONNECT_FAILED=4)
      // from "SSID not found/out of range" (WL_NO_SSID_AVAIL=1) from "still
      // trying" (WL_IDLE_STATUS=0), which a plain dot cannot.
      Serial.printf(" [status=%d, %ds elapsed]", (int)WiFi.status(), wifi_wait_count / 2);
    }
  }
  Serial.println();
  Serial.print("WiFi connected, IP = ");
  Serial.println(WiFi.localIP());

  if (oled_ok) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("WiFi connected");
    display.setCursor(0, 16);
    display.println(WiFi.localIP().toString());
    display.display();
  }

  server.on("/capture", HTTP_GET, handleCapture);
  server.on("/mask", HTTP_GET, handleMask);
  server.on("/status", HTTP_GET, handleStatus);
  server.begin();
  Serial.println("HTTP server started.");
  Serial.println("Endpoints: GET /capture, GET /mask?x=&y=&w=&h=&on=, GET /status");
}

void loop() {
  server.handleClient();
}
