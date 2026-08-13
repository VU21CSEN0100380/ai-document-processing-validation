import json
import logging
from datetime import datetime, timezone
from pathlib import Path


class JsonFormatter(logging.Formatter):
    SAFE_EXTRA_FIELDS = ("document_id", "event", "status", "error_type")

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in self.SAFE_EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if any(getattr(handler, "name", "") == "docai_json" for handler in root.handlers):
        return
    formatter = JsonFormatter()
    stream = logging.StreamHandler()
    stream.name = "docai_json"
    stream.setFormatter(formatter)
    file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    file_handler.name = "docai_json_file"
    file_handler.setFormatter(formatter)
    root.setLevel(logging.INFO)
    root.addHandler(stream)
    root.addHandler(file_handler)

