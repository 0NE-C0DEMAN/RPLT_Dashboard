"""Streamlit session state helpers.

Tracks the currently-active table, the user's session id, and the
list of imported tables in this session.
"""

from __future__ import annotations

import uuid
from typing import Optional

import streamlit as st

from .ingest import TableInfo, load_metadata
from .db import drop_table


_KEY_SESSION_ID = "rgf_session_id"
_KEY_ACTIVE_TABLE = "rgf_active_table"
_KEY_IMPORTED = "rgf_imported_tables"


def session_id() -> str:
    if _KEY_SESSION_ID not in st.session_state:
        st.session_state[_KEY_SESSION_ID] = uuid.uuid4().hex[:12]
    return st.session_state[_KEY_SESSION_ID]


def set_active_table(table_name: str) -> None:
    st.session_state[_KEY_ACTIVE_TABLE] = table_name


def get_active_table() -> Optional[str]:
    return st.session_state.get(_KEY_ACTIVE_TABLE)


def get_active_info() -> Optional[TableInfo]:
    name = get_active_table()
    if not name:
        return None
    return load_metadata(name)


def imported_tables() -> list[str]:
    if _KEY_IMPORTED not in st.session_state:
        st.session_state[_KEY_IMPORTED] = []
    return st.session_state[_KEY_IMPORTED]


def add_imported(table_name: str) -> None:
    items = imported_tables()
    if table_name not in items:
        items.append(table_name)
        st.session_state[_KEY_IMPORTED] = items


def remove_imported(table_name: str) -> None:
    items = imported_tables()
    if table_name in items:
        items.remove(table_name)
        st.session_state[_KEY_IMPORTED] = items
        drop_table(table_name)
        # Invalidate the cache.py registry so subsequent
        # ``ensure_registered`` re-checks DuckDB for this table.
        from .cache import _registered
        _registered.discard(table_name)
        if get_active_table() == table_name:
            st.session_state[_KEY_ACTIVE_TABLE] = None
