"""Shared Contract Evidence / Assurance monitor presentation system."""

# ruff: noqa: D103, E501, EM101, FBT001, PLR0913, PLR0917, TRY003

from __future__ import annotations

import html
import re


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def help_tip(text: str, *, focusable: bool = True) -> str:
    tabindex = ' tabindex="0"' if focusable else ""
    return f'<span class="help"{tabindex}>?<span class="help-tip">{esc(text)}</span></span>'


def status_class(status: str) -> str:
    return {"MET": "met", "NOT MET": "not-met", "UNKNOWN": "unknown", "N/A": "na"}.get(
        status, "unknown"
    )


def status_label(status: str) -> str:
    return {"MET": "PASS", "NOT MET": "FAIL", "UNKNOWN": "UNKNOWN", "N/A": "N/A"}.get(
        status, status
    )


def marker(actual: bool, target: bool) -> str:
    if actual and target:
        return '<span class="marker both">ACTUAL = TARGET</span>'
    result = []
    if actual:
        result.append('<span class="marker actual">ACTUAL</span>')
    if target:
        result.append('<span class="marker target">TARGET</span>')
    return "".join(result)


def scope_count(matched: int, total: int, status: str, label: str = "paths") -> str:
    shown_label = label
    if total == 1 and label == "paths":
        shown_label = "path"
    elif total == 1 and label == "evidence paths":
        shown_label = "evidence path"
    elif total == 1 and label == "model paths":
        shown_label = "model path"
    if status == "N/A":
        return f'<span class="scope-count na"><b>{total}</b><small>{esc(shown_label)}</small></span>'
    return f'<span class="scope-count {status_class(status)}"><b>{matched}/{total}</b><small>{esc(shown_label)}</small></span>'


def state_option_label(signal: str, option: str) -> str:
    if signal == "M&S validation":
        return {
            "N/A": "N/A",
            "L0": "L0",
            "L1": "L1",
            "L2": "L2",
            "L3": "L3",
            "L4": "L4",
            "UNKNOWN": "UNKNOWN",
            "NOT DECLARED": "NOT DECLARED",
        }.get(option, option)
    return option


def lane(
    label: str,
    options: list[str],
    actual_values: list[str],
    target: str,
    status: str,
    tip: str,
    matched: int,
    total: int,
    scope_label: str = "paths",
    extra_class: str = "",
) -> str:
    actual_set = set(actual_values)
    cells = []
    for option in options:
        is_actual = option in actual_set
        is_target = option == target
        selected = " selected" if is_actual or is_target else ""
        display = state_option_label(label, option)
        if status == "N/A" and option == "N/A":
            option_marker = '<span class="marker inactive">INACTIVE</span>'
        else:
            option_marker = marker(is_actual, is_target)
        cells.append(
            f'<span class="state-option{selected}"><span>{esc(display)}</span>{option_marker}</span>'
        )
    class_name = f"signal-card {status_class(status)}-signal {extra_class}".strip()
    return (
        f'<div class="{esc(class_name)}">'
        f'<div class="signal-head"><strong>{esc(label)} <span class="help" tabindex="0">?<span class="help-tip">{esc(tip)}</span></span></strong>'
        f'<span class="signal-rule">{scope_count(matched, total, status, scope_label)}<span class="status {status_class(status)}">{esc(status_label(status))}</span></span></div>'
        f'<div class="state-lane">{"".join(cells)}</div></div>'
    )


def coverage_card(
    state: dict,
    *,
    label: str = "Semantic coverage",
    subject: str = "criteria",
    subject_singular: str | None = None,
    retained_subject: str = "paths",
    retained_subject_singular: str | None = None,
    tip: str = "Checks that every required behavior has the exact evidence path or paths declared by the profile.",
) -> str:
    segments = (
        '<span class="coverage-segment pass"></span>' * state["semantic_actual"]
        + '<span class="coverage-segment fail"></span>' * state["failed_count"]
        + '<span class="coverage-segment missing"></span>' * state["missing_count"]
    )
    subject_one = subject_singular or {"criteria": "criterion"}.get(subject, subject)
    retained_one = retained_subject_singular or {"paths": "path"}.get(
        retained_subject, retained_subject
    )
    shown_subject = subject_one if state["required_count"] == 1 else subject
    pass_subject = subject_one if state["semantic_actual"] == 1 else subject
    fail_subject = subject_one if state["failed_count"] == 1 else subject
    missing_subject = subject_one if state["missing_count"] == 1 else subject
    shown_retained = (
        retained_one if state["required_path_count"] == 1 else retained_subject
    )
    return (
        f'<div class="signal-card coverage-card {status_class(state["semantic_status"])}-signal">'
        f'<div class="signal-head"><strong>{esc(label)} {help_tip(tip)}</strong>'
        f'<span class="status {status_class(state["semantic_status"])}">{esc(status_label(state["semantic_status"]))}</span></div>'
        '<div class="coverage-summary">'
        f"<strong>{state['semantic_actual']}<span>/</span>{state['required_count']}</strong><small>{esc(shown_subject)} passing</small>"
        "</div>"
        f'<div class="coverage-strip">{segments}</div>'
        '<div class="coverage-counts">'
        f'<span class="pass">{state["semantic_actual"]} {esc(pass_subject)} pass</span>'
        f'<span class="fail">{state["failed_count"]} {esc(fail_subject)} fail</span>'
        f'<span class="missing">{state["missing_count"]} {esc(missing_subject)} missing</span>'
        f"<span>{state['retained_count']}/{state['required_path_count']} {esc(shown_retained)} retained</span>"
        "</div></div>"
    )


def technical_support_card(
    *,
    item_id: str,
    title: str,
    status: str,
    href: str,
    metrics: tuple[tuple[str, str], ...] = (),
) -> str:
    metrics_html = ""
    if metrics:
        metrics_html = (
            '<div class="metric-values">'
            + "".join(
                f"<div><span>{esc(label)}</span><strong>{esc(value)}</strong></div>"
                for label, value in metrics
            )
            + "</div>"
        )
    return (
        f'<a class="signal-card {status_class(status)}-signal technical-support-card" href="{esc(href)}">'
        '<div class="signal-head">'
        f"<strong>{esc(item_id)}</strong>"
        f'<span class="status {status_class(status)}">{esc(status_label(status))}</span></div>'
        f'<div class="coverage-summary"><small>{esc(title)}</small></div>'
        f"{metrics_html}</a>"
    )


def domain_card(
    *,
    label: str,
    status: str,
    href: str,
    meta: str,
    help_text: str | None = None,
) -> str:
    help_html = f" {help_tip(help_text, focusable=False)}" if help_text else ""
    return (
        f'<a class="domain" href="{esc(href)}"><strong>{esc(label)}{help_html}</strong>'
        f'<span class="status {status_class(status)}">{esc(status_label(status))}</span>'
        f'<span class="domain-meta">{esc(meta)}</span></a>'
    )


def history_section(
    *,
    section_id: str,
    status: str,
    link_href: str,
    link_label: str,
) -> str:
    return (
        f'<section class="section" id="{esc(section_id)}"><div class="section-head">'
        f'<h3>History</h3><a class="section-link" href="{esc(link_href)}">{esc(link_label)}</a></div>'
        '<div class="panel history"><strong>Current</strong><div class="history-line">'
        f'<i class="history-point {status_class(status)}"></i></div>'
        f'<span class="status {status_class(status)}">{esc(status_label(status))}</span>'
        "</div></section>"
    )


def inspector_head(*, eyebrow: str, title: str, status: str) -> str:
    return (
        '<div class="inspector-head"><div>'
        f'<span class="eyebrow">{esc(eyebrow)}</span><h3>{esc(title)}</h3></div>'
        f'<span class="status big {status_class(status)}">{esc(status_label(status))}</span></div>'
    )


def signal_group(
    *,
    title: str,
    body: str,
    class_name: str,
    scope: str | None = None,
) -> str:
    scope_html = f'<span class="group-scope">{esc(scope)}</span>' if scope else ""
    return (
        f'<div class="signal-group {esc(class_name)}">'
        f'<div class="signal-group-head"><strong>{esc(title)}</strong>{scope_html}</div>'
        f"{body}</div>"
    )


def confidence_subgroup(body: str) -> str:
    return (
        '<div class="confidence-subgroup"><div class="subgroup-head">'
        "<strong>Evidence confidence</strong></div>"
        f'<div class="confidence-grid">{body}</div></div>'
    )


def drilldowns(links: tuple[tuple[str, str], ...]) -> str:
    return (
        '<div class="drilldowns">'
        + "".join(
            f'<a href="{esc(href)}">{esc(label)}</a>' for label, href in links if href
        )
        + "</div>"
    )


def section_head(*, title: str, links: tuple[tuple[str, str], ...]) -> str:
    return (
        f'<div class="section-head"><h3>{esc(title)}</h3>'
        '<div class="section-links">'
        + "".join(
            f'<a class="section-link" href="{esc(href)}">{esc(label)}</a>'
            for label, href in links
            if href
        )
        + "</div></div>"
    )


def na_fault_tile(label: str = "Target", *, help_text: str | None = None) -> str:
    help_html = f" {help_tip(help_text, focusable=False)}" if help_text else ""
    return (
        '<div class="fault-tile na" aria-disabled="true">'
        f'<div class="tile-head"><strong>{esc(label)}{help_html}</strong>'
        '<span class="status na">N/A</span></div>'
        '<div class="na-center">N/A</div></div>'
    )


def metric_tile(
    *,
    title: str,
    status: str,
    data_attrs: tuple[tuple[str, str], ...],
    metrics: tuple[tuple[str, str, str, str | None], ...],
    help_text: str | None = None,
) -> str:
    attrs = "".join(f' data-{esc(name)}="{esc(value)}"' for name, value in data_attrs)
    help_html = f" {help_tip(help_text, focusable=False)}" if help_text else ""
    metric_html = "".join(
        (f'<div class="{status_class(metric_status)}">' if metric_status else "<div>")
        + f"<span>{esc(label)}</span><strong>{esc(actual)}</strong>"
        + f"<i>{esc(target)}</i></div>"
        for label, actual, target, metric_status in metrics
    )
    return (
        f'<button class="fault-tile {status_class(status)}" type="button"{attrs}>'
        f'<div class="tile-head"><strong>{esc(title)}{help_html}</strong>'
        f'<span class="status {status_class(status)}">{esc(status_label(status))}</span></div>'
        f'<div class="tile-metrics">{metric_html}</div></button>'
    )


def verdict_header(
    *,
    kicker: str,
    entity_id: str,
    status: str,
    domain_cards: str,
    domain_strip_class: str = "domain-strip",
) -> str:
    return (
        '<header class="verdict"><div class="verdict-main"><div>'
        f'<div class="kicker">{esc(kicker)}</div><h2>{esc(entity_id)}</h2></div>'
        f'<div class="overall {status_class(status)}">{esc(status_label(status))}</div>'
        f'</div><div class="{esc(domain_strip_class)}">{domain_cards}</div></header>'
    )


def support_panel(cards: str) -> str:
    return (
        '<div class="panel technical-support-panel"><div class="signal-grid">'
        f"{cards}</div></div>"
    )


def assurance_navigation(spec: dict) -> str:
    """Render hierarchy-only navigation outside the monitor surface."""
    path = list(spec.get("path") or [])
    children = list(spec.get("children") or [])
    children_label = str(spec.get("children_label") or "")
    if not path:
        return ""

    crumbs = []
    for index, item in enumerate(path):
        if index:
            crumbs.append(
                '<span class="tf-assurance-sep" aria-hidden="true">&rsaquo;</span>'
            )
        label = esc(item.get("label") or item.get("id") or "")
        title = esc(item.get("title") or label)
        url = item.get("url")
        if url:
            crumbs.append(
                f'<a class="tf-assurance-crumb" href="{esc(url)}" title="{title}">{label}</a>'
            )
        else:
            crumbs.append(
                f'<span class="tf-assurance-crumb current" aria-current="page" title="{title}">{label}</span>'
            )

    next_html = ""
    if children and children_label:
        if len(children) == 1:
            child = children[0]
            next_html = (
                f'<a class="tf-assurance-next direct" href="{esc(child["url"])}" '
                f'title="{esc(child.get("title") or child.get("label") or "")}">'
                f'<span>{esc(children_label)}</span><b>1</b><i aria-hidden="true">&rsaquo;</i></a>'
            )
        else:
            items = "".join(
                f'<a href="{esc(child["url"])}" title="{esc(child.get("title") or child.get("label") or "")}">'
                f"{esc(child.get('label') or child.get('id') or '')}</a>"
                for child in children
            )
            next_html = (
                '<details class="tf-assurance-next">'
                f"<summary><span>{esc(children_label)}</span><b>{len(children)}</b>"
                '<i aria-hidden="true">&rsaquo;</i></summary>'
                f'<div class="tf-assurance-menu">{items}</div></details>'
            )

    return (
        '<nav class="tf-assurance-nav" aria-label="Assurance hierarchy">'
        f'<div class="tf-assurance-path">{"".join(crumbs)}</div>{next_html}</nav>'
    )


def render_monitor_shell(
    source: str,
    *,
    page_title: str,
    assurance_id: str,
    monitor: str,
    script: str,
    toc_items: tuple[tuple[str, str], ...],
    navigation: str = "",
) -> str:
    source = re.sub(
        r"<!-- TERNFORGE-P34-REQUIREMENT-MONITOR-START -->.*?<!-- TERNFORGE-P34-REQUIREMENT-MONITOR-END -->",
        "",
        source,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'<style id="tf-requirement-monitor-style">.*?</style>',
        "",
        source,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'<script id="tf-requirement-monitor-script">.*?</script>',
        "",
        source,
        flags=re.DOTALL,
    )
    article = (
        f'<section id="assurance-{esc(assurance_id)}">'
        f"<h1>{esc(page_title)}"
        f'<a class="headerlink" href="#assurance-{esc(assurance_id)}" '
        f'title="Link to this heading">#</a></h1>{navigation}{monitor}</section>'
    )
    source, article_count = re.subn(
        r'(<article class="bd-article">).*?(</article>)',
        lambda match: match.group(1) + article + match.group(2),
        source,
        count=1,
        flags=re.DOTALL,
    )
    if article_count != 1:
        raise RuntimeError("Could not replace assurance monitor article body")

    source = source.replace("</head>", MONITOR_STYLE + "\n</head>", 1)
    source = source.replace("</body>", script + "\n</body>", 1)

    source, breadcrumb_count = re.subn(
        r'(<li class="breadcrumb-item active" aria-current="page"><span class="ellipsis">).*?(</span></li>)',
        lambda match: match.group(1) + esc(page_title) + match.group(2),
        source,
        count=1,
        flags=re.DOTALL,
    )
    if breadcrumb_count != 1:
        raise RuntimeError("Could not replace assurance monitor breadcrumb")

    source, title_count = re.subn(
        r"(<title>).*?(?= (?:&#8212;|—) llm-router)",
        lambda match: match.group(1) + esc(page_title),
        source,
        count=1,
        flags=re.DOTALL,
    )
    if title_count != 1:
        raise RuntimeError("Could not replace assurance monitor document title")

    toc = "".join(
        f'<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" '
        f'href="{esc(href)}">{esc(label)}</a></li>'
        for label, href in toc_items
    )
    secondary = (
        '<div id="pst-secondary-sidebar" class="bd-sidebar-secondary bd-toc">'
        '<div class="sidebar-secondary-items sidebar-secondary__inner">'
        '<div class="sidebar-secondary-item"><div class="tocsection onthispage">'
        '<i class="fa-solid fa-list"></i> On this page</div>'
        '<nav class="bd-toc-nav page-toc">'
        '<ul class="visible nav section-nav flex-column">'
        f"{toc}</ul></nav></div></div></div>"
    )
    source, sidebar_count = re.subn(
        r'<div id="pst-secondary-sidebar" class="bd-sidebar-secondary bd-toc">.*?</div></div>\s*</div>\s*<footer class="bd-footer-content">',
        secondary + '\n</div>\n<footer class="bd-footer-content">',
        source,
        count=1,
        flags=re.DOTALL,
    )
    if sidebar_count != 1:
        raise RuntimeError("Could not replace assurance monitor secondary sidebar")
    return source


def monitor_script(
    *,
    setup_js: str,
    bind_js: str,
    nav_selector: str,
    init_js: str = "",
) -> str:
    return f"""<script id="tf-requirement-monitor-script">
(()=>{{const root=document.querySelector('#tf-requirement-monitor');if(!root)return;{setup_js}function syncSticky(){{const header=document.querySelector('.bd-header');const top=header?.getBoundingClientRect().bottom||0;root.style.setProperty('--sticky-top',top+'px')}}{bind_js}let flashTimer;function flashTarget(hash){{if(!hash||!hash.startsWith('#'))return;const target=root.querySelector(hash);if(!target||!target.classList.contains('section'))return;root.querySelectorAll('.section.nav-flash').forEach(node=>node.classList.remove('nav-flash'));void target.offsetWidth;target.classList.add('nav-flash');clearTimeout(flashTimer);flashTimer=setTimeout(()=>target.classList.remove('nav-flash'),1700);}}document.querySelectorAll('{nav_selector}').forEach(link=>link.addEventListener('click',()=>requestAnimationFrame(()=>flashTarget(link.getAttribute('href')))));window.addEventListener('hashchange',()=>flashTarget(location.hash));function syncAssurancePath(){{document.querySelectorAll('.tf-assurance-path').forEach(path=>{{const current=path.querySelector('.tf-assurance-crumb.current');if(!current)return;path.scrollLeft=Math.max(0,current.offsetLeft+current.offsetWidth-path.clientWidth);}});}}window.addEventListener('resize',()=>{{syncSticky();syncAssurancePath()}});syncSticky();syncAssurancePath();{init_js}if(location.hash)requestAnimationFrame(()=>flashTarget(location.hash));}})();
</script>"""


MONITOR_STYLE = '<style id="tf-requirement-monitor-style">\n.bd-article-container{overflow:visible!important}\n#tf-requirement-monitor{--surface:var(--pst-color-surface);--surface2:color-mix(in srgb,var(--pst-color-surface) 88%,var(--pst-color-background));--text:var(--pst-color-text-base);--muted:var(--pst-color-text-muted);--line:var(--pst-color-border);--green:#2e9d58;--red:#d24b4b;--amber:var(--pst-color-warning);--blue:var(--pst-color-primary);--shadow:0 .35rem 1rem color-mix(in srgb,#000 9%,transparent);--sticky-top:var(--pst-header-height,4rem);color:var(--text);font-size:.86rem;line-height:1.35}\n#tf-requirement-monitor *{box-sizing:border-box}#tf-requirement-monitor button{font:inherit;color:inherit}#tf-requirement-monitor a{color:inherit}.tf-exp-badge{display:inline-block;margin-left:.45rem;padding:.12rem .28rem;border:1px solid var(--pst-color-border);border-radius:.25rem;color:var(--pst-color-text-muted);font-size:.55rem;font-weight:800;letter-spacing:.06em;vertical-align:.18rem}\n#tf-requirement-monitor .verdict{position:sticky;top:var(--sticky-top);z-index:24;margin:.35rem 0 1rem;padding:.75rem .85rem;background:color-mix(in srgb,var(--pst-color-background) 94%,transparent);backdrop-filter:blur(8px);border:1px solid var(--line);border-radius:.45rem;box-shadow:var(--shadow)}#tf-requirement-monitor .verdict-main{display:flex;align-items:center;justify-content:space-between;gap:1rem}#tf-requirement-monitor .kicker,#tf-requirement-monitor .eyebrow{font-size:.62rem;font-weight:800;letter-spacing:.075em;text-transform:uppercase;color:var(--muted)}#tf-requirement-monitor h2{font-size:1rem;margin:.1rem 0 0}#tf-requirement-monitor h3{font-size:.86rem;letter-spacing:.04em;text-transform:uppercase;margin:0}#tf-requirement-monitor .overall{font-size:.92rem;font-weight:900;padding:.42rem .65rem;border-radius:.45rem;border:1px solid var(--line);background:var(--surface);color:var(--muted)}#tf-requirement-monitor .overall.not-met{border-color:color-mix(in srgb,var(--red) 65%,var(--line));background:color-mix(in srgb,var(--red) 9%,var(--surface));color:var(--red)}#tf-requirement-monitor .overall.met{border-color:color-mix(in srgb,var(--green) 60%,var(--line));background:color-mix(in srgb,var(--green) 8%,var(--surface));color:var(--green)}#tf-requirement-monitor .overall.unknown{border-color:color-mix(in srgb,var(--amber) 60%,var(--line));background:color-mix(in srgb,var(--amber) 8%,var(--surface));color:var(--amber)}\n#tf-requirement-monitor .domain-strip{display:grid;grid-template-columns:1fr 1fr;gap:.45rem;margin-top:.55rem}#tf-requirement-monitor .domain-strip.with-support{grid-template-columns:repeat(3,minmax(0,1fr))}#tf-requirement-monitor .domain{display:grid;grid-template-columns:1fr auto;gap:.12rem .5rem;align-items:center;padding:.45rem .55rem;border:1px solid var(--line);border-radius:.4rem;background:var(--surface);text-decoration:none}#tf-requirement-monitor .domain:hover{border-color:var(--blue)}#tf-requirement-monitor .domain strong{font-size:.67rem;text-transform:uppercase;letter-spacing:.03em;color:var(--muted)}#tf-requirement-monitor .domain-meta{grid-column:1/-1;font-size:.58rem;color:var(--muted)}#tf-requirement-monitor .status{font-size:.63rem;font-weight:900;letter-spacing:.02em;white-space:nowrap}#tf-requirement-monitor .status.met{color:var(--green)}#tf-requirement-monitor .status.not-met{color:var(--red)}#tf-requirement-monitor .status.unknown{color:var(--amber)}#tf-requirement-monitor .status.na{color:var(--muted)}#tf-requirement-monitor .status.big{font-size:.72rem}\n#tf-requirement-monitor .section{position:relative;margin-top:1rem;scroll-margin-top:calc(var(--sticky-top) + 8.7rem);border-radius:.55rem}#tf-requirement-monitor .section.nav-flash{animation:tf-destination-flash 1.6s ease-out}@keyframes tf-destination-flash{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--blue) 0%,transparent)}16%{box-shadow:0 0 0 3px color-mix(in srgb,var(--blue) 72%,transparent)}68%{box-shadow:0 0 0 2px color-mix(in srgb,var(--blue) 42%,transparent)}100%{box-shadow:0 0 0 0 color-mix(in srgb,var(--blue) 0%,transparent)}}@media(prefers-reduced-motion:reduce){#tf-requirement-monitor .section.nav-flash{animation:tf-destination-flash-reduced .8s linear}}@keyframes tf-destination-flash-reduced{0%,70%{box-shadow:0 0 0 3px color-mix(in srgb,var(--blue) 58%,transparent)}100%{box-shadow:0 0 0 0 transparent}}#tf-requirement-monitor .section-head{display:flex;align-items:end;justify-content:space-between;gap:1rem;margin-bottom:.45rem}#tf-requirement-monitor .section-links{display:flex;gap:.55rem}#tf-requirement-monitor .section-link,#tf-requirement-monitor .drilldowns a{font-size:.62rem;color:var(--muted);text-decoration:none}#tf-requirement-monitor .section-link:hover,#tf-requirement-monitor .drilldowns a:hover{color:var(--text)}#tf-requirement-monitor .dashboard-layout{display:grid;grid-template-columns:minmax(0,1.12fr) minmax(19rem,.88fr);gap:.55rem;align-items:start}#tf-requirement-monitor .panel,#tf-requirement-monitor .inspector{border:1px solid var(--line);border-radius:.5rem;background:var(--surface);box-shadow:var(--shadow)}\n#tf-requirement-monitor .matrix-wrap{overflow-x:auto;padding:.38rem}#tf-requirement-monitor table{border-collapse:separate;border-spacing:.25rem;width:100%;margin:0}#tf-requirement-monitor th{font-size:.61rem;color:var(--muted);font-weight:700;text-align:left;white-space:nowrap;padding:.1rem}#tf-requirement-monitor thead th{text-align:center}#tf-requirement-monitor thead th:first-child{text-align:left}#tf-requirement-monitor td{padding:0}#tf-requirement-monitor .matrix-cell{width:100%;height:3.3rem;min-width:5.7rem;padding:.35rem .4rem;border:1px solid var(--line);border-radius:.4rem;background:var(--surface2);text-align:left}#tf-requirement-monitor button.matrix-cell{cursor:pointer}#tf-requirement-monitor button.matrix-cell:hover,#tf-requirement-monitor button.matrix-cell.selected{outline:2px solid color-mix(in srgb,var(--blue) 55%,transparent);outline-offset:1px}#tf-requirement-monitor .matrix-cell.not-met{border-color:color-mix(in srgb,var(--red) 58%,var(--line));background:color-mix(in srgb,var(--red) 7%,var(--surface))}#tf-requirement-monitor .matrix-cell.unknown{border-color:color-mix(in srgb,var(--amber) 58%,var(--line));background:color-mix(in srgb,var(--amber) 6%,var(--surface))}#tf-requirement-monitor .matrix-cell.met{border-color:color-mix(in srgb,var(--green) 55%,var(--line));background:color-mix(in srgb,var(--green) 6%,var(--surface))}#tf-requirement-monitor .matrix-cell.na{display:grid;place-items:center;border-color:transparent;background:color-mix(in srgb,var(--surface2) 45%,transparent);color:var(--muted);text-align:center}#tf-requirement-monitor .cell-status{display:block;margin-bottom:.22rem}#tf-requirement-monitor .cell-values{display:grid;grid-template-columns:1fr 1fr;gap:.3rem}#tf-requirement-monitor .cell-values small{display:block;font-size:.5rem;color:var(--muted);text-transform:uppercase}#tf-requirement-monitor .cell-values strong{font-size:.82rem}\n#tf-requirement-monitor .technical-support-panel{padding:.55rem}#tf-requirement-monitor .technical-support-card{display:block;text-decoration:none}#tf-requirement-monitor .technical-support-card:hover{border-color:var(--blue)}#tf-requirement-monitor .inspector{padding:.55rem}#tf-requirement-monitor .inspector-head{display:flex;align-items:start;justify-content:space-between;gap:.7rem;margin-bottom:.5rem}#tf-requirement-monitor .signal-grid{display:grid;grid-template-columns:1fr;gap:.48rem}#tf-requirement-monitor .signal-group{display:grid;gap:.28rem;padding:.38rem;border:1px solid color-mix(in srgb,var(--line) 82%,transparent);border-radius:.46rem;background:color-mix(in srgb,var(--surface2) 54%,transparent)}#tf-requirement-monitor .signal-group-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.45rem;padding:0 .04rem .26rem;border-bottom:1px solid color-mix(in srgb,var(--line) 72%,transparent)}#tf-requirement-monitor .signal-group-head>strong,#tf-requirement-monitor .signal-group-head>div>strong{font-size:.57rem;letter-spacing:.065em;text-transform:uppercase;color:var(--muted)}#tf-requirement-monitor .group-scope{font-size:.52rem;font-weight:800;color:var(--muted);white-space:nowrap}#tf-requirement-monitor .representation-stack{display:grid;gap:.22rem}#tf-requirement-monitor .dependent-wrap{margin-left:.72rem;padding-left:.5rem;border-left:2px solid color-mix(in srgb,var(--line) 78%,transparent)}#tf-requirement-monitor .dependent-signal{background:color-mix(in srgb,var(--surface2) 38%,transparent);border-style:dashed}#tf-requirement-monitor .confidence-subgroup{display:grid;gap:.28rem;margin-top:.12rem;padding-top:.38rem;border-top:1px solid color-mix(in srgb,var(--line) 72%,transparent)}#tf-requirement-monitor .subgroup-head strong{font-size:.57rem;letter-spacing:.065em;text-transform:uppercase;color:var(--muted)}#tf-requirement-monitor .confidence-grid{display:grid;gap:.28rem}#tf-requirement-monitor .signal-card{border:1px solid var(--line);border-radius:.4rem;background:var(--surface2);padding:.38rem .42rem}#tf-requirement-monitor .signal-card.met-signal{border-color:color-mix(in srgb,var(--green) 42%,var(--line))}#tf-requirement-monitor .signal-card.not-met-signal{border-color:color-mix(in srgb,var(--red) 50%,var(--line))}#tf-requirement-monitor .signal-card.unknown-signal{border-color:color-mix(in srgb,var(--amber) 45%,var(--line))}#tf-requirement-monitor .signal-card.na-signal{background:color-mix(in srgb,var(--surface2) 35%,transparent);border-style:dashed;padding:.34rem .4rem}#tf-requirement-monitor .na-signal .signal-head strong{color:var(--muted)}#tf-requirement-monitor .na-signal .state-option{color:color-mix(in srgb,var(--muted) 78%,transparent);border-color:color-mix(in srgb,var(--line) 70%,transparent);background:color-mix(in srgb,var(--surface) 70%,transparent)}#tf-requirement-monitor .na-signal .state-option.selected{color:var(--muted);border-color:color-mix(in srgb,var(--muted) 55%,var(--line))}#tf-requirement-monitor .signal-head{display:flex;align-items:center;justify-content:space-between;gap:.45rem;font-size:.67rem}#tf-requirement-monitor .signal-rule{display:flex;align-items:center;gap:.35rem}#tf-requirement-monitor .scope-count{display:inline-flex;align-items:baseline;gap:.16rem;padding:.1rem .24rem;border:1px solid var(--line);border-radius:.28rem;background:var(--surface);white-space:nowrap}#tf-requirement-monitor .scope-count b{font-size:.55rem}#tf-requirement-monitor .scope-count small{font-size:.44rem;color:var(--muted)}#tf-requirement-monitor .scope-count.met{border-color:color-mix(in srgb,var(--green) 42%,var(--line))}#tf-requirement-monitor .scope-count.not-met{border-color:color-mix(in srgb,var(--red) 48%,var(--line))}#tf-requirement-monitor .scope-count.unknown{border-color:color-mix(in srgb,var(--amber) 46%,var(--line))}#tf-requirement-monitor .coverage-summary{display:flex;align-items:baseline;gap:.38rem;margin-top:.28rem}#tf-requirement-monitor .coverage-summary>strong{font-size:1.08rem;line-height:1}#tf-requirement-monitor .coverage-summary>strong span{font-size:.7rem;color:var(--muted);margin:0 .05rem}#tf-requirement-monitor .coverage-summary small{font-size:.52rem;color:var(--muted)}#tf-requirement-monitor .coverage-strip{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:.18rem;margin-top:.34rem}#tf-requirement-monitor .coverage-segment{height:.28rem;border-radius:999px;background:var(--line)}#tf-requirement-monitor .coverage-segment.pass{background:var(--green)}#tf-requirement-monitor .coverage-segment.fail{background:var(--red)}#tf-requirement-monitor .coverage-segment.missing{background:transparent;border:1px dashed var(--red)}#tf-requirement-monitor .coverage-counts{display:flex;gap:.45rem;margin-top:.25rem;font-size:.48rem;font-weight:700;color:var(--muted)}#tf-requirement-monitor .coverage-counts .pass{color:var(--green)}#tf-requirement-monitor .coverage-counts .fail,#tf-requirement-monitor .coverage-counts .missing{color:var(--red)}#tf-requirement-monitor .metric-values{display:grid;grid-template-columns:1fr 1fr;gap:.28rem;margin-top:.32rem}#tf-requirement-monitor .metric-values div{padding:.28rem .32rem;border-radius:.3rem;background:var(--surface)}#tf-requirement-monitor .metric-values span{display:block;font-size:.49rem;color:var(--muted);text-transform:uppercase}#tf-requirement-monitor .metric-values strong{display:block;font-size:.78rem;margin-top:.05rem}#tf-requirement-monitor .state-lane{display:flex;gap:.22rem;flex-wrap:wrap;margin-top:.32rem}#tf-requirement-monitor .state-option{display:inline-flex;align-items:center;gap:.22rem;padding:.2rem .3rem;border:1px solid var(--line);border-radius:.3rem;background:var(--surface);font-size:.55rem;color:var(--muted)}#tf-requirement-monitor .state-option.selected{color:var(--text);border-color:var(--blue)}#tf-requirement-monitor .marker{font-size:.43rem;font-weight:900;padding:.08rem .16rem;border-radius:.2rem;white-space:nowrap}#tf-requirement-monitor .marker.both{background:color-mix(in srgb,var(--blue) 13%,var(--surface));color:var(--blue)}#tf-requirement-monitor .marker.actual{background:color-mix(in srgb,var(--green) 12%,var(--surface));color:var(--green)}#tf-requirement-monitor .marker.target{background:color-mix(in srgb,var(--blue) 12%,var(--surface));color:var(--blue)}#tf-requirement-monitor .marker.inactive{background:color-mix(in srgb,var(--muted) 12%,var(--surface));color:var(--muted)}\n#tf-requirement-monitor .help{position:relative;display:inline-grid;place-items:center;width:.82rem;height:.82rem;border:1px solid var(--line);border-radius:50%;font-size:.5rem;color:var(--muted);cursor:help;vertical-align:.08rem;text-transform:none;letter-spacing:normal}#tf-requirement-monitor .help-tip{position:absolute;z-index:50;left:50%;bottom:1rem;transform:translateX(-50%);width:15rem;max-width:calc(100vw - 2rem);padding:.36rem .42rem;border:1px solid color-mix(in srgb,var(--line) 82%,var(--text));border-radius:.3rem;background:var(--pst-color-background);box-shadow:0 .45rem 1.4rem rgba(0,0,0,.28);font-size:.55rem;font-weight:600;color:var(--text);line-height:1.35;text-transform:none;letter-spacing:normal;opacity:0;visibility:hidden;pointer-events:none}#tf-requirement-monitor .help:hover .help-tip,#tf-requirement-monitor .help:focus .help-tip{opacity:1;visibility:visible}#tf-requirement-monitor .signal-group-head>.help .help-tip{left:auto;right:0;transform:none}#tf-requirement-monitor .tile-metrics .help{display:inline-grid;font-size:.5rem;color:var(--muted)}#tf-requirement-monitor .tile-metrics .help-tip{font-size:.55rem;color:var(--text)}#tf-requirement-monitor .drilldowns{display:flex;justify-content:flex-end;gap:.55rem;margin-top:.45rem;padding-top:.4rem;border-top:1px solid var(--line)}\n#tf-requirement-monitor .fault-layout{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(19rem,.95fr);gap:.55rem;align-items:start}#tf-requirement-monitor .fault-layout.no-inspector{grid-template-columns:1fr}#tf-requirement-monitor .fault-layout.no-inspector .fault-grid{grid-template-columns:repeat(5,minmax(0,1fr))}#tf-requirement-monitor .fault-grid{display:grid;grid-template-columns:1fr 1fr;gap:.38rem}#tf-requirement-monitor .fault-tile{min-height:5.3rem;padding:.48rem;border:1px solid var(--line);border-radius:.42rem;background:var(--surface);text-align:left}#tf-requirement-monitor button.fault-tile{cursor:pointer}#tf-requirement-monitor button.fault-tile:hover,#tf-requirement-monitor button.fault-tile.selected{outline:2px solid color-mix(in srgb,var(--blue) 55%,transparent);outline-offset:1px}#tf-requirement-monitor .fault-tile.not-met{border-color:color-mix(in srgb,var(--red) 55%,var(--line))}#tf-requirement-monitor .fault-tile.met{border-color:color-mix(in srgb,var(--green) 50%,var(--line))}#tf-requirement-monitor .fault-tile.na{background:color-mix(in srgb,var(--surface2) 45%,transparent);color:var(--muted);border-style:dashed}#tf-requirement-monitor .tile-head{display:flex;align-items:start;justify-content:space-between;gap:.4rem;font-size:.61rem}#tf-requirement-monitor .tile-metrics{display:grid;grid-template-columns:1fr 1fr;gap:.28rem;margin-top:.5rem}#tf-requirement-monitor .tile-metrics div{padding:.28rem .32rem;border-radius:.3rem;background:var(--surface2)}#tf-requirement-monitor .tile-metrics span{display:block;font-size:.49rem;color:var(--muted)}#tf-requirement-monitor .tile-metrics strong{font-size:.72rem}#tf-requirement-monitor .tile-metrics i{font-size:.49rem;color:var(--muted);font-style:normal;margin-left:.16rem}#tf-requirement-monitor .tile-metrics .not-met strong{color:var(--red)}#tf-requirement-monitor .na-center{display:flex;align-items:center;justify-content:center;gap:.4rem;height:3rem;font-size:.61rem;color:var(--muted)}#tf-requirement-monitor .fault-signals{grid-template-columns:1fr}#tf-requirement-monitor .fault-chain{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr) auto minmax(0,1fr);align-items:stretch;gap:.28rem}#tf-requirement-monitor .fault-chain>i{align-self:center;color:var(--muted);font-style:normal;font-weight:800}#tf-requirement-monitor .fault-stage{display:grid;grid-template-columns:1fr auto;gap:.12rem .35rem;align-items:center;padding:.36rem .42rem;border:1px solid var(--line);border-radius:.38rem;background:var(--surface)}#tf-requirement-monitor .fault-stage>span{font-size:.5rem;color:var(--muted)}#tf-requirement-monitor .fault-stage>strong{font-size:.82rem}#tf-requirement-monitor .fault-stage>small{grid-column:1/-1;font-size:.47rem;color:var(--muted)}#tf-requirement-monitor .fault-stage>.status{justify-self:end}#tf-requirement-monitor .fault-stage.met{border-color:color-mix(in srgb,var(--green) 42%,var(--line))}#tf-requirement-monitor .fault-stage.not-met{border-color:color-mix(in srgb,var(--red) 50%,var(--line))}#tf-requirement-monitor .fault-stage.unknown{border-color:color-mix(in srgb,var(--amber) 45%,var(--line))}#tf-requirement-monitor .mutation-grid{display:grid;gap:.32rem}#tf-requirement-monitor .mutation-chain{padding:.34rem;border:1px solid var(--line);border-radius:.4rem;background:color-mix(in srgb,var(--surface2) 52%,transparent)}#tf-requirement-monitor .mutation-chain-head{margin:0 0 .28rem .05rem}#tf-requirement-monitor .mutation-chain-head strong{font-size:.55rem;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}\n#tf-requirement-monitor .history{display:flex;align-items:center;gap:.55rem;padding:.55rem .65rem}#tf-requirement-monitor .history-line{flex:1;height:2px;background:var(--line);position:relative}#tf-requirement-monitor .history-point{position:absolute;right:0;top:50%;transform:translate(50%,-50%);width:.5rem;height:.5rem;border-radius:50%;background:var(--muted);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--muted) 12%,transparent)}#tf-requirement-monitor .history-point.not-met{background:var(--red);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--red) 12%,transparent)}#tf-requirement-monitor .history-point.met{background:var(--green);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--green) 12%,transparent)}#tf-requirement-monitor .history-point.unknown{background:var(--amber);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--amber) 12%,transparent)}#tf-requirement-monitor .history strong{font-size:.67rem}\n@media(max-width:1200px){#tf-requirement-monitor .dashboard-layout,#tf-requirement-monitor .fault-layout{grid-template-columns:1fr}#tf-requirement-monitor .confidence-grid{grid-template-columns:repeat(3,minmax(0,1fr))}#tf-requirement-monitor .fault-grid,#tf-requirement-monitor .fault-layout.no-inspector .fault-grid{grid-template-columns:repeat(3,1fr)}#tf-requirement-monitor .fault-tile:nth-child(3n+1) .tile-metrics .help-tip{left:0;transform:none}}@media(max-width:760px){#tf-requirement-monitor .domain-strip,#tf-requirement-monitor .domain-strip.with-support{grid-template-columns:1fr}#tf-requirement-monitor .confidence-grid{grid-template-columns:1fr}#tf-requirement-monitor .fault-grid,#tf-requirement-monitor .fault-layout.no-inspector .fault-grid{grid-template-columns:1fr 1fr}#tf-requirement-monitor .fault-signals{grid-template-columns:1fr}#tf-requirement-monitor .fault-tile:nth-child(odd) .tile-metrics .help-tip{left:0;transform:none}}\n</style>'

ASSURANCE_NAV_STYLE = r"""
.tf-assurance-nav{position:relative;display:flex;align-items:center;justify-content:space-between;gap:.8rem;min-height:2.15rem;margin:.05rem 0 .85rem;padding:.28rem .1rem .48rem;border-bottom:1px solid var(--pst-color-border);font-size:.78rem;line-height:1.2}
.tf-assurance-path{display:flex;align-items:center;gap:.38rem;min-width:0;overflow-x:auto;white-space:nowrap;scrollbar-width:none}
.tf-assurance-path::-webkit-scrollbar{display:none}
.tf-assurance-crumb{flex:0 0 auto;color:var(--pst-color-text-muted);text-decoration:none}
a.tf-assurance-crumb:hover{color:var(--pst-color-text-base);text-decoration:none}
.tf-assurance-crumb.current{color:var(--pst-color-text-base);font-weight:700}
.tf-assurance-sep{flex:0 0 auto;color:color-mix(in srgb,var(--pst-color-text-muted) 62%,transparent);font-weight:700}
.tf-assurance-next{position:relative;flex:0 0 auto;margin:0}
.tf-assurance-next.direct,.tf-assurance-next summary{display:inline-flex;align-items:center;gap:.32rem;padding:.3rem .42rem;border-radius:.34rem;color:var(--pst-color-text-muted);text-decoration:none;cursor:pointer;white-space:nowrap;user-select:none}
.tf-assurance-next summary{list-style:none}
.tf-assurance-next summary::-webkit-details-marker{display:none}
.tf-assurance-next.direct:hover,.tf-assurance-next summary:hover,.tf-assurance-next[open] summary{background:color-mix(in srgb,var(--pst-color-primary) 7%,transparent);color:var(--pst-color-text-base);text-decoration:none}
.tf-assurance-next b{font-size:.66rem;color:var(--pst-color-text-base);font-weight:800}
.tf-assurance-next i{font-style:normal;font-weight:800;color:var(--pst-color-text-muted);transition:transform .12s ease}
.tf-assurance-next[open] summary i{transform:rotate(90deg)}
.tf-assurance-menu{position:absolute;z-index:45;right:0;top:calc(100% + .28rem);min-width:13.5rem;max-width:min(21rem,calc(100vw - 2rem));padding:.28rem;border:1px solid var(--pst-color-border);border-radius:.42rem;background:var(--pst-color-background);box-shadow:0 .45rem 1.35rem color-mix(in srgb,#000 16%,transparent)}
.tf-assurance-menu a{display:block;padding:.38rem .45rem;border-radius:.3rem;color:var(--pst-color-text-base);text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-assurance-menu a:hover{background:color-mix(in srgb,var(--pst-color-primary) 7%,transparent);text-decoration:none}
@media(max-width:760px){.tf-assurance-nav{gap:.4rem}.tf-assurance-next.direct,.tf-assurance-next summary{padding:.28rem .34rem}.tf-assurance-menu{position:fixed;right:1rem;left:1rem;top:auto;min-width:0;max-width:none}}
"""
MONITOR_STYLE = MONITOR_STYLE.replace("</style>", ASSURANCE_NAV_STYLE + "</style>")
