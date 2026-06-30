import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import time

from auth.auth_manager import require_auth, get_current_user, is_admin
from database.database import get_db, init_db
from database import crud
from utils.helpers import sidebar_user_info, confidence_slider, model_selector, device_selector

st.set_page_config(page_title="Camera Management", page_icon="📡", layout="wide")
init_db()
require_auth()
sidebar_user_info()

user = get_current_user()

st.title("📡 Camera Management")
st.markdown("Add, manage, and monitor RTSP/IP cameras with live YOLO11 detection.")

tab_list, tab_add, tab_monitor = st.tabs(["📋 My Cameras", "➕ Add Camera", "🔴 Live Monitor"])

with tab_list:
    with get_db() as db:
        uid = None if is_admin() else user["id"]
        cameras = crud.get_cameras(db, user_id=uid)

    if not cameras:
        st.info("No cameras configured yet. Add one in the **Add Camera** tab.")
    else:
        for cam in cameras:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 4, 2, 1])
                with col1:
                    status = "🟢 Active" if cam.is_active else "🔴 Inactive"
                    st.markdown(f"**{cam.name}** {status}")
                    if cam.location:
                        st.caption(f"📍 {cam.location}")
                with col2:
                    st.code(cam.rtsp_url, language=None)
                with col3:
                    if cam.description:
                        st.caption(cam.description)
                    st.caption(f"Added: {cam.created_at.strftime('%Y-%m-%d') if cam.created_at else 'N/A'}")
                with col4:
                    col_edit, col_del = st.columns(2)
                    with col_edit:
                        if st.button("✏️", key=f"edit_{cam.id}", help="Edit camera"):
                            st.session_state[f"editing_{cam.id}"] = True
                    with col_del:
                        if st.button("🗑️", key=f"del_{cam.id}", help="Delete camera"):
                            with get_db() as db:
                                crud.delete_camera(db, cam.id)
                            st.success(f"Deleted camera: {cam.name}")
                            st.rerun()

                if st.session_state.get(f"editing_{cam.id}"):
                    with st.form(f"edit_form_{cam.id}"):
                        new_name = st.text_input("Name", value=cam.name)
                        new_url = st.text_input("RTSP URL", value=cam.rtsp_url)
                        new_desc = st.text_input("Description", value=cam.description or "")
                        new_loc = st.text_input("Location", value=cam.location or "")
                        new_active = st.checkbox("Active", value=cam.is_active)
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.form_submit_button("💾 Save", use_container_width=True):
                                with get_db() as db:
                                    crud.update_camera(db, cam.id, name=new_name, rtsp_url=new_url, description=new_desc, location=new_loc, is_active=new_active)
                                st.session_state.pop(f"editing_{cam.id}", None)
                                st.success("Camera updated.")
                                st.rerun()
                        with c2:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                st.session_state.pop(f"editing_{cam.id}", None)
                                st.rerun()
                st.markdown("---")

with tab_add:
    st.subheader("Add New Camera")
    with st.form("add_camera_form"):
        cam_name = st.text_input("Camera Name *", placeholder="e.g. Front Door")
        cam_url = st.text_input(
            "RTSP / IP Camera URL *",
            placeholder="rtsp://user:pass@192.168.1.100:554/stream",
        )
        cam_desc = st.text_input("Description", placeholder="Optional description")
        cam_loc = st.text_input("Location", placeholder="e.g. Building A, Floor 2")
        cam_active = st.checkbox("Mark as active", value=True)

        submitted = st.form_submit_button("➕ Add Camera", type="primary")
        if submitted:
            if not cam_name or not cam_url:
                st.error("Camera name and URL are required.")
            else:
                with get_db() as db:
                    crud.create_camera(db, user["id"], cam_name, cam_url, cam_desc, cam_loc)
                st.success(f"Camera '{cam_name}' added successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("Supported URL Formats")
    st.code("""
# RTSP (most common)
rtsp://username:password@192.168.1.100:554/stream1
rtsp://admin:pass@10.0.0.50/h264Preview_01_main

# HTTP MJPEG streams
http://192.168.1.100:8080/video

# USB/local webcam (number)
0   # First webcam
1   # Second webcam

# Video file (for testing)
/path/to/video.mp4
    """)

with tab_monitor:
    st.subheader("Live Camera Monitor")

    with get_db() as db:
        uid = None if is_admin() else user["id"]
        cameras = crud.get_cameras(db, user_id=uid)

    active_cams = [c for c in cameras if c.is_active]

    if not active_cams:
        st.info("No active cameras. Add cameras and mark them as active.")
        st.stop()

    with st.sidebar:
        st.subheader("Monitor Settings")
        selected_cam_id = st.selectbox(
            "Select camera",
            options=[c.id for c in active_cams],
            format_func=lambda cid: next((c.name for c in active_cams if c.id == cid), str(cid)),
        )
        mon_model = model_selector("mon_model")
        mon_conf = confidence_slider("mon_conf", 0.5)
        mon_device = device_selector("mon_device")
        enable_detection = st.checkbox("Enable YOLO detection", value=True)
        update_interval = st.slider("Refresh interval (s)", 0.1, 5.0, 0.5, 0.1)

    selected_cam = next((c for c in active_cams if c.id == selected_cam_id), None)
    if not selected_cam:
        st.warning("Select a camera from the sidebar.")
        st.stop()

    st.markdown(f"**Monitoring:** {selected_cam.name} — `{selected_cam.rtsp_url}`")

    col_stream, col_stats = st.columns([3, 1])

    run_monitor = st.toggle("▶ Start Live Monitor", value=False)

    if run_monitor:
        try:
            import cv2
            from detection.yolo_detector import YOLODetector, YOLO_AVAILABLE

            frame_placeholder = col_stream.empty()
            stats_placeholder = col_stats.empty()
            stop_btn = st.button("⏹ Stop", type="secondary")

            detector = YOLODetector.get_instance(mon_model, mon_device) if enable_detection and YOLO_AVAILABLE else None

            cap = cv2.VideoCapture(selected_cam.rtsp_url)
            if not cap.isOpened():
                st.error(f"Cannot open stream: {selected_cam.rtsp_url}")
                st.stop()

            frame_count = 0
            total_detections = 0

            while not stop_btn:
                ret, frame = cap.read()
                if not ret:
                    st.warning("Stream lost. Reconnecting...")
                    break

                frame_count += 1
                detections = []

                if detector:
                    annotated, detections = detector.detect_frame(frame, mon_conf)
                    total_detections += len(detections)
                    display_frame = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                else:
                    display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                frame_placeholder.image(display_frame, use_container_width=True, caption=f"Frame {frame_count}")

                with stats_placeholder.container():
                    st.metric("Frame #", frame_count)
                    st.metric("Detections (this frame)", len(detections))
                    st.metric("Total Objects Seen", total_detections)
                    if detections:
                        from utils.helpers import summarize_detections
                        summary = summarize_detections(detections)
                        st.markdown("**This frame:**")
                        for cls, cnt in sorted(summary.items(), key=lambda x: -x[1])[:5]:
                            st.markdown(f"- **{cls}**: {cnt}")

                time.sleep(update_interval)

            cap.release()
            st.info("Stream stopped.")

        except ImportError:
            st.error("OpenCV not installed. Run: `pip install opencv-python-headless`")
        except Exception as e:
            st.error(f"Stream error: {e}")
    else:
        col_stream.info("Toggle **Start Live Monitor** to begin streaming.")
        with col_stats:
            st.markdown("**Camera Details**")
            st.markdown(f"**Name:** {selected_cam.name}")
            st.markdown(f"**URL:** `{selected_cam.rtsp_url}`")
            if selected_cam.description:
                st.markdown(f"**Description:** {selected_cam.description}")
            if selected_cam.location:
                st.markdown(f"**Location:** {selected_cam.location}")
