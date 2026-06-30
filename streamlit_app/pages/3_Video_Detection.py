import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import time

from auth.auth_manager import require_auth, get_current_user
from database.database import get_db, init_db
from database import crud
from utils.helpers import sidebar_user_info, show_detection_table, confidence_slider, model_selector, device_selector
from utils.file_utils import save_uploaded_file, is_valid_video
from config.settings import ALLOWED_VIDEO_TYPES, MAX_VIDEO_SIZE_MB

st.set_page_config(page_title="Video Detection", page_icon="🎬", layout="wide")
init_db()
require_auth()
sidebar_user_info()

user = get_current_user()

st.title("🎬 Video Detection")
st.markdown("Upload a video file and run YOLO11 object detection on every frame.")

with st.sidebar:
    st.subheader("Detection Settings")
    model_name = model_selector("vid_model")
    confidence = confidence_slider("vid_conf", 0.5)
    iou = st.slider("IoU threshold", 0.1, 1.0, 0.45, 0.05, key="vid_iou")
    device = device_selector("vid_device")
    frame_skip = st.slider(
        "Frame skip",
        min_value=1,
        max_value=10,
        value=2,
        key="vid_frame_skip",
        help="Process every Nth frame (higher = faster but less detailed)",
    )
    save_result = st.checkbox("Save to history", value=True)

uploaded = st.file_uploader(
    f"Upload video (max {MAX_VIDEO_SIZE_MB} MB) — {', '.join(ALLOWED_VIDEO_TYPES)}",
    type=ALLOWED_VIDEO_TYPES,
    key="vid_upload",
)

if uploaded:
    if not is_valid_video(uploaded):
        st.error("Invalid video file type.")
        st.stop()

    size_mb = len(uploaded.getbuffer()) / (1024 * 1024)
    if size_mb > MAX_VIDEO_SIZE_MB:
        st.error(f"File too large ({size_mb:.1f} MB). Max is {MAX_VIDEO_SIZE_MB} MB.")
        st.stop()

    st.video(uploaded)
    st.caption(f"File size: {size_mb:.1f} MB")

    if st.button("🚀 Run Video Detection", type="primary", use_container_width=True):
        with st.spinner("Installing packages if needed — please wait..."):
            from detection.yolo_detector import YOLO_AVAILABLE

        if not YOLO_AVAILABLE:
            st.error("❌ Could not install or import ultralytics. Please contact the app admin.")
            st.stop()

        progress_bar = st.progress(0, text="Saving video...")
        status_text = st.empty()

        try:
            vid_path, vid_fname = save_uploaded_file(uploaded, "videos")
            progress_bar.progress(20, text="Loading YOLO model...")

            from detection.yolo_detector import YOLODetector
            detector = YOLODetector.get_instance(model_name, device)

            progress_bar.progress(40, text="Processing video... (this may take several minutes)")
            status_text.info(f"Processing video with frame skip = {frame_skip}. Large videos take longer.")

            out_path, all_detections, elapsed = detector.detect_video(
                vid_path,
                confidence=confidence,
                iou=iou,
                output_prefix=f"vid_{user['id']}",
                frame_skip=frame_skip,
            )

            progress_bar.progress(90, text="Saving results...")

            unique_classes = len(set(d.get("class_name") for d in all_detections))

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Total Objects Found", len(all_detections))
            with col_m2:
                st.metric("Unique Classes", unique_classes)
            with col_m3:
                st.metric("Processing Time", f"{elapsed:.1f}s")
            with col_m4:
                st.metric("Frame Skip", frame_skip)

            if os.path.exists(out_path):
                st.subheader("Annotated Video")
                st.video(out_path)
                with open(out_path, "rb") as f:
                    st.download_button(
                        "📥 Download Annotated Video",
                        data=f,
                        file_name=f"annotated_{uploaded.name}",
                        mime="video/mp4",
                    )

            if all_detections:
                st.subheader("Detection Summary (sample)")
                import json
                st.download_button(
                    "📥 Download Detections JSON",
                    data=json.dumps(all_detections[:500], indent=2),
                    file_name="video_detections.json",
                    mime="application/json",
                )
                show_detection_table(all_detections[:20])
                if len(all_detections) > 20:
                    st.caption(f"Showing first 20 of {len(all_detections)} detections.")

            if save_result:
                result_fname = os.path.basename(out_path) if out_path else None
                with get_db() as db:
                    crud.save_detection(
                        db,
                        user_id=user["id"],
                        detection_type="video",
                        detections=all_detections[:200],
                        model_used=model_name,
                        confidence_threshold=confidence,
                        device=device,
                        processing_time=elapsed,
                        original_filename=uploaded.name,
                        result_filename=result_fname,
                    )
                st.caption("✔ Saved to detection history")

            progress_bar.progress(100, text="Done!")
            st.success(f"✅ Video processed in {elapsed:.1f}s — {len(all_detections)} detections found.")

        except Exception as e:
            progress_bar.empty()
            st.error(f"Video detection failed: {e}")
else:
    st.info("Upload a video file to run object detection on all frames.")
    with st.expander("ℹ️ Tips for video detection"):
        st.markdown(f"""
        - Use **frame skip 2-4** for faster processing (detects every 2nd-4th frame)
        - Larger models (yolo11l, yolo11x) are slower but more accurate
        - Video is saved as MP4 with bounding boxes drawn on each frame
        - Large files ({MAX_VIDEO_SIZE_MB} MB max) may take several minutes
        - Use CUDA device if a compatible GPU is available for 5-10x speedup
        """)
