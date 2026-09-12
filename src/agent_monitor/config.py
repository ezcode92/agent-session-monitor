from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

CONFIG_PATH = Path('.agent-monitor') / 'config.json'


def default_config() -> dict[str, Any]:
    codex = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
    return {
        'timezone': None, 'auto_refresh_seconds': 5,
        'paths': {
            'codex': [str(codex / 'sessions'), str(codex / 'archived_sessions')],
        },
    }


def codex_only_config(config: dict[str, Any]) -> dict[str, Any]:
    """Keep legacy paths inactive without deleting settings or source files."""
    result = dict(config)
    paths = config.get('paths', {})
    if not isinstance(paths, dict):
        paths = {}
    archived = config.get('deprecated_paths', {})
    archived = dict(archived) if isinstance(archived, dict) else {}
    archived.update({agent: roots for agent, roots in paths.items() if agent != 'codex'})
    result['paths'] = {'codex': list(paths.get('codex', [])) if isinstance(paths.get('codex'), list) else []}
    if archived:
        result['deprecated_paths'] = archived
    return result


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
    return codex_only_config(base)


def save_config(config: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(codex_only_config(config), ensure_ascii=False, indent=2), encoding='utf-8')


def path_diagnostics(config: dict[str, Any]) -> list[dict[str, str]]:
    """Validate configured roots without making scan failure fatal."""
    diagnostics = []
    for agent, roots in codex_only_config(config)['paths'].items():
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
