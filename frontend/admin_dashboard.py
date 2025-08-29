# frontend/admin_dashboard.py
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from api_client import (
    get_all_validators,
    get_validator_stats,
    get_user_counts_by_role,
    get_recently_active_validators,
)

from validator_history import render_history_for_user

def admin_dashboard():
    st.set_page_config(page_title="Admin Dashboard", layout="wide")
    user = st.session_state.user
    try:
        st.sidebar.image("C:\\Users\\rtekale\\Downloads\\ptclogo.png", width=60)
    except Exception:
        pass

    st.sidebar.markdown("## 📋 Navigation")
    nav_buttons = {
        "🙋 My Info": "My Info",
        "👥 Users": "Users",
        "📊 Validation": "Validation",
        "🕘 History": "History",
        "🔄 Live Command Processing": "Live Command Processing",
        "🕒 Recently Active Validators": "Recently Active Validators",
        "🏆 Leaderboard": "Leaderboard",
        "🚪 Logout": "Logout"
    }

    for i, (label, page_name) in enumerate(nav_buttons.items()):
        if st.sidebar.button(label, key=f"nav_btn_{i}"):
            if page_name == "Logout":
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.page = "Login"
                st.rerun()
            else:
                st.session_state.page = page_name

    page = st.session_state.get("page", "My Info")

    if page == "My Info":
        st.subheader("🙋 My Info")
        st.markdown(f"###  Name: `{user['name']}`")
        st.markdown(f"###  Email: `{user['email']}`")

    elif page == "Users":
        st.subheader("👥 All Users")
        data = get_user_counts_by_role()
        validator_count = data.get("validator_count", 0)
        viewer_count = data.get("viewer_count", 0)
        validator_names = data.get("validator_names", [])
        viewer_names = data.get("viewer_names", [])

        col1, col2 = st.columns(2)
        col1.metric("🧑‍🔧 Validators", validator_count)
        col2.metric("👁️ Viewers", viewer_count)

        with st.expander(" Validators List"):
            for name in validator_names:
                st.markdown(f"- 👤 **{name}**")
        with st.expander(" Viewers List"):
            for name in viewer_names:
                st.markdown(f"- 👤 **{name}**")

    elif page == "Validation":
        st.subheader(" Validator Performance")
        validators = get_all_validators()
        validator_names = {v["name"]: v["id"] for v in validators}
        selected = st.selectbox(" Select Validator", list(validator_names.keys()))

        if selected:
            stats = get_validator_stats(validator_names[selected])
            col1, col2 = st.columns(2)
            col3, col4 = st.columns(2)

            col1.metric("✅ Total Processed", stats["processed"])
            col2.metric("🕒 Remaining", stats["remaining"])
            col3.metric("🔥 Dynamic", stats["dynamic"])
            col4.metric("📦 Static", stats["static"])

            st.markdown("###  Command Breakdown")
            fig, ax = plt.subplots(figsize=(4, 2))
            ax.bar(["Dynamic", "Static"], [stats["dynamic"], stats["static"]])
            ax.set_ylabel("Count")
            st.pyplot(fig)

    elif page == "History":
        st.subheader("History")
        validators = get_all_validators()
        validator_names = {v["name"]: v["id"] for v in validators}
        selected = st.selectbox(" Select Validator", list(validator_names.keys()))
        if selected:
            selected_user = {"id": validator_names[selected], "name": selected, "role": "validator"}
            render_history_for_user(selected_user)

    elif page == "Live Command Processing":
        st.subheader(" Live Command Processing")
        validators = get_all_validators()
        st.markdown("####  Active Validators and Their Command Status")
        for v in validators:
            stats = get_validator_stats(v["id"])
            remaining = stats["remaining"]
            last_id = stats["processed"]
            st.markdown(f"**👨‍💻 {v['name']}** — Currently at Command ID: `{last_id}` | Remaining: `{remaining}`")

    elif page == "Recently Active Validators":
        st.subheader(" Recently Active Validators")
        def format_last_seen(ts):
            now = datetime.now()
            delta = now - ts
            if delta < timedelta(minutes=1):
                return "Just now"
            elif delta < timedelta(minutes=10):
                return f"{int(delta.total_seconds() // 60)} mins ago"
            elif delta < timedelta(hours=1):
                return f"{int(delta.total_seconds() // 60)} mins ago (inactive)"
            elif delta < timedelta(days=1):
                return f"{int(delta.total_seconds() // 3600)} hours ago (offline)"
            else:
                return ts.strftime("%d %b %Y, %I:%M %p")

        active_users = get_recently_active_validators()
        for user in active_users:
            last_seen = user["last_seen"]
            if isinstance(last_seen, str):
                last_seen = datetime.strptime(last_seen, "%Y-%m-%d %H:%M:%S")
            formatted = format_last_seen(last_seen)
            st.markdown(f"👤 **{user['name']}** — Last Seen: *{formatted}*")

    elif page == "Leaderboard":
        st.subheader("🏆 Top Validators")
        validators = get_all_validators()
        leaderboard = [(v["name"], get_validator_stats(v["id"])["processed"]) for v in validators]
        sorted_lb = sorted(leaderboard, key=lambda x: x[1], reverse=True)
        for i, (name, score) in enumerate(sorted_lb, 1):
            st.markdown(f"**{i}. {name}** —  `{score}` commands")
