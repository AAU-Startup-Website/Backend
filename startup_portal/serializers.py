"""
Shared serializer utilities: reject unexpected fields; file upload hardening.
"""
import os
from rest_framework import serializers


class StrictSerializerMixin:
    """Reject request keys that are not declared on the serializer."""

    def to_internal_value(self, data):
        if hasattr(data, 'keys'):
            allowed = set(self.fields.keys())
            # Multipart/form may include nested keys differently; only check top-level
            unknown = set(data.keys()) - allowed
            # DRF sometimes passes QueryDict; ignore empty extras from form encoding noise
            unknown = {k for k in unknown if k != ''}
            if unknown:
                raise serializers.ValidationError(
                    {field: 'Unexpected field.' for field in sorted(unknown)}
                )
        return super().to_internal_value(data)


class StrictModelSerializer(StrictSerializerMixin, serializers.ModelSerializer):
    pass


def validate_upload_file(value, *, max_mb=5, allowed_extensions=None, allowed_content_types=None):
    if value is None:
        return value

    max_bytes = max_mb * 1024 * 1024
    if value.size > max_bytes:
        raise serializers.ValidationError(f'File size must not exceed {max_mb} MB.')

    if allowed_extensions:
        ext = os.path.splitext(value.name)[1].lower().lstrip('.')
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f'File type ".{ext}" is not allowed. Allowed: {", ".join(sorted(allowed_extensions))}.'
            )

    content_type = getattr(value, 'content_type', None)
    if allowed_content_types and content_type and content_type not in allowed_content_types:
        raise serializers.ValidationError(
            f'MIME type "{content_type}" is not allowed.'
        )

    return value
