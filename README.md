# paper-ecg-explainer

Educational tool that reads a **scanned or photographed paper ECG**, checks the heart rhythm for signs of
**atrial fibrillation (AF)** and produces an HTML report that explains everything in plain language
(report language: Polish).

> **Not a medical device.** This is an educational/hobby project. It can be wrong and must not be used
> for diagnosis or treatment decisions. Always have an ECG interpreted by a physician.

## What it does

1. **Digitizes the printout.** Detects the red grid, straightens a skewed scan, measures the 1 mm grid
   pitch (25 mm/s, 10 mm/mV) and traces the black line of every lead, skipping lead labels and the
   calibration pulse.
2. **Finds heartbeats.** Detects QRS complexes by fusing the slope energy of all simultaneously
   recorded leads and measures RR intervals.
3. **Checks rhythm irregularity.** RR coefficient of variation, normalized RMSSD and the share of
   beat-to-beat changes above 10%.
4. **Looks for P waves.** Overlays the segments right before each QRS: repeatable P waves mean sinus
   rhythm, random segments suggest AF.
5. **Analyzes atrial activity.** Cancels the average QRST complex and computes the spectrum of the
   remaining signal: dominant frequency and organization index (fibrillation vs. flutter waves).
6. **Writes a plain-language report** with a glossary of ECG symbols, annotated charts on ECG-paper
   style grids and synthetic "normal vs. AF" examples for comparison.

## Usage

```bash
pip install -r requirements.txt
python ekg_analiza.py scan_limb_leads.webp scan_chest_leads.webp
```

By default the tool expects the common 3-row × 2-column printout (e.g. AsCARD):

| file   | left column   | right column     |
|--------|---------------|------------------|
| 1st    | I, II, III    | aVR, aVL, aVF    |
| 2nd    | V1, V2, V3    | V4, V5, V6       |

Other layouts can be named explicitly:

```bash
python ekg_analiza.py scan.jpg --odprowadzenia "I,II,III,aVR,aVL,aVF" -o report.html
```

The report (`raport_ekg.html`) is saved next to the first scan unless `-o` is given.

## Project layout

| file               | role                                                   |
|--------------------|--------------------------------------------------------|
| `ekg_analiza.py`   | command-line entry point                               |
| `digitalizacja.py` | image → signal (grid detection, deskew, line tracing)  |
| `analiza.py`       | QRS detection, RR irregularity, P waves, atrial spectrum |
| `wykresy.py`       | charts drawn on ECG-paper style grids                  |
| `raport.py`        | HTML report with plain-language explanations           |

## Limitations

- Only the few seconds printed on the paper are analyzed; AF thresholds are heuristics from literature,
  not clinically validated here.
- Digitization quality depends on the scan (folds, faint print, show-through stamps).
- It does not assess QRS morphology, ST segments, intervals or anything beyond rhythm.

Scans and reports are git-ignored on purpose: they contain personal medical data.
