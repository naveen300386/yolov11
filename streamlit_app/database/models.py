from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(20), default="user", nullable=False)
    google_id = Column(String(100), unique=True, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    detections = relationship("Detection", back_populates="user", cascade="all, delete-orphan")
    cameras = relationship("Camera", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    detection_type = Column(String(20), nullable=False)
    original_filename = Column(String(255), nullable=True)
    result_filename = Column(String(255), nullable=True)
    detections_json = Column(Text, nullable=True)
    objects_detected = Column(Integer, default=0)
    unique_classes = Column(Integer, default=0)
    model_used = Column(String(50), nullable=True)
    confidence_threshold = Column(Float, nullable=True)
    device = Column(String(20), nullable=True)
    processing_time = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="detections")

    def __repr__(self):
        return f"<Detection(id={self.id}, type='{self.detection_type}', objects={self.objects_detected})>"


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    rtsp_url = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="cameras")

    def __repr__(self):
        return f"<Camera(id={self.id}, name='{self.name}')>"


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppSettings(key='{self.key}', value='{self.value}')>"
