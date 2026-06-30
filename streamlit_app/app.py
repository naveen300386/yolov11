import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="YOLO11 Detection Platform",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Safe startup ──────────────────────────────────────────────────────────────
try:
    from config.settings import ensure_dirs
    ensure_dirs()
except Exception as e:
    st.error(f"Startup error (dirs): {e}")
    st.stop()

try:
    from database.database import init_db
    init_db()
except Exception as e:
    st.error(f"Startup error (database): {e}")
    st.stop()

try:
    from auth.auth_manager import init_auth, login, logout, register_user, login_with_google
    from auth.google_oauth import is_google_oauth_configured, get_google_auth_url, handle_oauth_callback
    init_auth()
except Exception as e:
    st.error(f"Startup error (auth): {e}")
    st.stop()

# ── Google OAuth callback ─────────────────────────────────────────────────────
try:
    if st.query_params.get("code") and st.query_params.get("state"):
        user_info = handle_oauth_callback()
        if user_info:
            success = login_with_google(
                google_id=user_info.get("sub", ""),
                email=user_info.get("email", ""),
                name=user_info.get("name", ""),
            )
            if success:
                st.rerun()
            else:
                st.error("Google login failed. Please try again.")
except Exception:
    pass


def show_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<h1 style='text-align:center;'>🎯 YOLO11 Detection</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center; opacity:0.7;'>Production-ready object detection platform</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            with st.form("login_form"):
                username  = st.text_input("Username", placeholder="Enter username")
                password  = st.text_input("Password", type="password", placeholder="Enter password")
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                if submitted:
                    if username and password:
                        if login(username, password):
                            st.success("Welcome back!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                    else:
                        st.warning("Please enter both username and password.")

            if is_google_oauth_configured():
                st.markdown("---")
                auth_url = get_google_auth_url()
                st.markdown(
                    f"""<a href="{auth_url}" target="_self" style="
                        display: block;
                        text-align: center;
                        padding: 10px 20px;
                        background: #4285f4;
                        color: white;
                        border-radius: 6px;
                        text-decoration: none;
                        font-weight: 500;
                        margin-top: 8px;
                    ">🔵 Continue with Google</a>""",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("💡 Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in Streamlit secrets to enable Google sign-in.")

        with tab_register:
            with st.form("register_form"):
                new_user  = st.text_input("Username", placeholder="Choose a username", key="reg_user")
                new_email = st.text_input("Email", placeholder="your@email.com", key="reg_email")
                new_pass  = st.text_input("Password", type="password", placeholder="Min 6 characters", key="reg_pass")
                new_pass2 = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="reg_pass2")
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                if reg_submitted:
                    ok, msg = register_user(new_user, new_email, new_pass, new_pass2)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        st.markdown("---")
        st.markdown(
            "<p style='text-align:center; font-size:12px; opacity:0.5;'>Default admin: <b>admin</b> / <b>admin123</b> — change after first login</p>",
            unsafe_allow_html=True,
        )


def show_home():
    from utils.helpers import sidebar_user_info
    sidebar_user_info()

    user = st.session_state.user
    st.markdown(f"# 🎯 Welcome, {user['username']}!")
    st.markdown("Use the sidebar to navigate between features.")

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info("🖼️ **Image Detection**\nUpload images for instant object detection")
    with col2:
        st.info("🎬 **Video Detection**\nProcess video files with YOLO11")
    with col3:
        st.info("📸 **Webcam**\nReal-time detection from your camera")
    with col4:
        st.info("📡 **IP/RTSP Cameras**\nMonitor multiple network cameras")

    st.markdown("---")
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.success("📊 **Dashboard**\nAnalytics and detection history charts")
    with col6:
        st.success("📋 **History**\nBrowse and download all past detections")
    with col7:
        st.success("⚙️ **Settings**\nModel selection, confidence, and device")
    with col8:
        if user.get("role") == "admin":
            st.success("👤 **Admin**\nManage users and system settings")

    st.markdown("---")
    st.markdown(
        "### Quick Start\n"
        "1. Navigate to **Image Detection** in the sidebar\n"
        "2. Upload an image and click **Run Detection**\n"
        "3. View results and download annotated image\n"
        "4. Check **Dashboard** for usage analytics\n\n"
        "> **Default admin credentials:** `admin` / `admin123` — please change in Admin panel"
    )


if st.session_state.get("authenticated"):
    show_home()
else:
    show_login()
