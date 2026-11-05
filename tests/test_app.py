import pytest
from fastapi.testclient import TestClient

from app.config import ConfigError, load_settings
from app.main import create_app
from app.security import check_password

GOOD_KEY = "x" * 40


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", GOOD_KEY)
    monkeypatch.setenv("DB_URL", "sqlite://")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("BUCKET", str(tmp_path / "uploads"))
    monkeypatch.setenv("APP_OWNER", "Test Student 123")
    with TestClient(create_app()) as c:
        yield c


def test_health_and_ready(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["checks"] == {"db": True, "storage": True}


def test_home_and_info_show_owner(client):
    assert "Test Student 123" in client.get("/").text
    info = client.get("/info").json()
    assert info["owner"] == "Test Student 123"
    assert info["db_engine"] == "sqlite"


def test_items_crud(client):
    r = client.post("/api/items", json={"title": "Lab 1", "description": "docker"})
    assert r.status_code == 201
    item_id = r.json()["id"]
    assert client.get(f"/api/items/{item_id}").json()["title"] == "Lab 1"
    r = client.put(f"/api/items/{item_id}", json={"title": "Lab 1 v2"})
    assert r.json()["title"] == "Lab 1 v2"
    assert len(client.get("/api/items").json()) == 1
    assert client.delete(f"/api/items/{item_id}").status_code == 204
    assert client.get(f"/api/items/{item_id}").status_code == 404


def test_attachment_roundtrip(client):
    item_id = client.post("/api/items", json={"title": "with file"}).json()["id"]
    r = client.post(f"/api/items/{item_id}/attachment", files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.json()["attachment_name"] == "a.txt"
    assert client.get(f"/api/items/{item_id}/attachment").content == b"hello"


def test_metrics(client):
    client.post("/api/items", json={"title": "m"})
    body = client.get("/metrics").text
    assert "http_requests_total" in body
    assert "items_total 1.0" in body
    assert "db_up 1.0" in body


def test_password_checker(client):
    weak = client.post("/api/admin/check-password", json={"password": "password"}).json()
    assert weak["ok"] is False
    assert weak["rules"]["not_common"] is False
    assert check_password("Str0ng!Passw0rd#2026")["ok"] is True
    assert check_password("Short1!", min_length=12)["rules"]["min_length"] is False


def test_secret_key_required(monkeypatch):
    monkeypatch.setenv("DB_URL", "sqlite://")
    monkeypatch.setenv("SECRET_KEY", "too-short")
    with pytest.raises(ConfigError):
        load_settings()


def test_secrets_from_files(tmp_path, monkeypatch):
    (tmp_path / "key").write_text(GOOD_KEY + "\n")
    (tmp_path / "pw").write_text("p@ss/word")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY_FILE", str(tmp_path / "key"))
    monkeypatch.setenv("DB_PASSWORD_FILE", str(tmp_path / "pw"))
    monkeypatch.setenv("DB_URL", "postgresql+psycopg://app_rw:${DB_PASSWORD}@db:5432/campus")
    s = load_settings()
    assert s.secret_key == GOOD_KEY
    assert s.db_url == "postgresql+psycopg://app_rw:p%40ss%2Fword@db:5432/campus"
    assert s.db_engine == "postgresql"
