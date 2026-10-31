import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()
USERNAME_PATTERN = re.compile(r'^[a-z0-9_.]{3,30}$')


def checked_password(value, user=None):
    try:
        validate_password(value, user)
    except DjangoValidationError as e:
        raise serializers.ValidationError(list(e.messages))
    return value


class EmailField(serializers.EmailField):
    def to_internal_value(self, data):
        return super().to_internal_value(data).strip().lower()


class UsernameField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data).strip().lower()
        if not USERNAME_PATTERN.match(value):
            raise serializers.ValidationError('Use 3 to 30 letters, numbers, dots or underscores.')
        return value


class SessionRequestSerializer(serializers.Serializer):
    """`transport` says how the session reaches the client: a browser asks for `cookie` (HttpOnly, no token in the body)."""

    transport = serializers.ChoiceField(choices=['token', 'cookie'], default='token')


class RegisterSerializer(SessionRequestSerializer):
    email = EmailField(max_length=150)
    username = UsernameField(max_length=60)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)

    def validate(self, attrs):
        try:
            attrs['password'] = checked_password(attrs['password'], User(username=attrs['username'], email=attrs['email']))
        except serializers.ValidationError as e:
            raise serializers.ValidationError({'password': e.detail})
        return attrs


class LoginSerializer(SessionRequestSerializer):
    """Signs in with a username or an email address."""

    username = serializers.CharField(max_length=150, required=False)
    password = serializers.CharField(max_length=128, trim_whitespace=False)

    def validate(self, attrs):
        identifier = (attrs.get('username') or '').strip().lower()
        if not identifier:
            raise serializers.ValidationError({'username': 'Enter your username.'})
        attrs['identifier'] = identifier
        return attrs
