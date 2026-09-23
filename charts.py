"""Report charts, drawn like ECG paper so they are easy to compare with the printout.
Every chart takes `lang` ("en" / "pl") for its labels."""
import base64
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from texts import num

INK = "#0b0b0b"
TEXT = "#52514e"
ACCENT = "#2a78d6"      # detected beats / results
REFERENCE = "#eb6834"   # reference pattern for comparison
GRID_MINOR = "#f7d4d4"
GRID_MAJOR = "#ec9f9f"
PAPER = "#fff7f5"

LABELS = {
    "en": {
        "p": "atria\ncontract", "qrs": "ventricles contract\n(the beat)", "t": "ventricles\nrest",
        "large_square": "1 large square = 0.2 s",
        "sinus_title": "Normal (sinus) rhythm - generated example",
        "af_title": "Atrial fibrillation - generated example",
        "overlay": "Lead {name}: top - scan, bottom - line read by the program (blue)",
        "lead": "Lead {name}", "segment": "segment {i}", "mean": "mean {v} s", "rr_axis": "RR interval [s]",
        "p_left": "Analyzed recording ({name}): segments just before\neach beat, overlaid",
        "p_right": "For comparison - normal rhythm:\nthe same bump (P wave) every time",
        "flutter_band": "typically\nflutter", "af_band": "typically fibrillation",
        "peak": "strongest undulation:\n{hz} per s = about {pm}/min",
        "freq_axis": "how fast the line undulates [times per second]  (x60 = per minute)",
    },
    "pl": {
        "p": "przedsionki\nsię kurczą", "qrs": "komory się kurczą\n(uderzenie)", "t": "komory\nodpoczywają",
        "large_square": "1 duża kratka = 0,2 s",
        "sinus_title": "Rytm prawidłowy (zatokowy) - przykład wygenerowany",
        "af_title": "Migotanie przedsionków - przykład wygenerowany",
        "overlay": "Odprowadzenie {name}: górny pasek - skan, dolny - linia odczytana przez program (niebieska)",
        "lead": "Odprowadzenie {name}", "segment": "odcinek {i}", "mean": "średnio {v} s", "rr_axis": "odstęp RR [s]",
        "p_left": "Analizowany zapis ({name}): odcinki tuż przed\nkażdym uderzeniem, nałożone na siebie",
        "p_right": "Dla porównania - rytm prawidłowy:\nten sam garb (załamek P) za każdym razem",
        "flutter_band": "typowo\ntrzepotanie", "af_band": "typowo migotanie",
        "peak": "najsilniejsze falowanie:\n{hz} razy/s = ok. {pm}/min",
        "freq_axis": "jak szybko faluje linia [razy na sekundę]  (x60 = razy na minutę)",
    },
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": "#c9c7c1",
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def ecg_paper(ax, t0, t1, v0, v1):
    """Grid like on the printout: small square 0.04 s x 0.1 mV, large square 0.2 s x 0.5 mV."""
    ax.set_facecolor(PAPER)
    for x in np.arange(np.floor(t0 / 0.04) * 0.04, t1, 0.04):
        major = abs(x / 0.2 - round(x / 0.2)) < 1e-6
        ax.axvline(x, color=GRID_MAJOR if major else GRID_MINOR, lw=0.8 if major else 0.5, zorder=0)
    for y in np.arange(np.floor(v0 / 0.1) * 0.1, v1, 0.1):
        major = abs(y / 0.5 - round(y / 0.5)) < 1e-6
        ax.axhline(y, color=GRID_MAJOR if major else GRID_MINOR, lw=0.8 if major else 0.5, zorder=0)
    ax.set_xlim(t0, t1)
    ax.set_ylim(v0, v1)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)


# ---------- synthetic waveforms (for explanations only) ----------

def _gauss(t, a, mu, sd):
    return a * np.exp(-((t - mu) ** 2) / (2 * sd ** 2))


def _beat(t, tr, with_p=True):
    y = (_gauss(t, -0.10, tr - 0.035, 0.008) + _gauss(t, 1.0, tr, 0.011)
         + _gauss(t, -0.25, tr + 0.035, 0.010) + _gauss(t, 0.28, tr + 0.28, 0.045))
    if with_p:
        y += _gauss(t, 0.14, tr - 0.17, 0.025)
    return y


def synthetic_strip(kind, duration=5.0, fs=500, seed=3):
    """kind: "sinus" or "af"."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, duration, 1 / fs)
    y = np.zeros_like(t)
    if kind == "sinus":
        r = np.arange(0.45, duration - 0.2, 0.8)
        for tr in r:
            y += _beat(t, tr, with_p=True)
    else:
        r, tr = [], 0.35
        while tr < duration - 0.2:
            r.append(tr)
            tr += rng.uniform(0.40, 0.95)
        for tr in r:
            y += _beat(t, tr, with_p=False)
        phase = rng.uniform(0, 2 * np.pi, 3)
        y += (0.045 * np.sin(2 * np.pi * 6.3 * t + phase[0]) + 0.03 * np.sin(2 * np.pi * 7.9 * t + phase[1])
              + 0.02 * np.sin(2 * np.pi * 5.1 * t + phase[2]))
    return t, y, np.array(r)


def beat_diagram(lang="en"):
    L = LABELS[lang]
    t = np.linspace(-0.35, 0.65, 1000)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ecg_paper(ax, -0.35, 0.65, -0.45, 1.25)
    ax.plot(t, _beat(t, 0.0), color=INK, lw=1.8)
    for x, y0, letter, caption in [(-0.19, 0.2, "P", L["p"]), (0.04, 1.07, "QRS", L["qrs"]), (0.28, 0.36, "T", L["t"])]:
        ax.annotate(letter, (x, y0), ha="center", va="bottom", fontsize=15, fontweight="bold", color=ACCENT)
        ax.annotate(caption, (x, -0.42), ha="center", va="bottom", fontsize=9, color=TEXT)
    ax.plot([0.45, 0.65], [1.15, 1.15], color=INK, lw=1)
    ax.text(0.55, 1.17, L["large_square"], ha="center", va="bottom", fontsize=8, color=TEXT)
    ax.set_xticks([])
    ax.set_yticks([])
    return to_base64(fig)


def rhythm_comparison(lang="en"):
    L = LABELS[lang]
    fig, axes = plt.subplots(2, 1, figsize=(10, 4.6))
    for ax, kind, title in [(axes[0], "sinus", L["sinus_title"]), (axes[1], "af", L["af_title"])]:
        t, y, r = synthetic_strip(kind)
        ecg_paper(ax, 0, 5, -0.4, 1.2)
        ax.plot(t, y, color=INK, lw=1.4)
        for a, b in zip(r[:-1], r[1:]):
            ax.annotate("", xy=(b, 1.1), xytext=(a, 1.1), arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=1))
            ax.text((a + b) / 2, 1.13, f"{num(b - a, 2, lang)} s", ha="center", va="bottom", fontsize=8, color=TEXT)
        ax.set_title(title, loc="left", fontsize=10.5, color=INK)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.tight_layout()
    return to_base64(fig)


# ---------- charts from the actual recording ----------

def digitization_overlay(printout, lead, lang="en"):
    x0, y0, x1, y1 = lead.box
    crop = printout.image[y0:y1, x0:x1]
    fig, axes = plt.subplots(2, 1, figsize=(10, 4.2), gridspec_kw={"hspace": 0.05})
    for ax in axes:
        ax.imshow(crop)
        ax.axis("off")
    axes[1].plot(lead.x_px - x0, lead.y_px - y0, color=ACCENT, lw=1.6)
    axes[0].set_title(LABELS[lang]["overlay"].format(name=lead.name), loc="left", fontsize=9.5, color=TEXT)
    return to_base64(fig)


def strip_with_beats(window, lang="en"):
    l, r = window.main, window.beats
    v0 = min(-0.5, np.floor(l.mv.min() * 2) / 2)
    v1 = max(1.2, np.ceil(l.mv.max() * 2) / 2 + 0.6)
    fig, ax = plt.subplots(figsize=(10, 2.8))
    ecg_paper(ax, l.t[0], l.t[-1], v0, v1)
    ax.plot(l.t, l.mv, color=INK, lw=1.2)
    for tr in r:
        i = int(np.argmin(np.abs(l.t - tr)))
        ax.plot(tr, l.mv[i], "o", ms=8, mfc="none", mec=ACCENT, mew=2)
    top = v1 - 0.3
    for a, b in zip(r[:-1], r[1:]):
        ax.annotate("", xy=(b, top), xytext=(a, top), arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=1))
        ax.text((a + b) / 2, top + 0.04, f"{num(b - a, 2, lang)} s\n({60 / (b - a):.0f}/min)",
                ha="center", va="bottom", fontsize=8, color=TEXT)
    # where the beats would fall if the heart beat perfectly regularly
    if len(r) > 2:
        for tt in np.arange(r[0], l.t[-1], np.mean(np.diff(r))):
            ax.axvline(tt, ymin=0, ymax=0.08, color=REFERENCE, lw=2.2)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(LABELS[lang]["lead"].format(name=l.name), loc="left", fontsize=10, color=INK, pad=10)
    return to_base64(fig)


def rr_bars(result, lang="en"):
    L = LABELS[lang]
    fig, ax = plt.subplots(figsize=(10, 3.2))
    x, positions, labels = 0, [], []
    windows = np.array(result.rr_window)
    for i, _ in enumerate(result.windows):
        rr = result.rr[windows == i]
        xs = np.arange(x, x + len(rr))
        ax.bar(xs, rr, width=0.8, color=ACCENT)
        positions.append(xs.mean() if len(xs) else x)
        labels.append(L["segment"].format(i=i + 1))
        x += len(rr) + 1.2
    mean_rr = result.rr.mean()
    ax.axhline(mean_rr, color=REFERENCE, lw=2, ls="--")
    ax.text(x - 1, mean_rr + 0.015, L["mean"].format(v=num(mean_rr, 2, lang)), color=TEXT,
            ha="right", va="bottom", fontsize=9)
    ax.set_ylabel(L["rr_axis"])
    ax.set_ylim(0, max(1.0, result.rr.max() * 1.15))
    ax.set_xticks(positions)
    ax.set_xticklabels(labels)
    ax.grid(axis="y", color="#e6e4df", lw=0.7)
    ax.set_axisbelow(True)
    return to_base64(fig)


def p_wave_overlay(result, lang="en"):
    L = LABELS[lang]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.2), sharey=True)
    name, segs = result.p_examples[0] if result.p_examples else ("-", np.zeros((0, 10)))
    fs = result.windows[0].leads[0].fs
    t = np.linspace(-0.30, -0.06, segs.shape[1]) if len(segs) else np.array([])
    for ax in axes:
        ecg_paper(ax, -0.30, -0.06, -0.25, 0.3)
        ax.set_xticks([])
        ax.set_yticks([])
    for s in segs:
        axes[0].plot(t, s, color=ACCENT, lw=1.3, alpha=0.8)
    axes[0].set_title(L["p_left"].format(name=name), loc="left", fontsize=9.5, color=INK)
    ts, ys, rs = synthetic_strip("sinus", fs=int(fs))
    n0, n1 = int(-0.30 * fs), int(-0.06 * fs)
    rng = np.random.default_rng(1)
    for tr in rs[1:]:
        i = int(tr * fs)
        s = ys[i + n0:i + n1] + rng.normal(0, 0.01, n1 - n0)
        axes[1].plot(np.linspace(-0.30, -0.06, len(s)), s - s.mean(), color=REFERENCE, lw=1.3, alpha=0.8)
    axes[1].set_title(L["p_right"], loc="left", fontsize=9.5, color=INK)
    fig.tight_layout()
    return to_base64(fig)


def atrial_spectrum(result, lang="en"):
    L = LABELS[lang]
    f, p = result.spectrum_f, result.spectrum_p
    fig, ax = plt.subplots(figsize=(10, 3.2))
    m = (f >= 2) & (f <= 12)
    ax.axvspan(4.2, 5.8, color="#f3e3c2", zorder=0)
    ax.axvspan(5.8, 10, color="#d9e6f7", zorder=0)
    ax.text(5.0, 0.97, L["flutter_band"], transform=ax.get_xaxis_transform(), ha="center", va="top",
            fontsize=8.5, color=TEXT)
    ax.text(7.9, 0.97, L["af_band"], transform=ax.get_xaxis_transform(), ha="center", va="top",
            fontsize=8.5, color=TEXT)
    ax.plot(f[m], p[m] / p[m].max(), color=ACCENT, lw=2)
    fd = result.dominant_freq
    ax.plot([fd], [1.0], "o", ms=8, color=ACCENT, mec="white", mew=2)
    ax.annotate(L["peak"].format(hz=num(fd, 1, lang), pm=f"{fd * 60:.0f}"), (fd, 1.0),
                xytext=(12, -28), textcoords="offset points", fontsize=9, color=INK)
    ax.set_xlim(2, 12)
    ax.set_ylim(0, 1.12)
    ax.set_yticks([])
    ax.set_xlabel(L["freq_axis"])
    return to_base64(fig)
