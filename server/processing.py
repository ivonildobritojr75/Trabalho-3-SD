# server/processing.py
from pathlib import Path
import cv2
import numpy as np
import imageio
import hashlib

SUPPORTED_FILTERS = {"grayscale", "pixelate", "edges"}

def probe_video(src_path: Path) -> dict:
    cap = cv2.VideoCapture(str(src_path))
    if not cap.isOpened():
        return {}
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frames / fps if fps > 0 else 0
    cap.release()

    sha1 = hashlib.sha1()
    with open(src_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            sha1.update(chunk)

    return {
        'fps': float(fps),
        'width': w,
        'height': h,
        'duration_sec': float(duration),
        'checksums': { 'sha1': sha1.hexdigest() }
    }

def _apply_filter(frame, name: str):
    if name == 'grayscale':
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    elif name == 'pixelate':
        h, w = frame.shape[:2]
        scale = max(1, min(w, h) // 32)
        small = cv2.resize(frame, (w//scale, h//scale), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    elif name == 'edges':
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.Canny(gray, 100, 200)
    else:
        return frame

def process_video(src_path: Path, dst_dir: Path, out_name: str, filter_name: str):
    filter_name = (filter_name or 'grayscale').lower()
    if filter_name not in SUPPORTED_FILTERS:
        filter_name = 'grayscale'

    dst_dir.mkdir(parents=True, exist_ok=True)
    out_path = dst_dir / out_name

    cap = cv2.VideoCapture(str(src_path))
    if not cap.isOpened():
        return False, None

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)

    # Usa H.264 para web (se disponível), senão cai no XVID
    if out_path.suffix.lower() in {'.mp4', '.m4v', '.mov'}:
        fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264
    else:
        fourcc = cv2.VideoWriter_fourcc(*'XVID')

    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h), True)
    if not writer.isOpened():
        cap.release()
        return False, None

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        proc = _apply_filter(frame, filter_name)
        if len(proc.shape) == 2:  # grayscale/edges
            proc = cv2.cvtColor(proc, cv2.COLOR_GRAY2BGR)
        writer.write(proc)

    cap.release()
    writer.release()
    return True, out_path

def generate_thumbnails(src_path: Path, thumbs_dir: Path):
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(src_path))
    first_frame_path = None
    frames_for_gif = []
    step = 5
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx == 0:
            first = frame
            first_frame_path = thumbs_dir / 'frame_0001.jpg'
            cv2.imwrite(str(first_frame_path), first)
        if idx % step == 0 and len(frames_for_gif) < 40:
            bgr = frame
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            frames_for_gif.append(rgb)
        idx += 1
    cap.release()

    preview_gif_path = None
    if frames_for_gif:
        preview_gif_path = thumbs_dir / 'preview.gif'
        imageio.mimsave(preview_gif_path, frames_for_gif, fps=8)

    return first_frame_path, preview_gif_path
