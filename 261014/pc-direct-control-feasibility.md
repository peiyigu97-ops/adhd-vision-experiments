# ESP32CAM + GC0308 Dual-Camera Eye Tracker · PC Direct-Control Feasibility Analysis

> Date: 2026-10-14 (title / eye-tracking camera model updated 2026-10-30, see the update note below)
> Related: [`261010/dual-camera-glasses-roadmap.md`](../261010/dual-camera-glasses-roadmap.md) (the 261010 v2 plan, **now deprecated, see the update note below**), `261004/` (OV9281/GC0308 measured-data code), `261004/experiment_report.md`, `260809/ADHD PlanA 技术方案整理.md` (FOMO lead, not included in this repository)

> **2026-10-30 update (two changes)**:
> 1. **Eye-tracking camera switched from OV9281 to GC0308**: reason and validation data in `261004/experiment_report.md` section 7i — the OV9281 module was too bulky, the prism-reflection alternative was infeasible, GC0308 is physically smaller and easier to mount; with the EllSeg detector it reaches 86.9% on static images and 100% fair-frame accuracy on continuous video after fixed mounting — already validated feasible. Every "OV9281" below should be read as "GC0308" accordingly. Constraint 1's "USB UVC module" hardware-form conclusion applies equally to GC0308 (GC0308 is likewise a USB UVC module, likewise needs one USB cable to the PC — this hard constraint has not changed with the camera swap).
> 2. **This plan is upgraded from "pre-validation bench" to the current main-line plan**: the Pi Zero 2 W's WiFi has never connected, and the user has decided to abandon the entire Pi all-in-one route (the 261010 roadmap is now marked deprecated), adopting this document's "PC takes over everything" architecture directly as the current direction, no longer a "temporary plan to validate, then migrate back to the Pi." Sections 9 and 10's "open questions" therefore now have answers — see the in-section update notes.

---

## 1. The Question This Plan Answers

In the 261010 roadmap (v2, **now deprecated**), all compute and display sat on the Raspberry Pi Zero 2 W, which simultaneously drove two cameras, ran pupil detection, and rendered the OLED mask. This plan proposes an alternative path:

**Drop Linux single-board computers like the Raspberry Pi / Orange Pi entirely, use the PC as the sole compute unit, and let the ESP32-CAM serve only as an "outward-facing scene camera + OLED driver node," connected to the PC over WiFi.**

Proposed original topology:

```
[GC0308 + IR]  ──USB──>  PC (pupil detection + resolving the user's attention target)
                          │
[ESP32-CAM]    ──WiFi──>  PC (scene image uplink)
                          │
                          └──WiFi──>  ESP32-CAM ──I2C──> OLED (optical occlusion output)
```

Data flows in two paths:
- **Eye-tracking path**: GC0308 (built-in IR, see section 7b.1) captures the pupil image → the PC resolves it with EllSeg → yields "which direction/object the user is looking at outward"
- **Scene path**: the ESP32-CAM captures the outside scene → the PC judges whether that object is a distractor
- **Output path**: if judged a distractor → the PC sends back a command → the ESP32-CAM drives the OLED → optical occlusion

> **The two devices connect differently — do not conflate them:**
> - **ESP32-CAM**: independently powered (battery/power supply, not routed through the PC), **fully wireless** to the PC — can only be WiFi (Bluetooth bandwidth is insufficient, see Constraint 2), no cable needed to the computer at all.
> - **GC0308**: because it is a USB UVC module, it must have a **USB cable** directly to the PC (see Constraint 1) — this is dictated by its hardware form and cannot be worked around; this constraint is shared by both OV9281 and GC0308, unchanged by the camera swap.
>
> The "Constraint 1" and "the cost of cutting the Pi" discussed below both refer to this one GC0308 cable, **they do not involve the ESP32-CAM**.

**Conclusion: the plan is viable, and is the pragmatic choice for this stage. But it comes with one essential cost and two hard constraints, which must be accepted before proceeding.**

---

## 2. Conclusions at a Glance

| Question | Conclusion |
|---|---|
| ESP32-CAM independently powered + fully WiFi to the PC | ✅ Feasible, no cable to the computer needed at all; VGA @ 10-15fps is the ceiling |
| What path does GC0308 take | ❌ **USB direct to the PC only**, cannot route through the ESP32, cannot be made wireless |
| Replace WiFi with Bluetooth (for the ESP32-CAM) | ❌ **Does not hold at all**, bandwidth is an order of magnitude short |
| The cost of cutting the Pi | ⚠️ This cost **falls entirely on the GC0308** — the wearer is tethered to the computer by one USB cable. The ESP32-CAM itself is fully wireless throughout, unaffected |
| Suitable use case | ✅ Bench prototype / classroom demo; **2026-10-30 update: this is now the final positioning, no longer required to also satisfy "truly wearable"** |
| Recommended architecture | ⭐ Push FOMO down onto the ESP32-CAM, the PC only sends the gaze-point coordinates |

---

## 3. Hard Constraints (cannot be bypassed, must be accepted first)

### Constraint 1: GC0308 must have one USB cable to the PC

Already validated under `261004/`: GC0308, like OV9281, is a **USB UVC module** (confirmed by enumeration in `gc0308/identify_gc0308.py`, a close-range eye-tracking module, see `261004/experiment_report.md` section 7i for details).

The UVC stream must be received by a **USB Host**. The only devices that can act as Host are Linux single-board computers — exactly the category this plan drops. The ESP32-S3 does carry USB-OTG, but only at **full-speed 12Mbps**; a 720p grayscale single frame is 0.92MB, which works out to **under 2fps** — unusable.

> **The cost of this plan: cutting the Pi = the wearer is tethered to the computer by one USB cable.**
> USB 2.0's practical reliable length is 3-5m; longer requires an active extension cable or a powered hub.

This constraint directly determines the plan's positioning:

| Use case | Feasible? |
|---|---|
| Bench prototype / classroom demo | ✅ Fully feasible, and a good choice |
| Actually wearing it while walking around | ❌ A cable means not wearable |

~~**If the ultimate goal is wearability, the Pi route must be kept, it cannot truly be dropped.**~~ **2026-10-30 update: the Pi Zero 2 W's WiFi problem was never solved, the user has decided to abandon this route, accepting the cost that "this stage is not truly wearable," and focusing on getting the PC direct-control path fully working.**

### Constraint 2: WiFi only, Bluetooth is ruled out outright

This needs to be stated clearly up front — of the user's proposed "WiFi / Bluetooth connection," the Bluetooth half does not hold:

| Channel | Actual throughput | Can it carry video? |
|---|---|---|
| ESP32 BLE | actually a few KB/s to a few dozen KB/s (theoretical tuned ceiling ~700kbps) | ❌ an order of magnitude short |
| BT Classic SPP | about 100-200KB/s | ❌ not enough |
| ESP32 WiFi TCP | actually 5-15Mbps (drops to 3-8Mbps under concurrent camera load) | ✅ |

And **ESP32's WiFi and Bluetooth share the same 2.4GHz radio**, so they cannot both run at full speed simultaneously.

> **Conclusion: WiFi is the only option. Bluetooth isn't even good enough as a backup channel.**

---

## 4. The Bandwidth and Latency Math

### 4.1 Bandwidth

- VGA 640×480 JPEG (quality 12) ≈ 30KB/frame
- 10fps → 300KB/s ≈ **2.4Mbps** (fits within the ESP32 WiFi)
- ESP32-CAM's actual capture-and-send-simultaneously throughput is about 3-8Mbps

> **Technical ceiling: VGA @ 10-15fps.** Pushing to 720p or higher frame rate immediately hits the bandwidth floor.

### 4.2 Latency Chain (the naive "PC takes over everything" plan)

| Stage | Time |
|---|---|
| Scene capture + JPEG encoding | 15-30ms |
| WiFi uplink | ~60ms |
| PC decode + inference (GPU / CPU) | 20-50ms / 100-300ms |
| Result return | ~10ms |
| OLED refresh (400kHz I2C, full-screen 1024B) | ~23ms |
| **Total** | **about 130-200ms (GPU scenario)** |

---

## 5. Key Insight: Latency Is Tolerant to Stillness, But Head Turns Cause Mask Slippage

### 5.1 Good news: the geometric mapping is fixed

The scene camera, the eye, and the OLED are **all rigidly mounted on one pair of glasses**, fully head-locked. Therefore:

> **World direction → scene-camera pixel → OLED pixel** is a **fixed mapping**, determinable with a single calibration.

The 261010 roadmap's Stage 10 five-point calibration logic (reusing the affine fit in `261004/calibration_ellseg.py`, 2026-10-30 update: the calibration script has since switched from `calibration.py` to the EllSeg version, see `261004/experiment_report.md` section 7h) is exactly what handles this.

This means: **the PC being a bit slow doesn't affect "where on the OLED the mask is drawn"** — it only affects "how quickly you notice you're looking at a distractor."

### 5.2 The trap: the mask and the distractor move out of sync

The mask is drawn on the OLED, and the OLED turns with the head:

- A head turn → the mask on the OLED **does not move on the retina**
- But the distractor **does move on the retina** → the two instantly diverge

> **While the head is turning, every frame's latency turns into mask slippage.**
> At a head speed of 300°/s, 200ms of latency can slip by 60°.

**This is the thing that genuinely needs optimizing, not the bandwidth.**

| Scenario | Latency tolerance |
|---|---|
| Static viewing, static distractor | Doesn't matter, even hundreds of ms are fine |
| During a head turn | Latency = slippage, must be pushed down to roughly one frame |

---

## 6. Recommended Architecture: Push FOMO Down onto the ESP32-CAM

`作品集/课程/260809/ADHD PlanA 技术方案整理.md` (not included in this repository) already recorded: the teacher recommended **FOMO runs on the ESP32 in about 100KB of memory**. This lead connects directly here.

```
[GC0308 + IR] ──USB──> PC: pupil detection (EllSeg) → gaze-point coordinates
                         │
                         └──WiFi (kbps scale)──> ESP32-CAM
                                                  │
                            local FOMO detection + local mask rendering
                                                  ↓
                                               OLED
```

### 6.1 Why this is better

1. **Mask positioning no longer waits on a PC round trip.** The ESP32-CAM knows for itself which pixel of **its own frame** the distractor is at, and "own-frame pixel → OLED pixel" is a fixed calibration matrix. The mask updates at the camera's frame rate, latency ≈ one frame + OLED refresh ≈ **60-90ms** (versus 200ms for the naive plan).
2. **Bandwidth drops from Mbps to kbps.** The PC only sends "which pixel of the scene frame the gaze point falls on," a few bytes @ 30Hz. **The scene video itself never needs to be transmitted at all.**
3. **The PC's latency stops mattering.** The PC being 200ms slow only affects response timeliness, not where the mask is drawn. A person staring at their phone is a matter of hundreds of milliseconds to seconds — acceptable.
4. **Consistent with item 5 of the roadmap**: the MVP uses a closed, predefined set of categories ("phone screen," "television," "billboard"), not open-set general detection.

### 6.2 Hybrid mode (if the PC's larger model is still wanted)

Keep the PC's compute, but divide the work clearly and asynchronously:

- **ESP32-CAM runs FOMO** → handles "**fast localization**"
- **PC runs the large model** → handles "**accurate judgment**"

Localization always stays local; it's fine if the PC's conclusion arrives a bit later.

---

## 7. Specific Engineering Pitfalls

| # | Pitfall | Explanation and fix |
|---|---|---|
| ① | **The ESP32-CAM has no IR-cut filter** | AI-Thinker boards generally don't have one (this is also why it has night-vision ability and looks pinkish in daylight). **GC0308's built-in IR (see `261004/experiment_report.md` section 7b.1) will leak directly into the scene camera**, causing color shift and lower contrast. Cross-leakage on the same pair of glasses is nearly inevitable. Fix: add an IR-cut filter to the scene camera, or build a physical light baffle between the two lenses. **2026-10-30 update: the original text here targeted OV9281's external 850nm fill light; now that it's switched to GC0308, the light source is the module's own built-in IR instead — the cross-leakage risk itself hasn't gone away, only the source changed from "external light" to "built into the module"; the fix is unchanged** |
| ② | **Don't do "one HTTP request per frame"** | At 10fps, TCP handshake + HTTP header overhead is too punishing. Use a **persistent connection** (WebSocket or raw TCP + binary framing) |
| ③ | **OLED refresh and WiFi fight for CPU** | Split across the dual cores: pin the WiFi stack to core 0, pin camera capture + OLED drawing to core 1 |
| ④ | **Pin conflicts** | OLED on **GPIO14(SDA) / GPIO15(SCL)**, **avoid GPIO12** (MTDI strapping — wrong boot-time level and the board won't come up). GPIO16 is already taken by PSRAM |
| ⑤ | **Power supply actually gets simpler** | Since we're already tethered by USB, draw a 5V line straight from the PC — no battery, no worrying about brownout. One of the few actual conveniences of the wired plan |

---

## 8. Phased Roadmap

| Phase | Content | Goal |
|---|---|---|
| **Phase 1** | PC takes over everything. ESP32-CAM only does two things: stream the scene video, paint the mask the PC sends back onto the OLED | Get the **geometric calibration** (scene pixel ↔ OLED pixel) and the **mask visual effect** right first. Don't touch FOMO yet, fastest path to a result |
| **Phase 2** | Push FOMO down onto the ESP32-CAM, the PC steps back to only sending the gaze point | Solve **head-turn slippage**, pushing latency from 200ms down to 60-90ms |
| ~~**Phase 3**~~ | ~~If a truly wearable form is the goal: move the OV9281 back to a Pi/Orange Pi, shorten the USB cable to inside the glasses~~ | ~~Eliminate the trailing cable~~ **2026-10-30 update: the Pi route has been abandoned (261010 roadmap deprecated), this phase is no longer planned** |

> Phase 1 and Phase 2 code are compatible — `mask_renderer`'s output just needs a different source, nothing is wasted.

---

## 9. Open Questions

~~**Is this stage's goal a bench demo, or a final product meant to be worn while walking around?**~~

**2026-10-30 update: already answered** — bench demo / PC direct control, not pursuing true wearability. The Pi Zero 2 W's WiFi problem couldn't be solved, the user decided to abandon the wearable route, with both GC0308 and ESP32-CAM connected directly to the computer. Per the original open-question text above, this corresponds to the "bench demo" branch, and the recommendation to go straight to a merged Phase 1 + Phase 2 still holds, no change needed.

---

## 10. Relationship to the v2 Roadmap

**2026-10-30 update: the v2 roadmap (261010, the Pi Zero 2 W all-in-one plan) is now deprecated; this plan is no longer a "pre-validation bench," it is the only main-line plan currently being pursued.** The table below is kept as-is, as a historical record of the difference between the two plans:

| Dimension | v2 roadmap (261010, deprecated) | This plan (261014, current main line) |
|---|---|---|
| Compute location | Pi Zero 2 W (on-body) | PC (desktop) |
| Scene camera | Pi CSI Camera Module 3 | ESP32-CAM |
| Eye-tracking camera | OV9281 USB → Pi | GC0308 USB → PC (as of 2026-10-30, was OV9281) |
| Wearability | ✅ only one power line (in theory, never actually validated — it was already a paper plan before the Pi's WiFi problem surfaced) | ❌ needs one USB cable to the PC (this cost has been accepted) |
| Development speed | Slow (the Pi Zero's weak compute means every number must be measured; the WiFi problem meant even the dev environment couldn't be set up) | Fast (the PC has ample compute, the algorithm can be reused directly) |
| Applicable stage | ~~final form~~ already abandoned | **current main line, no longer just a "prototype validation stage"** |

~~**Positioning recommendation: this plan should serve as a "pre-validation bench" for v2, not a replacement.**~~
~~Validate the three core things — geometric calibration, mask visuals, distractor judgment — on the PC first, then decide whether to migrate back to the Pi. The already-purchased ESP32-CAM + OLED hardware therefore isn't wasted, it becomes part of the validation bench.~~

**Current positioning**: this plan is the endpoint, not a waypoint. The ESP32-CAM + OLED + GC0308 are already mounted on the frame per this architecture (see `261004/experiment_report.md` section 7i.11, confirmed by the user on 2026-10-30), the next steps are weigh-and-wear testing and the scene-camera → OLED geometric calibration, not "validate then migrate back to the Pi."

---

*This document was compiled from a discussion on 2026-10-14, updated 2026-10-30 for camera selection and plan positioning. The technical figures (bandwidth, latency, FPS) are engineering estimates; actual values must be **measured and recorded per the roadmap's existing rule, not taken as conclusions directly**.*
