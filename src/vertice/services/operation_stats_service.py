import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BatchRunStat:
    operation: str
    timestamp: str
    primary_count: int
    secondary_count: int
    error_count: int
    elapsed_seconds: float | None = None
    extra_label: str | None = None
    extra_value: str | None = None


@dataclass(frozen=True)
class ErrorStat:
    timestamp: str
    operation: str
    stage: str
    exception_type: str
    error_message: str
    context_label: str | None = None
    context_value: str | None = None


class OperationStatsService:
    SCRAPE_PATTERN = re.compile(
        r"^(?P<timestamp>[^|]+)\s+\|\s+\w+\s+\|[^|]+\|\s+\[SCRAPE\] batch finished \| "
        r"new_articles=(?P<new_articles>\d+) \| duplicates=(?P<duplicates>\d+) \| "
        r"errors=(?P<errors>\d+) \| sources=(?P<sources>\d+)"
    )
    ENRICH_PATTERN = re.compile(
        r"^(?P<timestamp>[^|]+)\s+\|\s+\w+\s+\|[^|]+\|\s+\[ENRICH\] batch finished \| "
        r"processed=(?P<processed>\d+) \| skipped=(?P<skipped>\d+) \| "
        r"errors=(?P<errors>\d+) \| elapsed=(?P<elapsed>[\d.]+)s"
    )
    SUMMARY_PATTERN = re.compile(
        r"^(?P<timestamp>[^|]+)\s+\|\s+\w+\s+\|[^|]+\|\s+\[SUMMARY\] batch finished \| "
        r"processed=(?P<processed>\d+) \| skipped=(?P<skipped>\d+) \| errors=(?P<errors>\d+) \| "
        r"model=(?P<model>.+?) \| elapsed=(?P<elapsed>[\d.]+)s"
    )

    def __init__(self, repository, app_log_path: Path, operation_error_log_path: Path) -> None:
        self.repository = repository
        self.app_log_path = app_log_path
        self.operation_error_log_path = operation_error_log_path

    def build_dashboard(self) -> dict:
        processing_counts = self.repository.get_processing_counts()
        batch_runs = self._read_batch_runs()
        error_records = self._read_error_records()
        operation_counts = Counter(item.operation for item in error_records)

        latest_scrape = self._latest_batch(batch_runs, "scrape")
        latest_enrich = self._latest_batch(batch_runs, "enrich")
        latest_summary = self._latest_batch(batch_runs, "summary")

        return {
            "processing_counts": processing_counts,
            "execution_counts": {
                "scrape_runs": sum(1 for item in batch_runs if item.operation == "scrape"),
                "enrich_runs": sum(1 for item in batch_runs if item.operation == "enrich"),
                "summary_runs": sum(1 for item in batch_runs if item.operation == "summary"),
                "logged_errors": len(error_records),
            },
            "latest_runs": {
                "scrape": latest_scrape,
                "enrich": latest_enrich,
                "summary": latest_summary,
            },
            "recent_batch_runs": batch_runs[:18],
            "recent_errors": error_records[:20],
            "error_breakdown": [
                {"operation": operation, "count": count}
                for operation, count in operation_counts.most_common()
            ],
        }

    def _latest_batch(self, batch_runs: list[BatchRunStat], operation: str) -> BatchRunStat | None:
        for item in batch_runs:
            if item.operation == operation:
                return item
        return None

    def _read_batch_runs(self) -> list[BatchRunStat]:
        if not self.app_log_path.exists():
            return []

        batch_runs: list[BatchRunStat] = []
        with self.app_log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue

                scrape_match = self.SCRAPE_PATTERN.match(line)
                if scrape_match:
                    batch_runs.append(
                        BatchRunStat(
                            operation="scrape",
                            timestamp=scrape_match.group("timestamp").strip(),
                            primary_count=int(scrape_match.group("new_articles")),
                            secondary_count=int(scrape_match.group("duplicates")),
                            error_count=int(scrape_match.group("errors")),
                            elapsed_seconds=None,
                            extra_label="fontes",
                            extra_value=scrape_match.group("sources"),
                        )
                    )
                    continue

                enrich_match = self.ENRICH_PATTERN.match(line)
                if enrich_match:
                    batch_runs.append(
                        BatchRunStat(
                            operation="enrich",
                            timestamp=enrich_match.group("timestamp").strip(),
                            primary_count=int(enrich_match.group("processed")),
                            secondary_count=int(enrich_match.group("skipped")),
                            error_count=int(enrich_match.group("errors")),
                            elapsed_seconds=float(enrich_match.group("elapsed")),
                            extra_label=None,
                            extra_value=None,
                        )
                    )
                    continue

                summary_match = self.SUMMARY_PATTERN.match(line)
                if summary_match:
                    batch_runs.append(
                        BatchRunStat(
                            operation="summary",
                            timestamp=summary_match.group("timestamp").strip(),
                            primary_count=int(summary_match.group("processed")),
                            secondary_count=int(summary_match.group("skipped")),
                            error_count=int(summary_match.group("errors")),
                            elapsed_seconds=float(summary_match.group("elapsed")),
                            extra_label="modelo",
                            extra_value=summary_match.group("model").strip(),
                        )
                    )

        batch_runs.reverse()
        return batch_runs

    def _read_error_records(self) -> list[ErrorStat]:
        if not self.operation_error_log_path.exists():
            return []

        error_records: list[ErrorStat] = []
        with self.operation_error_log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue

                context = payload.get("context") or {}
                context_label = None
                context_value = None
                if context.get("title"):
                    context_label = "artigo"
                    context_value = str(context["title"])
                elif context.get("model"):
                    context_label = "modelo"
                    context_value = str(context["model"])
                elif context.get("article_url"):
                    context_label = "url"
                    context_value = str(context["article_url"])

                error_records.append(
                    ErrorStat(
                        timestamp=str(payload.get("timestamp", "-")),
                        operation=str(payload.get("operation", "-")),
                        stage=str(payload.get("stage", "-")),
                        exception_type=str(payload.get("exception_type", "-")),
                        error_message=str(payload.get("error_message", "-")),
                        context_label=context_label,
                        context_value=context_value,
                    )
                )

        error_records.reverse()
        return error_records
