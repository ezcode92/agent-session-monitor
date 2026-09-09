"""The single registry for sidebar links, page files and stable URL paths."""
from pathlib import Path
import streamlit as st

PAGES = (
    ("overview", "개요", ""),
    ("history", "작업 이력", "history"),
    ("reviews", "회고·개선", "reviews"),
    ("agent_analysis", "에이전트 분석", "agent-analysis"),
    ("analytics", "기간 분석", "analytics"),
    ("orchestration", "오케스트레이션", "orchestration"),
    ("settings", "설정", "settings"),
)


def navigation():
    directory = Path(__file__).with_name("pages")
    return st.navigation([
        st.Page(directory / f"{name}.py", title=title, url_path=url, default=not url)
        for name, title, url in PAGES
    ], position="sidebar", expanded=True)
