from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

CONFIG_PATH = Path('.agent-monitor') / 'config.json'


def default_config() -> dict[str, Any]:
    codex = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
    claude = Path(os.environ.get('CLAUDE_CONFIG_DIR', Path.home() / '.claude'))
    gemini = Path.home() / '.gemini'
    return {
        'timezone': None, 'auto_refresh_seconds': 5,
        'paths': {
            'codex': [str(codex / 'sessions'), str(codex / 'archived_sessions')],
            'claude': [str(claude / 'projects')],
            'antigravity': [str(gemini / x) for x in ('antigravity', 'antigravity-cli', 'antigravity-ide')],
        },
    }


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return default_config()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    base = default_config()
    base.update({k: v for k, v in data.items() if k != 'paths'})
    if isinstance(data.get('paths'), dict): base['paths'].update(data['paths'])
    return base


def save_config(config: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')


def path_diagnostics(config: dict[str, Any]) -> list[dict[str, str]]:
    """Validate configured roots without making scan failure fatal."""
    diagnostics = []
    for agent, roots in config.get('paths', {}).items():
        for root_text in roots if isinstance(roots, list) else []:
            root = Path(root_text).expanduser()
            try:
                if not root.exists(): diagnostics.append({'agent': agent, 'path': str(root), 'kind': 'missing', 'message': 'Configured path does not exist'})
                elif not root.is_dir(): diagnostics.append({'agent': agent, 'path': str(root), 'kind': 'not_directory', 'message': 'Configured path is not a directory'})
                else:
                    next(root.iterdir(), None)
            except OSError as exc:
                diagnostics.append({'agent': agent, 'path': str(root), 'kind': 'unreadable', 'message': str(exc)})
    return diagnostics


def normalized_timezone(config: dict[str, Any]) -> tuple[str, dict[str, str] | None]:
    requested = config.get('timezone')
    if requested:
        try:
            return ZoneInfo(str(requested)).key, None
        except (ZoneInfoNotFoundError, ValueError):
            return 'UTC', {'kind': 'invalid_timezone', 'path': 'timezone', 'message': f'Unknown IANA timezone: {requested}'}
    try:
        from tzlocal import get_localzone_name
        return ZoneInfo(get_localzone_name()).key, None
    except Exception:
        return 'UTC', None
