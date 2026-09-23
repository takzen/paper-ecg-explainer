"""
Analizator EKG ze skanów wydruku - narzędzie edukacyjne (NIE jest wyrobem medycznym).

Użycie:
    python ekg_analiza.py skan1.webp skan2.webp
    python ekg_analiza.py skan1.webp --odprowadzenia "I,II,III,aVR,aVL,aVF" -o folder_wynikow

Domyślnie zakłada wydruk 3 wiersze x 2 kolumny (np. AsCARD):
  pierwszy plik  -> I, II, III | aVR, aVL, aVF
  drugi plik     -> V1, V2, V3 | V4, V5, V6
"""
import argparse
import os
import sys
import webbrowser

from analiza import analizuj
from digitalizacja import digitalizuj
import przegladarka
import raport

DOMYSLNE = [
    "I,II,III,aVR,aVL,aVF",
    "V1,V2,V3,V4,V5,V6",
]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Analiza rytmu serca ze zdjęcia/skanu EKG (edukacyjnie).")
    ap.add_argument("pliki", nargs="+", help="skany wydruku EKG (jpg/png/webp), w kolejności nagrania")
    ap.add_argument("--odprowadzenia", action="append",
                    help="nazwy odprowadzeń dla kolejnego pliku, kolumnami od góry, np. \"I,II,III,aVR,aVL,aVF\"")
    ap.add_argument("-o", "--wyjscie", default=None,
                    help="folder na wyniki (domyślnie folder pierwszego skanu)")
    ap.add_argument("--nie-otwieraj", action="store_true", help="nie otwieraj przeglądarki po analizie")
    args = ap.parse_args()

    nazwy = args.odprowadzenia or []
    wydruki = []
    for i, plik in enumerate(args.pliki):
        n = (nazwy[i] if i < len(nazwy) else DOMYSLNE[i % len(DOMYSLNE)]).split(",")
        if len(n) != 6:
            sys.exit(f"Plik {plik}: podaj 6 nazw odprowadzeń (3 wiersze x 2 kolumny).")
        print(f"Odczytuję {plik} ...")
        wydruki.append(digitalizuj(plik, [x.strip() for x in n]))

    print("Analizuję rytm ...")
    wynik = analizuj(wydruki)
    folder = args.wyjscie or os.path.dirname(os.path.abspath(args.pliki[0]))
    os.makedirs(folder, exist_ok=True)
    sciezka_raportu = os.path.join(folder, "raport_ekg.html")
    sciezka_przegladarki = os.path.join(folder, "przegladarka_ekg.html")
    raport.generuj(wydruki, wynik, sciezka_raportu)
    przegladarka.generuj(wydruki, wynik, sciezka_przegladarki, link_raportu="raport_ekg.html")

    print()
    print(f"  Średnie tętno:        {wynik.tetno:.0f}/min")
    print(f"  Nierówność rytmu:     {wynik.ocena_niemiarowosci} (nRMSSD {wynik.nrmssd * 100:.0f}%, CV {wynik.cv * 100:.0f}%)")
    print(f"  Załamki P:            {wynik.p_ocena} (podobieństwo {wynik.p_korelacja:.2f})")
    print(f"  Falowanie linii:      ~{wynik.czestotliwosc_dominujaca * 60:.0f}/min, {wynik.ocena_fal}")
    print(f"  Wniosek:              {raport.WNIOSKI[wynik.wniosek][1]}")
    print()
    print(f"Przeglądarka wykresu: {sciezka_przegladarki}")
    print(f"Raport z objaśnieniami: {sciezka_raportu}")
    print("To narzędzie edukacyjne - nie zastępuje oceny lekarza.")
    if not args.nie_otwieraj:
        webbrowser.open("file:///" + sciezka_przegladarki.replace(os.sep, "/"))


if __name__ == "__main__":
    main()
