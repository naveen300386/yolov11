import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import time
import json

from auth.auth_manager import require_auth, get_current_user
from database.database import get_db, init_db
from database import crud
from utils.helpers import sidebar_user_info, confidence_slider, model_selector, device_selector

st.set_page_config(page_title="Webcam Detection", page_icon="📸", layout="wide")
init_db()
require_auth()
sidebar_user_info()

user = get_current_user()

st.title("📸 Webcam Detection")
st.markdown("Real-time object detection using your webcam.")

with st.sidebar:
    st.subheader("Detection Settings")
    model_name = model_selector("webcam_model")
    confidence = confidence_slider("webcam_conf", 0.5)
    device = device_selector("webcam_device")

# Try streamlit-webrtc
try:
    from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration
    import av
    import numpy as np

    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False


if WEBRTC_AVAILABLE:
    from detection.yolo_detector import YOLODetector, YOLO_AVAILABLE

    if not YOLO_AVAILABLE:
        st.error("YOLO not installed. Run: `pip install ultralytics`")
        st.stop()

    RTC_CONFIGURATION = RTCConfiguration(
        {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )

    class YOLOVideoProcessor(VideoProcessorBase):
        def __init__(self):
            self.confidence = confidence
            self.model_name = model_name
            self.device = device
            self._detector = None
            self.last_detections = []
            self.frame_count = 0

        def _get_detector(self):
            if self._detector is None:
                self._detector = YOLODetector.get_instance(self.model_name, self.device)
            return self._detector

        def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
            img = frame.to_ndarray(format="bgr24")
            try:
                det = self._get_detector()
                annotated, detections = det.detect_frame(img, self.confidence)
                self.last_detections = detections
                self.frame_count += 1
                return av.VideoFrame.from_ndarray(annotated, format="bgr24")
            except Exception:
                return frame

    st.info("Click **START** to begin webcam detection. Allow camera access in your browser.")
    col_stream, col_info = st.columns([2, 1])
    with col_stream:
        ctx = webrtc_streamer(
            key="yolo-webcam",
            video_processor_factory=YOLOVideoProcessor,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )

    with col_info:
        st.subheader("Live Stats")
        if ctx.video_processor:
            proc = ctx.video_processor
            st.metric("Frames Processed", proc.frame_count)
            st.metric("Last Frame Detections", len(proc.last_detections))
            if proc.last_detections:
                st.markdown("**Detected Objects:**")
                from utils.helpers import summarize_detections
                summary = summarize_detections(proc.last_detections)
                for cls, count in sorted(summary.items(), key=lambda x: -x[1]):
                    st.markdown(f"- **{cls}**: {count}")
        else:
            st.info("Start the stream to see live detection stats.")

else:
    st.warning("**streamlit-webrtc** is not installed. Using snapshot mode instead.")
    st.markdown("Install it with: `pip install streamlit-webrtc av`")
    st.markdown("---")

    # Fallback: JavaScript-based webcam snapshot
    st.markdown("### Snapshot Mode")
    st.markdown("Use your browser to take a photo, then run detection on it.")

    snapshot_js = """
    <div style="display:flex; flex-direction:column; align-items:center; gap:12px; font-family:sans-serif;">
      <video id="video" width="640" height="480" autoplay playsinline
             style="border:2px solid #444; border-radius:8px; background:#000; max-width:100%;"></video>

      <div style="display:flex; gap:10px; flex-wrap:wrap; justify-content:center;">
        <button onclick="startCamera()"
          style="padding:10px 20px; background:#1f77b4; color:white; border:none; border-radius:6px; cursor:pointer; font-size:15px;">
          ▶ Start Camera
        </button>
        <button onclick="captureSnapshot()"
          style="padding:10px 20px; background:#2ca02c; color:white; border:none; border-radius:6px; cursor:pointer; font-size:15px;">
          📸 Capture Snapshot
        </button>
      </div>

      <canvas id="canvas" width="640" height="480" style="display:none;"></canvas>

      <div id="result-section" style="display:none; flex-direction:column; align-items:center; gap:10px; width:100%;">
        <p style="color:#aaa; margin:0;">✅ Snapshot captured! Download it and upload to <strong>Image Detection</strong> for analysis.</p>
        <img id="snapshot" style="max-width:640px; width:100%; border:2px solid #2ca02c; border-radius:8px;" />
        <a id="download-btn" download="webcam_snapshot.jpg"
           style="padding:12px 32px; background:#e84040; color:white; border:none; border-radius:6px;
                  cursor:pointer; font-size:16px; font-weight:bold; text-decoration:none; display:inline-block;">
          💾 Save / Download Image
        </a>
        <button onclick="resetCapture()"
          style="padding:8px 20px; background:#555; color:white; border:none; border-radius:6px; cursor:pointer; font-size:14px;">
          🔄 Take Another
        </button>
      </div>
    </div>

    <script>
    let stream;

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({video: true, audio: false});
        const video = document.getElementById('video');
        video.srcObject = stream;
        video.style.display = 'block';
      } catch(e) {
        alert('Camera access denied: ' + e.message);
      }
    }

    function captureSnapshot() {
      const video = document.getElementById('video');
      if (!video.srcObject) {
        alert('Please start the camera first!');
        return;
      }
      const canvas = document.getElementById('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.95);

      const img = document.getElementById('snapshot');
      img.src = dataUrl;

      const btn = document.getElementById('download-btn');
      btn.href = dataUrl;

      document.getElementById('result-section').style.display = 'flex';
      document.getElementById('video').style.display = 'none';
    }

    function resetCapture() {
      document.getElementById('result-section').style.display = 'none';
      document.getElementById('video').style.display = 'block';
    }
    </script>
    """
    st.components.v1.html(snapshot_js, height=700)
    st.info("📌 After downloading the snapshot, go to **Image Detection** in the sidebar to upload and run YOLO detection on it.")

st.markdown("---")
with st.expander("ℹ️ Webcam Detection Notes"):
    st.markdown("""
    - Browser must allow camera access (HTTPS or localhost)
    - For production deployment, use HTTPS with a valid certificate
    - If the stream lags, try reducing model size (yolo11n is fastest)
    - TURN server may be required for non-local deployments
    - As an alternative, use the **Image Detection** page with captured screenshots
    """)
