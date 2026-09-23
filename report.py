"""Long-form HTML report: ECG basics and each analysis step explained in plain language (en / pl)."""
import datetime
import html
import os

import numpy as np

import charts
import texts
from texts import num

CSS = """
:root{--bg:#f7f6f3;--card:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8883;--line:#e4e2dc;
--accent:#2a78d6;--warn-bg:#fff4e5;--warn-ink:#8a4b00;--ok-bg:#e9f6ec;--ok-ink:#1d6b32;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141413;--card:#1f1f1d;--ink:#f4f3ee;
--ink2:#c3c2b7;--muted:#9a988f;--line:#34332f;--accent:#3987e5;--warn-bg:#3a2a12;--warn-ink:#ffcf8a;
--ok-bg:#16301d;--ok-ink:#9fe0b0;}}
:root[data-theme="dark"]{--bg:#141413;--card:#1f1f1d;--ink:#f4f3ee;--ink2:#c3c2b7;--muted:#9a988f;--line:#34332f;
--accent:#3987e5;--warn-bg:#3a2a12;--warn-ink:#ffcf8a;--ok-bg:#16301d;--ok-ink:#9fe0b0;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:980px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:1.9rem;margin:0 0 4px}
h2{font-size:1.35rem;margin:48px 0 8px;padding-top:8px;border-top:1px solid var(--line)}
h3{font-size:1.05rem;margin:24px 0 6px}
p,li{color:var(--ink2);max-width:75ch}
.sub{color:var(--muted);margin:0 0 24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin:16px 0}
.warning{background:var(--warn-bg);color:var(--warn-ink);border-radius:12px;padding:14px 18px;margin:16px 0}
.warning p{color:inherit;margin:0}
.verdict{display:flex;gap:16px;align-items:flex-start}
.icon{font-size:2rem;line-height:1;width:48px;height:48px;border-radius:50%;display:grid;place-items:center;
background:var(--warn-bg);color:var(--warn-ink);flex:none}
.icon.ok{background:var(--ok-bg);color:var(--ok-ink)}
.verdict h3{margin:0 0 4px;font-size:1.25rem;color:var(--ink)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:16px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.tile .label{font-size:.85rem;color:var(--muted)}
.tile .value{font-size:1.6rem;font-weight:650;color:var(--ink)}
.tile .note{font-size:.85rem;color:var(--ink2)}
figure{margin:16px 0;background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px;overflow:hidden}
figure img{width:100%;height:auto;display:block}
figcaption{color:#52514e;font-size:.9rem;padding:8px 4px 0}
.meaning{border-left:3px solid var(--accent);padding:2px 0 2px 14px;margin:12px 0}
.meaning b{color:var(--ink)}
table{border-collapse:collapse;width:100%}
td{border-top:1px solid var(--line);padding:10px 8px;vertical-align:top;color:var(--ink2)}
td:first-child{font-weight:650;color:var(--ink);white-space:nowrap;width:1%}
.numbers td:first-child{white-space:normal;width:40%}
@media (max-width:600px){td:first-child{white-space:normal}}
"""

S = {
    "en": {
        "title": "ECG analysis report", "files": "Files", "generated": "generated",
        "warning": ("<b>This is an educational tool, not a diagnosis.</b> The program reads the chart from a photo "
                    "and computes simple indicators. It can be wrong. Diagnosis and treatment are decided by a doctor. "
                    "With shortness of breath, chest pain, fainting or a very fast heartbeat call 112 (or your local "
                    "emergency number)."),
        "t_rate": "Mean heart rate", "t_rate_n": "normal at rest is about 60–100/min",
        "t_irr": "Rhythm irregularity", "t_irr_n": "intervals from {a} s to {b} s",
        "t_p": "P waves", "t_p_n": "is the same “bump” before every beat",
        "t_f": "Baseline undulation",
        "h_basics": "1. Basics: how to read an ECG in 2 minutes",
        "basics_intro": ("An ECG records the electrical current that drives the heart. Every heartbeat draws the same "
                         "shape on the paper, made of three parts:"),
        "beat_caption": "One normal heartbeat (illustration).",
        "basics_list": ("<li><b>P</b> is a small bump: the atria (upper chambers) contract and push blood down.</li>"
                        "<li><b>QRS</b> is a tall spike: the ventricles contract and pump blood out. This is the actual "
                        "beat you feel as your pulse.</li>"
                        "<li><b>T</b> is a gentle bump: the ventricles rest before the next beat.</li>"),
        "af_intro": ("In <b>atrial fibrillation (AF)</b> the atria do not contract evenly but quiver chaotically "
                     "(300–600 times a minute). On an ECG this shows as two things: <b>the P bump disappears</b> "
                     "(the line undulates finely instead) and <b>the beats (QRS) come at irregular intervals</b>, "
                     "with no pattern."),
        "compare_caption": ("Top: even intervals and a P bump before every spike. Bottom: every interval is different, "
                            "no P bump, the line undulates. Both strips are generated examples, not the analyzed recording."),
        "h_glossary": "2. What the labels and symbols on the printout mean",
        "h_digit": "3. Step one: did the program read the chart correctly?",
        "digit_intro": ("The program finds the red grid on the scan, straightens a skewed photo, measures the grid "
                        "square and follows the black line. The blue line is what it read. If it matches the black one, "
                        "the numbers below make sense."),
        "digit_meta": "{file}: scan rotated by {angle}°, 1 mm = {px} pixels.",
        "h_rr": "4. Step two: does the heart beat evenly?",
        "rr_intro": ("The program found every beat (blue circles) and measured the interval to the next one. The orange "
                     "ticks at the bottom show where the beats would fall <b>if the heart beat perfectly evenly</b> at "
                     "the same average pace. The more the circles drift away from the ticks, the more irregular the rhythm."),
        "strip_caption": "Segment {i} (leads {leads}). Shown is the lead where the beats are clearest.",
        "h_rr_all": "All intervals side by side",
        "bars_caption": "Each bar is the interval between two beats. With an even rhythm the bars would be almost equally tall.",
        "n_rr": "Number of measured intervals", "minmax": "Shortest / longest interval",
        "cv": "Interval variability (CV)", "cv_n": "{v}%. A healthy resting rhythm is usually below 5–8%.",
        "nrmssd": "Mean change between consecutive beats (nRMSSD)", "nrmssd_n": "{v}%. Above about 10% is typical of fibrillation.",
        "large": "How often the next interval differed by more than 10%", "large_n": "{v}% of cases",
        "meaning": "What it means:",
        "irr_is": "rhythm irregularity is <b>{v}</b>.",
        "irr_high": "The intervals jump around with no pattern, short then long. This is the most important sign of atrial fibrillation.",
        "irr_low": "The intervals are fairly similar.",
        "irr_mod": "The intervals differ somewhat. This can be normal (e.g. with breathing) or a few extra beats.",
        "h_p": "5. Step three: is there a P wave before the beats?",
        "p_intro": ("The program cut out a short piece of the recording just before every beat and overlaid them. If "
                    "the atria work normally, every piece contains the same P bump, so the lines overlap (right chart). "
                    "In fibrillation the lines are random (no P, “f” waves instead)."),
        "p_result": ("the similarity of the pieces is {k} (1 = identical, 0 = completely different; usually above 0.6 in a "
                     "normal rhythm). Result: P waves <b>{v}</b>."),
        "h_f": "6. Step four: how fast does the line quiver between beats?",
        "f_intro": ("The program “erased” the beats (QRS and T) and checked how fast what remains undulates, i.e. the "
                    "work of the atria. In <b>flutter</b> the atria contract fast but regularly (about 250–350/min) and "
                    "the line looks like saw teeth. In <b>fibrillation</b> they quiver faster and chaotically "
                    "(about 350–600/min)."),
        "spectrum_caption": "The higher the curve, the more undulation at that speed.",
        "f_result": ("the strongest undulation is about <b>{pm} times a minute</b> ({hz}/s) and its “orderliness” is {oi} "
                     "(0 = chaos, 1 = perfectly regular). Assessment: <b>{v}</b>. Note: this is the least certain part "
                     "of the analysis because the recording is short and the scan can distort small waves."),
        "h_next": "What next?",
        "next": ("<li>Show the recording (the original, not just this report) to a GP or a cardiologist.</li>"
                 "<li>If fibrillation is confirmed, the doctor will assess stroke risk (CHA₂DS₂-VASc score) and decide on "
                 "anticoagulants and rate or rhythm control. This matters because untreated fibrillation raises the "
                 "risk of stroke.</li><li>A longer recording (24 h Holter) or a current ECG for comparison often helps.</li>"),
        "h_limits": "Limitations of the program",
        "limits": ("<li>It analyzes only the few seconds printed on the paper. A doctor also assesses the QRS shape, the ST "
                   "segment and many other things the program does not check.</li>"
                   "<li>Reading from a photo is approximate. Thick lines, paper folds and faint print can distort the result.</li>"
                   "<li>The program is not a medical device and has not been clinically tested.</li>"),
    },
    "pl": {
        "title": "Raport z analizy EKG", "files": "Pliki", "generated": "wygenerowano",
        "warning": ("<b>To narzędzie edukacyjne, a nie diagnoza.</b> Program odczytuje wykres ze zdjęcia i liczy proste "
                    "wskaźniki. Może się pomylić. O rozpoznaniu i leczeniu decyduje lekarz. Przy duszności, bólu "
                    "w klatce piersiowej, omdleniu albo bardzo szybkim biciu serca dzwoń pod 112."),
        "t_rate": "Średnie tętno", "t_rate_n": "norma w spoczynku to ok. 60–100/min",
        "t_irr": "Nierówność rytmu", "t_irr_n": "odstępy od {a} s do {b} s",
        "t_p": "Załamki P", "t_p_n": "czy przed każdym uderzeniem jest ten sam „garb”",
        "t_f": "Falowanie linii",
        "h_basics": "1. Podstawy: jak czytać EKG w 2 minuty",
        "basics_intro": ("EKG to zapis prądu, który steruje sercem. Każde uderzenie serca rysuje na papierze ten sam "
                         "kształt, złożony z trzech części:"),
        "beat_caption": "Jedno prawidłowe uderzenie serca (rysunek poglądowy).",
        "basics_list": ("<li><b>P</b> to mały garb, czyli przedsionki (górne komory serca) się kurczą i „podają” krew niżej.</li>"
                        "<li><b>QRS</b> to wysoki szpic, czyli komory się kurczą i wypychają krew. To jest właściwe "
                        "uderzenie, które czujesz na tętnie.</li>"
                        "<li><b>T</b> to łagodny garb, czyli komory odpoczywają przed kolejnym uderzeniem.</li>"),
        "af_intro": ("<b>Migotanie przedsionków (AF)</b> polega na tym, że przedsionki zamiast kurczyć się równo, drgają "
                     "chaotycznie (300–600 razy na minutę). Na EKG widać wtedy dwie rzeczy: <b>znika garb P</b> (zamiast "
                     "niego linia drobno faluje) i <b>uderzenia (QRS) są w nierównych odstępach</b>, bez żadnego wzoru."),
        "compare_caption": ("Góra: równe odstępy i garb P przed każdym szpicem. Dół: odstępy za każdym razem inne, brak "
                            "garbu P, linia faluje. Oba paski są wygenerowane jako przykład, to nie jest analizowany zapis."),
        "h_glossary": "2. Co oznaczają napisy i symbole na wydruku",
        "h_digit": "3. Krok pierwszy: czy program dobrze odczytał wykres?",
        "digit_intro": ("Program szuka na skanie czerwonej siatki, prostuje przekrzywione zdjęcie, mierzy wielkość kratki "
                        "i idzie wzdłuż czarnej linii. Niebieska linia to to, co odczytał. Jeśli pokrywa się z czarną, "
                        "dalsze liczby mają sens."),
        "digit_meta": "{file}: skan obrócony o {angle}°, 1 mm = {px} piksela.",
        "h_rr": "4. Krok drugi: czy serce bije równo?",
        "rr_intro": ("Program znalazł każde uderzenie (niebieskie kółka) i zmierzył odstęp do następnego. Pomarańczowe "
                     "kreski na dole pokazują, gdzie wypadałyby uderzenia, <b>gdyby serce biło idealnie równo</b> w tym "
                     "samym średnim tempie. Im bardziej kółka rozjeżdżają się z kreskami, tym bardziej nierówny rytm."),
        "strip_caption": "Odcinek {i} (odprowadzenia {leads}). Pokazane to, na którym uderzenia widać najlepiej.",
        "h_rr_all": "Wszystkie odstępy obok siebie",
        "bars_caption": "Każdy słupek to odstęp między dwoma uderzeniami. Przy równym rytmie słupki miałyby prawie tę samą wysokość.",
        "n_rr": "Liczba zmierzonych odstępów", "minmax": "Najkrótszy / najdłuższy odstęp",
        "cv": "Zmienność odstępów (CV)", "cv_n": "{v}%. Przy zdrowym rytmie w spoczynku zwykle mniej niż 5–8%.",
        "nrmssd": "Średnia zmiana między kolejnymi uderzeniami (nRMSSD)", "nrmssd_n": "{v}%. Powyżej ok. 10% to sygnał typowy dla migotania.",
        "large": "Ile razy kolejny odstęp różnił się o ponad 10%", "large_n": "{v}% przypadków",
        "meaning": "Co to znaczy:",
        "irr_is": "nierówność rytmu jest <b>{v}</b>.",
        "irr_high": "Odstępy skaczą bez wzoru, raz krótki, raz długi. To najważniejszy znak migotania przedsionków.",
        "irr_low": "Odstępy są dość podobne.",
        "irr_mod": "Odstępy trochę się różnią. Może to być normalne (np. przy oddychaniu) albo pojedyncze dodatkowe pobudzenia.",
        "h_p": "5. Krok trzeci: czy przed uderzeniami jest załamek P?",
        "p_intro": ("Program wyciął krótki kawałek zapisu tuż przed każdym uderzeniem i nałożył je na siebie. Jeśli "
                    "przedsionki pracują prawidłowo, w każdym kawałku jest ten sam garb P, więc linie się pokrywają "
                    "(prawy wykres). Przy migotaniu linie są przypadkowe (brak P, zamiast tego fale „f”)."),
        "p_result": ("podobieństwo kawałków wynosi {k} (1 = identyczne, 0 = zupełnie różne; przy rytmie prawidłowym "
                     "zwykle powyżej 0,6). Wynik: załamki P <b>{v}</b>."),
        "h_f": "6. Krok czwarty: jak szybko drga linia między uderzeniami?",
        "f_intro": ("Program „wymazał” z zapisu uderzenia (QRS i T) i sprawdził, jak szybko faluje to, co zostało, czyli "
                    "praca przedsionków. Przy <b>trzepotaniu</b> przedsionki kurczą się szybko, ale regularnie (ok. "
                    "250–350/min), a linia wygląda jak zęby piły. Przy <b>migotaniu</b> drgają szybciej i chaotycznie "
                    "(ok. 350–600/min)."),
        "spectrum_caption": "Im wyższa krzywa, tym więcej falowania o danej prędkości.",
        "f_result": ("najsilniejsze falowanie to ok. <b>{pm} razy na minutę</b> ({hz}/s), a „porządek” falowania to {oi} "
                     "(0 = chaos, 1 = idealnie regularne). Ocena: <b>{v}</b>. Uwaga: to najmniej pewna część analizy, "
                     "bo zapis jest krótki, a skan może zniekształcać drobne fale."),
        "h_next": "Co dalej?",
        "next": ("<li>Pokaż ten zapis (oryginał, nie tylko ten raport) lekarzowi rodzinnemu albo kardiologowi.</li>"
                 "<li>Jeśli migotanie się potwierdzi, lekarz oceni ryzyko udaru (skala CHA₂DS₂-VASc) i zdecyduje o lekach "
                 "przeciwzakrzepowych oraz o kontroli rytmu lub tętna. To ważne, bo nieleczone migotanie zwiększa "
                 "ryzyko udaru.</li><li>Pomocny bywa dłuższy zapis (Holter 24 h) albo aktualne EKG do porównania.</li>"),
        "h_limits": "Ograniczenia programu",
        "limits": ("<li>Analizuje tylko kilkanaście sekund zapisu (tyle jest na wydruku). Lekarz ocenia też kształt QRS, "
                   "odcinek ST i wiele innych rzeczy, których program nie sprawdza.</li>"
                   "<li>Odczyt ze zdjęcia jest przybliżony. Grube linie, zagięcia papieru i słaby wydruk mogą zniekształcić wynik.</li>"
                   "<li>Program nie jest wyrobem medycznym i nie przeszedł badań klinicznych.</li>"),
    },
}


def _figure(b64, caption=""):
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return f'<figure><img alt="{html.escape(caption)}" src="data:image/png;base64,{b64}">{cap}</figure>'


def _tile(label, value, note):
    return (f'<div class="tile"><div class="label">{label}</div><div class="value">{value}</div>'
            f'<div class="note">{note}</div></div>')


def generate(printouts, result, path, lang="en"):
    s, r = S[lang], result
    icon, title, desc = texts.CONCLUSIONS[r.conclusion][lang]
    irregularity = texts.IRREGULARITY[lang][r.irregularity]
    p_waves = texts.P_WAVES[lang][r.p_waves]
    waves = texts.ATRIAL_WAVES[lang][r.atrial_waves]
    fd = r.dominant_freq
    rr_min, rr_max = r.rr.min(), r.rr.max()
    n = lambda x, d=2: num(x, d, lang)

    out = []
    add = out.append
    add(f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{s['title']}</title>
<style>{CSS}</style></head><body><main>
<h1>{s['title']}</h1>
<p class="sub">{s['files']}: {", ".join(html.escape(os.path.basename(p.path)) for p in printouts)} ·
{s['generated']} {datetime.datetime.now():%Y-%m-%d %H:%M}</p>
<div class="warning"><p>{s['warning']}</p></div>
<div class="card"><div class="verdict"><div class="icon{' ok' if icon == '✓' else ''}">{icon}</div>
<div><h3>{title}</h3><p>{desc}</p></div></div>
<div class="tiles">
{_tile(s['t_rate'], f"{r.heart_rate:.0f}/min", s['t_rate_n'])}
{_tile(s['t_irr'], irregularity, s['t_irr_n'].format(a=n(rr_min), b=n(rr_max)))}
{_tile(s['t_p'], p_waves, s['t_p_n'])}
{_tile(s['t_f'], f"~{fd * 60:.0f}/min" if not np.isnan(fd) else "–", waves)}
</div></div>""")

    add(f"<h2>{s['h_basics']}</h2><p>{s['basics_intro']}</p>")
    add(_figure(charts.beat_diagram(lang), s["beat_caption"]))
    add(f"<ul>{s['basics_list']}</ul><p>{s['af_intro']}</p>")
    add(_figure(charts.rhythm_comparison(lang), s["compare_caption"]))

    add(f"<h2>{s['h_glossary']}</h2><div class='card'><table>")
    for term, meaning in texts.GLOSSARY[lang]:
        add(f"<tr><td>{term}</td><td>{meaning}</td></tr>")
    add("</table></div>")

    add(f"<h2>{s['h_digit']}</h2><p>{s['digit_intro']}</p>")
    for p in printouts:
        add(f"<p class='sub'>{s['digit_meta'].format(file=html.escape(os.path.basename(p.path)), angle=n(p.angle, 1), px=n(p.px_per_mm, 1))}</p>")
        for lead in [l for l in p.leads if l.name in ("II", "V1")] or p.leads[:1]:
            add(_figure(charts.digitization_overlay(p, lead, lang)))

    add(f"<h2>{s['h_rr']}</h2><p>{s['rr_intro']}</p>")
    for i, w in enumerate(r.windows):
        add(_figure(charts.strip_with_beats(w, lang), s["strip_caption"].format(i=i + 1, leads=w.name)))
    add(f"<h3>{s['h_rr_all']}</h3>")
    add(_figure(charts.rr_bars(r, lang), s["bars_caption"]))
    irr_note = {"high": s["irr_high"], "low": s["irr_low"]}.get(r.irregularity, s["irr_mod"])
    add(f"""<div class="card"><table class="numbers">
<tr><td>{s['n_rr']}</td><td>{len(r.rr)}</td></tr>
<tr><td>{s['minmax']}</td><td>{n(rr_min)} s ({60 / rr_min:.0f}/min) / {n(rr_max)} s ({60 / rr_max:.0f}/min)</td></tr>
<tr><td>{s['cv']}</td><td>{s['cv_n'].format(v=f"{r.cv * 100:.0f}")}</td></tr>
<tr><td>{s['nrmssd']}</td><td>{s['nrmssd_n'].format(v=f"{r.nrmssd * 100:.0f}")}</td></tr>
<tr><td>{s['large']}</td><td>{s['large_n'].format(v=f"{r.pct_large_changes:.0f}")}</td></tr>
</table></div>
<div class="meaning"><b>{s['meaning']}</b> {s['irr_is'].format(v=irregularity)} {irr_note}</div>""")

    add(f"<h2>{s['h_p']}</h2><p>{s['p_intro']}</p>")
    add(_figure(charts.p_wave_overlay(r, lang)))
    add(f"<div class='meaning'><b>{s['meaning']}</b> {s['p_result'].format(k=n(r.p_correlation), v=p_waves)}</div>")

    if r.spectrum_f is not None:
        add(f"<h2>{s['h_f']}</h2><p>{s['f_intro']}</p>")
        add(_figure(charts.atrial_spectrum(r, lang), s["spectrum_caption"]))
        add(f"<div class='meaning'><b>{s['meaning']}</b> "
            f"{s['f_result'].format(pm=f'{fd * 60:.0f}', hz=n(fd, 1), oi=n(r.organization_index), v=waves)}</div>")

    add(f"<h2>{s['h_next']}</h2><ul>{s['next']}</ul><h2>{s['h_limits']}</h2><ul>{s['limits']}</ul>")
    add("</main></body></html>")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
