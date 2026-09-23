"""
Generate two FICTIONAL ECG printout scans (3 rows x 2 columns, like AsCARD) with simulated
atrial fibrillation. Used for the demo, screenshots and testing. Not a recording of any real person.

    uv run demo/make_demo.py
    uv run ecg_explain.py demo/demo_limb.png demo/demo_chest.png -o demo/output
"""
import os

import cv2
import numpy as np

PX_PER_MM = 11.8
FS = PX_PER_MM * 25          # pixels per second (25 mm/s)
PX_PER_MV = PX_PER_MM * 10   # pixels per millivolt (10 mm/mV)
DURATION = 3.9               # seconds per column
FOLDER = os.path.dirname(os.path.abspath(__file__))

# (QRS amplitude, T amplitude, f-wave strength) for each lead
LEADS = {
    "I": (0.55, 0.15, 0.4), "II": (1.0, 0.25, 1.0), "III": (0.45, 0.1, 1.2),
    "aVR": (-0.75, -0.2, 0.5), "aVL": (0.12, 0.05, 0.2), "aVF": (0.75, 0.18, 1.1),
    "V1": (-0.55, -0.1, 1.4), "V2": (-0.9, 0.2, 0.8), "V3": (-0.45, 0.25, 0.5),
    "V4": (0.7, 0.3, 0.4), "V5": (1.05, 0.25, 0.3), "V6": (0.9, 0.2, 0.3),
}


def _g(t, a, mu, sd):
    return a * np.exp(-((t - mu) ** 2) / (2 * sd ** 2))


def af_beats(rng):
    r, t = [], 0.25
    while t < DURATION - 0.15:
        r.append(t)
        t += rng.uniform(0.38, 0.92)
    return np.array(r)


def lead_signal(name, r, t, rng):
    qrs, tw, f = LEADS[name]
    y = np.zeros_like(t)
    for tr in r:
        y += (_g(t, -0.12 * qrs, tr - 0.03, 0.008) + _g(t, qrs, tr, 0.011)
              + _g(t, -0.3 * abs(qrs), tr + 0.03, 0.01) + _g(t, tw, tr + 0.26, 0.045))
    phase = rng.uniform(0, 2 * np.pi, 3)
    y += f * (0.05 * np.sin(2 * np.pi * 6.2 * t + phase[0]) + 0.03 * np.sin(2 * np.pi * 7.7 * t + phase[1])
              + 0.02 * np.sin(2 * np.pi * 5.3 * t + phase[2]))
    return y + rng.normal(0, 0.006, len(t))


def make_scan(names, filename, seed):
    rng = np.random.default_rng(seed)
    h, w = 2409, 3436
    img = np.full((h, w, 3), 246, np.uint8)
    x0, y0, x1, y1 = 560, 300, 3250, 1760
    img[y0:y1, x0:x1] = (255, 238, 235)
    for k, x in enumerate(np.arange(x0, x1, PX_PER_MM)):
        cv2.line(img, (int(x), y0), (int(x), y1), (225, 110, 110) if k % 5 == 0 else (242, 165, 163), 1)
    for k, y in enumerate(np.arange(y0, y1, PX_PER_MM)):
        cv2.line(img, (x0, int(y)), (x1, int(y)), (225, 110, 110) if k % 5 == 0 else (242, 165, 163), 1)

    columns = [700, 700 + int(DURATION * FS) + 140]
    rows = [620, 1010, 1400]
    t = np.arange(0, DURATION, 1 / FS)
    ink = (35, 35, 35)
    for k, xk in enumerate(columns):
        r = af_beats(rng)
        for j, yb in enumerate(rows):
            name = names[k * 3 + j]
            mv = lead_signal(name, r, t, rng)
            pts = np.stack([xk + t * FS, yb - mv * PX_PER_MV], 1).astype(np.int32)
            cv2.polylines(img, [pts], False, ink, 3, cv2.LINE_AA)
            cv2.putText(img, name, (xk - 95, yb - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.3, ink, 3, cv2.LINE_AA)
        # 1 mV calibration pulse before the bottom row
        yb = rows[-1] + 180
        pulse = np.array([[xk - 110, yb], [xk - 90, yb], [xk - 90, int(yb - PX_PER_MV)],
                          [xk - 55, int(yb - PX_PER_MV)], [xk - 55, yb], [xk - 35, yb]], np.int32)
        cv2.polylines(img, [pulse], False, ink, 3, cv2.LINE_AA)
        cv2.putText(img, "DEMO - fictional data * 25 mm/s * 10 mm/mV", (xk, 1680),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, ink, 2, cv2.LINE_AA)

    # slight skew, like a real scan
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), 0.6, 1.0)
    img = cv2.warpAffine(img, rot, (w, h), borderValue=(246, 246, 246))
    cv2.imwrite(os.path.join(FOLDER, filename), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))


if __name__ == "__main__":
    make_scan(["I", "II", "III", "aVR", "aVL", "aVF"], "demo_limb.png", 7)
    make_scan(["V1", "V2", "V3", "V4", "V5", "V6"], "demo_chest.png", 11)
    print("Saved demo/demo_limb.png and demo/demo_chest.png (fictional data).")
