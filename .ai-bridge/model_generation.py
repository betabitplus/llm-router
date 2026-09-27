"""Model generation: one adapter over headless subscription CLIs, a consumption ledger and a
budget guard (ADR_0004).

A call runs in an empty temporary directory without tools, plugins, MCP servers or memory,
with a replaced system prompt and a JSON schema; the answer is validated again against the
same schema on receipt. The adapter writes nothing a model did not return: an accepted
answer is stored as a response file with the prompt it answered, and whatever is taken
from it names the call. Every call, accepted or not, appends one row to the ledger: its
tokens, its list-price equivalent where the backend reports one, its duration and the plan
windows the backend reported. Before each call the guard compares the last known windows
and the run's call count with the Test Plan's limits, and for a quota pool that reports no
window, the calls the ledger shows it took in the last seven days; above a limit the call is
not made and is recorded as deferred. Deferred, rejected, invalid and unavailable calls return no
answer, so nothing downstream can mistake them for a pass.

Backends:

``claude-cli``       ``claude -p`` under the signed-in Claude subscription (``CLAUDE_CODE_OAUTH_TOKEN``
                     in CI). Its stream reports tokens, the list-price equivalent and the 5-hour and
                     weekly window utilization. API-key variables are removed from its environment,
                     so a call never bills an API account instead of the subscription.
``antigravity-cli``  ``agy -p`` where a person signed in to Antigravity. It reports tokens only;
                     it has no system-prompt flag, so the system text leads the prompt. Its
                     smaller quota, every model outside the Gemini family, is bounded by its
                     calls in the last seven days.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent
LEDGER_SCHEMA = "ternforge-model-ledger-1"
RESPONSE_SCHEMA = "ternforge-model-response-1"
LEDGER_PATH = BRIDGE / "semantic-mutants" / "model-ledger.jsonl"
BACKENDS = ("claude-cli", "antigravity-cli")
# Test Plan labels of the Model generation tables.
ROLES = {
    "Semantic mutant generator": "generator",
    "Draft test author": "draft_author",
    "Survivor verdict": "verdict",
    "Survivor verdict review": "verdict_review",
}


def model_family(model: str) -> str:
    """Whose model it is, whichever backend serves it: Antigravity serves Claude as well as Gemini."""
    name = model.lower()
    return "anthropic" if name.startswith("claude") else "google" if name.startswith("gemini") else "openai" if name.startswith("gpt") else "other"

BUDGET_LABELS = {
    "5-hour window": "five_hour",
    "Weekly window": "seven_day",
    "Calls per run": "calls_per_run",
    "List price per call": "usd_per_call",
    "Draft attempts per mutant": "draft_attempts",
    "Parallel calls per backend": "parallel_calls",
    "Smaller-pool calls per week": "pool_calls_per_week",
}
# Test Plan labels of the Survivor judgement settings.
JUDGEMENT_LABELS = {
    "Symbolic paths per mutant": "symbolic_paths",
    "Symbolic time limit per mutant": "symbolic_seconds",
    "False-equivalent rate": "alpha",
    "Assessed equivalence": "assessed_equivalence",
}
OUTCOMES = ("ok", "invalid", "rejected", "error", "timeout", "unavailable", "deferred")
# The cheapest model of each backend, for the probe that reads availability and windows.
PROBE_MODELS = {"claude-cli": "claude-haiku-4-5-20251001", "antigravity-cli": "gemini-3.8-flash-low"}
# Variables that would bill an API account instead of the subscription.
API_KEY_VARIABLES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "GEMINI_API_KEY", "GOOGLE_API_KEY")
TIMEOUT = 300


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def stable_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def module_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def new_call_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)


# --- the answer's shape ----------------------------------------------------------------


def schema_errors(value, schema: dict, path: str = "$") -> list[str]:
    """Validate against the subset of JSON Schema the generation schemas use: type, enum,
    required, properties, additionalProperties, items, min/maxItems and min/maxLength.
    """
    kinds = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}
    kind = schema.get("type")
    if kind:
        if (isinstance(value, bool) and kind in {"integer", "number"}) or not isinstance(value, kinds[kind]):
            return [f"{path}: expected {kind}"]
    errors = []
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: not one of {schema['enum']}")
    if kind == "string":
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']}")
    if kind == "array":
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        for index, item in enumerate(value):
            errors.extend(schema_errors(item, schema.get("items") or {}, f"{path}[{index}]"))
    if kind == "object":
        properties = schema.get("properties") or {}
        errors.extend(f"{path}: missing {key}" for key in schema.get("required") or [] if key not in value)
        if schema.get("additionalProperties") is False:
            errors.extend(f"{path}: unexpected {key}" for key in value if key not in properties)
        for key, item in value.items():
            if key in properties:
                errors.extend(schema_errors(item, properties[key], f"{path}.{key}"))
    return errors


# --- one call ----------------------------------------------------------------------------


@dataclass
class Invocation:
    """What one backend call returned; ``structured`` is set only when the outcome is ok."""

    outcome: str
    reason: str = ""
    structured: dict | None = None
    tokens: dict = field(default_factory=dict)
    list_usd: float | None = None
    seconds: float = 0.0
    windows: dict | None = None
    backend_version: str = ""
    model_reported: str = ""


def _clip(text: str, limit: int = 240) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def subscription_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key not in API_KEY_VARIABLES}


# Named sign-ins of the Claude CLI, side by side: each profile is its own CLAUDE_CONFIG_DIR, so one
# machine can spread work over several subscriptions and switch without signing in again.
CLAUDE_PROFILES_DIR = Path.home() / ".claude-cli-profiles"
CLAUDE_PROFILE_SETTING = Path.home() / ".config" / "ternforge" / "claude-profile"
# Variables of the agent session that started the run (Claude Code, the desktop app); a headless
# call inherits none of them, so it never runs with that session's effort, auth or channels.
HOST_SESSION_PREFIXES = ("CLAUDE_CODE_", "CLAUDECODE", "CLAUDE_AGENT_SDK", "CLAUDE_EFFORT", "CLAUDE_PID", "CLAUDE_PREVIEW", "CLAUDE_CONFIG_DIR")


def claude_profile() -> tuple[str, str]:
    """The Claude CLI profile calls use, and where that choice comes from: TERNFORGE_CLAUDE_PROFILE,
    else this machine's setting (``model_generation.py profile NAME``), else ``default``, the CLI's
    own sign-in."""
    name = os.environ.get("TERNFORGE_CLAUDE_PROFILE", "").strip()
    if name:
        return name, "TERNFORGE_CLAUDE_PROFILE"
    try:
        name = CLAUDE_PROFILE_SETTING.read_text().strip()
    except OSError:
        name = ""
    if name:
        return name, str(CLAUDE_PROFILE_SETTING)
    return "default", "the CLI's own sign-in"


def claude_env(profile: str) -> dict[str, str]:
    env = {key: value for key, value in subscription_env().items() if not key.startswith(HOST_SESSION_PREFIXES)}
    if profile != "default":
        env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_PROFILES_DIR / profile)
    return env


def account_label(profile: str) -> str:
    """The sign-in a ledger row names: ``default`` for the CLI's own sign-in, else a short digest of
    the profile name. A profile is often named after a person or an alias, and the ledger is kept
    in the repository, so it never carries the name."""
    return profile if profile in {"", "default"} else "profile-" + sha256_text(profile)[:8]


class ClaudeCli:
    name = "claude-cli"
    # One plan window for the whole account: a rejection stops every model until it resets.
    account_windows = True

    def __init__(self, executable: str | None = None, runner=subprocess.run, profile: str | None = None):
        self.executable = executable or shutil.which("claude") or ""
        self.runner = runner
        self.profile = profile or claude_profile()[0]

    def version(self) -> str:
        if not self.executable:
            return ""
        done = self.runner([self.executable, "--version"], capture_output=True, text=True, timeout=60)
        match = re.search(r"\d+\.\d+\.\d+", done.stdout or "")
        return match.group(0) if match else ""

    def command(self, model: str, system: str, schema: dict | None, usd_cap: float | None) -> list[str]:
        command = [
            self.executable, "-p", "--output-format", "stream-json", "--verbose",
            "--tools", "", "--strict-mcp-config", "--safe-mode", "--disable-slash-commands",
            "--no-session-persistence", "--model", model, "--system-prompt", system,
        ]
        if schema is not None:
            command += ["--json-schema", json.dumps(schema)]
        if usd_cap is not None:
            command += ["--max-budget-usd", f"{usd_cap:.2f}"]
        return command

    def invoke(self, *, model: str, system: str, prompt: str, schema: dict | None, usd_cap: float | None = None, timeout: int = TIMEOUT) -> Invocation:
        if not self.executable:
            return Invocation("unavailable", "the claude CLI is not installed")
        if self.profile != "default" and not (CLAUDE_PROFILES_DIR / self.profile).is_dir():
            return Invocation("unavailable", "the chosen Claude CLI profile is not signed in (see `model_generation.py profile`, then sign it in with --login)")
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="ternforge-model-call-") as empty:
            try:
                done = self.runner(
                    self.command(model, system, schema, usd_cap), input=prompt, capture_output=True, text=True,
                    cwd=empty, env=claude_env(self.profile), timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return Invocation("timeout", f"no answer within {timeout} s", seconds=round(time.monotonic() - started, 1))
        invocation = parse_claude_stream(done.stdout or "", done.stderr or "", done.returncode, schema)
        invocation.seconds = round(time.monotonic() - started, 1)
        return invocation


def parse_claude_stream(stdout: str, stderr: str, returncode: int, schema: dict | None) -> Invocation:
    """Read a ``claude -p --output-format stream-json --verbose`` run into one Invocation."""
    init, limit, result = {}, {}, {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            init = event
        elif event.get("type") == "rate_limit_event":
            limit = event.get("rate_limit_info") or {}
        elif event.get("type") == "result":
            result = event
    windows = None
    if limit:
        unified = limit.get("unifiedWindows") or {}
        windows = {
            "status": limit.get("status"),
            "five_hour": (unified.get("five_hour") or {}).get("utilization"),
            "five_hour_resets_at": (unified.get("five_hour") or {}).get("resetsAt"),
            "seven_day": (unified.get("seven_day") or {}).get("utilization"),
            "seven_day_resets_at": (unified.get("seven_day") or {}).get("resetsAt"),
        }
    usage = result.get("usage") or {}
    tokens = {
        "input": int(usage.get("input_tokens") or 0),
        "cache_read": int(usage.get("cache_read_input_tokens") or 0),
        "cache_write": int(usage.get("cache_creation_input_tokens") or 0),
        "output": int(usage.get("output_tokens") or 0),
        "thinking": int((usage.get("output_tokens_details") or {}).get("thinking_tokens") or 0),
    } if usage else {}
    common = {
        "tokens": tokens,
        "list_usd": round(float(result["total_cost_usd"]), 6) if result.get("total_cost_usd") is not None else None,
        "windows": windows,
        "backend_version": str(init.get("claude_code_version") or ""),
        "model_reported": str(init.get("model") or ""),
    }
    if init and init.get("apiKeySource") not in {None, "none"}:
        return Invocation("error", "the call billed an API key instead of the subscription", **common)
    if (limit or {}).get("status") == "rejected":
        return Invocation("rejected", "the plan's usage window rejected the call", **common)
    if not result:
        tail = _clip(stderr.strip().splitlines()[-1] if stderr.strip() else f"exit {returncode}")
        if re.search(r"not logged in|log ?in|authenticate|authentication|oauth|credential", stderr, re.IGNORECASE):
            return Invocation("unavailable", "the claude CLI is not signed in: " + tail, **common)
        return Invocation("error", "no result from the claude CLI: " + tail, **common)
    text = " ".join(str(result.get(key) or "") for key in ("result", "api_error_status", "subtype"))
    if result.get("is_error") or result.get("subtype") != "success":
        if str(result.get("api_error_status")) == "429" or re.search(r"usage limit|rate limit|limit reached", text, re.IGNORECASE):
            return Invocation("rejected", "the plan's usage window rejected the call: " + _clip(text), **common)
        if str(result.get("api_error_status")) in {"401", "403"} or re.search(r"log ?in|authenticate|authentication|oauth", text, re.IGNORECASE):
            return Invocation("unavailable", "the claude CLI is not signed in: " + _clip(text), **common)
        if result.get("subtype") == "error_max_budget_usd":
            return Invocation("error", "the call reached its list-price cap", **common)
        return Invocation("error", "the call failed: " + _clip(text), **common)
    if schema is None:
        return Invocation("ok", "", {"text": str(result.get("result") or "")}, **common)
    structured = result.get("structured_output")
    if not isinstance(structured, dict):
        return Invocation("invalid", "the answer carries no structured output", **common)
    errors = schema_errors(structured, schema)
    if errors:
        return Invocation("invalid", "the answer breaks its schema: " + _clip("; ".join(errors[:4])), **common)
    return Invocation("ok", "", structured, **common)


class AntigravityCli:
    name = "antigravity-cli"
    # Two quotas, one for the Gemini family and one for every other model: a rejection stops
    # the models of its own pool only.
    account_windows = False

    @staticmethod
    def quota_pool(model: str) -> str:
        return "gemini" if model_family(model) == "google" else "other"
    # The CLI reports neither quota. The smaller one serves far fewer calls a week (about 64 of the
    # pilot's on Google AI Pro), so the guard bounds it by the calls the ledger shows it took.
    smaller_pool = "other"
    # agy has no switch that removes its tools; it is told not to reach for them, and a call that
    # does anyway is refused (the headless run denies the permission and answers nothing).
    TOOLLESS = "Answer from the text alone: do not run commands, read or write files, or use any tool."

    def __init__(self, executable: str | None = None, runner=subprocess.run):
        self.executable = executable or shutil.which("agy") or ""
        self.runner = runner

    def version(self) -> str:
        if not self.executable:
            return ""
        done = self.runner([self.executable, "--version"], capture_output=True, text=True, timeout=60)
        match = re.search(r"\d+\.\d+\.\d+", (done.stdout or "") + (done.stderr or ""))
        return match.group(0) if match else ""

    def command(self, model: str, system: str, prompt: str, schema: dict | None) -> list[str]:
        command = [
            self.executable, f"-p={self.TOOLLESS}\n{system}\n\n{prompt}", "--output-format", "json", "--model", model,
            "--disable-slash-commands", "--sandbox",
        ]
        if schema is not None:
            command += ["--json-schema", json.dumps(schema)]
        return command

    def invoke(self, *, model: str, system: str, prompt: str, schema: dict | None, usd_cap: float | None = None, timeout: int = TIMEOUT) -> Invocation:
        if not self.executable:
            return Invocation("unavailable", "the agy CLI is not installed")
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="ternforge-model-call-") as empty:
            try:
                done = self.runner(
                    self.command(model, system, prompt, schema), capture_output=True, text=True,
                    cwd=empty, env=subscription_env(), timeout=timeout, stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired:
                return Invocation("timeout", f"no answer within {timeout} s", seconds=round(time.monotonic() - started, 1))
        invocation = parse_antigravity_json(done.stdout or "", done.stderr or "", done.returncode, schema)
        invocation.seconds = round(time.monotonic() - started, 1)
        invocation.backend_version = self.version()
        return invocation


def parse_antigravity_json(stdout: str, stderr: str, returncode: int, schema: dict | None) -> Invocation:
    """Read an ``agy -p --output-format json`` run into one Invocation."""
    try:
        payload = json.loads(stdout.strip().splitlines()[-1]) if stdout.strip() else {}
    except ValueError:
        payload = {}
    usage = payload.get("usage") or {}
    tokens = {
        "input": int(usage.get("input_tokens") or 0),
        "cache_read": int(usage.get("cache_read_tokens") or 0),
        "cache_write": 0,
        "output": int(usage.get("output_tokens") or 0),
        "thinking": int(usage.get("thinking_tokens") or 0),
    } if usage else {}
    common = {"tokens": tokens, "list_usd": None, "windows": None}
    error = str(payload.get("error") or "") or (stderr.strip() if not payload else "")
    status = str(payload.get("status") or "").upper()
    if not payload or status == "ERROR" or error:
        # The first line only: a sign-in message goes on to a personal verification link.
        reason = _clip(error.strip().splitlines()[0] if error.strip() else f"exit {returncode}")
        if re.search(r"eligib|verify your account|sign ?in|log ?in|authenticate|authentication|credential", error, re.IGNORECASE):
            return Invocation("unavailable", "the Antigravity account cannot be used: " + reason, **common)
        if re.search(r"quota|credits|rate limit|resource.exhausted|429", error, re.IGNORECASE):
            return Invocation("rejected", "the Antigravity quota rejected the call: " + reason, **common)
        return Invocation("error", "the call failed: " + reason, **common)
    denied = sorted({str(item.get("action") or item.get("display_name") or "a tool") for item in payload.get("denied_actions") or []})
    if denied and payload.get("structured_output") is None and not str(payload.get("response") or "").strip():
        return Invocation("invalid", "the model reached for a tool the adapter does not allow (" + ", ".join(denied) + ") and answered nothing", **common)
    if schema is None:
        return Invocation("ok", "", {"text": str(payload.get("response") or "")}, **common)
    structured = payload.get("structured_output")
    if structured is None:
        text = str(payload.get("response") or "").strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        try:
            structured = json.loads(fenced.group(1) if fenced else text)
        except ValueError:
            return Invocation("invalid", "the answer is not the JSON its schema asks for", **common)
    if not isinstance(structured, dict):
        return Invocation("invalid", "the answer is not a JSON object", **common)
    errors = schema_errors(structured, schema)
    if errors:
        return Invocation("invalid", "the answer breaks its schema: " + _clip("; ".join(errors[:4])), **common)
    return Invocation("ok", "", structured, **common)


BACKEND_TYPES = {"claude-cli": ClaudeCli, "antigravity-cli": AntigravityCli}


# --- the budget, the ledger and one run -------------------------------------------------


def parse_roles(rows: list[dict]) -> dict[str, list[dict]]:
    """The Test Plan's Model generation table, fail-closed: every role, backend, order and model known."""
    roles: dict[str, list[dict]] = {}
    for row in rows:
        role = ROLES.get(row.get("Role", ""))
        backend = row.get("Backend", "").strip("`")
        model = row.get("Model", "").strip("`")
        order = row.get("Order", "")
        if role is None or backend not in BACKENDS or not model or not order.isdigit():
            raise RuntimeError(f"Test Plan: a Model generation row names an unknown role, backend, order or model: {row}")
        roles.setdefault(role, []).append({"order": int(order), "backend": backend, "model": model})
    if set(roles) != set(ROLES.values()):
        raise RuntimeError(f"Test Plan: Model generation must list every role {sorted(ROLES)}")
    for role, entries in roles.items():
        orders = [entry["order"] for entry in entries]
        if sorted(orders) != list(range(1, len(orders) + 1)):
            raise RuntimeError(f"Test Plan: the {role} backends must be ordered 1, 2, …")
        entries.sort(key=lambda entry: entry["order"])
    return roles


def parse_budget(rows: list[dict]) -> dict[str, float]:
    """The Test Plan's Generation budget table, fail-closed: every limit present and readable."""
    budget: dict[str, float] = {}
    for row in rows:
        key = BUDGET_LABELS.get(row.get("Budget", ""))
        value = re.sub(r"\*\*", "", row.get("Limit", "")).strip()
        if key is None:
            raise RuntimeError(f"Test Plan: unknown Generation budget row {row.get('Budget')!r}")
        match = re.fullmatch(r"(\d+(?:\.\d+)?)%", value) if key in {"five_hour", "seven_day"} else (
            re.fullmatch(r"\$(\d+(?:\.\d+)?)", value) if key == "usd_per_call" else re.fullmatch(r"(\d+)", value)
        )
        if not match:
            raise RuntimeError(f"Test Plan: Generation budget {row.get('Budget')!r} has an unreadable limit {value!r}")
        number = float(match.group(1))
        budget[key] = number / 100 if key in {"five_hour", "seven_day"} else number
    if set(budget) != set(BUDGET_LABELS.values()):
        raise RuntimeError(f"Test Plan: Generation budget must set every limit {sorted(BUDGET_LABELS)}")
    return budget


def parse_assessors(rows: list[dict]) -> list[dict]:
    """The Test Plan's Survivor judgement table, fail-closed: assessors numbered 1, 2, … in order,
    each with its models ordered 1, 2, …, every model a known backend's and listed once. Every
    assessor answers and none stands in for another; within an assessor a later model answers only
    when the ones before it cannot."""
    assessors = []
    for row in rows:
        number = row.get("Assessor", "")
        order = row.get("Order", "") or "1"
        backend = row.get("Backend", "").strip("`")
        model = row.get("Model", "").strip("`")
        if not number.isdigit() or not order.isdigit() or backend not in BACKENDS or not model:
            raise RuntimeError(f"Test Plan: a Survivor judgement row names an unknown assessor, order, backend or model: {row}")
        assessors.append({"assessor": int(number), "order": int(order), "backend": backend, "model": model, "key": f"{backend}:{model}"})
    numbers = [row["assessor"] for row in assessors]
    if numbers != sorted(numbers) or sorted(set(numbers)) != list(range(1, len(set(numbers)) + 1)):
        raise RuntimeError("Test Plan: the survivor assessors must be numbered 1, 2, … in order")
    for number, models in assessor_seats(assessors).items():
        if [row["order"] for row in models] != list(range(1, len(models) + 1)):
            raise RuntimeError(f"Test Plan: the models of survivor assessor {number} must be ordered 1, 2, …")
    if len({row["key"] for row in assessors}) != len(assessors):
        raise RuntimeError("Test Plan: a survivor assessor model is listed twice")
    return assessors


def assessor_seats(assessors: list[dict]) -> dict[int, list[dict]]:
    """Each assessor's models, in the order they answer."""
    seats: dict[int, list[dict]] = {}
    for row in assessors:
        seats.setdefault(row["assessor"], []).append(row)
    return seats


def assessor_configurations(assessors: list[dict], usable) -> list[list[str]]:
    """Every combination of models that can judge a survivor, one usable model per assessor, the
    first models first. Empty while an assessor has no usable model."""
    choices = [[row["key"] for row in models if row["key"] in usable] for models in assessor_seats(assessors).values()]
    return [list(combination) for combination in itertools.product(*choices)] if choices and all(choices) else []


def parse_judgement(rows: list[dict]) -> dict:
    """The Test Plan's Judgement settings, fail-closed. Assessed equivalence can only be advisory:
    a model's equivalent never takes a survivor out of its class (ADR_0005)."""
    settings: dict = {}
    for row in rows:
        key = JUDGEMENT_LABELS.get(row.get("Setting", ""))
        value = re.sub(r"\*\*", "", row.get("Value", "")).strip()
        if key is None:
            raise RuntimeError(f"Test Plan: unknown Judgement setting {row.get('Setting')!r}")
        if key == "symbolic_paths":
            # A bound on paths gives the same search on any machine; the time limit is only a safety net.
            match = re.fullmatch(r"(\d+) paths", value)
            parsed = int(match.group(1)) if match and int(match.group(1)) > 0 else None
        elif key == "symbolic_seconds":
            match = re.fullmatch(r"(\d+(?:\.\d+)?) s", value)
            parsed = float(match.group(1)) if match else None
        elif key == "alpha":
            match = re.fullmatch(r"(\d+(?:\.\d+)?)%", value)
            parsed = float(match.group(1)) / 100 if match else None
        else:
            parsed = value if value == "advisory" else None
        if parsed is None or (key == "alpha" and not (isinstance(parsed, float) and 0 < parsed < 1)):
            raise RuntimeError(f"Test Plan: Judgement setting {row.get('Setting')!r} has an unreadable value {value!r}")
        settings[key] = parsed
    if set(settings) != set(JUDGEMENT_LABELS.values()):
        raise RuntimeError(f"Test Plan: Judgement settings must set every value {sorted(JUDGEMENT_LABELS)}")
    return settings


def ledger_time(row: dict) -> datetime | None:
    """When a ledger row was written, or None for a row without a readable time."""
    try:
        return datetime.fromisoformat(str(row.get("at")))
    except ValueError:
        return None


def read_ledger(path: Path = LEDGER_PATH) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class Run:
    """One generation run: backends tried per role in order, every call guarded and ledgered."""

    def __init__(self, roles: dict, budget: dict, *, ledger_path: Path = LEDGER_PATH, backends: dict | None = None, clock=utc_now):
        self.roles = roles
        self.budget = budget
        self.ledger_path = ledger_path
        self.backends = backends or {}
        self.clock = clock
        self.run_id = new_call_id()
        self.calls = 0
        self.windows: dict[str, dict | None] = {}
        self.availability: dict[str, str] = {}
        # (role, backend, model) the run must skip, with why: a model that has not passed its role's canaries.
        self.blocked: dict[tuple[str, str, str], str] = {}
        # (backend, quota pool) whose quota rejected a call in this run.
        self.rejected_models: dict[tuple[str, str], str] = {}
        # (backend, smaller quota pool): its calls in the seven days before the run, read from the
        # ledger once and counted on as the run reserves calls, since the pool reports no window.
        self.pool_calls: dict[tuple[str, str], int] = {}
        self.versions: dict[str, str] = {}
        self.rows: list[dict] = []
        # Several calls may run at once (call_many): the budget, the windows and the ledger change
        # under one lock. Each backend takes at most the Test Plan's parallel calls at a time, and
        # halves that for the rest of the run when it answers overloaded; it never grows by itself.
        self.lock = threading.RLock()
        self.parallel = max(1, int(budget.get("parallel_calls", 1)))
        self.turns = threading.Condition(self.lock)
        self.in_flight: dict[str, int] = {}
        self.limits: dict[str, int] = {}

    def enter(self, name: str) -> tuple[int, int]:
        """Wait for a free place on the backend; return how many calls it runs now and its limit."""
        with self.turns:
            self.limits.setdefault(name, self.parallel)
            while self.in_flight.get(name, 0) >= self.limits[name]:
                self.turns.wait()
            self.in_flight[name] = self.in_flight.get(name, 0) + 1
            return self.in_flight[name], self.limits[name]

    def leave(self, name: str, overloaded: bool) -> None:
        with self.turns:
            self.in_flight[name] -= 1
            if overloaded:
                self.limits[name] = max(1, self.limits[name] // 2)
            self.turns.notify_all()

    def backend(self, name: str):
        if name not in self.backends:
            self.backends[name] = BACKEND_TYPES[name]()
        return self.backends[name]

    def account(self, name: str) -> str:
        """Which sign-in of a backend the run uses, as a label that carries no profile name."""
        return account_label(str(getattr(self.backend(name), "profile", "") or ""))

    def record(self, row: dict) -> dict:
        with self.lock:
            row = {"schema": LEDGER_SCHEMA, "run_id": self.run_id, "at": self.clock(), **row}
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with self.ledger_path.open("a") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            self.rows.append(row)
            return row

    def probe(self, name: str) -> str:
        """Availability and windows of a backend, read once per run with its cheapest model."""
        with self.lock:
            return self._probe(name)

    def _probe(self, name: str) -> str:
        if name in self.availability:
            return self.availability[name]
        backend = self.backend(name)
        system, prompt = "Answer with one word.", "Reply with OK."
        invocation = backend.invoke(model=PROBE_MODELS[name], system=system, prompt=prompt, schema=None, usd_cap=0.05, timeout=120)
        self.versions[name] = invocation.backend_version or backend.version()
        self.windows[name] = invocation.windows
        if invocation.outcome == "rejected":
            # A full window is a budget matter, not a missing backend: the guard defers every call.
            self.reject(name, PROBE_MODELS[name], invocation)
        unusable = invocation.outcome not in {"ok", "rejected"}
        self.availability[name] = (invocation.reason or invocation.outcome) if unusable else ""
        self.record({
            "call_id": new_call_id(), "role": "probe", "purpose": "probe", "contract_id": "", "subject": "",
            "backend": name, "account": self.account(name), "backend_version": self.versions[name], "model": PROBE_MODELS[name],
            "outcome": invocation.outcome, "reason": invocation.reason, "prompt_sha256": sha256_text(prompt),
            "system_sha256": sha256_text(system), "schema_sha256": "", "response_sha256": "",
            "tokens": invocation.tokens, "list_usd": invocation.list_usd, "seconds": invocation.seconds,
            "windows": invocation.windows,
        })
        return self.availability[name]

    def quota_pool(self, name: str, model: str) -> str:
        """Which quota of a backend a model draws on: the backend's own pools, else the model alone."""
        pool = getattr(self.backend(name), "quota_pool", None)
        return pool(model) if callable(pool) else model

    def smaller_pool(self, name: str, model: str) -> str:
        """The backend's smaller quota pool when the model draws on it, else an empty string."""
        smaller = getattr(self.backend(name), "smaller_pool", "")
        return smaller if smaller and self.quota_pool(name, model) == smaller else ""

    def pool_week(self, name: str, pool: str) -> int:
        """The calls a backend's quota pool took in the last seven days: the ledger's calls actually
        made, as ``spend`` counts them, read once per run."""
        if (name, pool) not in self.pool_calls:
            since = datetime.fromisoformat(self.clock()) - timedelta(days=7)
            self.pool_calls[(name, pool)] = sum(
                1 for row in read_ledger(self.ledger_path)
                if row.get("backend") == name and row.get("role") != "probe" and row.get("outcome") not in {"deferred", "unavailable"}
                and self.quota_pool(name, str(row.get("model") or "")) == pool and (at := ledger_time(row)) is not None and at >= since
            )
        return self.pool_calls[(name, pool)]

    def reject(self, name: str, model: str, invocation) -> None:
        """Remember a rejection for the run: for the whole backend when its plan window is the
        account's, otherwise for the quota pool the model draws on."""
        if getattr(self.backend(name), "account_windows", False):
            self.windows[name] = {**(invocation.windows or {}), "status": "rejected"}
        else:
            self.rejected_models[(name, self.quota_pool(name, model))] = invocation.reason

    def deferral(self, name: str, model: str = "") -> str:
        """Why the guard would not make a call on this backend and model now, or an empty string."""
        if self.calls >= self.budget["calls_per_run"]:
            return f"the run reached its limit of {int(self.budget['calls_per_run'])} calls"
        if model and (name, self.quota_pool(name, model)) in self.rejected_models:
            return f"the {self.quota_pool(name, model)} quota of {name} rejects calls until it resets"
        pool = self.smaller_pool(name, model) if model else ""
        limit = self.budget.get("pool_calls_per_week")
        if pool and limit is not None and self.pool_week(name, pool) >= limit:
            return f"the {pool} quota of {name} took {self.pool_week(name, pool)} calls in the last 7 days, at or above its limit of {int(limit)}"
        windows = self.windows.get(name) or {}
        if windows.get("status") == "rejected":
            return "the plan's usage window rejects calls until it resets"
        for key, label in (("five_hour", "5-hour"), ("seven_day", "weekly")):
            used = windows.get(key)
            if used is not None and used >= self.budget[key]:
                return f"the {label} window is at {used:.0%}, at or above its {self.budget[key]:.0%} limit"
        return ""

    def call(self, role: str, *, purpose: str, contract_id: str, subject: str, system: str, prompt: str, schema: dict, response_dir: Path) -> tuple[dict, dict | None]:
        """Try the role's backends in order. Return the ledger row of the last attempt and, when a
        backend answered within its schema, the stored response.
        """
        row, response, _attempts = self.call_with_attempts(
            role, purpose=purpose, contract_id=contract_id, subject=subject, system=system, prompt=prompt, schema=schema, response_dir=response_dir,
        )
        return row, response

    def call_many(self, requests: list[dict]) -> list[tuple[dict, dict | None, list[dict]]]:
        """Make independent calls at once, each as ``call_with_attempts`` makes it, and return their
        results in the order asked. Each backend still takes at most the parallel calls at a time,
        and every call is guarded and ledgered on its own."""
        if len(requests) <= 1 or self.parallel == 1:
            return [self.call_with_attempts(**request) for request in requests]
        with ThreadPoolExecutor(max_workers=min(len(requests), self.parallel * len(BACKENDS))) as pool:
            return list(pool.map(lambda request: self.call_with_attempts(**request), requests))

    def call_with_attempts(self, role: str, *, purpose: str, contract_id: str, subject: str, system: str, prompt: str, schema: dict, response_dir: Path) -> tuple[dict, dict | None, list[dict]]:
        """``call``, and the ledger rows of every attempt it made, in order."""
        schema_sha = sha256_text(stable_json(schema))
        attempts = []
        for entry in self.roles[role]:
            name, model = entry["backend"], entry["model"]
            base = {
                "call_id": new_call_id(), "role": role, "purpose": purpose, "contract_id": contract_id, "subject": subject,
                "backend": name, "account": self.account(name), "model": model, "prompt_sha256": sha256_text(prompt), "system_sha256": sha256_text(system),
                "schema_sha256": schema_sha, "response_sha256": "",
            }
            # The guard decides and reserves the call under the lock, so calls made at once never
            # overrun the run's limit or a window another call has just reported full.
            with self.lock:
                skipped = self.blocked.get((role, name, model))
                if skipped:
                    attempts.append(self.record({**base, "backend_version": self.versions.get(name, ""), "outcome": "unavailable", "reason": skipped, "tokens": {}, "list_usd": None, "seconds": 0.0, "windows": None}))
                    continue
                unavailable = self._probe(name)
                if unavailable:
                    attempts.append(self.record({**base, "backend_version": self.versions.get(name, ""), "outcome": "unavailable", "reason": unavailable, "tokens": {}, "list_usd": None, "seconds": 0.0, "windows": self.windows.get(name)}))
                    continue
                deferred = self.deferral(name, model)
                if deferred:
                    attempts.append(self.record({**base, "backend_version": self.versions.get(name, ""), "outcome": "deferred", "reason": deferred, "tokens": {}, "list_usd": None, "seconds": 0.0, "windows": self.windows.get(name)}))
                    continue
                self.calls += 1
                pool = self.smaller_pool(name, model)
                if pool:
                    self.pool_calls[(name, pool)] = self.pool_week(name, pool) + 1
            in_flight, limit = self.enter(name)
            invocation = None
            try:
                invocation = self.backend(name).invoke(model=model, system=system, prompt=prompt, schema=schema, usd_cap=self.budget["usd_per_call"])
            finally:
                self.leave(name, invocation is not None and overloaded(invocation))
            with self.lock:
                if invocation.windows is not None:
                    self.windows[name] = invocation.windows
                if invocation.outcome == "rejected":
                    self.reject(name, model, invocation)
                version = invocation.backend_version or self.versions.get(name, "")
            response = None
            if invocation.outcome == "ok":
                response = {
                    "schema": RESPONSE_SCHEMA, "call_id": base["call_id"], "role": role, "purpose": purpose,
                    "contract_id": contract_id, "subject": subject, "backend": name, "backend_version": version,
                    "model": model, "system": system, "prompt": prompt, "answer_schema": schema,
                    "prompt_sha256": base["prompt_sha256"], "system_sha256": base["system_sha256"], "schema_sha256": schema_sha,
                    "structured": invocation.structured,
                }
                base["response_sha256"] = response_sha256(response)
                response_dir.mkdir(parents=True, exist_ok=True)
                (response_dir / f"{base['call_id']}.json").write_text(json.dumps(response, indent=2, sort_keys=True) + "\n")
            # How busy the backend was, for deciding its parallel limit later from what happened.
            row = self.record({
                **base, "backend_version": version, "outcome": invocation.outcome, "reason": invocation.reason,
                "tokens": invocation.tokens, "list_usd": invocation.list_usd, "seconds": invocation.seconds,
                "windows": invocation.windows, "in_flight": in_flight, "parallel_limit": limit,
                "backed_off": overloaded(invocation),
            })
            attempts.append(row)
            if response is not None:
                return row, response, attempts
            if invocation.outcome in {"rejected", "unavailable"}:
                continue
            return row, None, attempts
        return attempts[-1], None, attempts

    def summary(self) -> dict:
        return {"run_id": self.run_id, **spend(self.rows)}


# What a backend says when it is overloaded rather than out of quota: capacity or rate, not budget.
OVERLOAD = re.compile(r"\b(?:429|503)\b|RESOURCE_EXHAUSTED|UNAVAILABLE|no capacity|rate.?limit|overloaded", re.IGNORECASE)


def overloaded(invocation) -> bool:
    return invocation.outcome not in {"ok", "invalid"} and bool(OVERLOAD.search(invocation.reason or ""))


def response_sha256(response: dict) -> str:
    """The digest a proposal or draft carries: the answer and everything it answered."""
    keys = ("call_id", "backend", "model", "prompt_sha256", "system_sha256", "schema_sha256", "structured")
    return sha256_text(stable_json({key: response.get(key) for key in keys}))


def verify_response(response: dict) -> list[str]:
    """What does not add up in a stored response: its digests against its own text and schema."""
    problems = []
    if response.get("schema") != RESPONSE_SCHEMA:
        problems.append("unknown response schema")
    if sha256_text(str(response.get("prompt") or "")) != response.get("prompt_sha256"):
        problems.append("the prompt does not match its digest")
    if sha256_text(str(response.get("system") or "")) != response.get("system_sha256"):
        problems.append("the system prompt does not match its digest")
    if sha256_text(stable_json(response.get("answer_schema") or {})) != response.get("schema_sha256"):
        problems.append("the answer schema does not match its digest")
    if schema_errors(response.get("structured") or {}, response.get("answer_schema") or {}):
        problems.append("the answer breaks its schema")
    return problems


def spend(rows: list[dict]) -> dict:
    """What a set of ledger rows cost: attempts by outcome, the calls actually made (an attempt the
    guard deferred or a backend that was unavailable makes none), tokens, list price and window span."""
    attempts = [row for row in rows if row.get("role") != "probe"]
    outcomes = {outcome: sum(row.get("outcome") == outcome for row in attempts) for outcome in OUTCOMES}
    tokens = {key: sum(int((row.get("tokens") or {}).get(key) or 0) for row in rows) for key in ("input", "cache_read", "cache_write", "output", "thinking")}
    # Thinking is part of the output a backend counts, not tokens on top of it.
    tokens["total"] = tokens["input"] + tokens["cache_read"] + tokens["cache_write"] + tokens["output"]
    priced = [row["list_usd"] for row in rows if row.get("list_usd") is not None]
    windows = [row["windows"] for row in rows if row.get("windows")]
    span = {}
    for key in ("five_hour", "seven_day"):
        values = [window[key] for window in windows if window.get(key) is not None]
        if values:
            span[key] = [values[0], values[-1]]
    return {
        "attempts": len(attempts),
        "calls": sum(row.get("outcome") not in {"deferred", "unavailable"} for row in attempts),
        "deferred": outcomes["deferred"],
        "probes": len(rows) - len(attempts),
        "outcomes": outcomes,
        "tokens": tokens,
        "list_usd": round(sum(priced), 4) if priced else None,
        "seconds": round(sum(float(row.get("seconds") or 0) for row in rows), 1),
        "windows": span,
        "models": sorted({f"{row['backend']}:{row['model']}" for row in attempts if row.get("outcome") == "ok"}),
    }


def main(argv: list[str]) -> int:
    """``model_generation.py profile [NAME] [--login]``: show the Claude CLI profile calls use and the
    profiles signed in on this machine, or choose one (``default`` is the CLI's own sign-in). With
    ``--login`` the person signs that profile in, once, in the browser."""
    if not argv or argv[0] != "profile":
        print(main.__doc__)
        return 2
    names = sorted(path.name for path in CLAUDE_PROFILES_DIR.iterdir() if path.is_dir()) if CLAUDE_PROFILES_DIR.is_dir() else []
    if len(argv) >= 2:
        name = argv[1]
        if name != "default" and "--login" in argv:
            (CLAUDE_PROFILES_DIR / name).mkdir(parents=True, exist_ok=True)
            done = subprocess.run([shutil.which("claude") or "claude", "auth", "login", "--claudeai"], env=claude_env(name), check=False)
            if done.returncode != 0:
                return done.returncode
        elif name != "default" and name not in names:
            print(f"no signed-in profile {name}: run `model_generation.py profile {name} --login` first")
            return 1
        CLAUDE_PROFILE_SETTING.parent.mkdir(parents=True, exist_ok=True)
        CLAUDE_PROFILE_SETTING.write_text(name + "\n")
    active, source = claude_profile()
    print(f"claude-cli profile: {active} (from {source})")
    print("signed-in profiles: " + ", ".join(["default", *names]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
