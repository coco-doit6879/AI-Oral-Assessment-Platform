import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from . import (
    academic,
    desktop_policy,
    diagnostic_routes,
    diagnostic_store,
    diagnostics,
    google_login,
    routes_admin,
    routes_exam,
    runtime_settings,
    schemas,
    speech,
    storage,
    stt,
    user_profiles,
)
from .config import settings
from .db import get_db
from .models import Audit, AuthSession, User
from .security import (
    check_client_access,
    cookies,
    current_user,
    digest,
    fail,
    hasher,
    issue_tokens,
    public_user,
    verify_password,
)

cfg = settings()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("oral.api")
# Equal-cost verification for unknown usernames.
dummy_hash = hasher.hash("this-is-not-a-real-account-password")


@asynccontextmanager
async def lifespan(app):
    storage.initialize_storage()
    yield


app = FastAPI(title="AI Oral Assessment API", version="0.1.0", root_path="/api", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-Chunk-Sha256", "X-Oral-Client"],
)


@app.middleware("http")
async def boundary(request: Request, call_next):
    request_id = str(uuid.uuid4())
    # Reject cross-origin cookie mutations, including login CSRF. Non-browser clients use Bearer tokens.
    origin = request.headers.get("origin")
    if (
        request.method not in {"GET", "HEAD", "OPTIONS"}
        and origin
        and origin not in [*cfg.allowed_origins.split(","), runtime_settings.settings().public_origin]
    ):
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "ORIGIN_DENIED", "message": "Origin không được phép", "details": {}}},
        )
    begin = time.monotonic()
    exception_type = None
    try:
        with diagnostics.context(request_id=request_id):
            response = await call_next(request)
    except Exception as exc:
        exception_type = type(exc).__name__
        log.error("request_failed request_id=%s type=%s", request_id, type(exc).__name__)
        response = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Có lỗi xử lý; vui lòng thử lại",
                    "details": {"request_id": request_id},
                }
            },
        )
    resource_id = None
    for key in ("session_id", "attempt_id", "exam_id", "key"):
        value = request.path_params.get(key)
        if value:
            try:
                resource_id = str(uuid.UUID(str(value)))
                break
            except ValueError:
                pass
    if request.url.path not in {"/admin/diagnostics", "/diagnostics/client", "/health"}:
        diagnostic_store.append("API", "ERROR" if response.status_code >= 500 else "WARNING" if response.status_code >= 400 else "INFO", "request_finished", {
            "request_id": request_id, "method": request.method, "exception_type": exception_type, "resource_id": resource_id,
            "path": diagnostic_routes.route_template(request.app, request.url.path),
            "http_status": response.status_code, "elapsed_seconds": round(time.monotonic() - begin, 3),
        })
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    log.info(
        "request_id=%s method=%s path=%s status=%s ms=%.0f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (time.monotonic() - begin) * 1000,
    )
    return response


@app.exception_handler(HTTPException)
async def http_error(_, exc):
    detail = (
        exc.detail
        if isinstance(exc.detail, dict)
        else {"code": "HTTP_ERROR", "message": str(exc.detail), "details": {}}
    )
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_error(_, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dữ liệu không hợp lệ",
                "details": {
                    "fields": [
                        {"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]}
                        for e in exc.errors()
                    ]
                },
            }
        },
    )


@app.exception_handler(IntegrityError)
async def conflict(_, exc):
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "DATA_CONFLICT",
                "message": "Dữ liệu trùng hoặc đang được tham chiếu",
                "details": {},
            }
        },
    )


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    if cfg.redis_url:
        Redis.from_url(cfg.redis_url, socket_timeout=2).ping()
    return {"status": "ok", "ai_provider": runtime_settings.settings().ai_provider}


@app.post("/auth/login")
def login(body: schemas.Login, request: Request, response: Response, db: Session = Depends(get_db)):
    if cfg.redis_url:
        cache = Redis.from_url(cfg.redis_url, socket_timeout=2)
        # Username-based bucket works behind reverse proxies without trusting arbitrary forwarded IPs.
        key = f"login:{digest(body.username.lower())}:{int(time.time() // 60)}"
        count = cache.incr(key)
        cache.expire(key, 65)
        if count > 10:
            fail(429, "RATE_LIMITED", "Quá nhiều lần đăng nhập; thử lại sau 1 phút")
    matches = db.scalars(select(User).where(or_(
        User.username == body.username, func.lower(User.email) == body.username.lower(),
    ))).all()
    user = matches[0] if len(matches) == 1 else None
    verified = verify_password(body.password, user.password_hash if user else dummy_hash)
    if not user or not verified or user.status != "ACTIVE":
        fail(401, "INVALID_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu không đúng")
    check_client_access(user, request)
    access, refresh = issue_tokens(db, user)
    db.add(Audit(user_id=user.id, event="LOGIN", details={}))
    db.commit()
    cookies(response, access, refresh)
    return {"user": public_user(user)}


@app.get("/auth/me")
def me(user=Depends(current_user)):
    return public_user(user)


@app.post("/auth/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token", "")
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest(token)).with_for_update())
    if not row or row.revoked or row.expires_at < time.time():
        fail(401, "INVALID_REFRESH", "Vui lòng đăng nhập lại")
    user = db.get(User, row.user_id)
    if not user or user.status != "ACTIVE":
        fail(401, "INVALID_REFRESH", "Tài khoản không hoạt động")
    check_client_access(user, request)
    row.revoked = True
    access, new_refresh = issue_tokens(db, user)
    db.commit()
    cookies(response, access, new_refresh)
    return {"user": public_user(user)}


@app.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token", "")
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest(token)).with_for_update())
    if row:
        row.revoked = True
        db.commit()
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}


from . import examination, excel_imports, result_roster, storage_management  # noqa: E402

app.include_router(diagnostic_routes.router, tags=["Diagnostics"])
app.include_router(result_roster.router, tags=["Results roster"])
app.include_router(excel_imports.router, tags=["Excel imports"])
app.include_router(storage_management.router, tags=["Storage management"])
app.include_router(examination.router, tags=["Examination workflow"])
app.include_router(desktop_policy.router, tags=["Desktop policy"])
app.include_router(user_profiles.router, tags=["User profiles"])
app.include_router(academic.router, tags=["Academic organization"])
app.include_router(routes_admin.router, prefix="/admin", tags=["Administration"])
app.include_router(routes_exam.router, tags=["Exams and evidence"])
app.include_router(stt.router, tags=["Speech to text"])
app.include_router(speech.router, tags=["Speech configuration"])

app.include_router(runtime_settings.router, tags=["Platform settings"])
app.include_router(google_login.router, tags=["Google sign in"])


@app.middleware("http")
async def freeze_runtime_config(request: Request, call_next):
    with runtime_settings.snapshot():
        return await call_next(request)
