# Glasses-style Dual Camera + OLED Prototype — Mounting and Power Plan

Status: planning stage, assembly not yet started
Dependencies: `261004/experiment_report.md` (pupil-detection feasibility), `261010/dual-camera-glasses-roadmap.md`, `261014/pc-direct-control-feasibility.md`

---

## 0. Correcting a Previous Misjudgment

The previous round of discussion treated the ESP32-CAM as a "pure relay board" and suggested mounting the whole thing behind the ear, with only a cable running to the front of the frame. **This was wrong**: the OV2640 on the ESP32-CAM faces outward to shoot the scene, and just like OV9281 and the OLED, it is a sensing component that must hug the face with a strict orientation requirement — it cannot be moved away from the front of the frame. This plan is based on the corrected premise: **all three components stay at the front of the frame**, and the balance problem is solved by left-right distribution, not front-back distribution.

---

## 1. List of the Three Face-Hugging Components

| Component | Orientation | Position requirement | Weight reference (bare part) |
|---|---|---|---|
| OV9281 (eye-tracking camera) | inward, aimed at the eyeball | near the temple's hinge, angle fixed, no longer moving much after that | about 5-10g (including the lens barrel) |
| OLED 0.96" + reflector | facing the inside of the lens, entering the field of view via reflection | in front of the same eye, same side as OV9281 | about 3-5g |
| ESP32-CAM (scene camera) | outward, shooting the scene | the other front corner of the frame, or the same-side outer edge, FOV must not be blocked by the temple/hinge | about 8-12g |

OV9281 + OLED must be on the same side (both serving the gaze and projection of the same eye). The ESP32-CAM can sit on the other front corner, spreading the weight out rather than concentrating it on one side.

---

## 2. Power Plan

### OV9281: no extra power needed
It's a USB UVC camera; on the PC direct-control path it already needs a USB cable back to the computer anyway, which handles power — no battery needed.

### ESP32-CAM: USB-to-5V supply, no battery at this stage
Solder out two thin wires (5V / GND), bundle them together with OV9281's USB cable running back to the computer, and connect to a USB-to-5V power head. Peak current is about 200-250mA, well within a USB port's 500mA supply capacity.

Rationale: this stage is a feasibility prototype, the priority is validating the calibration and detection chain, not building a wearable final product. Adding a lithium battery means an extra boost/protection/charging circuit, higher debugging cost, and a battery bulging against the face is a risk not worth taking. Once the chain is working, consider going wireless with battery power — that's a task for the next stage.

### Shared cable bundle
Bundle the three components' wiring (OV9281's USB cable, the ESP32-CAM's 5V/GND + I2C to the OLED, the OLED's own 4-wire I2C) along the temple as much as possible, splitting into one bundle per side, converging at the end of the temple.

---

## 3. Weight and Balance

With everything kept at the front, the balance strategy shifts to **left-right distribution**:
- One side (say the left-eye side): OV9281 + OLED, roughly 8-15g combined
- The other side (right front corner): ESP32-CAM, roughly 8-12g

The two sides end up close in weight, better balanced than piling everything on one side. Once actually assembled, do an actual weigh-in and wear test — if it's noticeably heavy on one side or uncomfortable on the nose bridge, adjust from there; the estimated numbers are only a pre-assembly reference, not the final word.

---

## 4. Assembly Order

1. **Fix OV9281 and the OLED first** (same side): these two have the highest precision requirement for angle — once the pupil/reflection alignment is dialed in, fix them with hot glue, to avoid position drift later causing the kind of "head displacement" data-incomparability problem already validated in the `261004` report.
2. **Then fix the ESP32-CAM** (the other front corner):
   - the lens direction must match the scene direction, not blocked by the temple/hinge
   - don't wrap the antenna area in metal or foil (it will directly affect WiFi)
   - the board heats up when worn against skin for a long time (camera + WiFi running simultaneously), leave a little clearance for heat dissipation, don't press it flush against the skin
3. **Leave strain relief in the wiring**: leave some slack in the cable segment at the hinge's pivot point, and consider adding a short piece of heat-shrink tubing, to prevent repeated opening/closing from eventually snapping the wire.

---

## 5. Open Items / Next Steps

- **Weigh-in and wear test**: once everything is mounted, actually measure whether the balance is acceptable, decide whether the left-right distribution needs further adjustment.
- **Calibration dependency unresolved**: the code for the scene-camera-pixel → OLED-pixel projection mapping calibration hasn't been written yet. The `261010` document mentioned the affine-fit logic in `calibration.py` could be reused, but the capture method needs to be redesigned (requires a fixed-position external reference camera to photograph where the OLED, after reflecting through the lens, actually lands in the real world) — this is independent of the current mounting plan and is the next technical gap to address.
- **Pupil-detection success rate is still 27.2%** (see `261004/experiment_report.md`): finishing the physical mounting does not mean the gaze-judgment chain is usable — these two things need to be advanced separately.
- **Power / wireless**: once the calibration + detection chain is validated, evaluate whether to switch to battery power and whether on-board processing is needed (ESP32-CAM running FOMO) — not invested in at this stage.
