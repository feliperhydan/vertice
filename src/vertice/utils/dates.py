from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional


def normalize_datetime(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        pass

    normalized = value.replace("Z", "+00:00")

    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.isoformat()
        except ValueError:
            continue

    return value
