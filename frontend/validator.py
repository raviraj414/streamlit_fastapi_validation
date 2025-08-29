# frontend/validator.py
import streamlit as st
from api_client import signup_user, login_user, get_last_processed_cmd_id
st.set_page_config(page_title="Creo Trail Validator", layout="centered")

# -------------------- Session State --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

def signup():
    st.markdown("<h2 style='text-align:center; color:#3b82f6;'>🔧 Creo Trail Validator</h2>", unsafe_allow_html=True)
    st.write("<p style='text-align:center;'>Create your account</p>", unsafe_allow_html=True)

    with st.form("signup_form", clear_on_submit=True):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["Viewer", "Validator", "Admin"])
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Account")

        if submitted:
            if not name or not email or not password:
                st.error("Please fill all required fields.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                ok = signup_user(name, email, password, role)
                if ok:
                    st.success("✅ Signup successful! Please login.")
                else:
                    st.error("Signup failed. Email may already exist.")

    st.write("<p style='text-align:center;'>Already have an account? <a href='#' style='color:#3b82f6;'>Sign in</a></p>", unsafe_allow_html=True)

def login():
    st.markdown("<h2 style='text-align:center; color:#3b82f6;'>🔧 Creo Trail Validator</h2>", unsafe_allow_html=True)
    st.write("<p style='text-align:center;'>Sign in to your account</p>", unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        login_type = st.selectbox("Role", ["Validator", "Viewer", "Admin"])
        submitted = st.form_submit_button("Sign In")

        if submitted:
            if not email or not password:
                st.error("Please enter email and password.")
            else:
                user = login_user(email, password)
                if user:
                    if user["role"].lower() != login_type.lower():
                        st.error("Incorrect role selected.")
                        return

                    st.session_state.logged_in = True
                    st.session_state.user = user

                    if login_type == "Validator":
                        st.session_state.current_index = get_last_processed_cmd_id(user["id"]) or 0
                        st.session_state.pop("cmds_data", None)
                        st.session_state.pop("sub_idx", None)

                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials.")

    st.write("<p style='text-align:center;'>Don't have an account? <a href='#' style='color:#3b82f6;'>Sign up</a></p>", unsafe_allow_html=True)
    st.info("Getting Started:\nCreate an account using the signup link above, or ask your administrator for login credentials.")

# -------------------- App Entry --------------------
if not st.session_state.logged_in:
    menu = ["Login", "Sign Up"]
    choice = st.sidebar.radio("Menu", menu)
    if choice == "Login":
        login()
    else:
        signup()
else:
    role = st.session_state.user["role"].lower()

    if role == "admin":
        import admin_dashboard
        admin_dashboard.admin_dashboard()

    elif role == "validator":
        import validator_dashboard
        validator_dashboard.validator_dashboard()

    else:
        st.title("👀 Viewer")
        st.info("Viewer dashboard coming soon.")
        if st.sidebar.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.experimental_rerun()
