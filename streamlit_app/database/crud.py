import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from database.models import User, Detection, Camera, AppSettings
import bcrypt


# ─── User CRUD ────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def create_user(db: Session, username: str, email: str, password: str, role: str = "user") -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def create_google_user(db: Session, username: str, email: str, google_id: str, role: str = "user") -> User:
    user = User(
        username=username,
        email=email,
        google_id=google_id,
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
    return db.query(User).filter(User.google_id == google_id).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_all_users(db: Session) -> List[User]:
    return db.query(User).all()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if user and user.password_hash and verify_password(password, user.password_hash):
        if user.is_active:
            user.last_login = datetime.utcnow()
            return user
    return None


def update_user(db: Session, user_id: int, **kwargs) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if user:
        for k, v in kwargs.items():
            if k == "password":
                setattr(user, "password_hash", hash_password(v))
            else:
                setattr(user, k, v)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = get_user_by_id(db, user_id)
    if user:
        db.delete(user)
        return True
    return False


def ensure_admin_exists(db: Session, username: str, email: str, password: str):
    if not get_user_by_username(db, username):
        create_user(db, username, email, password, role="admin")


# ─── Detection CRUD ────────────────────────────────────────────────────────────

def save_detection(
    db: Session,
    user_id: int,
    detection_type: str,
    detections: List[Dict],
    model_used: str,
    confidence_threshold: float,
    device: str,
    processing_time: float,
    original_filename: str = None,
    result_filename: str = None,
) -> Detection:
    classes = set(d.get("class_name", "") for d in detections)
    record = Detection(
        user_id=user_id,
        detection_type=detection_type,
        original_filename=original_filename,
        result_filename=result_filename,
        detections_json=json.dumps(detections),
        objects_detected=len(detections),
        unique_classes=len(classes),
        model_used=model_used,
        confidence_threshold=confidence_threshold,
        device=device,
        processing_time=processing_time,
    )
    db.add(record)
    db.flush()
    return record


def get_detections(
    db: Session,
    user_id: Optional[int] = None,
    detection_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Detection]:
    q = db.query(Detection)
    if user_id is not None:
        q = q.filter(Detection.user_id == user_id)
    if detection_type:
        q = q.filter(Detection.detection_type == detection_type)
    return q.order_by(Detection.created_at.desc()).offset(offset).limit(limit).all()


def get_detection_by_id(db: Session, detection_id: int) -> Optional[Detection]:
    return db.query(Detection).filter(Detection.id == detection_id).first()


def delete_detection(db: Session, detection_id: int) -> bool:
    d = get_detection_by_id(db, detection_id)
    if d:
        db.delete(d)
        return True
    return False


def get_detection_stats(db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
    q = db.query(Detection)
    if user_id:
        q = q.filter(Detection.user_id == user_id)
    detections = q.all()
    if not detections:
        return {"total": 0, "by_type": {}, "total_objects": 0, "avg_objects": 0.0}
    by_type: Dict[str, int] = {}
    total_objects = 0
    for d in detections:
        by_type[d.detection_type] = by_type.get(d.detection_type, 0) + 1
        total_objects += d.objects_detected or 0
    return {
        "total": len(detections),
        "by_type": by_type,
        "total_objects": total_objects,
        "avg_objects": round(total_objects / len(detections), 2),
    }


# ─── Camera CRUD ──────────────────────────────────────────────────────────────

def create_camera(db: Session, user_id: int, name: str, rtsp_url: str, description: str = "", location: str = "") -> Camera:
    cam = Camera(user_id=user_id, name=name, rtsp_url=rtsp_url, description=description, location=location)
    db.add(cam)
    db.flush()
    return cam


def get_cameras(db: Session, user_id: Optional[int] = None) -> List[Camera]:
    q = db.query(Camera)
    if user_id:
        q = q.filter(Camera.user_id == user_id)
    return q.order_by(Camera.created_at.desc()).all()


def get_camera_by_id(db: Session, camera_id: int) -> Optional[Camera]:
    return db.query(Camera).filter(Camera.id == camera_id).first()


def update_camera(db: Session, camera_id: int, **kwargs) -> Optional[Camera]:
    cam = get_camera_by_id(db, camera_id)
    if cam:
        for k, v in kwargs.items():
            setattr(cam, k, v)
        cam.updated_at = datetime.utcnow()
    return cam


def delete_camera(db: Session, camera_id: int) -> bool:
    cam = get_camera_by_id(db, camera_id)
    if cam:
        db.delete(cam)
        return True
    return False


# ─── App Settings CRUD ────────────────────────────────────────────────────────

def get_setting(db: Session, key: str, default: Any = None) -> Any:
    s = db.query(AppSettings).filter(AppSettings.key == key).first()
    return s.value if s else default


def set_setting(db: Session, key: str, value: str, description: str = "") -> AppSettings:
    s = db.query(AppSettings).filter(AppSettings.key == key).first()
    if s:
        s.value = value
        s.updated_at = datetime.utcnow()
    else:
        s = AppSettings(key=key, value=value, description=description)
        db.add(s)
    return s
