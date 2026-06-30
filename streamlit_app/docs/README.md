# YOLO11 Object Detection Platform

A production-ready Streamlit web application for real-time and batch object detection using **Ultralytics YOLO11**, with dual authentication (username/password + Google OAuth), SQLite database, role-based access control, and comprehensive analytics.

---

## Features

| Feature | Details |
|---------|---------|
| **Authentication** | Username/password with bcrypt + Google OAuth 2.0 |
| **Roles** | `admin` (full access) and `user` (own data only) |
| **Image Detection** | Upload JPG/PNG/WebP → detect → download annotated image |
| **Video Detection** | Upload MP4/AVI/MOV → process all frames → download annotated video |
| **Webcam** | Real-time YOLO11 via WebRTC (requires `streamlit-webrtc`) |
| **IP/RTSP Cameras** | Add unlimited cameras, live monitoring with detection overlay |
| **CUDA GPU** | Automatic GPU use if available, CPU fallback |
| **Dashboard** | Plotly charts: detections over time, by type, model usage |
| **History** | Browse/download all detection records, export CSV |
| **Admin Panel** | User management, system settings, database backup |
| **Database** | SQLite via SQLAlchemy — zero configuration |

---

## Quick Start

### Prerequisites

- Python 3.11+
- `uv` or `pip` package manager

### Install and Run

```bash
# Clone / enter directory
cd streamlit_app

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py --server.port 5000
```

### Default Login

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

**⚠️ Change the admin password immediately after first login.**

---

## Project Structure

```
streamlit_app/
├── app.py                     # Main entry + login page
├── requirements.txt           # Python dependencies
├── run.sh                     # Startup script
├── .streamlit/
│   └── config.toml            # Streamlit server config
├── config/
│   └── settings.py            # All configurable constants
├── auth/
│   ├── auth_manager.py        # Login, registration, session
│   └── google_oauth.py        # Google OAuth flow
├── database/
│   ├── database.py            # SQLAlchemy engine + session
│   ├── models.py              # ORM models (User, Detection, Camera, AppSettings)
│   └── crud.py                # All database operations
├── detection/
│   ├── yolo_detector.py       # YOLO11 wrapper (image, video, frame)
│   └── stream_processor.py    # Background RTSP stream threads
├── utils/
│   ├── helpers.py             # UI helpers, formatters
│   └── file_utils.py          # Upload/download utilities
├── pages/
│   ├── 1_Dashboard.py         # Analytics and charts
│   ├── 2_Image_Detection.py   # Image upload + detection
│   ├── 3_Video_Detection.py   # Video processing
│   ├── 4_Webcam_Detection.py  # WebRTC webcam
│   ├── 5_Camera_Management.py # RTSP camera CRUD + live view
│   ├── 6_Detection_History.py # Browse and download history
│   ├── 7_Settings.py          # User and system settings
│   └── 8_Admin.py             # Admin-only panel
├── data/                      # SQLite database (auto-created)
├── uploads/                   # Uploaded files (auto-created)
└── outputs/                   # Detection results (auto-created)
```

---

## Configuration

### Environment Variables

Create a `.env` file in the `streamlit_app/` directory:

```env
# Admin credentials (change these!)
ADMIN_PASSWORD=your-secure-password
ADMIN_EMAIL=admin@yourcompany.com

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-app-domain.com

# App secret
SECRET_KEY=your-random-secret-key-min-32-chars
```

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → APIs & Services → Credentials
3. Create **OAuth 2.0 Client ID** (Web application)
4. Add **Authorized redirect URIs**: `https://your-domain.com`
5. Copy **Client ID** and **Client Secret** to `.env`

---

## YOLO11 Models

Models download automatically on first use from [Ultralytics](https://docs.ultralytics.com/).

| Model | Size | mAP | Speed (CPU) |
|-------|------|-----|-------------|
| yolo11n | 6 MB | 39.5 | ~45ms |
| yolo11s | 22 MB | 47.0 | ~95ms |
| yolo11m | 68 MB | 51.5 | ~175ms |
| yolo11l | 87 MB | 53.4 | ~250ms |
| yolo11x | 136 MB | 54.7 | ~400ms |

---

## RTSP / IP Camera URL Formats

```
# Common RTSP formats
rtsp://username:password@192.168.1.100:554/stream1
rtsp://admin:admin@10.0.0.50/h264Preview_01_main
rtsp://192.168.1.100:8554/live

# HTTP MJPEG
http://192.168.1.100:8080/video

# USB webcam (by index)
0    # First camera
1    # Second camera
```

---

## Security Notes

- Passwords are hashed with **bcrypt** (cost factor 12)
- Sessions use **Streamlit session_state** (server-side)
- Google OAuth uses **PKCE state parameter** to prevent CSRF
- File uploads are sanitized (type + size checked)
- Admin actions are role-protected at every page
- **Do not run with default credentials in production**

See [DEPLOYMENT.md](./DEPLOYMENT.md) for production hardening.
