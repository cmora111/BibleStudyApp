
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import shutil
import urllib.request
from urllib.error import URLError, HTTPError


@dataclass(slots=True)
class DatasetItem:
    key: str
    label: str
    description: str
    category: str
    target_path: str
    source_url: str = ""
    optional: bool = True
    installed_if_exists: bool = True


class DatasetManager:
    def __init__(self, root_dir: str | Path | None = None):
        if root_dir is None:
            root_dir = Path.cwd()
        self.root_dir = Path(root_dir)
        self.output_dir = self.root_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.manifest_path = self.output_dir / "dataset_manager_manifest.json"
        self.catalog = self._build_catalog()
        self.manifest = self._load_manifest()

    def _build_catalog(self) -> list[DatasetItem]:
        return [
            DatasetItem(
                key="asv_csv",
                label="ASV Bible CSV",
                description="Primary ASV CSV used by the importer/reader.",
                category="Bibles",
                target_path="output/bibles/ASV.csv",
            ),
            DatasetItem(
                key="kjv_csv",
                label="KJV Bible CSV",
                description="Primary KJV CSV used by the importer/reader.",
                category="Bibles",
                target_path="output/bibles/KJV.csv",
            ),
            DatasetItem(
                key="web_csv",
                label="WEB Bible CSV",
                description="Primary WEB CSV used by the importer/reader.",
                category="Bibles",
                target_path="output/bibles/WEB.csv",
            ),
            DatasetItem(
                key="crossrefs_csv",
                label="Cross References CSV",
                description="Cross-reference dataset used by the cross reference engine.",
                category="Cross References",
                target_path="output/crossrefs/openbible_crossrefs.csv",
            ),
            DatasetItem(
                key="timeline_csv",
                label="Timeline Events CSV",
                description="Timeline dataset used by timeline/map explorer.",
                category="Timeline",
                target_path="data/timeline_events.csv",
            ),
            DatasetItem(
                key="geography_modern",
                label="Geography Modern CSV",
                description="Modern geography lookup table.",
                category="Geography",
                target_path="output/geography/modern.csv",
            ),
            DatasetItem(
                key="geography_ancient",
                label="Geography Ancient CSV",
                description="Ancient geography lookup table.",
                category="Geography",
                target_path="output/geography/ancient.csv",
            ),
            DatasetItem(
                key="strongs_demo",
                label="Strong's Demo Lexicon CSV",
                description="Demo Strong's lexicon/bootstrap dataset.",
                category="Lexicons",
                target_path="datasets/output/strongs_lexicon_demo.csv",
            ),
            DatasetItem(
                key="alignment_demo",
                label="Alignment Demo CSV",
                description="Demo alignment dataset used for testing.",
                category="Lexicons",
                target_path="datasets/output/alignment_demo.csv",
            ),
        ]

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            try:
                return json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except Exception:
                return {"datasets": {}}
        return {"datasets": {}}

    def save_manifest(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2), encoding="utf-8")

    def resolve_path(self, target_path: str) -> Path:
        return self.root_dir / target_path

    def get_item(self, key: str) -> DatasetItem:
        for item in self.catalog:
            if item.key == key:
                return item
        raise KeyError(f"Unknown dataset key: {key}")

    def installed_items(self) -> list[dict]:
        rows = []
        for item in self.catalog:
            path = self.resolve_path(item.target_path)
            exists = path.exists() if item.installed_if_exists else False
            size = path.stat().st_size if path.exists() else 0
            rows.append(
                {
                    "key": item.key,
                    "label": item.label,
                    "category": item.category,
                    "path": str(path),
                    "exists": exists,
                    "size_bytes": size,
                    "size_mb": round(size / 1024 / 1024, 2),
                    "description": item.description,
                }
            )
        return rows

    def free_disk_space(self, path: str | Path | None = None) -> dict:
        target = Path(path) if path else self.root_dir
        usage = shutil.disk_usage(target)
        return {
            "path": str(target),
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "total_gb": round(usage.total / 1024 / 1024 / 1024, 2),
            "free_gb": round(usage.free / 1024 / 1024 / 1024, 2),
        }

    def register_local_file(self, key: str, local_source: str | Path, copy_into_target: bool = True) -> dict:
        item = self.get_item(key)
        src = Path(local_source).expanduser().resolve()
        if not src.exists():
            raise FileNotFoundError(f"Local source not found: {src}")

        target = self.resolve_path(item.target_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        if copy_into_target:
            shutil.copy2(src, target)
        else:
            if src != target:
                raise ValueError("copy_into_target=False is only valid when source already matches target path")

        digest = self.sha256_file(target)
        self.manifest.setdefault("datasets", {})[key] = {
            "path": str(target),
            "source": str(src),
            "sha256": digest,
            "size_bytes": target.stat().st_size,
            "registered": True,
        }
        self.save_manifest()
        return self.manifest["datasets"][key]

    def sha256_file(self, path: str | Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def download_dataset(self, key: str, url: str | None = None, min_free_gb: float = 2.0) -> dict:
        item = self.get_item(key)
        source_url = url or item.source_url
        if not source_url:
            raise ValueError(f"No download URL configured for dataset '{key}'")

        disk = self.free_disk_space()
        if disk["free_gb"] < min_free_gb:
            raise RuntimeError(
                f"Not enough free disk space. Required at least {min_free_gb:.1f} GB, found {disk['free_gb']:.2f} GB."
            )

        target = self.resolve_path(item.target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_suffix(target.suffix + ".part")

        headers = {}
        existing = part.stat().st_size if part.exists() else 0
        if existing > 0:
            headers["Range"] = f"bytes={existing}-"

        req = urllib.request.Request(source_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                mode = "ab" if existing > 0 and getattr(resp, "status", 200) == 206 else "wb"
                if mode == "wb" and part.exists():
                    part.unlink()
                with open(part, mode) as f:
                    shutil.copyfileobj(resp, f, length=1024 * 1024)
        except HTTPError as exc:
            raise RuntimeError(f"Download failed with HTTP {exc.code}: {exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"Download failed: {exc.reason}") from exc

        part.replace(target)
        digest = self.sha256_file(target)
        self.manifest.setdefault("datasets", {})[key] = {
            "path": str(target),
            "source_url": source_url,
            "sha256": digest,
            "size_bytes": target.stat().st_size,
            "downloaded": True,
        }
        self.save_manifest()
        return self.manifest["datasets"][key]
