"""Serve only the built Vite frontend. The separate legacy Flask app is not imported."""
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles


def mount_frontend(app):
    default = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
    directory = Path(os.getenv('FRONTEND_DIST', str(default)))
    if directory.is_dir() and (directory / 'index.html').is_file():
        app.mount('/', StaticFiles(directory=str(directory), html=True), name='frontend')
