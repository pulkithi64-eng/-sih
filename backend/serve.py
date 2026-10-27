"""Container entrypoint: initialise demo state once, then serve on the host's PORT."""
import os
import secrets
import shutil
from pathlib import Path


def restore_demo(snapshot: Path, data: Path):
    """Copy a build-time demo snapshot only onto a new data volume."""
    database = data / "verisense.db"
    if database.exists():
        return
    if not (snapshot / "verisense.db").is_file():
        raise RuntimeError("Build-time demo snapshot is missing")
    data.mkdir(parents=True, exist_ok=True)
    shutil.copytree(snapshot / "storage", data / "storage", dirs_exist_ok=True)
    # Publish the DB last so an interrupted initial copy can safely be retried.
    temporary = data / "verisense.db.initialising"
    shutil.copy2(snapshot / "verisense.db", temporary)
    temporary.replace(database)


def main():
    data = Path(os.environ.get("VERISENSE_DATA_DIR", "/data"))
    data.mkdir(parents=True, exist_ok=True)
    if os.environ.get("VERISENSE_DEMO_MODE", "true").lower() in ("1", "true", "yes"):
        restore_demo(Path(os.environ.get("VERISENSE_DEMO_SNAPSHOT", "/opt/verisense-demo")), data)
    # Persist the signing secret outside source control; a provider-supplied
    # VERISENSE_SECRET takes precedence. Restarts do not invalidate sessions.
    if not os.environ.get("VERISENSE_SECRET"):
        secret_file = data / ".jwt-secret"
        if not secret_file.exists():
            with secret_file.open("x", encoding="utf-8") as stream:
                stream.write(secrets.token_urlsafe(48))
            secret_file.chmod(0o600)
        os.environ["VERISENSE_SECRET"] = secret_file.read_text(encoding="utf-8").strip()
    os.environ.setdefault("VERISENSE_DB", str(data / "verisense.db"))
    os.environ.setdefault("VERISENSE_STORAGE", str(data / "storage"))
    os.environ.setdefault("VERISENSE_SOURCES_STATE", str(data / "sources_state.json"))
    import cv2
    cv2.setNumThreads(1)
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "7860")), workers=1)


if __name__ == "__main__":
    main()
