# paper-ecg-explainer

**Turn a scanned or photographed paper ECG into an interactive, plain-language explanation of the heart rhythm, in English or Polish.**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![uv](https://img.shields.io/badge/managed%20with-uv-6340ac)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-educational%20prototype-orange)
![Not a medical device](https://img.shields.io/badge/NOT%20a%20medical%20device-red)

> [!CAUTION]
> **Educational project only. This is NOT a medical device and NOT a diagnostic tool.**
>
> - It has not been clinically validated and can be wrong, both by missing a problem and by flagging one that is not there.
> - Do **not** use it to diagnose, treat, or decide anything about anyone's health.
> - Always have an ECG interpreted by a qualified physician. In an emergency (chest pain, shortness of breath,
>   fainting, very fast heartbeat) call your local emergency number (112 in the EU).
>
> **PL:** Projekt wyłącznie edukacyjny. **To nie jest wyrób medyczny ani narzędzie diagnostyczne.** Może się mylić.
> Nie używaj go do stawiania diagnozy ani podejmowania decyzji o leczeniu. EKG zawsze ocenia lekarz.
> W nagłym wypadku dzwoń pod 112.

![Interactive ECG viewer on a fictional demo recording](docs/viewer.png)
<sub>Screenshot generated from a **fictional, synthetic** ECG (see [`demo/`](demo)), not from a real patient.
Polish version: [`docs/viewer_pl.png`](docs/viewer_pl.png).</sub>

## Why

ECG printouts are hard to read if you are not a doctor: a red grid, spikes, cryptic labels like *aVR* or *V1*.
This project started from a simple wish to understand what such a chart actually shows. The first working
version was built in about 30 minutes with [Claude Code](https://claude.com/claude-code).

## What it does

1. **Digitizes the paper printout:** detects the red grid, straightens a skewed scan, measures the 1 mm pitch
   (25 mm/s, 10 mm/mV) and traces the line of every lead, skipping labels and the calibration pulse.
2. **Finds heartbeats:** detects QRS complexes by fusing the slope energy of all leads recorded at the same time.
3. **Looks for rhythm anomalies:**
   - irregular RR intervals (sudden changes from one beat to the next),
   - very short intervals (rate above 120/min) and long pauses,
   - missing repeatable P waves before the beats,
   - fibrillatory "f" waves between the beats (QRST cancellation + spectrum: dominant frequency and organization index).
4. **Opens an interactive viewer** (`ecg_viewer.html`, one offline HTML file):
   - **EN / PL switch** that changes the whole interface instantly,
   - all 12 leads redrawn on an ECG-paper grid with the anomalies marked on the trace,
   - hover for a tooltip, click for a plain-language explanation and *"what normal looks like"*,
   - clickable anomaly list, RR interval map, zoom, ← / → to step through anomalies,
   - overlay of the original scan to check the digitization.
5. **Prints:** a print-ready PDF (`ecg_print.pdf`, A4 landscape) with numbered anomalies, legend, anomaly table
   and a glossary of ECG symbols. The viewer also has a print button with the same layout.
6. **Writes a longer report** (`ecg_report.html`) explaining ECG basics with synthetic "normal vs. AF" examples.

## Quick start

Requires [uv](https://docs.astral.sh/uv/) (it installs Python and the dependencies for you).

```bash
git clone https://github.com/takzen/paper-ecg-explainer.git
cd paper-ecg-explainer

# try it on the fictional demo recording
uv run demo/make_demo.py
uv run ecg_explain.py demo/demo_limb.png demo/demo_chest.png -o demo/output

# your own scans (limb leads first, chest leads second), Polish output
uv run ecg_explain.py scan_limb_leads.jpg scan_chest_leads.jpg --lang pl
```

| option | meaning |
|--------|---------|
| `--lang en\|pl` | language of the report and PDF, and the viewer's default language (default `en`) |
| `-o, --output DIR` | output folder (default: folder of the first scan) |
| `--leads "I,II,III,aVR,aVL,aVF"` | lead names for the next file, column by column from the top |
| `--no-open` | do not open the viewer in the browser |

The PDF is rendered by a locally installed Edge or Chrome in headless mode; without one, use the print button
in the viewer.

### Supported printout layout

By default the tool expects the common 3-row × 2-column printout (e.g. AsCARD):

| file | left column | right column  |
|------|-------------|---------------|
| 1st  | I, II, III  | aVR, aVL, aVF |
| 2nd  | V1, V2, V3  | V4, V5, V6    |

## Project layout

| file | role |
|------|------|
| `ecg_explain.py` | command-line entry point, PDF export |
| `digitize.py` | image → signal (grid detection, deskew, line tracing) |
| `analysis.py` | QRS detection, RR irregularity, P waves, atrial spectrum, anomaly list |
| `texts.py` | all user-facing wording in English and Polish |
| `viewer.py`, `viewer_template.html` | interactive viewer (data builder + HTML/JS template with the EN/PL switch) |
| `report.py`, `charts.py` | longer HTML report with charts |
| `demo/make_demo.py` | generates fictional ECG scans for the demo |

## Limitations

- Only the few seconds printed on the paper are analyzed. The thresholds are heuristics from literature and
  have not been clinically validated.
- Digitization quality depends on the scan: folds, faint print or stamps showing through the paper can distort it.
- It looks at the **rhythm** only. It does not assess QRS morphology, ST segments, intervals (PR, QT) or
  anything else a physician checks.
- Only the 3×2 printout layout is supported for now.

## Privacy

Real ECG scans and the generated reports are git-ignored on purpose. They are personal medical data and should
never be committed. The only images in this repository are screenshots made from the fictional demo recording.

## License

[MIT](LICENSE) © 2026 Krzysztof Pika

## Medical disclaimer

This software is provided for educational and informational purposes only. It is not intended to be a substitute
for professional medical advice, diagnosis or treatment, and it is not a medical device under EU Regulation
2017/745 (MDR) or any other regulation. The authors accept no liability for any decision made based on its output.
