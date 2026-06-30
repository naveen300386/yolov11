import threading
import time
import queue
from typing import Optional, Callable, Dict, Any, List
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class StreamProcessor:
    def __init__(
        self,
        source: str,
        detector=None,
        confidence: float = 0.5,
        iou: float = 0.45,
        max_queue_size: int = 5,
        reconnect_delay: float = 2.0,
    ):
        self.source = source
        self.detector = detector
        self.confidence = confidence
        self.iou = iou
        self.frame_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.stats_queue: queue.Queue = queue.Queue(maxsize=100)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.reconnect_delay = reconnect_delay
        self._is_running = False
        self._last_error: Optional[str] = None
        self._frame_count = 0
        self._detection_count = 0

    def start(self):
        if self._is_running:
            return
        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=5)

    def get_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _capture_loop(self):
        if not CV2_AVAILABLE:
            self._last_error = "opencv not installed"
            return

        while not self._stop_event.is_set():
            cap = None
            try:
                cap = cv2.VideoCapture(self.source)
                if not cap.isOpened():
                    self._last_error = f"Cannot open stream: {self.source}"
                    time.sleep(self.reconnect_delay)
                    continue

                self._last_error = None

                while not self._stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    self._frame_count += 1

                    if self.detector:
                        try:
                            annotated, detections = self.detector.detect_frame(frame, self.confidence, self.iou)
                            self._detection_count += len(detections)
                            display = annotated
                            if not self.stats_queue.full():
                                self.stats_queue.put({
                                    "frame": self._frame_count,
                                    "detections": detections,
                                    "timestamp": time.time(),
                                })
                        except Exception:
                            display = frame
                    else:
                        display = frame

                    if not self.frame_queue.full():
                        self.frame_queue.put(display)
                    else:
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put(display)
                        except queue.Empty:
                            pass

            except Exception as e:
                self._last_error = str(e)
            finally:
                if cap:
                    cap.release()

            if not self._stop_event.is_set():
                time.sleep(self.reconnect_delay)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def get_stats(self) -> Dict[str, Any]:
        return {
            "frame_count": self._frame_count,
            "detection_count": self._detection_count,
            "is_running": self._is_running,
            "last_error": self._last_error,
            "source": self.source,
        }


_active_streams: Dict[str, StreamProcessor] = {}


def get_stream(stream_id: str, source: str, detector=None, confidence: float = 0.5) -> StreamProcessor:
    if stream_id not in _active_streams or not _active_streams[stream_id].is_running:
        _active_streams[stream_id] = StreamProcessor(source, detector, confidence)
        _active_streams[stream_id].start()
    return _active_streams[stream_id]


def stop_stream(stream_id: str):
    if stream_id in _active_streams:
        _active_streams[stream_id].stop()
        del _active_streams[stream_id]


def stop_all_streams():
    for s in _active_streams.values():
        s.stop()
    _active_streams.clear()
