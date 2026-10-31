"""Stage 3: parsed books -> portal data (data/manifest.json, data/q/<chapter>.json, data/excluded.json).

Usage: build_data.py [book ...]     (default: all configured books)
Run from anywhere; paths are relative to mcq-portal/.
"""
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import parse_questions as P
import verify_ocr as V
from index_parse import parse_index

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
DATA = ROOT / "data"

BOOKS = {
    "polity": dict(name="Indian Polity & Governance", pdf="Preview_Indian_Polity_and_Governance_Part_4_2026_26118_C_E_Book.pdf", index=(3, 3), keep_groups=False),
    "history": dict(name="Indian History", pdf="Preview_Indian_History_Part_2_2026_26116_C_E_Book_Merged.pdf", index=(3, 4), keep_groups=True),
    "geography": dict(name="General Geography", pdf="Preview_General_Geography_Part_3_2026_26117_C_E_Book_combined.pdf", index=(3, 5), keep_groups=True, prefix_groups={"CA": "Indian Geography", "CB": "World Geography"}),
    "science": dict(name="General Science", pdf="Preview_General_Science_Part_7_2026_26121_C_E_Book_combined_1.pdf", index=(3, 3), keep_groups=True),
    "bpsc": dict(name="BPSC General Studies", pdf="Preview_BPSC_General_Studies_2026_2616_N_E_Book_2026.pdf", index=(3, 4), keep_groups=True),
}

# an issue in this set means the question cannot be graded / displayed reliably -> not used in tests
BLOCKING = ("ans_special", "ans_tail", "no_ans_line", "ambiguous_answer", "empty_stem", "ans_not_in_options", "labels_")
SEE_ABOVE = re.compile(r"^see (the )?explanation (of |for )?(the )?(above|previous|preceding)( question)?\.?$", re.I)


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def qhash(q):
    key = norm(q["stem"]) + "|" + "|".join(sorted(norm(o["text"]) for o in q["options"]))
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def label_key(lab):
    return (lab[0], lab[1]) if lab else None


OCR_Q_MIN = 0.90      # stem+options tokens found in the OCR of the original crop
OCR_FULL_MIN = 0.85   # whole block (incl. explanation) agreement, both directions


def load_verify(key):
    """OCR texts of the original crops, keyed by crop hash (independent of question ids)."""
    f = WORK / f"ocr_{key}.json"
    return json.loads(f.read_text()) if f.exists() else {}


_CORPUS = None
WORD = re.compile(r"[a-z]{4,}")


def corpus():
    """Word frequencies over the OCR of ALL original crops: a real word appears here, a glued or
    mis-joined artefact of text extraction (e.g. 'thefol') does not."""
    global _CORPUS
    if _CORPUS is None:
        from collections import Counter

        _CORPUS = Counter()
        for f in WORK.glob("ocr_*.json"):
            for t in json.loads(f.read_text()).values():
                _CORPUS.update(WORD.findall(t.lower()))
    return _CORPUS


def options_in_order(opts, ocr_text):
    """Option texts must appear in the OCR of the original in label order (a<b<c<d)."""
    al = re.sub(r"[^a-z0-9]", "", ocr_text.lower())
    last = -1
    for o in opts:
        t = re.sub(r"[^a-z0-9]", "", o["text"].lower())
        if len(t) < 3:
            continue
        pos = al.find(t, last + 1)
        if pos < 0:
            if t in al:  # present but earlier than a previous option -> out of order
                return False
            continue  # not found at all (OCR noise): other checks cover it
        last = pos
    return True


def odd_words(text, own_ocr):
    own = set(WORD.findall(own_ocr.lower()))
    c = corpus()
    return [w for w in WORD.findall(text.lower()) if w not in own and c[w] < 2]


def build_book(key, cfg):
    verify = load_verify(key)
    flat, meta = P.load_lines(str(WORK / "lines" / f"{key}.json"))
    qs, chs, rej, orph = P.parse(flat, meta)
    pages = json.load(open(WORK / "lines" / f"{key}.json"))
    labels = {int(k): v for k, v in json.load(open(WORK / "labels" / f"{key}.json")).items()}
    if key == "bpsc":
        import bpsc_index

        entries = bpsc_index.entries()
    else:
        entries = parse_index(pages, *cfg["index"])
    entries.sort(key=lambda e: (e["start"][0], e["start"][1]))
    report = dict(book=key, parsed=len(qs), sections=len(chs), orphan_ans=len(orph), rejected=len(rej), dup_pages=meta["dup_pages"], index_entries=len(entries))

    def label_at(page):
        for p in range(page, 0, -1):
            if labels.get(p):
                return tuple(labels[p])
        return ("", 0)

    # section -> index entry via printed page label of its first question
    starts = [c["start_q"] for c in chs] + [len(qs)]
    sec_entry = []
    for si in range(len(chs)):
        first = qs[starts[si]]
        lab = label_at(first["page"])
        idx = None
        for ei, e in enumerate(entries):
            if e["start"] <= lab:
                idx = ei
        sec_entry.append(idx)
    report["section_entry"] = sec_entry
    mono = all(a is None or b is None or a <= b for a, b in zip(sec_entry, sec_entry[1:]))
    report["monotonic"] = mono

    by_entry = defaultdict(list)
    for si in range(len(chs)):
        by_entry[sec_entry[si]].extend(qs[starts[si]:starts[si + 1]])

    excluded, chapters = [], []
    DATA.joinpath("q").mkdir(parents=True, exist_ok=True)
    for ei in sorted(k for k in by_entry if k is not None):
        e = entries[ei]
        cid = f"{key}-{ei:03d}"
        out, seen, last_expl = [], {}, ""
        for seq, q in enumerate(by_entry[ei], 1):
            if any(i in ("options_unparsed", "no_options", "empty_option") for i in q["issues"]):
                # option text could not be split reliably: show the printed original, grade by letter
                q["reasons"] = sorted(set(q["reasons"]) | {"options_unparsed"})
                q["options"] = [dict(label=l, text="") for l in "abcd"]
                q["issues"] = [i for i in q["issues"] if i not in ("options_unparsed", "no_options", "empty_option")]
            blocking = [i for i in q["issues"] if i.startswith(BLOCKING)]
            expl = q["explanation"]
            is_ref = bool(SEE_ABOVE.match(expl.strip()))
            if is_ref:
                expl = last_expl
            else:
                last_expl = expl
            if blocking:
                excluded.append(dict(book=key, chapter=e["title"], num=q["num"], page=q["page"], reasons=blocking, stem=q["stem"][:90]))
                continue
            rec = dict(
                id=f"{cid}-{seq}", n=q["num"], book=key, stem=q["stem"], options=q["options"],
                answer=q["answer"], exam=q["exams"], expl=expl,
                view="image" if q["reasons"] else "text", ref=is_ref, **({"rimg": True} if q.get("expl_amb") and not is_ref else {}),
                qseg=q["qsegments"], fseg=q["segments"],
            )
            ocr_text = verify.get(V.key(rec))
            v = V.metrics(rec, ocr_text) if ocr_text is not None else None
            if v:
                if v["ans"] and v["ans"] != rec["answer"]:
                    excluded.append(dict(book=key, chapter=e["title"], num=q["num"], page=q["page"], reasons=["ocr_ans_mismatch"], stem=q["stem"][:90]))
                    continue
                if v["q"] < OCR_Q_MIN or not options_in_order(rec["options"], ocr_text) or odd_words(" ".join([rec["stem"]] + [o["text"] for o in rec["options"]]), ocr_text):
                    rec["view"] = "image"
                if not rec["ref"] and odd_words(rec["expl"], ocr_text):
                    rec["rimg"] = True
                if min(v["m1"], v["m2"]) < OCR_FULL_MIN:
                    rec["rimg"] = True
            h = qhash(q)
            if h in seen and seen[h]["answer"] == rec["answer"]:
                if rec["exam"] and rec["exam"] not in seen[h]["exam"]:
                    seen[h]["exam"] += " | " + rec["exam"]
                continue
            seen[h] = rec
            rec["h"] = h
            out.append(rec)
        if not out:
            continue
        DATA.joinpath("q", f"{cid}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
        grp = e["group"] if cfg["keep_groups"] else ""
        if cfg.get("prefix_groups"):
            grp = "Economic Geography" if e["group"] == "Economic Geography" else cfg["prefix_groups"].get(e["start"][0], grp)
        chapters.append(dict(id=cid, title=e["title"], group=grp, count=len(out)))
    unmapped = by_entry.get(None, [])
    report["unmapped_questions"] = len(unmapped)
    report["kept"] = sum(c["count"] for c in chapters)
    report["verified"] = bool(verify)
    report["excluded"] = len(excluded)
    return dict(id=key, name=cfg["name"], chapters=chapters), excluded, report


def main():
    keys = sys.argv[1:] or list(BOOKS)
    man_path = DATA / "manifest.json"
    man = json.loads(man_path.read_text()) if man_path.exists() else dict(books={}, subjects=[])
    exc_path = DATA / "excluded.json"
    exc = json.loads(exc_path.read_text()) if exc_path.exists() else []
    for k in keys:
        subj, excluded, rep = build_book(k, BOOKS[k])
        man["books"][k] = BOOKS[k]["pdf"]
        man["subjects"] = [s for s in man["subjects"] if s["id"] != k] + [subj]
        exc = [e for e in exc if e["book"] != k] + excluded
        print(json.dumps({x: rep[x] for x in rep if x != "section_entry"}))
    order = list(BOOKS)
    man["subjects"].sort(key=lambda s: order.index(s["id"]))
    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=1))
    exc_path.write_text(json.dumps(exc, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
