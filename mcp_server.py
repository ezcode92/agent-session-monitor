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
    args = parser.parse_args()
    from agent_monitor.config import load_config
    from agent_monitor.service import AgentMonitor
    from agent_monitor.project_store import ProjectStore
    from agent_monitor.project_analysis import ProjectAnalysis
    from agent_monitor.mcp_server import create_server

    monitor = AgentMonitor(load_config(args.config))
    create_server(ProjectAnalysis(monitor.get_snapshot, ProjectStore(args.analysis_db))).run(transport="stdio")


if __name__ == "__main__":
    main()
