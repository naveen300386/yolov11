import os
import secrets
import streamlit as st
import httpx
from typing import Optional, Dict
from config.settings import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = ["openid", "email", "profile"]


def is_google_oauth_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def get_google_auth_url() -> str:
    state = secrets.token_urlsafe(32)
    st.session_state["google_oauth_state"] = state
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


def exchange_code_for_token(code: str, state: str) -> Optional[Dict]:
    expected_state = st.session_state.get("google_oauth_state")
    if not expected_state or state != expected_state:
        return None
    try:
        with httpx.Client() as client:
            resp = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        st.error(f"OAuth token exchange error: {e}")
    return None


def get_user_info(access_token: str) -> Optional[Dict]:
    try:
        with httpx.Client() as client:
            resp = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        st.error(f"Failed to get user info: {e}")
    return None


def handle_oauth_callback() -> Optional[Dict]:
    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    if not code or not state:
        return None
    token_data = exchange_code_for_token(code, state)
    if not token_data:
        return None
    access_token = token_data.get("access_token")
    if not access_token:
        return None
    user_info = get_user_info(access_token)
    st.query_params.clear()
    return user_info
