"""FastAPI endpoints: input validation, uploads, health."""

import pytest
from fastapi.testclient import TestClient

from lumen.api import server


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "UPLOAD_DIR", tmp_path / "uploads")
    return TestClient(server.app)


def _register(client, src, ref):
    return client.post("/api/v1/register", json={
        "source_sensor": "TMC2", "reference_sensor": "TMC2",
        "source_path": src, "reference_path": ref,
    })


def test_register_rejects_paths_outside_data_dir(client):
    r = _register(client, "../../etc/passwd", "lumen/cli.py")
    assert r.status_code == 400
    assert not server.jobs or all(j.get("status") != "pending" for j in server.jobs.values())


def test_register_rejects_missing_file(client):
    r = _register(client, "data/does_not_exist.xml", "data/does_not_exist.xml")
    assert r.status_code == 404


def test_unknown_job_is_404(client):
    assert client.get("/api/v1/jobs/nope").status_code == 404


def test_upload_saves_file(client, tmp_path):
    r = client.post("/api/v1/upload", files={"file": ("label.xml", b"<Product/>")})
    assert r.status_code == 200
    assert r.json()["size"] == 10
    assert (tmp_path / "uploads" / "label.xml").read_bytes() == b"<Product/>"


@pytest.mark.parametrize("name", ["evil.exe", "spaces in name.xml", "noext"])
def test_upload_rejects_bad_names(client, name):
    assert client.post("/api/v1/upload", files={"file": (name, b"x")}).status_code == 400


def test_upload_strips_directories(client, tmp_path):
    r = client.post("/api/v1/upload", files={"file": ("../escape.xml", b"x")})
    assert r.status_code == 200
    assert (tmp_path / "uploads" / "escape.xml").exists()
    assert not (tmp_path / "escape.xml").exists()


def test_health_reports_real_gpu_state(client):
    import torch

    body = client.get("/health").json()
    assert body["status"] == "healthy"
    assert body["cuda"] == torch.cuda.is_available()  # used to always claim "available"
