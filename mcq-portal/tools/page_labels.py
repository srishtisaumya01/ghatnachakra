"""Read the printed page label from each PDF page footer -> {pdf_page: [prefix, number]}.

Usage: page_labels.py <pdf> <out.json>
Footers look like  "D–16", "CA–41", "B–40", "G–30" or "(20)".
"""
import json
import re
import sys
from multiprocessing import Pool

import pdfplumber

LAB = re.compile(r"(?<![A-Za-z])([A-Z]{1,3})\s*[–\-−]\s*(\d{1,3})(?!\d)")
PAR = re.compile(r"\((\d{1,3})\)")


def one(args):
    path, i = args
    with pdfplumber.open(path) as pdf:
        pg = pdf.pages[i]
        H = pg.height
        txt = pg.crop((0, H - 100, pg.width, H), strict=False).filter(
            lambda o: o.get("object_type") != "char" or (abs(o["matrix"][1]) < 1e-3 and abs(o["matrix"][2]) < 1e-3)
        ).extract_text() or ""
    m = LAB.findall(txt)
    if m:
        return i + 1, [m[-1][0], int(m[-1][1])]
    m = PAR.findall(txt)
    if m:
        return i + 1, ["", int(m[-1])]
    return i + 1, None


if __name__ == "__main__":
    path, out = sys.argv[1:3]
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
    with Pool(8) as p:
        res = p.map(one, [(path, i) for i in range(n)], chunksize=8)
    json.dump({str(k): v for k, v in res}, open(out, "w"))
    print(out, sum(1 for _, v in res if v), "of", n, "labelled")
