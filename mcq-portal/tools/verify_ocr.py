"""Independent check: OCR the original book crop of every question and compare with parsed data.

Usage: verify_ocr.py [book ...]  -> work/verify_<book>.json
For each question: m1 = share of parsed tokens found in OCR, m2 = share of OCR tokens found
in parsed text, ans = OCR'd "Ans. (x)" letter (None if unreadable).
"""
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA, WORK = ROOT / "data", ROOT / "work"
PDFDIR = ROOT.parent
TOK = re.compile(r"[a-z0-9]+")
_pdf = {}


def render(book, segs, man, scale=3.0):
    from PIL import Image
    from pypdfium2 import PdfDocument

    if book not in _pdf:
        _pdf[book] = PdfDocument(str(PDFDIR / man["books"][book]))
    pdf = _pdf[book]
    parts = []
    for sg in segs:
        page = pdf[sg["page"] - 1]
        W, H = page.get_size()
        img = page.render(scale=scale).to_pil().convert("L")
        x0, x1 = (0.071 * W, 0.5 * W - 3) if sg["col"] == 0 else (0.5 * W + 3, 0.929 * W)
        parts.append(img.crop((int(x0 * scale), int(max(0, sg["top"] - 3) * scale), int(x1 * scale), int(min(H, sg["bottom"] + 4) * scale))))
    w = max(p.width for p in parts)
    out = Image.new("L", (w, sum(p.height for p in parts) + 6 * len(parts)), 255)
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height + 6
    return out


def ocr(img):
    import io

    b = io.BytesIO()
    img.save(b, "PNG")
    r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "6", "-l", "eng"], input=b.getvalue(), capture_output=True)
    return r.stdout.decode("utf8", "ignore")


def key(q):
    return hashlib.sha1(json.dumps([q["book"], q["fseg"]]).encode()).hexdigest()[:16]


def check(args):
    q, man = args
    return key(q), ocr(render(q["book"], q["fseg"], man))


def metrics(q, text):
    """m1/m2: agreement of whole block (stem+options+exam+answer+explanation) with the OCR text;
    q: share of stem+options tokens found in OCR; ans: OCR'd answer letter."""
    expl = "See the explanation of the above question." if q.get("ref") else q["expl"]
    parsed = " ".join([q["stem"]] + [o["text"] for o in q["options"]] + [q["exam"], "Ans.", q["answer"], expl])
    got, mine = Counter(TOK.findall(text.lower())), Counter(TOK.findall(parsed.lower()))
    inter = sum((got & mine).values())
    qm = Counter(TOK.findall(" ".join([q["stem"]] + [o["text"] for o in q["options"]]).lower()))
    am = re.search(r"Ans[\.\s]*[\(\[]?\s*([a-eA-E])\s*[\)\]]", text)
    return dict(m1=round(inter / max(1, sum(mine.values())), 3), m2=round(inter / max(1, sum(got.values())), 3),
                q=round(sum((got & qm).values()) / max(1, sum(qm.values())), 3), ans=am.group(1).lower() if am else None)


def main():
    man = json.loads((DATA / "manifest.json").read_text())
    books = sys.argv[1:] or [s["id"] for s in man["subjects"]]
    for b in books:
        sub = next(s for s in man["subjects"] if s["id"] == b)
        qs = [q for ch in sub["chapters"] for q in json.loads((DATA / "q" / f"{ch['id']}.json").read_text())]
        cache = WORK / f"ocr_{b}.json"
        texts = json.loads(cache.read_text()) if cache.exists() else {}
        todo = [q for q in qs if key(q) not in texts]
        with Pool(8) as p:
            texts.update(dict(p.map(check, [(q, man) for q in todo], chunksize=20)))
        cache.write_text(json.dumps(texts))
        res = {q["id"]: metrics(q, texts[key(q)]) for q in qs}
        (WORK / f"verify_{b}.json").write_text(json.dumps(res))
        bad = [k for k, v in res.items() if v["q"] < 0.9]
        print(b, len(qs), "checked;", len(bad), "text-suspicious;", sum(1 for q in qs if res[q["id"]]["ans"] and res[q["id"]]["ans"] != q["answer"]), "answer mismatches")


if __name__ == "__main__":
    main()
