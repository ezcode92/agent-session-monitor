from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class SourceFile:
    agent: str
    path: Path
    size: int
    mtime_ns: int
    source_label: str | None = None
    source_kind: str | None = None

    @property
    def source_path(self) -> str:
        return str(self.path)


def scan_sources(paths: dict[str, Iterable[str]]) -> list[SourceFile]:
    found: dict[str, SourceFile] = {}
    for agent, roots in paths.items():
        for root_text in roots:
            root = Path(root_text).expanduser()
            # A missing or protected root must not prevent other configured
            # installations from being scanned.
            try:
                is_directory = root.is_dir()
            except OSError:
                continue
            if not is_directory:
                continue
            pattern = '**/transcript.jsonl' if agent == 'antigravity' else '**/*.jsonl'
            try:
                candidates = root.glob(pattern)
                for path in candidates:
                    try:
                        stat = path.stat()
                    except OSError:
                        continue
                    label = root.name or agent
                    found[str(path.resolve())] = SourceFile(agent, path.resolve(), stat.st_size, stat.st_mtime_ns, label, agent)
            except OSError:
                # pathlib can raise while traversing an unreadable child.
                continue
    return sorted(found.values(), key=lambda source: str(source.path))
