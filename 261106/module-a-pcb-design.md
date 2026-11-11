# Module A (Glasses Body) PCB Plan — Wired Version + Wireless Upgrade Path

Status: plan stage, not yet fabricated
Dependencies: `261016/mounting-and-power-plan.md` (physical mounting and wiring), `261017/meeting-notes-cross-reference.md` (modular-split decision), `261014/pc-direct-control-feasibility.md` (the hard constraint that GC0308 must be USB-direct to the PC)

---

## 0. Premise: Why Not Put an ESP32 / Run WiFi on the Glasses

The 261017 meeting notes already settled on a modular split:
- **Module A**: lightweight glasses, does not integrate full-face recognition hardware
- **Module B**: a spatial/environmental camera, independent of the glasses, handles full-face recognition, synced via the cloud

Since the environment camera and WiFi responsibilities have already been handed off to Module B, there's no need to put an ESP32 running WiFi on the glasses (Module A) anymore — doing so would go against the teacher's explicit direction of "avoid over-stacking technology, keep the prototype simple." GC0308 is itself a USB UVC module and must be wired directly to the PC (a hard constraint, cannot be worked around, see Constraint 1 in the 261014 document).

**Conclusion**: the simplest plan at this stage is to let the glasses become a pure USB peripheral of the PC — the OLED also goes over USB-I2C, no wireless. This is the "wired version" in this document.

Going wireless isn't something to do right now, but as a complete "advanced design," this document also plans out the future upgrade path, so it can be applied directly later rather than starting from scratch.

---

## 1. Wired Version Plan (current stage, recommended to build this version first)

### 1.1 Architecture

```
PC ──USB──> [GC0308 eye-tracking camera]  (direct connection, does not go through the custom board, a hard constraint)
PC ──USB──> [custom small board: USB-C → CH341T] ──I2C──> [OLED 0.96" module] ──convex lens + half-mirror──> eye
```

### 1.2 Bill of Materials

| Component | Role | Sourcing reference (in stock at LCSC) |
|---|---|---|
| USB-C socket | the board's only interface, connects back to the PC, also provides power | TYPE-C-31-M-12 |
| CH341T | USB-to-I2C bridge chip, lets the PC act directly as the I2C Host driving the OLED, no MCU needed on the board at all | CH341T (SSOP-20, SMD, I2C mode) |
| Decoupling capacitors | chip supply filtering | 0.1µF ×2 (0402) |
| I2C pull-up resistors | needed on-board if the OLED module itself doesn't already have pull-ups | 4.7kΩ ×2 (0402, include or omit based on actual testing of the OLED module) |
| OLED interface | 4-wire I2C: VCC / GND / SDA / SCL, connecting to the already-validated OLED + convex-lens + half-mirror light path | match whatever header/FPC connector the OLED module itself uses |
| Pass-through connector (optional) | purely for physical cable management, bundling GC0308's USB cable with this board's USB cable — doesn't go through any chip, purely mechanical pass-through | 2-pin/4-pin header or FPC clip |

### 1.3 Advantages

- Zero MCU, zero WiFi, zero battery on the glasses — a genuine "optical smart glasses" rather than "glasses with a dev board strapped on"
- The PC side uses `pyusb` or the official CH341 Python/DLL library to directly write SSD1306 registers and render the mask, no need to write firmware for a microcontroller at all — the shortest possible development chain
- Very few components (one bridge chip + a handful of passives + two connectors), the board can be made very small, easily fitting inside the temple

### 1.4 To Be Verified

- [ ] CH341T's I2C driver mode's library support and measured latency on the target OS (Windows, the default environment for the PC direct-control plan)
- [ ] Whether the OLED module already includes its own I2C pull-up resistors (determines whether the board needs to solder them on)
- [ ] Whether the board's actual size can fit inside the temple's internal space, and whether it conflicts with the weight-distribution/wiring plan in 261016

---

## 2. Structural Engineering Reference: PCB-as-Frame (the Arduglasses Case, Provided by the Teacher on 2026-11-06)

The teacher sent over the Hackster project [Arduglasses](https://www.hackster.io/bateske/arduglasses-d7c00a) as a reference. First, let's be clear about what this case **is and isn't**, before discussing which parts are worth borrowing.

**What the project actually is**: Arduglasses' OLED is **opaque** — the lens itself is the screen, and the wearer only sees the screen content (the blue skull pattern in the photos is a facial-expression effect shown to outside observers, not the wearer), you cannot see through it to the real world. This is the opposite direction from our already-validated "OLED + convex lens + half-mirror" plan — our light path's core purpose is **to preserve a real view of the world, only selectively overlaying/occluding where needed**, which is a hard requirement for the ADHD use case. **Conclusion: we do not adopt Arduglasses' "screen-as-lens" optical approach; Section 1's wired-version light-path design stands unchanged.**

But it does offer three things worth borrowing on the engineering-implementation side, unrelated to the optical-path choice:

### 2.1 PCB-as-Frame (the board itself serves as a structural member)

Arduglasses makes the front frame and temples directly out of the rigid PCB's own outline (rather than making a small board that fits inside the temple cavity, with a separate plastic/3D-printed shell). The circuit board itself is the skeleton, saving the extra shell part, making the whole thing lighter and thinner.

**Implication for Module A**: Section 1's wired-version small board currently defaults to the "fits inside the temple cavity" approach; it could be upgraded to "the board itself is part of the temple's skeleton" — but two things need confirming first before adopting this:
- The strength and wearing comfort of a rigid FR4 board at the nose bridge/hinge (FR4 is fairly brittle, long-term wear at a flex point is prone to fatigue fracture, needs a flexible transition section to solve, see below)
- This would turn PCB fabrication from "one small board" into "an irregular structural part," raising both fabrication complexity and cost — is it worth investing in at this stage, or should it wait until the optical path and detection chain are validated before doing this optimization?

### 2.2 Front-Frame–to–Temple Flexible Transition Board (solving the problem of a rigid board crossing the hinge)

Arduglasses uses an FPC-like flexible board transition between the front frame and the temples, rather than routing a separate flex cable. If the "PCB-as-frame" approach is adopted, this is a problem that must be solved alongside it — a rigid board cannot cross the hinge's pivot point, a section of flexible board or ribbon cable is needed to bridge it.

### 2.3 Power Management Circuit Reference (completing Section 3.3's wireless-version power design)

Arduglasses' schematic splits the power section into two separate chips — a **Boost** (step-up) chip and a **Charger** (charge management) chip — rather than one chip handling everything. This validates that Section 3.3's "TP4056 + LDO/boost" split approach is a common pattern, and this module division can be referenced directly during component selection without having to feel it out from scratch.

**Conclusion**: these three points are recorded as "advanced design" structural-optimization directions, but they do not change what gets fabricated per Section 1's wired version right now — validate the optical path and detection chain first, then decide whether to upgrade the PCB into a structural member.

---

## 3. Wireless Upgrade Path (future stage, not doing this now)

### 3.1 Trigger Conditions

Only evaluate switching to this path once both of the following have been validated:
1. The calibration chain (scene-pixel → OLED-pixel affine mapping) runs end to end and is repeatable
2. The pupil-detection chain's stability (currently EllSeg on GC0308: 86.9% static, 100% continuous-video with fixed mounting) is reproduced in actual wearing conditions

Investing in wireless development before this is exactly the "over-stacking technology" the teacher explicitly warned against in the 261017 meeting notes.

### 3.2 Architecture

```
PC ──WiFi──> [custom small board: ESP32-S3-WROOM-1] ──I2C──> [OLED 0.96" module] ──convex lens + half-mirror──> eye
                     │
                  lithium battery + charge/discharge protection
GC0308 ──USB──> PC (unchanged, the hard constraint still exists, cannot be made wireless)
```

**Note**: going wireless can only solve the problem of "who drives the OLED, do we still need to trail a USB cable for it." GC0308's hard constraint as a USB UVC module (see Constraint 1 in the 261014 document) does not disappear just because the rest of the glasses go wireless — unless a small board capable of acting as a USB Host (a Pi/Orange Pi-class board, already rejected by the user, see the 261010 roadmap's deprecation note) is reintroduced in the future. In other words, **even after completing this section's wireless upgrade, the glasses will still have one cable to the PC**, just reduced from two (GC0308 + OLED) to one (GC0308 only).

### 3.3 Component Changes (relative to the wired version)

| Component | Wired version | Wireless version | Note |
|---|---|---|---|
| MCU | CH341T (no MCU) | ESP32-S3-WROOM-1 (or the smaller ESP32-C3-MINI) | needs to run the WiFi stack + I2C driving the OLED; the C3 package is smaller, better suited for fitting inside the temple, but the S3 has more GPIOs and more compute headroom |
| Power | direct USB 5V supply, no battery needed | needs a lithium battery + charge/discharge management chip | new: TP4056 (charge management) + protection board (overcharge/overdischarge/short-circuit protection — many off-the-shelf lithium cells already include this, prefer a cell with a built-in protection board) |
| Regulation | not needed (USB 5V is sufficient) | needs a 3.3V LDO or buck-boost chip | lithium battery voltage range is 3.0-4.2V, ESP32 needs a stable 3.3V, recommend AMS1117-3.3 (simple) or TPS63020 (more efficient but pricier) |
| Interface | USB-C | USB-C (charging only, no longer carries data) | data goes over WiFi, USB-C downgrades to a pure charging port |
| Antenna | none | PCB antenna or external IPEX antenna connector | be careful not to wrap the antenna area in metal housing (the 261016 document already flagged this applies equally to the ESP32-CAM) |

### 3.4 Upgrade-Path Compatibility Design (things to consider now, while laying out the board)

Even building the wired version now, if we want the future upgrade to not require redesigning the whole board from scratch, the layout can reserve:
- Both CH341T and ESP32-S3/C3 route their I2C output to the same OLED connector — **choose footprints that are pin-compatible, or at least easy to route to**, making it convenient to swap chips later
- Reserve a battery-connector footprint (JST-PH 2-pin, unpopulated, leave the pads empty) — even though the wired version doesn't use it, the footprint costs nothing to reserve
- Reserve USB-C routing for a future "charge-only" scenario — no need to add TP4056 now, but the VBUS trace can be routed out, making it easy to add later

This is "reserving room" rather than "doing it now" — the wired version only populates the CH341T-related components as usual, the reserved pads stay empty, with no impact on current fabrication cost or complexity.

### 3.5 To Be Verified (wireless version, only needed once the trigger conditions above are met)

- [ ] Measured I2C-driving-OLED latency for ESP32-S3 and ESP32-C3 (relative to the CH341T plan's extra cost of one additional WiFi hop)
- [ ] Whether the overall weight change after adding the lithium battery + charge/discharge circuit breaks the weight-distribution budget in the 261016 document
- [ ] Whether the antenna's position and physical distance from GC0308/OLED causes mutual interference (electromagnetic / structural)

---

## 4. Summary: What to Do Now, What to Do Later

| Stage | Do | Don't |
|---|---|---|
| Now (first fabrication revision) | USB-C + CH341T + OLED interface, purely wired, zero MCU | don't add a battery, don't add WiFi, don't add an ESP32 |
| Once the calibration + detection chain is validated | evaluate whether to switch to the ESP32-S3/C3 + lithium-battery wireless version | don't invest in wireless development before validation (echoing the 261016 document's existing conclusion in its "power/wireless" open item) |
| Once the wireless version is validated (further out) | evaluate whether to upgrade the PCB into a "board-as-frame" structural member (Section 2's Arduglasses reference) | don't change Section 1's small-board-plus-plastic-structure approach at this stage, don't blindly chase structural integration |

The wired version's BOM is extremely minimal, low cost, and low debugging cost — the priority is fabricating and validating whether the "USB-I2C bridge driving an OLED + convex lens + half-mirror" light path holds up under actual wearing conditions — that is the real question to validate at this stage, not whether to go wireless.
