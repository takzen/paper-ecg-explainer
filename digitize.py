"""
Read ECG traces from a scan or photo of a paper printout.

Steps:
  1. detect the red grid and straighten a skewed scan,
  2. measure the small grid square (1 mm) -> convert pixels to seconds and millivolts,
  3. split the printout into columns (time segments) and rows (leads),
  4. follow the dark trace of every lead column by column.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image
from scipy import signal as sps

MM_PER_SECOND = 25.0  # standard paper speed
MM_PER_MV = 10.0      # standard gain


@dataclass
class Lead:
    name: str
    column: int             # 0 = left half of the printout, 1 = right half
    t: np.ndarray           # time [s] from the start of the column
    mv: np.ndarray          # voltage [mV], baseline removed
    fs: float               # "sampling rate" = pixels per second
    x_px: np.ndarray        # sample positions in the image (for overlays)
    y_px: np.ndarray
    box: tuple              # (x0, y0, x1, y1) image crop containing this lead
    x_zero: float = 0.0     # pixel where the column time starts
    y_zero: float = 0.0     # pixel corresponding to 0 mV (before baseline removal)
    px_per_mv: float = 118.0


@dataclass
class Printout:
    path: str
    image: np.ndarray       # deskewed RGB image
    angle: float            # rotation applied to the scan [deg]
    px_per_mm: float
    fs: float
    leads: list = field(default_factory=list)


def _trace_mask(rgb, threshold=150):
    """Dark/grey trace pixels (the grid is red, so it is excluded).
    threshold=150 - clear trace; threshold=200 - also faint parts of steep strokes."""
    a = rgb.astype(np.int16)
    r, g = a[..., 0], a[..., 1]
    return ((a.max(2) < threshold) & ((r - g) < 45)).astype(np.uint8)


def _grid_mask(rgb):
    a = rgb.astype(np.int16)
    r, g = a[..., 0], a[..., 1]
    return ((r > 150) & ((r - g) > 55)).astype(np.uint8)


def _paper_box(grid):
    rows = np.where(grid.mean(1) > 0.05)[0]
    cols = np.where(grid.mean(0) > 0.05)[0]
    return cols[0], rows[0], cols[-1], rows[-1]


def _skew_angle(grid):
    """Angle at which the horizontal grid lines are sharpest when projected onto the Y axis."""
    x0, y0, x1, y1 = _paper_box(grid)
    m = cv2.resize(grid[y0:y1, x0:x1].astype(np.float32), None, fx=0.5, fy=0.5)
    h, w = m.shape
    best, best_score = 0.0, -1.0
    for angle in np.arange(-3.0, 3.01, 0.1):
        rot = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        rotated = cv2.warpAffine(m, rot, (w, h))
        sharpness = np.var(np.diff(rotated.sum(1)))
        if sharpness > best_score:
            best, best_score = angle, sharpness
    return float(best)


def _grid_pitch(profile):
    """Small grid square (1 mm) in pixels, from the autocorrelation of the grid profile."""
    p = profile - profile.mean()
    ac = np.correlate(p, p, mode="full")[len(p) - 1:]
    ac /= ac[0]
    lag1 = 6 + int(np.argmax(ac[6:25]))
    # refine on the large square (5 mm), which is 5x longer
    lo, hi = 5 * lag1 - 6, 5 * lag1 + 7
    lag5 = lo + int(np.argmax(ac[lo:hi]))
    return lag5 / 5.0


def _column_split(trace, x0, x1, bands):
    """Boundary between columns: the narrowest spot in the middle of the printout with no trace in the lead bands."""
    prof = sum(trace[ya:yb, x0:x1].sum(0).astype(float) for ya, yb in bands)
    prof = np.convolve(prof, np.ones(9) / 9, mode="same")
    w = x1 - x0
    a, b = int(w * 0.35), int(w * 0.65)
    return x0 + a + int(np.argmin(prof[a:b]))


def _lead_rows(trace, xa, xb, y0, y1, count):
    """Find baseline levels: rows through which the trace runs across almost the full width."""
    band = cv2.dilate(trace[y0:y1, xa:xb], np.ones((51, 1), np.uint8))
    coverage = band.mean(1)
    density = np.convolve(trace[y0:y1, xa:xb].sum(1).astype(float), np.ones(15) / 15, mode="same")
    peaks, _ = sps.find_peaks(density, distance=150)
    peaks = [p for p in peaks if coverage[p] > 0.6]
    # take the first `count` rows from the top (printed text sits below the traces)
    return [y0 + p for p in sorted(peaks)[:count]]


def _follow_trace(strong, faint, xa, xb, ya, yb, y_start):
    """Walk column by column and pick the trace segment closest to the previous one.
    Faint pixels (only in the `faint` mask) are accepted only when they touch the previous
    segment, so the tracker does not jump onto stamps or text showing through the paper."""
    n = xb - xa
    y_out = np.full(n, np.nan)
    previous = None
    history = []

    def segments(mask, x):
        idx = np.flatnonzero(mask[ya:yb, x])
        if idx.size == 0:
            return []
        return [(s[0] + ya, s[-1] + ya) for s in np.split(idx, np.flatnonzero(np.diff(idx) > 2) + 1)]

    def dist(s, ref):
        if s[1] < ref[0]:
            return ref[0] - s[1]
        if s[0] > ref[1]:
            return s[0] - ref[1]
        return 0

    for i, x in enumerate(range(xa, xb)):
        ref = previous or (y_start - 40, y_start + 40)
        candidates = [(dist(s, ref), s) for s in segments(strong, x)]
        candidates = [c for c in candidates if c[0] <= (60 if previous else 0)]
        if previous:
            candidates += [(dist(s, ref), s) for s in segments(faint, x) if dist(s, ref) <= 3]
        if not candidates:
            previous = None if (history and i - history[-1][0] > 15) else previous
            continue
        a, b = min(candidates)[1]
        baseline = np.median([h[1] for h in history[-150:]]) if history else y_start
        if b - a > 8:  # vertical stroke (e.g. a QRS complex) -> take the end farther from the baseline
            y = a if abs(a - baseline) > abs(b - baseline) else b
        else:
            y = (a + b) / 2
        y_out[i] = y
        history.append((i, (a + b) / 2))
        previous = (a, b)
    return y_out


def _trace_extent(y, max_gap=12, min_len=80):
    """Extent of the actual trace: joins pieces separated by small gaps and drops
    short pieces at the edges (labels such as 'II', 'aVR', 'V4')."""
    ok = np.flatnonzero(~np.isnan(y))
    if ok.size == 0:
        return 0, 0
    gaps = np.flatnonzero(np.diff(ok) > max_gap)
    pieces = [(p[0], p[-1] + 1) for p in np.split(ok, gaps + 1)]
    while len(pieces) > 1 and pieces[0][1] - pieces[0][0] < min_len:
        pieces.pop(0)
    while len(pieces) > 1 and pieces[-1][1] - pieces[-1][0] < min_len:
        pieces.pop()
    return pieces[0][0], pieces[-1][1]


def _calibration_pulse_end(mv, fs):
    """The rectangle at the start of a trace (1 mV for ~0.1 s) is the scale reference, not the heart - cut it off."""
    window = mv[: int(0.4 * fs)]
    high = np.abs(window - np.median(mv)) > 0.7
    n_min = int(0.04 * fs)
    i = 0
    while i < len(high):
        if high[i]:
            j = i
            while j < len(high) and high[j]:
                j += 1
            if j - i >= n_min:
                return min(len(mv) - 1, j + int(0.04 * fs))
            i = j
        i += 1
    return 0


def _remove_baseline(x, fs):
    """Remove slow baseline wander (breathing, movement) with two median filters."""
    k1 = int(0.2 * fs) | 1
    k2 = int(0.6 * fs) | 1
    baseline = sps.medfilt(sps.medfilt(x, k1), k2)
    return x - baseline


def digitize(path, lead_names, rows=3, columns=2):
    rgb = np.asarray(Image.open(path).convert("RGB"))

    angle = _skew_angle(_grid_mask(rgb))
    h, w = rgb.shape[:2]
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rgb = cv2.warpAffine(rgb, rot, (w, h), borderValue=(255, 255, 255))

    grid = _grid_mask(rgb)
    trace = _trace_mask(rgb)
    trace_faint = _trace_mask(rgb, threshold=200)
    x0, y0, x1, y1 = _paper_box(grid)

    paper = grid[y0:y1, x0:x1].astype(float)
    px_per_mm = (_grid_pitch(paper.sum(0)) + _grid_pitch(paper.sum(1))) / 2
    fs = px_per_mm * MM_PER_SECOND
    px_per_mv = px_per_mm * MM_PER_MV

    printout = Printout(path=path, image=rgb, angle=angle, px_per_mm=px_per_mm, fs=fs)

    baselines = _lead_rows(trace, x0, x1, y0, y1, rows)
    spacing = np.median(np.diff(baselines)) if len(baselines) > 1 else 300
    bands = [(int(yc - spacing * 0.3), int(yc + spacing * 0.3)) for yc in baselines]
    bounds = [x0]
    if columns == 2:
        bounds.append(_column_split(trace, x0, x1, bands))
    bounds.append(x1)

    for k in range(columns):
        xa, xb = bounds[k], bounds[k + 1]
        for r, yc in enumerate(baselines):
            name = lead_names[k * rows + r]
            ya = int(max(y0, yc - spacing * 0.5))
            yb = int(min(y1, yc + spacing * 0.5))
            y = _follow_trace(trace, trace_faint, xa, xb, ya, yb, yc)
            a, b = _trace_extent(y)
            y = y[a:b]
            xs = np.arange(xa + a, xa + b)
            ok = ~np.isnan(y)
            y = np.interp(np.arange(len(y)), np.flatnonzero(ok), y[ok])
            mv = -(y - np.median(y)) / px_per_mv
            cut = _calibration_pulse_end(mv, fs)
            y, xs, mv = y[cut:], xs[cut:], mv[cut:]
            mv = _remove_baseline(mv, fs)
            t = (xs - bounds[k]) / fs
            box = (int(xs[0]) - 20, ya, int(xs[-1]) + 20, yb)
            printout.leads.append(
                Lead(name, k, t, mv, fs, xs, y, box,
                     x_zero=float(bounds[k]), y_zero=float(np.median(y)), px_per_mv=px_per_mv))
    return printout
