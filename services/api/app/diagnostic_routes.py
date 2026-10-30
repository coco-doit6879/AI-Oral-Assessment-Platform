import sqlite3
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import Field
from starlette.routing import compile_path

from . import diagnostic_store
from .schemas import Input
from .security import admin, current_user, fail

router = APIRouter()


@lru_cache(maxsize=4)
def route_patterns(app):
    # OpenAPI exposes effective paths for both flattened and lazily included routers.
    return [(compile_path(path)[0], path) for path in app.openapi()["paths"]]


def route_template(app, path):
    # Only route templates are retained, not URLs, queries or arbitrary client strings.
    path = path.split("?", 1)[0].split("#", 1)[0]
    for pattern, template in route_patterns(app):
        if pattern.fullmatch(path):
            return template
    return "(unmatched)"


@router.get("/admin/diagnostics")
def logs(source: Literal["API", "WEB", "AI", "WORKER"] | None = None,
         level: Literal["INFO", "WARNING", "ERROR"] | None = None,
         correlation: str | None = Query(None, max_length=200), model: str | None = Query(None, max_length=200),
         before: int | None = Query(None, gt=0), since: float | None = Query(None, ge=0, allow_inf_nan=False),
         limit: int = Query(50, ge=1, le=100), user=Depends(admin)):
    try:
        return diagnostic_store.read(source=source, level=level, correlation=correlation, model=model,
                                     before=before, since=since, limit=limit)
    except (OSError, sqlite3.Error):
        fail(503, "DIAGNOSTICS_UNAVAILABLE", "Không đọc được kho log; kiểm tra quyền ghi và dung lượng DATA_DIR.")


class ClientEvent(Input):
    view: Literal["dashboard", "courses", "exams", "results", "users", "settings", "storage", "logs", "academic", "classes", "departments", "examination", "student", "unknown"] = "unknown"
    exception_type: Literal["Error", "TypeError", "RangeError", "ReferenceError", "SyntaxError", "URIError", "EvalError", "UnknownError"] | None = None
    event: Literal["request_failed", "client_error", "unhandled_rejection"]
    path: str = Field(default="/", max_length=1000)
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"] = "GET"
    http_status: int | None = Field(None, ge=0, le=599)
    request_id: str | None = Field(None, max_length=36, pattern=r"^[a-fA-F0-9-]{36}$")


@router.post("/diagnostics/client", status_code=204)
def client_event(body: ClientEvent, request: Request, user=Depends(current_user)):
    diagnostic_store.append("WEB", "ERROR", body.event, {
        "path": route_template(request.app, body.path), "method": body.method,
        "view": body.view, "exception_type": body.exception_type, "http_status": body.http_status, "request_id": body.request_id, "user_id": user.id,
    }, throttle_user=user.id)
    return Response(status_code=204)
