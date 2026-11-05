"""campus-app HTTP API (FastAPI)."""

import html
import logging
import socket
import sys
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import select

from .analytics import Analytics
from .config import ConfigError, Settings, load_settings
from .db import Database, Item
from .logs import setup_logging
from .security import check_password
from .storage import make_storage

log = logging.getLogger("campus")
HOSTNAME = socket.gethostname()


class ItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)


class ItemOut(ItemIn):
    id: int
    created_at: str
    attachment_name: str | None = None


class PasswordIn(BaseModel):
    password: str


def to_out(item: Item) -> ItemOut:
    return ItemOut(
        id=item.id,
        title=item.title,
        description=item.description,
        created_at=item.created_at.isoformat(),
        attachment_name=item.attachment_name,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    setup_logging(settings.log_level, settings.log_format, settings.secrets)

    db = Database(settings.db_url)
    storage = make_storage(settings.storage_backend, settings.bucket)

    registry = CollectorRegistry()
    requests_total = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"], registry=registry)
    latency = Histogram("http_request_duration_seconds", "Request latency", ["method", "route"], registry=registry)
    items_total = Gauge("items_total", "Items stored in the database", registry=registry)
    db_up = Gauge("db_up", "1 if the database answers", registry=registry)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.create_schema()
        app.state.analytics = Analytics(settings.clickhouse_url, settings.app_owner)
        log.info("started", extra={"event": "startup"})
        log.info("db=%s storage=%s version=%s", settings.db_engine, settings.storage_backend, settings.app_version)
        yield
        db.engine.dispose()
        log.info("stopped", extra={"event": "shutdown"})

    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = getattr(request.scope.get("route"), "path", "unmatched")
            requests_total.labels(request.method, route, str(status)).inc()
            latency.labels(request.method, route).observe(elapsed)
            if route != "/metrics":
                log.info(
                    "request",
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status,
                        "duration_ms": round(elapsed * 1000, 1),
                    },
                )

    @app.get("/", response_class=HTMLResponse)
    def home():
        return (
            f"<!doctype html><title>{html.escape(settings.app_name)}</title>"
            f"<h1>{html.escape(settings.app_name)}</h1>"
            f"<p>Owner: <b>{html.escape(settings.app_owner)}</b></p>"
            f"<p>Version {html.escape(settings.app_version)} · served by {html.escape(HOSTNAME)}</p>"
        )

    @app.get("/info")
    def info():
        return {
            "app": settings.app_name,
            "owner": settings.app_owner,
            "version": settings.app_version,
            "git_sha": settings.git_sha,
            "hostname": HOSTNAME,
            "db_engine": settings.db_engine,
            "storage_backend": settings.storage_backend,
            "analytics": app.state.analytics.enabled,
        }

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz():
        checks = {"db": db.ping(), "storage": storage.check()}
        code = 200 if all(checks.values()) else 503
        return JSONResponse({"ready": code == 200, "checks": checks}, status_code=code)

    @app.get("/metrics")
    def metrics():
        up = db.ping()
        db_up.set(1 if up else 0)
        if up:
            items_total.set(db.count_items())
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/items", response_model=list[ItemOut])
    def list_items(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        with db.session() as s:
            rows = s.scalars(select(Item).order_by(Item.id).limit(limit).offset(offset)).all()
            return [to_out(i) for i in rows]

    @app.post("/api/items", response_model=ItemOut, status_code=201)
    def create_item(body: ItemIn):
        with db.session() as s:
            item = Item(title=body.title, description=body.description)
            s.add(item)
            s.commit()
            app.state.analytics.record("create", item.id)
            return to_out(item)

    def get_or_404(s, item_id: int) -> Item:
        item = s.get(Item, item_id)
        if not item:
            raise HTTPException(404, "item not found")
        return item

    @app.get("/api/items/{item_id}", response_model=ItemOut)
    def get_item(item_id: int):
        with db.session() as s:
            return to_out(get_or_404(s, item_id))

    @app.put("/api/items/{item_id}", response_model=ItemOut)
    def update_item(item_id: int, body: ItemIn):
        with db.session() as s:
            item = get_or_404(s, item_id)
            item.title, item.description = body.title, body.description
            s.commit()
            app.state.analytics.record("update", item.id)
            return to_out(item)

    @app.delete("/api/items/{item_id}", status_code=204)
    def delete_item(item_id: int):
        with db.session() as s:
            s.delete(get_or_404(s, item_id))
            s.commit()
            app.state.analytics.record("delete", item_id)
        return Response(status_code=204)

    @app.post("/api/items/{item_id}/attachment", response_model=ItemOut)
    async def upload(item_id: int, file: UploadFile):
        data = await file.read()
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(413, "file too large (max 10 MB)")
        with db.session() as s:
            item = get_or_404(s, item_id)
            key = f"items/{item_id}/{uuid.uuid4().hex}"
            storage.put(key, data, file.content_type or "application/octet-stream")
            item.attachment_key, item.attachment_name = key, file.filename
            item.attachment_type = file.content_type
            s.commit()
            app.state.analytics.record("attach", item.id)
            return to_out(item)

    @app.get("/api/items/{item_id}/attachment")
    def download(item_id: int):
        with db.session() as s:
            item = get_or_404(s, item_id)
            if not item.attachment_key:
                raise HTTPException(404, "no attachment")
            data = storage.get(item.attachment_key)
            headers = {"content-disposition": f'attachment; filename="{item.attachment_name}"'}
            return Response(data, media_type=item.attachment_type or "application/octet-stream", headers=headers)

    @app.post("/api/admin/check-password")
    def password_policy(body: PasswordIn):
        return check_password(body.password, settings.password_min_length)

    return app


def _build() -> FastAPI:
    try:
        return create_app()
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


app = _build() if "pytest" not in sys.modules else None
