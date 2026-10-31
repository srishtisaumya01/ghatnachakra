"""Stage 1: PDF -> per-page, per-column text lines with layout flags.

For every page we drop the diagonal watermark (rotated chars), the header banner and
the footer, split into the two text columns and emit lines carrying:
  text, x0, x1, top, bottom, bold (fraction), boxed (inside explanation box), page, col.
Usage: extract_lines.py <pdf> <out.json> [first_page last_page]
"""
import json
import sys
from multiprocessing import Pool

import pdfplumber

HEADER_BOTTOM = 61.0


def page_lines(args):
    pdf_path, pno = args
    with pdfplumber.open(pdf_path) as pdf:
        pg = pdf.pages[pno]
        W, H = pg.width, pg.height
        # footer rule: widest horizontal line in lower part of the page
        foot = H - 40
        for l in pg.lines:
            if abs(l["top"] - l["bottom"]) < 1 and (l["x1"] - l["x0"]) > 400 and l["top"] > H * 0.8:
                foot = min(foot, l["top"] - 1)
        # vertical box edges
        verts = [
            (l["x0"], l["top"], l["bottom"])
            for l in pg.lines
            if abs(l["x0"] - l["x1"]) < 1 and (l["bottom"] - l["top"]) > 2 and 0.06 * W < l["x0"] < 0.94 * W
        ]

        def keep(o):
            if o.get("object_type") != "char":
                return False
            m = o["matrix"]
            if abs(m[1]) > 1e-3 or abs(m[2]) > 1e-3:
                return False  # rotated watermark
            return HEADER_BOTTOM <= o["top"] and o["top"] < foot

        fp = pg.filter(keep)
        out = []
        mid = W / 2
        for col, (cx0, cx1) in enumerate(((0, mid), (mid, W))):
            sub = fp.crop((cx0, 0, cx1, H), strict=False)
            try:
                lines = sub.extract_text_lines(layout=False, strip=True, return_chars=True)
            except Exception:
                lines = []
            for ln in lines:
                chars = [c for c in ln["chars"] if c["text"].strip()]
                if not chars:
                    continue
                b0 = int("Bold" in chars[0]["fontname"] or "bold" in chars[0]["fontname"])
                bold = sum("Bold" in c["fontname"] or "bold" in c["fontname"] for c in chars) / len(chars)
                size = sum(c["size"] for c in chars) / len(chars)
                gap = max([b["x0"] - a["x1"] for a, b in zip(chars, chars[1:])] or [0])
                ymid = (ln["top"] + ln["bottom"]) / 2
                boxed = any(
                    cx0 <= vx <= cx1 and vt - 1 <= ymid <= vb + 1 for vx, vt, vb in verts
                )
                out.append(
                    dict(
                        text=ln["text"],
                        x0=round(ln["x0"], 1),
                        x1=round(ln["x1"], 1),
                        top=round(ln["top"], 1),
                        bottom=round(ln["bottom"], 1),
                        bold=round(bold, 2),
                        b0=b0,
                        gap=round(gap, 1),
                        size=round(size, 1),
                        boxed=boxed,
                        page=pno + 1,
                        col=col,
                    )
                )
        shapes = [
            (round(o["x0"], 1), round(o["top"], 1), round(o["x1"], 1), round(o["bottom"], 1))
            for o in (pg.images + pg.rects + pg.curves)
            if HEADER_BOTTOM <= o["top"] and o["top"] < foot
        ]
        return pno + 1, W, H, out, shapes


def main():
    pdf_path, out_path = sys.argv[1], sys.argv[2]
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
    lo = int(sys.argv[3]) - 1 if len(sys.argv) > 3 else 0
    hi = int(sys.argv[4]) if len(sys.argv) > 4 else n
    with Pool(8) as pool:
        res = pool.map(page_lines, [(pdf_path, i) for i in range(lo, hi)], chunksize=4)
    json.dump(res, open(out_path, "w"))
    print(out_path, len(res), "pages", sum(len(r[3]) for r in res), "lines")


if __name__ == "__main__":
    main()
