import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import io
import json
import time

from auth.auth_manager import require_auth, get_current_user
from database.database import get_db, init_db
from database import crud
from utils.helpers import sidebar_user_info, show_detection_table, confidence_slider, model_selector, device_selector, get_image_as_bytes
from utils.file_utils import save_uploaded_file, is_valid_image
from config.settings import ALLOWED_IMAGE_TYPES

st.set_page_config(page_title="Image Detection", page_icon="🖼️", layout="wide")
init_db()
require_auth()
sidebar_user_info()

user = get_current_user()

st.title("🖼️ Image Detection")
st.markdown("Upload an image and detect objects with YOLO11.")

# Sidebar controls
with st.sidebar:
    st.subheader("Detection Settings")
    model_name = model_selector("img_model")
    confidence = confidence_slider("img_conf", 0.5)
    iou = st.slider("IoU threshold", 0.1, 1.0, 0.45, 0.05, key="img_iou")
    device = device_selector("img_device")
    save_result = st.checkbox("Save to history", value=True)

# Upload
uploaded = st.file_uploader(
    f"Upload image ({', '.join(ALLOWED_IMAGE_TYPES)})",
    type=ALLOWED_IMAGE_TYPES,
    key="img_upload",
)

if uploaded:
    if not is_valid_image(uploaded):
        st.error("Invalid image file type.")
        st.stop()

    col_orig, col_result = st.columns(2)
    with col_orig:
        st.subheader("Original Image")
        st.image(uploaded, use_container_width=True)

    if st.button("🚀 Run Detection", type="primary", use_container_width=True):
        with st.spinner("Installing packages if needed and loading model — please wait..."):
            try:
                from detection.yolo_detector import YOLODetector, YOLO_AVAILABLE
                if not YOLO_AVAILABLE:
                    st.error("❌ Could not install or import ultralytics. Please contact the app admin.")
                    st.stop()

                from PIL import Image
                img = Image.open(uploaded).convert("RGB")
                detector = YOLODetector.get_instance(model_name, device)
                annotated, detections, elapsed, result_path = detector.detect_image(
                    img,
                    confidence=confidence,
                    iou=iou,
                    save_output=save_result,
                    output_prefix=f"img_{user['id']}",
                )

                with col_result:
                    st.subheader("Detection Result")
                    if annotated is not None:
                        st.image(annotated, use_container_width=True)

                st.success(f"✅ Found **{len(detections)}** objects in **{elapsed:.3f}s**")

                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Objects Detected", len(detections))
                with col_m2:
                    st.metric("Processing Time", f"{elapsed:.3f}s")
                with col_m3:
                    unique = len(set(d.get("class_name") for d in detections))
                    st.metric("Unique Classes", unique)

                if detections:
                    st.subheader("Detection Details")
                    show_detection_table(detections)

                    import json as _json
                    st.download_button(
                        "📥 Download Results JSON",
                        data=_json.dumps(detections, indent=2),
                        file_name="detections.json",
                        mime="application/json",
                    )

                if annotated is not None and save_result:
                    try:
                        img_bytes = get_image_as_bytes(annotated)
                        st.download_button(
                            "📥 Download Annotated Image",
                            data=img_bytes,
                            file_name=f"annotated_{uploaded.name}",
                            mime="image/jpeg",
                        )
                    except Exception:
                        pass

                if save_result:
                    result_fname = os.path.basename(result_path) if result_path else None
                    with get_db() as db:
                        orig_path, _ = save_uploaded_file(uploaded, "images")
                        crud.save_detection(
                            db,
                            user_id=user["id"],
                            detection_type="image",
                            detections=detections,
                            model_used=model_name,
                            confidence_threshold=confidence,
                            device=device,
                            processing_time=elapsed,
                            original_filename=uploaded.name,
                            result_filename=result_fname,
                        )
                    st.caption("✔ Saved to detection history")

            except ImportError as e:
                st.error(f"Missing dependency: {e}. Ensure ultralytics and Pillow are installed.")
            except Exception as e:
                st.error(f"Detection failed: {e}")
else:
    st.info("Upload an image to get started. Supported formats: " + ", ".join(ALLOWED_IMAGE_TYPES))
    with st.expander("📖 How it works"):
        st.markdown("""
        1. Upload any image in the supported formats above
        2. Adjust confidence threshold and model in the sidebar
        3. Click **Run Detection** to detect objects
        4. View the annotated image with bounding boxes
        5. Download results as JSON or annotated image
        
        **YOLO11 Models:**
        - `yolo11n` — Nano (fastest, least accurate)
        - `yolo11s` — Small
        - `yolo11m` — Medium
        - `yolo11l` — Large
        - `yolo11x` — Extra Large (slowest, most accurate)
        """)
