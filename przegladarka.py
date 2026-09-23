"""
Interaktywna przeglądarka EKG (jeden plik HTML, działa offline w przeglądarce).

Pokazuje wszystkie odprowadzenia na siatce jak na papierze i zaznacza na nich anomalie:
nierówne odstępy, bardzo krótkie odstępy, miejsca bez załamka P i fale f.
Kliknięcie anomalii na liście przewija wykres do tego miejsca i wyjaśnia, co to znaczy.
"""
import base64
import html
import json
import os
import re

import cv2
import numpy as np

from analiza import znajdz_anomalie
from raport import SLOWNIK, WNIOSKI

SZABLON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "przegladarka.html")


def _skan_base64(wydruk, odp):
    x0, y0, x1, y1 = odp.ramka
    wycinek = cv2.cvtColor(wydruk.obraz[y0:y1, x0:x1], cv2.COLOR_RGB2BGR)
    ok, jpg = cv2.imencode(".jpg", wycinek, [cv2.IMWRITE_JPEG_QUALITY, 72])
    return "data:image/jpeg;base64," + base64.b64encode(jpg.tobytes()).decode()


def _dane(wydruki, wynik):
    anomalie, fale, strefy_p = znajdz_anomalie(wynik)
    wydruk_okna = [w for w in wydruki for _ in sorted({o.kolumna for o in w.odprowadzenia})]
    okna = []
    for i, okno in enumerate(wynik.okna):
        wd = wydruk_okna[i]
        leady = []
        for o in okno.odprowadzenia:
            x0, y0, x1, y1 = o.ramka
            leady.append({
                "nazwa": o.nazwa,
                "t0": round(float(o.t[0]), 4),
                "dt": 1 / o.fs,
                "mv": [round(float(v), 3) for v in o.mv],
                "skan": {
                    "src": _skan_base64(wd, o),
                    "t0": (x0 - o.x_zero) / o.fs,
                    "t1": (x1 - o.x_zero) / o.fs,
                    "mvGora": -(y0 - o.y_zero) / o.px_na_mv,
                    "mvDol": -(y1 - o.y_zero) / o.px_na_mv,
                },
            })
        okna.append({
            "nazwa": okno.nazwa,
            "plik": os.path.basename(wd.plik),
            "kolumna": int(okno.odprowadzenia[0].kolumna),
            "glowne": okno.glowne.nazwa,
            "t0": max(l["t0"] for l in leady),
            "t1": min(l["t0"] + len(l["mv"]) * l["dt"] for l in leady),
            "uderzenia": [round(float(t), 4) for t in okno.uderzenia],
            "leady": leady,
        })

    def czysc(v):
        if isinstance(v, (np.floating, float)):
            return None if np.isnan(v) else round(float(v), 4)
        if isinstance(v, str):
            return re.sub(r"(\d)\.(\d)", lambda m: m[1] + "," + m[2], v)  # polski zapis liczb: 0,62 s
        return v

    ikona, tytul, opis = WNIOSKI[wynik.wniosek]
    return {
        "pliki": [os.path.basename(w.plik) for w in wydruki],
        "wynik": {
            "wniosek": wynik.wniosek, "ikona": ikona, "tytul": tytul, "opis": opis,
            "tetno": round(wynik.tetno), "nierownosc": wynik.ocena_niemiarowosci,
            "cv": czysc(wynik.cv), "nrmssd": czysc(wynik.nrmssd),
            "pOcena": wynik.p_ocena, "pKorelacja": czysc(wynik.p_korelacja),
            "fd": czysc(wynik.czestotliwosc_dominujaca), "oi": czysc(wynik.indeks_organizacji),
            "fale": wynik.ocena_fal,
            "rrMin": czysc(wynik.rr.min()), "rrMax": czysc(wynik.rr.max()), "rrSr": czysc(wynik.rr.mean()),
        },
        "okna": okna,
        "anomalie": [{k: czysc(v) for k, v in a.items()} for a in anomalie],
        "faleF": fale,
        "strefyP": [{k: czysc(v) for k, v in s.items()} for s in strefy_p],
        "slownik": SLOWNIK,
    }


def generuj(wydruki, wynik, sciezka, link_raportu=None):
    dane = _dane(wydruki, wynik)
    dane["linkRaportu"] = link_raportu
    with open(SZABLON, encoding="utf-8") as f:
        szablon = f.read()
    json_txt = json.dumps(dane, ensure_ascii=False).replace("</", "<\\/")
    tytul = html.escape(", ".join(dane["pliki"]))
    wynik_html = szablon.replace("/*__DANE__*/null", json_txt).replace("__PLIKI__", tytul)
    with open(sciezka, "w", encoding="utf-8") as f:
        f.write(wynik_html)
