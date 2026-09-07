"""Synthetic, local-only monitor benchmark; does not read configured user logs."""
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import agent_monitor.service as service
from agent_monitor.service import AgentMonitor


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
    main()
