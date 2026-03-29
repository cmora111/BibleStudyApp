from __future__ import annotations

import os
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SetupReport:
    ok: bool
    messages: list[str]


def real_db_path() -> Path:
    return Path.home() / "UltimateBibleApp" / "data" / "bible.db"


def verify_core_verses() -> list[str]:
    db_path = real_db_path()
    messages: list[str] = []
    if not db_path.exists():
        return [f"FAIL: database not found at {db_path}"]

    conn = sqlite3.connect(db_path)
    tests = [
        ("esv", "galatians", 3, 22),
        ("esv", "romans", 8, 28),
        ("kjv", "romans", 8, 28),
        ("asv", "romans", 8, 28),
    ]
    for tr, book, ch, vs in tests:
        row = conn.execute(
            "SELECT text FROM verses WHERE translation=? AND book=? AND chapter=? AND verse=?",
            (tr, book, ch, vs),
        ).fetchone()
        if row:
            messages.append(f"PASS: {tr.upper()} {book.title()} {ch}:{vs}")
        else:
            messages.append(f"WARN: missing {tr.upper()} {book.title()} {ch}:{vs}")
    conn.close()
    return messages


def _run_python_script(project_dir: Path, script_path: Path, extra_args: list[str] | None = None) -> SetupReport:
    if not script_path.exists():
        return SetupReport(False, [f"Missing script: {script_path}"])

    proc = subprocess.run(
        ["python", str(script_path), *(extra_args or [])],
        cwd=str(project_dir),
        env={**os.environ, "PYTHONPATH": "."},
        capture_output=True,
        text=True,
    )

    messages: list[str] = []
    if proc.stdout.strip():
        messages.append(proc.stdout.strip())
    if proc.stderr.strip():
        messages.append(proc.stderr.strip())

    return SetupReport(proc.returncode == 0, messages or [f"Finished: {script_path.name}"])


def load_demo_scholar_tokens(project_dir: str | Path) -> SetupReport:
    project = Path(project_dir).expanduser().resolve()
    script = project / "scripts" / "load_demo_scholar_tokens.py"
    return _run_python_script(project, script)


def build_starter_bundle(project_dir: str | Path) -> SetupReport:
    project = Path(project_dir).expanduser().resolve()
    script = project / "scripts" / "build_strongs_dataset_bundle.py"
    out_dir = project / "datasets" / "output"
    return _run_python_script(project, script, ["--out", str(out_dir)])


def run_full_setup(project_dir: str | Path) -> SetupReport:
    messages: list[str] = []

    demo = load_demo_scholar_tokens(project_dir)
    messages.extend(demo.messages)

    starter = build_starter_bundle(project_dir)
    messages.extend(starter.messages)

    messages.extend(verify_core_verses())

    return SetupReport(demo.ok and starter.ok, messages)
