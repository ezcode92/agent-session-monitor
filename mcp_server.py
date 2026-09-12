"""Standalone stdio MCP entrypoint; does not start or import Streamlit."""
from pathlib import Path
import argparse
import os
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / ".agent-monitor/config.json")
    parser.add_argument("--analysis-db", type=Path, default=Path(os.environ.get("AGENT_MONITOR_ANALYSIS_DB", ROOT / ".agent-monitor/analysis.sqlite3")))
    parser.add_argument("--scope", choices=("analysis", "results"), default="analysis",
                        help="analysis exposes the full worker API; results exposes completed reports read-only")
    args = parser.parse_args()
    from agent_monitor.project_store import ProjectStore
    from agent_monitor.mcp_server import create_results_server, create_server

    store = ProjectStore(args.analysis_db)
    if args.scope == "results":
        server = create_results_server(store)
    else:
        from agent_monitor.config import load_config
        from agent_monitor.service import AgentMonitor
        from agent_monitor.project_analysis import ProjectAnalysis

        monitor = AgentMonitor(load_config(args.config))
        server = create_server(ProjectAnalysis(monitor.get_snapshot, store))
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
