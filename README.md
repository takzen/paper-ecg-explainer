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
6. **Opens an interactive ECG viewer** (`przegladarka_ekg.html`, single offline HTML file):
   all 12 leads redrawn on an ECG-paper grid with anomalies marked directly on the trace:
   irregular RR intervals, very short intervals, missing P-wave zones and individual f waves.
   Hover any marker for a tooltip, click it (or an entry in the anomaly list) for a plain-language
   explanation and "what normal looks like", zoom in, step through anomalies with ← / →, and overlay
   the original scan to verify the digitization.
7. **Writes a plain-language report** (`raport_ekg.html`) with a glossary of ECG symbols, annotated
   charts and synthetic "normal vs. AF" examples for comparison.

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
python ekg_analiza.py scan.jpg --odprowadzenia "I,II,III,aVR,aVL,aVF" -o results_folder
```

Both HTML files are saved next to the first scan (or into the folder given with `-o`) and the viewer
opens in the browser automatically (`--nie-otwieraj` disables that).

## Project layout

| file               | role                                                   |
|--------------------|--------------------------------------------------------|
| `ekg_analiza.py`   | command-line entry point                               |
| `digitalizacja.py` | image → signal (grid detection, deskew, line tracing)  |
| `analiza.py`       | QRS detection, RR irregularity, P waves, atrial spectrum |
| `wykresy.py`       | charts drawn on ECG-paper style grids                  |
| `raport.py`        | HTML report with plain-language explanations           |
| `przegladarka.py`  | builds the interactive viewer from `przegladarka.html` |

## Limitations

- Only the few seconds printed on the paper are analyzed; AF thresholds are heuristics from literature,
  not clinically validated here.
- Digitization quality depends on the scan (folds, faint print, show-through stamps).
- It does not assess QRS morphology, ST segments, intervals or anything beyond rhythm.

Scans and reports are git-ignored on purpose: they contain personal medical data.
