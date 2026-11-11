# Cross-Reference: 261017 Meeting Notes vs. Measured Results

## Premise (important, don't get the direction backwards)

The points in this document described as "consistent with the teacher's meeting notes" are **not** a case of the teacher independently verifying and arriving at the same conclusion — rather, the user relayed the measured results from `261004/experiment_report.md` section 7d (starburst method, MediaPipe detection) and the ESP32/OV9281 interface analysis from `261016` **to the teacher**, who understood them, agreed, and made product decisions based on them. The information flow is one-directional: user tests → relayed to the teacher → teacher adopts it and gives next-step direction. It is not a case of "mutual confirmation" where both sides independently reached the same conclusion.

---

## 1. Cross-Reference Against Existing Measured Results

| Meeting note content | Corresponding measured source | Cross-reference conclusion |
|---|---|---|
| "The pure-algorithm recognition approach is feasible, measured accuracy can reach 100%" | `261004/experiment_report.md` section 7d.3: 60-frame multi-direction MediaPipe test, 60/60 detected | **A discrepancy that needs clarifying**: this 100% is the **detection rate** (face and iris detected), not the **angular accuracy**. Section 7d.3's conclusion 3 already recorded: "within the 60-frame center batch, the iris coordinates themselves show clear drift... the current data can only answer 'is detection stable,' it still cannot answer 'is the iris-coordinate → gaze-angle mapping accurate.'" If the teacher's understanding of "100% accuracy" includes angular accuracy, this conclusion currently has no data to support it — this needs to be proactively clarified at the next sync, to avoid expectations being pulled too high |
| "ESP32 cannot be made compatible with the eye camera (the notes originally wrote OB9281, likely a typo/transcription error for OV9281)" | `261016/esp32-hardware-decision-process.md`: the official ESP32 `esp32-camera` driver library supports OV2640/OV3660/OV5640/OV7725/NT99141, not OV9281; and physically, one ESP32-CAM board only has a single DVP camera interface, it cannot carry two cameras at once | Fully consistent, the teacher agreed with this judgment |
| "ESP32-CAM connects independently to the OLED + the eye camera runs an extension cable straight to the PC" | same document, Stage 1/2 architecture design | Fully consistent, the teacher agreed and adopted it as the initial prototype plan |
| "The pure-algorithm approach requires keeping the camera 8-10cm from the face" | the premise raised in this conversation for discussing "mount 1 (brim-mounted) / mount 2 (fold-flip glasses)": "MediaPipe needs a full-face input, meaning OV9281 needs some distance from the face" | Consistent, the teacher gave a specific number (8-10cm); prior discussion had stayed at a qualitative judgment |
| "Previously considered a hat-brim mount or fold-flip dual-purpose glasses" | Mount 1 (brim-mounted) and Mount 2 (fold-flip lens) independently proposed by the user in this conversation | The user's Mount 1/2 matches the description of what the teacher's meeting notes called "previously considered" |

## 2. New Decisions Brought by the Meeting Notes (Not Present in Prior Discussion)

These are new directions the teacher gave in the meeting that were not covered in prior discussion — not confirmations of existing results:

**Abandon the brim-mount/fold-flip plans, switch to a modular split**:
- Module A: lightweight glasses (does not integrate full-face recognition hardware)
- Module B: a spatial/environmental camera (independent of the glasses, handles full-face recognition)
- The two modules sync data via the cloud for distractor recognition; Module B is not required to be physically mounted on the wearer's head

This directly answers a question left unresolved in this conversation — no longer need to keep comparing "Mount 1 brim-mounted vs. Mount 2 fold-flip" to see which is better, because their shared problem (head-camera relative position drift, or the intermittent capture caused by flipping) is sidestepped under the modular split: Module B need not follow the head's movement, it can be a standalone device in a fixed scene.

Cost: sacrifices the "fully wearable, measure wherever you go" continuous-monitoring capability, moving closer to "a fixed-scene experimental prototype." This is consistent with the teacher's emphasis on "avoid over-focusing on technical details" and "keep the prototype simple and fast" — use the modular plan to first get the algorithm chain validated, leave the form-factor problem for later.

**Simplified prototype-testing suggestions**:
- Prioritize PC-side visualization testing (directly calling the algorithm to draw the gaze trajectory), don't rush to integrate hardware
- Avoid over-stacking technology, to prevent the project from turning into mere technology-stacking

## 3. After-Class Tasks (quoted verbatim, all offline/follow-up tasks for the user)

1. Once the long cable arrives, assemble the camera and the ESP32-CAM and glue them onto the glasses for testing
2. Make a paper model, photograph the process, and later use AI background removal/replacement on the photos
3. Continue advancing testing of the eye-tracking and distractor-recognition algorithms
4. Once experimental progress is complete, sync the test results and progress back to the advisor

Item 3 is consistent with the current direction of `261004/experiment_report.md` section 7d and can be picked up directly. Items 1 and 2 are new tasks not covered in this conversation, requiring the user to advance hardware arrival and model-making offline.

## 4. Open Items

- At the next sync with the teacher, proactively clarify that "100%" refers to the detection rate rather than angular accuracy, to avoid a mismatched expectation carrying into later decisions
- Confirm the concrete form and cloud data-sync method for the modular plan (Module A lightweight glasses + Module B spatial/environmental camera) — the meeting notes only gave a direction here, no concrete design
- `261004/experiment_report.md` section 7d.3's open item ③ (whether the main hardware's field of view supports full-face input) may no longer be a problem under the modular plan — because Module B is no longer constrained by the main glasses hardware's field-of-view design and can be selected independently; needs re-evaluating whether this open item still stands
