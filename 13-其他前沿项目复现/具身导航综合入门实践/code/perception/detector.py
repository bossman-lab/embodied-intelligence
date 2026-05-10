"""
感知模块 —— YOLO 目标检测
===========================
封装 YOLOv8 推理、结果解析与可视化标注。
"""

import cv2
from ultralytics import YOLO


class YOLODetector:
    """基于 YOLOv8 的目标检测器。"""

    def __init__(self, config):
        self.model = YOLO(config.YOLO_MODEL)
        self.conf = config.YOLO_CONF_THRESHOLD
        self.targets = [t.lower() for t in config.TARGET_OBJECTS]

    def detect(self, image_rgb: "np.ndarray") -> list:
        """
        对 RGB 图像执行检测。

        Returns
        -------
        list of dict:
            {class, confidence, bbox=(x1,y1,x2,y2), is_target}
        """
        bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        results = self.model(bgr, verbose=False, conf=self.conf)
        dets = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls = self.model.names[int(box.cls[0])].lower()
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                dets.append({
                    "class": cls,
                    "confidence": float(box.conf[0]),
                    "bbox": (x1, y1, x2, y2),
                    "is_target": cls in self.targets,
                })
        return dets

    def draw_detections(self, image_rgb: "np.ndarray", detections: list) -> "np.ndarray":
        """在图像上绘制检测框和标签，目标框用绿色，非目标用灰色。"""
        img = image_rgb.copy()
        for d in detections:
            x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
            color, thick = ((0, 255, 0), 3) if d["is_target"] else ((200, 200, 200), 1)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)
            label = f"{d['class']} {d['confidence']:.2f}"
            lsz, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(img, (x1, y1 - lsz[1] - 6), (x1 + lsz[0], y1), color, -1)
            cv2.putText(img, label, (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        return img
