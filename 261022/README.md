# 261022 — ESP32CAM WiFi Streaming + OLED Occlusion Display Integration

Independent of `261003/`, `260919/`, `260918/` and other earlier folders, this is the firmware and test scripts for the new "PC does the fusion, ESP32CAM only captures and displays" architecture.

## Background

The earlier `261003/esp32_camera2_OLED_object_detection/*.ino` ran local Edge Impulse object detection and displayed the result directly on the OLED — a fully closed loop, no WiFi/PC communication. This firmware revision flips the architecture: the ESP32CAM is only responsible for **capturing frames** and **receiving PC commands to draw on the OLED**; detection/fusion judgment is moved entirely to the PC side. Reason: see the conversation log — the Edge Impulse model is shelved for now, pending the OV9281-side eye-detection algorithm being settled before deciding whether to move object detection back on-device too.

> Update (2026-10-23): the eye-detection algorithm is no longer "DeepVOG, under test" — DeepVOG itself was excluded because its `tensorflow-gpu` dependency has been pulled from PyPI; the approach that actually passed validation is EllSeg (no IR, close-up eye crop, 86.7% accuracy on fair frames after manual review) — see `261004/experiment_report.md` section 7f. This ESP32CAM line is unrelated to that conclusion and proceeds independently.

## Files

- `esp32cam_wifi_mask_server/esp32cam_wifi_mask_server.ino` — firmware to flash onto the ESP32CAM
- `test_esp32cam_link.py` — PC-side test script verifying the three HTTP endpoints work
- `test_mask_manual.py` — a step-by-step manual test for the `/mask` endpoint: draws once, waits for you to confirm you saw it, then clears it (better suited for manual visual verification than `test_esp32cam_link.py`'s version, which auto-clears after 2 seconds; supports a custom region via `--x/--y/--w/--h`)
- `fusion_poc.py` — a PoC of the PC-side "decide whether to occlude → send command" fusion logic; the eye-tracking and object-detection parts are simulated with keyboard input / a hardcoded rectangle — see the in-file docstring for the exact scope boundary, do not mistake this for the final fusion logic

## Hardware Wiring (reused from an already-validated config, unchanged)

- Camera: standard AI-Thinker ESP32-CAM pinout (copied from `261003/esp32_camera2_OLED_object_detection`)
- OLED (SSD1306 128x64): SDA=GPIO13, SCL=GPIO14, I2C address 0x3C (copied from `261003/OLED_test_ESP32CAM`)

## Required Edits Before Flashing

Open `esp32cam_wifi_mask_server.ino` and change these two lines to the actual WiFi credentials:

```cpp
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
```

## Flashing Environment Requirements (arduino-cli is not installed on this machine; the following is inferred from the code's dependencies, not actually compile-verified — please double-check before flashing)

- **Board**: select "AI Thinker ESP32-CAM" in the Arduino IDE (matches the board already validated in 261003)
- **Partition Scheme**: needs "Huge APP" or a similarly large partition scheme (camera + WiFi + OLED together may not fit in the standard partition)
- **PSRAM**: must be enabled in the board settings (the code's `fb_location = CAMERA_FB_IN_PSRAM` directly depends on this — without PSRAM enabled, `esp_camera_init` fails immediately)
- **Extra libraries needed** (install via the Arduino IDE Library Manager, not bundled with the ESP32 core):
  - `Adafruit GFX Library`
  - `Adafruit SSD1306`
  - (`esp_camera.h`, `WiFi.h`, `WebServer.h`, `Wire.h` come bundled with the ESP32 board package, no separate install needed)
- **Upload method**: the ESP32-CAM has no direct USB connection, a USB-to-TTL adapter is needed; entering download mode, as usual, requires grounding GPIO0 before flashing, then disconnecting and resetting after flashing completes — if you already have a working wiring/process from flashing 261003 previously, just reuse it; this is only a reminder, not a new requirement

## HTTP Endpoints

| Endpoint | Method | Params | Description |
|---|---|---|---|
| `/capture` | GET | none | returns a single JPEG frame (QVGA 320x240), poll-based snapshot, not a continuous video stream |
| `/mask` | GET | `x,y,w,h,on` | draws/clears a dense-text occlusion rectangle on the OLED (128x64). `on=1` draws, `on=0` clears (full-screen redraw) |
| `/status` | GET | none | returns JSON: WiFi connection status, whether the camera/OLED initialized successfully, local IP |

## Verification Steps

1. Flash the firmware, open the serial monitor to see the printed IP address
2. `python test_esp32cam_link.py --ip <that IP>`
3. The script tests in order: `/status` → `/capture` (saves an image to `test_captures/` to check the frame looks right) → `/mask` (a small "/" dense-fill block should appear in the OLED's top-left corner, clearing after 2 seconds)

## Known Simplifications/Gaps at This Stage (recorded honestly)

- **The OLED directly represents "what the eye sees"**: the user has not yet installed the optical lens, so the `(x,y,w,h)` parameters are just the OLED's own pixel coordinates, with no geometric-mapping conversion applied. Once the lens is installed and the scene-camera↔OLED calibration is done, these will need to switch to coordinates converted through the calibration matrix.
- **`/capture` is poll-based snapshotting, not an MJPEG stream**: the PC side needs to repeatedly call this endpoint to stitch together a "quasi-real-time" effect; the actual frame rate depends on PC polling frequency and WiFi latency, no streaming optimization has been done.
- **`/mask` clearing is a full-screen redraw**: if multiple occlusion regions ever need to be shown at once, the current implementation will clear all other regions along with it — the server would need to maintain a list of occlusion regions to support multi-region display.
- **No authentication**: for local-LAN internal testing only, must not be exposed to the public internet.
- **Local Edge Impulse inference is not currently used**: ~~the model is still there, this firmware revision just doesn't call it~~ **2026-11-04 correction: this phrasing could easily be misread as "the model is a ready-to-use FOMO model, just plug it back in" — after actually inspecting the model, that's not the case, see the "2026-11-04 correction" section at the end of this file** — object detection is done on the PC side this time (or, for now, with a fixed manual rectangle simulating a "distractor" to validate the chain).

## Relationship to the OV9281/Eye-Detection Line

This firmware only handles the external scene camera (the ESP32CAM's OV2640/OV3660), it has nothing to do with OV9281 eye detection. The current primary approach for the eye-detection algorithm is EllSeg (no IR, close-up eye crop, 86.7% accuracy on fair frames after manual review) — see `261004/experiment_report.md` section 7f.

The fusion logic (the PC side judging whether the pupil's gaze point falls inside a box detected by the ESP32CAM, and deciding whether to send a `/mask` command) hasn't been written yet this round — that's the next step.

## Integration Log (2026-10-25)

First flash + integration test of a new board, all three endpoints passed (including manual visual confirmation on the OLED, not just checking the program's return values). Real problems uncovered during the process, recorded honestly:

1. **`camera_config_t` field-name spelling**: the code originally used `pin_sccb_sda`/`pin_sccb_scl`, inconsistent with the version already validated working in 261003 (`pin_sscb_sda`/`pin_sscb_scl`) — the `esp32-camera` library has renamed this field between versions, and the two spellings aren't necessarily both compatible. Changed to match the old spelling used in 261003.
2. **WiFi SSID with special characters prevented connection**: the hotspot name originally used was `Aida's iPhone`, containing a curly apostrophe, and the board kept reporting `status=1` (`WL_NO_SSID_AVAIL`, unable to even scan and find this SSID) — suspected this special character got mangled somewhere along the chain of "phone display → manually transcribed by a person → typed into the code → compiled." Switching to a pure-ASCII hotspot name connected immediately, confirming the hypothesis. **Lesson: whenever a WiFi SSID contains any non-ASCII character, switch to plain English/digits first before troubleshooting — don't go guessing around at the encoding layer.**
3. **iPhone personal hotspot defaults to WPA3+5GHz, not guaranteed compatible with classic ESP32**: neither of these is explicitly supported by this particular ESP32 board (the AI-Thinker one, not an S3/C3) — had the user turn on "Maximum Compatibility" in the hotspot settings ahead of time, forcing it back to WPA2+2.4GHz, to avoid this potential risk (didn't get a chance to verify "would it really fail to connect without Maximum Compatibility," since it was switched off proactively before the SSID character issue was confirmed — the two variables weren't isolated separately).
4. **A "looks like nothing happened" pitfall with `/mask` testing**: the first test region (x=0,y=0,w=40,h=20) overlapped with the "WiFi connected" + IP-address text already shown on boot, so the drawn "/" characters overlaid on existing text and were hard to notice — momentarily mistaken for `/mask` not working. Switched to testing on a blank area in the lower half of the screen and confirmed it was working normally. **Going forward, if occlusion effects are to be overlaid in the OLED's top-left corner, the boot-time info text residue needs to be cleared or avoided first.**
5. Added `WiFi.mode(WIFI_STA)` plus clearing old state before connecting to the WiFi-connection logic, and when stuck, printed the raw `WiFi.status()` status code every 10 seconds (rather than a row of indistinguishable dots), making it easier to pinpoint the exact failure cause next time a connection fails (SSID not found / wrong password / other).

**Verification conclusion**: `/status`, `/capture` (saved image confirmed as a real frame), `/mask` (manually confirmed the occlusion pattern appeared and cleared on the OLED) all three passed. The ESP32CAM link itself is usable; next step is writing the PC-side fusion judgment logic (eye-detection result → scene-camera frame → deciding when to send a `/mask` command).

## Fusion Logic PoC (`fusion_poc.py`)

Added after the link was validated. **This is not the final fusion logic, it's a PoC validating that this "judge-trigger-execute" state machine and HTTP timing have no inherent problem** — for a direct reason: there is currently neither a trustworthy eye-tracking→OLED coordinate mapping (the calibration data recorded in `261004` section 7c.3 is not trustworthy), nor a real object-detection model wired in (object detection is deliberately shelved for now, see "Known Simplifications" above).

The script uses WASD keys to simulate the gaze point moving within the OLED coordinate system (128x64), and a hardcoded rectangle to simulate a distractor's position — both explicitly labeled in the code comments and in on-screen text at runtime (an orange box labeled "FAKE OBJECT," a green/red dot labeled "SIMULATED GAZE"), so they won't be confused with real detection results. The real parts are: polling the ESP32CAM's actual `/capture` for a scene-frame reference display, actually calling the `/mask` endpoint to control the real OLED, and the "only send a request when state changes (not every frame)" debounce logic.

Usage:
```bash
python fusion_poc.py --ip <ESP32CAM's IP>
```
Click the "OLED-space" preview window to get keyboard focus, use WASD to move the simulated gaze point in and out of the orange box, and observe whether the real OLED correctly draws/clears the occlusion; press q to quit (automatically clears the OLED, no stuck frame left behind).

**To turn this PoC into the real fusion logic, three things are needed:**
1. Finish a trustworthy pupil-coordinate → OLED-coordinate calibration in 261004 (i.e. formally re-run Stages 9 and 10)
2. Select and integrate a real object-detection model for the scene camera, mapping the detection-box coordinates into the OLED coordinate system
3. Replace `fusion_poc.py`'s `get_simulated_gaze()` keyboard-reading logic and the hardcoded `FAKE_OBJECT_RECT` with the real outputs from the two items above — the core state-machine/debounce/HTTP-trigger logic doesn't need to change

**Verification result (2026-10-25)**: manually confirmed working — the moment the simulated gaze point (WASD-controlled) entered the hardcoded "fake distractor" rectangle, the real OLED screen really did draw the occlusion pattern; once it moved out of the rectangle, the real OLED really did clear it. The "judge jump → trigger HTTP → real device responds" link itself is fully verified; the remaining work is replacing simulated data with real data per the three items above, not in the engineering mechanism of this link itself.

## Later Update (2026-10-30)

Item 1 from the "to turn this PoC into real fusion logic" list above (real pupil-coordinate → OLED-coordinate calibration) has since been completed, see the `261030/` folder:
- The eye-tracking camera has switched from OV9281 to GC0308 (reason in `261004/experiment_report.md` section 7i)
- `261030/calibration_gc0308_oled.py`: calibrates "GC0308 pupil coordinates → OLED (128x64) coordinates" directly, no intermediate conversion needed anymore
- `261030/phase1_fusion.py`: the real-data version of `fusion_poc.py`, with the gaze point switched to real GC0308+EllSeg data; the core debounce state machine logic is reused as-is, unchanged

Item 2 (real object detection/FOMO) is still not wired in — `261030/phase1_fusion.py`'s distractor rectangle is still a hardcoded placeholder — this is explicitly out of scope for Phase 1 (`261014` section 8), not an oversight.

## 2026-11-04 Correction: What We Previously Called "the model is still there" Is Not FOMO, It's a Practice Classifier

While discussing Phase 2 (pushing object detection down onto the ESP32-CAM locally), we actually inspected the Edge Impulse model that `261003/esp32_camera2_OLED_object_detection.ino` depends on (`260919/ei-aida-project-1-arduino-1.0.7-impulse-#1.zip`, project name "Aida-project-1"), and found it doesn't match the assumption implicit in the earlier phrasing "the model is still there, bring it back when the time is right":

- Checking `model_metadata.h`: `EI_CLASSIFIER_OBJECT_DETECTION = 0`, `results_type = EI_CLASSIFIER_TYPE_CLASSIFICATION` — **this is a whole-image classifier, not a FOMO object-detection model** — it does not output an object's position/bounding box within the frame, it only judges "which single class this whole image belongs to"
- The 10 classes in `model_variables.h`: `"Aida", "bottle", "computer", "digital mouse", "earpods", "ipad", "pen", "phone", "ringo", "unknown"` — clearly a "common desktop items recognition" practice-project training set, not specifically collected and labeled for distractors like "phone screen," "television," "billboard"
- Cross-referencing the FOMO-training steps `260809/ADHD PlanA 技术方案整理.md` (not included in this repository) itself laid out (① define distractor categories ② collect ~200 target images ③ label and train with FOMO), "Aida-project-1" was most likely just a practice project used at the time to first get the Edge Impulse workflow running end to end — real FOMO training targeting distractors was never actually done

**Conclusion**: Phase 2 is not "plug the existing model back into the firmware" — a simple software wiring job — it's a from-scratch training pipeline: first define distractor categories, collect/label images, train with FOMO (not a classifier) from scratch, export a new library to replace `Aida-project-1_inferencing.h`. This is new work, not a shelved half-finished piece that can just be picked back up and used.
