"""Writes data/answers.json: {question id: [answer, chapter id, subject id]}.

The API evaluates tests from this small file instead of loading all 19 MB of question text. Re-run after build_data.py.
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def main():
    man = json.loads((DATA / "manifest.json").read_text())
    idx = {}
    for s in man["subjects"]:
        for ch in s["chapters"]:
            for q in json.loads((DATA / "q" / f"{ch['id']}.json").read_text()):
                idx[q["id"]] = [q["answer"], ch["id"], s["id"]]
    (DATA / "answers.json").write_text(json.dumps(idx, separators=(",", ":")))
    print(len(idx), "answers indexed")


if __name__ == "__main__":
    main()
