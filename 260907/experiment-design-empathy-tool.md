# ADHD Project · Experiment Design (Empathy Tool Direction)

> Context: the project direction shifted from "efficiency tool" back to "empathy tool" (letting ADHD and non-ADHD people swap and experience each other's sensory situation). This document lays out the concrete design for two preparatory experiments referenced in the meeting notes: "multi-sensory quantification experiment" and "social-context identity-switch field research."

---

## 1. Direction change: adjusting the experiment goal

The original (efficiency-oriented) goal was "find the optimal boundary between distraction and focus, to support product intervention strategy with data."

After the shift (empathy-oriented), the goal becomes: **collect real, objective and subjective performance data from ADHD individuals under different sensory distractions, and compare it against a non-ADHD control group — this difference data becomes the raw material for a later visual/sensory translation device.** First nail down exactly what the experiential difference looks like, then decide how to translate that difference into an experience for the other group.

---

## 2. Experiment 1: Multi-sensory Quantification Experiment

### 2.1 Task design: why "tidy the desk" was dropped

"Tidy the desk" has a core problem under unsupervised conditions: **the definition of "done" is subjective and soft** (whether things are folded neatly, whether placement counts as correct — it cannot be judged objectively). In a mail-based experiment with no direct supervision, this task cannot be objectively verified.

**Replacement: Cancellation Task**

A classic paradigm from cognitive psychology for measuring attention/vigilance (e.g. the clinically used d2 test).

**Task format**: print a page of randomly arranged characters (e.g. a full page of letters) containing a fixed number of target characters (e.g. all "F"s and "E"s), and ask the subject to "cross out all target characters as fast as possible."

**Why this fits an unsupervised mail experiment**:
- The total count and positions of target characters are known in advance by the experimenter, so the returned sheet can be verified directly and objectively without on-site supervision
- Time can be recorded with a mechanical hourglass/timer shipped in the kit (avoiding phone-based timing, since the phone itself is used as the visual-distraction condition)
- A cognitive vigilance task is relatively unaffected by personal lifestyle habits (unlike a tidying task, which is skewed by "do you naturally like things tidy"), giving a purer distraction variable

**Details that must be controlled**:
- Each condition uses a sheet with different content but the same total character count, target frequency, and layout randomness, to avoid practice effects contaminating the distraction effect
- Sheet/envelope numbering must be randomized across subjects to avoid an order effect (e.g. "always doing the baseline condition first")

### 2.2 Subject grouping

- Group A: suspected/diagnosed ADHD subjects
- Group B: non-ADHD subjects (control)
- Both groups perform identical tasks and distraction conditions, to compute the difference

### 2.3 Multi-sensory comparison matrix (single → combined)

A 2×2×2 factorial design: visual (V), auditory (A), tactile (T), each "present/absent," 8 conditions total:

| Condition | Visual (V) | Auditory (A) | Tactile (T) | Description |
|---|---|---|---|---|
| 0 | — | — | — | Baseline (no distraction, mandatory, the comparison anchor) |
| 1 | ✓ | — | — | Visual only (phone playing a short video) |
| 2 | — | ✓ | — | Auditory only (distracting music) |
| 3 | — | — | ✓ | Tactile only (vibrating phone / plush fidget toy within reach) |
| 4 | ✓ | ✓ | — | Visual + auditory combined |
| 5 | ✓ | — | ✓ | Visual + tactile combined |
| 6 | — | ✓ | ✓ | Auditory + tactile combined |
| 7 | ✓ | ✓ | ✓ | All three combined |

**Reduced version** (if 8 conditions is too much load for a mail experiment): baseline + 3 single-sense conditions + 1 full-combination condition, 5 conditions total. This sacrifices the full interaction-effect analysis but can still answer the core "single vs. fully combined" question with a lower operational burden.

### 2.4 Data recorded uniformly per condition

**Objective data**:
- Total completion time (timer reading)
- Omission errors (target characters missed)
- Commission errors (wrong characters crossed out)

**Subjective data (added to serve the empathy-translation goal)**:
- Self-rated distraction intensity (1–5, filled in on the back of the sheet after the task)
- In-the-moment feeling after each distraction interruption (simple scale from "very hard to come back" to "very easy to come back")
- Open-ended short note: "What was going through your mind the moment you got interrupted?" (one sentence is enough)
- Physiological-feeling description (optional): heartbeat change, irritation/guilt, other subjective bodily sensations

### 2.5 Materials package

Builds on the "mailed rulebook + film camera" approach:
- Rulebook: explains the steps for each of the 8 (or 5) conditions, and which distraction tool goes with which envelope
- Film camera: photos only at a few key moments (e.g. "the moment of first distraction," "the moment of completion") to control shooting cost, while the photos themselves mark key moments
- New "feeling record card": at each photographed key moment, additionally write one or two words describing the feeling at that instant — these raw words can themselves become language material for the later translation device
- Mechanical hourglass/timer: replaces phone timing, to avoid conflicting with the visual-distraction condition

### 2.6 Core value of the data analysis

The factorial design can test whether "the sum of single-sense distraction effects" equals "the actual effect of the combined condition" — if single visual/auditory distraction each cause about a 10% efficiency drop, but the three-sense combination causes a 40% crash (rather than the expected ~30%), that indicates a **super-additive amplification effect**. This data can directly validate or challenge the core theory that "multi-dimensional completion cannot simply be summed," making it evidentially substantive material for the portfolio.

---

## 3. Experiment 2: Social-Context Identity-Switch Field Research

Per the meeting notes, 3–5 cases should be collected, organized around three specific theoretical anchors rather than aimless gathering:

### 3.1 Spatial dimension · Liminal Space

Proposed by anthropologist Arnold van Gennep in *The Rites of Passage* (1909), describing the three-stage structure in rituals: "separation from old state → transitional phase → entry into new state." The middle "liminal" phase is considered the stage where identity is most unsettled and most reshapeable. This framework can be used to analyze the spatial difference between a classroom and a counseling room, or architectural cases of "liminal spaces" such as corridors and waiting rooms.

### 3.2 Clothing dimension · Enclothed Cognition

Adam & Galinsky's classic 2012 experiment: subjects wearing a white coat showed significantly fewer errors (roughly halved) on a Stroop attention test — but **the key precondition was that subjects believed it was "a doctor's coat"**; if told it was "a painter's smock," the effect disappeared. This shows that what triggers an identity switch is not just "what you wear" but also "how you understand what you're wearing," directly informing the ritual design of the device (form + assigned meaning).

### 3.3 Product/online-offline dimension · Fake Commute

Remote workers, having lost the physical transition of commuting, struggle to complete the "clocking off" psychological switch, and so proactively invent ritualistic substitutes such as "put on headphones, walk a loop, then come home." This proves that **an identity switch requires a physical/temporal buffer zone, and once technology compresses it away, people instinctively invent a ritual to fill the gap** — structurally identical to a product's logic of "artificially triggering an identity switch."

---

## 4. Reference Links

**Liminal Space**
- Meridian University, *Liminal Space Meaning: The Psychology of In-Between*: https://meridianuniversity.edu/content/liminal-space-meaning-the-psychology-of-in-between
- First In Architecture, *What is Liminal Space?*: https://www.firstinarchitecture.co.uk/what-is-liminal-space/
- ResearchGate, *Looking for Liminality in Architectural Space*: https://www.researchgate.net/publication/326675016_Looking_for_Liminality_in_Architectural_Space
- Satyori Glossary, *Liminal Space*: https://satyori.com/glossary/liminal-space/

**Enclothed Cognition**
- Wikipedia, *Enclothed cognition*: https://en.wikipedia.org/wiki/Enclothed_cognition
- Original paper PDF (Adam & Galinsky, 2012): https://utstat.utoronto.ca/reid/sta2201s/2012/labcoatarticle.pdf
- BPS Research Digest analysis (with concrete experimental data): https://www.bps.org.uk/research-digest/introducing-enclothed-cognition-how-what-we-wear-affects-how-we-think
- ScienceDirect original abstract: https://www.sciencedirect.com/science/article/abs/pii/S0022103112000200

**Fake Commute**
- Washington Post, *Fake commute: A way to carve out transition time around work*: https://www.washingtonpost.com/lifestyle/wellness/fake-commute-home-work-transition-/2021/02/22/49f79d56-6cb7-11eb-9f80-3d7646ce1bc0_story.html
- Fast Company, *Want to be more productive? Try a fake commute*: https://www.fastcompany.com/90703258/want-to-be-more-productive-try-a-fake-commute
- Forbes, *How Fake Commuting Can Improve Your Remote Workday*: https://www.forbes.com/sites/ashiraprossack1/2021/01/30/how-fake-commuting-can-improve-your-remote-workday/365610

---

## 5. Open Decisions

1. Full 8-condition factorial matrix vs. the 5-condition reduced version — depends on recruitable sample size and mail turnaround time
2. Specific character design for the cancellation task (target character type, matrix density) needs small-scale pretesting to calibrate difficulty, avoiding ceiling or floor effects
3. Recruitment channels and sample size for the ADHD group and the control group still need to be settled
4. For the identity-switch field research's 3–5 cases, beyond the three theoretical anchors above, should case selection also draw on the Masking phenomenon?

---

*Note: this document consolidates the latest version of the experiment design discussion; the earlier "tidy the desk" task plan and the purely efficiency-oriented experiment goal have been superseded by this document's approach.*
