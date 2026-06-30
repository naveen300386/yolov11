import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any
from database.database import get_db
from database import crud
from config.settings import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_EMAIL


def init_auth():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    _ensure_admin()


def _ensure_admin():
    try:
        with get_db() as db:
            crud.ensure_admin_exists(db, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD)
    except Exception:
        pass


def login(username: str, password: str) -> bool:
    try:
        with get_db() as db:
            user = crud.authenticate_user(db, username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "google_id": user.google_id,
                }
                return True
    except Exception as e:
        st.error(f"Login error: {e}")
    return False


def login_with_google(google_id: str, email: str, name: str) -> bool:
    try:
        with get_db() as db:
            user = crud.get_user_by_google_id(db, google_id)
            if not user:
                user = crud.get_user_by_email(db, email)
                if user:
                    user.google_id = google_id
                    user.last_login = datetime.utcnow()
                else:
                    username = _generate_username(email, name)
                    user = crud.create_google_user(db, username, email, google_id)
            if user and user.is_active:
                user.last_login = datetime.utcnow()
                st.session_state.authenticated = True
                st.session_state.user = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "google_id": user.google_id,
                }
                return True
    except Exception as e:
        st.error(f"Google login error: {e}")
    return False


def _generate_username(email: str, name: str) -> str:
    base = email.split("@")[0].replace(".", "_").replace("-", "_").lower()[:20]
    with get_db() as db:
        if not crud.get_user_by_username(db, base):
            return base
        for i in range(2, 100):
            candidate = f"{base}_{i}"
            if not crud.get_user_by_username(db, candidate):
                return candidate
    return base


def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    for key in ["google_oauth_state", "oauth_token"]:
        st.session_state.pop(key, None)


def require_auth() -> bool:
    init_auth()
    if not st.session_state.get("authenticated"):
        st.warning("Please log in to access this page.")
        if st.button("Go to Login"):
            st.switch_page("app.py")
        st.stop()
        return False
    return True


def require_admin():
    require_auth()
    if st.session_state.user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()


def get_current_user() -> Optional[Dict[str, Any]]:
    return st.session_state.get("user")


def is_admin() -> bool:
    user = get_current_user()
    return user is not None and user.get("role") == "admin"


def register_user(username: str, email: str, password: str, confirm_password: str) -> tuple[bool, str]:
    if password != confirm_password:
        return False, "Passwords do not match."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    try:
        with get_db() as db:
            if crud.get_user_by_username(db, username):
                return False, "Username already taken."
            if email and crud.get_user_by_email(db, email):
                return False, "Email already registered."
            crud.create_user(db, username, email, password, role="user")
            return True, "Account created successfully. Please log in."
    except Exception as e:
        return False, f"Registration failed: {e}"
