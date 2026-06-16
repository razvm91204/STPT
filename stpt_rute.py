"""
Descarcă toate orărele STPT din PDF-uri de pe stpt.ro
Rulează: python descarca_stpt.py
PDF-urile se salvează în folderul ./stpt_orare/
"""

import urllib.request
import os
import time

BASE = "https://stpt.ro/grafice/"

PDFS = [
    # Tramvaie
    "1a", "1b",
    "2a", "2b",
    "4a", "4b",
    "5a", "5b",
    "6a-a", "6a-b",
    "6b-a", "6b-b",
    "7a", "7b",
    "8a", "8b",
    "9a", "9b",
    # Troleibuze
    "11a", "11b",
    "14a", "14b",
    "16a", "16b",
    "17a", "17b",
    "18a", "18b",
    # Autobuze urbane
    "5b-a", "5b-b",
    "13a", "13b",
    "15a", "15b",
    "21a", "21b",
    "24a", "24b",
    "28a", "28b",
    "32a", "32b",
    "33a", "33b",
    "33b-a", "33b-b",
    "40a", "40b",
    "46a", "46b",
    # Expres
    "e1a", "e1b",
    "e2a", "e2b",
    "e3a", "e3b",
    "e4a", "e4b",       # Linia E4
    "e4b-a", "e4b-b",   # Linia E4B
    "e6a", "e6b",
    "e7a", "e7b",
    "e8a", "e8b",
]

os.makedirs("stpt_orare", exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

ok, erori = [], []

for key in PDFS:
    url  = BASE + key + ".pdf"
    dest = os.path.join("stpt_orare", key + ".pdf")

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()

        if len(data) < 500:
            raise ValueError(f"Fișier prea mic ({len(data)} bytes) — probabil eroare")

        with open(dest, "wb") as f:
            f.write(data)

        print(f"  OK  {key}.pdf  ({len(data)//1024} KB)")
        ok.append(key)

    except Exception as e:
        print(f"  !!  {key}.pdf  -- {e}")
        erori.append((key, str(e)))

    time.sleep(0.3)

print(f"\nGata: {len(ok)} descarcate, {len(erori)} erori.")
if erori:
    print("Erori:")
    for k, msg in erori:
        print(f"  {k}: {msg}")
print(f"\nPDF-urile sunt in folderul: {os.path.abspath('stpt_orare')}")
print("Uploadeaza tot folderul (sau un zip) in chat.")
