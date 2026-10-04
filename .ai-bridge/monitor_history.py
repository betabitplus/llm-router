"""The monitor's history and release snapshots (ADR_0009).

Every retained run adds one row to a committed JSON Lines file: the run, the commit its inputs came from, whether its
inputs were exactly that commit's files, and the numbers each page shows. A run drawn again replaces its own row, and
git merges the file as a union (``.gitattributes``), so the rows two clones add both keep; reading it, the later
drawing of a run wins. A release snapshot freezes one run's numbers, failing items and exceptions under the name
``git describe`` gives its commit, and is never rewritten.

Own code, labelled as such: SonarQube keeps the same history in its server (its activity graph and its versions); a
static portal reads a file instead.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

SCHEMA = "ternforge-monitor-history-1"
SNAPSHOT_SCHEMA = "ternforge-release-snapshot-1"


def load(path: Path) -> list[dict]:
    """The rows in run order, one per run: a union merge may keep two drawings of a run, and the later one wins."""
    by_run: dict[str, dict] = {}
    if path.is_file():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and row.get("run_id"):
                earlier = by_run.get(row["run_id"])
                if earlier is None or str(row.get("drawn_at") or "") >= str(earlier.get("drawn_at") or ""):
                    by_run[row["run_id"]] = row
    return sorted(by_run.values(), key=lambda row: (str(row.get("started_at") or ""), str(row["run_id"])))


def write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for row in rows))


def record(path: Path, row: dict) -> list[dict]:
    """The history with ``row`` in it: in place of an earlier drawing of its run, else added in run order. The file is
    written only when the history changes."""
    rows = load(path)
    kept = [earlier for earlier in rows if earlier["run_id"] != row["run_id"]]
    earlier = next((item for item in rows if item["run_id"] == row["run_id"]), None)
    if earlier is not None and {**earlier, "schema": SCHEMA, "drawn_at": ""} == {**row, "schema": SCHEMA, "drawn_at": ""}:
        return rows
    rows = sorted([*kept, {"schema": SCHEMA, **row}], key=lambda item: (str(item.get("started_at") or ""), str(item["run_id"])))
    write(path, rows)
    return rows


def tree_state(root: Path, inputs: dict[str, str], head: str) -> str | None:
    """"clean" when every input the run recorded is byte for byte the file of the commit it ran at, "dirty" when one
    differs or is missing there, None when the run recorded no inputs or no commit. One ``git cat-file --batch`` reads
    the commit's files."""
    if not inputs or not head or not re.fullmatch(r"[0-9a-f]{40}", head):
        return None
    paths = sorted(inputs)
    out = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=root, input="".join(f"{head}:{path}\n" for path in paths).encode(),
        capture_output=True, check=False,
    ).stdout
    at = 0
    for path in paths:
        end = out.find(b"\n", at)
        if end < 0:
            return None
        header = out[at:end].decode(errors="replace")
        at = end + 1
        if header.endswith(" missing"):
            return "dirty"
        size = int(header.split()[2])
        if hashlib.sha256(out[at:at + size]).hexdigest() != inputs[path]:
            return "dirty"
        at += size + 1
    return "clean"


def series(rows: list[dict], page: str, key: str, last: int = 30) -> list[dict]:
    """One number over the last runs, oldest first: for each run that has it, the run, when it started, the number and
    what it is of, the commit, whether the run's inputs were that commit's files, whether the run was seeded into the
    history before it began, and whether its drawing was qualified."""
    out = []
    for row in rows:
        number = ((row.get("numbers") or {}).get(page) or {}).get(key)
        value, of = (number[0], number[1] if len(number) > 1 else None) if isinstance(number, list) and number else (number, None)
        if value is not None:
            out.append({
                "run": row["run_id"], "at": row.get("started_at"), "value": value, "of": of, "commit": row.get("commit") or "",
                "tree": row.get("tree") or "", "seeded": bool(row.get("seeded")), "qualified": row.get("qualified"),
            })
    return out[-last:]


def describe(root: Path, head: str) -> tuple[str, bool]:
    """The name ``git describe`` gives a commit (v0.24.3, or v0.24.3-76-g12a7d77 past it), and whether that is a
    release tag itself."""
    exact = subprocess.run(["git", "describe", "--tags", "--exact-match", "--match", "v*", head], cwd=root, text=True, capture_output=True, check=False).stdout.strip()
    if exact:
        return exact, True
    name = subprocess.run(["git", "describe", "--tags", "--match", "v*", head], cwd=root, text=True, capture_output=True, check=False).stdout.strip()
    return name or head[:7], False


def snapshot_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "-", name)


def write_snapshot(directory: Path, snapshot: dict) -> Path | None:
    """Freeze a snapshot: never over an existing one of the same name."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{snapshot_name(snapshot['name'])}.json"
    if path.exists():
        return None
    path.write_text(json.dumps({"schema": SNAPSHOT_SCHEMA, **snapshot}, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    return path


def snapshots(directory: Path) -> list[dict]:
    """Every frozen snapshot, newest run first."""
    found = []
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        try:
            found.append({**json.loads(path.read_text()), "file": path.name})
        except ValueError:
            continue
    return sorted(found, key=lambda item: str(item.get("started_at") or ""), reverse=True)
