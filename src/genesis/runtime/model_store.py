"""Local model-package install, active-version pointer, rollback and integrity checks."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from genesis.trainer.releases import verify_release


class ModelStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.versions = self.root / "versions"
        self.versions.mkdir(parents=True, exist_ok=True)
        self.active_file = self.root / "active.json"

    def active(self) -> dict[str, Any] | None:
        if not self.active_file.exists():
            return None
        pointer = json.loads(self.active_file.read_text(encoding="utf-8"))
        target = self.versions / pointer["version"]
        if not target.is_dir():
            raise ValueError("active version pointer refers to a missing package")
        return {"version": pointer["version"], "path": str(target), "manifest": json.loads((target / "manifest.json").read_text(encoding="utf-8"))}

    def install(self, package: str | Path, *, activate: bool = True) -> dict[str, Any]:
        verified = verify_release(package)
        version = verified["version"]
        target = self.versions / version
        if target.exists():
            raise ValueError("version already installed; refusing to overwrite immutable version")
        staging = Path(tempfile.mkdtemp(prefix=".install-", dir=self.root))
        try:
            with zipfile.ZipFile(package) as archive:
                for name in ("manifest.json", "knowledge.jsonl"):
                    with archive.open(name) as src, (staging / name).open("wb") as dst:
                        shutil.copyfileobj(src, dst)
            # Verify staged bytes before making the version visible.
            manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
            import hashlib
            if hashlib.sha256((staging / "knowledge.jsonl").read_bytes()).hexdigest() != manifest["files"]["knowledge.jsonl"]:
                raise ValueError("staged package integrity failure")
            os.replace(staging, target)
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
        if activate:
            self.activate(version)
        return {"installed": version, "activated": activate, "path": str(target)}

    def activate(self, version: str) -> dict[str, Any]:
        target = self.versions / version
        if not target.is_dir():
            raise ValueError(f"version not installed: {version}")
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        import hashlib
        if hashlib.sha256((target / "knowledge.jsonl").read_bytes()).hexdigest() != manifest["files"]["knowledge.jsonl"]:
            raise ValueError("installed package integrity check failed")
        temporary = self.active_file.with_suffix(".tmp")
        temporary.write_text(json.dumps({"version": version}, sort_keys=True) + "\\n", encoding="utf-8")
        os.replace(temporary, self.active_file)
        return {"active_version": version}

    def list_versions(self) -> list[dict[str, Any]]:
        result = []
        for path in sorted(self.versions.iterdir()):
            if path.is_dir() and (path / "manifest.json").exists():
                manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
                result.append({"version": manifest.get("version"), "record_count": manifest.get("record_count"), "path": str(path)})
        return result
