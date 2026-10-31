from django.conf import settings
from django.db import models


class Attempt(models.Model):
    """One submitted test. Marks are computed on the server from the answer key, never taken from the browser."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attempts')
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=120)
    config = models.JSONField(default=dict)
    duration = models.FloatField(default=0)
    total = models.PositiveIntegerField()
    correct = models.PositiveIntegerField()
    wrong = models.PositiveIntegerField()
    skipped = models.PositiveIntegerField()
    score = models.FloatField()
    maxscore = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=['user', '-created_at'])]


class AttemptItem(models.Model):
    STATUS = [('correct', 'correct'), ('wrong', 'wrong'), ('skipped', 'skipped')]

    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='items')
    qid = models.CharField(max_length=40)
    chapter = models.CharField(max_length=30)
    subject = models.CharField(max_length=20)
    chosen = models.CharField(max_length=1, blank=True, default='')
    answer = models.CharField(max_length=1)
    status = models.CharField(max_length=8, choices=STATUS)
    flagged = models.BooleanField(default=False)
    secs = models.FloatField(default=0)

    class Meta:
        indexes = [models.Index(fields=['qid'])]
