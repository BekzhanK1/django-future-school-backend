"""DRF helpers: API datetimes are represented in Django ``TIME_ZONE`` (Asia/Almaty)."""

from __future__ import annotations

from django.db import models
from django.utils import timezone
from rest_framework import serializers


class LocalDateTimeField(serializers.DateTimeField):
    """Serialize aware UTC datetimes as ISO-8601 in the active Django local zone."""

    def to_representation(self, value):  # type: ignore[override]
        if value is None:
            return None
        value = self.enforce_timezone(value)
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_default_timezone())
        return timezone.localtime(value).isoformat()


class ModelSerializer(serializers.ModelSerializer):
    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,  # type: ignore[misc]
        models.DateTimeField: LocalDateTimeField,
    }
