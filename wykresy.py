"""Wykresy do raportu - rysowane jak na papierze EKG, żeby łatwo porównać je z wydrukiem."""
import base64
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

TUSZ = "#0b0b0b"
TEKST = "#52514e"
AKCENT = "#2a78d6"      # zaznaczone uderzenia / wyniki
PORÓWNANIE = "#eb6834"  # wzorzec do porównania
KRATKA_MALA = "#f7d4d4"
KRATKA_DUZA = "#ec9f9f"
PAPIER = "#fff7f5"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": "#c9c7c1",
    "axes.labelcolor": TEKST,
    "xtick.color": TEKST,
    "ytick.color": TEKST,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def do_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def papier_ekg(ax, t0, t1, v0, v1):
    """Siatka jak na wydruku: mała kratka 0,04 s x 0,1 mV, duża 0,2 s x 0,5 mV."""
    ax.set_facecolor(PAPIER)
    for x in np.arange(np.floor(t0 / 0.04) * 0.04, t1, 0.04):
        duza = abs(x / 0.2 - round(x / 0.2)) < 1e-6
        ax.axvline(x, color=KRATKA_DUZA if duza else KRATKA_MALA, lw=0.8 if duza else 0.5, zorder=0)
    for y in np.arange(np.floor(v0 / 0.1) * 0.1, v1, 0.1):
        duza = abs(y / 0.5 - round(y / 0.5)) < 1e-6
        ax.axhline(y, color=KRATKA_DUZA if duza else KRATKA_MALA, lw=0.8 if duza else 0.5, zorder=0)
    ax.set_xlim(t0, t1)
    ax.set_ylim(v0, v1)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)


# ---------- przebiegi syntetyczne (tylko do objaśnień) ----------

def _gauss(t, a, mu, sd):
    return a * np.exp(-((t - mu) ** 2) / (2 * sd ** 2))


def _uderzenie(t, tr, z_p=True):
    y = (_gauss(t, -0.10, tr - 0.035, 0.008) + _gauss(t, 1.0, tr, 0.011)
         + _gauss(t, -0.25, tr + 0.035, 0.010) + _gauss(t, 0.28, tr + 0.28, 0.045))
    if z_p:
        y += _gauss(t, 0.14, tr - 0.17, 0.025)
    return y


def pasek_syntetyczny(rodzaj, dlugosc=5.0, fs=500, ziarno=3):
    rng = np.random.default_rng(ziarno)
    t = np.arange(0, dlugosc, 1 / fs)
    y = np.zeros_like(t)
    if rodzaj == "zatokowy":
        r = np.arange(0.45, dlugosc - 0.2, 0.8)
        for tr in r:
            y += _uderzenie(t, tr, z_p=True)
    else:
        r, tr = [], 0.35
        while tr < dlugosc - 0.2:
            r.append(tr)
            tr += rng.uniform(0.40, 0.95)
        for tr in r:
            y += _uderzenie(t, tr, z_p=False)
        faza = rng.uniform(0, 2 * np.pi, 3)
        y += (0.045 * np.sin(2 * np.pi * 6.3 * t + faza[0]) + 0.03 * np.sin(2 * np.pi * 7.9 * t + faza[1])
              + 0.02 * np.sin(2 * np.pi * 5.1 * t + faza[2]))
    return t, y, np.array(r)


def schemat_uderzenia():
    t = np.linspace(-0.35, 0.65, 1000)
    y = _uderzenie(t, 0.0)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    papier_ekg(ax, -0.35, 0.65, -0.45, 1.25)
    ax.plot(t, y, color=TUSZ, lw=1.8)
    opisy = [(-0.19, 0.2, "P", "przedsionki\nsię kurczą"),
             (0.04, 1.07, "QRS", "komory się kurczą\n(uderzenie)"),
             (0.28, 0.36, "T", "komory\nodpoczywają")]
    for x, y0, lit, opis in opisy:
        ax.annotate(lit, (x, y0), ha="center", va="bottom", fontsize=15, fontweight="bold", color=AKCENT)
        ax.annotate(opis, (x, -0.42), ha="center", va="bottom", fontsize=9, color=TEKST)
    # legenda kratki
    ax.plot([0.45, 0.65], [1.15, 1.15], color=TUSZ, lw=1)
    ax.text(0.55, 1.17, "1 duża kratka = 0,2 s", ha="center", va="bottom", fontsize=8, color=TEKST)
    ax.set_xticks([])
    ax.set_yticks([])
    return do_base64(fig)


def porownanie_rytmow():
    fig, osie = plt.subplots(2, 1, figsize=(10, 4.6))
    for ax, rodzaj, tytul in [
        (osie[0], "zatokowy", "Rytm prawidłowy (zatokowy) - przykład wygenerowany"),
        (osie[1], "migotanie", "Migotanie przedsionków - przykład wygenerowany"),
    ]:
        t, y, r = pasek_syntetyczny(rodzaj)
        papier_ekg(ax, 0, 5, -0.4, 1.2)
        ax.plot(t, y, color=TUSZ, lw=1.4)
        for a, b in zip(r[:-1], r[1:]):
            ax.annotate("", xy=(b, 1.1), xytext=(a, 1.1),
                        arrowprops=dict(arrowstyle="<->", color=AKCENT, lw=1))
            ax.text((a + b) / 2, 1.13, f"{b - a:.2f} s", ha="center", va="bottom", fontsize=8, color=TEKST)
        ax.set_title(tytul, loc="left", fontsize=10.5, color=TUSZ)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.tight_layout()
    return do_base64(fig)


# ---------- wykresy z prawdziwego zapisu ----------

def nakladka_odczytu(wydruk, odp):
    x0, y0, x1, y1 = odp.ramka
    wycinek = wydruk.obraz[y0:y1, x0:x1]
    fig, osie = plt.subplots(2, 1, figsize=(10, 4.2), gridspec_kw={"hspace": 0.05})
    for ax in osie:
        ax.imshow(wycinek)
        ax.axis("off")
    osie[1].plot(odp.x_px - x0, odp.y_px - y0, color=AKCENT, lw=1.6)
    osie[0].set_title(f"Odprowadzenie {odp.nazwa}: górny pasek - skan, dolny - linia odczytana przez program (niebieska)",
                      loc="left", fontsize=9.5, color=TEKST)
    return do_base64(fig)


def pasek_z_uderzeniami(okno):
    o = okno.glowne
    r = okno.uderzenia
    v0 = min(-0.5, np.floor(o.mv.min() * 2) / 2)
    v1 = max(1.2, np.ceil(o.mv.max() * 2) / 2 + 0.6)
    fig, ax = plt.subplots(figsize=(10, 2.8))
    papier_ekg(ax, o.t[0], o.t[-1], v0, v1)
    ax.plot(o.t, o.mv, color=TUSZ, lw=1.2)
    for tr in r:
        i = int(np.argmin(np.abs(o.t - tr)))
        ax.plot(tr, o.mv[i], "o", ms=8, mfc="none", mec=AKCENT, mew=2)
    gora = v1 - 0.3
    for a, b in zip(r[:-1], r[1:]):
        ax.annotate("", xy=(b, gora), xytext=(a, gora), arrowprops=dict(arrowstyle="<->", color=AKCENT, lw=1))
        ax.text((a + b) / 2, gora + 0.04, f"{b - a:.2f} s\n({60 / (b - a):.0f}/min)",
                ha="center", va="bottom", fontsize=8, color=TEKST)
    # gdzie wypadałyby uderzenia, gdyby serce biło równo
    if len(r) > 2:
        sr = np.mean(np.diff(r))
        for k, tt in enumerate(np.arange(r[0], o.t[-1], sr)):
            ax.axvline(tt, ymin=0, ymax=0.08, color=PORÓWNANIE, lw=2.2)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"Odprowadzenie {o.nazwa}", loc="left", fontsize=10, color=TUSZ, pad=10)
    return do_base64(fig)


def tachogram(wynik):
    fig, ax = plt.subplots(figsize=(10, 3.2))
    x, pozycje, etykiety = 0, [], []
    for i, okno in enumerate(wynik.okna):
        rr = wynik.rr[np.array(wynik.rr_okno) == i]
        xs = np.arange(x, x + len(rr))
        ax.bar(xs, rr, width=0.8, color=AKCENT)
        pozycje.append(xs.mean() if len(xs) else x)
        etykiety.append(f"odcinek {i + 1}")
        x += len(rr) + 1.2
    sr = wynik.rr.mean()
    ax.axhline(sr, color=PORÓWNANIE, lw=2, ls="--")
    ax.text(x - 1, sr + 0.015, f"średnio {sr:.2f} s", color=TEKST, ha="right", va="bottom", fontsize=9)
    ax.set_ylabel("odstęp RR [s]")
    ax.set_ylim(0, max(1.0, wynik.rr.max() * 1.15))
    ax.set_xticks(pozycje)
    ax.set_xticklabels(etykiety)
    ax.grid(axis="y", color="#e6e4df", lw=0.7)
    ax.set_axisbelow(True)
    return do_base64(fig)


def zalamki_p(wynik):
    fig, osie = plt.subplots(1, 2, figsize=(10, 3.2), sharey=True)
    nazwa, seg = wynik.przyklady_p[0] if wynik.przyklady_p else ("-", np.zeros((0, 10)))
    fs = wynik.okna[0].odprowadzenia[0].fs
    t = np.linspace(-0.30, -0.06, seg.shape[1]) if len(seg) else np.array([])
    for ax in osie:
        papier_ekg(ax, -0.30, -0.06, -0.25, 0.3)
        ax.set_xticks([])
        ax.set_yticks([])
    for s in seg:
        osie[0].plot(t, s, color=AKCENT, lw=1.3, alpha=0.8)
    osie[0].set_title(f"Twój zapis ({nazwa}): odcinki tuż przed\nkażdym uderzeniem, nałożone na siebie",
                      loc="left", fontsize=9.5, color=TUSZ)
    ts, ys, rs = pasek_syntetyczny("zatokowy", fs=int(fs))
    n0, n1 = int(-0.30 * fs), int(-0.06 * fs)
    rng = np.random.default_rng(1)
    for tr in rs[1:]:
        i = int(tr * fs)
        s = ys[i + n0:i + n1] + rng.normal(0, 0.01, n1 - n0)
        osie[1].plot(np.linspace(-0.30, -0.06, len(s)), s - s.mean(), color=PORÓWNANIE, lw=1.3, alpha=0.8)
    osie[1].set_title("Dla porównania - rytm prawidłowy:\nten sam garb (załamek P) za każdym razem",
                      loc="left", fontsize=9.5, color=TUSZ)
    fig.tight_layout()
    return do_base64(fig)


def widmo(wynik):
    f, p = wynik.widmo_f, wynik.widmo_p
    fig, ax = plt.subplots(figsize=(10, 3.2))
    m = (f >= 2) & (f <= 12)
    ax.axvspan(4.2, 5.8, color="#f3e3c2", zorder=0)
    ax.axvspan(5.8, 10, color="#d9e6f7", zorder=0)
    ax.text(5.0, 0.97, "typowo\ntrzepotanie", transform=ax.get_xaxis_transform(), ha="center", va="top",
            fontsize=8.5, color=TEKST)
    ax.text(7.9, 0.97, "typowo migotanie", transform=ax.get_xaxis_transform(), ha="center", va="top",
            fontsize=8.5, color=TEKST)
    ax.plot(f[m], p[m] / p[m].max(), color=AKCENT, lw=2)
    fd = wynik.czestotliwosc_dominujaca
    ax.plot([fd], [1.0], "o", ms=8, color=AKCENT, mec="white", mew=2)
    ax.annotate(f"najsilniejsze falowanie:\n{fd:.1f} razy/s = ok. {fd * 60:.0f}/min", (fd, 1.0),
                xytext=(12, -28), textcoords="offset points", fontsize=9, color=TUSZ)
    ax.set_xlim(2, 12)
    ax.set_ylim(0, 1.12)
    ax.set_yticks([])
    ax.set_xlabel("jak szybko faluje linia [razy na sekundę]  (x60 = razy na minutę)")
    return do_base64(fig)
