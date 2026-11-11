# Dual-Camera Glasses Eye Tracker v2: Pi Zero 2 W All-in-One Design + Dense-Text Occlusion

> **Update 2026-10-30 (camera selection change, see `261004/experiment_report.md` section 7i)**: this document was written on 2026-10-10, when the pupil camera plan was OV9281 + external 850nm IR fill light. In subsequent real-world testing, the OV9281 module turned out to be too bulky to mount directly at the front of the frame as originally planned, and the prism-reflection alternative was confirmed infeasible (section 7i.1). We switched to the GC0308 module (a close-range eye-tracking design, physically smaller and easier to mount), paired with the EllSeg deep-learning detector (no active IR fill needed) — static-image re-test accuracy 86.9%, and after rigid mounting, continuous-video fair-frame accuracy 100% (sections 7i.6/7i.10). **This path has been fully validated — GC0308 replaces OV9281 as the final pupil-camera choice.** This update synchronizes the sections below touching camera selection, IR fill, and detection-algorithm dependencies; the rest of the content (scene camera, PCB layout, dense-text occlusion scheme) is unaffected and kept as-is. **One newly added, still-unverified risk — see the annotation in Section 3, 3.2: EllSeg is a deep-learning model, and even on a PC it only runs at about 6–8 FPS; the Pi Zero 2 W's compute is far weaker than a PC, so whether this number is even usable is unknown and needs to be scheduled and verified separately — it cannot be assumed to carry over directly.** On the physical side: the ESP32-CAM, OLED, and GC0308 have all been mounted onto the frame per the section-261016 fixturing plan (confirmed by the user on 2026-10-30); the next step is weigh-and-wear testing (see `261004/experiment_report.md` section 7i.11). Section 1 of this document (hardware list) covering the frame body / power supply has not yet been updated accordingly — pending the weigh-in results before deciding whether the balance plan needs adjusting.

## Context

The v1 plan (ESP32CAM doing scene recognition) had a fundamental compute shortfall: the ESP32CAM is a single/dual-core MCU-class chip, unable to run even a lightweight object-detection model, and its UART image transfer bandwidth ceiling is extremely low (only 1–3 FPS snapshots, not continuous processing). After the user flagged this, we re-discussed and confirmed:

1. **On-body compute unit**: Raspberry Pi Zero 2 W (quad-core Cortex-A53), capable of running full Linux + native OpenCV, directly reusing the already-validated `pupil_detector.py` (Haar cascade + Otsu threshold + contour detection) algorithm logic without switching development frameworks. We checked the Luckfox Pico Max (RV1106, with a 1 TOPS NPU) as a comparison: its own official forum explicitly states its native OpenCV experience is poor and not recommended for object-detection services, requiring the proprietary RKNN/MPI framework — not suitable at this stage, so it was ruled out. **(Update 2026-10-30: the pupil-detection algorithm later switched from `pupil_detector.py` to `pupil_detector_ellseg.py` — see the risk annotation in sections 3.1/3.2 below; the original text is kept only to record the reasoning at the time, it does not mean this algorithm choice still holds today.)**
2. **Front-facing scene camera**: dropped the ESP32CAM plan, switched to using the Pi Zero 2 W's own CSI camera interface to directly connect a scene camera module. This fundamentally eliminates the UART bandwidth bottleneck (the image goes straight into the Pi for processing, with no serial transfer needed), rather than just shifting the bottleneck elsewhere. The ESP32CAM + existing OLED combination is scrapped/shelved.
3. **Display approach**: periscope-style reflection (OLED reflects through the temple's light path onto the lens). The physical limitation was explained to the user beforehand: the OLED is additive light — it cannot do true "occlusion/replacement"-style blurring, only "visual masking": overlaying a dense bright-text pattern at the distractor's location, exploiting retinal summation plus the fact that sufficiently high pattern density makes background detail hard to discern, to achieve an approximate occlusion effect. This limitation was explained to and accepted by the user: the effect weakens as ambient light drops (largely ineffective in strong outdoor light), it is non-deterministic pixel-level processing, and object edges may show through.
4. **Physical integration**: the Pi Zero 2 W body and the CSI scene camera are both mounted on the frame body itself (rather than as a separate unit at the waist), with only a single power line running out to a battery pack at the waist/clothing. This avoids the signal-attenuation/poor-contact risk of a CSI flex cable running from the temple all the way to the waist (a flex cable longer than 15–20 cm becomes unreliable) — this is the key reason this design beats a "compute box worn separately at the waist" approach.
5. **Distractor judgment**: start with a closed, predefined set of categories (e.g. "phone screen," "television," "billboard," etc.), implemented with lightweight classical vision features or a small quantized classifier, rather than open-set general detection (insufficient compute, and not needed at the MVP stage anyway).

This plan delivers a directly executable hardware selection list, PCB module layout plan, and firmware/algorithm code division of labor.

---

## System Architecture Overview

```
┌─────────────── Glasses body (frame integration zone) ───────────────┐
│                                                        │
│  [Scene CSI camera] ──CSI cable──┐                    │
│                            ▼                          │
│  [GC0308] ──USB──→ [Pi Zero 2 W]                       │
│   (inside the frame, facing inward at the pupil, no IR fill needed) │
│                            ├──I2C──→ [SSD1306 OLED]    │
│                            │          │                │
│                            │     (inside temple, reflective light path) │
│                            │          ▼                │
│                            │     [periscope reflection zone on lens] │
│                            │          │                │
│                            └──────────┴───→ wearer's eye │
│                                                        │
└────────────────────┬───────────────────────────────────┘
                      │ single power line (micro-USB or JST)
                      ▼
            [waist/clothing battery pack: 1× 18650 + boost/protection board]
```

Both cameras, the OLED, and the Pi body are all integrated on the frame; only the power line runs from the frame to the on-body battery pack — no data signal is transmitted over it.

---

## 1. Hardware Selection List

| Module | Specific model/spec | Estimated price (¥) | Key selection rationale |
|---|---|---|---|
| Main compute board | Raspberry Pi Zero 2 W | ~85 | Quad-core A53, can run native OpenCV, already-validated algorithm reusable directly |
| Scene camera | Pi official Camera Module 3 (wide-angle) or compatible OV5647 module | ~35-150 | Needs the adapter cable below |
| CSI adapter cable | Pi Zero dedicated 22pin→15pin adapter FPC cable, **15 cm or shorter** | ~15 | The Pi Zero uses a 22-pin/0.5mm-pitch mini connector, incompatible with the standard 15-pin camera cable — an adapter is mandatory; routing distance on the frame is short, so pick the shortest usable length to preserve signal integrity |
| Pupil camera | ~~reuse the existing OV9281 USB UVC module (already validated at 117 FPS @ 720p)~~ **changed to GC0308 (close-range eye-tracking module, already validated)** | already owned | 2026-10-30 update: the OV9281 module turned out too bulky to mount directly at the front of the frame, and the prism-reflection alternative was also infeasible (see `261004/experiment_report.md` section 7i.1). Switched to GC0308 — physically smaller and easier to mount, paired with the EllSeg detector: 86.9% static-image accuracy, 100% continuous-video fair-frame accuracy after fixed mounting (sections 7i.6/7i.10), on par with the OV9281+EllSeg baseline |
| IR fill light | ~~850nm ring LED to be re-purchased~~ **possibly no longer needed, to be confirmed** | TBD | This procurement item was for `pupil_detector.py` (Otsu threshold method) — that algorithm has a true success rate of 0% without IR, and absolutely needs IR fill to open up the contrast. Pupil detection has now switched to the EllSeg deep-learning model, repeatedly validated in sections 7i/7f/7g to achieve usable accuracy without any active IR fill, under ambient light alone — the premise for this procurement need may no longer hold. But this is "probably not needed" rather than "confirmed not needed" — note that GC0308's built-in IR (section 7b.1) is hardware the module itself carries, a separate matter from the external 850nm ring LED discussed here; do not conflate the two. Do not simply cross this line off the list until it's confirmed the EllSeg path depends on no IR whatsoever |
| Projection OLED | reuse existing SSD1306 0.96" or smaller (128x32 fits better into the temple) | already owned/~5 | Used for MVP validation of the light-path feasibility, not chasing high brightness |
| Periscope reflective element | small half-transparent/half-reflective coated lens, or a simple 45° small mirror + polarizer | ~20-50 | Search Taobao for "HUD beam-splitter lens," or salvage from a used AR glasses/HUD teardown |
| Power | 1× 18650 lithium battery + TP4056 charge-protection board + 5V boost module | ~25 | Pi Zero 2 W measured power draw is about 200-400mA @ 5V; an 18650 (2000-3000mAh) can support several hours |
| Power line | thin-gauge silicone wire, micro-USB plug or soldered directly to the Pi's 5V/GND test points | ~10 | Soldering directly to the test points is more compact than using the micro-USB port, but a micro-USB port is more newcomer-friendly to start with |
| Frame body | used flat-lens frame (temple interior needs a cavity or room to be routed/slotted) | ~20-40 | Prefer a frame with thicker temples and a plastic material (easier to drill and route wires through) |

**Total estimated cost: about ¥300-400** (excluding the IR LED, excluding PCB fabrication)

---

## 2. PCB Module Layout Plan

### 2.1 Design principles
- The first PCB revision **only serves as an interconnect carrier board** (it does not integrate the Pi itself — the Pi Zero 2 W board is screwed or stuck with double-sided tape onto the inside of the frame, not disassembled)
- Carrier board's role: consolidate the IR LED driver circuit, OLED power/signal adapter, and USB/CSI cable routing anchor points onto one small board, reducing loose scattered wiring
- Size constraint: temple interior width is typically 1.5-2 cm, keep carrier board width **under 15mm**, length can run as a long strip along the temple direction (40-60mm)

### 2.2 Carrier board module list (from the front of the temple to the back)

```
Front of temple (near the frame)                      Back of temple (near the ear)
┌──────────┬──────────────┬─────────────┬──────────────┐
│ IR LED   │ OLED interface│ USB/CSI     │ Power input   │
│ driver   │ zone (I2C 4pin)│ anchor zone │ (JST 2pin)   │
│ module   │              │             │              │
│ [current-limit resistor]│ [4pin header]│ [USB-A socket │ [JST connector] │
│ [IR LED  │ (to OLED module)│ or direct route│ [5V->3.3V │
│  body,   │              │  to Pi's USB]│  step-down    │
│  facing  │              │             │  (if needed)]│
│  inward] │              │             │              │
└──────────┴──────────────┴─────────────┴──────────────┘
```

- **IR LED driver zone**: one current-limiting resistor (calculated from the chosen LED's forward current, requires the datasheet at purchase time) + the LED body footprint, with a cutout facing the eye side
- **OLED interface zone**: 4-pin header (VCC/GND/SDA/SCL); the OLED module itself does not sit on this board, connected via a short flex cable; the OLED's physical position hugs the inside of the temple near the frame side (to make reflecting the light path onto the lens convenient)
- **USB/CSI routing zone**: not an actual circuit module, just cable-anchor points (small pass-through holes + hot-glue fixing), since the USB cable (to GC0308, originally planned for OV9281, updated 2026-10-30 — see the camera-selection change above) and the CSI cable (to the scene camera) both go directly to the Pi without passing through this board for signal processing — the carrier board here only keeps the cables from shaking loose
- **Power input zone**: a JST 2-pin header taking the line coming in from the waist battery pack; if the battery pack's output isn't already the 5V the Pi needs, a small step-down/regulator module goes here (most 18650+boost setups output 5V directly, in which case this is just a pass-through)

### 2.3 Wiring logic
- IR LED driver → directly to a Pi GPIO (through the current-limiting resistor, or a small MOSFET circuit if PWM dimming is used)
- OLED → the Pi's I2C bus (SDA=GPIO2, SCL=GPIO3, the standard I2C pins on the Pi Zero 2 W's 40-pin header)
- Power → does not go through the Pi's GPIO, connects directly to the Pi's 5V/GND (via the Pi's USB port, or soldered to the PP5V0 test point; for newcomers, start with the micro-USB port — simpler wiring and easier to disconnect/debug)

### 2.4 Fabrication recommendation
For the first revision, skip flex boards and use a **2-layer FR4 rigid board** (JLCPCB etc., ~10-piece minimum order, a few tens of yuan), to validate the module layout and wiring logic; for the temple's curvature-fitting problem, the first revision should bridge fixed anchor points with flexible ribbon cable plus segmented rigid boards, rather than jumping straight to FPC (flexible PCB fabrication is expensive and the design has low tolerance for error — not recommended for the first revision).

---

## 3. Software/Firmware Division of Labor (where the code lives, how it's written)

### 3.1 Directory structure (new, parallel to the existing OV9281_test project)

```
OV9281_test/
  glasses_system/              <- new directory, all code running on the Pi Zero 2 W
    scene_capture.py           <- CSI scene-camera capture (using picamera2, the Pi's official recommendation)
    distractor_classifier.py   <- closed-set classifier (simple color/shape rules at first, no deep learning in the MVP stage)
    mask_renderer.py           <- generates the dense-text occlusion pattern, renders to the OLED
    fusion_main.py             <- main loop: pupil coordinates (reusing pupil_detector_ellseg.py; it was pupil_detector.py before 2026-10-30, see the camera-selection change) + scene target position → projection-coordinate mapping → drives the OLED
    oled_driver.py             <- SSD1306 I2C driver wrapper (using the luma.oled or Adafruit_SSD1306 library)
```

- **Reuse, don't rewrite**: `fusion_main.py` directly does `from pupil_detector_ellseg import detect_eye, detect_pupil` (same interface as the original `pupil_detector.py` — just change one import line, see `261004/experiment_report.md` section 7h.2). The original plan here used `pupil_detector.py` (Haar cascade + Otsu threshold, a lightweight classical algorithm); on 2026-10-30, alongside the camera-selection change, this was switched to `pupil_detector_ellseg.py` (the EllSeg deep-learning model) — **this substitution brings a new risk that the original plan had never considered at all, and it must be verified standalone before proceeding further**: `pupil_detector.py` is pure OpenCV classical algorithm code, able to run at 60-100+ FPS on a PC — this was precisely the premise behind the original judgment that "the Pi Zero 2 W's compute is good enough." `pupil_detector_ellseg.py` depends on PyTorch running an actual convolutional neural network; the same PC (which has an RTX 4070 on board but no CUDA-enabled torch installed, see section 7f.2 — so this is CPU inference) only measures about 6-8 FPS (a consistent number verified repeatedly across sections 7f.6/7g.4/7i.10). The Pi Zero 2 W is a quad-core Cortex-A53 with no AVX instruction set, and a clock speed and cache far below a PC's x86 CPU — PyTorch running a CNN on this kind of ARM board is very likely to be substantially slower than even the PC's 6-8 FPS — **this number is currently completely unknown and cannot be assumed to "degrade gracefully from the PC number" — it must be measured**, corresponding to the risk annotation in step 1 of section 3.2
- **Runtime environment**: the Pi Zero 2 W runs Raspberry Pi OS Lite (no desktop, to save resources). ~~Develop remotely over SSH, using the VSCode Remote-SSH extension on this PC (`D:\工业设计\python.exe`) to connect over~~ **2026-10-30 update: the Pi Zero 2 W's WiFi has never been able to connect to the user's network, switched to direct USB connection to the PC for development** (the Pi Zero 2 W has no independent Ethernet port; direct-to-PC connection goes through the USB-OTG port's "gadget mode," where the Pi presents a virtual network adapter over the USB cable for the PC to use, and SSH then connects to that virtual adapter — not over WiFi). This change only affects **how development is done during the build phase**, it does not affect the final product's architecture — in the original plan the Pi's WiFi was only ever meant for the developer's remote connection; the entire data flow at runtime was already fully local (CSI camera straight into the Pi, USB camera straight into the Pi, I2C straight out to the OLED) with no step depending on the network — so even though the Pi's WiFi has never worked well, it doesn't block the final "single power line" wearable form factor.

### 3.2 Build order (avoid integrating all modules at once)

1. **First validate the Pi can run the existing algorithm — this step now hides an assumption with no data behind it, and it must be verified before proceeding**: deploy `pupil_detector_ellseg.py` (along with the PyTorch runtime it depends on and the EllSeg weight file `weights/all.git_ok` it needs — see `261004/experiment_report.md` section 7f.1 for how to obtain it) to the Pi, connect GC0308 over USB to the Pi, and run a Pi-ported version of the same logic as `gc0308_rerun_ellseg_video.py`, confirming the detection rate matches the order of magnitude measured on the PC (static-image 86.9%, continuous-video fair-frame accuracy 100% after fixed mounting — see sections 7i.6/7i.10) — **here, "matches order of magnitude" can only refer to accuracy, not FPS**: there is simply no historical reference number for FPS on this hardware ("15.17%/30.16%" from the old plan belonged to the `pupil_detector.py` era — the algorithm itself has since changed and no longer applies). Whether the Pi Zero 2 W can run PyTorch + EllSeg at an acceptable frame rate is an entirely new, unprecedented risk point — this one number needs to be measured first before deciding whether to continue at the Pi Zero 2 W hardware tier — if the measured frame rate turns out to be unusably low (say, single digits or below), the original hardware choice of "on-body compute unit = Pi Zero 2 W" itself may need to be reconsidered — this is not something a minor patch can fix
2. **Then validate the CSI scene camera standalone**: use the `picamera2` library alone to get capture/streaming working, with no detection logic attached
3. **Then validate the OLED display standalone**: use the `luma.oled` library to display a line of test text, confirming the I2C wiring is correct
4. **Only then do the fusion**: once all three are validated standalone, write `fusion_main.py` to chain them together

### 3.3 Specific implementation idea for the dense-text occlusion
- `distractor_classifier.py`: does predefined classification on the scene frame (simple methods for the MVP, e.g. brightness/color-histogram matching for a fixed region, or an extremely small MobileNet quantized model trained on 2-3 classes, depending on what the Pi Zero's actual compute allows)
- Once a region is judged a "distractor," `mask_renderer.py` uses that region's pixel coordinates within the scene frame, combined with the already-known geometric mapping relationship between the scene camera and the periscope projection region (requires actual measurement/calibration, similar to the 5-point calibration logic planned for Stage 10 of this project, reusable from the affine-fit method in `calibration.py`), to compute where on the OLED the text should be lit up
- The OLED driver uses `luma.oled`'s `ImageDraw` interface, looping to draw dense text (e.g. repeatedly printing "///" or filling the rectangular region with random characters)

---

## 4. Validation Methods

| Stage | Validation criterion |
|---|---|
| Pi runs pupil detection end-to-end | Detection rate matches the PC-side number in order of magnitude (static-image 86.9%, continuous-video fair-frame accuracy near 100% after fixed mounting — see sections 7i.6/7i.10). **FPS has no historical reference number and must be measured first** (EllSeg only gets 6-8 FPS on a PC's CPU inference, and the Pi Zero 2 W's compute is clearly weaker — this number is completely unknown — see the risk annotation in section 3.2, cannot be assumed usable) |
| CSI scene camera | Can stream stably, record the measured FPS |
| OLED display | I2C communication succeeds, screen shows the expected pattern |
| Geometric mapping calibration | Use a 5-point calibration method similar to calibration.py, verify the mapping error from scene pixel coordinates → OLED projection coordinates is within an acceptable range (needs defining a quantified "acceptable" standard first) |
| Overall fusion | Point at a known distractor (e.g. a phone), observe whether the OLED lights up the occlusion text at the correct location, record the actual wearing-view effect with a photo |
| Outdoor light test | Honestly record the actual degree to which the occlusion effect weakens in strong light — this is a known limitation, it needs data, not assumption |

---

## 5. Out of Scope for This Round

- Not doing open-set general object detection at the MVP stage (a closed, predefined set is sufficient to validate the concept)
- Not doing a flex board for the first PCB revision (validate the layout with a rigid board first)
- Not expanding on IR LED procurement details here (continuing the project's existing rule of "get the irradiance data sheet first, then test," handled separately) — **2026-10-30 update: whether this procurement is even necessary is now in doubt — see the "IR fill light" row's note in Section 1's hardware list; do not assume it still holds**
- Do not assume the Pi Zero 2 W's actual performance numbers — all FPS/detection-rate figures must be measured and recorded after the fact, never copied over from PC-side test results

---

## 6. No-IR Pure-Algorithm Direction Exploration (parallel branch, conclusion has moved past "exploratory" — see the 2026-10-30 update)

The experimental record has been migrated to `261004/experiment_report.md` section 7d (Approach A: classical algorithm improvement, the starburst method; Approach B: MediaPipe appearance-regression iris localization), which fits that document's "complete, traceable technical validation trail" framing and archives the actual code, data, manual-review process, and conclusions. This section keeps only a summary of the relationship to the main plan:

Neither no-IR exploration path affects the pacing of the main plan (Pi Zero 2 W all-in-one + 850nm IR fill), the two run in parallel without blocking each other. If either direction eventually proves a usable success rate without IR (on the order of, or exceeding, the 27.2% baseline — see `261004/experiment_report.md` section 6c), we would then re-evaluate whether to remove the IR LED module from the main hardware list (see the "IR fill light" item in Section 1's hardware list). Until then, the main plan continues as originally planned: purchase the IR LED, proceed with PCB and firmware development.

Note one one-directional information dependency (not a blocking one): if Approach B is to continue, it needs confirmation of whether the main dual-camera's actual field of view and wearing distance can capture a full face (see `261004/experiment_report.md` section 7d.3 open item ③). The answer to this question can only be confirmed once the main hardware selection/PCB layout (see Sections 1 and 2) is finalized — but it does not work the other way around — the main plan does not need to wait on Approach B's conclusion to proceed.

**2026-10-30 update**: the paragraph above was written in early October — by then, the judgment basis (the 27.2% baseline) had already been surpassed by later progress, and this is no longer "still exploratory" but already has a complete conclusion — both Approach A (starburst method) and Approach B (MediaPipe) have since been superseded by the later EllSeg path (EllSeg achieves 86.9% without IR on static images, and 100% fair-frame accuracy on continuous video after fixed mounting — see `261004/experiment_report.md` sections 7f-7i); Approaches A/B are no longer candidate directions. The previously open question of "whether to remove the IR LED module" now leans toward "most likely yes, but a dedicated formal validation of 'confirmed zero IR needed' specifically for the EllSeg path has not yet been done" — the "IR fill light" row in Section 1's hardware list has been annotated accordingly as "to be confirmed," do not treat it as already removed.
