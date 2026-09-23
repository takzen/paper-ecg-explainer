"""
All user-facing wording, in English and Polish.

The target audience cannot read an ECG, so every text explains things in plain language.
Functions that describe an anomaly return {"title": {lang: str}, "text": {lang: str}} so the
interactive viewer can switch languages without re-running the analysis.
"""

LANGS = ("en", "pl")


def num(x, digits=2, lang="en"):
    """Language-aware decimal separator: 0.62 (en) / 0,62 (pl)."""
    s = f"{x:.{digits}f}"
    return s.replace(".", ",") if lang == "pl" else s


def _both(fn):
    """Build a {lang: text} dict by calling fn(lang, n) for every language."""
    return {lang: fn(lang, lambda x, d=2: num(x, d, lang)) for lang in LANGS}


# conclusion code -> {lang: (icon, title, description)}
CONCLUSIONS = {
    "af": {
        "en": ("⚠", "The recording looks like atrial fibrillation",
               "The heart beats irregularly, with no steady rhythm, and there are no repeatable P waves "
               "before the beats. This is what atrial fibrillation typically looks like."),
        "pl": ("⚠", "Zapis wygląda na migotanie przedsionków",
               "Serce bije nierówno, bez stałego rytmu, a przed uderzeniami nie widać powtarzalnych "
               "załamków P. Tak zwykle wygląda migotanie przedsionków."),
    },
    "flutter": {
        "en": ("⚠", "The recording looks like atrial flutter (or fibrillation)",
               "The heart beats irregularly and the line between beats undulates fairly regularly. This fits "
               "atrial flutter with variable conduction. Fibrillation cannot be ruled out."),
        "pl": ("⚠", "Zapis wygląda na trzepotanie przedsionków (albo migotanie)",
               "Serce bije nierówno, a linia między uderzeniami faluje dość regularnie. Pasuje to do "
               "trzepotania przedsionków ze zmiennym przewodzeniem. Migotania nie da się wykluczyć."),
    },
    "sinus": {
        "en": ("✓", "The recording looks like a normal (sinus) rhythm",
               "The intervals between beats are similar and each beat is preceded by a similar P wave."),
        "pl": ("✓", "Zapis wygląda na rytm prawidłowy (zatokowy)",
               "Odstępy między uderzeniami są podobne, a przed każdym uderzeniem jest podobny załamek P."),
    },
    "unclear": {
        "en": ("?", "Inconclusive result",
               "The program cannot clearly assess the rhythm. Show the recording to a doctor."),
        "pl": ("?", "Wynik niejednoznaczny",
               "Program nie potrafi jednoznacznie ocenić rytmu. Pokaż zapis lekarzowi."),
    },
}

IRREGULARITY = {
    "en": {"high": "high", "moderate": "moderate", "low": "low"},
    "pl": {"high": "wysoka", "moderate": "umiarkowana", "low": "niska"},
}
P_WAVES = {
    "en": {"repeatable": "repeatable", "absent": "none repeatable", "uncertain": "uncertain"},
    "pl": {"repeatable": "powtarzalne", "absent": "brak powtarzalnych", "uncertain": "niepewne"},
}
ATRIAL_WAVES = {
    "en": {"fibrillation": "irregular/fast (as in fibrillation)", "flutter": "regular (as in flutter)",
           "ambiguous": "ambiguous", "no_data": "no data"},
    "pl": {"fibrillation": "nieregularne/szybkie (jak w migotaniu)", "flutter": "regularne (jak w trzepotaniu)",
           "ambiguous": "niejednoznaczne", "no_data": "brak danych"},
}

GLOSSARY = {
    "en": [
        ("I, II, III", "Limb leads. Electrodes on the arms and a leg “look” at the heart from different angles "
                       "at the front of the body. <b>II</b> looks from below and shows the atria best."),
        ("aVR, aVL, aVF", "Also limb leads, just computed differently. <b>aVR</b> looks from the right shoulder, so "
                          "everything appears “upside down” (that is normal). <b>aVL</b> from the left shoulder, "
                          "<b>aVF</b> from below (like II and III)."),
        ("V1 – V6", "Chest leads. Electrodes stuck on the chest, from the breastbone (V1) to the left side (V6). "
                    "<b>V1</b> is closest to the atria."),
        ("25 mm/s", "Paper speed. 1 small square (1 mm) = 0.04 s, 1 large square (5 mm) = 0.2 s, "
                    "5 large squares = 1 second."),
        ("10 mm/mV", "Gain. 10 small squares up = 1 millivolt. That is the height of the rectangle at the start."),
        ("Rectangle ⊓ at the start", "Calibration pulse, the scale reference (1 mV). It is not a heartbeat."),
        ("35/50/0.75 Hz", "Machine filters. 35 Hz reduces muscle tremor, 50 Hz reduces mains interference, "
                          "0.75 Hz reduces the slow baseline wander caused by breathing."),
        ("Time / Date", "When this part of the recording was taken (on Polish machines: “Godz” / “Data”)."),
        ("P", "Small bump before a beat: the atria contract. In fibrillation it is <b>missing</b> and the line "
              "undulates finely instead (“f” waves)."),
        ("QRS", "Tall, sharp spike: the ventricles contract. Every QRS is one heartbeat (what you feel as your pulse)."),
        ("T", "Gentle bump after a beat: the ventricles “rest” before the next contraction."),
        ("RR", "Interval between two consecutive beats (peak to peak). In a healthy rhythm the intervals are "
               "almost equal; in fibrillation they differ every time."),
    ],
    "pl": [
        ("I, II, III", "Odprowadzenia kończynowe. Elektrody na rękach i nodze „patrzą” na serce z różnych stron "
                       "z przodu ciała. <b>II</b> patrzy od dołu i najlepiej pokazuje przedsionki."),
        ("aVR, aVL, aVF", "Też odprowadzenia kończynowe, tylko liczone inaczej. <b>aVR</b> patrzy z prawego barku, "
                          "więc wszystko ma „do góry nogami” (to normalne). <b>aVL</b> z lewego barku, "
                          "<b>aVF</b> od dołu (podobnie jak II i III)."),
        ("V1 – V6", "Odprowadzenia przedsercowe. Elektrody przyklejone na klatce piersiowej, od mostka (V1) "
                    "po lewy bok (V6). <b>V1</b> leży najbliżej przedsionków."),
        ("25 mm/s", "Prędkość przesuwu papieru. 1 mała kratka (1 mm) = 0,04 s, 1 duża kratka (5 mm) = 0,2 s, "
                    "5 dużych kratek = 1 sekunda."),
        ("10 mm/mV", "Wzmocnienie. 10 małych kratek w górę = 1 miliwolt. Tyle wysokości ma prostokąt na początku zapisu."),
        ("Prostokąt ⊓ na początku", "Impuls kalibracyjny, czyli wzorzec skali (1 mV). To nie jest bicie serca."),
        ("35/50/0.75 Hz", "Filtry w aparacie. 35 Hz tłumi drżenie mięśni, 50 Hz tłumi zakłócenia z sieci "
                          "elektrycznej, 0,75 Hz tłumi powolne falowanie linii przy oddychaniu."),
        ("Godz / Data", "Godzina i data wykonania tego fragmentu zapisu."),
        ("P", "Mały garb przed uderzeniem, czyli skurcz przedsionków. Przy migotaniu go <b>nie ma</b>, "
              "zamiast niego linia drobno faluje (fale „f”)."),
        ("QRS", "Wysoki, ostry szpic, czyli skurcz komór. Każdy QRS to jedno uderzenie serca (to, co czujesz na tętnie)."),
        ("T", "Łagodny garb po uderzeniu, czyli komory „odpoczywają” przed kolejnym skurczem."),
        ("RR", "Odstęp między dwoma kolejnymi uderzeniami (od szczytu do szczytu). Przy zdrowym rytmie odstępy są "
               "prawie równe, a przy migotaniu za każdym razem inne."),
    ],
}


# ---------- anomaly descriptions ----------

def anomaly_rate(hr):
    return {
        "title": _both(lambda l, n: {"en": f"Fast heart rate: {hr:.0f}/min on average",
                                     "pl": f"Szybkie tętno: średnio {hr:.0f}/min"}[l]),
        "text": _both(lambda l, n: {
            "en": (f"At rest the heart should beat about 60–100 times a minute. Here it averages {hr:.0f}/min. "
                   "In fibrillation the ventricles often beat too fast because they receive too many impulses "
                   "from the atria."),
            "pl": (f"W spoczynku serce powinno bić ok. 60–100 razy na minutę. Tu średnio {hr:.0f}/min. "
                   "Przy migotaniu komory często biją za szybko, bo dostają z przedsionków zbyt wiele impulsów."),
        }[l]),
    }


def anomaly_irregular(rr_prev, rr):
    change = rr - rr_prev
    return {
        "title": _both(lambda l, n: {"en": f"Irregular interval: {n(rr)} s after {n(rr_prev)} s",
                                     "pl": f"Nierówny odstęp: {n(rr)} s po {n(rr_prev)} s"}[l]),
        "text": _both(lambda l, n: {
            "en": (f"This beat came {n(abs(change))} s {'earlier' if change < 0 else 'later'} than the previous "
                   f"interval would suggest ({n(rr_prev)} s → {n(rr)} s, i.e. {60 / rr_prev:.0f}/min → "
                   f"{60 / rr:.0f}/min). A healthy heart at rest beats almost like a metronome. Jumps like this, "
                   "one way and then the other, are the main sign of atrial fibrillation."),
            "pl": (f"To uderzenie przyszło o {n(abs(change))} s {'wcześniej' if change < 0 else 'później'}, niż "
                   f"wynikałoby z poprzedniego odstępu ({n(rr_prev)} s → {n(rr)} s, czyli {60 / rr_prev:.0f}/min → "
                   f"{60 / rr:.0f}/min). Zdrowe serce w spoczynku bije prawie jak metronom. Takie skoki raz "
                   "w jedną, raz w drugą stronę to główny znak migotania przedsionków."),
        }[l]),
    }


def anomaly_short(rr):
    return {
        "title": _both(lambda l, n: {"en": f"Very short interval: {n(rr)} s ({60 / rr:.0f}/min)",
                                     "pl": f"Bardzo krótki odstęp: {n(rr)} s ({60 / rr:.0f}/min)"}[l]),
        "text": _both(lambda l, n: {
            "en": (f"Only {n(rr)} s passed between these two beats. If the heart beat like this all the time, "
                   f"the heart rate would be {60 / rr:.0f}/min."),
            "pl": (f"Między tymi dwoma uderzeniami minęło tylko {n(rr)} s. Gdyby serce tak biło cały czas, "
                   f"tętno wynosiłoby {60 / rr:.0f}/min."),
        }[l]),
    }


def anomaly_pause(rr, mean_rr):
    return {
        "title": _both(lambda l, n: {"en": f"Longer pause: {n(rr)} s", "pl": f"Dłuższa przerwa: {n(rr)} s"}[l]),
        "text": _both(lambda l, n: {"en": f"The interval is 50% longer than the average ({n(mean_rr)} s).",
                                    "pl": f"Odstęp jest o połowę dłuższy niż średnia ({n(mean_rr)} s)."}[l]),
    }


def anomaly_no_p(window):
    return {
        "title": _both(lambda l, n: {"en": f"No P waves (segment {window + 1})",
                                     "pl": f"Brak załamków P (odcinek {window + 1})"}[l]),
        "text": _both(lambda l, n: {
            "en": ("The hatched areas are the spots just before each beat where a healthy rhythm shows a small P "
                   "wave that looks the same every time. Here no beat is preceded by a repeatable bump. The atria "
                   "are not contracting normally."),
            "pl": ("Zakreskowane pola to miejsca tuż przed każdym uderzeniem, gdzie przy zdrowym rytmie widać "
                   "mały, zawsze taki sam garb P. Tu przed żadnym uderzeniem nie ma powtarzalnego garbu. "
                   "Przedsionki nie kurczą się normalnie."),
        }[l]),
    }


def anomaly_f_waves(lead, rate):
    return {
        "title": _both(lambda l, n: {"en": f"f waves in {lead}: about {rate:.0f}/min",
                                     "pl": f"Fale f w {lead}: ok. {rate:.0f}/min"}[l]),
        "text": _both(lambda l, n: {
            "en": (f"The pink triangles mark small waves between the beats (about {rate:.0f} per minute). These "
                   "are the atria quivering very fast instead of contracting once. In flutter the waves are "
                   "even (about 250–350/min), in fibrillation faster and irregular."),
            "pl": (f"Różowe trójkąciki pokazują drobne fale między uderzeniami (ok. {rate:.0f} na minutę). "
                   "To przedsionki, które zamiast jednego skurczu drgają bardzo szybko. "
                   "Przy trzepotaniu fale są równe (ok. 250–350/min), przy migotaniu szybsze i nieregularne."),
        }[l]),
    }
