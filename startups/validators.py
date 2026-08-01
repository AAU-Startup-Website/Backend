from django.core.exceptions import ValidationError

MAX_PITCH_DECK_SIZE_MB = 10
MAX_PITCH_DECK_SIZE_BYTES = MAX_PITCH_DECK_SIZE_MB * 1024 * 1024


def validate_file_size(file):
    if file.size > MAX_PITCH_DECK_SIZE_BYTES:
        raise ValidationError(
            f"File too large. Maximum size is {MAX_PITCH_DECK_SIZE_MB}MB."
        )
