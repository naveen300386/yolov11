import time
import json
import io
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    import subprocess, sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python-headless", "--quiet"])
        import cv2
        CV2_AVAILABLE = True
    except Exception:
        CV2_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    import subprocess, sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics", "--quiet"])
        from ultralytics import YOLO
        YOLO_AVAILABLE = True
    except Exception:
        YOLO_AVAILABLE = False

from config.settings import OUTPUT_DIR, DEFAULT_MODEL, DEFAULT_CONFIDENCE, DEFAULT_DEVICE


class YOLODetector:
    _instances: Dict[str, "YOLODetector"] = {}

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str = DEFAULT_DEVICE):
        if not YOLO_AVAILABLE:
            raise RuntimeError("ultralytics package not installed. Run: pip install ultralytics")
        self.model_name = model_name
        self.device = self._resolve_device(device)
        self.model = YOLO(model_name)
        self.model.to(self.device)

    @classmethod
    def get_instance(cls, model_name: str = DEFAULT_MODEL, device: str = DEFAULT_DEVICE) -> "YOLODetector":
        key = f"{model_name}_{device}"
        if key not in cls._instances:
            cls._instances[key] = cls(model_name, device)
        return cls._instances[key]

    @classmethod
    def clear_instances(cls):
        cls._instances.clear()

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device.lower() in ("cuda", "gpu"):
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
            except ImportError:
                pass
            return "cpu"
        return "cpu"

    @staticmethod
    def is_cuda_available() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def detect_image(
        self,
        image_input,
        confidence: float = DEFAULT_CONFIDENCE,
        iou: float = 0.45,
        save_output: bool = True,
        output_prefix: str = "result",
    ) -> Tuple[Any, List[Dict], float, Optional[str]]:
        start = time.time()
        if isinstance(image_input, (str, Path)):
            img = Image.open(image_input).convert("RGB") if PIL_AVAILABLE else None
        elif PIL_AVAILABLE and isinstance(image_input, Image.Image):
            img = image_input.convert("RGB")
        elif isinstance(image_input, bytes):
            img = Image.open(io.BytesIO(image_input)).convert("RGB") if PIL_AVAILABLE else None
        else:
            img = image_input

        results = self.model(img, conf=confidence, iou=iou, verbose=False)
        elapsed = time.time() - start

        detections = self._parse_results(results)
        annotated = self._get_annotated_image(results)

        result_path = None
        if save_output and annotated is not None:
            fname = f"{output_prefix}_{int(time.time())}.jpg"
            fpath = OUTPUT_DIR / fname
            if PIL_AVAILABLE and isinstance(annotated, Image.Image):
                annotated.save(str(fpath))
            elif CV2_AVAILABLE and isinstance(annotated, np.ndarray):
                cv2.imwrite(str(fpath), annotated)
            result_path = str(fpath)

        return annotated, detections, elapsed, result_path

    def detect_video(
        self,
        video_path: str,
        confidence: float = DEFAULT_CONFIDENCE,
        iou: float = 0.45,
        output_prefix: str = "video_result",
        frame_skip: int = 1,
    ) -> Tuple[str, List[Dict], float]:
        if not CV2_AVAILABLE:
            raise RuntimeError("opencv-python-headless not installed")

        start = time.time()
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out_fname = f"{output_prefix}_{int(time.time())}.mp4"
        out_path = str(OUTPUT_DIR / out_fname)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

        all_detections: List[Dict] = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_skip == 0:
                results = self.model(frame, conf=confidence, iou=iou, verbose=False)
                dets = self._parse_results(results)
                all_detections.extend(dets)
                annotated = results[0].plot()
                writer.write(annotated)
            else:
                writer.write(frame)
            frame_idx += 1

        cap.release()
        writer.release()
        elapsed = time.time() - start
        return out_path, all_detections, elapsed

    def detect_frame(self, frame: np.ndarray, confidence: float = DEFAULT_CONFIDENCE, iou: float = 0.45) -> Tuple[np.ndarray, List[Dict]]:
        results = self.model(frame, conf=confidence, iou=iou, verbose=False)
        detections = self._parse_results(results)
        annotated = results[0].plot()
        return annotated, detections

    @staticmethod
    def _parse_results(results) -> List[Dict]:
        detections = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                try:
                    cls_id = int(box.cls[0])
                    cls_name = r.names.get(cls_id, f"class_{cls_id}")
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].tolist()
                    detections.append({
                        "class_id": cls_id,
                        "class_name": cls_name,
                        "confidence": round(conf, 4),
                        "bbox": [round(x, 1) for x in xyxy],
                    })
                except Exception:
                    continue
        return detections

    @staticmethod
    def _get_annotated_image(results):
        try:
            annotated_np = results[0].plot()
            if PIL_AVAILABLE:
                return Image.fromarray(annotated_np[..., ::-1])
            return annotated_np
        except Exception:
            return None

    def get_model_info(self) -> Dict[str, Any]:
        info = {
            "model": self.model_name,
            "device": self.device,
            "cuda_available": self.is_cuda_available(),
        }
        try:
            info["classes"] = list(self.model.names.values())
            info["num_classes"] = len(self.model.names)
        except Exception:
            pass
        return info
