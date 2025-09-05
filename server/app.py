import os
import uuid
from flask import Flask, request, jsonify, send_from_directory, abort, render_template_string
from datetime import datetime
from pathlib import Path

from config import MEDIA_ROOT, DB_PATH, ALLOWED_EXTS, SERVER_HOST, SERVER_PORT, SERVER_DEBUG
from db import init_db, insert_video, list_videos, get_video
from storage import (
    ensure_media_root, save_incoming, move_to_final_structure,
    write_meta_json, generate_thumbnails, generate_preview_gif, public_paths_for,
)
from processing import process_video, probe_video

app = Flask(__name__)

def allowed_file(filename: str):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS

# ==========================
# Endpoints
# ==========================

@app.route('/api/health')
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat() + "Z"}

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "Campo 'file' ausente"}), 400

    f = request.files['file']
    chosen_filter = (request.form.get('filter') or 'grayscale').strip().lower()
    if f.filename == '':
        return jsonify({"error": "Arquivo não selecionado"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": f"Extensão não permitida: {f.filename}"}), 400

    ensure_media_root()
    incoming_path, original_name = save_incoming(f)

    vid = str(uuid.uuid4())
    paths = move_to_final_structure(incoming_path, vid, original_name)

    meta_probe = probe_video(paths['path_original'])

    dst_dir = paths['dir_processed'] / chosen_filter
    dst_dir.mkdir(parents=True, exist_ok=True)
    ok, processed_path = process_video(
        src_path=paths['path_original'],
        dst_dir=dst_dir,
        out_name='video' + paths['ext'],
        filter_name=chosen_filter,
    )
    if not ok:
        return jsonify({"error": "Falha ao processar vídeo"}), 500

    # Thumbnails
    thumbs = generate_thumbnails(processed_path, paths['dir_thumbs'], num_frames=1)
    first_frame_path = thumbs[0] if thumbs else None

    # Preview GIF
    preview_gif_path = generate_preview_gif(processed_path, paths['dir_thumbs'], fps=5, max_frames=20)

    meta = {
        "id": vid,
        "original_name": original_name,
        "original_ext": paths['ext'][1:],
        "mime_type": getattr(f, 'mimetype', None),
        "size_bytes": os.path.getsize(paths['path_original']),
        "duration_sec": meta_probe.get('duration_sec'),
        "fps": meta_probe.get('fps'),
        "width": meta_probe.get('width'),
        "height": meta_probe.get('height'),
        "filter": chosen_filter,
        "created_at": datetime.utcnow().isoformat() + 'Z',
        "path_original": str(paths['path_original']),
        "path_processed": str(processed_path),
        "thumb_frame": str(first_frame_path) if first_frame_path else None,
        "thumb_gif": str(preview_gif_path) if preview_gif_path else None,
        "checksums": meta_probe.get('checksums', {}),
        "params": {"filter": chosen_filter}
    }

    write_meta_json(paths['dir_uuid'] / 'meta.json', meta)
    init_db(DB_PATH)
    insert_video(meta)

    public = public_paths_for(meta)
    return jsonify({
        "ok": True,
        "id": vid,
        "filter": chosen_filter,
        "original_url": public['original_url'],
        "processed_url": public['processed_url'],
        "thumb_url": public['thumb_url'],
        "preview_url": public['preview_url'],
        "detail_url": f"/api/videos/{vid}",
    })

@app.route('/api/videos', methods=['GET'])
def api_videos():
    rows = list_videos(limit=int(request.args.get('limit', 100)))
    for r in rows:
        r.update(public_paths_for(r))
    return jsonify(rows)

@app.route('/api/videos/<vid>', methods=['GET'])
def api_video_detail(vid):
    row = get_video(vid)
    if not row:
        return jsonify({"error": "não encontrado"}), 404
    row.update(public_paths_for(row))
    return jsonify(row)

@app.route('/media/<path:subpath>')
def media_serve(subpath):
    base = Path(MEDIA_ROOT)
    target = base / subpath
    if not target.exists():
        abort(404)
    return send_from_directory(base, subpath, as_attachment=False)

# ==========================
# Galeria web
# ==========================

TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Galeria de Vídeos Processados</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 12px; }
    .thumb { width: 100%; border-radius: 8px; object-fit: cover; aspect-ratio: 16/9; }
    .meta { font-size: 12px; color: #444; margin-top: 6px; line-height: 1.4; }
    .links { margin-top: 8px; display: flex; gap: 8px; }
    a { text-decoration: none; color: #0b6; }
  </style>
</head>
<body>
  <h1>Galeria de Vídeos Processados</h1>
  <div class="grid">
    {% for v in videos %}
      <div class="card">
        <img class="thumb" src="{{ v.thumb_url or v.preview_url }}" alt="thumb">
        <div class="meta">
          <div><b>ID:</b> {{ v.id }}</div>
          <div><b>Filtro:</b> {{ v.filter }}</div>
          <div><b>Resolução:</b> {{ v.width }}×{{ v.height }} @ {{ v.fps }} fps</div>
          <div><b>Duração:</b> {{ '%.2f' % (v.duration_sec or 0) }} s</div>
          <div><b>Original:</b> {{ v.original_name }}</div>
        </div>
        <div class="links">
          <a href="{{ v.original_url }}" target="_blank">Original</a>
          <a href="{{ v.processed_url }}" target="_blank">Processado</a>
          {% if v.preview_url %}<a href="{{ v.preview_url }}" target="_blank">Preview</a>{% endif %}
          <a href="/api/videos/{{ v.id }}" target="_blank">JSON</a>
        </div>
      </div>
    {% endfor %}
  </div>
</body>
</html>
"""

@app.route('/')
def gallery():
    rows = list_videos(limit=100)
    for r in rows:
        r.update(public_paths_for(r))
    return render_template_string(TEMPLATE, videos=rows)

# ==========================
# Inicialização
# ==========================

if __name__ == '__main__':
    Path(MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
    init_db(DB_PATH)
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=SERVER_DEBUG)
