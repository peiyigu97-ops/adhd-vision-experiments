# 261030 — Phase 1: The PC-Takes-Over-Everything Chain, First Run With Real Data

Corresponds to **Phase 1** of `261014/pc-direct-control-feasibility.md`'s Section 8 "Phased Roadmap":
> PC takes over everything. ESP32-CAM only does two things: stream the scene video, paint the mask the PC sends back onto the OLED. Goal: get the **geometric calibration** (scene pixel ↔ OLED pixel) and the **mask visual effect** right first, don't touch FOMO yet, fastest path to a result.

## Background: What Is Being Replaced This Round

`261022/fusion_poc.py` already validated that the "judge whether to occlude → send /mask command" state machine + HTTP timing has no inherent problem, but its README explicitly states two things are simulated:

1. "Current gaze position": moved manually via WASD keys, not real eye-tracking data
2. "Distractor position": a hardcoded fixed rectangle, not real object detection

`261022/README.md` itself laid out the replacement order:
1. First fill in a trustworthy "pupil coordinates → OLED coordinates" calibration
2. Then integrate a real object-detection model
3. Replace the simulated parts in `fusion_poc.py` with the real outputs from the two items above

**This round only does item 1**; item 2 (real object detection/FOMO) is explicitly out of scope per Phase 1's definition — "don't touch FOMO" is a direct quote from the `261014` document, not an oversight this time.

## Relationship to the Existing 261004 Calibration Script (Why Not Just Reuse calibration_ellseg.py)

`261004/calibration_ellseg.py` calibrates "pupil pixel coordinates → an 800×600 PC window's coordinates," and its `detect_eye()` uses a two-stage Haar cascade face + eye detector — this detection logic is designed for a scenario like OV9281's, where "the eye only occupies a small portion of the frame, and the eye must first be located within the larger frame."

GC0308 isn't used that way: `261029/gc0308_capture_video.py` already validated that when GC0308 works at close range, the eye already fills the frame by default, and the correct approach is to manually box an ROI once at the start (excluding the nose-bridge noise region) and reuse that fixed box throughout, rather than running Haar cascade frame by frame (which would likely fail to find a "face" anyway).

So this folder has a newly written calibration script specifically for GC0308, targeting **the OLED's 128×64 pixel coordinate system** directly (rather than an arbitrary 800×600 window), eliminating the "calibrate to an arbitrary space, then convert to OLED coordinates" step and the error it introduces.

## Scene-Camera → OLED Mapping: Using the Simplest Possible Scheme, Not a Real Geometric Calibration

`261022/esp32cam_wifi_mask_server.ino`'s documentation states clearly: **the OLED currently has no optical lens installed, so the OLED screen itself directly represents "what the eye can see"** — the (x,y,w,h) received by the `/mask` endpoint goes through no geometric mapping at all, it's just the OLED's own pixel coordinates.

`261016/mounting-and-power-plan.md` mentioned that the real scene-camera → OLED geometric calibration (which requires an external reference camera to photograph where the OLED, after reflecting through the lens, actually lands in the real world) hasn't been done yet — this is independent of the current Phase 1, and will only matter once the lens is installed.

In this round's `phase1_fusion.py`, the step from "distractor position in the scene frame" to "OLED coordinates" uses **the simplest possible linear scaling** (the ESP32-CAM's QVGA 320×240 frame → OLED 128×64, roughly a 2.5x proportional downscale) — this is a deliberate simplified placeholder, not a formal calibration; the code comments make this clear, don't mistake it for a completed geometric-mapping calibration.

## Files

- `calibration_gc0308_oled.py` — a GC0308-specific 5-point calibration, with the target points directly being 5 points in the OLED coordinate system (128×64). After calibration, the fitted affine matrix, the GC0308 crop box, and the camera index are all saved together into one JSON file (`gc0308_oled_calibration.json`), which the fusion script below loads directly, so it doesn't need to re-calibrate every time
- `phase1_fusion.py` — the Phase 1 main program: loads the calibration JSON → reads GC0308+EllSeg in real time to compute the real gaze point (already in the OLED coordinate system) → polls the ESP32-CAM's `/capture` for a scene reference display (overlaying a "fake distractor" rectangle, converted to OLED coordinates via the linear scaling described above) → reuses the "only send a request on state change" debounce logic already validated in `fusion_poc.py` → actually calls `/mask`, this time passing coordinates computed from real eye-tracking data, not keyboard simulation

## Run Order

1. Confirm GC0308's current camera index (it may have changed again):
   ```
   python "261004/gc0308/identify_gc0308.py"
   ```
2. Run calibration (only needs to be done once after GC0308 is fixed-mounted to the frame, unless the physical position changes again later):
   ```
   python "261030/calibration_gc0308_oled.py" --camera-index <confirmed index>
   ```
   Follow the prompt to box an ROI once, then look at the 5 calibration points in turn; once finished, `gc0308_oled_calibration.json` is generated in the current directory
3. Confirm the ESP32-CAM's IP (via the serial monitor, or the router admin page), then run the fusion main program:
   ```
   python "261030/phase1_fusion.py" --esp32-ip <ESP32CAM's IP>
   ```
   This time the gaze point shown in the window is real (it follows your eye), the distractor rectangle is still a hardcoded placeholder (labeled "FAKE OBJECT"), and you can watch whether the real OLED correctly draws/clears the occlusion pattern as the real gaze point moves in and out of this rectangle

## Explicitly Not Done This Round, Next Steps

- **Real object detection/FOMO**: out of scope per Phase 1's definition, comes up in Phase 2 (`261014` section 8)
- **Formal geometric calibration of scene camera → OLED**: currently using the linear-scaling placeholder, will be done once the lens is installed (the "open item" in `261016`)
- **Calibration precision**: historical data in `261004/experiment_report.md` section 7h shows 5-point calibration error on the order of 114-154px (under an 800×600 window); once converted into the OLED's 128×64 space, this error's proportional size becomes much more pronounced (114px is close to the OLED's entire width) — this round calibrates GC0308 directly against OLED coordinates, so the error's order of magnitude will likely be different, and needs to be measured and honestly recorded, it cannot be assumed to be "probably similar"
