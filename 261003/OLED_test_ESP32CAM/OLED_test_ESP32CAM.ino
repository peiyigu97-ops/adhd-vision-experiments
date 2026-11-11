#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define OLED_SDA 13
#define OLED_SCL 14
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

void scanI2C() {
  Serial.println("\n===== I2C SCAN =====");
  int found = 0;
  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    byte error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("Found I2C device at 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
      found++;
    }
  }
  if (found == 0) Serial.println("NO I2C DEVICE FOUND!");
  Serial.println("====================");
}

bool tryOLED(byte address) {
  Serial.print("Trying OLED address 0x");
  Serial.println(address, HEX);

  if (!display.begin(SSD1306_SWITCHCAPVCC, address)) {
    Serial.println("SSD1306 init FAILED.");
    return false;
  }

  Serial.println("SSD1306 init SUCCESS!");

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("OLED TEST");
  display.setTextSize(2);
  display.setCursor(0, 20);
  display.println("HELLO!");
  display.setTextSize(1);
  display.setCursor(0, 50);
  display.print("ADDR 0x");
  if (address < 16) display.print("0");
  display.println(address, HEX);
  display.display();
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n================================");
  Serial.println("ESP32-CAM OLED TEST");
  Serial.println("================================");

  Wire.begin(OLED_SDA, OLED_SCL);
  delay(100);

  scanI2C();

  if (tryOLED(0x3C)) {
    Serial.println("OLED DISPLAYING AT 0x3C");
    return;
  }

  if (tryOLED(0x3D)) {
    Serial.println("OLED DISPLAYING AT 0x3D");
    return;
  }

  Serial.println("\nOLED TEST FAILED.");
  Serial.println("Check VDD/GND/SDA/SCL.");
}

void loop() {
  static bool state = false;
  state = !state;

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(0, 20);
  display.println(state ? "OLED OK" : "TEST");
  display.display();

  delay(2000);
}
