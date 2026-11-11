# Auditory Stimulus Quantification Experiment Plan (Pre-Examination Reference)

> Purpose: provide quantification dimensions, experiment design, and literature support for the auditory pre-test in the "task initiation" project.
> Core logic: **people first, tools second** — Step 1 uses diverse real audio to elicit subjective + physiological responses from people, sorting clips into "effective/ineffective" groups; Step 2 then uses psychoacoustic tools to work backward and find which parameter actually separates the two groups; Step 3 (optional) runs a controlled validation experiment based on Step 2's finding. Tools do not pre-shape the audio design — they only come in after the sorting is done.

---

## 1. Overall framework for quantifying auditory stimuli

**Acoustic / psychoacoustic objective parameters** (describe the sound itself; tools are only used to compute these in Step 2): frequency (Hz), tempo/BPM, sound pressure level (dB), loudness, sharpness, roughness, fluctuation strength. This set comes from Zwicker & Fastl's psychoacoustic theory.

**Cognitive / behavioral dependent variables** (measured directly on people in Step 1): reaction time and its variability (RT variability/SD) — one of the most sensitive indicators in sustained-attention tests, especially sensitive for ADHD; omission/commission errors — auditory omission error is one of the most reliable variables distinguishing the ADHD group from controls.

---

## 2. Step 1: Diverse Audio Library + Subjective Scale + Physiological Pre-screening

**Core principle**: the audio source pool should be "arbitrary" and broad in coverage — it must not be a precisely synthesized, controlled combination, since that would mean the tool has already pre-computed the answer. The literature is only used to decide which dimensions the candidate pool should cover at both extremes; each specific clip is drawn from real-world, diverse material. **The one exception is "loudness"** — loudness is pure amplitude scaling and does not change the frequency/rhythmic content of the audio, so it must be controlled by adjusting the volume of the *same* clip rather than searching for different clips, so that loudness is the only variable changing between conditions.

### 2.1 Coverage of the candidate audio library — theoretical basis

- Patterson, R. D. (1982). *Guidelines for auditory warning systems on civil aircraft*: the perceived-safe pitch range for warning sounds is 150–1000 Hz — the candidate pool should at least cover clearly low (a few hundred Hz) and clearly high (over a thousand Hz) audio
- Haas & Edworthy (1996): frequency, SPL, and pulse interval all affect urgency — this study itself also fixed the base timbre and only varied SPL to represent loudness differences, consistent with this plan's loudness-control approach
- Milliman (1982) / Brodsky (2002) tempo classification: slow < 72 BPM, fast > 94–140 BPM
- Bradley & Lang (2007), *IADS-2*: the valence/arousal distribution of emotional sounds is sparse at the extremes and dense in the middle — selection should deliberately seek out "extreme" sounds
- Gaver, W. W. (1986), *Auditory Icons*: distinguishes Auditory Icons (natural environmental sounds with semantic association) from Earcons (abstract synthesized tones) — Step 1 needs both types, since it is not yet known whether an "effective" sound works through semantic association or through pure acoustic parameters

### 2.2 Candidate audio list — 4 content groups × 2 loudness versions + vocal control group

First assemble the **frequency × tempo** 2×2 combinations (4 real audio clips with different content), then make a loud and a quiet version of each, naturally yielding 8 clips; the vocal group is handled separately and does not participate in the loudness-control logic (it measures semantic/tone differences instead).

| Content group | Frequency | Tempo | What to look for (keywords/source suggestions) |
|---|---|---|---|
| C1 | Low | Slow | Distant thunder (search Freesound for "distant thunder rumble") or slow ambient music |
| C2 | Low | Fast | Fast, bass-heavy music loop (filter on Tunebat for BPM > 110 with prominent bass) |
| C3 | High | Slow | Wind chimes (search Freesound for "wind chimes") or widely spaced single bird calls |
| C4 | High | Fast | Dense flock bird chatter (search Freesound for "bird flock chirping") or continuous notification tones |

**Make two loudness versions of each clip in Audacity** ("Effect > Amplify" to adjust gain):

| ID | Content | Loudness |
|---|---|---|
| C1-loud | C1 | ~75 dB |
| C1-quiet | C1 | ~55 dB |
| C2-loud | C2 | ~75 dB |
| C2-quiet | C2 | ~55 dB |
| C3-loud | C3 | ~75 dB |
| C3-quiet | C3 | ~55 dB |
| C4-loud | C4 | ~75 dB |
| C4-quiet | C4 | ~55 dB |

**Vocal control group** (independent of the loudness-control logic above):

| ID | Content |
|---|---|
| V1 | Self-recorded "Time to get up" — calm tone |
| V2 | Self-recorded, same sentence — urgent, rushed tone |

**10 clips total** (8 content × loudness combinations + 2 vocal), each trimmed to the most representative 6–10 second segment.

### 2.3 Ready-made audio sources

**International free sound-effect libraries**:
- **Freesound.org** — the largest CC-licensed sound library, register and search by keyword to download directly; note the distinction between CC0 (free use) and CC-BY (attribution required)
- **Zapsplat** — free after registration, with "notification," "alarm," "alert" categories
- **Mixkit** — no registration needed, free commercial-use sound library
- **BBC Sound Effects Archive** — the BBC's official free sound library, high-quality natural/ambient sounds, free for personal non-commercial use

**Chinese-language sound libraries**:
- **Ear0 (ear0.com)** — a Chinese sound-effect site focused on natural/ambient and everyday sounds
- **Aigei (aigei.com)** — a general-purpose asset site; some resources require attention to copyright/membership restrictions

**Standardized emotional sound libraries (optional, for validity calibration)**:
- **IADS-2** (Bradley & Lang, 2007) — a sound library already annotated with valence/arousal scores; available on application to the University of Florida NIMH Center for the Study of Emotion and Attention

**BPM lookup tools** (web-based, no download needed):
- **Tunebat.com** — open the site and search by song name for BPM, or upload an audio file for automatic analysis ("Song Key & BPM Finder"); works on both mobile and desktop browsers
- **SongBPM.com** — another web tool, search by song name
- For offline batch analysis, search the App Store for **"BPM Finder"** (supports batch analysis of audio files)

**Vocal material**: no external site needed — record with a phone voice-recording app.

**Copyright note**: check the licensing terms of each platform after downloading. Academic/classroom use is lower-risk, but if the portfolio will be publicly displayed or entered into a competition, prefer CC0 or attributed material.

### 2.4 Audio preprocessing standard

1. **Unified format**: convert everything to WAV, 44.1 kHz sample rate (Audacity export is sufficient)
2. **Duration trimming**: trim each clip to the most representative 6–10 second segment
3. **Loudness control**: use Audacity's "Amplify" function to bring each content group to ~55 dB and ~75 dB versions (the one step in this plan that requires actively adjusting a parameter, used to strictly control this single variable)

### 2.5 Physiological measurement plan (ECG+ 30-second protocol)

Use the Apple Watch S10's ECG feature plus the **ECG+** app throughout; each clip is measured once, giving both HR and HRV in one pass:

- Before the experiment, take one **resting baseline** measurement (30 seconds, no audio playing) as this subject's personal baseline
- For each candidate clip, trigger ECG recording in sync: hold down the crown with one hand to start recording, and start audio playback with the other hand at the same time (manual sync, 1–2 second error is acceptable — ECG cannot be triggered automatically via Shortcuts)
- **Audio duration is handled by type**:
  - Music/ambient sounds: can loop to fill the full 30 seconds, directly using the overall RMSSD/HR values from the ECG+ report
  - Short warning/notification/vocal types: keep the original 6–10 second duration, do not loop-stretch them (to avoid distorting the natural listening experience); within the 30-second recording, the first part corresponds to the "stimulus period" and the latter part to the "recovery period" — focus qualitatively on how the R-R interval time series in the ECG+ report fluctuates before vs. after the stimulus
- **Data recorded each time**: HRV (rMSSD), mean HR, mean RR — given directly by the ECG+ report, no extra computation needed
- **Between-group comparison uses ΔHRV/ΔHR** (this trial's value minus personal baseline), to cancel out individual differences in resting heart rate

**Material log template**:

| Subject ID | Audio ID | Type | HRV (rMSSD) | Mean HR | Mean RR |
|---|---|---|---|---|---|
| P01 | baseline | - | | | |
| P01 | C1-loud | natural sound - low-slow - loud | | | |
| P01 | C1-quiet | natural sound - low-slow - quiet | | | |
| P01 | V1 | vocal - calm | | | |

### 2.6 Specific questionnaire items

Immediately after each clip finishes, rate on a 7-point Likert scale (1 = strongly disagree, 7 = strongly agree):

- **Arousal**: "This sound makes me feel alert/activated"
- **Urgency** (core dimension, corresponds to task initiation): "This sound makes me feel I need to do something right now"
- **Annoyance**: "This sound feels harsh/unpleasant to me"
- **Behavioral-intent check item** (binary choice): "If this were a task reminder sound, would you immediately drop what you're doing to deal with it?" [yes/no]

The three-dimension split follows the Hellier & Edworthy line of research, which treats "perceived urgency" as an independent third dimension separate from pure emotional valence/arousal.

### 2.7 Sample size and procedure

- **Sample size**: 20–25 people
- **Design type**: within-subjects, every participant hears all 10 clips
- **Order control**: Latin square or fully randomized playback order
- **Single-session duration**: each clip needs about "30s ECG + ~10s playback + 20s questionnaire," so 10 clips takes roughly 20–25 minutes per person

### 2.8 Screening criteria (four quadrants)

| | Strong physiological response | Weak physiological response |
|---|---|---|
| **High subjective rating** | Strongly effective candidate | Needs confirmation (possibly social-desirability effect) |
| **Low subjective rating** | Potential subliminal-effective candidate (highest design value) | Ineffective, excluded |

After Step 1, we get an "effective audio group" and an "ineffective audio group" — at this point we still don't know which parameter caused the split; that is exactly what Step 2 solves.

---

## 3. Step 2: Using Tools to Work Backward — Which Parameter Split the Two Groups?

**Tools appear for the first time here, and only analyze the audio Step 1 actually sorted — never any synthetically generated audio.**

### 3.1 Open-source tools

**Basic acoustic parameters (`librosa`)**: tempo/BPM via `beat.beat_track()`; fundamental frequency via `pyin()`; spectral centroid via `spectral_centroid()`; RMS via `feature.rms()`

**Psychoacoustic parameters (`MOSQITO`)**:
- Loudness (ISO 532-1): `mosqito.sq_metrics.loudness_zwst`
- Sharpness (DIN 45692): `mosqito.sq_metrics.sharpness_din_st`
- Roughness and fluctuation strength: corresponding functions available in the library
- Install: `pip install mosqito --break-system-packages`

### 3.2 Analysis workflow

1. Run every clip in the "effective group" and "ineffective group" through librosa + MOSQITO to get a complete parameter table for each clip
2. Compare between groups (t-tests, or scatter plots of "frequency × tempo," "loudness × roughness" to see if the groups separate)
3. Identify which parameter(s) show the most significant between-group difference — this conclusion grows out of the data, it is not assumed in advance

---

## 4. Step 3 (Optional): Controlled Validation Based on Step 2's Finding

Only worth doing once Step 2 has told you "which parameter matters" — use synthetic audio to run a clean causal validation, eliminating the semantics, timbre, and other confounds mixed into the real audio in Step 1.

Suppose Step 2 finds "fundamental frequency" and "tempo" are the key discriminating variables — run a 2×2 synthetic audio factorial experiment:

| Condition | Fundamental frequency (set from Step 2's measured high/low group means) | Tempo (same) |
|---|---|---|
| B1 | Low | Slow |
| B2 | Low | Fast |
| B3 | High | Slow |
| B4 | High | Fast |

Production method: use Audacity or Python to synthesize sine/square waves, hold all other variables fixed, and manipulate only these two parameters already proven important by Step 2.

This is the step where Patterson (1982)'s pulse design specification (single pulse 300–500 ms, looped into a 6–10 second clip) finally becomes useful, along with Gaver (1986)'s recommendation that Earcons should exclude semantic interference, and Hellier et al. (2002)'s finding that semantics independently affects urgency judgment.

---

## 5. Background on the Physiological-Metric Choice (Writing Reference)

- Skin conductance (EDA/GSR) was considered, but required extra hardware (a Grove-GSR sensor + Arduino development) and was judged too much workload, so it was dropped
- The Apple Watch's background HRV algorithm (based on the optical heart-rate sensor) was considered, but this data is the result of Apple's closed-source black-box algorithm firing sporadically, and third-party apps cannot programmatically retrieve raw beat-by-beat data — the sampling density is insufficient to correspond to each individual audio clip, so it was dropped; and Workout mode only makes heart rate continuously sampled, not HRV — the two work through different mechanisms
- Final choice: the **ECG feature** — because it uses electrodes to directly measure the heart's electrical signal (512 Hz sampling), and the raw waveform data can be read via HealthKit's `HKElectrocardiogram` interface, letting a third-party app (such as ECG+) automatically detect R-waves and compute genuine RMSSD — this path is technically real and feasible, at the cost of each measurement requiring a manual trigger + 30 seconds of stillness, with no automatic continuous background monitoring
- Brouwer et al. (2013): heart rate more strongly reflects valence (pleasantness), while heart-rate variability (HRV) more closely tracks arousal — this is the rationale for adding HRV rather than relying on heart rate alone
- An accelerometer/gyroscope to capture the precise timing of a wrist "initiation" motion was considered, but required extra watchOS development and was judged too much workload, so it was dropped; blood oxygen, cardio fitness (VO2 Max), recovery heart rate and similar metrics were not adopted due to weak relevance to the research question or insufficient granularity to correspond to a single audio clip

---

## 6. Literature

### ADHD and auditory attention

1. *Specific Rhythm Auditory Stimulation for Attention: A Pilot Randomized Controlled Trial*. https://www.cpn.or.kr/journal/view.html?doi=10.9758%2Fcpn.24.1247
2. Simões, E. N., Carvalho, A. L. N., & Schmidt, S. L. (2021). *The Role of Visual and Auditory Stimuli in Continuous Performance Tests: Differential Effects on Children With ADHD*. Journal of Attention Disorders. https://doi.org/10.1177/1087054718769149
3. *Interval Timing in Children: Effects of Auditory and Visual Pacing Stimuli and Relationships with Reading and Attention Variables*. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3416773/
4. *Effects of auditory white noise stimulation on sustained attention and response time variability*. Frontiers in Psychology, 2023. https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1301771/full
5. *Attention deficits revealed by passive auditory change detection for pure tones and lexical tones in ADHD children*. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4549566/
6. *Sensory–Cognitive Profiles in Children with ADHD: Exploring Perceptual–Motor, Auditory, and Oculomotor Function*. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12189118/
7. Virginia Tech dissertation (rhythmic entrainment and ADHD, Flanker task + EEG experiment). https://vtechworks.lib.vt.edu/server/api/core/bitstreams/329eedd7-1bd0-45e5-9ece-cb3192a78ffe/content
8. *Auditory time thresholds in the range of milliseconds but not seconds are impaired in ADHD*. Scientific Reports, 2022. https://www.nature.com/articles/s41598-022-05425-2

### Psychoacoustic parameters and warning-sound design

9. *Designing effective warning sounds: psychoacoustical considerations*. TU Dresden, INTER-NOISE 2024. https://fis.tu-dresden.de/portal/en/publications/designing-effective-warning-sounds-psychoacoustical-considerations
10. *Concurrent categorical scaling of sound quality measures (CCSM)*. Fraunhofer, 2025. https://publica.fraunhofer.de/handle/publica/503741
11. *Sound quality evaluation of air-conditioning sounds in a vehicle using psychoacoustic parameters*. JASA, 2008. https://labs.sonicfield.org/library/sound-quality-evaluation-of-air-conditioning-sounds-in-a-vehicle-using-psychoaco
12. *The tram bonus*. Archives of Acoustics, 2014. https://doaj.org/article/e81d7a602df44800bd20501f0fea3e63
13. *Psychoacoustic Annoyance (Zwicker & Fastl)* methodology overview. https://metricgate.com/docs/psychoacoustic-annoyance/
14. Patterson, R. D. (1982). *Guidelines for auditory warning systems on civil aircraft*. Civil Aviation Authority Paper 82017. https://www.semanticscholar.org/paper/Guidelines-for-auditory-warning-systems-on-civil-Patterson/cd93db7b798ce1b6fcdb0fc9762b5f9a6f154c65
15. Hellier, E. J., Edworthy, J., & Dennis, I. (1993). *Improving auditory warning design: Quantifying and predicting the effects of different warning parameters on perceived urgency*. Human Factors, 35(4), 693-706. https://doi.org/10.1177/001872089303500408
16. Haas, E. C., & Edworthy, J. (1996). *Measuring Perceived Urgency to Create Safe Auditory Warnings*. Proceedings of the Human Factors and Ergonomics Society Annual Meeting. https://doi.org/10.1518/154193129604001611
17. Edworthy, J., Loxley, S., & Dennis, I. (1991). *Improving auditory warning design: Relationship between warning sound parameters and perceived urgency*. Human Factors, 33, 205-231. https://doi.org/10.1177/001872089103300206
18. Hellier, E., Edworthy, J., Weedon, B., Walters, K., & Adams, A. (2002). *The Perceived Urgency of Speech Warnings: Semantics versus Acoustics*. Human Factors. https://journals.sagepub.com/doi/10.1518/0018720024494810

### Emotional sound libraries and physiological metrics

19. Bradley, M. M., & Lang, P. J. (2007). *International Affective Digitized Sounds (IADS-2): Affective ratings of sounds and instruction manual*. University of Florida. https://link.springer.com/article/10.3758/BRM.40.1.315
20. Brouwer, A. M., Van Wouwe, N., Mühl, C., Van Erp, J., & Toet, A. (2013). *Perceiving blocks of emotional pictures and sounds: effects on physiological variables*. Frontiers in Human Neuroscience, 7, 295. https://pmc.ncbi.nlm.nih.gov/articles/PMC3689025
21. *Researchers Quantify Intensity of Emotional Response to Sound, Images and Touch Through Skin Conductance*. NYU Engineering, 2024. https://engineering.nyu.edu/news/researchers-quantify-intensity-emotional-response-sound-images-and-touch-through-skin

### Music tempo/BPM and arousal

22. Milliman, R. E. (1982). *Using background music to affect the behavior of supermarket shoppers*. Journal of Marketing.
23. Brodsky, W. (2002). *The effects of music tempo on simulated driving performance and vehicular control*. Transportation Research Part F.
24. Edworthy, J., & Waring, H. (2006/2010). Research on music tempo's relationship with heart rate, blood pressure, and anxiety level (fast tempo 120-130 BPM raises anxiety/heart rate/blood pressure; slow tempo 50-60 BPM lowers them).

### Sound type and semantics

25. Gaver, W. W. (1986). *Auditory Icons: Using Sound in Computer Interfaces*. Human-Computer Interaction, 2(2), 167-177. https://doi.org/10.1207/s15327051hci0202_3
