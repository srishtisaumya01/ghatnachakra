"""Marking a submitted test."""
from django.db import transaction

from . import catalog
from .models import Attempt, AttemptItem

MAX_QUESTIONS = 500


def evaluate(user, name, duration, config, answers):
    """Stores the attempt and returns it. +`correct` per right answer, -`negative` per wrong one, skipped counts as nothing.
    Unknown question ids and repeated ids are ignored; the answer key is the server's own."""
    key = catalog.answer_key()
    marking = config.get('marking') or {}
    right, minus = float(marking.get('correct', 1)), float(marking.get('negative', 0))
    rows, seen = [], set()
    for a in answers[:MAX_QUESTIONS]:
        qid = a.get('qid')
        if qid in seen or qid not in key:
            continue
        seen.add(qid)
        answer, chapter, subject = key[qid]
        chosen = a.get('chosen') or ''
        status = 'skipped' if not chosen else 'correct' if chosen == answer else 'wrong'
        rows.append(AttemptItem(qid=qid, chapter=chapter, subject=subject, chosen=chosen, answer=answer, status=status,
                                flagged=bool(a.get('flagged')), secs=max(0.0, min(float(a.get('secs') or 0), 36000.0))))
    correct = sum(r.status == 'correct' for r in rows)
    wrong = sum(r.status == 'wrong' for r in rows)
    skipped = len(rows) - correct - wrong
    with transaction.atomic():
        attempt = Attempt.objects.create(
            user=user, name=name, config={'marking': {'correct': right, 'negative': minus}, 'minutes': config.get('minutes', 0)},
            duration=duration, total=len(rows), correct=correct, wrong=wrong, skipped=skipped,
            score=round(correct * right - wrong * minus, 2), maxscore=round(len(rows) * right, 2))
        AttemptItem.objects.bulk_create([AttemptItem(attempt=attempt, qid=r.qid, chapter=r.chapter, subject=r.subject, chosen=r.chosen,
                                                     answer=r.answer, status=r.status, flagged=r.flagged, secs=r.secs) for r in rows])
    return attempt
