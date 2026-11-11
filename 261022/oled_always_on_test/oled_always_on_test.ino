/*
  OLED 常亮测试
  ============
  261022 -- 单独拆出来的小工具，跟 esp32cam_wifi_mask_server 那个联调固件
  没有关系。目的很单纯：原型阶段要看OLED在戴上透镜/遮罩后反射的光线效果，
  所以只需要屏幕整块白、一直亮着、不闪烁、不切换内容，排除掉其他逻辑的
  干扰（WiFi、摄像头、遮挡区域刷新等这次都不要）。

  接线照搬已验证可用的 261003/OLED_test_ESP32CAM：
    SDA=13, SCL=14, I2C地址 0x3C
*/

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define OLED_SDA 13
#define OLED_SCL 14
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

void setup() {
  Serial.begin(115200);
  Serial.println("\n==== OLED 常亮测试 ====");

  Wire.begin(OLED_SDA, OLED_SCL);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed at 0x3C");
    return;
  }

  // 整屏填白并点亮，之后不再调用 clearDisplay()，也不再重绘，
  // 保证屏幕从上电开始就是稳定的最大亮度，方便观察反光效果。
  display.ssd1306_command(SSD1306_DISPLAYON);
  display.fillScreen(SSD1306_WHITE);
  display.display();

  Serial.println("OLED 已整屏点亮，常驻不变。");
}

void loop() {
  // 故意留空：不重绘、不清屏、不切换，屏幕内容从 setup() 之后不再变化。
}
