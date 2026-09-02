"""Build the complete local engineering portal from one pytest execution."""

from __future__ import annotations

import html
import json
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

from defusedxml import ElementTree

ALLURE_VERSION = "3.16.0"
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
BUILD = DOCS / "_build" / "portal"
RAW_RESULTS = DOCS / "_build" / "portal-allure-results"
CURATED_RESULTS = DOCS / "_build" / "portal-allure-curated"
BDD_RESULTS = DOCS / "_build" / "portal-allure-bdd"
REPORT_ROOT = DOCS / "_build" / "portal-allure-reports"
MATRIX_HTML = DOCS / "_build" / "portal-verification-matrix.html"
JUNIT = DOCS / "_traceability" / "local-pytest.xml"
NEEDS_JSON = BUILD / "needs.json"


def run(*args: str) -> None:
    """Run one portal build command from the repository root."""
    subprocess.run(args, cwd=ROOT, check=True)


def _junit_metadata() -> dict[str, dict[str, list[str]]]:
    metadata: dict[str, dict[str, list[str]]] = {}
    for case in ElementTree.parse(JUNIT).getroot().iter("testcase"):
        classname = case.attrib.get("classname", "")
        name = case.attrib.get("name", "").split("[", 1)[0]
        key = f"{classname}#{name}"
        values = metadata.setdefault(key, {})
        for prop in case.findall("./properties/property"):
            prop_name = prop.attrib.get("name")
            prop_value = prop.attrib.get("value")
            if prop_name and prop_value:
                values.setdefault(prop_name, []).append(prop_value)
    return metadata


def _verification_ids(reference: str) -> list[str]:
    return [
        item.strip().split("[", 1)[0] for item in reference.split(",") if item.strip()
    ]


def _junit_verification_counts() -> dict[str, dict[str, tuple[int, int]]]:
    totals: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    for case in ElementTree.parse(JUNIT).getroot().iter("testcase"):
        properties = {
            prop.attrib.get("name"): prop.attrib.get("value")
            for prop in case.findall("./properties/property")
        }
        kind = properties.get("verification_kind")
        verifies = properties.get("verifies")
        if not kind or not verifies:
            continue
        failed = case.find("failure") is not None or case.find("error") is not None
        skipped = case.find("skipped") is not None
        for requirement_id in _verification_ids(verifies):
            totals[requirement_id][kind][0] += 1
            if not failed and not skipped:
                totals[requirement_id][kind][1] += 1
    return {
        requirement_id: {
            kind: (counts[0], counts[1]) for kind, counts in by_kind.items()
        }
        for requirement_id, by_kind in totals.items()
    }


def _needs() -> dict[str, dict[str, object]]:
    """Read the authoritative graph produced by the strict Sphinx build."""
    data = json.loads(NEEDS_JSON.read_text(encoding="utf-8"))
    current_version = str(data["current_version"])
    return data["versions"][current_version]["needs"]


def _requirement_catalog() -> list[dict[str, object]]:
    """Return requirement presentation data from canonical ``needs.json``."""
    catalog: list[dict[str, object]] = []
    for need in _needs().values():
        kind = str(need.get("type", ""))
        if kind not in {"req", "treq"}:
            continue
        artifacts = need.get("required_evidence")
        docname = str(need.get("docname", "requirements/index"))
        catalog.append(
            {
                "id": str(need["id"]),
                "kind": kind,
                "title": str(need.get("title", need["id"])),
                "status": str(need.get("status", "")),
                "artifacts": list(artifacts) if isinstance(artifacts, list) else [],
                "page": f"{docname}.html",
            }
        )
    return sorted(catalog, key=lambda item: str(item["id"]))


def _requirement_titles() -> dict[str, str]:
    return {str(item["id"]): str(item["title"]) for item in _requirement_catalog()}


def _add_label(result: dict[str, object], name: str, value: str) -> None:
    labels = result.get("labels")
    if not isinstance(labels, list):
        labels = []
        result["labels"] = labels
    if {"name": name, "value": value} not in labels:
        labels.append({"name": name, "value": value})


def _label_values(result: dict[str, object], name: str) -> list[str]:
    labels = result.get("labels", [])
    if not isinstance(labels, list):
        return []
    return [
        str(label["value"])
        for label in labels
        if isinstance(label, dict) and label.get("name") == name and "value" in label
    ]


def _human_title(name: str) -> str:
    base, separator, parameter = name.partition("[")
    title = base.removeprefix("test_").replace("_", " ").strip().capitalize()
    return f"{title} — {parameter.rstrip(']')}" if separator else title


def _attachment_sources(result: dict[str, object]) -> set[str]:
    sources: set[str] = set()

    def visit(items: object) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            attachments = item.get("attachments", [])
            if isinstance(attachments, list):
                for attachment in attachments:
                    if isinstance(attachment, dict) and attachment.get("source"):
                        sources.add(str(attachment["source"]))
            visit(item.get("steps"))

    visit([result])
    return sources


def _enrich_result(
    result: dict[str, object],
    properties: dict[str, list[str]],
    requirement_titles: dict[str, str],
) -> str:
    for kind in properties.get("verification_kind", []):
        _add_label(result, "layer", kind)
    for reference in properties.get("verifies", []):
        for requirement_id in _verification_ids(reference):
            _add_label(result, "requirement", requirement_id)
            title = requirement_titles.get(requirement_id, requirement_id)
            _add_label(result, "requirement_view", f"{requirement_id} — {title}")

    layer = (_label_values(result, "layer") or ["other"])[0]
    if layer == "bdd":
        return layer

    result["name"] = _human_title(str(result.get("name", "")))
    requirements = ", ".join(_label_values(result, "requirement"))
    description = f"{layer.title()} verification"
    if requirements:
        description += f" for {requirements}."
    else:
        description += "."
    full_name = str(result.get("fullName", ""))
    if full_name:
        description += f"\n\nExecution source: `{full_name}`"
    result["description"] = description
    return layer


def _copy_result(
    result_path: Path,
    result: dict[str, object],
    destination: Path,
) -> None:
    (destination / result_path.name).write_text(
        json.dumps(result, ensure_ascii=False),
        encoding="utf-8",
    )
    for source in _attachment_sources(result):
        raw_source = RAW_RESULTS / source
        curated_source = CURATED_RESULTS / source
        if raw_source.exists():
            shutil.copy2(raw_source, destination / source)
        elif curated_source.exists() and destination != CURATED_RESULTS:
            shutil.copy2(curated_source, destination / source)


def curate_allure_results() -> None:
    """Create human-facing Allure input without fixture setup/teardown noise."""
    metadata = _junit_metadata()
    requirement_titles = _requirement_titles()
    for directory in (CURATED_RESULTS, BDD_RESULTS):
        shutil.rmtree(directory, ignore_errors=True)
        directory.mkdir(parents=True)

    for result_path in RAW_RESULTS.glob("*-result.json"):
        result = json.loads(result_path.read_text(encoding="utf-8"))
        properties = metadata.get(str(result.get("fullName", "")), {})
        layer = _enrich_result(result, properties, requirement_titles)
        _copy_result(result_path, result, CURATED_RESULTS)
        if layer == "bdd":
            _copy_result(result_path, result, BDD_RESULTS)


VERIFICATION_KINDS = ("bdd", "unit", "integration", "property", "e2e")


def _matrix_cell(
    counts: tuple[int, int] | None,
    *,
    required: bool,
) -> str:
    if counts is None:
        if required:
            return '<span class="status missing">missing</span>'
        return '<span class="status none">—</span>'
    total, passed = counts
    if passed == total:
        css_class = "pass" if required else "extra"
        label = f"{passed}/{total}"
        return f'<span class="status {css_class}">{label}</span>'
    return f'<span class="status fail">{passed}/{total}</span>'


def _matrix_table(
    rows: list[dict[str, object]],
    counts: dict[str, dict[str, tuple[int, int]]],
) -> str:
    body: list[str] = []
    for row in rows:
        requirement_id = str(row["id"])
        title = html.escape(str(row["title"]))
        status = html.escape(str(row["status"]))
        page = html.escape(str(row["page"]))
        artifacts = {str(value) for value in row["artifacts"]}  # type: ignore[arg-type]
        cells = [
            _matrix_cell(
                counts.get(requirement_id, {}).get(kind),
                required=kind in artifacts,
            )
            for kind in VERIFICATION_KINDS
        ]
        body.append(
            "<tr>"
            f'<th scope="row"><a href="{page}#{requirement_id}" target="_top">'
            f"{requirement_id}</a><small>{title} · {status}</small></th>"
            + "".join(f"<td>{cell}</td>" for cell in cells)
            + "</tr>"
        )
    headers = "".join(f"<th>{kind.upper()}</th>" for kind in VERIFICATION_KINDS)
    return (
        '<div class="matrix-scroll"><table class="matrix"><thead><tr>'
        f"<th>Requirement</th>{headers}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def generate_verification_matrix() -> None:
    """Render a compact requirement-by-verification coverage overview."""
    counts = _junit_verification_counts()
    catalog = _requirement_catalog()
    requirements = [row for row in catalog if row["kind"] == "req"]
    constraints = [row for row in catalog if row["kind"] == "treq"]
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Verification matrix</title>
<style>
  :root {{
    color-scheme: light dark;
    font-family: system-ui, sans-serif;
  }}
  body {{
    margin: 0;
    padding: 0.75rem;
    background: Canvas;
    color: CanvasText;
  }}
  h2 {{ margin: 0.5rem 0 0.75rem; font-size: 1rem; }}
  p {{ margin: 0 0 1rem; color: GrayText; }}
  .matrix-scroll {{
    width: 100%;
    overflow-x: auto;
    overscroll-behavior-inline: contain;
  }}
  .matrix {{
    width: 100%;
    min-width: 50rem;
    border-collapse: collapse;
    font-size: 0.86rem;
  }}
  .matrix th, .matrix td {{
    border-bottom: 1px solid color-mix(in srgb, CanvasText 18%, transparent);
    padding: 0.5rem 0.65rem;
    text-align: center;
  }}
  .matrix thead th {{
    position: sticky;
    top: 0;
    background: Canvas;
    z-index: 2;
  }}
  .matrix th:first-child {{
    position: sticky;
    left: 0;
    width: 52%;
    min-width: 18rem;
    background: Canvas;
    text-align: left;
    z-index: 1;
  }}
  .matrix thead th:first-child {{ z-index: 3; }}
  .matrix tbody tr:hover {{
    background: color-mix(in srgb, Highlight 10%, transparent);
  }}
  .matrix a {{ color: LinkText; text-decoration: none; font-weight: 650; }}
  .matrix small {{
    display: block;
    margin-top: 0.15rem;
    color: GrayText;
    font-weight: 400;
  }}
  .status {{
    display: inline-block;
    min-width: 3.2rem;
    padding: 0.18rem 0.45rem;
    border-radius: 999px;
    font-variant-numeric: tabular-nums;
  }}
  .pass {{ background: color-mix(in srgb, #2eae60 24%, transparent); }}
  .fail, .missing {{
    background: color-mix(in srgb, #d64545 25%, transparent);
  }}
  .extra {{ background: color-mix(in srgb, #4f8ddf 20%, transparent); }}
  .none {{ color: GrayText; }}
  .legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.8rem;
    margin-bottom: 1rem;
    font-size: 0.8rem;
    color: GrayText;
  }}
</style>
</head>
<body>
<p>
  Requested verification is shown as pass/total. A dash means that verification
  layer is not requested for that object.
</p>
<div class="legend">
  <span><b>green</b> requested and passing</span>
  <span><b>red</b> missing or failing</span>
  <span><b>blue</b> additional evidence</span>
</div>
<h2>Product requirements</h2>
{_matrix_table(requirements, counts)}
<h2>Engineering constraints</h2>
{_matrix_table(constraints, counts)}
</body>
</html>
"""
    MATRIX_HTML.write_text(document, encoding="utf-8")


def generate_report(source: Path, name: str, group_by: str, report_name: str) -> Path:
    """Generate one Allure perspective from the curated result corpus."""
    output = REPORT_ROOT / name
    run(
        "npx",
        "--yes",
        f"allure@{ALLURE_VERSION}",
        "awesome",
        str(source),
        "--output",
        str(output),
        "--report-name",
        report_name,
        "--theme",
        "dark",
        "--group-by",
        group_by,
        "--single-file",
    )
    report = output / "index.html"
    document = report.read_text(encoding="utf-8")
    app_root = '<div id="app"></div>'
    if document.count(app_root) != 1:
        msg = f"Allure report shell changed unexpectedly: {report}"
        raise RuntimeError(msg)
    report.write_text(
        document.replace(app_root, '<main id="app"></main>'), encoding="utf-8"
    )
    return report


def main() -> None:
    """Build test evidence, documentation, and human-facing test perspectives."""
    if shutil.which("npx") is None:
        message = "npx is required to generate the Allure 3 test portal"
        raise SystemExit(message)

    for directory in (BUILD, RAW_RESULTS, CURATED_RESULTS, BDD_RESULTS, REPORT_ROOT):
        shutil.rmtree(directory, ignore_errors=True)
    MATRIX_HTML.unlink(missing_ok=True)
    JUNIT.parent.mkdir(parents=True, exist_ok=True)

    run(
        "uv",
        "run",
        "--no-sync",
        "pytest",
        f"--junitxml={JUNIT}",
        f"--alluredir={RAW_RESULTS}",
        "--clean-alluredir",
    )

    # Build the authoritative graph before derived presentation. The resulting
    # needs.json is the only requirement catalogue consumed by the views below.
    run(
        "uv",
        "run",
        "--no-sync",
        "sphinx-build",
        "-E",
        "-W",
        "--keep-going",
        "-D",
        "plot_gallery=0",
        "-b",
        "html",
        str(DOCS),
        str(BUILD),
    )

    curate_allure_results()
    generate_verification_matrix()
    reports = {
        "bdd": generate_report(
            BDD_RESULTS,
            "bdd",
            "epic,feature,rule",
            "llm-router executable specifications",
        ),
        "requirements": generate_report(
            CURATED_RESULTS,
            "requirements",
            "requirement_view,layer",
            "llm-router verification by requirement",
        ),
        "all": generate_report(
            CURATED_RESULTS,
            "all",
            "layer,parentSuite,suite",
            "llm-router all test results",
        ),
    }

    shutil.copy2(MATRIX_HTML, BUILD / "verification-matrix.html")
    target = BUILD / "test-results"
    for name, report in reports.items():
        destination = target / name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(report, destination / "index.html")
    shutil.copy2(reports["requirements"], target / "index.html")

    print("\nLocal engineering portal built successfully:")
    for page in (
        "index.html",
        "requirements/index.html",
        "requirements/maps.html",
        "specifications.html",
        "verification.html",
        "tests.html",
        "test-results/bdd/index.html",
        "test-results/requirements/index.html",
        "test-results/all/index.html",
    ):
        print((BUILD / page).resolve().as_uri())


if __name__ == "__main__":
    main()
