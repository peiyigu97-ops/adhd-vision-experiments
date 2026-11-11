/* Edge Impulse Arduino examples
 * Aida-project-1
 * ESP32-CAM + OV3660 + OLED
 */

#include <Aida-project-1_inferencing.h>
#include "edge-impulse-sdk/dsp/image/image.hpp"
#include "esp_camera.h"

// ============================================================
// OLED
// ============================================================

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define OLED_SDA 13
#define OLED_SCL 14

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    &Wire,
    -1
);


// ============================================================
// 摄像头型号
// ============================================================

#define CAMERA_MODEL_AI_THINKER


#if defined(CAMERA_MODEL_AI_THINKER)

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

#else

#error "Camera model not selected"

#endif


// ============================================================
// Edge Impulse 摄像头参数
// ============================================================

#define EI_CAMERA_RAW_FRAME_BUFFER_COLS  320
#define EI_CAMERA_RAW_FRAME_BUFFER_ROWS  240
#define EI_CAMERA_FRAME_BYTE_SIZE        3


// ============================================================
// 全局变量
// ============================================================

static bool debug_nn = false;
static bool is_initialised = false;

uint8_t *snapshot_buf;


// ============================================================
// 摄像头配置
// ============================================================

static camera_config_t camera_config = {

    .pin_pwdn       = PWDN_GPIO_NUM,
    .pin_reset      = RESET_GPIO_NUM,
    .pin_xclk       = XCLK_GPIO_NUM,

    .pin_sscb_sda   = SIOD_GPIO_NUM,
    .pin_sscb_scl   = SIOC_GPIO_NUM,

    .pin_d7         = Y9_GPIO_NUM,
    .pin_d6         = Y8_GPIO_NUM,
    .pin_d5         = Y7_GPIO_NUM,
    .pin_d4         = Y6_GPIO_NUM,
    .pin_d3         = Y5_GPIO_NUM,
    .pin_d2         = Y4_GPIO_NUM,
    .pin_d1         = Y3_GPIO_NUM,
    .pin_d0         = Y2_GPIO_NUM,

    .pin_vsync      = VSYNC_GPIO_NUM,
    .pin_href       = HREF_GPIO_NUM,
    .pin_pclk       = PCLK_GPIO_NUM,

    .xclk_freq_hz   = 20000000,

    .ledc_timer     = LEDC_TIMER_0,
    .ledc_channel   = LEDC_CHANNEL_0,

    .pixel_format   = PIXFORMAT_JPEG,

    .frame_size     = FRAMESIZE_QVGA,

    .jpeg_quality   = 12,

    .fb_count       = 1,

    .fb_location    = CAMERA_FB_IN_PSRAM,

    .grab_mode      = CAMERA_GRAB_WHEN_EMPTY
};


// ============================================================
// 函数声明
// ============================================================

bool ei_camera_init(void);

void ei_camera_deinit(void);

bool ei_camera_capture(
    uint32_t img_width,
    uint32_t img_height,
    uint8_t *out_buf
);

static int ei_camera_get_data(
    size_t offset,
    size_t length,
    float *out_ptr
);


// ============================================================
// Arduino setup
// ============================================================

void setup()
{
    Serial.begin(115200);

    Serial.println();
    Serial.println("================================");
    Serial.println("Edge Impulse ESP32-CAM");
    Serial.println("Aida-project-1 + OLED");
    Serial.println("================================");


    // ========================================================
    // 初始化 OLED
    // ========================================================

    Wire.begin(OLED_SDA, OLED_SCL);

    if (!display.begin(
            SSD1306_SWITCHCAPVCC,
            0x3C
        ))
    {
        Serial.println("OLED initialization failed!");

        while (1)
        {
            delay(1000);
        }
    }


    // OLED 开机画面

    display.clearDisplay();

    display.setTextColor(SSD1306_WHITE);

    display.setTextSize(1);

    display.setCursor(0, 0);
    display.println("Aida-project-1");

    display.setCursor(0, 18);
    display.println("Edge Impulse");

    display.setCursor(0, 36);
    display.println("Initializing...");

    display.display();


    // ========================================================
    // 初始化摄像头
    // ========================================================

    if (ei_camera_init() == false)
    {
        ei_printf("Failed to initialize Camera!\r\n");

        display.clearDisplay();

        display.setTextSize(1);
        display.setCursor(0, 0);

        display.println("Camera ERROR");

        display.display();
    }
    else
    {
        ei_printf("Camera initialized\r\n");
    }


    // OLED 显示准备开始

    display.clearDisplay();

    display.setTextColor(SSD1306_WHITE);

    display.setTextSize(1);

    display.setCursor(0, 0);
    display.println("Camera OK");

    display.setCursor(0, 18);
    display.println("Starting");

    display.setCursor(0, 32);
    display.println("inference...");

    display.display();


    ei_printf("\nStarting continuous inference in 2 seconds...\n");

    ei_sleep(2000);
}


// ============================================================
// Arduino loop
// ============================================================

void loop()
{
    if (ei_sleep(5) != EI_IMPULSE_OK)
    {
        return;
    }


    // --------------------------------------------------------
    // 分配图像缓冲区
    // --------------------------------------------------------

    snapshot_buf = (uint8_t*)malloc(
        EI_CAMERA_RAW_FRAME_BUFFER_COLS *
        EI_CAMERA_RAW_FRAME_BUFFER_ROWS *
        EI_CAMERA_FRAME_BYTE_SIZE
    );


    if (snapshot_buf == nullptr)
    {
        ei_printf("ERR: Failed to allocate snapshot buffer!\n");
        return;
    }


    // --------------------------------------------------------
    // 创建 Edge Impulse signal
    // --------------------------------------------------------

    ei::signal_t signal;

    signal.total_length =
        EI_CLASSIFIER_INPUT_WIDTH *
        EI_CLASSIFIER_INPUT_HEIGHT;

    signal.get_data = &ei_camera_get_data;


    // --------------------------------------------------------
    // 拍摄照片
    // --------------------------------------------------------

    if (
        ei_camera_capture(
            (size_t)EI_CLASSIFIER_INPUT_WIDTH,
            (size_t)EI_CLASSIFIER_INPUT_HEIGHT,
            snapshot_buf
        ) == false
    )
    {
        ei_printf("Failed to capture image\r\n");

        free(snapshot_buf);

        return;
    }


    // --------------------------------------------------------
    // 运行 Edge Impulse 模型
    // --------------------------------------------------------

    ei_impulse_result_t result = { 0 };


    EI_IMPULSE_ERROR err =
        run_classifier(
            &signal,
            &result,
            debug_nn
        );


    if (err != EI_IMPULSE_OK)
    {
        ei_printf(
            "ERR: Failed to run classifier (%d)\n",
            err
        );

        free(snapshot_buf);

        return;
    }


    // --------------------------------------------------------
    // 输出推理时间
    // --------------------------------------------------------

    ei_printf(
        "\nPredictions "
        "(DSP: %d ms., Classification: %d ms., Anomaly: %d ms.):\n",
        result.timing.dsp,
        result.timing.classification,
        result.timing.anomaly
    );


    // ========================================================
    // Object Detection
    // ========================================================

#if EI_CLASSIFIER_OBJECT_DETECTION == 1

    ei_printf("Object detection bounding boxes:\r\n");

    // --------------------------------------------------------
    // 找到置信度最高的目标
    // --------------------------------------------------------

    int best_box = -1;
    float best_value = 0.0f;

    for (
        uint32_t i = 0;
        i < result.bounding_boxes_count;
        i++
    )
    {
        ei_impulse_result_bounding_box_t bb =
            result.bounding_boxes[i];

        if (bb.value == 0)
        {
            continue;
        }

        // Serial Monitor 输出每个检测框
        ei_printf(
            "  %s (%f) "
            "[ x: %u, y: %u, width: %u, height: %u ]\r\n",

            bb.label,
            bb.value,
            bb.x,
            bb.y,
            bb.width,
            bb.height
        );

        // 记录置信度最高的目标
        if (bb.value > best_value)
        {
            best_value = bb.value;
            best_box = i;
        }
    }

    // --------------------------------------------------------
    // OLED 显示置信度最高的目标
    // --------------------------------------------------------

    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);

    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("DETECTED");

    if (best_box >= 0)
    {
        const char *best_label =
            result.bounding_boxes[best_box].label;

        float best_percent =
            best_value * 100.0f;

        // 标签短时使用大字体
        if (strlen(best_label) <= 8)
        {
            display.setTextSize(2);
            display.setCursor(0, 17);
            display.println(best_label);
        }
        else
        {
            display.setTextSize(1);
            display.setCursor(0, 20);
            display.println(best_label);
        }

        display.setTextSize(1);
        display.setCursor(0, 48);
        display.print("Confidence: ");
        display.print(best_percent, 1);
        display.println("%");
    }
    else
    {
        display.setTextSize(2);
        display.setCursor(0, 20);
        display.println("NONE");

        display.setTextSize(1);
        display.setCursor(0, 48);
        display.println("No object");
    }

    display.display();


// ========================================================
// Classification
// ========================================================

#else

    ei_printf("Predictions:\r\n");


    // --------------------------------------------------------
    // 找到概率最高的分类
    // --------------------------------------------------------

    uint16_t best_ix = 0;

    float best_value =
        result.classification[0].value;


    for (
        uint16_t i = 1;
        i < EI_CLASSIFIER_LABEL_COUNT;
        i++
    )
    {
        if (
            result.classification[i].value >
            best_value
        )
        {
            best_value =
                result.classification[i].value;

            best_ix = i;
        }
    }


    // --------------------------------------------------------
    // Serial 输出全部分类结果
    // --------------------------------------------------------

    for (
        uint16_t i = 0;
        i < EI_CLASSIFIER_LABEL_COUNT;
        i++
    )
    {
        ei_printf(
            "  %s: ",
            ei_classifier_inferencing_categories[i]
        );


        ei_printf(
            "%.5f\r\n",
            result.classification[i].value
        );
    }


    // ========================================================
    // OLED 显示最高概率结果
    // ========================================================

    const char *best_label =
        ei_classifier_inferencing_categories[best_ix];


    float best_percent =
        best_value * 100.0f;


    display.clearDisplay();

    display.setTextColor(SSD1306_WHITE);


    // --------------------------------------------------------
    // 第一行：Result
    // --------------------------------------------------------

    display.setTextSize(1);

    display.setCursor(0, 0);

    display.println("RESULT");


    // --------------------------------------------------------
    // 第二部分：识别结果
    // --------------------------------------------------------

    // 如果标签比较短，用大字体

    if (strlen(best_label) <= 8)
    {
        display.setTextSize(2);

        display.setCursor(0, 17);

        display.println(best_label);
    }
    else
    {
        display.setTextSize(1);

        display.setCursor(0, 18);

        display.println(best_label);
    }


    // --------------------------------------------------------
    // 概率
    // --------------------------------------------------------

    display.setTextSize(1);

    display.setCursor(0, 48);

    display.print("Confidence: ");

    display.print(best_percent, 1);

    display.println("%");


    display.display();

#endif


    // ========================================================
    // Anomaly Detection
    // ========================================================

#if EI_CLASSIFIER_HAS_ANOMALY

    ei_printf(
        "Anomaly prediction: %.3f\r\n",
        result.anomaly
    );

#endif


    // ========================================================
    // Visual Anomaly
    // ========================================================

#if EI_CLASSIFIER_HAS_VISUAL_ANOMALY

    ei_printf("Visual anomalies:\r\n");


    for (
        uint32_t i = 0;
        i < result.visual_ad_count;
        i++
    )
    {
        ei_impulse_result_bounding_box_t bb =
            result.visual_ad_grid_cells[i];


        if (bb.value == 0)
        {
            continue;
        }


        ei_printf(
            "  %s (%f) "
            "[ x: %u, y: %u, width: %u, height: %u ]\r\n",

            bb.label,

            bb.value,

            bb.x,

            bb.y,

            bb.width,

            bb.height
        );
    }

#endif


    // --------------------------------------------------------
    // 释放图像缓冲区
    // --------------------------------------------------------

    free(snapshot_buf);
}


// ============================================================
// 初始化摄像头
// ============================================================

bool ei_camera_init(void)
{
    if (is_initialised)
    {
        return true;
    }


    esp_err_t err =
        esp_camera_init(&camera_config);


    if (err != ESP_OK)
    {
        Serial.printf(
            "Camera init failed with error 0x%x\n",
            err
        );

        return false;
    }


    sensor_t *s =
        esp_camera_sensor_get();


    // --------------------------------------------------------
    // OV3660 摄像头设置
    // --------------------------------------------------------

    if (s->id.PID == OV3660_PID)
    {
        s->set_vflip(s, 1);

        s->set_brightness(s, 1);

        s->set_saturation(s, 0);
    }


    is_initialised = true;

    return true;
}


// ============================================================
// 关闭摄像头
// ============================================================

void ei_camera_deinit(void)
{
    esp_err_t err =
        esp_camera_deinit();


    if (err != ESP_OK)
    {
        ei_printf(
            "Camera deinit failed\n"
        );

        return;
    }


    is_initialised = false;
}


// ============================================================
// 拍照、转换、缩放
// ============================================================

bool ei_camera_capture(
    uint32_t img_width,
    uint32_t img_height,
    uint8_t *out_buf
)
{
    bool do_resize = false;


    if (!is_initialised)
    {
        ei_printf(
            "ERR: Camera is not initialized\r\n"
        );

        return false;
    }


    // --------------------------------------------------------
    // 从摄像头获取 JPEG
    // --------------------------------------------------------

    camera_fb_t *fb =
        esp_camera_fb_get();


    if (!fb)
    {
        ei_printf(
            "Camera capture failed\n"
        );

        return false;
    }


    // --------------------------------------------------------
    // JPEG → RGB888
    // --------------------------------------------------------

    bool converted =
        fmt2rgb888(
            fb->buf,
            fb->len,
            PIXFORMAT_JPEG,
            snapshot_buf
        );


    esp_camera_fb_return(fb);


    if (!converted)
    {
        ei_printf(
            "Conversion failed\n"
        );

        return false;
    }


    // --------------------------------------------------------
    // 判断是否需要缩放
    // --------------------------------------------------------

    if (
        (img_width != EI_CAMERA_RAW_FRAME_BUFFER_COLS) ||
        (img_height != EI_CAMERA_RAW_FRAME_BUFFER_ROWS)
    )
    {
        do_resize = true;
    }


    // --------------------------------------------------------
    // 缩放到 Edge Impulse 模型需要的尺寸
    // --------------------------------------------------------

    if (do_resize)
    {
        ei::image::processing::crop_and_interpolate_rgb888(

            snapshot_buf,

            EI_CAMERA_RAW_FRAME_BUFFER_COLS,

            EI_CAMERA_RAW_FRAME_BUFFER_ROWS,

            out_buf,

            img_width,

            img_height
        );
    }


    return true;
}


// ============================================================
// 给 Edge Impulse 提供图像数据
// ============================================================

static int ei_camera_get_data(
    size_t offset,
    size_t length,
    float *out_ptr
)
{
    size_t pixel_ix =
        offset * 3;


    size_t pixels_left =
        length;


    size_t out_ptr_ix = 0;


    while (pixels_left != 0)
    {
        // BGR → RGB

        out_ptr[out_ptr_ix] =
            (snapshot_buf[pixel_ix + 2] << 16) +
            (snapshot_buf[pixel_ix + 1] << 8) +
            snapshot_buf[pixel_ix];


        out_ptr_ix++;

        pixel_ix += 3;

        pixels_left--;
    }


    return 0;
}


// ============================================================
// 确认模型是 Camera 模型
// ============================================================

#if !defined(EI_CLASSIFIER_SENSOR) || \
    EI_CLASSIFIER_SENSOR != EI_CLASSIFIER_SENSOR_CAMERA

#error "Invalid model for current sensor"

#endif
