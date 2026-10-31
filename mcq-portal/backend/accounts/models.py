import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def hash_token(raw):
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class AuthToken(models.Model):
    """A login on one device. Only a hash is stored, so a database leak does not leak usable tokens."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='auth_tokens')
    key_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    MAX_PER_USER = 5

    @classmethod
    def prune(cls, user):
        cls.objects.filter(user=user, expires_at__lte=timezone.now()).delete()
        keep = list(cls.objects.filter(user=user).order_by('-created_at').values_list('pk', flat=True)[: cls.MAX_PER_USER - 1])
        cls.objects.filter(user=user).exclude(pk__in=keep).delete()

    @classmethod
    def issue(cls, user):
        raw = secrets.token_urlsafe(32)
        token = cls.objects.create(user=user, key_hash=hash_token(raw), expires_at=timezone.now() + timedelta(days=settings.AUTH_TOKEN_LIFETIME_DAYS))
        return raw, token
