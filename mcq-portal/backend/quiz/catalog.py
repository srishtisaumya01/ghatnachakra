"""The question bank on disk: manifest (subjects, chapters, books) and the answer key used for marking."""
import json
import threading

from django.conf import settings

_lock = threading.Lock()
_cache = {}


def manifest():
    with _lock:
        if 'manifest' not in _cache:
            _cache['manifest'] = json.loads((settings.DATA_DIR / 'manifest.json').read_text(encoding='utf-8'))
        return _cache['manifest']


def answer_key():
    """qid -> (answer, chapter id, subject id). Read from data/answers.json (tools/build_answer_index.py)."""
    with _lock:
        if 'key' not in _cache:
            raw = json.loads((settings.DATA_DIR / 'answers.json').read_text(encoding='utf-8'))
            _cache['key'] = {qid: tuple(v) for qid, v in raw.items()}
        return _cache['key']


def public_stats():
    man = manifest()
    subjects = [{'id': s['id'], 'name': s['name'], 'chapters': len(s['chapters']), 'questions': sum(c['count'] for c in s['chapters'])} for s in man['subjects']]
    return {'subjects': subjects, 'chapters': sum(s['chapters'] for s in subjects), 'questions': sum(s['questions'] for s in subjects)}
