from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.web import mount_frontend
from serve import restore_demo


def test_hosted_spa_deep_links_and_missing_api(tmp_path):
    (tmp_path / "index.html").write_text("<h1>VeriSense</h1>", encoding="utf-8")
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    mount_frontend(app, str(tmp_path))
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert "VeriSense" in client.get("/portal/applications/1").text
        assert client.get("/evaluation").status_code == 200
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/not-a-route").status_code == 404
        assert client.get("/mock/not-a-route").status_code == 404
        assert client.get("/assets/missing.js").status_code == 404


def test_restart_does_not_overwrite_saved_database_or_uploads(tmp_path):
    snapshot = tmp_path / "snapshot"
    (snapshot / "storage").mkdir(parents=True)
    (snapshot / "storage/demo.pdf").write_bytes(b"sample")
    (snapshot / "verisense.db").write_bytes(b"initial")
    data = tmp_path / "data"
    restore_demo(snapshot, data)
    assert (data / "storage/demo.pdf").read_bytes() == b"sample"
    (data / "verisense.db").write_bytes(b"officer decisions")
    (data / "storage/new.pdf").write_bytes(b"upload")
    restore_demo(snapshot, data)
    assert (data / "verisense.db").read_bytes() == b"officer decisions"
    assert (data / "storage/new.pdf").read_bytes() == b"upload"


def test_fingerprinted_cache_gzip_and_html_revalidation(tmp_path):
    (tmp_path / "index.html").write_text("<h1>VeriSense</h1>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    source = "console.log('static example');\n" * 200
    (tmp_path / "assets/bundle-Ab12Cd34.js").write_bytes(source.encode("utf-8"))
    (tmp_path / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    app = FastAPI()

    @app.get("/api/private-example")
    def private_example():
        return {"example": "not a static asset" * 200}

    mount_frontend(app, str(tmp_path))
    with TestClient(app) as client:
        asset = client.get("/assets/bundle-Ab12Cd34.js", headers={"Accept-Encoding": "gzip"})
        assert asset.status_code == 200 and asset.text == source
        assert asset.headers["Content-Encoding"] == "gzip"
        assert "Accept-Encoding" in asset.headers["Vary"]
        assert asset.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        unchanged = client.get("/assets/bundle-Ab12Cd34.js", headers={"If-None-Match": asset.headers["ETag"]})
        assert unchanged.status_code == 304
        assert "immutable" in unchanged.headers["Cache-Control"]
        for route in ("/", "/index.html", "/portal/alerts"):
            assert client.get(route).headers["Cache-Control"] == "no-cache"
        assert "immutable" not in client.get("/favicon.svg").headers["Cache-Control"]
        private = client.get("/api/private-example")
        assert "Content-Encoding" not in private.headers
        assert "immutable" not in private.headers.get("Cache-Control", "")
