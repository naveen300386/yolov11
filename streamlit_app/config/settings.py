import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Directories — created lazily, not at import time
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_DIR   = BASE_DIR / "data"

def ensure_dirs():
    for d in [UPLOAD_DIR, OUTPUT_DIR, DATA_DIR]:
        d.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{DATA_DIR}/yolo_detection.db"

# Authentication
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-secret-key")
SESSION_EXPIRY_HOURS = 24

# Google OAuth
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000")

# YOLO Settings
DEFAULT_MODEL = "yolo11n.pt"
AVAILABLE_MODELS = [
    "yolo11n.pt",
    "yolo11s.pt",
    "yolo11m.pt",
    "yolo11l.pt",
    "yolo11x.pt",
]
DEFAULT_CONFIDENCE = 0.5
DEFAULT_IOU        = 0.45
DEFAULT_DEVICE     = "cpu"

# RTSP Settings
RTSP_TIMEOUT = 10
MAX_CAMERAS  = 10

# File limits
MAX_IMAGE_SIZE_MB   = 50
MAX_VIDEO_SIZE_MB   = 500
ALLOWED_IMAGE_TYPES = ["jpg", "jpeg", "png", "bmp", "webp", "tiff"]
ALLOWED_VIDEO_TYPES = ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"]

# Admin defaults
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL", "admin@example.com")
