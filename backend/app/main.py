import ipaddress

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .database import Base, engine
from .routers import data, faq, history, knowledge, reply, settings as settings_router, student
from .schemas import StudentLinkResponse, UpdateCheckResponse, UpdateInstallResponse, UpdateProgressResponse
from .services.app_info import get_app_info
from .services.updater import UpdateError, check_for_update, get_update_progress, start_download_and_launch_update
from .settings import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REMOTE_STATIC_PATHS = {"/favicon.ico", "/app-icon.png"}


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback


def has_student_access(request: Request) -> bool:
    key = request.query_params.get("access_key") or request.headers.get("X-Student-Access-Key")
    return bool(settings.student_access_key and key == settings.student_access_key)


def is_allowed_remote_path(request: Request) -> bool:
    path = request.url.path
    if path in {"/student-chat", "/student-chat/"}:
        return has_student_access(request)
    if path == "/api/student/reply/generate":
        return has_student_access(request)
    return path.startswith("/assets/") or path in REMOTE_STATIC_PATHS


@app.middleware("http")
async def restrict_remote_access(request: Request, call_next):
    client_host = request.client.host if request.client else None
    if not is_loopback_host(client_host) and not is_allowed_remote_path(request):
        return JSONResponse(
            status_code=403,
            content={"detail": "学生网页端只能访问老师提供的完整网页端地址，管理功能仅允许本机使用。"},
        )
    return await call_next(request)


app.include_router(reply.router)
app.include_router(student.router)
app.include_router(knowledge.router)
app.include_router(faq.router)
app.include_router(history.router)
app.include_router(settings_router.router)
app.include_router(data.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/app/info")
def app_info():
    return get_app_info()


@app.get("/api/app/student-link", response_model=StudentLinkResponse)
def student_link(request: Request):
    if settings.student_chat_url:
        return {"url": settings.student_chat_url}
    base_url = str(request.base_url).rstrip("/")
    suffix = f"?access_key={settings.student_access_key}" if settings.student_access_key else ""
    return {"url": f"{base_url}/student-chat{suffix}"}


@app.get("/api/app/update/check", response_model=UpdateCheckResponse)
def update_check():
    try:
        return check_for_update().__dict__
    except UpdateError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/app/update/install", response_model=UpdateInstallResponse)
def update_install():
    try:
        start_download_and_launch_update()
    except UpdateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "message": "已开始下载安装包，请留意下载进度。",
        "installer_path": None,
    }


@app.get("/api/app/update/progress", response_model=UpdateProgressResponse)
def update_progress():
    return get_update_progress()


static_dir = Path(__file__).resolve().parent / "static"


@app.get("/student-chat", include_in_schema=False)
@app.get("/student-chat/", include_in_schema=False)
def student_chat_page():
    index_file = static_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="前端页面尚未构建。")
    return FileResponse(index_file)


if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
