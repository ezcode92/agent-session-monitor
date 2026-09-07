"""Optional core-service discovery.  Keeps Streamlit usable during initial setup."""
from __future__ import annotations
import importlib
from typing import Any


class CoreContractError(RuntimeError):
    """The application was installed without its required collector service."""


def load_snapshot(force: bool = False) -> dict[str, Any]:
    """Call the first available stable service entrypoint, else return an empty snapshot.

    Preferred core contract: ``agent_monitor.service.get_snapshot(force=False)``
    returning keys sessions, requests, usage, diagnostics, paths and scanned_at.
    """
    for module_name, func_name in (
        ("agent_monitor.service", "get_snapshot"),
        ("agent_monitor.service", "scan"),
        ("agent_monitor.service", "load"),
    ):
        try:
            func = getattr(importlib.import_module(module_name), func_name)
            value = func(force=force)
            return value if isinstance(value, dict) else {"sessions": getattr(value, "sessions", [])}
        except (ImportError, AttributeError, TypeError):
            continue
    raise CoreContractError(
        "코어 서비스 계약을 찾지 못했습니다. "
        "agent_monitor.service.get_snapshot(force=False)를 제공해야 합니다."
    )
