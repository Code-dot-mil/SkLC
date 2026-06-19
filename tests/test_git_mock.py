import json
from pathlib import Path

from skill_exchange.git_mock import append_event, read_events


def test_append_and_read_events(tmp_path: Path):
    path = tmp_path / "1.md.jsonl"

    append_event(path, {"type": "mr.opened", "mr_id": "1"})
    append_event(path, {"type": "pipeline.completed", "status": "success"})

    events = read_events(path)
    assert events == [
        {"type": "mr.opened", "mr_id": "1"},
        {"type": "pipeline.completed", "status": "success"},
    ]
    assert all(json.loads(line) for line in path.read_text().splitlines())
