"""
Odczyt przebiegu EKG ze skanu/zdjęcia wydruku.

Kroki:
  1. rozpoznanie czerwonej siatki i wyprostowanie przekrzywionego skanu,
  2. zmierzenie wielkości kratki (1 mm) -> przeliczenie pikseli na sekundy i miliwolty,
  3. podział wydruku na kolumny (odcinki czasu) i wiersze (odprowadzenia),
  4. prześledzenie czarnej linii w każdym odprowadzeniu kolumna po kolumnie.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image
from scipy import signal as sps

MM_NA_SEKUNDE = 25.0  # standardowy przesuw papieru
MM_NA_MV = 10.0       # standardowe wzmocnienie


@dataclass
class Odprowadzenie:
    nazwa: str
    kolumna: int            # 0 = lewa połowa wydruku, 1 = prawa
    t: np.ndarray           # czas [s] od początku kolumny
    mv: np.ndarray          # napięcie [mV], linia bazowa usunięta
    fs: float               # "próbkowanie" = piksele na sekundę
    x_px: np.ndarray        # położenie próbek na obrazie (do nakładki)
    y_px: np.ndarray
    ramka: tuple            # (x0, y0, x1, y1) wycinka obrazu z tym odprowadzeniem


@dataclass
class Wydruk:
    plik: str
    obraz: np.ndarray       # wyprostowany obraz RGB
    kat: float              # o ile stopni obrócono skan
    px_na_mm: float
    fs: float
    odprowadzenia: list = field(default_factory=list)


def _maska_krzywej(rgb, prog=150):
    """Piksele czarnej/szarej linii (siatka jest czerwona, więc ją pomijamy).
    prog=150 - wyraźna linia; prog=200 - także blade fragmenty stromych kresek."""
    a = rgb.astype(np.int16)
    r, g = a[..., 0], a[..., 1]
    return ((a.max(2) < prog) & ((r - g) < 45)).astype(np.uint8)


def _maska_siatki(rgb):
    a = rgb.astype(np.int16)
    r, g = a[..., 0], a[..., 1]
    return ((r > 150) & ((r - g) > 55)).astype(np.uint8)


def _ramka_papieru(siatka):
    wiersze = np.where(siatka.mean(1) > 0.05)[0]
    kolumny = np.where(siatka.mean(0) > 0.05)[0]
    return kolumny[0], wiersze[0], kolumny[-1], wiersze[-1]


def _kat_skosu(siatka):
    """Kąt, przy którym poziome linie siatki są najbardziej 'ostre' w rzucie na oś Y."""
    x0, y0, x1, y1 = _ramka_papieru(siatka)
    m = cv2.resize(siatka[y0:y1, x0:x1].astype(np.float32), None, fx=0.5, fy=0.5)
    h, w = m.shape
    najlepszy, wynik = 0.0, -1.0
    for kat in np.arange(-3.0, 3.01, 0.1):
        rot = cv2.getRotationMatrix2D((w / 2, h / 2), kat, 1.0)
        obr = cv2.warpAffine(m, rot, (w, h))
        ostrosc = np.var(np.diff(obr.sum(1)))
        if ostrosc > wynik:
            najlepszy, wynik = kat, ostrosc
    return float(najlepszy)


def _okres_siatki(profil):
    """Wielkość małej kratki (1 mm) w pikselach, z autokorelacji profilu siatki."""
    p = profil - profil.mean()
    ak = np.correlate(p, p, mode="full")[len(p) - 1:]
    ak /= ak[0]
    lag1 = 6 + int(np.argmax(ak[6:25]))
    # doprecyzowanie na dużej kratce (5 mm), która jest 5x dłuższa
    lo, hi = 5 * lag1 - 6, 5 * lag1 + 7
    lag5 = lo + int(np.argmax(ak[lo:hi]))
    return lag5 / 5.0


def _podzial_kolumn(krzywa, x0, x1, pasy):
    """Granica między kolumnami: najwęższe miejsce w środku wydruku, gdzie w pasach odprowadzeń nie ma linii."""
    prof = sum(krzywa[ya:yb, x0:x1].sum(0).astype(float) for ya, yb in pasy)
    prof = np.convolve(prof, np.ones(9) / 9, mode="same")
    w = x1 - x0
    a, b = int(w * 0.35), int(w * 0.65)
    return x0 + a + int(np.argmin(prof[a:b]))


def _wiersze_odprowadzen(krzywa, xa, xb, y0, y1, ile):
    """Szuka poziomów linii bazowych: wierszy, przez które krzywa ciągnie się przez prawie całą szerokość."""
    pas = cv2.dilate(krzywa[y0:y1, xa:xb], np.ones((51, 1), np.uint8))
    pokrycie = pas.mean(1)
    gestosc = np.convolve(krzywa[y0:y1, xa:xb].sum(1).astype(float), np.ones(15) / 15, mode="same")
    szczyty, _ = sps.find_peaks(gestosc, distance=150)
    szczyty = [s for s in szczyty if pokrycie[s] > 0.6]
    # najgęstsze kandydaty, ale wybieramy 'ile' pierwszych od góry (pod wykresami jest tekst)
    return [y0 + s for s in sorted(szczyty)[:ile]]


def _sledz_linie(mocna, slaba, xa, xb, ya, yb, y_start):
    """Idzie kolumna po kolumnie i wybiera fragment linii najbliższy poprzedniemu.
    Blade piksele (tylko w masce 'slaba') przyjmujemy wyłącznie, gdy stykają się z poprzednim
    fragmentem - dzięki temu nie przeskakujemy na przebijające przez papier pieczątki i napisy."""
    n = xb - xa
    y_wart = np.full(n, np.nan)
    poprzedni = None
    historia = []

    def odcinki(maska, x):
        idx = np.flatnonzero(maska[ya:yb, x])
        if idx.size == 0:
            return []
        return [(o[0] + ya, o[-1] + ya) for o in np.split(idx, np.flatnonzero(np.diff(idx) > 2) + 1)]

    def odl(o, ref):
        if o[1] < ref[0]:
            return ref[0] - o[1]
        if o[0] > ref[1]:
            return o[0] - ref[1]
        return 0

    for i, x in enumerate(range(xa, xb)):
        ref = poprzedni or (y_start - 40, y_start + 40)
        kandydaci = [(odl(o, ref), o) for o in odcinki(mocna, x)]
        kandydaci = [k for k in kandydaci if k[0] <= (60 if poprzedni else 0)]
        if poprzedni:
            kandydaci += [(odl(o, ref), o) for o in odcinki(slaba, x) if odl(o, ref) <= 3]
        if not kandydaci:
            poprzedni = None if (historia and i - historia[-1][0] > 15) else poprzedni
            continue
        a, b = min(kandydaci)[1]
        baza = np.median([h[1] for h in historia[-150:]]) if historia else y_start
        if b - a > 8:  # pionowa kreska (np. zespół QRS) -> bierzemy koniec dalszy od linii bazowej
            y = a if abs(a - baza) > abs(b - baza) else b
        else:
            y = (a + b) / 2
        y_wart[i] = y
        historia.append((i, (a + b) / 2))
        poprzedni = (a, b)
    return y_wart


def _zakres_krzywej(y, max_luka=12, min_dl=80):
    """Zakres właściwej krzywej: łączy kawałki przedzielone drobnymi przerwami,
    a krótkie kawałki na brzegach (napisy 'II', 'aVR', 'V4'...) odrzuca."""
    ok = np.flatnonzero(~np.isnan(y))
    if ok.size == 0:
        return 0, 0
    przerwy = np.flatnonzero(np.diff(ok) > max_luka)
    kawalki = [(k[0], k[-1] + 1) for k in np.split(ok, przerwy + 1)]
    while len(kawalki) > 1 and kawalki[0][1] - kawalki[0][0] < min_dl:
        kawalki.pop(0)
    while len(kawalki) > 1 and kawalki[-1][1] - kawalki[-1][0] < min_dl:
        kawalki.pop()
    return kawalki[0][0], kawalki[-1][1]


def _koniec_impulsu_kalibracyjnego(mv, fs):
    """Prostokąt na początku zapisu (1 mV przez ~0,1 s) to wzorzec skali, nie serce - odcinamy go."""
    okno = mv[: int(0.4 * fs)]
    wysoko = np.abs(okno - np.median(mv)) > 0.7
    n_min = int(0.04 * fs)
    i = 0
    while i < len(wysoko):
        if wysoko[i]:
            j = i
            while j < len(wysoko) and wysoko[j]:
                j += 1
            if j - i >= n_min:
                return min(len(mv) - 1, j + int(0.04 * fs))
            i = j
        i += 1
    return 0


def _usun_linie_bazowa(x, fs):
    """Usuwa powolne falowanie linii (oddech, ruch) dwoma filtrami medianowymi."""
    k1 = int(0.2 * fs) | 1
    k2 = int(0.6 * fs) | 1
    baza = sps.medfilt(sps.medfilt(x, k1), k2)
    return x - baza


def digitalizuj(plik, nazwy_odprowadzen, wierszy=3, kolumn=2):
    rgb = np.asarray(Image.open(plik).convert("RGB"))

    kat = _kat_skosu(_maska_siatki(rgb))
    h, w = rgb.shape[:2]
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), kat, 1.0)
    rgb = cv2.warpAffine(rgb, rot, (w, h), borderValue=(255, 255, 255))

    siatka = _maska_siatki(rgb)
    krzywa = _maska_krzywej(rgb)
    krzywa_blada = _maska_krzywej(rgb, prog=200)
    x0, y0, x1, y1 = _ramka_papieru(siatka)

    fragment = siatka[y0:y1, x0:x1].astype(float)
    px_na_mm = (_okres_siatki(fragment.sum(0)) + _okres_siatki(fragment.sum(1))) / 2
    fs = px_na_mm * MM_NA_SEKUNDE
    px_na_mv = px_na_mm * MM_NA_MV

    wydruk = Wydruk(plik=plik, obraz=rgb, kat=kat, px_na_mm=px_na_mm, fs=fs)

    poziomy_wydruku = _wiersze_odprowadzen(krzywa, x0, x1, y0, y1, wierszy)
    odstep = np.median(np.diff(poziomy_wydruku)) if len(poziomy_wydruku) > 1 else 300
    pasy = [(int(yc - odstep * 0.3), int(yc + odstep * 0.3)) for yc in poziomy_wydruku]
    granice = [x0]
    if kolumn == 2:
        granice.append(_podzial_kolumn(krzywa, x0, x1, pasy))
    granice.append(x1)

    for k in range(kolumn):
        xa, xb = granice[k], granice[k + 1]
        for r, yc in enumerate(poziomy_wydruku):
            nazwa = nazwy_odprowadzen[k * wierszy + r]
            ya = int(max(y0, yc - odstep * 0.5))
            yb = int(min(y1, yc + odstep * 0.5))
            y = _sledz_linie(krzywa, krzywa_blada, xa, xb, ya, yb, yc)
            a, b = _zakres_krzywej(y)
            y = y[a:b]
            xs = np.arange(xa + a, xa + b)
            ok = ~np.isnan(y)
            y = np.interp(np.arange(len(y)), np.flatnonzero(ok), y[ok])
            mv = -(y - np.median(y)) / px_na_mv
            ciecie = _koniec_impulsu_kalibracyjnego(mv, fs)
            y, xs, mv = y[ciecie:], xs[ciecie:], mv[ciecie:]
            mv = _usun_linie_bazowa(mv, fs)
            t = (xs - granice[k]) / fs
            ramka = (int(xs[0]) - 20, ya, int(xs[-1]) + 20, yb)
            wydruk.odprowadzenia.append(
                Odprowadzenie(nazwa, k, t, mv, fs, xs, y, ramka))
    return wydruk
