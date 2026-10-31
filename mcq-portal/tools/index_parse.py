"""Parse a book's printed INDEX (chapter title + page range) from the stage-1 lines JSON.

parse_index(pages, lo, hi) -> [ {title, group, start:(prefix,num), end:(prefix,num)} ]
`pages` is the list loaded from <book>.json, lo..hi are 1-based pdf pages of the index.
"""
import re

RANGE = re.compile(
    r"^(?P<title>.*?)\s*(?:(?P<p1>[A-Z]{1,3})\s*[–\-−]?\s*)?(?P<a>\d{1,3})\s*[-–−]\s*(?:(?P<p2>[A-Z]{1,3})\s*[–\-−]?\s*)?(?P<b>\d{1,3})\s*$"
)
MARK = re.compile(r"^(\d{1,3}\s*\.|\([ivxIVX]+\)|[a-z]\s*\.|[IVX]+\s*\.|[lq•▪]\s)")
SKIP = re.compile(r"^(Chapter\s+Page No\.?|INDEX|Page No\.?|\(\d+(st|nd|rd|th) in \d+ Part Series\))", re.I)


def clean(t):
    t = re.sub(r"^(\d{1,3}\s*\.|\([ivxIVX]+\)|[a-z]\s*\.|[IVX]+\s*\.|[lq•▪])\s*", "", t.strip())
    return re.sub(r"\s+", " ", t).strip(" :-")


def parse_index(pages, lo, hi):
    lines = []
    for pno, W, H, ls, *_ in pages:
        if lo <= pno <= hi:
            for l in sorted(ls, key=lambda l: (l["col"], l["top"])):
                lines.append(l)
    entries, group, last, last_l = [], "", None, None
    for l in lines:
        t = l["text"].strip()
        if not t or SKIP.match(t):
            continue
        m = RANGE.match(t)
        if m and m.group("title"):
            p1 = m.group("p1") or ""
            p2 = m.group("p2") or p1
            last = dict(title=clean(m.group("title")), group=clean(group), start=(p1, int(m.group("a"))), end=(p2, int(m.group("b"))))
            entries.append(last)
            last_l = l
            continue
        if MARK.match(t):
            group = t
            last = None
            continue
        if last is not None and l["col"] == last_l["col"] and l["x0"] > last_l["x0"] + 5 and l["top"] - last_l["bottom"] < 14:
            last["title"] = (last["title"] + " " + clean(t)).strip()
            last_l = l
    return entries
