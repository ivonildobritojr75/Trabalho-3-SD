# server/config.py
import os
from pathlib import Path

# Diretório raiz de mídia (pode ser absoluto). Por padrão, cria na raiz do projeto.
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', str(Path(__file__).resolve().parents[1] / 'MEDIA_ROOT'))

# Caminho do banco SQLite
DB_PATH = os.environ.get('DB_PATH', 'server.db')

# Extensões permitidas
ALLOWED_EXTS = set((os.environ.get('ALLOWED_EXTS') or 'mp4,mov,avi,mkv').split(','))

# Servidor Flask
SERVER_HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.environ.get('SERVER_PORT', '5000'))
SERVER_DEBUG = os.environ.get('SERVER_DEBUG', '1') == '1'

# Base URL pública do servidor (usada para montar links /media/...)
SERVER_BASE_URL = os.environ.get('SERVER_BASE_URL', f'http://localhost:{SERVER_PORT}')
