from pathlib import Path
import sys

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from agent_monitor.ui.app import run


def main() -> None:
    """Testable Streamlit entrypoint; importing this module has no UI side effects."""
    run()

if __name__ == "__main__":
    main()
