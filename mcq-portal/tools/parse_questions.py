"""Stage 2: line stream -> structured MCQs with strict validation.

Usage: parse_questions.py <lines.json> <book_key> <out.json>
Every question keeps `segments` (page/col/top/bottom) so the original book crop can be
rendered on demand, and `issues` (list of strings) for anything that is not 100% clean.
"""
import json
import re
import sys
from collections import Counter

QSTART = re.compile(r"^(\d{1,4})(?:\s*[\.,](?!\d)\s*|\s+)(\S.*)?$")
DOTTED = re.compile(r"^\d{1,4}\s*\.(?!\d)\s*(\S|$)")
ANS = re.compile(r"^(?:Ans\s*\.\s*|Ans(?:wer)?\s*[-–:]?\s*(?=\()|उत्तर\s*[-–:.]?\s*)(.*)$", re.I)
ANS_VAL = re.compile(r"^[\(\[]\s*([a-eA-E])\s*[\)\]]\s*(.*)$")
OPT_MARK = re.compile(r"\(([a-e])\)")
LISTISH = re.compile(r"^(\d+\s*[\.\)]|\(?[ivxIVX]+[\.\)]|[A-D]\s*[\.\)]|\([A-D1-9]\)|List|Code|Select|Assertion|Reason|Statement|Match|Consider|Which|Choose|Read|Note|Column)")
EXAM_TAG = re.compile(r"(19|20)\d\d|Pre|Mains|Exam|P\.?C\.?S|I\.A\.S|Re-", re.I)


def load_lines(path):
    pages = json.load(open(path))
    flat = []
    meta = {"dup_pages": [], "shapes": {}}
    prev = None
    for pno, W, H, ls, *rest in pages:
        meta["shapes"][pno] = rest[0] if rest else []
        meta["size"] = (W, H)
        key = tuple(l["text"] for l in ls)
        if ls and key == prev:
            meta["dup_pages"].append(pno)
            continue
        prev = key
        for l in sorted(ls, key=lambda l: (l["col"], l["top"], l["x0"])):
            flat.append(l)
    return flat, meta


def build_vocab(flat):
    c = Counter()
    for l in flat:
        for w in re.findall(r"[A-Za-z]+", l["text"]):
            c[w.lower()] += 1
    return c


class Joiner:
    """Joins wrapped lines. `amb` is set when a line-end hyphen could not be resolved with
    certainty (hyphenation vs real hyphen) -- such text is shown from the original image."""

    def __init__(self, vocab):
        self.v = vocab
        self.amb = False

    def join(self, texts, keep_breaks=False):
        self.amb = False
        out = ""
        for i, t in enumerate(texts):
            t = t.strip()
            if not t:
                continue
            if not out:
                out = t
                continue
            if out.endswith("-") and re.search(r"[A-Za-z]-$", out) and re.match(r"[A-Za-z]", t):
                m1 = re.search(r"([A-Za-z]+)-$", out)
                m2 = re.match(r"([A-Za-z]+)", t)
                merged = (m1.group(1) + m2.group(1)).lower()
                hyph = (m1.group(1) + "-" + m2.group(1)).lower()
                if t[0].islower() and self.v.get(merged, 0) >= 2 and self.v.get(merged, 0) > self.v.get(hyph, 0):
                    out = out[:-1] + t  # soft hyphenation: re-join the word
                    continue
                self.amb = True
                out = out + t  # keep the hyphen, no space
                continue
            if keep_breaks and LISTISH.match(t):
                out += "\n" + t
            else:
                out += " " + t
        return re.sub(r"[ \t]{2,}", " ", out).strip()


OPT_MARK2 = re.compile(r"(?<![\w\)\]])\(([a-e])\)")


def split_options(text):
    """Return (stem, [(label, text)], relabeled).

    Finds the last in-order run (a)(b)(c)(d)[(e)]. Markers glued to a word or a closing
    bracket such as 19(1)(a) are not option markers. If the book itself misprinted a
    label (e.g. (a)(b)(c)(c)) the four markers are relabelled by position and flagged.
    """
    marks = [(m.start(), m.end(), m.group(1)) for m in OPT_MARK2.finditer(text)]
    best, relabeled = None, False
    for i, (s, e, lab) in enumerate(marks):
        if lab != "a":
            continue
        run = [marks[i]]
        want = "b"
        for m in marks[i + 1:]:
            if m[2] == want:
                run.append(m)
                want = chr(ord(want) + 1)
            if want > "e":
                break
        if len(run) >= 4:
            best, relabeled = run, False
    dup = set()
    if best is None:
        for i, (s, e, lab) in enumerate(marks):
            if lab == "a" and len(marks) - i == 4:
                labs = [m[2] for m in marks[i:i + 4]]
                best = marks[i:i + 4]
                if sorted(labs) == ["a", "b", "c", "d"]:
                    relabeled = "swapped"
                else:
                    relabeled = "relabeled"
                    dup = {x for x in labs if labs.count(x) > 1}
                break
    if not best:
        return None, None, False
    stem = text[: best[0][0]].strip()
    opts = []
    for idx, (s, e, lab) in enumerate(best):
        end = best[idx + 1][0] if idx + 1 < len(best) else len(text)
        label = chr(ord("a") + idx) if relabeled == "relabeled" else lab
        opts.append((label, text[e:end].strip()))
    if relabeled == "swapped":
        opts.sort(key=lambda o: o[0])
    return stem, opts, (relabeled, dup) if relabeled else False


def parse(flat, meta):
    vocab = build_vocab(flat)
    J = Joiner(vocab)
    n = len(flat)
    xc = Counter()
    for l in flat:
        if not l["boxed"] and ANS.match(l["text"].strip()):
            xc[round(l["x0"])] += 1
    allowed = [x for x, c in xc.items() if c >= 15]
    if not allowed:
        raise SystemExit("no question margins found")
    questions = []
    chapters = []
    i = 0
    last = 0
    pre_lines = []
    cur_chapter = -1
    rejected = []
    consumed = []

    def is_start(j, ref):
        l = flat[j]
        if l["boxed"] or not l.get("b0", l["bold"] > 0.5):
            return None
        if not any(abs(l["x0"] - x) <= 2.5 for x in allowed):
            return None
        t = l["text"].strip()
        m = QSTART.match(t)
        if not m:
            return None
        if DOTTED.match(t) or (int(m.group(1)) == ref + 1 and m.group(2) and m.group(2)[0].isupper()):
            return int(m.group(1))
        return None

    def find_block(i, num):
        """(end_index, has_ans_line) of the question block starting at i, or None."""
        for j in range(i + 1, min(i + 70, n)):
            l = flat[j]
            if l["boxed"]:
                continue
            if ANS.match(l["text"].strip()):
                return j, True
            if is_start(j, num) is not None:
                # another question starts before any "Ans." line: only a real (answer-less)
                # question if it carries its own option list, otherwise it is theory text
                starts = {m.group(1) for k in range(i, j) if not flat[k]["boxed"] for m in [re.match(r"^\(([a-e])\)", flat[k]["text"].strip())] if m}
                has_tag = any(flat[k]["bold"] > 0.6 and re.search(r"(19|20)\d\d", flat[k]["text"]) and not flat[k]["text"].lstrip().startswith("(") for k in range(i + 1, j) if not flat[k]["boxed"])
                has_opts = {"a", "c"} <= starts and has_tag
                return (j - 1, False) if has_opts else None
        return None

    while i < n:
        l = flat[i]
        num = is_start(i, last)
        started = False
        misnum = False
        if num is not None:
            fb = find_block(i, num)
            if fb is not None:
                end, has_ans = fb
                if num == 1 or last < num <= last + 25:
                    started = True
                elif num <= last:
                    # identical duplicate pages are already removed, so this is a real question
                    # carrying a misprinted number (e.g. "3" printed twice): keep it, flagged
                    rejected.append((l["page"], num, last))
                    misnum = True
                    started = True
        if not started:
            if not l["boxed"]:
                pre_lines.append(l)
            i += 1
            continue

        new_chapter = num == 1 and (last >= 1 or cur_chapter < 0)
        if new_chapter:
            cur_chapter += 1
            chapters.append(dict(start_q=len(questions), pre_lines=pre_lines[-60:]))
            gap = False
        else:
            gap = num != last + 1
        pre_lines = []
        block = [flat[k] for k in range(i, end + 1) if not flat[k]["boxed"]]
        boxed_inside = [flat[k] for k in range(i, end + 1) if flat[k]["boxed"]]
        cur_expl = []
        if boxed_inside:
            if has_ans and questions:
                questions[-1]["_expl_lines"] += boxed_inside
            else:
                cur_expl = boxed_inside
        if has_ans:
            am = ANS.match(block[-1]["text"].strip())
            raw = (am.group(1) or "").strip()
            av = ANS_VAL.match(raw)
            if av:
                ans, ans_tail = av.group(1).lower(), av.group(2).strip()
            else:
                ans, ans_tail = "", ""
            body_lines = block[:-1]
        else:
            raw, ans, ans_tail = "", "", ""
            body_lines = block

        first = QSTART.match(body_lines[0]["text"].strip())
        body = [(body_lines[0], (first.group(2) or "").strip())] + [(b, b["text"].strip()) for b in body_lines[1:]]
        opt_start = None
        for idx, (b, tx) in enumerate(body):
            if re.match(r"^\(a\)", tx):
                opt_start = idx
        tags, stem_lines, opt_lines = [], [], []
        qobjs, stem_objs = [], []
        if opt_start is None:
            stem_lines = [tx for b, tx in body]
            qobjs = [b for b, tx in body]
            stem_objs = qobjs
        else:
            stem_lines = [tx for b, tx in body[:opt_start]]
            stem_objs = [b for b, tx in body[:opt_start]]
            qobjs = list(stem_objs)
            for b, tx in body[opt_start:]:
                if b["bold"] > 0.6 and not re.match(r"^\([a-e]\)", tx):
                    tags.append(tx)
                else:
                    opt_lines.append(tx)
                    qobjs.append(b)
        stem_raw = J.join(stem_lines, keep_breaks=True)
        amb = J.amb
        opt_raw = J.join(opt_lines)
        amb = amb or J.amb
        issues = []
        rl_dup = set()
        if opt_start is None:
            full = J.join([tx for b, tx in body])
            stem, opts, rl = split_options(full)
            if opts:
                stem_raw = stem
            else:
                opts = []
                issues.append("no_options")
        else:
            _, opts, rl = split_options(opt_raw)
            if rl:
                issues.append("label_typo_" + rl[0])
                rl_dup = rl[1]
            if opts is None:
                opts = []
                issues.append("options_unparsed")
        labels = [o[0] for o in opts]
        if opts and labels not in (["a", "b", "c", "d"], ["a", "b", "c", "d", "e"]):
            issues.append("labels_" + "".join(labels))
        if any(not o[1] for o in opts):
            issues.append("empty_option")
        if any(x.startswith("label_typo_relabeled") for x in issues) and ans in rl_dup:
            issues.append("ambiguous_answer")
        if not has_ans:
            issues.append("no_ans_line")
        elif not ans:
            issues.append("ans_special:" + raw[:20])
        elif ans not in labels and opts:
            issues.append("ans_not_in_options")
        if not stem_raw:
            issues.append("empty_stem")
        if misnum:
            issues.append("number_misprint")
        elif gap:
            issues.append("number_gap")
        if ans_tail:
            issues.append("ans_tail:" + ans_tail[:30])
        segs = {}
        for b in block:
            key = (b["page"], b["col"])
            s = segs.setdefault(key, [b["top"], b["bottom"]])
            s[0] = min(s[0], b["top"])
            s[1] = max(s[1], b["bottom"])
        qsegs = {}
        for b in qobjs:
            key = (b["page"], b["col"])
            sg = qsegs.setdefault(key, [b["top"], b["bottom"]])
            sg[0] = min(sg[0], b["top"])
            sg[1] = max(sg[1], b["bottom"])
        reasons = []
        if re.search(r"list\s*[-–]?\s*(i|1|ii|2)\b|match|column|table|group", stem_raw, re.I):
            reasons.append("match_or_table_keyword")
        if re.search(r"(following|given|above|shown)\s+(figure|diagram|map|picture|graph|chart|image|table|illustration)|figure|diagram|the map", stem_raw, re.I):
            reasons.append("figure_keyword")
        if any(b.get("gap", 0) > 18 for b in stem_objs[1:] + stem_objs[:1]):
            reasons.append("column_gap_in_stem")
        for (pg_, col_), (t_, b_) in qsegs.items():
            W_ = meta["size"][0]
            for (sx0, st, sx1, sb) in meta["shapes"].get(pg_, []):
                cx = (sx0 + sx1) / 2
                if (cx < W_ / 2) == (col_ == 0) and sb > t_ and st < b_ and (sx1 - sx0) > 6 and (sb - st) > 6:
                    reasons.append("graphic_in_question")
                    break
        if "label_typo_relabeled" in issues or "label_typo_swapped" in issues:
            reasons.append("label_typo")
        if amb:
            reasons.append("hyphen_linebreak")
        if any(b["size"] < 8.8 for b in qobjs):
            reasons.append("script_text")  # sub/superscripts are separate tiny-font lines
        questions.append(
            dict(
                reasons=sorted(set(reasons)), _qsegs=qsegs,
                num=num, chapter=cur_chapter, stem=stem_raw,
                options=[dict(label=a, text=b) for a, b in opts],
                answer=ans, exams=tags, issues=issues,
                _segs=segs, _expl_lines=cur_expl, page=block[0]["page"],
            )
        )
        last = num if new_chapter else max(last, num)
        consumed.append((i, end))
        i = end + 1
        expl_started = expl_done = False
        while i < n:
            l2 = flat[i]
            if l2["boxed"]:
                if not expl_done:
                    if any(x + 2 <= l2["x0"] <= x + 22 for x in allowed) and l2["size"] <= 11.5:
                        questions[-1]["_expl_lines"].append(l2)
                        expl_started = True
                    elif l2["size"] > 11.5 and expl_started:
                        expl_done = True  # a heading, not explanation text
                i += 1
                continue
            if is_start(i, last) is not None:
                break
            if expl_started:
                expl_done = True
            pre_lines.append(l2)
            i += 1
    for q in questions:
        el = q.pop("_expl_lines")
        q["explanation"] = J.join([x["text"] for x in el])
        q["expl_amb"] = J.amb or any(x["size"] < 8.8 for x in el)
        segs = q.pop("_segs")
        for x in el:
            key = (x["page"], x["col"])
            s = segs.setdefault(key, [x["top"], x["bottom"]])
            s[0] = min(s[0], x["top"])
            s[1] = max(s[1], x["bottom"])
        q["segments"] = [dict(page=k[0], col=k[1], top=v[0], bottom=v[1]) for k, v in sorted(segs.items())]
        qs_ = q.pop("_qsegs")
        q["qsegments"] = [dict(page=k[0], col=k[1], top=v[0], bottom=v[1]) for k, v in sorted(qs_.items())]
        if not q["explanation"]:
            q["issues"].append("no_explanation")
        q["exams"] = " | ".join(t.strip() for t in q["exams"] if t.strip())
    cov = [False] * n
    for a, b in consumed:
        for k in range(a, b + 1):
            cov[k] = True
    orphans = [(flat[k]["page"], flat[k]["text"][:40]) for k in range(n) if not cov[k] and not flat[k]["boxed"] and ANS.match(flat[k]["text"].strip())]
    return questions, chapters, rejected, orphans


def main():
    lines_path, book, out_path = sys.argv[1:4]
    flat, meta = load_lines(lines_path)
    qs, chs, rej, orph = parse(flat, meta)
    print('identical duplicate pages dropped:', len(meta['dup_pages']), meta['dup_pages'][:40])
    print('orphan Ans lines:', len(orph), orph[:20])
    print('rejected valid-structure candidates:', len(rej), rej[:15])
    json.dump(dict(book=book, questions=qs, chapters=[dict(start_q=c["start_q"], pre=[(l["text"], l["size"], l["bold"], l["page"]) for l in c["pre_lines"]]) for c in chs]), open(out_path, "w"))
    c = Counter(i.split(":")[0] for q in qs for i in q["issues"])
    print(book, "questions", len(qs), "chapters", len(chs), "issues", dict(c))


if __name__ == "__main__":
    main()
