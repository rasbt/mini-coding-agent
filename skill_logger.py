
import json
from datetime import datetime, timezone
from pathlib import Path


def log_event(log_path, event_type, session_id, **details):
    """Append a timestamped skill event to a JSONL log file."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "event": event_type,
        **details,
    }

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")
