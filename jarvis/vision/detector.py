from __future__ import annotations

import logging
import time

from ultralytics import YOLO

from .objects import (
    BoundingBox,
    DetectedObject,
)


log = logging.getLogger(
    "jarvis.vision.detector"
)


# ============================================================
# SELECTABLE / RELEVANT CLASSES
# ============================================================

ALLOWED_CLASSES = {
    "laptop",
    "cell phone",
    "remote",
    "keyboard",
    "mouse",
    "tv",
    "monitor",
    "book",
    "clock",
    "bottle",
    "cup",
    "bowl",
    "scissors",
    "backpack",
    "handbag",
    "suitcase",
    "chair",
    "couch",
    "bed",
    "dining table",
    "bench",
    "toilet",
    "sink",
    "refrigerator",
    "microwave",
    "oven",
    "toaster",
    "vase",
    "umbrella",
    "tie",
    "sports ball",
    "baseball bat",
    "tennis racket",
    "skateboard",
    "bicycle",
    "motorcycle",
    "car",
    "bus",
    "truck",
}


# ============================================================
# NEVER SELECT
# ============================================================

NON_SELECTABLE_CLASSES = {
    "person",
    "people",
    "face",
}


# ============================================================
# DETECTOR
# ============================================================

class ObjectDetector:

    def __init__(
        self,
        model_name="yolo11n.pt",
        confidence=0.35,
        detection_interval=3,
        image_size=512,
    ) -> None:

        self.confidence = float(
            confidence
        )

        self.detection_interval = max(
            1,
            int(detection_interval),
        )

        self.image_size = int(
            image_size
        )

        log.info(
            "Loading YOLO model: %s",
            model_name,
        )

        self.model = YOLO(
            model_name
        )

        self._frame_count = 0

        self._last_objects = []

        self._last_detection_time = 0.0

        log.info(
            "YOLO ready | "
            "confidence=%.2f | "
            "interval=%d | "
            "imgsz=%d",
            self.confidence,
            self.detection_interval,
            self.image_size,
        )

    # ========================================================
    # DETECT
    # ========================================================

    def detect(
        self,
        frame,
    ):

        self._frame_count += 1

        if frame is None:
            return self._last_objects

        if (
            self._frame_count
            %
            self.detection_interval
            !=
            0
        ):

            return self._last_objects

        try:

            results = self.model.track(
                source=frame,
                conf=self.confidence,
                persist=True,
                tracker="bytetrack.yaml",
                verbose=False,
                imgsz=self.image_size,
            )

        except Exception:

            log.exception(
                "YOLO detection failed"
            )

            return self._last_objects

        objects = []

        for result in results:

            if result.boxes is None:
                continue

            names = result.names

            for box in result.boxes:

                try:

                    if box.conf is None:
                        continue

                    confidence = float(
                        box.conf[0].item()
                    )

                    if (
                        confidence
                        <
                        self.confidence
                    ):
                        continue

                    class_id = int(
                        box.cls[0].item()
                    )

                    label = str(
                        names[class_id]
                    ).strip()

                    label_lower = (
                        label.lower()
                    )

                    if (
                        label_lower
                        in
                        NON_SELECTABLE_CLASSES
                    ):
                        continue

                    if (
                        label_lower
                        not in
                        ALLOWED_CLASSES
                    ):
                        continue

                    xyxy = (
                        box.xyxy[0]
                        .tolist()
                    )

                    x1, y1, x2, y2 = map(
                        float,
                        xyxy,
                    )

                    object_id = (
                        int(
                            box.id[0].item()
                        )
                        if box.id is not None
                        else -1
                    )

                    objects.append(
                        DetectedObject(
                            id=object_id,
                            label=label,
                            confidence=confidence,
                            box=BoundingBox(
                                x1=x1,
                                y1=y1,
                                x2=x2,
                                y2=y2,
                            ),
                        )
                    )

                except Exception:

                    log.exception(
                        "Failed to parse YOLO detection"
                    )

                    continue

        self._last_objects = objects

        self._last_detection_time = (
            time.time()
        )

        if objects:

            detection_text = ", ".join(
                (
                    f"{obj.label}"
                    f"#{obj.id}:"
                    f"{obj.confidence:.2f}"
                )
                for obj in objects
            )

            log.info(
                "YOLO objects: %s",
                detection_text,
            )

        return self._last_objects

    # ========================================================
    # PROPERTIES
    # ========================================================

    @property
    def last_objects(self):

        return self._last_objects

    @property
    def last_detection_time(self):

        return self._last_detection_time