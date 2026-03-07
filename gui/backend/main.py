"""FolderDiff GUI 백엔드 — FastAPI 앱 진입점."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.browse import router as browse_router
from .api.compare import router as compare_router
from .api.merge import router as merge_router

# ── 앱 생성 ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FolderDiff API",
    description="폴더/파일 비교 및 머지 도구 REST API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS (개발 환경) ──────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # dev 서버
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 라우터 등록 ───────────────────────────────────────────────────────────────

app.include_router(browse_router)
app.include_router(compare_router)
app.include_router(merge_router)

# ── 정적 파일 & SPA 서빙 ──────────────────────────────────────────────────────

_FRONTEND = Path(__file__).parent.parent / "frontend"
_STATIC = _FRONTEND / "static"

if _STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str = "") -> FileResponse:
    """SPA index.html을 서빙한다. API 경로는 제외."""
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    index = _FRONTEND / "index.html"
    return FileResponse(str(index))
