"""
Reusable UI component library.

Every visual element that appears on more than one page — and most that
appear on exactly one — lives here as a function, not as inline HTML
scattered through page files. Pages compose these; they should rarely
need to write their own st.markdown(unsafe_allow_html=True) calls.
"""

from app.components.coming_soon import coming_soon
from app.components.kpi_card import kpi_card
from app.components.machine_tile import machine_tile
from app.components.stage_progress import stage_progress
from app.components.status_badge import status_badge
from app.components.top_bar import top_bar

__all__ = [
    "coming_soon",
    "kpi_card",
    "machine_tile",
    "stage_progress",
    "status_badge",
    "top_bar",
]
