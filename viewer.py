"""
Interactive ECG viewer: a single offline HTML file with an EN/PL language switch.

All leads are redrawn on an ECG-paper grid with the anomalies marked on the trace:
irregular and very short intervals, zones without a P wave and individual f waves.
Clicking an anomaly scrolls the chart to it and explains what it means.
"""
import base64
import html
import json
import os

import cv2
import numpy as np

import texts
from analysis import find_anomalies

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer_template.html")
PRINT_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
              'stroke-linejoin="round" aria-hidden="true"><path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 '
              '2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>')


def _scan_data_uri(printout, lead):
    x0, y0, x1, y1 = lead.box
    crop = cv2.cvtColor(printout.image[y0:y1, x0:x1], cv2.COLOR_RGB2BGR)
    ok, jpg = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 72])
    return "data:image/jpeg;base64," + base64.b64encode(jpg.tobytes()).decode()


def _clean(v):
    """Make numpy values JSON-safe."""
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else round(float(v), 4)
    if isinstance(v, np.integer):
        return int(v)
    return v


def _data(printouts, result, lang):
    anomalies, f_waves, p_zones = find_anomalies(result)
    window_printout = [p for p in printouts for _ in sorted({l.column for l in p.leads})]
    windows = []
    for i, w in enumerate(result.windows):
        pr = window_printout[i]
        leads = []
        for l in w.leads:
            x0, y0, x1, y1 = l.box
            leads.append({
                "name": l.name,
                "t0": round(float(l.t[0]), 4),
                "dt": 1 / l.fs,
                "mv": [round(float(v), 3) for v in l.mv],
                "scan": {
                    "src": _scan_data_uri(pr, l),
                    "t0": (x0 - l.x_zero) / l.fs,
                    "t1": (x1 - l.x_zero) / l.fs,
                    "mvTop": -(y0 - l.y_zero) / l.px_per_mv,
                    "mvBottom": -(y1 - l.y_zero) / l.px_per_mv,
                },
            })
        windows.append({
            "name": w.name,
            "file": os.path.basename(pr.path),
            "column": int(w.leads[0].column),
            "main": w.main.name,
            "t0": max(l["t0"] for l in leads),
            "t1": min(l["t0"] + len(l["mv"]) * l["dt"] for l in leads),
            "beats": [round(float(t), 4) for t in w.beats],
            "leads": leads,
        })

    both = lambda table, key: {lang_: table[lang_][key] for lang_ in texts.LANGS}
    return {
        "lang": lang,
        "files": [os.path.basename(p.path) for p in printouts],
        "conclusion": texts.CONCLUSIONS[result.conclusion],
        "labels": {
            "irregularity": both(texts.IRREGULARITY, result.irregularity),
            "pWaves": both(texts.P_WAVES, result.p_waves),
            "atrialWaves": both(texts.ATRIAL_WAVES, result.atrial_waves),
        },
        "result": {k: _clean(v) for k, v in {
            "heartRate": round(result.heart_rate), "cv": result.cv, "nrmssd": result.nrmssd,
            "pCorrelation": result.p_correlation, "dominantFreq": result.dominant_freq,
            "organizationIndex": result.organization_index,
            "rrMin": result.rr.min(), "rrMax": result.rr.max(), "rrMean": result.rr.mean(),
        }.items()},
        "windows": windows,
        "anomalies": [{k: _clean(v) for k, v in a.items()} for a in anomalies],
        "fWaves": f_waves,
        "pZones": [{k: _clean(v) for k, v in z.items()} for z in p_zones],
        "glossary": texts.GLOSSARY,
    }


def generate(printouts, result, path, lang="en", report_link=None):
    data = _data(printouts, result, lang)
    data["reportLink"] = report_link
    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = (page.replace("/*__DATA__*/null", payload)
                .replace("__FILES__", html.escape(", ".join(data["files"])))
                .replace("__PRINT_ICON__", PRINT_ICON))
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
