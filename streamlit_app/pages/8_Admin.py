import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
from datetime import datetime

from auth.auth_manager import require_admin, get_current_user
from database.database import get_db, init_db
from database import crud
from utils.helpers import sidebar_user_info

st.set_page_config(page_title="Admin Panel", page_icon="👤", layout="wide")
init_db()
require_admin()
sidebar_user_info()

user = get_current_user()

st.title("👤 Admin Panel")
st.markdown("Manage users, view all detections, and configure system settings.")

tab_users, tab_detections, tab_settings, tab_logs = st.tabs(
    ["👥 Users", "📊 All Detections", "⚙️ System Settings", "📁 Database"]
)

# ─── Users Tab ────────────────────────────────────────────────────────────────
with tab_users:
    with get_db() as db:
        users = crud.get_all_users(db)

    st.subheader(f"All Users ({len(users)})")

    users_data = []
    for u in users:
        users_data.append({
            "ID": u.id,
            "Username": u.username,
            "Email": u.email or "—",
            "Role": u.role,
            "Auth": "Google" if u.google_id else "Password",
            "Active": "✅" if u.is_active else "❌",
            "Created": u.created_at.strftime("%Y-%m-%d") if u.created_at else "—",
            "Last Login": u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "Never",
        })
    df_users = pd.DataFrame(users_data)
    st.dataframe(df_users, use_container_width=True, hide_index=True)

    st.download_button(
        "📥 Export Users CSV",
        data=df_users.to_csv(index=False),
        file_name="users_export.csv",
        mime="text/csv",
    )

    st.markdown("---")
    st.subheader("Create User")
    with st.form("create_user_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_username = st.text_input("Username *")
            new_email = st.text_input("Email")
        with c2:
            new_password = st.text_input("Password *", type="password")
            new_role = st.selectbox("Role", ["user", "admin"])
        if st.form_submit_button("➕ Create User", type="primary"):
            if not new_username or not new_password:
                st.error("Username and password are required.")
            else:
                try:
                    with get_db() as db:
                        if crud.get_user_by_username(db, new_username):
                            st.error("Username already exists.")
                        else:
                            crud.create_user(db, new_username, new_email, new_password, new_role)
                            st.success(f"User '{new_username}' created with role '{new_role}'.")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader("Edit / Delete User")
    non_self_users = [u for u in users if u.id != user["id"]]
    if non_self_users:
        selected_uid = st.selectbox(
            "Select user to manage",
            options=[u.id for u in non_self_users],
            format_func=lambda uid: next(f"{u.username} ({u.role})" for u in non_self_users if u.id == uid),
        )
        selected_user = next((u for u in non_self_users if u.id == selected_uid), None)
        if selected_user:
            col1, col2, col3 = st.columns(3)
            with col1:
                new_role_sel = st.selectbox(
                    "Change role",
                    ["user", "admin"],
                    index=0 if selected_user.role == "user" else 1,
                    key="edit_role",
                )
                if st.button("🔄 Update Role"):
                    with get_db() as db:
                        crud.update_user(db, selected_uid, role=new_role_sel)
                    st.success(f"Role updated to '{new_role_sel}'.")
                    st.rerun()
            with col2:
                new_active = st.checkbox("Active", value=selected_user.is_active, key="edit_active")
                if st.button("🔄 Update Status"):
                    with get_db() as db:
                        crud.update_user(db, selected_uid, is_active=new_active)
                    st.success(f"User status updated.")
                    st.rerun()
            with col3:
                with st.form(f"reset_pw_{selected_uid}"):
                    reset_pw = st.text_input("New password", type="password", key="admin_reset_pw")
                    if st.form_submit_button("🔒 Reset Password"):
                        if len(reset_pw) < 6:
                            st.error("Password too short.")
                        else:
                            with get_db() as db:
                                crud.update_user(db, selected_uid, password=reset_pw)
                            st.success("Password reset.")

            st.markdown("---")
            if st.button(f"🗑️ Delete user '{selected_user.username}'", type="secondary"):
                with get_db() as db:
                    crud.delete_user(db, selected_uid)
                st.success(f"User '{selected_user.username}' deleted.")
                st.rerun()
    else:
        st.info("No other users to manage.")

# ─── All Detections Tab ───────────────────────────────────────────────────────
with tab_detections:
    with get_db() as db:
        all_dets = crud.get_detections(db, limit=200)
        all_users_map = {u.id: u.username for u in crud.get_all_users(db)}

    st.subheader(f"All Detections ({len(all_dets)})")

    if not all_dets:
        st.info("No detections recorded yet.")
    else:
        rows = []
        for d in all_dets:
            rows.append({
                "ID": d.id,
                "User": all_users_map.get(d.user_id, f"#{d.user_id}"),
                "Type": d.detection_type,
                "File": d.original_filename or "—",
                "Objects": d.objects_detected or 0,
                "Model": d.model_used or "—",
                "Device": d.device or "—",
                "Date": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else "—",
            })
        df_dets = pd.DataFrame(rows)
        st.dataframe(df_dets, use_container_width=True, hide_index=True)

        st.download_button(
            "📥 Export Detections CSV",
            data=df_dets.to_csv(index=False),
            file_name="all_detections.csv",
            mime="text/csv",
        )

        st.markdown("---")
        del_id = st.number_input("Delete detection by ID", min_value=1, step=1, key="admin_del_det")
        if st.button("🗑️ Delete Detection Record"):
            with get_db() as db:
                ok = crud.delete_detection(db, int(del_id))
            if ok:
                st.success(f"Detection {del_id} deleted.")
                st.rerun()
            else:
                st.error("Detection not found.")

# ─── System Settings Tab ──────────────────────────────────────────────────────
with tab_settings:
    st.subheader("Application Settings")
    st.caption("These settings affect the entire application.")

    with get_db() as db:
        max_upload_img = crud.get_setting(db, "max_upload_image_mb", "50")
        max_upload_vid = crud.get_setting(db, "max_upload_video_mb", "500")
        allow_registration = crud.get_setting(db, "allow_registration", "true")
        default_role = crud.get_setting(db, "default_user_role", "user")

    with st.form("system_settings_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_max_img = st.number_input("Max image upload (MB)", value=int(max_upload_img), min_value=1, max_value=500)
            new_max_vid = st.number_input("Max video upload (MB)", value=int(max_upload_vid), min_value=1, max_value=5000)
        with col2:
            new_allow_reg = st.selectbox(
                "Allow public registration",
                ["true", "false"],
                index=0 if allow_registration == "true" else 1,
            )
            new_default_role = st.selectbox("Default user role", ["user", "admin"], index=0 if default_role == "user" else 1)

        if st.form_submit_button("💾 Save System Settings", type="primary"):
            with get_db() as db:
                crud.set_setting(db, "max_upload_image_mb", str(new_max_img))
                crud.set_setting(db, "max_upload_video_mb", str(new_max_vid))
                crud.set_setting(db, "allow_registration", new_allow_reg)
                crud.set_setting(db, "default_user_role", new_default_role)
            st.success("System settings saved!")

    st.markdown("---")
    st.subheader("Danger Zone")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("🗑️ Clear All Detection History", type="secondary"):
            if st.session_state.get("confirm_clear_history"):
                with get_db() as db:
                    for d in crud.get_detections(db, limit=10000):
                        crud.delete_detection(db, d.id)
                st.success("All detection history cleared.")
                st.session_state.pop("confirm_clear_history")
                st.rerun()
            else:
                st.session_state["confirm_clear_history"] = True
                st.warning("Click again to confirm deletion of ALL detection history.")
    with col_d2:
        if st.button("🗑️ Clear All Uploaded Files", type="secondary"):
            import shutil
            from config.settings import UPLOAD_DIR, OUTPUT_DIR
            for d in [UPLOAD_DIR, OUTPUT_DIR]:
                shutil.rmtree(str(d), ignore_errors=True)
                d.mkdir(exist_ok=True)
            st.success("All uploaded and output files deleted.")

# ─── Database Tab ─────────────────────────────────────────────────────────────
with tab_logs:
    st.subheader("Database Overview")
    from config.settings import DATA_DIR, DATABASE_URL
    st.markdown(f"**Database path:** `{DATABASE_URL}`")

    with get_db() as db:
        user_count = len(crud.get_all_users(db))
        det_count = len(crud.get_detections(db, limit=100000))
        cam_count = len(crud.get_cameras(db))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Users", user_count)
    with col2:
        st.metric("Detections", det_count)
    with col3:
        st.metric("Cameras", cam_count)

    st.markdown("---")
    db_file = DATA_DIR / "yolo_detection.db"
    if db_file.exists():
        db_size = db_file.stat().st_size / (1024 * 1024)
        st.markdown(f"**Database file size:** {db_size:.2f} MB")

        with open(str(db_file), "rb") as f:
            st.download_button(
                "📥 Download Database Backup",
                data=f,
                file_name=f"yolo_detection_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                mime="application/octet-stream",
            )
