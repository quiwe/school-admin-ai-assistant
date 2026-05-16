from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .database import Base, engine
from .routers import data, faq, history, knowledge, reply, settings as settings_router
from .schemas import UpdateCheckResponse, UpdateInstallResponse
from .services.app_info import get_app_info
from .services.updater import UpdateError, check_for_update, download_and_launch_update
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

app.include_router(reply.router)
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


@app.get("/api/app/update/check", response_model=UpdateCheckResponse)
def update_check():
    try:
        return check_for_update().__dict__
    except UpdateError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/app/update/install", response_model=UpdateInstallResponse)
def update_install():
    try:
        installer = download_and_launch_update()
    except UpdateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "message": "安装程序已启动，请按提示完成更新。桌面端会自动关闭。",
        "installer_path": str(installer),
    }


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
