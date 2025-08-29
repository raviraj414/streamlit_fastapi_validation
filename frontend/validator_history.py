# frontend/validator_history.py
import streamlit as st
import html
from datetime import datetime, date, time, timedelta

from api_client import fetch_user_history, fetch_contexts_for_command

_DEF_CSS = """
<style>
.h-center { text-align:center; }
.badge { display:inline-block; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600; color:white; }
.badge-dyn { background:#1f8e3d; } .badge-stat{ background:#1a73e8; }
.row-wrap { padding:8px 10px; border-radius:8px; }
.row-wrap:nth-child(odd)  { background:#fafafa; }
.row-wrap:nth-child(even) { background:#f3f6fc; }
.header-row { padding:10px 10px; border-radius:8px; background:#e9efff; font-weight:700; }
.context-box { background-color:#f0f2f6; padding:20px 25px; border-radius:10px; border-left:6px solid #2c6ecb; min-height:150px; box-shadow: 0 2px 5px rgba(0,0,0,0.08); overflow-x:auto; }
.command-pre { background-color:#f5f5f5; padding:10px; border-radius:6px; }
</style>
"""

def render_history_for_user(user):
    st.markdown(_DEF_CSS, unsafe_allow_html=True)
    st.markdown(f"🧑‍💻 Showing history for: {user['name']}")
    user_id = user["id"]

    if "history_loaded" not in st.session_state:
        st.session_state.history_loaded = False
    if "history_rows" not in st.session_state:
        st.session_state.history_rows = []
    if "history_selected" not in st.session_state:
        st.session_state.history_selected = None
    if "history_details" not in st.session_state:
        st.session_state.history_details = []
    if "history_mode" not in st.session_state:
        st.session_state.history_mode = "list"

    if not st.session_state.history_loaded:
        rows = fetch_user_history(user_id, None, None, None, "All")
        st.session_state.history_rows = rows
        st.session_state.history_loaded = True

    # Filters
    with st.expander(" Filters", expanded=True):
        col0, col1, col2, col3, col4 = st.columns([0.8, 1.2, 1.0, 1.0, 0.9])
        use_date = col0.checkbox("Use date", value=False, key="hist_use_date")
        default_start = date.today() - timedelta(days=7)
        default_end = date.today()
        date_range_val = col1.date_input("Date range", value=(default_start, default_end), disabled=not use_date, key="hist_date_range")
        command_id_input = col2.text_input("Command ID", value="", key="hist_cmd_id")
        type_choice = col3.selectbox("Type", options=["All", "Dynamic", "Static"], key="hist_type_choice")
        apply_clicked = col4.button("Apply", key="hist_apply")
        clear_clicked = col4.button("Clear", key="hist_clear")

        if clear_clicked:
            st.session_state.history_rows = fetch_user_history(user_id, None, None, None, "All")
            st.session_state.history_selected = None
            st.session_state.history_details = []
            st.session_state.history_mode = "list"
            st.experimental_rerun()

        if apply_clicked:
            start_dt = None; end_dt = None
            if use_date and isinstance(date_range_val, tuple) and len(date_range_val) == 2:
                start_dt = datetime.combine(date_range_val[0], time.min)
                end_dt = datetime.combine(date_range_val[1], time.max)
            cmd_id_val = None
            if command_id_input and command_id_input.strip().isdigit():
                cmd_id_val = int(command_id_input.strip())
            rows = fetch_user_history(user_id, start_dt.isoformat() if start_dt else None, end_dt.isoformat() if end_dt else None, cmd_id_val, type_choice)
            st.session_state.history_rows = rows
            st.session_state.history_selected = None
            st.session_state.history_details = []
            st.session_state.history_mode = "list"
            st.experimental_rerun()

    rows = st.session_state.history_rows

    st.write("#### Actions")
    st.caption("Click **View details** on any row to preview the command and all its contexts.")

    h1, h2, h3, h4, h5 = st.columns([0.8, 3.0, 1.0, 1.6, 1.2])
    cell_style = "background-color:#D3D3D3; color:black; padding:8px; border-radius:4px; text-align:center;"

    with h1:
        st.markdown(f"<div class='header-row' style='{cell_style}'>ID</div>", unsafe_allow_html=True)
    with h2:
        st.markdown(f"<div class='header-row' style='{cell_style}'>Command</div>", unsafe_allow_html=True)
    with h3:
        st.markdown(f"<div class='header-row' style='{cell_style}'>Type</div>", unsafe_allow_html=True)
    with h4:
        st.markdown(f"<div class='header-row' style='{cell_style}'>Processed Time</div>", unsafe_allow_html=True)
    with h5:
        st.markdown(f"<div class='header-row' style='{cell_style}'>View details</div>", unsafe_allow_html=True)

    if not rows:
        st.info("No history found. Apply filters or add activity.")
        return

    for i, r in enumerate(rows):
        c1, c2, c3, c4, c5 = st.columns([0.8, 3.0, 1.0, 1.6, 1.2])
        with c1:
            st.markdown(f"<div class='row-wrap' style='{cell_style}'>{r['command_id']}</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(
                f"<div class='row-wrap' style='{cell_style} white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{html.escape(r.get('command_text', '') or '')}</div>",
                unsafe_allow_html=True
            )
        with c3:
            badge_cls = "badge-dyn" if r["action"] == "Dynamic" else "badge-stat"
            st.markdown(f"<div class='row-wrap'><span class='badge {badge_cls}'>{r['action']}</span></div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='row-wrap' style='{cell_style}'>{r['processed_time']}</div>", unsafe_allow_html=True)
        with c5:
            if st.button("  View details", key=f"view_details_{i}_{r['command_id']}_{r['action']}"):
                st.session_state.history_selected = r
                st.session_state.history_details = fetch_contexts_for_command(r["command_id"])
                st.session_state.history_mode = "detail"
                st.experimental_rerun()

    # detail view
    if st.session_state.history_mode == "detail":
        if st.button("⬅ Back to History", key="btn_back_to_history"):
            st.session_state.history_mode = "list"
            st.session_state.history_selected = None
            st.experimental_rerun()

        sel = st.session_state.history_selected
        details = st.session_state.history_details
        if not sel:
            st.warning("No record selected.")
            return

        st.markdown("<h2>🔎 Details</h2>", unsafe_allow_html=True)
        st.markdown(f"**Command ID:** `{sel['command_id']}`")
        st.markdown(f"**Action:** `{sel['action']}`")
        st.markdown(f"**Processed at:** `{sel['processed_time']}`")
        st.markdown("**Command:**")
        st.code(sel.get("command_text") or "", language="bash")

        if not details:
            st.warning("No contexts found for this command.")
            return

        st.markdown("**Context Lines (Grouped by Arguments):**")
        for idx, arg in enumerate(details, start=1):
            ctx_lines = arg.get("context_lines", "")
            if not ctx_lines or not ctx_lines.strip():
                continue
            clean_ctx = html.escape(ctx_lines.replace("\\n", "\n").replace("\\\\", "\\").strip())
            full_cmd = html.escape(arg.get("full_command_line", "") or "")
            st.markdown(
                f"""
                <div class="context-box">
                    <div style="font-weight:600; margin-bottom:6px; color:#333;">🧾 Argument {idx}</div>
                    <div style="margin-bottom:10px; color:black;"><strong>Full Command:</strong> <code>{full_cmd}</code></div>
                    <div style="font-family:monospace; white-space:pre-wrap; word-wrap:break-word;
                                font-size:15px; color:black;">
                        {clean_ctx}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
