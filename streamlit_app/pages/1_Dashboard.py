import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

from auth.auth_manager import require_auth, is_admin, get_current_user
from database.database import get_db, init_db
from database import crud
from utils.helpers import sidebar_user_info, parse_detections, summarize_detections

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
init_db()
require_auth()
sidebar_user_info()

user = get_current_user()
is_adm = is_admin()

st.title("📊 Dashboard")
st.markdown("Overview of detection activity and analytics.")

# Load data
with get_db() as db:
    uid = None if is_adm else user["id"]
    stats = crud.get_detection_stats(db, uid)
    detections = crud.get_detections(db, user_id=uid, limit=500)
    all_users = crud.get_all_users(db) if is_adm else []

# Top metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Detections", stats["total"])
with col2:
    st.metric("Objects Found", stats["total_objects"])
with col3:
    st.metric("Avg Objects/Run", stats["avg_objects"])
with col4:
    if is_adm:
        st.metric("Total Users", len(all_users))
    else:
        by_type = stats.get("by_type", {})
        img_count = by_type.get("image", 0)
        st.metric("Image Detections", img_count)

st.markdown("---")

if not detections:
    st.info("No detection history yet. Run some detections to see analytics here!")
    st.stop()

# Build dataframe
rows = []
for d in detections:
    rows.append({
        "id": d.id,
        "date": d.created_at,
        "type": d.detection_type,
        "objects": d.objects_detected or 0,
        "model": d.model_used or "unknown",
        "device": d.device or "cpu",
        "time_s": d.processing_time or 0,
        "user_id": d.user_id,
    })
df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["date"])
df["day"] = df["date"].dt.date

# Charts row 1
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Detections Over Time")
    daily = df.groupby("day")["id"].count().reset_index()
    daily.columns = ["Date", "Count"]
    fig = px.area(daily, x="Date", y="Count", title="Daily detection runs")
    fig.update_layout(showlegend=False, height=300, margin=dict(t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Detection by Type")
    type_counts = df["type"].value_counts().reset_index()
    type_counts.columns = ["Type", "Count"]
    fig2 = px.pie(type_counts, names="Type", values="Count", hole=0.4)
    fig2.update_layout(height=300, margin=dict(t=30, b=0))
    st.plotly_chart(fig2, use_container_width=True)

# Charts row 2
col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Objects Detected Over Time")
    obj_daily = df.groupby("day")["objects"].sum().reset_index()
    obj_daily.columns = ["Date", "Objects"]
    fig3 = px.bar(obj_daily, x="Date", y="Objects", title="Objects found per day")
    fig3.update_layout(height=300, margin=dict(t=30, b=0))
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    st.subheader("Model Usage")
    model_counts = df["model"].value_counts().reset_index()
    model_counts.columns = ["Model", "Count"]
    fig4 = px.bar(model_counts, x="Model", y="Count", color="Model")
    fig4.update_layout(showlegend=False, height=300, margin=dict(t=30, b=0))
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# Processing time stats
col_e, col_f = st.columns(2)

with col_e:
    st.subheader("Processing Time Distribution")
    df_with_time = df[df["time_s"] > 0]
    if not df_with_time.empty:
        fig5 = px.histogram(df_with_time, x="time_s", nbins=20, title="Processing time (seconds)")
        fig5.update_layout(height=280, margin=dict(t=30, b=0))
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("No processing time data yet.")

with col_f:
    st.subheader("Device Usage")
    device_counts = df["device"].value_counts().reset_index()
    device_counts.columns = ["Device", "Count"]
    fig6 = px.pie(device_counts, names="Device", values="Count", hole=0.3, title="CPU vs GPU usage")
    fig6.update_layout(height=280, margin=dict(t=30, b=0))
    st.plotly_chart(fig6, use_container_width=True)

if is_adm:
    st.markdown("---")
    st.subheader("User Activity")
    with get_db() as db:
        all_dets = crud.get_detections(db, limit=1000)
    if all_dets:
        user_map = {u.id: u.username for u in all_users}
        user_counts = {}
        for d in all_dets:
            uname = user_map.get(d.user_id, f"user_{d.user_id}")
            user_counts[uname] = user_counts.get(uname, 0) + 1
        u_df = pd.DataFrame(list(user_counts.items()), columns=["User", "Detections"])
        fig7 = px.bar(u_df.sort_values("Detections", ascending=False), x="User", y="Detections", color="User")
        fig7.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig7, use_container_width=True)

# Recent detections table
st.markdown("---")
st.subheader("Recent Detections")
recent = df.head(10)[["date", "type", "objects", "model", "device", "time_s"]]
recent.columns = ["Date", "Type", "Objects", "Model", "Device", "Time (s)"]
recent["Time (s)"] = recent["Time (s)"].round(3)
st.dataframe(recent, use_container_width=True, hide_index=True)
