import os
import shutil
import time
from pathlib import Path
from typing import Optional, Tuple
import streamlit as st

from config.settings import UPLOAD_DIR, OUTPUT_DIR, ALLOWED_IMAGE_TYPES, ALLOWED_VIDEO_TYPES


def save_uploaded_file(uploaded_file, subdir: str = "") -> Tuple[str, str]:
    target_dir = UPLOAD_DIR / subdir if subdir else UPLOAD_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(uploaded_file.name).suffix.lower()
    fname = f"{int(time.time() * 1000)}_{uploaded_file.name}"
    fpath = target_dir / fname
    with open(str(fpath), "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(fpath), fname


def is_valid_image(uploaded_file) -> bool:
    ext = Path(uploaded_file.name).suffix.lstrip(".").lower()
    return ext in ALLOWED_IMAGE_TYPES


def is_valid_video(uploaded_file) -> bool:
    ext = Path(uploaded_file.name).suffix.lstrip(".").lower()
    return ext in ALLOWED_VIDEO_TYPES


def get_file_size_mb(file_path: str) -> float:
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        return 0.0


def cleanup_old_files(directory: Path, max_age_hours: int = 24):
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    for f in directory.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            try:
                f.unlink()
            except Exception:
                pass


def get_output_file_bytes(filename: str) -> Optional[bytes]:
    fpath = OUTPUT_DIR / filename
    if fpath.exists():
        with open(str(fpath), "rb") as f:
            return f.read()
    return None


def delete_output_file(filename: str) -> bool:
    fpath = OUTPUT_DIR / filename
    if fpath.exists():
        fpath.unlink()
        return True
    return False


def list_output_files() -> list:
    return sorted(OUTPUT_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
