import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st

from auth.auth_manager import require_auth, get_current_user
from database.database import get_db, init_db
from database import crud
from utils.helpers import sidebar_user_info
from config.settings import (
    AVAILABLE_MODELS, DEFAULT_MODEL, DEFAULT_CONFIDENCE, DEFAULT_DEVICE,
    DEFAULT_IOU, MAX_IMAGE_SIZE_MB, MAX_VIDEO_SIZE_MB
)

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
init_db()
require_auth()
sidebar_user_info()

user = get_current_user()

st.title("⚙️ Settings")
st.markdown("Configure detection parameters, account settings, and system preferences.")

tab_detect, tab_account, tab_system = st.tabs(["🎯 Detection", "👤 Account", "🖥️ System Info"])

with tab_detect:
    st.subheader("Default Detection Settings")
    st.markdown("These values pre-fill controls on detection pages.")

    with get_db() as db:
        saved_model = crud.get_setting(db, f"user_{user['id']}_default_model", DEFAULT_MODEL)
        saved_conf = float(crud.get_setting(db, f"user_{user['id']}_default_confidence", str(DEFAULT_CONFIDENCE)))
        saved_device = crud.get_setting(db, f"user_{user['id']}_default_device", DEFAULT_DEVICE)
        saved_iou = float(crud.get_setting(db, f"user_{user['id']}_default_iou", str(DEFAULT_IOU)))

    with st.form("detection_settings_form"):
        st.markdown("**Model Selection**")
        sel_model = st.selectbox(
            "Default YOLO model",
            AVAILABLE_MODELS,
            index=AVAILABLE_MODELS.index(saved_model) if saved_model in AVAILABLE_MODELS else 0,
            help="Larger models are more accurate but slower. n=nano, s=small, m=medium, l=large, x=extra-large",
        )

        st.markdown("**Inference Parameters**")
        col1, col2 = st.columns(2)
        with col1:
            sel_conf = st.slider("Default confidence threshold", 0.1, 1.0, saved_conf, 0.05)
        with col2:
            sel_iou = st.slider("Default IoU threshold", 0.1, 1.0, saved_iou, 0.05)

        st.markdown("**Compute Device**")
        from detection.yolo_detector import YOLODetector
        cuda_ok = YOLODetector.is_cuda_available()
        device_opts = ["cpu"]
        if cuda_ok:
            device_opts.insert(0, "cuda")
        dev_idx = device_opts.index(saved_device) if saved_device in device_opts else 0
        sel_device = st.selectbox(
            "Default device",
            device_opts,
            index=dev_idx,
            help="CUDA uses GPU (NVIDIA required). CPU is the universal fallback.",
        )

        if not cuda_ok and sel_device == "cuda":
            st.warning("CUDA is not available on this machine. CPU will be used.")

        if st.form_submit_button("💾 Save Detection Settings", type="primary"):
            with get_db() as db:
                crud.set_setting(db, f"user_{user['id']}_default_model", sel_model, "Default YOLO model")
                crud.set_setting(db, f"user_{user['id']}_default_confidence", str(sel_conf))
                crud.set_setting(db, f"user_{user['id']}_default_iou", str(sel_iou))
                crud.set_setting(db, f"user_{user['id']}_default_device", sel_device)
            st.success("Detection settings saved!")

    st.markdown("---")
    st.subheader("Model Reference")
    st.markdown("""
    | Model | Size | Speed | Accuracy | Use Case |
    |-------|------|-------|----------|----------|
    | yolo11n | Nano | ⚡⚡⚡⚡⚡ | ⭐⭐ | Real-time on CPU |
    | yolo11s | Small | ⚡⚡⚡⚡ | ⭐⭐⭐ | Fast with decent accuracy |
    | yolo11m | Medium | ⚡⚡⚡ | ⭐⭐⭐⭐ | Balanced |
    | yolo11l | Large | ⚡⚡ | ⭐⭐⭐⭐⭐ | High accuracy |
    | yolo11x | Extra | ⚡ | ⭐⭐⭐⭐⭐ | Maximum accuracy |

    Models download automatically on first use (~2–130 MB depending on size).
    """)

with tab_account:
    st.subheader("Account Information")
    st.markdown(f"**Username:** `{user['username']}`")
    st.markdown(f"**Email:** {user.get('email') or 'Not set'}")
    st.markdown(f"**Role:** `{user['role']}`")
    st.markdown(f"**Auth method:** {'Google OAuth' if user.get('google_id') else 'Username/Password'}")

    st.markdown("---")
    st.subheader("Change Password")
    if user.get("google_id") and not user.get("password_hash"):
        st.info("You signed in with Google. To set a password for direct login, use the form below.")

    with st.form("change_password_form"):
        if not user.get("google_id"):
            current_pass = st.text_input("Current Password", type="password")
        else:
            current_pass = None
        new_pass = st.text_input("New Password", type="password", help="Minimum 6 characters")
        confirm_pass = st.text_input("Confirm New Password", type="password")

        if st.form_submit_button("🔒 Change Password"):
            if new_pass != confirm_pass:
                st.error("New passwords do not match.")
            elif len(new_pass) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                with get_db() as db:
                    db_user = crud.get_user_by_id(db, user["id"])
                    if db_user:
                        if not user.get("google_id") and current_pass:
                            if not crud.verify_password(current_pass, db_user.password_hash or ""):
                                st.error("Current password is incorrect.")
                                st.stop()
                        crud.update_user(db, user["id"], password=new_pass)
                        st.success("Password changed successfully!")
                    else:
                        st.error("User not found.")

    st.markdown("---")
    st.subheader("Change Email")
    with st.form("change_email_form"):
        new_email = st.text_input("New Email", value=user.get("email") or "", placeholder="your@email.com")
        if st.form_submit_button("📧 Update Email"):
            if not new_email:
                st.error("Email cannot be empty.")
            else:
                with get_db() as db:
                    existing = crud.get_user_by_email(db, new_email)
                    if existing and existing.id != user["id"]:
                        st.error("Email already in use by another account.")
                    else:
                        crud.update_user(db, user["id"], email=new_email)
                        st.session_state.user["email"] = new_email
                        st.success("Email updated!")

with tab_system:
    st.subheader("System Information")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Python Environment**")
        import sys as _sys
        st.code(f"Python {_sys.version}")

        try:
            import streamlit
            st.markdown(f"Streamlit: `{streamlit.__version__}`")
        except ImportError:
            st.markdown("Streamlit: not detected (running)")

        try:
            from ultralytics import YOLO
            import ultralytics
            st.markdown(f"Ultralytics: `{ultralytics.__version__}`")
        except ImportError:
            st.markdown("Ultralytics: ⚠️ not installed")

        try:
            import cv2
            st.markdown(f"OpenCV: `{cv2.__version__}`")
        except ImportError:
            st.markdown("OpenCV: ⚠️ not installed")

        try:
            import numpy as np
            st.markdown(f"NumPy: `{np.__version__}`")
        except ImportError:
            st.markdown("NumPy: ⚠️ not installed")

    with col2:
        st.markdown("**Hardware**")
        from detection.yolo_detector import YOLODetector
        cuda_available = YOLODetector.is_cuda_available()
        st.markdown(f"CUDA available: {'✅ Yes' if cuda_available else '❌ No'}")

        if cuda_available:
            try:
                import torch
                st.markdown(f"CUDA version: `{torch.version.cuda}`")
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    mem_gb = props.total_memory / (1024 ** 3)
                    st.markdown(f"GPU {i}: `{props.name}` ({mem_gb:.1f} GB)")
            except Exception as e:
                st.markdown(f"GPU info: {e}")
        else:
            try:
                import psutil
                mem = psutil.virtual_memory()
                st.markdown(f"RAM: {mem.available / (1024**3):.1f} GB available of {mem.total / (1024**3):.1f} GB")
            except ImportError:
                pass

        st.markdown("**Storage**")
        from config.settings import UPLOAD_DIR, OUTPUT_DIR, DATA_DIR
        for label, path in [("Uploads", UPLOAD_DIR), ("Outputs", OUTPUT_DIR), ("Database", DATA_DIR)]:
            try:
                size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                st.markdown(f"{label}: `{size / (1024*1024):.1f} MB`")
            except Exception:
                st.markdown(f"{label}: `N/A`")

    st.markdown("---")
    st.subheader("Cache Management")
    if st.button("🔄 Clear Model Cache", help="Unloads cached YOLO models from memory"):
        from detection.yolo_detector import YOLODetector
        YOLODetector.clear_instances()
        st.success("Model cache cleared. Models will reload on next detection.")

    if st.button("🗑️ Clear Old Output Files (> 24h)", type="secondary"):
        from utils.file_utils import cleanup_old_files
        from config.settings import OUTPUT_DIR
        cleanup_old_files(OUTPUT_DIR, 24)
        cleanup_old_files(UPLOAD_DIR, 24)
        st.success("Old files cleaned up.")
