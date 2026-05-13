import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class OperationErrorLogger:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def log_error(
        self,
        operation: str,
        stage: str,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "stage": stage,
            "exception_type": error.__class__.__name__,
            "error_message": str(error),
            "context": context or {},
            "traceback": traceback.format_exc(),
        }

        with self._lock:
            with self.file_path.open("a", encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False)
                handle.write("\n")
