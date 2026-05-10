import base64
import json
import os
import re
import textwrap
import time
import urllib.error
import urllib.request
from io import BytesIO

import cv2
import numpy as np
import torch
from openai import OpenAI
from PIL import Image
from ultralytics.models.sam import Predictor as SAMPredictor


def _load_env_from_file(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _bootstrap_env() -> None:
    # Priority: process env > project .env > ~/.env
    _load_env_from_file(os.path.expanduser("~/.env"))
    _load_env_from_file(os.path.join(os.getcwd(), ".env"))


def _build_client_and_model() -> tuple[OpenAI, str]:
    _bootstrap_env()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    model = os.getenv("VLM_MODEL", "qwen-vl-plus").strip()

    if not api_key and os.getenv("GEMINI_API_KEY"):
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        base_url = os.getenv(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        ).strip()
        model = os.getenv("GEMINI_MODEL", "gemini-3-flash").strip()

    if not api_key:
        raise RuntimeError(
            "Missing API key. Set OPENAI_API_KEY or GEMINI_API_KEY in ~/.env."
        )

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs), model


def encode_np_array(image_np: np.ndarray) -> str:
    image = Image.fromarray(np.asarray(image_np, dtype=np.uint8), mode="RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def generate_robot_actions(user_command: str, image_input: np.ndarray | None = None) -> dict:
    """Call multimodal LLM and parse natural language + JSON bbox."""
    client, model_name = _build_client_and_model()

    system_prompt = textwrap.dedent(
        """
        你是机械臂视觉控制助手。请从图像和用户指令中选出目标物体，
        输出两部分：
        1) 一句自然语言说明（仅说明目标）
        2) 下一行输出 JSON:
        {
          "name": "object_name",
          "bbox": [x1, y1, x2, y2]
        }
        注意：只输出上述两部分，不要多余解释。
        """
    ).strip()

    messages = [{"role": "system", "content": system_prompt}]
    user_content = []

    if image_input is not None:
        base64_img = encode_np_array(image_input)
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"},
            }
        )

    user_content.append({"type": "text", "text": user_command})
    messages.append({"role": "user", "content": user_content})

    last_error = None
    for attempt in range(1, 4):
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.1,
                timeout=60,
            )

            content = completion.choices[0].message.content or ""
            match = re.search(r"(\{.*\})", content, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    coord = json.loads(json_str)
                except Exception:
                    coord = {}
                natural_response = content[: match.start()].strip()
            else:
                natural_response = content.strip()
                coord = {}

            return {"response": natural_response, "coordinates": coord}
        except Exception as exc:
            last_error = exc
            print(f"LLM request failed (attempt {attempt}/3): {exc}")
            time.sleep(1.5 * attempt)

    print(f"LLM request failed permanently: {last_error}")
    return {"response": "处理失败", "coordinates": {}}


def _default_sam_device() -> str:
    configured = os.getenv("OPENCLAW_SAM_DEVICE", "").strip()
    if configured:
        return configured

    if not torch.cuda.is_available():
        return "cpu"

    total_memory = torch.cuda.get_device_properties(0).total_memory
    if total_memory <= 8 * 1024**3:
        return "cpu"

    return "cuda:0"


def choose_model() -> SAMPredictor:
    device = _default_sam_device()
    overrides = {
        "task": "segment",
        "mode": "predict",
        "model": "sam_b.pt",
        "conf": 0.25,
        "save": False,
        "device": device,
    }
    print(f"[sam] local_device={device}")
    return SAMPredictor(overrides=overrides)


def process_sam_results(results):
    if not results or not results[0].masks:
        return None, None

    mask = results[0].masks.data[0].cpu().numpy()
    mask = (mask > 0).astype(np.uint8) * 255

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None

    m = cv2.moments(contours[0])
    if m["m00"] == 0:
        return None, mask

    cx = int(m["m10"] / m["m00"])
    cy = int(m["m01"] / m["m00"])
    return (cx, cy), mask


def _bbox_mask(shape: tuple[int, int], bbox) -> np.ndarray | None:
    if not bbox or len(bbox) != 4:
        return None
    height, width = shape
    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1 = max(0, min(width - 1, x1))
    x2 = max(0, min(width - 1, x2))
    y1 = max(0, min(height - 1, y1))
    y2 = max(0, min(height - 1, y2))
    if x2 <= x1 or y2 <= y1:
        return None
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[y1:y2, x1:x2] = 255
    return mask


def _full_image_mask(shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[:, :] = 255
    return mask


def _normalize_object_name(name: str) -> str:
    text = (name or "").strip().lower()
    aliases = {
        "banana": ["banana", "bananas", "xiangjiao", "香蕉"],
        "apple": ["apple", "pingguo", "苹果"],
        "hammer": ["hammer", "chui", "chuizi", "锤子"],
        "knife": ["knife", "dao", "xiaodao", "刀", "小刀"],
        "duck": ["duck", "yellow duck", "toy duck", "ya", "yazi", "鸭子", "小黄鸭"],
    }
    for canonical, values in aliases.items():
        if text == canonical or text in values:
            return canonical
    return text or "object"


def _extract_segmentation_label(command_text: str, detection_info: dict) -> str:
    name = str(detection_info.get("name", "")).strip()
    if name:
        return _normalize_object_name(name)

    command = command_text or ""
    command_lower = command.lower()
    english_aliases = {
        "banana": "banana",
        "apple": "apple",
        "hammer": "hammer",
        "knife": "knife",
        "duck": "duck",
    }
    for key, value in english_aliases.items():
        if key in command_lower:
            return value

    chinese_aliases = {
        "香蕉": "banana",
        "苹果": "apple",
        "锤子": "hammer",
        "小刀": "knife",
        "刀": "knife",
        "小黄鸭": "duck",
        "鸭子": "duck",
    }
    for key, value in chinese_aliases.items():
        if key in command:
            return value

    return "object"


def _segment_with_roboflow(image_input: np.ndarray, label: str) -> np.ndarray | None:
    api_key = os.getenv("ROBOFLOW_API_KEY", "").strip()
    if not api_key:
        return None

    base_url = os.getenv(
        "ROBOFLOW_SAM_URL",
        "https://serverless.roboflow.com/sam3/concept_segment",
    ).strip()
    payload = {
        "image": {"type": "base64", "value": encode_np_array(image_input)},
        "prompts": [{"type": "text", "text": label}],
        "format": "polygon",
        "output_prob_thresh": 0.2,
    }

    data = None
    last_error = None
    for attempt in range(1, 4):
        request = urllib.request.Request(
            url=f"{base_url}?api_key={api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            print(f"[sam] Roboflow HTTP {exc.code} (attempt {attempt}/3): {body[:300]}")
            last_error = exc
        except Exception as exc:
            print(f"[sam] Roboflow request failed (attempt {attempt}/3): {exc}")
            last_error = exc
        time.sleep(1.5 * attempt)

    if data is None:
        print(f"[sam] Roboflow failed permanently for '{label}': {last_error}")
        return None

    prompt_results = data.get("prompt_results") or []
    predictions = []
    for prompt_result in prompt_results:
        predictions.extend(prompt_result.get("predictions") or [])

    if not predictions:
        print(f"[sam] Roboflow returned no predictions for '{label}'.")
        return None

    height, width = image_input.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    best_prediction = max(
        predictions,
        key=lambda item: float(item.get("confidence") or 0.0),
    )
    polygons = best_prediction.get("masks") or []
    for polygon in polygons:
        points = np.asarray(polygon, dtype=np.int32)
        if points.ndim != 2 or len(points) < 3:
            continue
        points[:, 0] = np.clip(points[:, 0], 0, width - 1)
        points[:, 1] = np.clip(points[:, 1], 0, height - 1)
        cv2.fillPoly(mask, [points], 255)

    if not np.any(mask):
        print("[sam] Roboflow prediction did not produce a valid mask.")
        return None

    print(
        f"[sam] Roboflow SAM3 success: label={label}, "
        f"confidence={float(best_prediction.get('confidence') or 0.0):.3f}"
    )
    return mask


def _segment_with_local_sam(
    image_input: np.ndarray,
    bbox,
) -> np.ndarray | None:
    # image_input from MuJoCo render() is already RGB.
    image_rgb = np.asarray(image_input, dtype=np.uint8)

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    predictor = None
    try:
        predictor = choose_model()
        predictor.set_image(image_rgb)

        if bbox:
            results = predictor(bboxes=[bbox])
            _, mask = process_sam_results(results)
            print(f"Using bbox from VLM: {bbox}")
        else:
            print("VLM did not return bbox. Click object in window.")
            cv2.namedWindow("Select Object", cv2.WINDOW_NORMAL)
            cv2.imshow("Select Object", cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))
            point = []

            def click_handler(event, x, y, flags, param):
                if event == cv2.EVENT_LBUTTONDOWN:
                    point.extend([x, y])
                    cv2.setMouseCallback("Select Object", lambda *args: None)

            cv2.setMouseCallback("Select Object", click_handler)
            while True:
                _ = cv2.waitKey(100)
                if point:
                    break
                if cv2.getWindowProperty("Select Object", cv2.WND_PROP_VISIBLE) < 1:
                    print("Selection window closed.")
                    return None
            cv2.destroyAllWindows()
            results = predictor(points=[point], labels=[1])
            _, mask = process_sam_results(results)

        return mask
    except torch.OutOfMemoryError as exc:
        print(f"[sam] local SAM OOM: {exc}")
        return None
    except Exception as exc:
        print(f"[sam] local SAM failed: {exc}")
        return None
    finally:
        if predictor is not None:
            del predictor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def _segment_with_fallback(
    image_input: np.ndarray,
    bbox,
    label: str,
) -> tuple[np.ndarray | None, str]:
    backend = os.getenv("OPENCLAW_SEGMENT_BACKEND", "auto").strip().lower()

    if backend in {"auto", "roboflow"}:
        mask = _segment_with_roboflow(image_input, label)
        if mask is not None:
            return mask, "roboflow_sam3"
        if backend == "roboflow":
            return _bbox_mask(image_input.shape[:2], bbox), "bbox_fallback"

    if backend in {"auto", "local", "sam", "ultralytics"}:
        mask = _segment_with_local_sam(image_input, bbox)
        if mask is not None:
            return mask, "local_sam"
        if backend in {"local", "sam", "ultralytics"}:
            return _bbox_mask(image_input.shape[:2], bbox), "bbox_fallback"

    return _bbox_mask(image_input.shape[:2], bbox), "bbox_fallback"


def _save_segmentation_debug(
    image_input: np.ndarray,
    mask: np.ndarray | None,
    bbox,
    output_mask: str,
    label: str,
    backend: str,
) -> None:
    stem, _ = os.path.splitext(output_mask)
    input_path = f"{stem}_input.png"
    bbox_path = f"{stem}_bbox.png"
    overlay_path = f"{stem}_overlay.png"

    cv2.imwrite(input_path, cv2.cvtColor(image_input, cv2.COLOR_RGB2BGR))

    bbox_image = image_input.copy()
    if bbox and len(bbox) == 4:
        x1, y1, x2, y2 = [int(v) for v in bbox]
        cv2.rectangle(bbox_image, (x1, y1), (x2, y2), (0, 180, 255), 2)
        cv2.putText(
            bbox_image,
            f"{label} [{backend}]",
            (max(0, x1), max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 180, 255),
            2,
            cv2.LINE_AA,
        )
    else:
        cv2.putText(
            bbox_image,
            f"{label} [{backend}]",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 180, 255),
            2,
            cv2.LINE_AA,
        )
    cv2.imwrite(bbox_path, cv2.cvtColor(bbox_image, cv2.COLOR_RGB2BGR))

    overlay = image_input.copy()
    if mask is not None and np.any(mask > 0):
        colored = np.zeros_like(overlay)
        colored[:, :] = (60, 220, 60)
        alpha = 0.35
        overlay = np.where(
            mask[..., None] > 0,
            (overlay * (1.0 - alpha) + colored * alpha).astype(np.uint8),
            overlay,
        )
        contours, _ = cv2.findContours(
            (mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(overlay, contours, -1, (0, 255, 0), 2)
    if bbox and len(bbox) == 4:
        x1, y1, x2, y2 = [int(v) for v in bbox]
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 180, 255), 2)
    cv2.putText(
        overlay,
        f"{label} [{backend}]",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.imwrite(overlay_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    print(
        f"[sam] debug images: {input_path}, {bbox_path}, {overlay_path}"
    )


def segment_image(
    image_input: np.ndarray,
    output_mask: str = "mask1.png",
    command_text: str | None = None,
    bbox_override=None,
    label_override: str | None = None,
):
    if command_text is None:
        print("Please describe target object and grasp intent.")
        command_text = input("Enter command: ").strip()

    if not command_text:
        print("No command provided.")
        return None

    result = generate_robot_actions(command_text, image_input)
    natural_response = result.get("response", "")
    detection_info = result.get("coordinates", {}) or {}

    if natural_response:
        print(f"VLM: {natural_response}")

    bbox = bbox_override if bbox_override is not None else detection_info.get("bbox")
    label = label_override or _extract_segmentation_label(command_text, detection_info)
    print(f"[sam] target_label={label}")
    if bbox_override is not None:
        print(f"[sam] using scene bbox override: {bbox}")
    mask, backend = _segment_with_fallback(image_input, bbox, label)
    print(f"[sam] backend={backend}")
    if mask is None:
        print("[sam] all segmentation backends failed, using full-image fallback mask.")
        mask = _full_image_mask(image_input.shape[:2])
        backend = "full_image_fallback"

    if mask is not None:
        if bbox:
            print(f"Using bbox from VLM: {bbox}")
        cv2.imwrite(output_mask, mask, [cv2.IMWRITE_PNG_BILEVEL, 1])
        print(f"Saved segmentation mask: {output_mask}")
        if os.getenv("OPENCLAW_SEGMENT_DEBUG", "1").strip().lower() not in {
            "0",
            "false",
            "no",
        }:
            _save_segmentation_debug(
                image_input,
                mask,
                bbox,
                output_mask,
                label,
                backend,
            )
    else:
        print("Segmentation failed.")

    return mask


if __name__ == "__main__":
    print("This module is designed to be imported by main_vlm.py.")
