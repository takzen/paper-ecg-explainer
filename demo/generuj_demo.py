"""
Generuje dwa FIKCYJNE skany wydruku EKG (układ 3 wiersze x 2 kolumny, jak AsCARD)
z symulowanym migotaniem przedsionków. Służą do demo, zrzutów ekranu i testów.
Nie są zapisem żadnej prawdziwej osoby.

    python demo/generuj_demo.py
    python ekg_analiza.py demo/demo_konczynowe.png demo/demo_przedsercowe.png -o demo/wynik
"""
import os

import cv2
import numpy as np

PX_NA_MM = 11.8
FS = PX_NA_MM * 25          # piksele na sekundę (25 mm/s)
PX_NA_MV = PX_NA_MM * 10    # piksele na miliwolt (10 mm/mV)
DLUGOSC = 3.9               # sekundy w kolumnie
FOLDER = os.path.dirname(os.path.abspath(__file__))

# (amplituda QRS, amplituda T, siła fal f) dla każdego odprowadzenia
ODPROWADZENIA = {
    "I": (0.55, 0.15, 0.4), "II": (1.0, 0.25, 1.0), "III": (0.45, 0.1, 1.2),
    "aVR": (-0.75, -0.2, 0.5), "aVL": (0.12, 0.05, 0.2), "aVF": (0.75, 0.18, 1.1),
    "V1": (-0.55, -0.1, 1.4), "V2": (-0.9, 0.2, 0.8), "V3": (-0.45, 0.25, 0.5),
    "V4": (0.7, 0.3, 0.4), "V5": (1.05, 0.25, 0.3), "V6": (0.9, 0.2, 0.3),
}


def _g(t, a, mu, sd):
    return a * np.exp(-((t - mu) ** 2) / (2 * sd ** 2))


def uderzenia_af(rng):
    r, t = [], 0.25
    while t < DLUGOSC - 0.15:
        r.append(t)
        t += rng.uniform(0.38, 0.92)
    return np.array(r)


def sygnal(nazwa, r, t, rng):
    qrs, tw, f = ODPROWADZENIA[nazwa]
    y = np.zeros_like(t)
    for tr in r:
        y += (_g(t, -0.12 * qrs, tr - 0.03, 0.008) + _g(t, qrs, tr, 0.011)
              + _g(t, -0.3 * abs(qrs), tr + 0.03, 0.01) + _g(t, tw, tr + 0.26, 0.045))
    faza = rng.uniform(0, 2 * np.pi, 3)
    y += f * (0.05 * np.sin(2 * np.pi * 6.2 * t + faza[0]) + 0.03 * np.sin(2 * np.pi * 7.7 * t + faza[1])
              + 0.02 * np.sin(2 * np.pi * 5.3 * t + faza[2]))
    return y + rng.normal(0, 0.006, len(t))


def skan(nazwy, plik, ziarno):
    rng = np.random.default_rng(ziarno)
    h, w = 2409, 3436
    img = np.full((h, w, 3), 246, np.uint8)
    x0, y0, x1, y1 = 560, 300, 3250, 1760
    img[y0:y1, x0:x1] = (255, 238, 235)
    for k, x in enumerate(np.arange(x0, x1, PX_NA_MM)):
        cv2.line(img, (int(x), y0), (int(x), y1), (225, 110, 110) if k % 5 == 0 else (242, 165, 163), 1)
    for k, y in enumerate(np.arange(y0, y1, PX_NA_MM)):
        cv2.line(img, (x0, int(y)), (x1, int(y)), (225, 110, 110) if k % 5 == 0 else (242, 165, 163), 1)

    kolumny = [700, 700 + int(DLUGOSC * FS) + 140]
    wiersze = [620, 1010, 1400]
    t = np.arange(0, DLUGOSC, 1 / FS)
    tusz = (35, 35, 35)
    for k, xk in enumerate(kolumny):
        r = uderzenia_af(rng)
        for j, yb in enumerate(wiersze):
            nazwa = nazwy[k * 3 + j]
            mv = sygnal(nazwa, r, t, rng)
            pts = np.stack([xk + t * FS, yb - mv * PX_NA_MV], 1).astype(np.int32)
            cv2.polylines(img, [pts], False, tusz, 3, cv2.LINE_AA)
            cv2.putText(img, nazwa, (xk - 95, yb - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.3, tusz, 3, cv2.LINE_AA)
        # impuls kalibracyjny 1 mV przed dolnym wierszem
        yb = wiersze[-1] + 180
        pts = np.array([[xk - 110, yb], [xk - 90, yb], [xk - 90, int(yb - PX_NA_MV)],
                        [xk - 55, int(yb - PX_NA_MV)], [xk - 55, yb], [xk - 35, yb]], np.int32)
        cv2.polylines(img, [pts], False, tusz, 3, cv2.LINE_AA)
        cv2.putText(img, "DEMO - dane fikcyjne * 25 mm/s * 10 mm/mV", (xk, 1680),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, tusz, 2, cv2.LINE_AA)

    # lekki skos jak na prawdziwym skanie
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), 0.6, 1.0)
    img = cv2.warpAffine(img, rot, (w, h), borderValue=(246, 246, 246))
    cv2.imwrite(os.path.join(FOLDER, plik), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))


if __name__ == "__main__":
    skan(["I", "II", "III", "aVR", "aVL", "aVF"], "demo_konczynowe.png", 7)
    skan(["V1", "V2", "V3", "V4", "V5", "V6"], "demo_przedsercowe.png", 11)
    print("Zapisano demo/demo_konczynowe.png i demo/demo_przedsercowe.png (dane fikcyjne).")
