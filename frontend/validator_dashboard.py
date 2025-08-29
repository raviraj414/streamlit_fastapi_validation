# frontend/validator_dashboard.py
import streamlit as st
import html
from datetime import datetime, timedelta

from api_client import (
    get_commands_with_contexts,
    insert_dynamic_command,
    insert_static_command,
    update_last_processed_cmd,
    get_last_processed_cmd_id,
    get_all_validators,
    get_validator_stats,
    get_user_counts_by_role,
    get_recently_active_validators,
)

from validator_history import render_history_for_user  # reuse history UI

# small CSS from original file (kept)
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

def _ensure_state():
    if "cmds_data" not in st.session_state:
        st.session_state.cmds_data = get_commands_with_contexts()
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "sub_idx" not in st.session_state:
        st.session_state.sub_idx = {}
    if "nav" not in st.session_state:
        st.session_state.nav = "dashboard"

def _set_nav(target: str):
    st.session_state.nav = target

def _navbar():
    try:
        st.sidebar.image("C:\\Users\\rtekale\\Downloads\\ptclogo.png", width=60)
    except Exception:
        pass
    st.sidebar.write(" ")
    st.sidebar.button("📋 Dashboard", key="btn_nav_dashboard", on_click=_set_nav, args=("dashboard",))
    st.sidebar.button("📜 History", key="btn_nav_history", on_click=_set_nav, args=("history",))
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Logout", key="btn_logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

# History rendering will call the separate module
def validator_dashboard():
    user = st.session_state.get("user")
    if not user or user["role"].lower() != "validator":
        st.warning("Unauthorized or invalid role.")
        return

    _ensure_state()
    _navbar()

    if st.session_state.nav == "history":
        # choose validator_history view entry
        render_history_for_user(user)
        return

    # Dashboard main view
    st.markdown("<h1 class='h-center'> Command Context Classifier</h1>", unsafe_allow_html=True)

    all_data = st.session_state.cmds_data
    grouped = {}
    for row in all_data:
        cmd_id = row["command_id"]
        grouped.setdefault(cmd_id, []).append(row)

    cmd_ids = list(grouped.keys())
    idx = st.session_state.current_index

    if idx >= len(cmd_ids):
        st.success("🎉 All commands reviewed!")
        return

    cmd_id = cmd_ids[idx]
    arg_list = grouped[cmd_id]

    sub_idx = st.session_state.sub_idx.get(cmd_id, 0)
    if sub_idx >= len(arg_list):
        sub_idx = 0

    argument = arg_list[sub_idx]

    st.markdown(f"### 🆔 Command ID: {cmd_id}")
    st.markdown(
        f"<pre class='command-pre'>{html.escape(argument['full_command_line'] or '')}</pre>",
        unsafe_allow_html=True
    )

    context = argument.get('context_lines') or "No context found."
    clean_context = "\n".join(line for line in (context.splitlines() if context else []))

    st.markdown(
    f"""
    <div class="context-box" style="background-color:#D3D3D3; padding:15px; border-radius:8px;">
        <h4 style="margin-top:0; margin-bottom:10px; color:black;">📄 Context Lines</h4>
        <div style="font-family:monospace; white-space:pre-wrap; word-wrap:break-word; 
                    font-size:15px; color:black;">
            {html.escape(clean_context)}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

    if st.button("➡️ Next Context", key=f"btn_next_ctx_{cmd_id}_{sub_idx}"):
        st.session_state.sub_idx[cmd_id] = (sub_idx + 1) % len(arg_list)
        st.rerun()

    col_dyn, col_stat = st.columns(2)
    with col_dyn:
        if st.button("✅ Mark as Dynamic", key=f"btn_mark_dyn_{cmd_id}_{sub_idx}"):
            insert_dynamic_command(user["id"], cmd_id, argument['full_command_line'])
            update_last_processed_cmd(user["id"], idx + 1)
            st.session_state.current_index += 1
            st.rerun()

    with col_stat:
        if st.button("✅ Mark as Static", key=f"btn_mark_stat_{cmd_id}_{sub_idx}"):
            insert_static_command(user["id"], cmd_id, argument['full_command_line'])
            update_last_processed_cmd(user["id"], idx + 1)
            st.session_state.current_index += 1
            st.rerun()

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Previous Command", key=f"btn_prev_cmd_{cmd_id}"):
            st.session_state.current_index = max(0, idx - 1)
            new_cmd_id = cmd_ids[st.session_state.current_index]
            st.session_state.sub_idx[new_cmd_id] = 0
            st.rerun()
    with col2:
        if st.button("➡️ Next Command", key=f"btn_next_cmd_{cmd_id}"):
            st.session_state.current_index = min(len(cmd_ids) - 1, idx + 1)
            new_cmd_id = cmd_ids[st.session_state.current_index]
            st.session_state.sub_idx[new_cmd_id] = 0
            st.rerun()
