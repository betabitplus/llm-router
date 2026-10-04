"""Metric bases (ADR_0009): what the monitor's numbers are measured against, and every change of it made together with
the product's code or tests.

A number gets better because the product did, or because what it is measured against was loosened: a held number
raised, an exception added, a required path, criterion or fault class dropped from a verification profile, a rule or
file excluded in a tool's settings. Each commit since the merge base with main, and the uncommitted change, is read
for the bases it changes, each with the direction of the change: looser, tighter, or changed when the reading cannot
tell. A base changed in the same commit as ``src`` or ``tests`` is marked; the mark fails nothing, it asks a reviewer
to look (Goodhart's law: a measure that becomes a target can be met by moving the measure).

Own code, labelled as such: no mature tool reads these bases. The git calls are plain ``git log``, ``git show`` and
``git diff``; each base is compared by parsing both sides with the standard library.
"""

from __future__ import annotations

import fnmatch
import json
import re
import subprocess
import tomllib
from pathlib import Path

# Each base: the paths it lives in, its name, and how its two sides are compared.
BASES = (
    (".ai-bridge/code-map-baseline.json", "Code map baseline", "ratchet"),
    (".ai-bridge/exceptions-baseline.json", "Exceptions baseline", "ratchet"),
    (".ai-bridge/code-exemptions.json", "Code exemptions", "records"),
    (".ai-bridge/exception-records.json", "Exception records", "records"),
    (".ai-bridge/survivor-verdicts/*/decisions.json", "Survivor decisions", "decisions"),
    (".ai-bridge/survivor-verdicts/*/verdicts.json", "Survivor verdicts", "verdicts"),
    ("docs/verification-profiles/*.md", "Verification profile", "profile"),
    ("pyproject.toml", "Tool settings", "settings"),
    (".github/workflows/*.yml", "CI workflow", "workflow"),
)
CODE = ("src/", "tests/")
SUPPRESSING = {"equivalent", "irrelevant"}
CLOSING = {"not-required", "kept"}
# The tool tables of pyproject.toml that decide what a check counts.
TOOLS = ("ruff", "coverage", "pytest", "pyright", "ty", "importlinter", "interrogate", "bandit", "deptry", "ternforge")


def base_of(path: str) -> tuple[str, str] | None:
    for pattern, label, kind in BASES:
        if fnmatch.fnmatch(path, pattern):
            return label, kind
    return None


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False).stdout


def _json(text: str) -> dict:
    try:
        value = json.loads(text) if text.strip() else {}
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _ratchet(before: str, after: str) -> tuple[str, str] | None:
    old, new = _json(before).get("numbers") or {}, _json(after).get("numbers") or {}
    rose = sorted(key for key in new if key in old and new[key] > old[key])
    fell = sorted(key for key in new if key in old and new[key] < old[key])
    held = sorted(key for key in new if key not in old)
    dropped = sorted(key for key in old if key not in new)
    added = len(_json(after).get("accepted") or []) - len(_json(before).get("accepted") or [])
    if rose or dropped or added > 0:
        parts = [f"{key} {old[key]}→{new[key]}" for key in rose] + [f"{key} no longer held" for key in dropped]
        return "looser", "held numbers rose: " + ", ".join(parts) if parts else f"{added} rises accepted"
    if fell or held:
        return "tighter", ", ".join([f"{key} {old[key]}→{new[key]}" for key in fell] + [f"{key} now held at {new[key]}" for key in held])
    return None


def _records(before: str, after: str) -> tuple[str, str] | None:
    old, new = _json(before), _json(after)
    added, removed = sorted(set(new) - set(old)), sorted(set(old) - set(new))
    renewed = [key for key in set(old) & set(new) if str((new[key] or {}).get("decided") or "") > str((old[key] or {}).get("decided") or "")]
    if added or renewed:
        return "looser", ", ".join(part for part in (f"{len(added)} added" if added else "", f"{len(renewed)} renewed" if renewed else "", f"{len(removed)} removed" if removed else "") if part)
    if removed:
        return "tighter", f"{len(removed)} removed"
    return ("changed", "reasons") if old != new else None


def _decisions(before: str, after: str) -> tuple[str, str]:
    def excusing(text: str) -> int:
        return sum(
            1 for row in _json(text).values() if isinstance(row, dict)
            and (row.get("verdict") in SUPPRESSING or row.get("disposition") in CLOSING)
        )
    old, new = excusing(before), excusing(after)
    if new > old:
        return "looser", f"decisions that excuse a survivor {old}→{new}"
    if new < old:
        return "tighter", f"decisions that excuse a survivor {old}→{new}"
    return None


def _verdicts(before: str, after: str) -> tuple[str, str]:
    def suppressing(text: str) -> int:
        return sum(1 for row in _json(text).values() if isinstance(row, dict) and ((row.get("answer") or {}).get("verdict") in SUPPRESSING))
    old, new = suppressing(before), suppressing(after)
    if new > old:
        return "looser", f"answers that judge a survivor out {old}→{new}"
    if new < old:
        return "tighter", f"answers that judge a survivor out {old}→{new}"
    return None


def profile_requirements(text: str) -> dict[str, dict]:
    """What each verification profile of a file asks for, by contract: its criteria with the paths each requires, and
    the fault classes it requires, read from the profile's own tables (Verification criteria, Fault applicability)."""
    profiles: dict[str, dict] = {}
    contract, section = "", ""
    header: list[str] = []
    for line in text.splitlines():
        heading = re.match(r"^##\s+Profile\s*·\s*(\S+)", line)
        if heading:
            contract = heading.group(1)
            profiles[contract] = {"criteria": {}, "required": set()}
            continue
        if line.startswith("### "):
            section, header = line[4:].strip().lower(), []
            continue
        if not line.startswith("|"):
            header = [] if not line.strip() else header
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not header:
            header = [cell.lower() for cell in cells]
            continue
        if set("".join(cells)) <= set("-: ") or not contract:
            continue
        if section == "verification criteria" and "required paths" in header and "criterion" in header:
            value = cells[header.index("required paths")]
            profiles[contract]["criteria"][cells[header.index("criterion")].strip("`")] = int(value) if value.isdigit() else 0
        elif section == "fault applicability" and "required" in header:
            profiles[contract]["required"].update(re.findall(r"`([^`]+)`", cells[header.index("required")]))
    return profiles


def _merged(texts: list[str]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for text in texts:
        merged.update(profile_requirements(text))
    return merged


def profile_change(old_texts: list[str], new_texts: list[str]) -> tuple[str, str] | None:
    """How the verification profiles one commit changes moved, read together, since a criterion may move between files:
    looser when a criterion goes or asks for fewer paths, a contract stops requiring a fault class, or a contract is no
    longer profiled; tighter when they only add. A criterion that only moves to another contract, or a fault class a
    contract profiled in the same change takes over, is neither."""
    old, new = _merged(old_texts), _merged(new_texts)
    where_old = {name: (contract, paths) for contract, row in old.items() for name, paths in row["criteria"].items()}
    where_new = {name: (contract, paths) for contract, row in new.items() for name, paths in row["criteria"].items()}
    less, more, moved = [], [], []
    for name, (contract, paths) in sorted(where_old.items()):
        if name not in where_new:
            less.append(f"{contract} drops {name}")
            continue
        now_contract, now_paths = where_new[name]
        if now_contract != contract:
            moved.append(f"{name} moves from {contract} to {now_contract}")
        if now_paths < paths:
            less.append(f"{name} paths {paths}→{now_paths}")
        elif now_paths > paths:
            more.append(f"{name} paths {paths}→{now_paths}")
    more.extend(f"{where_new[name][0]} adds {name}" for name in sorted(set(where_new) - set(where_old)))
    # A class a contract stops requiring that a contract profiled in the same change now requires has moved there,
    # as when a requirement's derived technical requirements are profiled.
    fresh = sorted(set(new) - set(old))
    handed = {
        (taker, name): contract
        for contract in sorted(set(old) & set(new)) for name in sorted(old[contract]["required"] - new[contract]["required"])
        for taker in fresh if name in new[taker]["required"]
    }
    for contract in sorted(set(old) | set(new)):
        if contract not in new:
            if any(name not in where_new for name in old[contract]["criteria"]) or not old[contract]["criteria"]:
                less.append(f"{contract} no longer profiled")
            continue
        if contract not in old:
            # A contract profiled now asks for more only by what it brings: a new criterion (counted above) or a fault
            # class no other contract handed it.
            more.extend(f"{contract} requires {name}" for name in sorted(new[contract]["required"]) if (contract, name) not in handed)
            continue
        for name in sorted(old[contract]["required"] - new[contract]["required"]):
            takers = sorted(taker for (taker, handed_name), giver in handed.items() if handed_name == name and giver == contract)
            if takers:
                moved.append(f"{contract} hands {name} to {', '.join(takers[:2])}")
            else:
                less.append(f"{contract} no longer requires {name}")
        more.extend(f"{contract} requires {name}" for name in sorted(new[contract]["required"] - old[contract]["required"]))
    shown = lambda parts: "; ".join(parts[:6]) + (f"; and {len(parts) - 6} more" if len(parts) > 6 else "")
    if less:
        return "looser", shown(less)
    if more:
        return "tighter", shown(more)
    if moved:
        return "changed", shown(moved)
    return None


def tool_settings(text: str) -> dict:
    try:
        return {key: value for key, value in (tomllib.loads(text).get("tool") or {}).items() if key in TOOLS}
    except tomllib.TOMLDecodeError:
        return {}


def _measure(settings: dict) -> dict[str, float]:
    """The size of what a tool table excludes, ignores or lets through, and its thresholds."""
    ruff = settings.get("ruff") or {}
    lint = ruff.get("lint") or {}
    coverage = settings.get("coverage") or {}
    options = ((settings.get("pytest") or {}).get("ini_options")) or {}
    count = lambda value: len(value) if isinstance(value, (list, dict)) else 0
    return {
        "ruff ignores": count(lint.get("ignore")) + sum(count(value) for value in (lint.get("per-file-ignores") or {}).values()),
        "excluded paths": count(ruff.get("extend-exclude")) + count((settings.get("pyright") or {}).get("exclude"))
        + count(((settings.get("ty") or {}).get("src") or {}).get("exclude")) + count((settings.get("interrogate") or {}).get("exclude"))
        + count((coverage.get("run") or {}).get("omit")),
        "coverage exclusions": count((coverage.get("report") or {}).get("exclude_lines")) + count((coverage.get("report") or {}).get("exclude_also")),
        "warnings ignored": count(options.get("filterwarnings")),
        "type checks off": sum(1 for key, value in (settings.get("pyright") or {}).items() if key.startswith("report") and value is False)
        + sum(1 for value in ((settings.get("ty") or {}).get("rules") or {}).values() if value == "ignore"),
        "ignored imports": sum(count(contract.get("ignore_imports")) for contract in (settings.get("importlinter") or {}).get("contracts") or []),
        "architecture contracts": -count((settings.get("importlinter") or {}).get("contracts")),
        "coverage floor": -float((coverage.get("report") or {}).get("fail_under") or 0),
        "docstring floor": -float((settings.get("interrogate") or {}).get("fail-under") or 0),
    }


def _settings(before: str, after: str) -> tuple[str, str] | None:
    old_settings, new_settings = tool_settings(before), tool_settings(after)
    if old_settings == new_settings:
        return None
    old, new = _measure(old_settings), _measure(new_settings)
    looser = [key for key in old if new[key] > old[key]]
    tighter = [key for key in old if new[key] < old[key]]
    shown = lambda key: f"{key} {abs(old[key]):g}→{abs(new[key]):g}"
    changed = sorted(key for key in set(old_settings) | set(new_settings) if old_settings.get(key) != new_settings.get(key))
    if looser:
        return "looser", ", ".join(shown(key) for key in looser)
    if tighter:
        return "tighter", ", ".join(shown(key) for key in tighter)
    return "changed", "settings of " + ", ".join(changed)


def compare(kind: str, before: str, after: str) -> tuple[str, str] | None:
    """How one base changed between its two sides, or None when nothing that counts changed."""
    if before == after:
        return None
    if kind == "settings":
        return _settings(before, after)
    if kind == "workflow":
        return "changed", "the steps CI runs"
    if kind == "profile":
        return profile_change([before], [after])
    return {"ratchet": _ratchet, "records": _records, "decisions": _decisions, "verdicts": _verdicts}[kind](before, after)


def _bases(paths: list[str], before, after) -> list[dict]:
    """The base changes among ``paths``, given how to read a path's two sides. The verification profiles are read
    together, as one base of the change, since a criterion may move between their files."""
    bases, profiles = [], []
    for path in paths:
        found = base_of(path)
        if not found:
            continue
        if found[1] == "profile":
            profiles.append(path)
            continue
        change = compare(found[1], before(path), after(path))
        if change:
            bases.append({"path": path, "label": found[0], "kind": found[1], "direction": change[0], "detail": change[1]})
    if profiles:
        change = profile_change([before(path) for path in profiles], [after(path) for path in profiles])
        if change:
            bases.append({"path": ", ".join(profiles), "label": "Verification profiles", "kind": "profile", "direction": change[0], "detail": change[1]})
    return bases


def commit_changes(root: Path, commit: str) -> dict:
    """One commit's base changes and code paths."""
    paths = [line for line in git(root, "show", "--no-renames", "--format=", "--name-only", commit).splitlines() if line]
    head = git(root, "show", "-s", "--format=%H%x00%h%x00%cI%x00%s", commit).rstrip("\n").split("\x00")
    bases = _bases(paths, lambda path: git(root, "show", f"{commit}^:{path}"), lambda path: git(root, "show", f"{commit}:{path}"))
    return {
        "commit": head[0], "short": head[1], "date": head[2][:10], "subject": head[3], "bases": bases,
        "code": sorted(path for path in paths if path.startswith(CODE)),
    }


def working_changes(root: Path) -> dict:
    """The uncommitted change against HEAD, read the same way."""
    status = [line for line in git(root, "status", "--porcelain", "--untracked-files=all").splitlines() if len(line) > 3]
    paths = sorted({line[3:].split(" -> ")[-1] for line in status})
    bases = _bases(paths, lambda path: git(root, "show", f"HEAD:{path}"), lambda path: (root / path).read_text() if (root / path).is_file() else "")
    return {"commit": "", "short": "working tree", "date": "", "subject": "Uncommitted changes", "bases": bases, "code": [path for path in paths if path.startswith(CODE)]}


def overall(bases: list[dict]) -> str:
    directions = {base["direction"] for base in bases}
    return "looser" if "looser" in directions else "tighter" if directions == {"tighter"} else "changed"


def base_changes(root: Path, base_ref: str = "main", cache: dict | None = None) -> dict:
    """Every change of a metric base since the merge base with ``base_ref``, newest first, and the uncommitted one.
    A commit's reading never changes, so ``cache`` (by commit) keeps it between builds."""
    merge_base = ""
    for ref in (base_ref, f"origin/{base_ref}"):
        merge_base = git(root, "merge-base", "HEAD", ref).strip()
        if merge_base:
            break
    commits = git(root, "rev-list", f"{merge_base}..HEAD").split() if merge_base else []
    cache = cache if cache is not None else {}
    rows = []
    for commit in commits:
        if commit not in cache:
            cache[commit] = commit_changes(root, commit)
        rows.append(cache[commit])
    rows.insert(0, working_changes(root))
    changes = [{**row, "with_code": bool(row["code"]), "direction": overall(row["bases"])} for row in rows if row["bases"]]
    return {"base": base_ref, "merge_base": merge_base, "commits": len(commits), "changes": changes}
