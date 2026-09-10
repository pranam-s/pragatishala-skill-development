"""ASGI entrypoint for ``uvicorn main:app`` (re-exports the real app)."""

from app.main import app

__all__ = ["app"]
