"""Shared presentation and session-local UI state; no collector or storage logic."""
from __future__ import annotations

from pathlib import Path
import streamlit as st


def apply_styles():
    st.html(Path(__file__).with_name("styles.css"))


def page_header(title, description):
    with st.container(key="asm-intro"):
        st.title(title, anchor=False)
        st.caption(description)
        context = st.session_state.get("ui-context")
        if context:
            filter_summary(context[2])


def metrics(items, key):
    """Each tuple is (label, value, explanation); CSS wraps by available space."""
    with st.container(key=f"asm-metrics-{key}"):
        for column, (label, value, description) in zip(st.columns(len(items)), items):
            column.metric(label, value, help=description)


def remember(widget, label, *, key, **kwargs):
    """Keep a control's value when Streamlit cleans up widgets on another page.

    Only use outside forms. Changes are mirrored before the next script run,
    so restoring a value cannot overwrite a just-received user interaction.
    """
    widget_key = f"_ui:{key}"
    options = kwargs.get("options")
    if options is not None:
        options = list(options)
        kwargs["options"] = options
        for identity in (key, widget_key):
            if identity not in st.session_state:
                continue
            value = st.session_state[identity]
            if widget == st.multiselect:
                st.session_state[identity] = [item for item in value if item in options] if isinstance(value, (list, tuple)) else []
            elif value not in options:
                st.session_state.pop(identity, None)
    if widget_key not in st.session_state and key in st.session_state:
        st.session_state[widget_key] = st.session_state[key]

    def save():
        st.session_state[key] = st.session_state[widget_key]

    result = widget(label, key=widget_key, on_change=save, **kwargs)
    st.session_state[key] = result
    return result


def saved_notice(message):
    st.session_state["ui-notice"] = message


def show_notice():
    message = st.session_state.pop("ui-notice", None)
    if message:
        st.success(message)


def filter_summary(state):
    page = state["page"]
    if page == "회고·개선":
        st.caption("표시 범위: 저장한 모든 작업·개선 항목 · 공통 필터 미적용")
    elif page == "설정":
        st.caption("표시 범위: 전체 수집 설정·진단 · 공통 필터 미적용")
    else:
        parts = [f"{state['start']:%Y-%m-%d %H:%M} ~ {state['end']:%Y-%m-%d %H:%M} 미만", state["timezone"]]
        if page == "에이전트 분석":
            parts.append("공통 기간만 적용 · 분석할 프로젝트는 아래에서 선택")
        else:
            for name, title in (("agents", "에이전트"), ("projects", "프로젝트"), ("models", "모델")):
                parts.append(f"{title}: {', '.join(state[name]) or '전체'}")
        st.caption("적용 범위: " + " · ".join(parts))
