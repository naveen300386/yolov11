import json
import time
import io
from datetime import datetime
from typing import Any, Dict, List, Optional
import streamlit as st

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def format_bytes(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60:
        return f"{seconds:.2f} s"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}m {s:.0f}s"


def parse_detections(detections_json: Optional[str]) -> List[Dict]:
    if not detections_json:
        return []
    try:
        return json.loads(detections_json)
    except Exception:
        return []


def summarize_detections(detections: List[Dict]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for d in detections:
        cls = d.get("class_name", "unknown")
        summary[cls] = summary.get(cls, 0) + 1
    return summary


def get_image_as_bytes(image) -> bytes:
    if PIL_AVAILABLE and isinstance(image, Image.Image):
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    return b""


def show_detection_table(detections: List[Dict]):
    import pandas as pd
    if not detections:
        st.info("No objects detected.")
        return
    rows = []
    for i, d in enumerate(detections, 1):
        rows.append({
            "#": i,
            "Class": d.get("class_name", "?"),
            "Confidence": f"{d.get('confidence', 0):.2%}",
            "BBox": str([round(x) for x in d.get("bbox", [])]),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def sidebar_user_info():
    user = st.session_state.get("user")
    if user:
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"**{user['username']}** `{user['role']}`")
            if user.get("email"):
                st.caption(user["email"])
            if st.button("Logout", use_container_width=True):
                from auth.auth_manager import logout
                logout()
                st.rerun()


def show_metric_card(label: str, value: Any, delta: str = None, help_text: str = None):
    st.metric(label=label, value=value, delta=delta, help=help_text)


def confidence_slider(key: str = "confidence", default: float = 0.5) -> float:
    return st.slider(
        "Confidence threshold",
        min_value=0.1,
        max_value=1.0,
        value=default,
        step=0.05,
        key=key,
        help="Minimum confidence score to show a detection",
    )


def model_selector(key: str = "model_select") -> str:
    from config.settings import AVAILABLE_MODELS, DEFAULT_MODEL
    return st.selectbox(
        "YOLO model",
        AVAILABLE_MODELS,
        index=AVAILABLE_MODELS.index(DEFAULT_MODEL) if DEFAULT_MODEL in AVAILABLE_MODELS else 0,
        key=key,
        help="Larger models are more accurate but slower",
    )


def device_selector(key: str = "device_select") -> str:
    from detection.yolo_detector import YOLODetector
    options = ["cpu"]
    if YOLODetector.is_cuda_available():
        options.insert(0, "cuda")
    return st.selectbox("Compute device", options, key=key, help="Use CUDA for GPU acceleration if available")
