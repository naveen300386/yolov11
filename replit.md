# YOLO11 Object Detection Platform

A production-ready Streamlit application for real-time and batch object detection using YOLO11, with dual authentication, SQLite, admin/user roles, and full analytics.

## Run & Operate

- **Start app:** `bash streamlit_app/run.sh` (port 5000)
- **Default login:** `admin` / `admin123` — change after first login
- **Venv:** `streamlit_venv/` at workspace root

## Stack

- **Frontend:** Streamlit 1.29+
- **Detection:** Ultralytics YOLO11 (yolo11n/s/m/l/x)
- **Database:** SQLite via SQLAlchemy ORM
- **Auth:** bcrypt password hashing + Google OAuth 2.0
- **Charts:** Plotly
- **GPU:** CUDA auto-detect with CPU fallback
- **Video:** OpenCV (opencv-python-headless)

## Where things live

```
streamlit_app/
├── app.py                  — login page + home
├── requirements.txt        — Python deps
├── run.sh                  — startup script
├── .streamlit/config.toml  — server config (port 5000)
├── config/settings.py      — all constants & env vars
├── auth/                   — auth_manager.py, google_oauth.py
├── database/               — models.py, crud.py, database.py
├── detection/              — yolo_detector.py, stream_processor.py
├── utils/                  — helpers.py, file_utils.py
├── pages/                  — 8 Streamlit pages
├── data/                   — SQLite DB (auto-created)
├── uploads/                — user uploads (auto-created)
├── outputs/                — annotated results (auto-created)
└── docs/                   — README.md, DEPLOYMENT.md
streamlit_venv/             — Python 3.11 virtualenv
```

## Product

- Image detection: upload → YOLO11 → annotated image + download
- Video detection: upload → per-frame YOLO11 → annotated video
- Webcam: real-time WebRTC detection (streamlit-webrtc)
- RTSP/IP cameras: add cameras, live monitor with detection overlay
- Dashboard: Plotly charts — detections over time, by type, model usage
- Detection History: browse, filter, download results + CSV export
- Admin Panel: user management, system settings, database backup

## Architecture decisions

- Streamlit multipage app — each page in `pages/` auto-registered by Streamlit
- YOLO detector is a singleton per (model, device) pair to avoid reload overhead
- Auth entirely via `st.session_state` — no cookies, no JWT
- SQLite is zero-config; swap to PostgreSQL by changing `DATABASE_URL` in settings.py
- RTSP streams use background threads (`stream_processor.py`) with a frame queue
- opencv-python-headless used (no libGL needed) instead of opencv-python

## User preferences

_Populate as you build._

## Gotchas

- Run `bash streamlit_app/run.sh` not `pnpm dev` — this is a Python/Streamlit project
- YOLO models download on first use (~6–136 MB depending on model size)
- libGL must be installed (handled via Nix) for OpenCV to work
- Webcam page requires streamlit-webrtc + av packages (optional)
- RTSP monitoring uses OpenCV VideoCapture — camera must be reachable from server

## Environment Variables (create streamlit_app/.env)

```env
ADMIN_PASSWORD=change-this
ADMIN_EMAIL=admin@example.com
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://your-domain.com
SECRET_KEY=random-64-char-secret
```

## Deployment

See `streamlit_app/docs/DEPLOYMENT.md` for Ubuntu, Windows, and Docker guides.
