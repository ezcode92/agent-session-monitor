"""Synthetic, local-only monitor benchmark; does not read configured user logs."""
import argparse
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import agent_monitor.service as service
from agent_monitor.service import AgentMonitor
from agent_monitor.ui.view_data import build_view_data


def write_log(path: Path, session_id: str, size: int) -> None:
    head = f'{{"type":"session_meta","payload":{{"id":"{session_id}"}},"timestamp":"2026-09-07T14:00:00Z"}}\n'
    row = '{"type":"event_msg","timestamp":"2026-09-07T14:00:00Z","payload":{"type":"message","text":"' + "x" * 180 + '"}}\n'
    path.write_text(head, encoding="utf-8")
    with path.open("a", encoding="utf-8") as stream:
        remaining = size - len(head.encode())
        while remaining > 0:
            stream.write(row)
            remaining -= len(row.encode())


def measure(call):
    started = time.perf_counter()
    call()
    return time.perf_counter() - started


def view_benchmark() -> None:
    """Measure view construction from one reused synthetic snapshot."""
    now = datetime(2026, 9, 8, tzinfo=timezone.utc)
    sessions = [{"agent": "codex", "session_id": f"s{index}", "started_at": now-timedelta(hours=1), "last_activity": now, "title": f"session {index}"} for index in range(20)]
    usage = [{"agent": "codex", "session_id": f"s{index % 20}", "turn_id": f"t{index}", "event_id": f"u{index}", "occurred_at": now-timedelta(minutes=index % 60), "input_tokens": 100, "output_tokens": 20, "total_tokens": 120} for index in range(1000)]
    requests = [{"agent": "codex", "session_id": f"s{index % 20}", "turn_id": f"t{index}", "started_at": now-timedelta(minutes=10), "ended_at": now, "status": "completed"} for index in range(1000)]
    events = [{"agent": "codex", "session_id": f"s{index % 20}", "event_id": f"e{index}", "occurred_at": now-timedelta(minutes=index % 60), "display": "synthetic"} for index in range(10000)]
    snapshot = {"timezone": "UTC", "sessions": sessions, "usage": usage, "requests": requests, "events": events, "orchestration": {"depths": {("codex", f"s{index}"): 0 for index in range(20)}}}
    state = {"start": now-timedelta(hours=2), "end": now+timedelta(seconds=1), "agents": [], "projects": [], "models": []}

    def samples(include_events: bool) -> list[float]:
        return [measure(lambda: build_view_data(snapshot, {**state, "include_events": include_events})) for _ in range(7)]

    without_events, with_events = samples(False), samples(True)
    print(f"same snapshot: {len(sessions)} sessions, {len(usage)} usage, {len(requests)} requests, {len(events)} events")
    print(f"include_events=False median={median(without_events):.6f}s samples={[round(value, 6) for value in without_events]}")
    print(f"include_events=True median={median(with_events):.6f}s samples={[round(value, 6) for value in with_events]}")


def main() -> None:
    target = 10 * 1024 * 1024
    temp = Path(tempfile.mkdtemp(prefix="agent-monitor-benchmark-", dir=ROOT))
    try:
        selected, unrelated = temp / "selected.jsonl", temp / "unrelated.jsonl"
        write_log(selected, "selected", target // 2)
        write_log(unrelated, "unrelated", target // 2)
        counts: dict[str, int] = {"selected": 0, "unrelated": 0}
        original = service.parse_source

        def counted(source):
            counts["selected" if source.path == selected else "unrelated"] += 1
            return original(source)

        service.parse_source = counted
        monitor = AgentMonitor({"timezone": "UTC", "paths": {"codex": [str(temp)], "claude": [], "antigravity": []}})
        cold = measure(monitor.refresh)
        after_cold = dict(counts)
        warm = measure(monitor.refresh)
        after_warm = dict(counts)
        unchanged_poll = measure(lambda: monitor.poll_session("selected"))
        after_unchanged = dict(counts)
        with selected.open("a", encoding="utf-8") as stream:
            stream.write('{"type":"event_msg","timestamp":"2026-09-07T14:01:00Z","payload":{"type":"message","text":"changed"}}\n')
        changed_poll = measure(lambda: monitor.poll_session("selected"))
        after_changed = dict(counts)
        report = "\n".join([
            "# Synthetic monitor benchmark",
            "", f"Synthetic bytes: {selected.stat().st_size + unrelated.stat().st_size}",
            f"cold refresh: {cold:.3f}s; parses: {after_cold}",
            f"warm refresh: {warm:.3f}s; parses: {after_warm}",
            f"unchanged selected poll: {unchanged_poll:.3f}s; parses: {after_unchanged}",
            f"changed selected poll: {changed_poll:.3f}s; parses: {after_changed}",
            "",
            "Expected: warm/unchanged add no parses; changed poll adds only selected.",
        ])
        (ROOT / ".agent-monitor-benchmark-report.md").write_text(report + "\n", encoding="utf-8")
        print(report)
    finally:
        service.parse_source = original if "original" in locals() else service.parse_source
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--view", action="store_true", help="benchmark synthetic view construction")
    args = parser.parse_args()
    view_benchmark() if args.view else main()
