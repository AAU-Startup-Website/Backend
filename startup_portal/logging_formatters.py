import json
import logging


class JSONFormatter(logging.Formatter):
    """Minimal structured JSON log formatter (no external dependency).

    Includes any `extra={...}` fields passed to the logger call (e.g. the
    username/ip/event fields used by the login lockout logging in
    users/views.py) alongside the standard fields.
    """

    RESERVED = set(logging.LogRecord(
        '', 0, '', 0, '', (), None
    ).__dict__.keys()) | {'message', 'asctime'}

    def format(self, record):
        payload = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info:
            payload['exc_info'] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in self.RESERVED:
                try:
                    json.dumps(value)
                except TypeError:
                    value = str(value)
                payload[key] = value

        return json.dumps(payload)
