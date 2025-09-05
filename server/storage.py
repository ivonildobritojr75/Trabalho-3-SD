import json
import shutil
from pathlib import Path
from datetime import datetime
from config import MEDIA_ROOT, SERVER_BASE_URL
import cv2
import imageio

def ensure_media_root():
    """Cria pastas principais do MEDIA_ROOT se não existirem."""
    base = Path(MEDIA_ROOT)
    (base / 'incoming').mkdir(parents=True, exist_ok=True)
    (base / 'videos').mkdir(parents=True, exist_ok=True)
    (base / 'trash').mkdir(parents=True, exist_ok=True)

def save_incoming(file_storage):
    """Salva upload em MEDIA_ROOT/incoming/ com nome seguro."""
    incoming_dir = Path(MEDIA_ROOT) / 'incoming'
    incoming_dir.mkdir(parents=True, exist_ok=True)
    original_name = file_storage.filename
    dest = incoming_dir / original_name
    file_storage.save(dest)
    return dest, original_name

def move_to_final_structure(incoming_path: Path, vid: str, original_name: str):
    """Organiza vídeo em estrutura por data e cria pastas para original, processado e thumbs."""
    now = datetime.utcnow()
    yyyy = f"{now.year:04d}"; mm = f"{now.month:02d}"; dd = f"{now.day:02d}"

    ext = incoming_path.suffix.lower()
    dir_uuid = Path(MEDIA_ROOT) / 'videos' / yyyy / mm / dd / vid
    dir_original = dir_uuid / 'original'
    dir_processed = dir_uuid / 'processed'
    dir_thumbs = dir_uuid / 'thumbs'

    for p in [dir_original, dir_processed, dir_thumbs]:
        p.mkdir(parents=True, exist_ok=True)

    final_original = dir_original / f"video{ext}"
    shutil.move(str(incoming_path), final_original)

    return {
        'dir_uuid': dir_uuid,
        'dir_original': dir_original,
        'dir_processed': dir_processed,
        'dir_thumbs': dir_thumbs,
        'path_original': final_original,
        'ext': ext,
    }

def write_meta_json(path: Path, meta: dict):
    """Salva dicionário como JSON formatado."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def public_paths_for(row: dict):
    """Converte caminhos absolutos em URLs servidas por /media/ ..."""
    def to_url(p: str | None):
        if not p:
            return None
        rel = str(Path(p).relative_to(MEDIA_ROOT)).replace('\\', '/')
        return f"{SERVER_BASE_URL}/media/{rel}"

    return {
        'original_url': to_url(row.get('path_original')),
        'processed_url': to_url(row.get('path_processed')),
        'thumb_url': to_url(row.get('thumb_frame')),
        'preview_url': to_url(row.get('thumb_gif')),
    }

def generate_thumbnails(video_path: Path, thumbs_dir: Path, num_frames: int = 3):
    """
    Gera miniaturas do vídeo e retorna lista de Paths.
    """
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total_frames // (num_frames + 1))

    saved_paths = []
    for i in range(1, num_frames + 1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
        ret, frame = cap.read()
        if ret:
            thumb_path = thumbs_dir / f"thumb_{i}.jpg"
            cv2.imwrite(str(thumb_path), frame)
            saved_paths.append(thumb_path)
    cap.release()
    return saved_paths

def generate_preview_gif(video_path: Path, thumbs_dir: Path, fps: int = 5, max_frames: int = 20):
    """
    Gera GIF de preview do vídeo a partir de frames.
    """
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total_frames // max_frames)

    frames = []
    for i in range(0, max_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)
    cap.release()

    if not frames:
        return None

    gif_path = thumbs_dir / "preview.gif"
    imageio.mimsave(str(gif_path), frames, fps=fps)
    return gif_path
