"""The exception registry (ADR_0009): every recorded decision that something which would count as a failure does not.

An exception stays where it lives: a survivor's verdict or decision, a code exemption, a comment in the product that
tells a tool to look away, a test that may skip, a pin the oracle rule spares, an import an architecture contract lets
through. The registry reads each one there and adds what every exception needs: what it excuses, who decided, why,
when, and until when it holds. A verdict a model gave holds while the question it answered is unchanged; every other
exception holds for ``REVIEW_DAYS`` from its decision and then fails until it is confirmed again or removed. Per type,
the number of exceptions may only fall (ESLint's bulk suppressions, betterer): a rise fails the gate until a reason
recorded in the baseline accepts it.

The comments and records are own code, labelled as such: no mature tool registers suppressions across ruff, the type
checkers, coverage.py, pytest and import-linter. Each reading follows the tool's own syntax.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import subprocess
import tokenize
import tomllib
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

REVIEW_DAYS = 90
# Each type: its name, what it excuses, and whether a model's verdict holds it (while its question is unchanged) or a
# decision with a date (for REVIEW_DAYS).
TYPES = {
    "judged": ("Judged out", "A surviving mutant a model judged equivalent or irrelevant and a model of another family confirmed."),
    "decided": ("Decided out", "A surviving mutant the owner or the owner's delegate decided is equivalent or irrelevant."),
    "not-required": ("Not required", "A silent requirement the owner or the delegate decided the product does not need."),
    "kept": ("Kept", "Code with no effect the owner or the delegate decided to keep."),
    "exemption": ("Code exemption", "A function the delegate decided needs no requirement (Code map)."),
    "comment": ("Tool comment", "A comment in the product that tells a tool to look away: # noqa, # type: ignore, # pragma: no cover and the like."),
    "skip": ("Test skip", "A place in the tests that skips a test or expects it to fail."),
    "pin": ("Pin outside the oracle rule", "An accepted pin that does what the pin oracle rule forbids new pins to do."),
    "import": ("Ignored import", "An import an architecture contract of import-linter lets through."),
}
STATES = {
    "valid": "Holds",
    "overdue": "Review overdue",
    "unreasoned": "No reason",
    "undated": "No decision date",
    "orphan": "Excuses nothing",
}
FAILING = {"overdue", "unreasoned", "undated", "orphan"}
# The comments each tool reads, by the marker that starts them; a reason may follow the codes after " - " or " -- ".
COMMENT_MARKERS = (
    ("noqa", re.compile(r"#\s*noqa\b(?::\s*(?P<codes>[A-Z]+[0-9]+(?:\s*,\s*[A-Z]+[0-9]+)*))?", re.IGNORECASE)),
    ("type: ignore", re.compile(r"#\s*type:\s*ignore\b(?:\[(?P<codes>[^\]]*)\])?")),
    ("pyright: ignore", re.compile(r"#\s*pyright:\s*ignore\b(?:\[(?P<codes>[^\]]*)\])?")),
    ("pyright", re.compile(r"#\s*pyright:\s*(?P<codes>(?!ignore\b)[A-Za-z]+\s*=\s*\w+(?:\s*,\s*[A-Za-z]+\s*=\s*\w+)*)")),
    ("ty: ignore", re.compile(r"#\s*ty:\s*ignore\b(?:\[(?P<codes>[^\]]*)\])?")),
    ("pragma: no cover", re.compile(r"#\s*pragma:\s*no\s+cover\b")),
    ("pragma: no branch", re.compile(r"#\s*pragma:\s*no\s+branch\b")),
    ("pragma: no mutate", re.compile(r"#\s*pragma:\s*no\s+mutate\b")),
    ("nosec", re.compile(r"#\s*nosec\b(?:\s+(?P<codes>B\d+(?:\s*,\s*B\d+)*))?")),
)
REASON = re.compile(r"^\s*(?:-{1,2}|—|:)\s*(?P<reason>\S.*)$")
SKIPS = {"skip", "skipif", "xfail", "importorskip"}


def blame_dates(root: Path, path: str, cache: dict[str, dict[int, str]]) -> dict[int, str]:
    """The day each line of a file was last written, from ``git blame``: an exception in the code is decided when its
    line was written. A line not committed yet is dated today, as git blame dates it; a file outside git has none."""
    if path not in cache:
        out = subprocess.run(["git", "blame", "--line-porcelain", "--", path], cwd=root, text=True, capture_output=True, check=False).stdout
        dates: dict[int, str] = {}
        line = 0
        for row in out.splitlines():
            head = re.match(r"^[0-9a-f]{40} \d+ (\d+)", row)
            if head:
                line = int(head.group(1))
            elif row.startswith("author-time "):
                dates[line] = datetime.fromtimestamp(int(row.split()[1]), UTC).date().isoformat()
        cache[path] = dates
    return cache[path]


def dated(root: Path, found: list[dict]) -> list[dict]:
    """The exceptions with the day their line was written, where git knows it."""
    cache: dict[str, dict[int, str]] = {}
    return [{**item, "decided": blame_dates(root, item["path"], cache).get(int(item.get("line") or 0), "")} for item in found]


def digest(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()[:12]


def _comments(source: str) -> list[tuple[int, str, str]]:
    """Every comment of a module: its line, the code before it on that line, and the comment."""
    lines = source.splitlines()
    found = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                line = token.start[0]
                found.append((line, lines[line - 1][: token.start[1]], token.string))
    except (tokenize.TokenError, SyntaxError):
        return []
    return found


def tool_comments(root: Path, package: str) -> list[dict]:
    """The comments in the product that tell a tool to look away, one exception per marker: the tool's codes, the code
    on its line (a record keys on it, so an edit of the line asks for the record again) and the reason written after
    the codes, if any."""
    found = []
    for path in sorted((root / "src" / package).rglob("*.py")):
        relative = str(path.relative_to(root))
        for line, code, comment in _comments(path.read_text()):
            for marker, pattern in COMMENT_MARKERS:
                for match in pattern.finditer(comment):
                    codes = " ".join(str(match.groupdict().get("codes") or "").replace(",", " ").split())
                    rest = comment[match.end():]
                    stated = REASON.match(rest)
                    found.append({
                        "type": "comment", "key": f"comment|{relative}|{marker}|{codes}|{digest(code)}",
                        "path": relative, "line": line, "marker": marker, "codes": codes,
                        # What it excuses is the code on its line; a comment alone on its line speaks for the module.
                        "excuses": " ".join(code.split())[:160] or "the whole module",
                        "reason": stated.group("reason").strip() if stated else "",
                    })
    return dated(root, found)


def _skip_name(node: ast.AST) -> str | None:
    """The pytest skip a node names: pytest.skip(...), pytest.mark.skipif(...), pytest.importorskip(...)."""
    target = node.func if isinstance(node, ast.Call) else node
    dotted = ast.unparse(target) if isinstance(target, (ast.Attribute, ast.Name)) else ""
    parts = dotted.split(".")
    if parts[0] == "pytest" and parts[-1] in SKIPS:
        return parts[-1]
    return None


def test_skips(root: Path) -> list[dict]:
    """Every place in the tests that skips a test or expects it to fail: pytest.skip and pytest.importorskip calls,
    and skip, skipif and xfail marks. The reason a call or mark gives as a string literal is its reason."""
    found = []
    for path in sorted((root / "tests").rglob("*.py")):
        relative = str(path.relative_to(root))
        source = path.read_text()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        lines = source.splitlines()
        seen: set[int] = set()
        for node in ast.walk(tree):
            name = _skip_name(node)
            if not name or not isinstance(node, (ast.Call, ast.Attribute)) or node.lineno in seen:
                continue
            seen.add(node.lineno)
            reason = ""
            if isinstance(node, ast.Call):
                literal = next((value.value for value in [*node.args, *(keyword.value for keyword in node.keywords if keyword.arg in {"reason", "msg"})]
                                if isinstance(value, ast.Constant) and isinstance(value.value, str)), "")
                reason = str(literal)
            found.append({
                "type": "skip", "key": f"skip|{relative}|{name}|{digest(lines[node.lineno - 1])}",
                "path": relative, "line": node.lineno, "marker": f"pytest {name}", "codes": "",
                "excuses": " ".join(lines[node.lineno - 1].split())[:160], "reason": reason,
            })
    return dated(root, found)


def ignored_imports(root: Path) -> list[dict]:
    """The imports each import-linter contract of pyproject.toml lets through (ignore_imports)."""
    config = tomllib.loads((root / "pyproject.toml").read_text()) if (root / "pyproject.toml").is_file() else {}
    contracts = ((config.get("tool") or {}).get("importlinter") or {}).get("contracts") or []
    text = (root / "pyproject.toml").read_text() if (root / "pyproject.toml").is_file() else ""
    found = []
    for contract in contracts:
        for expression in contract.get("ignore_imports") or []:
            line = next((index for index, row in enumerate(text.splitlines(), 1) if expression in row), 0)
            found.append({
                "type": "import", "key": f"import|{contract.get('id') or contract.get('name')}|{expression}",
                "path": "pyproject.toml", "line": line, "marker": "ignore_imports", "codes": str(contract.get("id") or ""),
                "excuses": f"{expression} in “{contract.get('name')}”", "reason": "",
            })
    return dated(root, found)


def spared_pins(root: Path, pins: str, problems: Callable[..., list[str]]) -> list[dict]:
    """The accepted pins the pin oracle rule would refuse as new drafts: the rule applies to new pins only (history 057),
    so each one it spares is an exception. A Requirement's pin (test_pin_req_*) is held to the public API rule too."""
    found = []
    for path in sorted((root / pins).glob("test_pin_*.py")):
        public = path.name.startswith("test_pin_req_")
        said = problems(path.read_text(), root, public_only=public)
        if said:
            relative = str(path.relative_to(root))
            found.append({
                "type": "pin", "key": f"pin|{relative}", "path": relative, "line": 1, "marker": "pin oracle rule", "codes": "",
                "excuses": "; ".join(said), "reason": "",
            })
    return dated(root, found)


def run_date(started_at: str) -> date:
    """The day a retained run started: exceptions are judged as of their run, so drawing a run again judges alike."""
    return date.fromisoformat(str(started_at)[:10])


def call_date(call_id: str) -> str:
    """The day a stored model call was made, from its id (20261002T201412Z-0a25a6)."""
    match = re.match(r"(\d{4})(\d{2})(\d{2})T", str(call_id or ""))
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else ""


def review(exception: dict, records: dict, today: date) -> dict:
    """An exception with its reason, decision date, the date it holds until, and its state as of ``today``.

    A model's verdict (``holds == "question"``) holds while its question is unchanged; everything else holds for
    REVIEW_DAYS from its decision. The reason comes from the exception itself, else from its record; the day from its
    record, which confirms it again, else from the exception (its decision, or the day its line was written)."""
    record = records.get(exception["key"]) or {}
    reason = str(exception.get("reason") or record.get("reason") or "").strip()
    decided = str(record.get("decided") or exception.get("decided") or "")[:10]
    by = str(exception.get("by") or record.get("by") or "")
    out = {**exception, "reason": reason, "decided": decided, "by": by, "review_by": ""}
    if not reason:
        return {**out, "state": "unreasoned"}
    if exception.get("holds") == "question":
        return {**out, "state": "valid"}
    if not decided:
        return {**out, "state": "undated"}
    review_by = date.fromisoformat(decided) + timedelta(days=REVIEW_DAYS)
    return {**out, "review_by": review_by.isoformat(), "state": "overdue" if today > review_by else "valid"}


def orphans(records: dict, exceptions: list[dict]) -> list[dict]:
    """The records that excuse nothing any more (the line changed or the comment went): each fails until removed."""
    keys = {exception["key"] for exception in exceptions}
    return [
        {"type": key.split("|", 1)[0] if key.split("|", 1)[0] in TYPES else "comment", "key": key, "path": key.split("|")[1] if "|" in key else "",
         "line": 0, "marker": "record", "codes": "", "excuses": "nothing: no exception has this key any more",
         "reason": str(record.get("reason") or ""), "decided": str(record.get("decided") or ""), "by": str(record.get("by") or ""),
         "review_by": "", "state": "orphan"}
        for key, record in sorted(records.items()) if key not in keys and not key.startswith("_")
    ]


def counts(exceptions: list[dict]) -> dict:
    """Per type, how many exceptions there are and how many fail (no reason, no date, overdue, excusing nothing)."""
    return {
        kind: {"all": sum(item["type"] == kind for item in exceptions), "failing": sum(item["type"] == kind and item["state"] in FAILING for item in exceptions)}
        for kind in TYPES
    }


def ratchet(numbers: dict[str, int], baseline: dict) -> tuple[dict, dict]:
    """The exceptions per type held to a baseline that falls with them: a rise is reported as [held, now] until the
    baseline records a reason, which accepts it into the accepted history, as the Code map's ratchet does."""
    held = dict(baseline.get("numbers") or {})
    reasons = dict(baseline.get("reasons") or {})
    accepted = list(baseline.get("accepted") or [])
    out, rises = {}, {}
    for key, value in numbers.items():
        if key in held and value > held[key]:
            reason = str(reasons.pop(key, "") or "").strip()
            if reason:
                accepted.append({"number": key, "from": held[key], "to": value, "reason": reason})
                out[key] = value
            else:
                rises[key] = [held[key], value]
                out[key] = held[key]
        else:
            out[key] = min(held.get(key, value), value)
    return {**baseline, "schema": "ternforge-exceptions-baseline-1", "numbers": out, "reasons": reasons, "accepted": accepted}, rises


def load(path: Path) -> dict:
    return json.loads(path.read_text()) if path.is_file() else {}
