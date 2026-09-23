"""
paper-ecg-explainer - educational tool that explains a scanned paper ECG in plain language.
NOT a medical device.

Usage:
    uv run ecg_explain.py scan_limb.jpg scan_chest.jpg
    uv run ecg_explain.py scan.jpg --leads "I,II,III,aVR,aVL,aVF" --lang pl -o results

By default a 3-row x 2-column printout (e.g. AsCARD) is assumed:
  first file  -> I, II, III | aVR, aVL, aVF
  second file -> V1, V2, V3 | V4, V5, V6
"""
import argparse
import os
import shutil
import subprocess
import sys
import webbrowser

import report
import texts
import viewer
from analysis import analyze
from digitize import digitize

DEFAULT_LEADS = [
    "I,II,III,aVR,aVL,aVF",
    "V1,V2,V3,V4,V5,V6",
]

BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "msedge", "google-chrome", "chromium", "chromium-browser", "chrome",
]

CONSOLE = {
    "en": {"reading": "Reading {f} ...", "analyzing": "Analyzing the rhythm ...", "pdf": "Rendering the print PDF ...",
           "rate": "Mean heart rate", "irr": "Rhythm irregularity", "p": "P waves", "f": "Atrial waves",
           "result": "Result", "viewer": "Interactive viewer", "report": "Report", "print": "Print (PDF)",
           "no_pdf": "No PDF (Edge/Chrome not found) - use the Print button in the viewer.",
           "disclaimer": "Educational tool - not a substitute for a doctor's assessment."},
    "pl": {"reading": "Odczytuję {f} ...", "analyzing": "Analizuję rytm ...", "pdf": "Przygotowuję PDF do druku ...",
           "rate": "Średnie tętno", "irr": "Nierówność rytmu", "p": "Załamki P", "f": "Falowanie linii",
           "result": "Wniosek", "viewer": "Przeglądarka", "report": "Raport", "print": "Do druku (PDF)",
           "no_pdf": "PDF nie powstał (brak Edge/Chrome) - drukuj przyciskiem Drukuj w przeglądarce.",
           "disclaimer": "Narzędzie edukacyjne - nie zastępuje oceny lekarza."},
}


def save_pdf(html_path, pdf_path):
    """Print the viewer to PDF (A4 landscape) with a headless Edge/Chrome."""
    url = "file:///" + os.path.abspath(html_path).replace(os.sep, "/")
    for candidate in BROWSER_CANDIDATES:
        exe = candidate if os.path.isfile(candidate) else shutil.which(candidate)
        if not exe:
            continue
        try:
            subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            "--virtual-time-budget=5000", f"--print-to-pdf={os.path.abspath(pdf_path)}", url],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0:
            return True
    return False


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Explain a scanned paper ECG in plain language (educational, not a medical device).")
    ap.add_argument("files", nargs="+", help="ECG printout scans (jpg/png/webp) in recording order")
    ap.add_argument("--leads", action="append",
                    help='lead names for the next file, column by column from the top, e.g. "I,II,III,aVR,aVL,aVF"')
    ap.add_argument("--lang", choices=texts.LANGS, default="en",
                    help="language of the report, PDF and the viewer's default (the viewer can switch EN/PL)")
    ap.add_argument("-o", "--output", default=None, help="output folder (default: folder of the first scan)")
    ap.add_argument("--no-open", action="store_true", help="do not open the viewer in the browser")
    args = ap.parse_args()
    c = CONSOLE[args.lang]

    names = args.leads or []
    printouts = []
    for i, path in enumerate(args.files):
        leads = (names[i] if i < len(names) else DEFAULT_LEADS[i % len(DEFAULT_LEADS)]).split(",")
        if len(leads) != 6:
            sys.exit(f"{path}: give 6 lead names (3 rows x 2 columns).")
        print(c["reading"].format(f=path))
        printouts.append(digitize(path, [x.strip() for x in leads]))

    print(c["analyzing"])
    result = analyze(printouts)
    folder = args.output or os.path.dirname(os.path.abspath(args.files[0]))
    os.makedirs(folder, exist_ok=True)
    report_path = os.path.join(folder, "ecg_report.html")
    viewer_path = os.path.join(folder, "ecg_viewer.html")
    pdf_path = os.path.join(folder, "ecg_print.pdf")
    report.generate(printouts, result, report_path, args.lang)
    viewer.generate(printouts, result, viewer_path, args.lang, report_link="ecg_report.html")
    print(c["pdf"])
    pdf_ok = save_pdf(viewer_path, pdf_path)

    lang = args.lang
    print()
    print(f"  {c['rate']:<22}{result.heart_rate:.0f}/min")
    print(f"  {c['irr']:<22}{texts.IRREGULARITY[lang][result.irregularity]} "
          f"(nRMSSD {result.nrmssd * 100:.0f}%, CV {result.cv * 100:.0f}%)")
    print(f"  {c['p']:<22}{texts.P_WAVES[lang][result.p_waves]} ({texts.num(result.p_correlation, 2, lang)})")
    print(f"  {c['f']:<22}~{result.dominant_freq * 60:.0f}/min, {texts.ATRIAL_WAVES[lang][result.atrial_waves]}")
    print(f"  {c['result']:<22}{texts.CONCLUSIONS[result.conclusion][lang][1]}")
    print()
    print(f"{c['viewer']}: {viewer_path}")
    print(f"{c['report']}: {report_path}")
    print(f"{c['print']}: {pdf_path}" if pdf_ok else c["no_pdf"])
    print(c["disclaimer"])
    if not args.no_open:
        webbrowser.open("file:///" + os.path.abspath(viewer_path).replace(os.sep, "/"))


if __name__ == "__main__":
    main()
