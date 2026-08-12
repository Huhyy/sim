"""Same-origin standalone frontend routes."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


FRONTEND_ROOT = Path(__file__).resolve().parent.parent / "frontend"
router = APIRouter(include_in_schema=False)


@router.get("/")
@router.get("/admin")
def frontend_shell():
    return FileResponse(FRONTEND_ROOT / "index.html")


__all__ = ["FRONTEND_ROOT", "router"]
