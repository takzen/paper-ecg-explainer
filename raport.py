"""Raport HTML - wszystko opisane prostym językiem, dla osoby, która nie zna EKG."""
import datetime
import html
import os

import numpy as np

import wykresy

WNIOSKI = {
    "migotanie": ("⚠", "Zapis wygląda na migotanie przedsionków",
                  "Serce bije nierówno, bez stałego rytmu, a przed uderzeniami nie widać powtarzalnych "
                  "załamków P. Tak zwykle wygląda migotanie przedsionków."),
    "trzepotanie": ("⚠", "Zapis wygląda na trzepotanie przedsionków (albo migotanie)",
                    "Serce bije nierówno, a linia między uderzeniami faluje dość regularnie. Pasuje to do "
                    "trzepotania przedsionków ze zmiennym przewodzeniem. Migotania nie da się wykluczyć."),
    "zatokowy": ("✓", "Zapis wygląda na rytm prawidłowy (zatokowy)",
                 "Odstępy między uderzeniami są podobne, a przed każdym uderzeniem jest podobny załamek P."),
    "niejednoznaczny": ("?", "Wynik niejednoznaczny",
                        "Program nie potrafi jednoznacznie ocenić rytmu. Pokaż zapis lekarzowi."),
}

SLOWNIK = [
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
    ("35/50/0.75 Hz", "Filtry w aparacie. 35 Hz tłumi drżenie mięśni, 50 Hz tłumi zakłócenia z sieci elektrycznej, "
                      "0,75 Hz tłumi powolne falowanie linii przy oddychaniu."),
    ("Godz / Data", "Godzina i data wykonania tego fragmentu zapisu."),
    ("AsCARD Red3", "Model aparatu EKG."),
    ("P", "Mały garb przed uderzeniem, czyli skurcz przedsionków. Przy migotaniu go <b>nie ma</b>, "
          "zamiast niego linia drobno faluje (fale „f”)."),
    ("QRS", "Wysoki, ostry szpic, czyli skurcz komór. Każdy QRS to jedno uderzenie serca (to, co czujesz na tętnie)."),
    ("T", "Łagodny garb po uderzeniu, czyli komory „odpoczywają” przed kolejnym skurczem."),
    ("RR", "Odstęp między dwoma kolejnymi uderzeniami (od szczytu do szczytu). Przy zdrowym rytmie odstępy są "
           "prawie równe, a przy migotaniu za każdym razem inne."),
]

STYL = """
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
.karta{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin:16px 0}
.ostrzezenie{background:var(--warn-bg);color:var(--warn-ink);border-radius:12px;padding:14px 18px;margin:16px 0}
.ostrzezenie p{color:inherit;margin:0}
.werdykt{display:flex;gap:16px;align-items:flex-start}
.ikona{font-size:2rem;line-height:1;width:48px;height:48px;border-radius:50%;display:grid;place-items:center;
background:var(--warn-bg);color:var(--warn-ink);flex:none}
.ikona.ok{background:var(--ok-bg);color:var(--ok-ink)}
.werdykt h3{margin:0 0 4px;font-size:1.25rem;color:var(--ink)}
.kafle{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:16px}
.kafel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.kafel .etyk{font-size:.85rem;color:var(--muted)}
.kafel .wart{font-size:1.6rem;font-weight:650;color:var(--ink)}
.kafel .opis{font-size:.85rem;color:var(--ink2)}
figure{margin:16px 0;background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px;overflow:hidden}
figure img{width:100%;height:auto;display:block}
figcaption{color:#52514e;font-size:.9rem;padding:8px 4px 0}
.co{border-left:3px solid var(--accent);padding:2px 0 2px 14px;margin:12px 0}
.co b{color:var(--ink)}
table{border-collapse:collapse;width:100%}
td{border-top:1px solid var(--line);padding:10px 8px;vertical-align:top;color:var(--ink2)}
td:first-child{font-weight:650;color:var(--ink);white-space:nowrap;width:1%}
.liczby td:first-child{white-space:normal;width:40%}
@media (max-width:600px){td:first-child{white-space:normal}}
"""


def _fig(b64, podpis=""):
    p = f"<figcaption>{podpis}</figcaption>" if podpis else ""
    return f'<figure><img alt="{html.escape(podpis)}" src="data:image/png;base64,{b64}">{p}</figure>'


def _kafel(etyk, wart, opis):
    return f'<div class="kafel"><div class="etyk">{etyk}</div><div class="wart">{wart}</div><div class="opis">{opis}</div></div>'


def generuj(wydruki, wynik, sciezka):
    ikona, tytul, opis = WNIOSKI[wynik.wniosek]
    w = wynik
    fd = w.czestotliwosc_dominujaca
    min_rr, max_rr = w.rr.min(), w.rr.max()

    czesci = []
    add = czesci.append
    add(f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Raport EKG</title>
<style>{STYL}</style></head><body><main>
<h1>Raport z analizy EKG</h1>
<p class="sub">Pliki: {", ".join(html.escape(os.path.basename(x.plik)) for x in wydruki)} ·
wygenerowano {datetime.datetime.now():%d.%m.%Y %H:%M}</p>
<div class="ostrzezenie"><p><b>To narzędzie edukacyjne, a nie diagnoza.</b> Program odczytuje wykres ze zdjęcia
i liczy proste wskaźniki. Może się pomylić. O rozpoznaniu i leczeniu decyduje lekarz. Przy duszności, bólu
w klatce piersiowej, omdleniu albo bardzo szybkim biciu serca dzwoń pod 112.</p></div>

<div class="karta"><div class="werdykt"><div class="ikona{' ok' if ikona == '✓' else ''}">{ikona}</div>
<div><h3>{tytul}</h3><p>{opis}</p></div></div>
<div class="kafle">
{_kafel("Średnie tętno", f"{w.tetno:.0f}/min", "norma w spoczynku to ok. 60–100/min")}
{_kafel("Nierówność rytmu", w.ocena_niemiarowosci, f"odstępy od {min_rr:.2f} s do {max_rr:.2f} s")}
{_kafel("Załamki P", w.p_ocena, "czy przed każdym uderzeniem jest ten sam „garb”")}
{_kafel("Falowanie linii", f"~{fd * 60:.0f}/min" if not np.isnan(fd) else "–", w.ocena_fal)}
</div></div>
""")

    add("""<h2>1. Podstawy: jak czytać EKG w 2 minuty</h2>
<p>EKG to zapis prądu, który steruje sercem. Każde uderzenie serca rysuje na papierze ten sam kształt,
złożony z trzech części:</p>""")
    add(_fig(wykresy.schemat_uderzenia(), "Jedno prawidłowe uderzenie serca (rysunek poglądowy)."))
    add("""<ul>
<li><b>P</b> to mały garb, czyli przedsionki (górne komory serca) się kurczą i „podają” krew niżej.</li>
<li><b>QRS</b> to wysoki szpic, czyli komory się kurczą i wypychają krew. To jest właściwe uderzenie,
które czujesz na tętnie.</li>
<li><b>T</b> to łagodny garb, czyli komory odpoczywają przed kolejnym uderzeniem.</li>
</ul>
<p><b>Migotanie przedsionków (AF)</b> polega na tym, że przedsionki zamiast kurczyć się równo, drgają chaotycznie
(300–600 razy na minutę). Na EKG widać wtedy dwie rzeczy: <b>znika garb P</b> (zamiast niego linia drobno
faluje) i <b>uderzenia (QRS) są w nierównych odstępach</b>, bez żadnego wzoru.</p>""")
    add(_fig(wykresy.porownanie_rytmow(),
             "Góra: równe odstępy i garb P przed każdym szpicem. Dół: odstępy za każdym razem inne, "
             "brak garbu P, linia faluje. Oba paski są wygenerowane jako przykład, to nie jest Twój zapis."))

    add("<h2>2. Co oznaczają napisy i symbole na wydruku</h2><div class='karta'><table>")
    for k, v in SLOWNIK:
        add(f"<tr><td>{k}</td><td>{v}</td></tr>")
    add("</table></div>")

    add("""<h2>3. Krok pierwszy: czy program dobrze odczytał wykres?</h2>
<p>Program szuka na skanie czerwonej siatki, prostuje przekrzywione zdjęcie, mierzy wielkość kratki i idzie
wzdłuż czarnej linii. Niebieska linia to to, co odczytał. Jeśli pokrywa się z czarną, dalsze liczby mają sens.</p>""")
    for wd in wydruki:
        add(f"<p class='sub'>{html.escape(os.path.basename(wd.plik))}: skan obrócony o {wd.kat:+.1f}°, "
            f"1 mm = {wd.px_na_mm:.1f} piksela.</p>")
        pokaz = [o for o in wd.odprowadzenia if o.nazwa in ("II", "V1")] or wd.odprowadzenia[:1]
        for o in pokaz:
            add(_fig(wykresy.nakladka_odczytu(wd, o)))

    add(f"""<h2>4. Krok drugi: czy serce bije równo?</h2>
<p>Program znalazł każde uderzenie (niebieskie kółka) i zmierzył odstęp do następnego. Pomarańczowe kreski
na dole pokazują, gdzie wypadałyby uderzenia, <b>gdyby serce biło idealnie równo</b> w tym samym średnim tempie.
Im bardziej kółka rozjeżdżają się z kreskami, tym bardziej nierówny rytm.</p>""")
    for i, okno in enumerate(w.okna):
        add(_fig(wykresy.pasek_z_uderzeniami(okno),
                 f"Odcinek {i + 1} (odprowadzenia {okno.nazwa}). Pokazane to, na którym uderzenia widać najlepiej."))
    add("<h3>Wszystkie odstępy obok siebie</h3>")
    add(_fig(wykresy.tachogram(w),
             "Każdy słupek to odstęp między dwoma uderzeniami. Przy równym rytmie słupki miałyby prawie "
             "tę samą wysokość."))
    add(f"""<div class="karta"><table class="liczby">
<tr><td>Liczba zmierzonych odstępów</td><td>{len(w.rr)}</td></tr>
<tr><td>Najkrótszy / najdłuższy odstęp</td><td>{min_rr:.2f} s ({60 / min_rr:.0f}/min) / {max_rr:.2f} s ({60 / max_rr:.0f}/min)</td></tr>
<tr><td>Zmienność odstępów (CV)</td><td>{w.cv * 100:.0f}%. Przy zdrowym rytmie w spoczynku zwykle mniej niż 5–8%.</td></tr>
<tr><td>Średnia zmiana między kolejnymi uderzeniami (nRMSSD)</td><td>{w.nrmssd * 100:.0f}%. Powyżej ok. 10% to sygnał
typowy dla migotania.</td></tr>
<tr><td>Ile razy kolejny odstęp różnił się o ponad 10%</td><td>{w.proc_duzych_zmian:.0f}% przypadków</td></tr>
</table></div>
<div class="co"><b>Co to znaczy:</b> nierówność rytmu jest <b>{w.ocena_niemiarowosci}</b>.
{"Odstępy skaczą bez wzoru, raz krótki, raz długi. To najważniejszy znak migotania przedsionków."
 if w.ocena_niemiarowosci == "wysoka" else
 "Odstępy są dość podobne." if w.ocena_niemiarowosci == "niska" else
 "Odstępy trochę się różnią. Może to być normalne (np. przy oddychaniu) albo pojedyncze dodatkowe pobudzenia."}</div>
""")

    add(f"""<h2>5. Krok trzeci: czy przed uderzeniami jest załamek P?</h2>
<p>Program wyciął krótki kawałek zapisu tuż przed każdym uderzeniem i nałożył je na siebie. Jeśli przedsionki
pracują prawidłowo, w każdym kawałku jest ten sam garb P, więc linie się pokrywają (prawy wykres).
Przy migotaniu linie są przypadkowe (brak P, zamiast tego fale „f”).</p>""")
    add(_fig(wykresy.zalamki_p(w)))
    add(f"""<div class="co"><b>Co to znaczy:</b> podobieństwo kawałków wynosi {w.p_korelacja:.2f}
(1 = identyczne, 0 = zupełnie różne; przy rytmie prawidłowym zwykle powyżej 0,6).
Wynik: <b>{w.p_ocena}</b> załamki P.</div>""")

    if w.widmo_f is not None:
        add(f"""<h2>6. Krok czwarty: jak szybko drga linia między uderzeniami?</h2>
<p>Program „wymazał” z zapisu uderzenia (QRS i T) i sprawdził, jak szybko faluje to, co zostało, czyli
praca przedsionków. Przy <b>trzepotaniu</b> przedsionki kurczą się szybko, ale regularnie (ok. 250–350/min),
a linia wygląda jak zęby piły. Przy <b>migotaniu</b> drgają szybciej i chaotycznie (ok. 350–600/min).</p>""")
        add(_fig(wykresy.widmo(w), "Im wyższa krzywa, tym więcej falowania o danej prędkości."))
        add(f"""<div class="co"><b>Co to znaczy:</b> najsilniejsze falowanie to ok. <b>{fd * 60:.0f} razy na minutę</b>
({fd:.1f}/s), a „porządek” falowania to {w.indeks_organizacji:.2f} (0 = chaos, 1 = idealnie regularne).
Ocena: <b>{w.ocena_fal}</b>. Uwaga: to najmniej pewna część analizy, bo zapis jest krótki,
a skan może zniekształcać drobne fale.</div>""")

    add("""<h2>Co dalej?</h2>
<ul>
<li>Pokaż ten zapis (oryginał, nie tylko ten raport) lekarzowi rodzinnemu albo kardiologowi.</li>
<li>Jeśli migotanie się potwierdzi, lekarz oceni ryzyko udaru (skala CHA₂DS₂-VASc) i zdecyduje o lekach
przeciwzakrzepowych oraz o kontroli rytmu lub tętna. To ważne, bo nieleczone migotanie zwiększa ryzyko udaru.</li>
<li>Pomocny bywa dłuższy zapis (Holter 24 h) albo aktualne EKG do porównania.</li>
</ul>
<h2>Ograniczenia programu</h2>
<ul>
<li>Analizuje tylko kilkanaście sekund zapisu (tyle jest na wydruku). Lekarz ocenia też kształt QRS, odcinek ST
i wiele innych rzeczy, których program nie sprawdza.</li>
<li>Odczyt ze zdjęcia jest przybliżony. Grube linie, zagięcia papieru i słaby wydruk mogą zniekształcić wynik.</li>
<li>Program nie jest wyrobem medycznym i nie przeszedł badań klinicznych.</li>
</ul>
</main></body></html>""")

    with open(sciezka, "w", encoding="utf-8") as f:
        f.write("\n".join(czesci))
