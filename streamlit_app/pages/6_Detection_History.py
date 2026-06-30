import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import json

from auth.auth_manager import require_auth, get_current_user, is_admin
from database.database import get_db, init_db
from database import crud
from utils.helpers import sidebar_user_info, parse_detections, summarize_detections
from utils.file_utils import get_output_file_bytes, delete_output_file

st.set_page_config(page_title="Detection History", page_icon="📋", layout="wide")
init_db()
require_auth()
sidebar_user_info()

user = get_current_user()

st.title("📋 Detection History")
st.markdown("Browse, filter, and download all your past detection results.")

# Filters sidebar
with st.sidebar:
    st.subheader("Filters")
    filter_type = st.multiselect(
        "Detection type",
        ["image", "video", "webcam", "rtsp"],
        default=[],
        help="Leave empty to show all",
    )
    limit = st.slider("Show last N records", 10, 500, 50)
    if is_admin():
        show_all = st.checkbox("Show all users (admin)", value=False)
    else:
        show_all = False

# Load data
with get_db() as db:
    uid = None if (is_admin() and show_all) else user["id"]
    all_detections = crud.get_detections(db, user_id=uid, limit=limit)
    all_users_map = {}
    if is_admin():
        all_users = crud.get_all_users(db)
        all_users_map = {u.id: u.username for u in all_users}

# Apply type filter
if filter_type:
    all_detections = [d for d in all_detections if d.detection_type in filter_type]

if not all_detections:
    st.info("No detection history found. Run some detections to see them here!")
    st.stop()

# Summary
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Records Shown", len(all_detections))
with col2:
    total_obj = sum(d.objects_detected or 0 for d in all_detections)
    st.metric("Total Objects", total_obj)
with col3:
    types = list(set(d.detection_type for d in all_detections))
    st.metric("Types", ", ".join(types) or "N/A")

st.markdown("---")

# Table view
rows = []
for d in all_detections:
    rows.append({
        "ID": d.id,
        "Date": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else "",
        "Type": d.detection_type,
        "File": d.original_filename or "—",
        "Objects": d.objects_detected or 0,
        "Classes": d.unique_classes or 0,
        "Model": d.model_used or "—",
        "Device": d.device or "—",
        "Time (s)": round(d.processing_time or 0, 3),
        **({"User": all_users_map.get(d.user_id, f"#{d.user_id}")} if is_admin() and show_all else {}),
    })
df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

# Export table
csv = df.to_csv(index=False)
st.download_button(
    "📥 Export Table as CSV",
    data=csv,
    file_name="detection_history.csv",
    mime="text/csv",
)

st.markdown("---")

# Detail viewer
st.subheader("View Detection Details")
detection_ids = [d.id for d in all_detections]
selected_id = st.selectbox(
    "Select detection ID",
    options=detection_ids,
    format_func=lambda x: f"ID {x} — {next((f'{d.detection_type} | {d.original_filename or \"\"} | {d.objects_detected} objects' for d in all_detections if d.id == x), str(x))}",
)

if selected_id:
    det = next((d for d in all_detections if d.id == selected_id), None)
    if det:
        col_info, col_action = st.columns([3, 1])
        with col_info:
            st.markdown(f"**Type:** {det.detection_type}")
            st.markdown(f"**Original file:** {det.original_filename or 'N/A'}")
            st.markdown(f"**Result file:** {det.result_filename or 'N/A'}")
            st.markdown(f"**Model:** {det.model_used} | **Device:** {det.device}")
            st.markdown(f"**Confidence threshold:** {det.confidence_threshold}")
            st.markdown(f"**Processing time:** {det.processing_time:.3f}s")
            st.markdown(f"**Date:** {det.created_at}")
            st.markdown(f"**Objects detected:** {det.objects_detected} | **Unique classes:** {det.unique_classes}")

        with col_action:
            if det.result_filename:
                result_bytes = get_output_file_bytes(det.result_filename)
                if result_bytes:
                    ext = det.result_filename.rsplit(".", 1)[-1].lower()
                    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "mp4": "video/mp4"}
                    mime = mime_map.get(ext, "application/octet-stream")
                    st.download_button(
                        "📥 Download Result",
                        data=result_bytes,
                        file_name=det.result_filename,
                        mime=mime,
                        use_container_width=True,
                    )

            if is_admin() or det.user_id == user["id"]:
                if st.button("🗑️ Delete Record", use_container_width=True, type="secondary"):
                    if det.result_filename:
                        delete_output_file(det.result_filename)
                    with get_db() as db:
                        crud.delete_detection(db, det.id)
                    st.success("Record deleted.")
                    st.rerun()

        # Show detections
        detections = parse_detections(det.detections_json)
        if detections:
            st.subheader(f"Detected Objects ({len(detections)} total)")
            summary = summarize_detections(detections)
            if summary:
                import plotly.express as px
                s_df = pd.DataFrame(list(summary.items()), columns=["Class", "Count"])
                fig = px.bar(s_df.sort_values("Count", ascending=False), x="Class", y="Count", color="Class")
                fig.update_layout(showlegend=False, height=250, margin=dict(t=10, b=0))
                st.plotly_chart(fig, use_container_width=True)

            det_df = pd.DataFrame([{
                "#": i + 1,
                "Class": d.get("class_name", "?"),
                "Confidence": f"{d.get('confidence', 0):.2%}",
                "BBox [x1,y1,x2,y2]": str([round(x) for x in d.get("bbox", [])]),
            } for i, d in enumerate(detections)])
            st.dataframe(det_df, use_container_width=True, hide_index=True)

            st.download_button(
                "📥 Download Detections JSON",
                data=json.dumps(detections, indent=2),
                file_name=f"detections_{det.id}.json",
                mime="application/json",
            )

        # Show result image if available
        if det.result_filename and det.detection_type == "image":
            result_bytes = get_output_file_bytes(det.result_filename)
            if result_bytes:
                st.subheader("Result Image")
                st.image(result_bytes, use_container_width=True)
