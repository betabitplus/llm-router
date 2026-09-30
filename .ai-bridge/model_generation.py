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

import atexit
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
    # A mutant whose drafts all missed climbs a ladder: the draft author with tools, then the last
    # resort, the verdict's own model, with the same tools.
    "Draft test author with tools": "draft_author_tools",
    "Draft test author, last resort": "draft_author_last",
    "Survivor verdict": "verdict",
    "Survivor verdict review": "verdict_review",
}
# The roles whose calls work in a copy of the project with tools, and the backends that can hold
# those tools to what the builder allows (agy cannot switch its own tools off, so it serves none).
TOOL_ROLES = ("draft_author_tools", "draft_author_last")
TOOL_BACKENDS = ("claude-cli",)
TOOLS = "Read,Grep,Glob,Write,Edit,Bash"
# The reasoning effort each backend takes by flag (Claude Code's model configuration, agy --help). An
# Antigravity model whose id names its level (gemini-3.8-flash-high) takes none: its id is its level.
EFFORT_LEVELS = {"claude-cli": ("low", "medium", "high", "xhigh", "max"), "antigravity-cli": ("low", "medium", "high", "max")}
LEVEL_IN_ID = re.compile(r"-(?:low|medium|high)$")
# The roles whose every answer execution checks in full: a draft is kept only when it breaks no rule,
# passes on the original five times and fails on the mutant. Only they may name a ladder of levels,
# the next level asked after a rejected draft, as Anthropic advises for work with a checker (run low,
# re-run the failures higher). A judge answers at the one level its canaries and calibration
# measured; the generator too, since execution checks its defect's form, not whether it matters.
ESCALATING_ROLES = ("draft_author", "draft_author_tools", "draft_author_last")


def model_family(model: str) -> str:
    """Whose model it is, whichever backend serves it: Antigravity serves Claude as well as Gemini."""
    name = model.lower()
    return "anthropic" if name.startswith("claude") else "google" if name.startswith("gemini") else "openai" if name.startswith("gpt") else "other"


def entry_key(backend: str, model: str, effort: str = "") -> str:
    """How records name a model at its level: ``backend:model``, and ``@level`` when a flag sets one.
    A model the Test Plan lists without a level keeps the name its answers were stored under."""
    return f"{backend}:{model}" + (f"@{effort}" if effort else "")


def parse_effort(cell: str, backend: str, model: str, where: str) -> list[str]:
    """A Test Plan Effort cell, fail-closed: empty or a dash when no flag sets the level, else one
    level or a rising ladder ``low → medium``, each a level the backend takes by flag."""
    text = cell.replace("`", "").strip()
    if text in {"", "—", "-"}:
        return []
    levels = [part.strip() for part in text.split("→")]
    allowed = EFFORT_LEVELS.get(backend, ())
    if any(level not in allowed for level in levels) or [allowed.index(level) for level in levels] != sorted({allowed.index(level) for level in levels}):
        raise RuntimeError(f"Test Plan: {where} names an unknown or unordered Effort {cell!r} for {backend}")
    if backend == "antigravity-cli" and LEVEL_IN_ID.search(model):
        raise RuntimeError(f"Test Plan: {where}: {model} names its level in its id, so its Effort stays empty")
    return levels

BUDGET_LABELS = {
    "5-hour window": "five_hour",
    "Weekly window": "seven_day",
    "Calls per run": "calls_per_run",
    "List price per call": "usd_per_call",
    "List price per call with tools": "usd_per_tool_call",
    "Draft attempts per mutant": "draft_attempts",
    "Parallel calls to start with": "parallel_calls",
    "Parallel calls at most": "parallel_calls_max",
    "Smaller-pool calls per week": "pool_calls_per_week",
    "Antigravity quota kept free": "agy_quota_floor",
}
# Budget rows given in percent.
PERCENT_BUDGETS = {"five_hour", "seven_day", "agy_quota_floor"}
# Test Plan labels of the Survivor judgement settings.
JUDGEMENT_LABELS = {
    "Symbolic paths per mutant": "symbolic_paths",
    "Symbolic time limit per mutant": "symbolic_seconds",
    "False-equivalent rate": "alpha",
    "Assessed equivalence": "assessed_equivalence",
}
OUTCOMES = ("ok", "invalid", "rejected", "error", "timeout", "capped", "unavailable", "deferred")
# A price cap is a fuse against a call that runs away, not a price list: it stands at this many
# times the most expensive answered call of its role, and never below the Test Plan's cap, so it
# moves with what the models cost instead of standing in the way when their prices change.
CAP_FACTOR = 3
# The cheapest model of each backend, for the probe that reads availability and windows.
PROBE_MODELS = {"claude-cli": "claude-haiku-4-5-20251001", "antigravity-cli": "gemini-3.8-flash-low"}
# Variables that would bill an API account instead of the subscription.
API_KEY_VARIABLES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "GEMINI_API_KEY", "GOOGLE_API_KEY")
TIMEOUT = 300
# A call with tools reads, writes and runs its check several times before it answers.
TOOL_TIMEOUT = 1500


@dataclass(frozen=True)
class Workspace:
    """The copy of the project a call with tools works in. It may read the copy, write the one file
    ``write`` names (relative to it) and run the one command ``command`` names; nothing else, and
    never anything under the person's home, where sign-ins and keys live."""

    root: Path
    write: str
    command: str

    def permissions(self) -> dict:
        return {
            "allow": ["Read(./**)", "Glob", "Grep", f"Write(./{self.write})", f"Edit(./{self.write})", f"Bash({self.command})"],
            "deny": ["Read(~/**)", "Write(~/**)", "Edit(~/**)"],
        }


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
    # A call with tools: how often it used each, and what its permissions refused.
    tools_used: dict = field(default_factory=dict)
    denied: list = field(default_factory=list)


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

    def profiles(self) -> list[str]:
        """Every Claude CLI sign-in of this machine, the chosen one first: a run moves to the next when
        the one in use has no room left in its windows."""
        named = sorted(path.name for path in CLAUDE_PROFILES_DIR.iterdir() if path.is_dir()) if CLAUDE_PROFILES_DIR.is_dir() else []
        return list(dict.fromkeys([self.profile, "default", *named]))

    def version(self) -> str:
        if not self.executable:
            return ""
        done = self.runner([self.executable, "--version"], capture_output=True, text=True, timeout=60)
        match = re.search(r"\d+\.\d+\.\d+", done.stdout or "")
        return match.group(0) if match else ""

    def command(self, model: str, system: str, schema: dict | None, usd_cap: float | None, workspace: Workspace | None = None, effort: str = "") -> list[str]:
        # Without a workspace a call has no tools at all; with one, only what its permissions allow,
        # without asking anyone. Neither reads the person's own settings: safe mode keeps a level
        # saved there for a model, and it would set the call's effort (it did, 2026-09-26 to 09-28).
        tools = ["--tools", "", "--setting-sources", ""] if workspace is None else [
            "--tools", TOOLS, "--permission-mode", "dontAsk",
            "--settings", json.dumps({"permissions": workspace.permissions()}, sort_keys=True), "--setting-sources", "",
        ]
        command = [
            self.executable, "-p", "--output-format", "stream-json", "--verbose",
            *tools, "--strict-mcp-config", "--safe-mode", "--disable-slash-commands",
            "--no-session-persistence", "--model", model, "--system-prompt", system,
        ]
        if schema is not None:
            command += ["--json-schema", json.dumps(schema)]
        if usd_cap is not None:
            command += ["--max-budget-usd", f"{usd_cap:.2f}"]
        if effort:
            command += ["--effort", effort]
        return command

    def invoke(self, *, model: str, system: str, prompt: str, schema: dict | None, usd_cap: float | None = None, timeout: int = TIMEOUT, workspace: Workspace | None = None, effort: str = "") -> Invocation:
        if not self.executable:
            return Invocation("unavailable", "the claude CLI is not installed")
        if self.profile != "default" and not (CLAUDE_PROFILES_DIR / self.profile).is_dir():
            return Invocation("unavailable", "the chosen Claude CLI profile is not signed in (see `model_generation.py profile`, then sign it in with --login)")
        started = time.monotonic()
        timeout = TOOL_TIMEOUT if workspace is not None else timeout
        with tempfile.TemporaryDirectory(prefix="ternforge-model-call-") as empty:
            try:
                done = self.runner(
                    self.command(model, system, schema, usd_cap, workspace, effort), input=prompt, capture_output=True, text=True,
                    cwd=str(workspace.root) if workspace is not None else empty, env=claude_env(self.profile), timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return Invocation("timeout", f"no answer within {timeout} s", seconds=round(time.monotonic() - started, 1))
        invocation = parse_claude_stream(done.stdout or "", done.stderr or "", done.returncode, schema)
        invocation.seconds = round(time.monotonic() - started, 1)
        return invocation


def parse_claude_stream(stdout: str, stderr: str, returncode: int, schema: dict | None) -> Invocation:
    """Read a ``claude -p --output-format stream-json --verbose`` run into one Invocation."""
    init, limit, result = {}, {}, {}
    used: dict[str, int] = {}
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
        elif event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    used[str(block.get("name"))] = used.get(str(block.get("name")), 0) + 1
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
        "tools_used": used,
        "denied": sorted({str(item.get("tool_name") or "a tool") for item in result.get("permission_denials") or [] if isinstance(item, dict)}),
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
            return Invocation("capped", "the call reached its list-price cap", **common)
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


# --- Antigravity accounts --------------------------------------------------------------

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


# What Antigravity says of an account it does not let in, such as one whose owner has yet to verify it.
INELIGIBLE = "the Antigravity account cannot be used: "
# The quotas agm reports per account.
QUOTA_FAMILIES = ("gemini-pro", "gemini-flash", "other")
# How long an account Antigravity did not let in is skipped without a call: long enough to spare a
# run's calls, short enough that an account its owner has since verified comes back.
BARRED_FOR = timedelta(hours=6)


# When Antigravity says a spent quota resets ("Individual quota reached. … Resets in 94h9m42s").
QUOTA_RESET = re.compile(r"Resets in (?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")


def quota_resets_at(reason: str, at: str) -> datetime | None:
    """When a quota a rejection names resets, read from its reason and the time of its row."""
    match = QUOTA_RESET.search(reason or "")
    if not match or not any(match.groups()):
        return None
    try:
        start = datetime.fromisoformat(at)
    except (TypeError, ValueError):
        return None
    hours, minutes, seconds = (int(value or 0) for value in match.groups())
    return start + timedelta(hours=hours, minutes=minutes, seconds=seconds)


def quota_family(model: str) -> str:
    """Which quota agm reports a model draws on: Gemini Pro, Gemini Flash, or the one Claude and GPT share."""
    if model_family(model) != "google":
        return "other"
    return "gemini-pro" if "-pro" in model.lower() else "gemini-flash"


def parse_agm_aliases(text: str) -> dict[str, str]:
    """``agm alias``: the alias of each account that has one, by account."""
    aliases = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and EMAIL.fullmatch(parts[1]):
            aliases[parts[1]] = parts[0]
    return aliases


def parse_agm_list(text: str) -> dict[str, dict]:
    """``agm list``: per account, whether agy uses it and what each quota has left, in percent."""
    accounts = {}
    for line in text.splitlines():
        match = re.fullmatch(r"\s*(\S+@\S+)\s+(?:(\S+)\s+)?(\d+)%\s+(\d+)%\s+(\d+)%\s*", line)
        if match and EMAIL.fullmatch(match.group(1)):
            _account, status, pro, flash, other = match.groups()
            accounts[match.group(1)] = {"agy": "cli" in (status or "").split(","), "gemini-pro": int(pro), "gemini-flash": int(flash), "other": int(other)}
    return accounts


class AgmAccounts:
    """The Antigravity sign-ins agm keeps (its multi-account switcher): which one agy uses and what each
    quota has left. A switch applies to agy alone (``--target agy``), never to the person's IDE. An
    account is known by its alias, its address stays in memory for the switch, and a record names it
    only by a digest."""

    def __init__(self, executable: str | None = None, runner=subprocess.run):
        self.executable = executable if executable is not None else shutil.which("agm") or ""
        self.runner = runner
        self.addresses: dict[str, str] = {}

    def _run(self, *args: str, timeout: int = 120) -> str:
        try:
            done = self.runner([self.executable, *args], capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return (done.stdout or "") if done.returncode == 0 else ""

    def cli_address(self) -> str:
        """The account agy's own credential store holds, as ``agm sync`` reads it: the one its calls
        use. agm's list may name another (on 2026-09-29 it named the second account while the store
        held the first), so this, not the list, says which account agy uses."""
        match = re.search(r"CLI \(agy\) credential store:\s*(\S+)", self._run("sync"))
        return match.group(1) if match and EMAIL.fullmatch(match.group(1)) else ""

    def alias_of(self, address: str) -> str:
        return next((alias for alias, known in self.addresses.items() if known == address), "account-" + sha256_text(address)[:8])

    def snapshot(self) -> dict[str, dict]:
        """Every account by alias with its quotas, read live, and whether agy uses it; empty without agm."""
        if not self.executable:
            return {}
        self._run("refresh-all", timeout=300)
        aliases = parse_agm_aliases(self._run("alias"))
        snapshot = {}
        for address, row in parse_agm_list(self._run("list")).items():
            alias = aliases.get(address) or "account-" + sha256_text(address)[:8]
            self.addresses[alias] = address
            snapshot[alias] = row
        actual = self.cli_address()
        if actual:
            for alias, row in snapshot.items():
                row["agy"] = self.addresses[alias] == actual
        return snapshot

    def switch(self, alias: str) -> bool:
        """Move agy alone to an account; True once its credential store holds that account."""
        try:
            done = self.runner(
                [self.executable, "switch", self.addresses.get(alias, alias), "--target", "agy"],
                capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return done.returncode == 0 and self.cli_address() == self.addresses.get(alias, alias)


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

    def __init__(self, executable: str | None = None, runner=subprocess.run, accounts: AgmAccounts | None = None):
        self.executable = executable or shutil.which("agy") or ""
        self.runner = runner
        # With agm, the run reads every account's quotas and moves agy to one that has some left.
        self.accounts = accounts if accounts is not None else AgmAccounts()
        self.profile = ""

    def version(self) -> str:
        if not self.executable:
            return ""
        done = self.runner([self.executable, "--version"], capture_output=True, text=True, timeout=60)
        match = re.search(r"\d+\.\d+\.\d+", (done.stdout or "") + (done.stderr or ""))
        return match.group(0) if match else ""

    def command(self, model: str, system: str, prompt: str, schema: dict | None, effort: str = "") -> list[str]:
        command = [
            self.executable, f"-p={self.TOOLLESS}\n{system}\n\n{prompt}", "--output-format", "json", "--model", model,
            "--disable-slash-commands", "--sandbox",
        ]
        if schema is not None:
            command += ["--json-schema", json.dumps(schema)]
        if effort:
            command += ["--effort", effort]
        return command

    def invoke(self, *, model: str, system: str, prompt: str, schema: dict | None, usd_cap: float | None = None, timeout: int = TIMEOUT, workspace: Workspace | None = None, effort: str = "") -> Invocation:
        if workspace is not None:
            return Invocation("unavailable", "a call with tools goes only through the claude CLI, whose permissions hold its tools to the copy")
        if not self.executable:
            return Invocation("unavailable", "the agy CLI is not installed")
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="ternforge-model-call-") as empty:
            try:
                done = self.runner(
                    self.command(model, system, prompt, schema, effort), capture_output=True, text=True,
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
            return Invocation("unavailable", INELIGIBLE + reason, **common)
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
        if role in TOOL_ROLES and backend not in TOOL_BACKENDS:
            raise RuntimeError(f"Test Plan: the {role} role works with tools, which only {', '.join(TOOL_BACKENDS)} can hold to the copy: {row}")
        effort = parse_effort(row.get("Effort", ""), backend, model, f"the {role} row of {model}")
        if len(effort) > 1 and role not in ESCALATING_ROLES:
            raise RuntimeError(f"Test Plan: the {role} role answers at one level; only a role whose answers execution checks in full climbs a ladder: {row}")
        roles.setdefault(role, []).append({"order": int(order), "backend": backend, "model": model, "effort": effort})
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
        match = re.fullmatch(r"(\d+(?:\.\d+)?)%", value) if key in PERCENT_BUDGETS else (
            re.fullmatch(r"\$(\d+(?:\.\d+)?)", value) if key in {"usd_per_call", "usd_per_tool_call"} else re.fullmatch(r"(\d+)", value)
        )
        if not match:
            raise RuntimeError(f"Test Plan: Generation budget {row.get('Budget')!r} has an unreadable limit {value!r}")
        number = float(match.group(1))
        budget[key] = number / 100 if key in PERCENT_BUDGETS else number
    if set(budget) != set(BUDGET_LABELS.values()):
        raise RuntimeError(f"Test Plan: Generation budget must set every limit {sorted(BUDGET_LABELS)}")
    return budget


def parse_assessors(rows: list[dict]) -> list[dict]:
    """The Test Plan's Survivor judgement table, fail-closed: assessors numbered 1, 2, … in order,
    each with its models ordered 1, 2, …, every model a known backend's and listed once. Every
    assessor answers and none stands in for another; within an assessor a later model answers only
    when the ones before it cannot. A row whose Effort is a ladder of levels is the search for the
    lowest level that meets the calibration floors: each level answers as a model of its own, in
    rising order, and the calibration asks a level only once the one below it missed the floors."""
    listed = []
    for row in rows:
        number = row.get("Assessor", "")
        order = row.get("Order", "") or "1"
        backend = row.get("Backend", "").strip("`")
        model = row.get("Model", "").strip("`")
        if not number.isdigit() or not order.isdigit() or backend not in BACKENDS or not model:
            raise RuntimeError(f"Test Plan: a Survivor judgement row names an unknown assessor, order, backend or model: {row}")
        levels = parse_effort(row.get("Effort", ""), backend, model, f"assessor {number}'s {model}")
        listed.append({"assessor": int(number), "order": int(order), "backend": backend, "model": model, "levels": levels})
    numbers = [row["assessor"] for row in listed]
    if numbers != sorted(numbers) or sorted(set(numbers)) != list(range(1, len(set(numbers)) + 1)):
        raise RuntimeError("Test Plan: the survivor assessors must be numbered 1, 2, … in order")
    assessors = []
    for number, models in assessor_seats(listed).items():
        if [row["order"] for row in models] != list(range(1, len(models) + 1)):
            raise RuntimeError(f"Test Plan: the models of survivor assessor {number} must be ordered 1, 2, …")
        for row in models:
            for level in row["levels"] or [""]:
                assessors.append({
                    "assessor": number, "order": sum(item["assessor"] == number for item in assessors) + 1, "backend": row["backend"],
                    "model": row["model"], "effort": level, "levels": row["levels"], "key": entry_key(row["backend"], row["model"], level),
                })
    if len({row["key"] for row in assessors}) != len(assessors):
        raise RuntimeError("Test Plan: a survivor assessor model is listed twice")
    return assessors


def assessor_seats(assessors: list[dict]) -> dict[int, list[dict]]:
    """Each assessor's models, in the order they answer."""
    seats: dict[int, list[dict]] = {}
    for row in assessors:
        seats.setdefault(row["assessor"], []).append(row)
    return seats


# The calibration floors an assessor model must meet, its canary (ADR_0006): a confirmed input for
# at least this share of the labelled distinct pairs, and at most the false-equivalent rate of the
# distinct pairs it answered, labelled or observed, judged equivalent.
INPUT_FLOOR = 0.8


def calibration_floors(key: str, labelled_distinct: list[str], answers: dict, confirmed: dict, observed: dict, alpha: float) -> dict:
    """One assessor model against the calibration floors. ``answers`` and ``confirmed`` hold, per
    labelled pair, each model's answer without problems and whether execution confirmed its input;
    ``observed`` holds each observed pair's answers without problems."""
    found = sum(1 for pid in labelled_distinct if (confirmed.get(pid) or {}).get(key) is True)
    verdicts = [(answers.get(pid) or {})[key].get("verdict") for pid in labelled_distinct if key in (answers.get(pid) or {})]
    verdicts += [given[key].get("verdict") for given in observed.values() if key in (given or {})]
    equivalent = verdicts.count("equivalent")
    return {
        "confirmed": found, "equivalent_on_distinct": equivalent, "distinct_answered": len(verdicts),
        "met": found >= INPUT_FLOOR * len(labelled_distinct) and equivalent <= alpha * len(verdicts),
    }


def ladder_below_floors(assessors: list[dict], complete: set, labelled_distinct: list[str], answers: dict, confirmed: dict, observed: dict, alpha: float) -> set[str]:
    """The models, among those that answered every labelled pair, that miss the calibration floors:
    they answer no new question for their assessor, and at a level of a ladder the calibration asks
    the next level. What they answered before stays in the judgements it is part of."""
    return {
        row["key"] for row in assessors
        if row["key"] in complete and not calibration_floors(row["key"], labelled_distinct, answers, confirmed, observed, alpha)["met"]
    }


def calibration_search(assessors: list[dict], below) -> set[str]:
    """The assessor models a calibration asks: every model listed at one level and, of a model whose
    Effort is a ladder of levels, only its lowest level not seen missing the floors (``below``). A
    new model so climbs one level at a time and stops at the first that meets them, and no level
    above that one is paid for."""
    asked, climbed = set(), set()
    for row in assessors:
        ladder = (row["assessor"], row["backend"], row["model"])
        if not row.get("levels"):
            if row["key"] not in below:
                asked.add(row["key"])
        elif ladder not in climbed and row["key"] not in below:
            asked.add(row["key"])
            climbed.add(ladder)
    return asked


def assessor_configurations(assessors: list[dict], usable) -> list[list[str]]:
    """Every combination of models that can judge a survivor, one usable model per assessor that has
    one, the first models first. An assessor none of whose models may answer takes no part; a
    combination needs at least two assessors from at least two model families, else there is none."""
    choices = [[row["key"] for row in models if row["key"] in usable] for models in assessor_seats(assessors).values()]
    choices = [choice for choice in choices if choice]
    if len(choices) < 2:
        return []

    def family(key: str) -> str:
        return model_family(key.split(":", 1)[1].split("@", 1)[0])

    return [list(combination) for combination in itertools.product(*choices) if len({family(key) for key in combination}) >= 2]


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


def answered_prices(rows: list[dict]) -> dict[tuple[str, bool], float]:
    """The most expensive answered call of each role, with tools and without, in ledger rows."""
    prices: dict[tuple[str, bool], float] = {}
    for row in rows:
        if row.get("outcome") == "ok" and row.get("list_usd") is not None and row.get("role") != "probe":
            key = (str(row.get("role")), "tools_used" in row)
            prices[key] = max(prices.get(key, 0.0), float(row["list_usd"]))
    return prices


def price_cap(budget: dict, prices: dict, role: str, tools: bool) -> float:
    """The list-price cap of a call of one role: the Test Plan's cap, or ``CAP_FACTOR`` times the most
    expensive answered call of the role, whichever is larger."""
    floor = float(budget["usd_per_tool_call" if tools else "usd_per_call"])
    return round(max(floor, CAP_FACTOR * prices.get((role, tools), 0.0)), 2)


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
        # (role, backend, model, level) the run must skip, with why: a model at a level that has not
        # passed its role's canaries. The level is empty for a model whose level no flag sets.
        self.blocked: dict[tuple[str, str, str, str], str] = {}
        # (backend, quota pool) whose quota rejected a call in this run.
        self.rejected_models: dict[tuple[str, str], str] = {}
        # (backend, smaller quota pool): its calls in the seven days before the run, read from the
        # ledger once and counted on as the run reserves calls, since the pool reports no window.
        self.pool_calls: dict[tuple[str, str], int] = {}
        self.versions: dict[str, str] = {}
        self.rows: list[dict] = []
        # The most expensive answered call of each role, read from the ledger once and raised as the
        # run's own calls are answered: what a call's price cap is measured against.
        self.prices: dict[tuple[str, bool], float] | None = None
        # Several calls may run at once (call_many): the budget, the windows and the ledger change
        # under one lock. Each quota pool finds how many calls it takes at a time the way TCP finds
        # its window: it starts at the Test Plan's parallel calls, doubles while every call at the
        # limit is answered (slow start), grows by one after its first overload answer and halves
        # on every overload answer, never above the Test Plan's ceiling nor below one.
        self.lock = threading.RLock()
        self.parallel = max(1, int(budget.get("parallel_calls", 1)))
        self.parallel_max = max(self.parallel, int(budget.get("parallel_calls_max", self.parallel)))
        self.turns = threading.Condition(self.lock)
        self.in_flight: dict[str, int] = {}
        self.limits: dict[str, int] = {}
        self.slow_start: dict[str, bool] = {}
        self.at_limit: dict[str, int] = {}
        # Every halving opens a new epoch: an answer to a call made before it is old news.
        self.epochs: dict[str, int] = {}
        # Antigravity accounts agm keeps: their quotas read once per run, the (backend, account, quota)
        # spent, and the account agy used before, put back when the run ends. A quota spent until a
        # time a rejection named stays spent until then, in this run and the next.
        self.agy_accounts: dict[str, dict] = {}
        self.exhausted: set[tuple[str, str, str]] = set()
        self.quota_resets: dict[tuple[str, str, str], str] = {}
        self.agy_original: dict[str, str] = {}
        # Claude sign-ins whose windows had no room left in this run.
        self.full_profiles: dict[str, set[str]] = {}

    def concurrency_pool(self, name: str, model: str) -> str:
        """What a limit on simultaneous calls applies to: the whole account where its plan window is
        one, otherwise the quota pool the model draws on."""
        return name if getattr(self.backend(name), "account_windows", False) else f"{name}:{self.quota_pool(name, model)}"

    def enter(self, pool: str) -> tuple[int, int, int]:
        """Wait for a free place in the pool; return how many calls it runs now, its limit and epoch."""
        with self.turns:
            self.limits.setdefault(pool, self.parallel)
            self.epochs.setdefault(pool, 0)
            while self.in_flight.get(pool, 0) >= self.limits[pool]:
                self.turns.wait()
            self.in_flight[pool] = self.in_flight.get(pool, 0) + 1
            return self.in_flight[pool], self.limits[pool], self.epochs[pool]

    def leave(self, pool: str, epoch: int, overloaded: bool, answered_at_limit: bool) -> None:
        """Free the place and adjust the pool's limit: halve it on an overload answer; after as many
        answered calls made at the limit as the limit, double it or, after an overload, add one.
        Calls made below the limit say nothing about more, and an answer to a call made before the
        last halving says nothing new: one burst of overload halves the limit once, as in TCP."""
        with self.turns:
            self.in_flight[pool] -= 1
            if epoch == self.epochs[pool]:
                if overloaded:
                    self.limits[pool] = max(1, self.limits[pool] // 2)
                    self.slow_start[pool] = False
                    self.at_limit[pool] = 0
                    self.epochs[pool] += 1
                elif answered_at_limit:
                    self.at_limit[pool] = self.at_limit.get(pool, 0) + 1
                    if self.at_limit[pool] >= self.limits[pool]:
                        grown = self.limits[pool] * 2 if self.slow_start.get(pool, True) else self.limits[pool] + 1
                        self.limits[pool] = min(self.parallel_max, grown)
                        self.at_limit[pool] = 0
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
            if self.prices is not None:
                for key, price in answered_prices([row]).items():
                    self.prices[key] = max(self.prices.get(key, 0.0), price)
            return row

    def price_cap(self, role: str, tools: bool) -> float:
        """The list-price cap of this role's next call (``price_cap``)."""
        with self.lock:
            if self.prices is None:
                self.prices = answered_prices(read_ledger(self.ledger_path))
            return price_cap(self.budget, self.prices, role, tools)

    def probe(self, name: str) -> str:
        """Availability and windows of a backend, read once per run with its cheapest model."""
        with self.lock:
            return self._probe(name)

    def accounts(self, name: str):
        """The Antigravity accounts agm keeps for a backend, or None where there is no agm."""
        accounts = getattr(self.backend(name), "accounts", None)
        return accounts if accounts is not None and getattr(accounts, "executable", "") else None

    def read_accounts(self, name: str) -> None:
        """Read once per run what each account's quotas have left and which one agy uses; the run puts
        that one back when it ends."""
        if name in self.agy_accounts:
            return
        accounts = self.accounts(name)
        snapshot = accounts.snapshot() if accounts else {}
        self.agy_accounts[name] = snapshot
        active = next((alias for alias, row in snapshot.items() if row.get("agy")), "")
        if snapshot:
            self.backend(name).profile = active
            self.agy_original[name] = active
            atexit.register(self.restore_accounts)
            # agm reads each account's short window, not the week: a rejection that named when its
            # quota resets keeps that quota spent until then on its account, so no call is spent on
            # finding out again; only a rejection whose account agy's credential store confirmed.
            now = datetime.fromisoformat(self.clock())
            labels = {account_label(alias) or alias: alias for alias in snapshot}
            for row in read_ledger(self.ledger_path):
                if row.get("backend") != name or not row.get("account_verified"):
                    continue
                # An account Antigravity did not let in a little while ago is skipped without a call.
                if row.get("outcome") == "unavailable" and str(row.get("reason") or "").startswith(INELIGIBLE):
                    at = datetime.fromisoformat(str(row.get("at")))
                    alias = labels.get(str(row.get("account") or ""))
                    if alias and now - at < BARRED_FOR:
                        self.exhausted.update((name, alias, family) for family in QUOTA_FAMILIES)
                    continue
                if row.get("outcome") != "rejected":
                    continue
                resets = quota_resets_at(str(row.get("reason") or ""), str(row.get("at") or ""))
                if resets is None or resets <= now:
                    continue
                self.spend_quota(name, str(row.get("model") or ""), labels.get(str(row.get("account") or "")), str(row.get("reason") or ""), resets)

    def confirm_refusal(self, name: str, used: str, model: str, invocation) -> bool | None:
        """For an Antigravity call its account refused (``refused_account``): whether agy's credential
        store still holds the account the call used. If it does, what the account refused counts as
        spent (the model's quota, or every quota of an account Antigravity does not let in) and the
        next check moves agy to another account; if the store holds another account (a person moved
        agy meanwhile), the run follows it and blames none. None where the call was not refused or no
        agm keeps accounts. The accounts are alike: which one answers is only a matter of which can."""
        if not (refused_account(invocation) and self.agy_accounts.get(name)):
            return None
        accounts = self.accounts(name)
        actual = accounts.cli_address()
        verified = actual == accounts.addresses.get(used, used)
        if actual and not verified:
            self.backend(name).profile = accounts.alias_of(actual)
        elif invocation.outcome == "unavailable":
            self.exhausted.update((name, used, family) for family in QUOTA_FAMILIES)
        else:
            self.spend_quota(name, model, used, invocation.reason, quota_resets_at(invocation.reason, self.clock()))
        return verified

    def spend_quota(self, name: str, model: str, alias: str | None, reason: str, resets: datetime | None = None) -> None:
        """Mark a model's quota spent on the account that refused it, with the time it resets when the
        refusal said."""
        if not alias:
            return
        family = quota_family(model)
        self.exhausted.add((name, alias, family))
        if resets is not None:
            self.quota_resets[(name, alias, family)] = resets.isoformat(timespec="seconds").replace("+00:00", "Z")

    def quota_left(self, name: str, alias: str, model: str) -> int:
        """What an account has left of the quota a model draws on, in percent; -1 once spent in this run."""
        family = quota_family(model)
        if (name, alias, family) in self.exhausted:
            return -1
        return int(((self.agy_accounts.get(name) or {}).get(alias) or {}).get(family, 0))

    def choose_account(self, name: str, model: str) -> str:
        """Keep the account agy uses while its quota for the model is above what the Test Plan keeps free,
        else move agy alone to the account with the most left. Why no account can take the call, or an
        empty string."""
        snapshot = self.agy_accounts.get(name) or {}
        if not snapshot:
            return ""
        backend = self.backend(name)
        floor = 100 * float(self.budget.get("agy_quota_floor", 0.0))
        if backend.profile in snapshot and self.quota_left(name, backend.profile, model) > floor:
            return ""
        best = max(sorted(snapshot), key=lambda alias: self.quota_left(name, alias, model))
        if self.quota_left(name, best, model) <= floor:
            resets = sorted(at for (owner, _alias, family), at in self.quota_resets.items() if owner == name and family == quota_family(model))
            if resets:
                return f"no Antigravity account has {quota_family(model)} quota left; the first one refused resets at {resets[0]}"
            return f"no Antigravity account has more than the {floor:.0f}% of its {quota_family(model)} quota the Test Plan keeps free"
        if not self.accounts(name).switch(best):
            return "agm could not move agy to an account with quota left"
        backend.profile = best
        return ""

    def restore_accounts(self) -> None:
        """Put agy back on the account it used before the run."""
        with self.lock:
            for name, alias in self.agy_original.items():
                backend, accounts = self.backend(name), self.accounts(name)
                if alias and backend.profile != alias and accounts and accounts.switch(alias):
                    backend.profile = alias

    def window_reason(self, name: str) -> str:
        """Why the windows of the sign-in a backend uses take no more calls, or an empty string."""
        windows = self.windows.get(name) or {}
        if windows.get("status") == "rejected":
            return "the plan's usage window rejects calls until it resets"
        for key, label in (("five_hour", "5-hour"), ("seven_day", "weekly")):
            used = windows.get(key)
            if used is not None and used >= self.budget[key]:
                return f"the {label} window is at {used:.0%}, at or above its {self.budget[key]:.0%} limit"
        return ""

    def switch_profile(self, name: str) -> bool:
        """Move a backend whose sign-in has no room left in its windows to another signed-in profile of
        the machine that has, probing each once; True once it uses one with room."""
        backend = self.backend(name)
        profiles = getattr(backend, "profiles", None)
        if not callable(profiles):
            return False
        full = self.full_profiles.setdefault(name, set())
        full.add(backend.profile)
        for other in profiles():
            if other in full:
                continue
            backend.profile = other
            system, prompt = "Answer with one word.", "Reply with OK."
            invocation = backend.invoke(model=PROBE_MODELS[name], system=system, prompt=prompt, schema=None, usd_cap=0.05, timeout=120)
            self.windows[name] = invocation.windows if invocation.outcome != "rejected" else {**(invocation.windows or {}), "status": "rejected"}
            self.record({
                "call_id": new_call_id(), "role": "probe", "purpose": "probe", "contract_id": "", "subject": "",
                "backend": name, "account": self.account(name), "backend_version": invocation.backend_version or self.versions.get(name, ""),
                "model": PROBE_MODELS[name], "outcome": invocation.outcome, "reason": invocation.reason, "prompt_sha256": sha256_text(prompt),
                "system_sha256": sha256_text(system), "schema_sha256": "", "response_sha256": "",
                "tokens": invocation.tokens, "list_usd": invocation.list_usd, "seconds": invocation.seconds, "windows": invocation.windows,
            })
            if invocation.outcome == "ok" and not self.window_reason(name):
                return True
            full.add(other)
        return False

    def has_room(self, pool: str) -> bool:
        """Whether a pool runs fewer calls now than it takes."""
        with self.turns:
            return self.in_flight.get(pool, 0) < self.limits.get(pool, self.parallel)

    def could_take(self, role: str, entry: dict, step: int) -> bool:
        """Whether a model of the role could take a call at once: its level passed its canaries, its
        backend is available, the guard would not defer it and its pool has room."""
        name, model = entry["backend"], entry["model"]
        with self.lock:
            if (role, name, model, self.level(role, entry, step)) in self.blocked or self._probe(name) or self.deferral(name, model):
                return False
        return self.has_room(self.concurrency_pool(name, model))

    def _probe(self, name: str) -> str:
        if name in self.availability:
            return self.availability[name]
        backend = self.backend(name)
        # With several Antigravity accounts the probe itself runs on one with quota left, and an
        # account Antigravity does not let in hands the probe on to the next, as it hands any call.
        self.read_accounts(name)
        system, prompt = "Answer with one word.", "Reply with OK."
        for turn in range(max(1, len(self.agy_accounts.get(name) or {}))):
            self.choose_account(name, PROBE_MODELS[name])
            used = str(getattr(backend, "profile", "") or "")
            invocation = backend.invoke(model=PROBE_MODELS[name], system=system, prompt=prompt, schema=None, usd_cap=0.05, timeout=120)
            verified = self.confirm_refusal(name, used, PROBE_MODELS[name], invocation) if invocation.outcome == "unavailable" else None
            self.versions[name] = invocation.backend_version or backend.version()
            self.windows[name] = invocation.windows
            self.record({
                "call_id": new_call_id(), "role": "probe", "purpose": "probe", "contract_id": "", "subject": "",
                "backend": name, "account": account_label(used), "backend_version": self.versions[name], "model": PROBE_MODELS[name],
                "outcome": invocation.outcome, "reason": invocation.reason, "prompt_sha256": sha256_text(prompt),
                "system_sha256": sha256_text(system), "schema_sha256": "", "response_sha256": "",
                "tokens": invocation.tokens, "list_usd": invocation.list_usd, "seconds": invocation.seconds,
                "windows": invocation.windows,
                **({"account_verified": verified} if verified is not None else {}),
                # What each Antigravity account had left when the run began, each named by a digest.
                **({"quotas": {
                    account_label(alias) or alias: {family: row.get(family) for family in ("gemini-pro", "gemini-flash", "other")}
                    for alias, row in sorted((self.agy_accounts.get(name) or {}).items())
                }} if self.agy_accounts.get(name) and turn == 0 else {}),
            })
            if verified is None:
                break
        if invocation.outcome == "rejected":
            # A full window is a budget matter, not a missing backend: the guard defers every call.
            self.reject(name, PROBE_MODELS[name], invocation)
        unusable = invocation.outcome not in {"ok", "rejected"}
        self.availability[name] = (invocation.reason or invocation.outcome) if unusable else ""
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
        # Where agm reads the accounts' quotas, they decide, and the ledger's count of the smaller pool is not needed.
        if model and self.agy_accounts.get(name):
            return self.choose_account(name, model)
        if model and (name, self.quota_pool(name, model)) in self.rejected_models:
            return f"the {self.quota_pool(name, model)} quota of {name} rejects calls until it resets"
        pool = self.smaller_pool(name, model) if model else ""
        limit = self.budget.get("pool_calls_per_week")
        if pool and limit is not None and self.pool_week(name, pool) >= limit:
            return f"the {pool} quota of {name} took {self.pool_week(name, pool)} calls in the last 7 days, at or above its limit of {int(limit)}"
        # A sign-in with no room left hands over to another of the machine's that has some.
        if self.window_reason(name):
            self.switch_profile(name)
        return self.window_reason(name)

    def call(self, role: str, *, purpose: str, contract_id: str, subject: str, system: str, prompt: str, schema: dict, response_dir: Path, workspace: Workspace | None = None) -> tuple[dict, dict | None]:
        """Try the role's backends in order. Return the ledger row of the last attempt and, when a
        backend answered within its schema, the stored response.
        """
        row, response, _attempts = self.call_with_attempts(
            role, purpose=purpose, contract_id=contract_id, subject=subject, system=system, prompt=prompt, schema=schema, response_dir=response_dir, workspace=workspace,
        )
        return row, response

    def call_many(self, requests: list[dict]) -> list[tuple[dict, dict | None, list[dict]]]:
        """Make independent calls at once, each as ``call_with_attempts`` makes it, and return their
        results in the order asked. Each backend still takes at most the parallel calls at a time,
        and every call is guarded and ledgered on its own."""
        if len(requests) <= 1 or self.parallel_max == 1:
            return [self.call_with_attempts(**request) for request in requests]
        # Enough workers for every pool at its ceiling (Antigravity has two pools); each pool's own
        # limit decides how many of them call at once.
        with ThreadPoolExecutor(max_workers=min(len(requests), self.parallel_max * (len(BACKENDS) + 1))) as pool:
            return list(pool.map(lambda request: self.call_with_attempts(**request), requests))

    def level(self, role: str, entry: dict, step: int) -> str:
        """The level a model answers at on a question's ``step``: of the levels of its ladder its
        canaries let answer, the one that many steps up, or the top one; the first listed when none may
        (its block is then the reason its attempt records); empty when no flag sets its level."""
        levels = list(entry.get("effort") or [])
        open_levels = [level for level in levels if (role, entry["backend"], entry["model"], level) not in self.blocked] or levels[:1]
        return open_levels[min(step, len(open_levels) - 1)] if open_levels else ""

    def call_with_attempts(self, role: str, *, purpose: str, contract_id: str, subject: str, system: str, prompt: str, schema: dict, response_dir: Path, workspace: Workspace | None = None, step: int = 0) -> tuple[dict, dict | None, list[dict]]:
        """``call``, and the ledger rows of every attempt it made, in order. With a workspace the call
        works in that copy of the project with the tools its permissions allow. ``step`` counts the
        answers to this question the cascade rejected before: a model with a ladder of levels answers
        that many levels up it (``level``)."""
        schema_sha = sha256_text(stable_json(schema))
        attempts = []
        # The role's models in order. A model whose call reached its price cap is asked once more at
        # twice the cap: a hard question gets its answer, a call that runs away is stopped again, and
        # the next model is asked.
        cap = self.price_cap(role, workspace is not None)
        queue = [(entry, cap, False) for entry in self.roles[role]]
        while queue:
            entry, usd_cap, again = queue.pop(0)
            # Two channels at once: while the model a call would use first runs as many calls as its pool
            # takes, a later model of the role on another pool that has room answers, and the first stays next.
            here = self.concurrency_pool(entry["backend"], entry["model"])
            if not self.has_room(here):
                for index, (other, other_cap, other_again) in enumerate(queue):
                    if self.concurrency_pool(other["backend"], other["model"]) != here and self.could_take(role, other, step):
                        queue.pop(index)
                        queue.insert(0, (entry, usd_cap, again))
                        entry, usd_cap, again = other, other_cap, other_again
                        break
            name, model = entry["backend"], entry["model"]
            effort = self.level(role, entry, step)
            base = {
                "call_id": new_call_id(), "role": role, "purpose": purpose, "contract_id": contract_id, "subject": subject,
                "backend": name, "account": self.account(name), "model": model, "effort": effort,
                "prompt_sha256": sha256_text(prompt), "system_sha256": sha256_text(system),
                "schema_sha256": schema_sha, "response_sha256": "",
            }
            # The guard decides and reserves the call under the lock, so calls made at once never
            # overrun the run's limit or a window another call has just reported full.
            with self.lock:
                skipped = self.blocked.get((role, name, model, effort))
                if skipped:
                    attempts.append(self.record({**base, "backend_version": self.versions.get(name, ""), "outcome": "unavailable", "reason": skipped, "tokens": {}, "list_usd": None, "seconds": 0.0, "windows": None}))
                    continue
                unavailable = self._probe(name)
                if unavailable:
                    attempts.append(self.record({**base, "backend_version": self.versions.get(name, ""), "outcome": "unavailable", "reason": unavailable, "tokens": {}, "list_usd": None, "seconds": 0.0, "windows": self.windows.get(name)}))
                    continue
                deferred = self.deferral(name, model)
                # The guard may have moved agy to another account: the row names the one the call uses.
                base["account"] = self.account(name)
                used = str(getattr(self.backend(name), "profile", "") or "")
                if deferred:
                    attempts.append(self.record({**base, "backend_version": self.versions.get(name, ""), "outcome": "deferred", "reason": deferred, "tokens": {}, "list_usd": None, "seconds": 0.0, "windows": self.windows.get(name)}))
                    continue
                self.calls += 1
                pool = self.smaller_pool(name, model)
                if pool:
                    self.pool_calls[(name, pool)] = self.pool_week(name, pool) + 1
            pool = self.concurrency_pool(name, model)
            in_flight, limit, epoch = self.enter(pool)
            invocation = None
            try:
                invocation = self.backend(name).invoke(
                    model=model, system=system, prompt=prompt, schema=schema, workspace=workspace, usd_cap=usd_cap, effort=effort,
                )
            finally:
                answered = invocation is not None and invocation.outcome in {"ok", "invalid"}
                self.leave(pool, epoch, invocation is not None and overloaded(invocation), answered and in_flight == limit)
            with self.lock:
                if invocation.windows is not None:
                    self.windows[name] = invocation.windows
                verified = self.confirm_refusal(name, used, model, invocation)
                if verified is None and invocation.outcome == "rejected":
                    self.reject(name, model, invocation)
                version = invocation.backend_version or self.versions.get(name, "")
            response = None
            if invocation.outcome == "ok":
                response = {
                    "schema": RESPONSE_SCHEMA, "call_id": base["call_id"], "role": role, "purpose": purpose,
                    "contract_id": contract_id, "subject": subject, "backend": name, "backend_version": version,
                    "model": model, "effort": effort, "system": system, "prompt": prompt, "answer_schema": schema,
                    "prompt_sha256": base["prompt_sha256"], "system_sha256": base["system_sha256"], "schema_sha256": schema_sha,
                    "structured": invocation.structured,
                }
                if workspace is not None:
                    response["workspace"] = {"write": workspace.write, "command": workspace.command, "tools_used": invocation.tools_used, "denied": invocation.denied}
                base["response_sha256"] = response_sha256(response)
                response_dir.mkdir(parents=True, exist_ok=True)
                (response_dir / f"{base['call_id']}.json").write_text(json.dumps(response, indent=2, sort_keys=True) + "\n")
            # How busy the backend was, for deciding its parallel limit later from what happened.
            row = self.record({
                **base, "backend_version": version, "outcome": invocation.outcome, "reason": invocation.reason,
                "tokens": invocation.tokens, "list_usd": invocation.list_usd, "seconds": invocation.seconds,
                "windows": invocation.windows, "in_flight": in_flight, "parallel_limit": limit,
                "backed_off": overloaded(invocation), "usd_cap": usd_cap,
                **({"tools_used": invocation.tools_used, "denied": invocation.denied} if workspace is not None else {}),
                **({"account_verified": verified} if verified is not None else {}),
            })
            attempts.append(row)
            if response is not None:
                return row, response, attempts
            if invocation.outcome == "capped" and not again:
                queue.insert(0, (entry, round(2 * usd_cap, 2), True))
                continue
            if refused_account(invocation) and self.agy_accounts.get(name):
                # The same model on another account, if one has quota left; else the guard defers it.
                queue.insert(0, (entry, usd_cap, again))
                continue
            if invocation.outcome in {"rejected", "unavailable", "capped"}:
                continue
            return row, None, attempts
        return attempts[-1], None, attempts

    def summary(self) -> dict:
        return {"run_id": self.run_id, **spend(self.rows)}


def refused_account(invocation) -> bool:
    """An Antigravity call its account refused: its quota spent, or the account not let in at all."""
    return invocation.outcome == "rejected" or (invocation.outcome == "unavailable" and str(invocation.reason or "").startswith(INELIGIBLE))


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
