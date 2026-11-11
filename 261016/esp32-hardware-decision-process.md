# ESP32 Hardware Decision Process (261016)

Records the stages and shifting conclusions in a discussion about "using an ESP32-family board as a hardware relay/capture node for the eye-tracking algorithm."

## Stage 1: ESP32-CAM as a relay node, the PC does the processing and sends back to the OLED

**User's question**: can the ESP32-CAM just act as a relay, sending incoming data to a PC for processing, then sending the result back to the ESP32-CAM for OLED display?

**Conclusion**: feasible, a common architecture — but only if the "incoming data" really does come from the camera. If the input comes from another sensor, using an ESP32-CAM would be wasteful (its only real value is that one OV2640 camera).

**Link design**:
```
[camera/sensor] → ESP32-CAM ──WiFi──> PC (processing/inference)
                      ↑                    │
                      └──── result return ───────┘
                      ↓
                   OLED (I2C)
```
Recommended as a single HTTP round trip: the ESP32 POSTs the frame/data to the PC, and the PC packs the result back into the same HTTP response — no polling needed, no need for the PC to connect back to the ESP32. Keep the return payload minimal (a few lines of text, or a 1024-byte 1-bit bitmap); a full SSD1306 refresh takes about 23ms, not a bottleneck.

**Hard hardware limits**:
- **GPIOs nearly exhausted**: on the AI-Thinker board, GPIO16 is taken by PSRAM, leaving only 12/13/14/15 freely usable (2/4 have strapping and flash-related entanglements). Recommend OLED on GPIO14=SDA, GPIO15=SCL, avoiding 12 (MTDI strapping, wrong boot-time level and it won't come up). GPIO1/3 are UART0 — if the OLED takes them, flashing becomes impossible.
- **No USB**: an FTDI serial adapter is required; flashing means pulling GPIO0 low before power-up, a poor debugging experience. The FTDI's 5V pin usually can't drive the module (camera + WiFi peak draw 180-250mA), brownout is essentially guaranteed, so an independent 5V/1A supply with a shared ground and a 470-1000µF electrolytic buffer capacitor is needed.
- **Camera and WiFi compete for PSRAM**: the JPEG frame buffer and the WiFi stack buffer both live in PSRAM, and squeeze each other at higher resolution. VGA + 10fps at about 200-500KB/s holds up; UXGA does not.
- **The real latency bottleneck is on the PC side**: LAN round-trip latency is only a few milliseconds; PC-side inference is the big cost. 100ms inference → 5-8fps round trip; if the PC runs a large model, latency reaches the second range, and the OLED display will visibly stutter.

**Alternative suggestion**:
- If the hardware hasn't been purchased yet, go straight for the **ESP32-S3-CAM** (Freenove S3 CAM, XIAO ESP32S3 Sense): native USB-C, 8MB PSRAM, on-chip AI vector instruction support, more spare GPIOs.
- For a simple detection task (e.g. face detection), the ESP32-S3 running ESP-DL/ESP-WHO on-chip inference is enough — no PC loop needed at all, an order-of-magnitude improvement in latency and stability.
- If the input isn't a camera, a plain ESP32 DevKit or ESP32-S3 dev board is more suitable — lower cost, more pins, USB debugging built in.

**Recommended first validation step**: OV2640 shoots a VGA JPEG → HTTP POST to a PC-side Flask script → PC returns one line of text → OLED displays it. Get this minimal chain working before swapping in the real PC-side processing logic.

## Stage 2: Does the plan still hold with OV9281 swapped in

**User's question**: can this kind of pure algorithmic recognition go the route of ESP32-CAM + OLED + OV9281 + power, direct-streaming to the PC for real-time display?

**Decisive factor**: the deciding variable isn't the OLED or the power supply (those two stay feasible, unchanged) — it's OV9281's specific interface form. This is the one thing that determines whether the whole plan can work at all.

**Not a bottleneck**:
- OLED display: I2C on 14/15, same pitfalls as Stage 1.
- Power supply: independent 5V supply + capacitor buffer, ESP32 can handle the current draw.
- Direct-streaming to the PC for real-time display: mature technology, the ESP32 acting as a WiFi camera server, MJPEG stream/HTTP push to the PC, OpenCV receiving the stream — this is a built-in ESP32-CAM official-example usage pattern, no new risk.

**The real bottleneck: OV9281 ≠ the OV2640 on the ESP32-CAM board**

The ESP32-CAM board was designed around the OV2640 (some versions OV3660), with a DVP-parallel + SCCB (an I2C variant) interface. OV9281 is a global-shutter sensor, commonly found in three package types, with very different feasibility:

1. **USB UVC module**: some OV9281 units are packaged as a standard USB camera, plugging straight into a computer's USB port. In this case **the ESP32-CAM relay isn't needed at all** — the architecture simplifies directly to "USB camera → computer algorithm processing," simpler and lower-latency than the original plan.
2. **MIPI CSI interface module**: common in Raspberry Pi/Jetson ecosystems. The ESP32 family has no MIPI support whatsoever — this path is a dead end.
3. **DVP parallel interface bare board**: in theory the physical interface could connect to the ESP32-CAM's camera socket, but the driver is a major hurdle — the official ESP32 `esp32-camera` driver library's supported sensor list is OV2640/OV3660/OV5640/OV7725/NT99141, and OV9281 is not on it. A global-shutter sensor's register init sequence and exposure-control logic are entirely different from a rolling-shutter sensor like the OV2640, with no existing driver to reuse — it would mean writing SCCB register configuration + DVP timing parsing from scratch, a non-trivial amount of work.

**Open items and recommendations**:
- Need to first confirm which package type the OV9281 module on hand (or to be purchased) actually is.
- If it's a USB UVC version: skip the ESP32-CAM, connect straight to the PC's USB.
- If it's a DVP bare board with no existing ESP32 driver: this piece of work would end up dominating the whole project's schedule — might as well switch back to a sensor like the OV2640/OV5640 with a mature driver, trading rolling-shutter limitations for stable delivery.
- Exception case: if the "algorithmic recognition" scenario genuinely needs global shutter to handle motion blur during fast eye saccades, that's a legitimate reason to choose OV9281 — but in that case it should go through USB UVC or MIPI (connected to a Pi-class board with MIPI support), not forced onto an ESP32-CAM.

## Open Questions

As of this record, still unconfirmed:
1. What package type the OV9281 module on hand/planned for purchase actually is — USB UVC, MIPI CSI, or a DVP bare board.
2. If it's a DVP bare board, is there an existing unofficial ESP32 driver available, or does SCCB + timing have to be written from scratch.
3. Whether the real motivation for choosing OV9281 over OV2640/OV5640 is "needing global shutter to handle saccade motion blur" — if not, we should most likely switch back to a sensor with a mature driver.

The answers to these questions will decide which of the three paths this plan ultimately takes: direct USB connection, MIPI into a Raspberry Pi, or continuing to push through an ESP32-CAM + DVP bare-board driver.
