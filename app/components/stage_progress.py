"""Production lifecycle stage progress bar."""

from typing import Literal

import streamlit as st

from core.repositories.batch_repository import VALID_STAGES as STAGES

StageState = Literal["done", "active", "pending"]


def stage_progress(current_stage: str) -> None:
    """
    Render the six-stage batch lifecycle progress bar.

    Args:
        current_stage: One of the values in STAGES. Every stage before it
            renders as "done", that stage as "active", everything after
            as "pending". This function has no knowledge of *why* a batch
            is in a given stage — that decision belongs to batch_service,
            not the UI layer.
    """
    if current_stage not in STAGES:
        raise ValueError(f"Unknown stage '{current_stage}'. Expected one of {STAGES}.")

    current_index = STAGES.index(current_stage)
    pills = []
    connectors = []

    for index, stage_name in enumerate(STAGES):
        if index < current_index:
            state: StageState = "done"
        elif index == current_index:
            state = "active"
        else:
            state = "pending"
        pills.append(f'<span class="gpp-stage-pill gpp-stage-pill--{state}">{stage_name}</span>')

        if index < len(STAGES) - 1:
            connector_state = "done" if index < current_index else ("active" if index == current_index else "pending")
            connector_class = f"gpp-stage-connector--{connector_state}" if connector_state != "pending" else ""
            connectors.append(f'<div class="gpp-stage-connector {connector_class}"></div>')

    track_html = ""
    for i, pill in enumerate(pills):
        track_html += pill
        if i < len(connectors):
            track_html += connectors[i]

    st.markdown(
        f'<div class="gpp-card"><div class="gpp-stage-track">{track_html}</div></div>',
        unsafe_allow_html=True,
    )
