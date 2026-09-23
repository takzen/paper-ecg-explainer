"""
Analiza rytmu na podstawie odczytanych przebiegów.

Co liczymy (i dlaczego):
  * uderzenia serca (zespoły QRS) i odstępy między nimi (RR) -> czy serce bije równo,
  * powtarzalność załamka P przed każdym uderzeniem -> czy rytm narzuca węzeł zatokowy,
  * częstotliwość falowania linii między uderzeniami -> migotanie czy trzepotanie przedsionków.
"""
from dataclasses import dataclass, field

import numpy as np
from scipy import signal as sps

# odprowadzenia, w których aktywność przedsionków (P, fale f/F) widać zwykle najlepiej
ODPROWADZENIA_PRZEDSIONKOWE = ["II", "III", "aVF", "V1"]


@dataclass
class Okno:
    """Kilka sekund zapisu, w których kilka odprowadzeń nagrano jednocześnie."""
    nazwa: str
    odprowadzenia: list                 # lista Odprowadzenie z tego samego odcinka czasu
    uderzenia: np.ndarray = None        # czasy załamków R [s]
    glowne: object = None               # odprowadzenie, w którym QRS jest najwyraźniejszy


@dataclass
class Wynik:
    okna: list
    rr: np.ndarray                      # wszystkie odstępy RR [s]
    rr_okno: list                       # do którego okna należy każdy RR
    tetno: float
    cv: float
    nrmssd: float
    proc_duzych_zmian: float
    ocena_niemiarowosci: str            # "wysoka" / "umiarkowana" / "niska"
    p_korelacja: float                  # 0..1, jak podobne są odcinki przed QRS
    p_ocena: str                        # "powtarzalne" / "brak powtarzalnych" / "niepewne"
    widmo_f: np.ndarray = None
    widmo_p: np.ndarray = None
    czestotliwosc_dominujaca: float = float("nan")
    indeks_organizacji: float = float("nan")
    ocena_fal: str = ""
    przyklady_p: list = field(default_factory=list)   # (nazwa, segmenty) do wykresu
    wniosek: str = ""


def _przytnij_brzegi(odp, sek=0.08):
    """Na brzegach kolumn drukarka stawia pionową kreskę - nie jest to sygnał serca."""
    n = int(sek * odp.fs)
    for pole in ("t", "mv", "x_px", "y_px"):
        setattr(odp, pole, getattr(odp, pole)[n:-n])


def _energia_nachylenia(x, fs):
    d = np.gradient(x) * fs
    e = np.convolve(d * d, np.ones(int(0.08 * fs)) / int(0.08 * fs), mode="same")
    return e / (np.percentile(e, 99) + 1e-9)


def wykryj_uderzenia(okno):
    """Łączy wszystkie odprowadzenia z okna: QRS to miejsce, gdzie linia jest stroma naraz w wielu z nich."""
    fs = okno.odprowadzenia[0].fs
    t0 = max(o.t[0] for o in okno.odprowadzenia)
    t1 = min(o.t[-1] for o in okno.odprowadzenia)
    siatka_t = np.arange(t0, t1, 1 / fs)
    suma = np.zeros_like(siatka_t)
    for o in okno.odprowadzenia:
        suma += np.interp(siatka_t, o.t, _energia_nachylenia(o.mv, fs))
    szczyty, _ = sps.find_peaks(suma, distance=int(0.27 * fs),
                                height=0.35 * np.percentile(suma, 99))

    # najwyraźniejsze odprowadzenie = największa amplituda QRS
    def amplituda(o):
        return np.percentile(np.abs(o.mv), 99.5)
    okno.glowne = max(okno.odprowadzenia, key=amplituda)
    g = okno.glowne
    r = []
    for s in szczyty:
        tc = siatka_t[s]
        m = (g.t > tc - 0.07) & (g.t < tc + 0.07)
        if not m.any():
            continue
        i = np.flatnonzero(m)[np.argmax(np.abs(g.mv[m]))]
        if g.t[0] + 0.04 < g.t[i] < g.t[-1] - 0.04:
            r.append(g.t[i])
    okno.uderzenia = np.array(r)


def _segmenty_przed_qrs(odp, uderzenia, od=-0.30, do=-0.06):
    n0, n1 = int(od * odp.fs), int(do * odp.fs)
    seg = []
    for tr in uderzenia:
        i = int(np.argmin(np.abs(odp.t - tr)))
        if i + n0 >= 0 and i + n1 <= len(odp.mv):
            s = odp.mv[i + n0:i + n1]
            seg.append(s - s.mean())
    return np.array(seg)


def ocen_zalamki_p(okna):
    """Jeśli przed każdym QRS jest ten sam załamek P, odcinki przed QRS są do siebie podobne."""
    korelacje, przyklady = [], []
    for okno in okna:
        for o in okno.odprowadzenia:
            if o.nazwa not in ODPROWADZENIA_PRZEDSIONKOWE:
                continue
            seg = _segmenty_przed_qrs(o, okno.uderzenia)
            if len(seg) < 3:
                continue
            c = np.corrcoef(seg)
            korelacje.append(np.mean(c[np.triu_indices(len(seg), 1)]))
            przyklady.append((o.nazwa, seg))
    k = float(np.mean(korelacje)) if korelacje else float("nan")
    if np.isnan(k):
        ocena = "niepewne"
    elif k > 0.6:
        ocena = "powtarzalne"
    elif k < 0.35:
        ocena = "brak powtarzalnych"
    else:
        ocena = "niepewne"
    return k, ocena, przyklady


def _aktywnosc_przedsionkow(odp, uderzenia):
    """Odejmuje uśredniony kształt uderzenia (QRS + T); zostaje to, co robią przedsionki."""
    fs = odp.fs
    n0, n1 = int(-0.10 * fs), int(0.45 * fs)
    idx = [int(np.argmin(np.abs(odp.t - tr))) for tr in uderzenia]
    idx = [i for i in idx if i + n0 >= 0 and i + n1 <= len(odp.mv)]
    x = odp.mv.copy()
    if len(idx) < 2:
        return x
    wzorzec = np.mean([x[i + n0:i + n1] for i in idx], axis=0)
    for i in idx:
        x[i + n0:i + n1] -= wzorzec
    return x


def widmo_przedsionkowe(okna):
    widma = []
    for okno in okna:
        for o in okno.odprowadzenia:
            if o.nazwa not in ODPROWADZENIA_PRZEDSIONKOWE:
                continue
            x = _aktywnosc_przedsionkow(o, okno.uderzenia)
            x = sps.detrend(x)
            b, a = sps.butter(3, [2.5, 15], btype="band", fs=o.fs)
            x = sps.filtfilt(b, a, x)
            nfft = 8192
            f = np.fft.rfftfreq(nfft, 1 / o.fs)
            p = np.abs(np.fft.rfft(x * np.hanning(len(x)), nfft)) ** 2
            pasmo = (f >= 3) & (f <= 12)
            widma.append(p / p[pasmo].sum())
    if not widma:
        return None, None, float("nan"), float("nan")
    p = np.mean(widma, axis=0)
    pasmo = (f >= 3) & (f <= 12)
    fd = float(f[pasmo][np.argmax(p[pasmo])])
    oi = float(p[(f >= fd - 0.5) & (f <= fd + 0.5)].sum() / p[pasmo].sum())
    return f, p, fd, oi


def analizuj(wydruki):
    okna = []
    for w in wydruki:
        for k in sorted({o.kolumna for o in w.odprowadzenia}):
            odp = [o for o in w.odprowadzenia if o.kolumna == k]
            for o in odp:
                _przytnij_brzegi(o)
            nazwy = ", ".join(o.nazwa for o in odp)
            okna.append(Okno(nazwa=nazwy, odprowadzenia=odp))
    for okno in okna:
        wykryj_uderzenia(okno)

    rr, rr_okno = [], []
    for i, okno in enumerate(okna):
        d = np.diff(okno.uderzenia)
        rr.extend(d)
        rr_okno.extend([i] * len(d))
    rr, rr_okno = np.array(rr), np.array(rr_okno)

    # kolejne różnice liczymy tylko wewnątrz okna (między oknami jest przerwa w zapisie)
    roznice = np.concatenate([np.diff(rr[rr_okno == i]) for i in range(len(okna))])
    sr = rr.mean()
    cv = rr.std() / sr
    nrmssd = np.sqrt(np.mean(roznice ** 2)) / sr
    duze = float(np.mean(np.abs(roznice) > 0.1 * sr) * 100)
    if nrmssd > 0.10 and cv > 0.08:
        niem = "wysoka"
    elif nrmssd > 0.05:
        niem = "umiarkowana"
    else:
        niem = "niska"

    pk, pocena, przyklady = ocen_zalamki_p(okna)
    f, p, fd, oi = widmo_przedsionkowe(okna)
    if np.isnan(fd):
        fale = "brak danych"
    elif fd >= 5.8 or oi < 0.35:
        fale = "nieregularne/szybkie (jak w migotaniu)"
    elif fd < 5.8 and oi >= 0.5:
        fale = "regularne (jak w trzepotaniu)"
    else:
        fale = "niejednoznaczne"

    wynik = Wynik(okna=okna, rr=rr, rr_okno=list(rr_okno), tetno=60 / sr, cv=cv,
                  nrmssd=nrmssd, proc_duzych_zmian=duze, ocena_niemiarowosci=niem,
                  p_korelacja=pk, p_ocena=pocena, widmo_f=f, widmo_p=p,
                  czestotliwosc_dominujaca=fd, indeks_organizacji=oi, ocena_fal=fale,
                  przyklady_p=przyklady)
    wynik.wniosek = _wniosek(wynik)
    return wynik


def fale_f(okno, odp):
    """Pojedyncze fale przedsionkowe (f/F) między uderzeniami - szczyty w zapisie po odjęciu QRS i T."""
    fs = odp.fs
    x = _aktywnosc_przedsionkow(odp, okno.uderzenia)
    b, a = sps.butter(3, [3, 12], btype="band", fs=fs)
    x = sps.filtfilt(b, a, sps.detrend(x))
    poza_qrs = np.ones(len(x), bool)
    for tr in okno.uderzenia:
        poza_qrs &= ~((odp.t > tr - 0.08) & (odp.t < tr + 0.12))
    if poza_qrs.sum() < fs * 0.5:
        return np.array([])
    szczyty, _ = sps.find_peaks(x, distance=int(0.1 * fs), prominence=0.8 * np.std(x[poza_qrs]))
    szczyty = [s for s in szczyty if poza_qrs[s]]
    return odp.t[szczyty]


def znajdz_anomalie(wynik):
    """Lista konkretnych miejsc w zapisie, które odbiegają od prawidłowego rytmu - z opisem dla laika."""
    anomalie, fale, strefy_p = [], [], []
    sr = wynik.rr.mean()

    def dodaj(**k):
        k["id"] = f"a{len(anomalie)}"
        anomalie.append(k)

    if wynik.tetno > 100:
        dodaj(typ="tempo", okno=None, t0=None, t1=None,
              tytul=f"Szybkie tętno: średnio {wynik.tetno:.0f}/min",
              opis=(f"W spoczynku serce powinno bić ok. 60–100 razy na minutę. Tu średnio {wynik.tetno:.0f}/min. "
                    "Przy migotaniu komory często biją za szybko, bo dostają z przedsionków zbyt wiele impulsów."))

    for i, okno in enumerate(wynik.okna):
        r = okno.uderzenia
        rr = np.diff(r)
        for j in range(len(rr)):
            a, b = r[j], r[j + 1]
            bpm = 60 / rr[j]
            if j > 0:
                zmiana = rr[j] - rr[j - 1]
                if abs(zmiana) > 0.1 * sr:
                    kierunek = "wcześniej" if zmiana < 0 else "później"
                    dodaj(typ="nierowny", okno=i, t0=a, t1=b,
                          tytul=f"Nierówny odstęp: {rr[j]:.2f} s po {rr[j - 1]:.2f} s",
                          opis=(f"To uderzenie przyszło o {abs(zmiana):.2f} s {kierunek}, niż wynikałoby z poprzedniego "
                                f"odstępu ({rr[j - 1]:.2f} s → {rr[j]:.2f} s, czyli {60 / rr[j - 1]:.0f}/min → {bpm:.0f}/min). "
                                "Zdrowe serce w spoczynku bije prawie jak metronom. Takie skoki raz w jedną, "
                                "raz w drugą stronę to główny znak migotania przedsionków."))
            if bpm > 120:
                dodaj(typ="szybki", okno=i, t0=a, t1=b,
                      tytul=f"Bardzo krótki odstęp: {rr[j]:.2f} s ({bpm:.0f}/min)",
                      opis=(f"Między tymi dwoma uderzeniami minęło tylko {rr[j]:.2f} s. Gdyby serce tak biło cały czas, "
                            f"tętno wynosiłoby {bpm:.0f}/min."))
            if rr[j] > 1.5 * sr:
                dodaj(typ="pauza", okno=i, t0=a, t1=b,
                      tytul=f"Dłuższa przerwa: {rr[j]:.2f} s",
                      opis=f"Odstęp jest o połowę dłuższy niż średnia ({sr:.2f} s).")

        # strefy przed QRS, gdzie powinien być załamek P
        for tr in r:
            strefy_p.append({"okno": i, "t0": tr - 0.30, "t1": tr - 0.06})
        if wynik.p_ocena == "brak powtarzalnych":
            dodaj(typ="brakP", okno=i, t0=None, t1=None,
                  tytul=f"Brak załamków P (odcinek {i + 1})",
                  opis=("Zakreskowane pola to miejsca tuż przed każdym uderzeniem, gdzie przy zdrowym rytmie widać "
                        "mały, zawsze taki sam garb P. Tu przed żadnym uderzeniem nie ma powtarzalnego garbu. "
                        "Przedsionki nie kurczą się normalnie."))

        for o in okno.odprowadzenia:
            if o.nazwa not in ODPROWADZENIA_PRZEDSIONKOWE:
                continue
            tf = fale_f(okno, o)
            for t in tf:
                i_ = int(np.argmin(np.abs(o.t - t)))
                fale.append({"okno": i, "lead": o.nazwa, "t": float(t), "mv": float(o.mv[i_])})
            if len(tf) >= 4:
                tempo = 60 / np.median(np.diff(tf))
                dodaj(typ="faleF", okno=i, t0=None, t1=None, lead=o.nazwa,
                      tytul=f"Fale f w {o.nazwa}: ok. {tempo:.0f}/min",
                      opis=(f"Różowe trójkąciki pokazują drobne fale między uderzeniami (ok. {tempo:.0f} na minutę). "
                            "To przedsionki, które zamiast jednego skurczu drgają bardzo szybko. "
                            "Przy trzepotaniu fale są równe (ok. 250–350/min), przy migotaniu szybsze i nieregularne."))
    return anomalie, fale, strefy_p


def _wniosek(w):
    if w.ocena_niemiarowosci == "wysoka" and w.p_ocena != "powtarzalne":
        if "trzepotaniu" in w.ocena_fal:
            return "trzepotanie"
        return "migotanie"
    if w.ocena_niemiarowosci == "niska" and w.p_ocena == "powtarzalne":
        return "zatokowy"
    return "niejednoznaczny"
