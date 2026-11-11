# ADHD Attention-Translation Glasses — Experiment Log

![status](https://img.shields.io/badge/status-feasibility_prototype-blue)
![best_pupil_accuracy](https://img.shields.io/badge/best_pupil_detection_accuracy-86.9%25_(no_IR)-brightgreen)
![camera_routes](https://img.shields.io/badge/camera_routes_tested-2-orange)
![detector_approaches](https://img.shields.io/badge/detector_approaches_compared-4-orange)
![platform](https://img.shields.io/badge/platform-ESP32%20%7C%20Windows%20%7C%20PyTorch-lightgrey)
![license](https://img.shields.io/badge/license-MIT-green)

**A complete experimental trail for a wearable "selective visual intervention" prototype for ADHD** — from the first Edge AI object-recognition attempts, through eye-tracking camera selection and pupil-detection algorithm comparisons, to PCB design and the first real-data run of the PC-direct-control pipeline.

---

## What this is

ADHD and non-ADHD individuals may assign completely different attention priorities to information in the same real-world scene. The original concept: build a pair of glasses that recognizes "distractors" in the wearer's field of view in real time, and selectively suppresses them visually (pixelation/blur/occlusion) while enhancing what's actually relevant — in effect, letting the same real scene present "different visual worlds" to different users.

This concept was repeatedly revised by experimental results as the project progressed: from a "trained object classifier" to "open-vocabulary detection," from "recognizing objects" to "recognizing the gaze point," from a "Raspberry Pi all-in-one wearable" to a "PC-direct-control desktop prototype," from "OV9281 + IR fill light" to "GC0308 + deep-learning pupil segmentation." Every pivot is backed by concrete experimental data, documented in the files below.

**This repository is a process log, not a product showcase**: what was tested at each step, how, what the program reported vs. what manual review confirmed, and why a given route was abandoned are all kept honest — including failures and overturned conclusions. That self-correcting methodology, reused throughout the technical trail, is the core value this repository preserves.

---

## Key findings so far

1. **Pupil detection: the deep-learning approach substantially outperforms classical thresholding, and needs no active IR illumination at all.**
   - Otsu threshold + circularity filtering (classical method): true success rate 0/20 (0%) with no IR; 22/81 (27.2%, fair frames only) with 850nm IR fill light added.
   - EllSeg (a PyTorch deep-learning segmentation model): **no IR fill light needed at all** — 13/15 (86.7%, fair frames) on static images after manual review, 12/14 (85.7%) on an independent continuous-video re-test — highly consistent results.
   - See [`261004/experiment_report.md`](261004/experiment_report.md) Sections 6, 7f, 7g.

2. **Camera selection: GC0308 (a close-range eye-tracking module) paired with EllSeg can replace the bulkier OV9281.**
   - With the classical algorithm, GC0308's bottleneck was sensor granular noise (0% across three attempts); switching to EllSeg, static-image review reached 53/61 (86.9%), and after rigid mounting to the frame, continuous-video fair-frame accuracy reached 100% (24/24).
   - See Section 7i.

3. **Every single "100% success" reported by a program was overturned or revised down by manual visual review.** This is the methodology running through every experimental stage: a circularity score passing threshold does not mean the fit actually landed on the pupil — annotated images must be manually checked, and when needed, "fair test frames" must be separated from "unfair test frames" (eyes closed/occluded/out of focus). This rule caught two false positives in Stage 6, and a statistical-basis pitfall in Sections 7a/7i.

4. **The hardware form factor was overturned more than once: the Raspberry Pi all-in-one wearable route has been abandoned; the current stage accepts a "USB-tethered-to-PC desktop prototype" as the endpoint, no longer pursuing true wearability.** See the update note at the top of [`261010/dual-camera-glasses-roadmap.md`](261010/dual-camera-glasses-roadmap.md) and [`261014/`](261014/).

---

## Technical roadmap (chronological)

| Stage | Docs | Core content | Status |
|---|---|---|---|
| Concept design | [`260912/`](260912/vision-experiment-mindmap.md) | Full concept mindmap for the perspective-transformation system: Edge AI → open-world vision → Relevance Engine → visual transformation | ✅ Complete (concept design) |
| Edge AI baseline | [`260918/`](260918/) [`260919/`](260919/) | First ESP32-CAM + Edge Impulse closed-loop object-recognition attempt | ✅ Complete, exposed closed-set recognition limits |
| ESP32 on-device detection | [`261003/`](261003/) | ESP32-CAM + OLED local inference + display firmware | ✅ Complete |
| **Eye-tracking feasibility validation (core)** | [`261004/experiment_report.md`](261004/experiment_report.md) | Full comparison of two camera routes (OV9281/GC0308) and four detection approaches (Otsu/starburst/MediaPipe/EllSeg), including the visual-review methodology | ✅ Main line validated, details ongoing |
| All-in-one wearable route | [`261010/`](261010/dual-camera-glasses-roadmap.md) | Pi Zero 2 W design | ❌ Deprecated (WiFi issue never solved), kept as historical record |
| PC-direct-control route | [`261014/`](261014/) | Feasibility analysis of dropping the Pi, PC as the sole compute unit | ✅ Current main line |
| ESP32 hardware selection | [`261016/`](261016/) | ESP32-CAM interface limits, OV9281 package-type investigation | ✅ Complete |
| Advisor meeting cross-reference | [`261017/`](261017/meeting-notes-cross-reference.md) | Cross-referencing measured results against advisor feedback, the modular-split decision | ✅ Complete |
| Industrial design renders | [`261021/`](261021/) | Glasses industrial-design renders | ✅ Complete |
| ESP32CAM+OLED integration | [`261022/`](261022/README.md) | WiFi streaming + OLED occlusion-display firmware, fusion-logic PoC | ✅ Complete |
| GC0308 miniaturization validation | [`261029/`](261029/) | GC0308 + EllSeg re-test (static images + continuous video + before/after fixed mounting) | ✅ Complete |
| Phase 1 full-chain integration | [`261030/README.md`](261030/README.md) | First end-to-end run with real data, real pupil coordinates → OLED coordinates | ✅ Complete |
| Module A PCB design | [`261106/`](261106/) | Glasses-body PCB plan (wired version + wireless upgrade path) | 🔶 Plan stage, not yet fabricated |
| Auditory stimulus experiment | [`260924/`](260924/) | Pre-test experiment design for the task-initiation project | 🔶 Design finalized, awaiting subject recruitment |
| Empathy-tool multi-sensory experiment | [`260907/`](260907/) | Cancellation task + 2×2×2 multi-sensory distraction matrix design | 🔶 Materials designed, awaiting execution |

---

## Repository structure

This repository is organized by the **original course date folders** (e.g. `261004`, `261010`) — the actual directory structure used during the experiments — so the cross-references inside the documents (e.g. "see `261004/experiment_report.md` Section 7i") remain valid without rewriting.

```
260907/   empathy-tool-direction multi-sensory experiment design
260912/   vision-system concept mindmap
260918/   ESP32-CAM official example firmware (used for the Edge AI baseline)
260919/   early ESP32-CAM object-recognition firmware
260924/   auditory stimulus quantification experiment plan (final version)
261003/   ESP32-CAM on-device object detection + OLED display firmware
261004/   [CORE] all eye-tracking feasibility validation code, data, and the experiment report
261010/   Pi Zero 2 W all-in-one plan (deprecated, kept as historical record)
261014/   PC-direct-control feasibility analysis (current main line)
261016/   ESP32/OV9281 hardware-selection investigation
261017/   advisor meeting notes cross-reference
261021/   glasses industrial-design renders
261022/   ESP32CAM WiFi streaming + OLED occlusion firmware and integration scripts
261029/   GC0308 miniaturization validation scripts
261030/   Phase 1 full-chain real-data integration (calibration + fusion main program)
261106/   Module A (glasses body) PCB design plan
```

---

## Reproducing this

Most Python scripts depend on `opencv-python`, `numpy`, and `torch` (for EllSeg inference — the CPU build is sufficient). EllSeg's own code and pre-trained weights are not included in this repository (third-party repo, large file size) — see [`261004/experiment_report.md`](261004/experiment_report.md) Section 7f.1 for how to obtain them. `261030/phase1_fusion.py` depends on `yolov8n.pt`, Ultralytics' official pre-trained weights — download it yourself before running (a standard COCO-pretrained model, freely available online).

Firmware (`.ino` files) targets the Arduino IDE + ESP32 board package; flashing-environment requirements are documented inside each firmware's own folder.

---

## License

MIT — see [`LICENSE`](LICENSE).

EllSeg, MediaPipe, and YOLOv8 are third-party tools referenced by this project under their own respective licenses; none of their code or weights are redistributed in this repository.

---

*This repository was compiled from the author's course experiment notes, honestly preserving the full process of overturned conclusions, re-tests, and methodology corrections.*
