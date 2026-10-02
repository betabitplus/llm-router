"""Shared Contract Evidence / Assurance monitor presentation system."""

# ruff: noqa: D103, E501, EM101, PLR0913, PLR0917, TRY003

from __future__ import annotations

import html
import re
import urllib.parse

EXPLORER_URL = "verification-explorer.html"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def explorer_href(owner: str, **filters: str) -> str:
    """Where the Verification Explorer lists an item's rows, narrowed like the monitor part that links there."""
    return EXPLORER_URL + "#" + urllib.parse.urlencode({"contract": owner, **filters})


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
    *,
    rungs: list[str],
) -> str:
    """One signal of a detail card: its row (name, scope, verdict) and its scale as a track, low to high."""
    scale = [option for option in rungs if option in options]
    off_scale = [option for option in options if option not in scale]
    actual_set = set(actual_values)

    def piece(option: str, kind: str) -> str:
        inactive = status == "N/A" and option == "N/A"
        is_actual = option in actual_set and not inactive
        is_target = option == target and not inactive
        word = (
            "INACTIVE"
            if inactive
            else "ACTUAL = TARGET"
            if is_actual and is_target
            else "ACTUAL"
            if is_actual
            else "TARGET"
            if is_target
            else ""
        )
        classes = kind + " actual" * is_actual + " target" * is_target + " inactive" * inactive
        mark = f'<i class="tmark">{word}</i>' if word else ""
        return f'<span class="{classes}"><span>{esc(state_option_label(label, option))}</span>{mark}</span>'

    class_name = f"signal-card track-lane {status_class(status)}-signal {extra_class}".strip()
    return (
        f'<div class="{esc(class_name)}">'
        f'<div class="signal-head"><strong>{esc(label)} {help_tip(tip)}</strong>'
        f'<span class="signal-rule">{scope_count(matched, total, status, scope_label)}'
        f'<span class="status {status_class(status)}">{esc(status_label(status))}</span></span></div>'
        f'<div class="track-row"><div class="track" style="--n:{len(scale)}">{"".join(piece(option, "seg") for option in scale)}</div>'
        f'<div class="track-off">{"".join(piece(option, "off") for option in off_scale)}</div></div></div>'
    )


def zero(count: int) -> str:
    """A zero is a fact, not a signal: it stays, quiet."""
    return "" if count else " zero"


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
        f'<span class="pass{zero(state["semantic_actual"])}">{state["semantic_actual"]} {esc(pass_subject)} pass</span>'
        f'<span class="fail{zero(state["failed_count"])}">{state["failed_count"]} {esc(fail_subject)} fail</span>'
        f'<span class="missing{zero(state["missing_count"])}">{state["missing_count"]} {esc(missing_subject)} missing</span>'
        f"<span>{state['retained_count']}/{state['required_path_count']} {esc(shown_retained)} retained</span>"
        "</div></div>"
    )


def support_summary(
    *,
    noun: str,
    parts: tuple[tuple[str, str, int, int, int], ...],
) -> str:
    """What the items a monitor rests on say, counted: per part how many pass of how many, with a strip of one
    segment per item. Which items and why they fail is the Verification Explorer's to list."""
    cards = []
    for label, status, passed, failed, total in parts:
        unknown = max(0, total - passed - failed)
        segments = (
            '<span class="coverage-segment pass"></span>' * passed
            + '<span class="coverage-segment fail"></span>' * failed
            + '<span class="coverage-segment missing"></span>' * unknown
        )
        cards.append(
            f'<div class="signal-card coverage-card {status_class(status)}-signal">'
            f'<div class="signal-head"><strong>{esc(label)}</strong>'
            f'<span class="status {status_class(status)}">{esc(status_label(status))}</span></div>'
            f'<div class="coverage-summary"><strong>{passed}<span>/</span>{total}</strong>'
            f"<small>{esc(noun)} passing</small></div>"
            f'<div class="coverage-strip">{segments}</div></div>'
        )
    return (
        '<div class="panel technical-support-panel"><div class="signal-grid">'
        + "".join(cards)
        + "</div></div>"
    )


def domain_card(
    *,
    label: str,
    status: str,
    href: str,
    meta: str,
    help_text: str | None = None,
    thumb: str = "",
    navigator: bool = False,
) -> str:
    help_html = f" {help_tip(help_text, focusable=False)}" if help_text else ""
    words = (
        f'<strong>{esc(label)}{help_html}</strong>'
        f'<span class="status {status_class(status)}">{esc(status_label(status))}</span>'
        f'<span class="domain-meta">{esc(meta)}</span>'
    )
    if navigator:
        return (
            f'<div class="domain {status_class(status)}-card with-nav">'
            f'<a class="domain-link" href="{esc(href)}">{words}</a>{thumb}</div>'
        )
    return f'<a class="domain {status_class(status)}-card" href="{esc(href)}">{words}{thumb}</a>'


def history_section(
    *,
    section_id: str,
    status: str,
    link_href: str,
    link_label: str,
    owner_id: str = "",
) -> str:
    # What changed since the previous retained run is written into the placeholder once the explorer has
    # compared the two runs, after the monitors are rendered; until then it says nothing rather than guess.
    changes = (
        f'<span class="history-changes" data-history-owner="{esc(owner_id)}"></span>' if owner_id else ""
    )
    return (
        f'<section class="section" id="{esc(section_id)}"><div class="section-head">'
        f'<h3>History</h3><a class="section-link" href="{esc(link_href)}">{esc(link_label)}</a></div>'
        '<div class="panel history"><strong>Current</strong><div class="history-line">'
        f'<i class="history-point {status_class(status)}"></i></div>'
        f'<span class="status {status_class(status)}">{esc(status_label(status))}</span>'
        f"{changes}</div></section>"
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


def no_retained_evidence() -> str:
    return '<div class="na-center">No test result yet, so there is nothing to judge here.</div>'


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
        '<div class="fault-tile na air" aria-disabled="true" title="N/A · the profile does not ask for this group">'
        f'<div class="tile-head"><strong>{esc(label)}{help_html}</strong>'
        '<span class="status na">N/A</span></div>'
        '<div class="na-center" aria-hidden="true"></div></div>'
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
    map_href: str | None = None,
    explorer_href: str | None = None,
    title: str = "",
) -> str:
    links = (
        f' <a class="section-link" href="{esc(map_href)}">Health Map ↗</a>' if map_href else ""
    ) + (
        f' <a class="section-link" href="{esc(explorer_href)}">Explorer ↗</a>'
        if explorer_href
        else ""
    )
    heading = (
        f'<h2>{esc(title)}</h2><div class="verdict-id"><code>{esc(entity_id)}</code>{links}</div>'
        if title
        else f"<h2>{esc(entity_id)}{links}</h2>"
    )
    return (
        '<div class="verdict-shell"><header class="verdict"><div class="verdict-main"><div>'
        f'<div class="kicker">{esc(kicker)}</div>{heading}</div>'
        f'<div class="overall {status_class(status)}">{esc(status_label(status))}</div>'
        f'</div><div class="{esc(domain_strip_class)}">{domain_cards}</div></header></div>'
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
    # The style and the script go in with a line break of their own (below), and leave with it, so a
    # page patched again reads as a page patched once.
    source = re.sub(
        r'<style id="tf-requirement-monitor-style">.*?</style>\n?',
        "",
        source,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'<script id="tf-requirement-monitor-script">.*?</script>\n?',
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


MONITOR_BEHAVIOUR_JS = (
    # A detail card renders every selection and shows one, so it keeps the height of its tallest.
    "function showLayer(id,key){const layers=[...root.querySelectorAll('#'+id+' .ins-layer')];const layer=layers.find(node=>node.dataset.for===key);if(!layer)return false;layers.forEach(node=>node.classList.toggle('on',node===layer));return true;}"
    # A lens glides to what is selected and the detail's edge points at it; both follow scroll and resize.
    "function glide(scope,item){if(!scope||!item)return;const box=scope.getBoundingClientRect(),at=item.getBoundingClientRect();let ring=scope.querySelector(':scope>.glide');if(!ring){ring=document.createElement('span');ring.className='glide';ring.setAttribute('aria-hidden','true');scope.appendChild(ring)}ring.classList.toggle('not-met',item.classList.contains('not-met'));ring.classList.toggle('unknown',item.classList.contains('unknown'));ring.style.width=at.width+'px';ring.style.height=at.height+'px';ring.style.transform='translate('+(at.left-box.left-scope.clientLeft+scope.scrollLeft)+'px,'+(at.top-box.top-scope.clientTop+scope.scrollTop)+'px)';requestAnimationFrame(()=>ring.classList.add('ready'))}"
    "function point(panel,item){if(!panel||!item)return;let tip=panel.querySelector(':scope>.pointer');if(!tip){tip=document.createElement('span');tip.className='pointer';tip.setAttribute('aria-hidden','true');panel.appendChild(tip)}const box=panel.getBoundingClientRect(),at=item.getBoundingClientRect();const y=Math.max(24,Math.min(box.height-24,at.top+at.height/2-box.top));tip.style.transform='translateY('+(y-7)+'px) rotate(45deg)';requestAnimationFrame(()=>tip.classList.add('ready'))}"
    "const aims=new Map();function aimAt(scope,item,panel){glide(scope,item);point(panel,item);if(scope&&item&&panel)aims.set(panel,{scope,item})}"
    "let followFrame=0;window.addEventListener('scroll',()=>{cancelAnimationFrame(followFrame);followFrame=requestAnimationFrame(()=>aims.forEach((aim,panel)=>point(panel,aim.item)))},{passive:true});"
    "window.addEventListener('resize',()=>aims.forEach((aim,panel)=>aimAt(aim.scope,aim.item,panel)));"
    # Every block knows its verdict, from the header card that links to it; History takes the overall verdict.
    "root.querySelectorAll('a.domain,a.domain-link').forEach(link=>{const href=link.getAttribute('href')||'';if(!href.startsWith('#'))return;const section=root.querySelector(href);const mark=link.querySelector('.status');if(section&&mark)section.dataset.tone=mark.classList.contains('not-met')?'fail':mark.classList.contains('unknown')?'unknown':mark.classList.contains('met')?'pass':'na'});"
    "const historySection=[...root.querySelectorAll('.section')].find(node=>/(^|-)history(-|$)/.test(node.id));const overallMark=root.querySelector('.overall');if(historySection&&overallMark)historySection.dataset.tone=overallMark.classList.contains('not-met')?'fail':overallMark.classList.contains('unknown')?'unknown':'pass';"
    # The arrow keys move between the buttons of one group.
    "function nearest(list,from,dx,dy){const at=from.getBoundingClientRect(),cx=at.left+at.width/2,cy=at.top+at.height/2;let best=null,score=Infinity;list.forEach(node=>{if(node===from)return;const r=node.getBoundingClientRect(),ddx=r.left+r.width/2-cx,ddy=r.top+r.height/2-cy;if(dx&&(Math.sign(ddx)!==dx||Math.abs(ddy)>Math.abs(ddx)))return;if(dy&&(Math.sign(ddy)!==dy||Math.abs(ddx)>Math.abs(ddy)*2))return;const s=dx?Math.abs(ddx)+Math.abs(ddy)*3:Math.abs(ddy)+Math.abs(ddx)*.6;if(s<score){score=s;best=node}});return best}"
    "function arrows(selector,select,read){const list=[...root.querySelectorAll(selector)];list.forEach(node=>node.addEventListener('keydown',event=>{const step={ArrowRight:[1,0],ArrowLeft:[-1,0],ArrowDown:[0,1],ArrowUp:[0,-1]}[event.key];if(!step)return;const next=nearest(list,node,step[0],step[1]);if(!next)return;event.preventDefault();next.focus();select(read(next))}))}"
    # Arriving at a block, a line of its verdict runs once round it: slow in, a stretched fast pass with a glint,
    # slow out into a point, with an afterglow behind it that fades by the time since the line passed.
    "const BEAM={travel:920,delay:.085,shortest:1.2,step:.0057,tau:.055,glow:.52,trails:20};"
    "const beamEase=(()=>{const x1=.55,y1=0,x2=.28,y2=1;const bx=s=>3*x1*s*(1-s)*(1-s)+3*x2*s*s*(1-s)+s*s*s,by=s=>3*y1*s*(1-s)*(1-s)+3*y2*s*s*(1-s)+s*s*s;return u=>{if(u<=0)return 0;if(u>=1)return 1;let lo=0,hi=1;for(let i=0;i<26;i++){const m=(lo+hi)/2;if(bx(m)<u)lo=m;else hi=m}return by((lo+hi)/2)}})();"
    "let beamShapeCache=null;function beamShape(){if(beamShapeCache)return beamShapeCache;let longest=0,peak=.5;for(let i=0;i<=400;i++){const t=i/400,u=t*(1+BEAM.delay),l=(beamEase(u)-beamEase(u-BEAM.delay))*100;if(l>longest){longest=l;peak=t}}return beamShapeCache={longest,peak}}"
    "function beamGlint(t,peak){const rise=.12,fall=.26;if(t>peak-rise&&t<=peak){const x=(t-(peak-rise))/rise;return x*x*(3-2*x)}if(t>peak&&t<peak+fall)return Math.pow(1-(t-peak)/fall,2.2);return 0}"
    "function beamDash(rect,from,to,opacity,width){const len=Math.max(0,to-from);rect.style.strokeDasharray=len.toFixed(3)+' '+(100-len).toFixed(3);rect.style.strokeDashoffset=(len-to).toFixed(3);rect.style.opacity=(len>0?opacity:0).toFixed(3);if(width)rect.style.strokeWidth=width.toFixed(2)+'px'}"
    "function beamFrame(svg,t){const rects=[...svg.children],glow=rects[0],line=rects[rects.length-1],trails=rects.slice(1,-1);const shape=beamShape(),u=t*(1+BEAM.delay),head=beamEase(u)*100,tail=beamEase(u-BEAM.delay)*100,length=head-tail;const floor=t<.8?BEAM.shortest:BEAM.shortest-(BEAM.shortest-.3)*(t-.8)/.2,stroke=Math.max(length,floor);const share=Math.max(length-BEAM.shortest,0)/(shape.longest-BEAM.shortest);const fade=t<=0||t>=1?0:Math.min(1,t/.04,(1-t)/.1);beamDash(line,head-stroke,head,fade,1.3+1.5*Math.pow(share,.8));beamDash(glow,head-stroke,head,.9*beamGlint(t,shape.peak));const back=head-stroke;trails.forEach((rect,k)=>{const to=Math.min(back,beamEase(u-BEAM.delay-k*BEAM.step)*100),from=Math.min(to,beamEase(u-BEAM.delay-(k+1)*BEAM.step)*100);beamDash(rect,from,to,BEAM.glow*Math.exp(-(k+.5)*BEAM.step/BEAM.tau)*fade)})}"
    "function arrive(section){if(!section)return;const ns='http://www.w3.org/2000/svg',gap=7;let svg=section.querySelector(':scope>.arrive');if(!svg){svg=document.createElementNS(ns,'svg');svg.setAttribute('class','arrive');svg.setAttribute('aria-hidden','true');const kinds=['glow'];for(let k=0;k<BEAM.trails;k++)kinds.push('trail');kinds.push('line');kinds.forEach(kind=>{const rect=document.createElementNS(ns,'rect');rect.setAttribute('class',kind);rect.setAttribute('pathLength','100');svg.appendChild(rect)});section.appendChild(svg)}const w=section.offsetWidth+gap*2,h=section.offsetHeight+gap*2;svg.setAttribute('width',w);svg.setAttribute('height',h);svg.setAttribute('viewBox','0 0 '+w+' '+h);svg.style.left=-gap+'px';svg.style.top=-gap+'px';[...svg.children].forEach(rect=>{rect.setAttribute('x',1.5);rect.setAttribute('y',1.5);rect.setAttribute('width',w-3);rect.setAttribute('height',h-3);rect.setAttribute('rx',16)});svg.dataset.tone=section.dataset.tone||'na';cancelAnimationFrame(svg._beam);svg._frame=t=>beamFrame(svg,t);svg.classList.remove('run','still');void svg.getBoundingClientRect();if(matchMedia('(prefers-reduced-motion: reduce)').matches){[...svg.children].forEach(rect=>{rect.style.opacity='0'});const line=svg.lastChild;line.style.strokeDasharray='none';line.style.opacity='1';svg.classList.add('still');return}svg.classList.add('run');const duration=BEAM.travel*(1+BEAM.delay),start=performance.now();const tick=now=>{const t=Math.min(1,(now-start)/duration);beamFrame(svg,t);if(t<1)svg._beam=requestAnimationFrame(tick);else svg.classList.remove('run')};svg._beam=requestAnimationFrame(tick)}"
    # The header sits in a shell of its full height: the shell sticks, the card in it settles while it is stuck.
    "const verdictShell=root.querySelector('.verdict-shell'),verdictCard=verdictShell?verdictShell.querySelector('.verdict'):null;let settled=false,settleTick=false;"
    "function settleMeasure(){if(!verdictCard)return;verdictCard.classList.add('measuring');const was=verdictCard.classList.contains('settled');verdictCard.classList.remove('settled');const full=Math.ceil(verdictCard.getBoundingClientRect().height);verdictCard.classList.add('settled');const small=Math.ceil(verdictCard.getBoundingClientRect().height);verdictCard.classList.toggle('settled',was);void verdictCard.offsetHeight;requestAnimationFrame(()=>verdictCard.classList.remove('measuring'));verdictShell.style.minHeight=full+'px';root.style.setProperty('--verdict-h',small+'px')}"
    "function settleCheck(){settleTick=false;if(!verdictShell)return;const top=parseFloat(root.style.getPropertyValue('--sticky-top'))||0;const on=window.scrollY>2&&verdictShell.getBoundingClientRect().top<=top+.5;if(on===settled)return;settled=on;verdictCard.classList.toggle('settled',on);verdictShell.classList.toggle('stuck',on)}"
    "window.addEventListener('scroll',()=>{if(settleTick)return;settleTick=true;requestAnimationFrame(settleCheck)},{passive:true});"
    "if(document.fonts&&document.fonts.ready)document.fonts.ready.then(()=>{settleMeasure();settleCheck()});window.addEventListener('load',()=>{settleMeasure();settleCheck()});"
    # A link to a block scrolls there smoothly and lights it as the page comes in to land.
    "function travel(hash,push){const target=hash&&hash.startsWith('#')?root.querySelector(hash):null;if(!target||!target.classList.contains('section'))return false;const margin=parseFloat(getComputedStyle(target).scrollMarginTop)||0;const top=Math.max(0,Math.round(target.getBoundingClientRect().top+window.scrollY-margin));if(push&&location.hash!==hash)history.pushState(null,'',hash);const arrived=()=>flashTarget(hash);if(Math.abs(top-window.scrollY)<2||matchMedia('(prefers-reduced-motion: reduce)').matches){window.scrollTo(0,top);requestAnimationFrame(arrived);return true}let finished=false;const finish=()=>{if(finished)return;finished=true;clearTimeout(guard);window.removeEventListener('scrollend',finish);arrived()};const guard=setTimeout(finish,1500);window.addEventListener('scrollend',finish);const goal=Math.min(top,document.documentElement.scrollHeight-innerHeight);const near=()=>{if(finished)return;if(Math.abs(window.scrollY-goal)<40){finish();return}requestAnimationFrame(near)};window.scrollTo({top:top,behavior:'smooth'});requestAnimationFrame(near);return true}"
)


def monitor_script(
    *,
    setup_js: str,
    bind_js: str,
    nav_selector: str,
    init_js: str = "",
) -> str:
    return f"""<script id="tf-requirement-monitor-script">
(()=>{{const root=document.querySelector('#tf-requirement-monitor');if(!root)return;{setup_js}{MONITOR_BEHAVIOUR_JS}function syncSticky(){{const header=document.querySelector('.bd-header');const top=header?.getBoundingClientRect().bottom||0;root.style.setProperty('--sticky-top',top+'px');const verdict=root.querySelector('.verdict');root.style.setProperty('--verdict-h',(verdict?verdict.offsetHeight:0)+'px');settleMeasure();settleCheck()}}{bind_js}let flashTimer;function flashTarget(hash){{if(!hash||!hash.startsWith('#'))return;const target=root.querySelector(hash);if(!target||!target.classList.contains('section'))return;root.querySelectorAll('.section.nav-flash').forEach(node=>node.classList.remove('nav-flash'));void target.offsetWidth;target.classList.add('nav-flash');arrive(target);const attn=[...target.querySelectorAll('button.matrix-cell.not-met,button.matrix-cell.unknown,button.fault-tile.not-met,button.fault-tile.unknown,.technical-support-panel .not-met-signal,.technical-support-panel .unknown-signal,.linked-note.not-met')];attn.forEach(node=>{{node.classList.remove('attn');void node.offsetWidth;node.classList.add('attn')}});clearTimeout(flashTimer);flashTimer=setTimeout(()=>{{target.classList.remove('nav-flash');attn.forEach(node=>node.classList.remove('attn'))}},2200);}}document.querySelectorAll('{nav_selector}').forEach(link=>link.addEventListener('click',event=>{{if(travel(link.getAttribute('href'),true)){{event.preventDefault();return}}requestAnimationFrame(()=>flashTarget(link.getAttribute('href')))}}));window.addEventListener('hashchange',()=>flashTarget(location.hash));function syncAssurancePath(){{document.querySelectorAll('.tf-assurance-path').forEach(path=>{{const current=path.querySelector('.tf-assurance-crumb.current');if(!current)return;path.scrollLeft=Math.max(0,current.offsetLeft+current.offsetWidth-path.clientWidth);}});}}window.addEventListener('resize',()=>{{syncSticky();syncAssurancePath()}});syncSticky();syncAssurancePath();{init_js}if(location.hash)requestAnimationFrame(()=>flashTarget(location.hash));}})();
</script>"""


MONITOR_STYLE = '<style id="tf-requirement-monitor-style">\n.bd-article-container{overflow:visible!important}\n#tf-requirement-monitor{--surface:var(--pst-color-surface);--surface2:color-mix(in srgb,var(--pst-color-surface) 88%,var(--pst-color-background));--text:var(--pst-color-text-base);--muted:var(--pst-color-text-muted);--line:var(--pst-color-border);--green:#2e9d58;--red:#d24b4b;--amber:var(--pst-color-warning);--blue:var(--pst-color-primary);--shadow:0 .35rem 1rem color-mix(in srgb,#000 9%,transparent);--sticky-top:var(--pst-header-height,4rem);color:var(--text);font-size:.86rem;line-height:1.35}\n#tf-requirement-monitor *{box-sizing:border-box}#tf-requirement-monitor button{font:inherit;color:inherit}#tf-requirement-monitor a{color:inherit}.tf-exp-badge{display:inline-block;margin-left:.45rem;padding:.12rem .28rem;border:1px solid var(--pst-color-border);border-radius:.25rem;color:var(--pst-color-text-muted);font-size:.55rem;font-weight:800;letter-spacing:.06em;vertical-align:.18rem}\n#tf-requirement-monitor .verdict{position:sticky;top:var(--sticky-top);z-index:24;margin:.35rem 0 1rem;padding:.75rem .85rem;background:color-mix(in srgb,var(--pst-color-background) 94%,transparent);backdrop-filter:blur(8px);border:1px solid var(--line);border-radius:.45rem;box-shadow:var(--shadow)}#tf-requirement-monitor .verdict-main{display:flex;align-items:center;justify-content:space-between;gap:1rem}#tf-requirement-monitor .verdict-main>div:first-child{min-width:0}#tf-requirement-monitor .kicker,#tf-requirement-monitor .eyebrow{font-size:.62rem;font-weight:800;letter-spacing:.075em;text-transform:uppercase;color:var(--muted)}#tf-requirement-monitor h2{font-size:1rem;margin:.1rem 0 0;overflow-wrap:anywhere}#tf-requirement-monitor h3{font-size:.86rem;letter-spacing:.04em;text-transform:uppercase;margin:0}#tf-requirement-monitor .overall{font-size:.92rem;font-weight:900;padding:.42rem .65rem;border-radius:.45rem;border:1px solid var(--line);background:var(--surface);color:var(--muted)}#tf-requirement-monitor .overall.not-met{border-color:color-mix(in srgb,var(--red) 65%,var(--line));background:color-mix(in srgb,var(--red) 9%,var(--surface));color:var(--red)}#tf-requirement-monitor .overall.met{border-color:color-mix(in srgb,var(--green) 60%,var(--line));background:color-mix(in srgb,var(--green) 8%,var(--surface));color:var(--green)}#tf-requirement-monitor .overall.unknown{border-color:color-mix(in srgb,var(--amber) 60%,var(--line));background:color-mix(in srgb,var(--amber) 8%,var(--surface));color:var(--amber)}\n#tf-requirement-monitor .domain-strip{display:grid;grid-template-columns:1fr 1fr;gap:.45rem;margin-top:.55rem}#tf-requirement-monitor .domain-strip.with-support{grid-template-columns:repeat(3,minmax(0,1fr))}#tf-requirement-monitor .domain{display:grid;grid-template-columns:1fr auto;gap:.12rem .5rem;align-items:center;padding:.45rem .55rem;border:1px solid var(--line);border-radius:.4rem;background:var(--surface);text-decoration:none}#tf-requirement-monitor .domain:hover{border-color:var(--blue)}#tf-requirement-monitor .domain strong{font-size:.67rem;text-transform:uppercase;letter-spacing:.03em;color:var(--muted)}#tf-requirement-monitor .domain-meta{grid-column:1/-1;font-size:.58rem;color:var(--muted)}#tf-requirement-monitor .status{font-size:.63rem;font-weight:900;letter-spacing:.02em;white-space:nowrap}#tf-requirement-monitor .status.met{color:var(--green)}#tf-requirement-monitor .status.not-met{color:var(--red)}#tf-requirement-monitor .status.unknown{color:var(--amber)}#tf-requirement-monitor .status.na{color:var(--muted)}#tf-requirement-monitor .status.big{font-size:.72rem}\n#tf-requirement-monitor .section{position:relative;margin-top:1rem;scroll-margin-top:calc(var(--sticky-top) + 8.7rem);border-radius:.55rem}#tf-requirement-monitor .section.nav-flash{animation:tf-destination-flash 1.6s ease-out}@keyframes tf-destination-flash{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--blue) 0%,transparent)}16%{box-shadow:0 0 0 3px color-mix(in srgb,var(--blue) 72%,transparent)}68%{box-shadow:0 0 0 2px color-mix(in srgb,var(--blue) 42%,transparent)}100%{box-shadow:0 0 0 0 color-mix(in srgb,var(--blue) 0%,transparent)}}@media(prefers-reduced-motion:reduce){#tf-requirement-monitor .section.nav-flash{animation:tf-destination-flash-reduced .8s linear}}@keyframes tf-destination-flash-reduced{0%,70%{box-shadow:0 0 0 3px color-mix(in srgb,var(--blue) 58%,transparent)}100%{box-shadow:0 0 0 0 transparent}}#tf-requirement-monitor .section-head{display:flex;align-items:end;justify-content:space-between;gap:1rem;margin-bottom:.45rem}#tf-requirement-monitor .section-links{display:flex;gap:.55rem}#tf-requirement-monitor .section-link,#tf-requirement-monitor .drilldowns a{font-size:.62rem;color:var(--muted);text-decoration:none}#tf-requirement-monitor .section-link:hover,#tf-requirement-monitor .drilldowns a:hover{color:var(--text)}#tf-requirement-monitor .dashboard-layout{display:grid;grid-template-columns:minmax(0,1.12fr) minmax(19rem,.88fr);gap:.55rem;align-items:start}#tf-requirement-monitor .panel,#tf-requirement-monitor .inspector{border:1px solid var(--line);border-radius:.5rem;background:var(--surface);box-shadow:var(--shadow)}\n#tf-requirement-monitor .matrix-wrap{overflow-x:auto;padding:.38rem}#tf-requirement-monitor table{border-collapse:separate;border-spacing:.25rem;width:100%;margin:0}#tf-requirement-monitor th{font-size:.61rem;color:var(--muted);font-weight:700;text-align:left;white-space:nowrap;padding:.1rem}#tf-requirement-monitor thead th{text-align:center}#tf-requirement-monitor thead th:first-child{text-align:left}#tf-requirement-monitor td{padding:0}#tf-requirement-monitor .matrix-cell{width:100%;height:3.3rem;min-width:5.7rem;padding:.35rem .4rem;border:1px solid var(--line);border-radius:.4rem;background:var(--surface2);text-align:left}#tf-requirement-monitor button.matrix-cell{cursor:pointer}#tf-requirement-monitor button.matrix-cell:hover,#tf-requirement-monitor button.matrix-cell.selected{outline:2px solid color-mix(in srgb,var(--blue) 55%,transparent);outline-offset:1px}#tf-requirement-monitor .matrix-cell.not-met{border-color:color-mix(in srgb,var(--red) 58%,var(--line));background:color-mix(in srgb,var(--red) 7%,var(--surface))}#tf-requirement-monitor .matrix-cell.unknown{border-color:color-mix(in srgb,var(--amber) 58%,var(--line));background:color-mix(in srgb,var(--amber) 6%,var(--surface))}#tf-requirement-monitor .matrix-cell.met{border-color:color-mix(in srgb,var(--green) 55%,var(--line));background:color-mix(in srgb,var(--green) 6%,var(--surface))}#tf-requirement-monitor .matrix-cell.na{display:grid;place-items:center;border-color:transparent;background:color-mix(in srgb,var(--surface2) 45%,transparent);color:var(--muted);text-align:center}#tf-requirement-monitor .cell-status{display:block;margin-bottom:.22rem}#tf-requirement-monitor .cell-values{display:grid;grid-template-columns:1fr 1fr;gap:.3rem}#tf-requirement-monitor .cell-values small{display:block;font-size:.5rem;color:var(--muted);text-transform:uppercase}#tf-requirement-monitor .cell-values strong{font-size:.82rem}\n#tf-requirement-monitor .technical-support-panel{padding:.55rem}\n#tf-requirement-monitor .technical-support-panel .signal-grid{grid-template-columns:repeat(auto-fit,minmax(15rem,1fr))}#tf-requirement-monitor .inspector{padding:.55rem}#tf-requirement-monitor .inspector-head{display:flex;align-items:start;justify-content:space-between;gap:.7rem;margin-bottom:.5rem}#tf-requirement-monitor .signal-grid{display:grid;grid-template-columns:1fr;gap:.48rem}#tf-requirement-monitor .signal-group{display:grid;gap:.28rem;padding:.38rem;border:1px solid color-mix(in srgb,var(--line) 82%,transparent);border-radius:.46rem;background:color-mix(in srgb,var(--surface2) 54%,transparent)}#tf-requirement-monitor .signal-group-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.45rem;padding:0 .04rem .26rem;border-bottom:1px solid color-mix(in srgb,var(--line) 72%,transparent)}#tf-requirement-monitor .signal-group-head>strong,#tf-requirement-monitor .signal-group-head>div>strong{font-size:.57rem;letter-spacing:.065em;text-transform:uppercase;color:var(--muted)}#tf-requirement-monitor .group-scope{font-size:.52rem;font-weight:800;color:var(--muted);white-space:nowrap}#tf-requirement-monitor .representation-stack{display:grid;gap:.22rem}#tf-requirement-monitor .dependent-wrap{margin-left:.72rem;padding-left:.5rem;border-left:2px solid color-mix(in srgb,var(--line) 78%,transparent)}#tf-requirement-monitor .dependent-signal{background:color-mix(in srgb,var(--surface2) 38%,transparent);border-style:dashed}#tf-requirement-monitor .confidence-subgroup{display:grid;gap:.28rem;margin-top:.12rem;padding-top:.38rem;border-top:1px solid color-mix(in srgb,var(--line) 72%,transparent)}#tf-requirement-monitor .subgroup-head strong{font-size:.57rem;letter-spacing:.065em;text-transform:uppercase;color:var(--muted)}#tf-requirement-monitor .confidence-grid{display:grid;gap:.28rem}#tf-requirement-monitor .signal-card{border:1px solid var(--line);border-radius:.4rem;background:var(--surface2);padding:.38rem .42rem}#tf-requirement-monitor .signal-card.met-signal{border-color:color-mix(in srgb,var(--green) 42%,var(--line))}#tf-requirement-monitor .signal-card.not-met-signal{border-color:color-mix(in srgb,var(--red) 50%,var(--line))}#tf-requirement-monitor .signal-card.unknown-signal{border-color:color-mix(in srgb,var(--amber) 45%,var(--line))}#tf-requirement-monitor .signal-card.na-signal{background:color-mix(in srgb,var(--surface2) 35%,transparent);border-style:dashed;padding:.34rem .4rem}#tf-requirement-monitor .na-signal .signal-head strong{color:var(--muted)}#tf-requirement-monitor .na-signal .state-option{color:color-mix(in srgb,var(--muted) 78%,transparent);border-color:color-mix(in srgb,var(--line) 70%,transparent);background:color-mix(in srgb,var(--surface) 70%,transparent)}#tf-requirement-monitor .na-signal .state-option.selected{color:var(--muted);border-color:color-mix(in srgb,var(--muted) 55%,var(--line))}#tf-requirement-monitor .signal-head{display:flex;align-items:center;justify-content:space-between;gap:.45rem;font-size:.67rem}#tf-requirement-monitor .signal-rule{display:flex;align-items:center;gap:.35rem}#tf-requirement-monitor .scope-count{display:inline-flex;align-items:baseline;gap:.16rem;padding:.1rem .24rem;border:1px solid var(--line);border-radius:.28rem;background:var(--surface);white-space:nowrap}#tf-requirement-monitor .scope-count b{font-size:.55rem}#tf-requirement-monitor .scope-count small{font-size:.44rem;color:var(--muted)}#tf-requirement-monitor .scope-count.met{border-color:color-mix(in srgb,var(--green) 42%,var(--line))}#tf-requirement-monitor .scope-count.not-met{border-color:color-mix(in srgb,var(--red) 48%,var(--line))}#tf-requirement-monitor .scope-count.unknown{border-color:color-mix(in srgb,var(--amber) 46%,var(--line))}#tf-requirement-monitor .coverage-summary{display:flex;align-items:baseline;gap:.38rem;margin-top:.28rem}#tf-requirement-monitor .coverage-summary>strong{font-size:1.08rem;line-height:1}#tf-requirement-monitor .coverage-summary>strong span{font-size:.7rem;color:var(--muted);margin:0 .05rem}#tf-requirement-monitor .coverage-summary small{font-size:.52rem;color:var(--muted)}#tf-requirement-monitor .coverage-strip{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:.18rem;margin-top:.34rem}#tf-requirement-monitor .coverage-segment{height:.28rem;border-radius:999px;background:var(--line)}#tf-requirement-monitor .coverage-segment.pass{background:var(--green)}#tf-requirement-monitor .coverage-segment.fail{background:var(--red)}#tf-requirement-monitor .coverage-segment.missing{background:transparent;border:1px dashed var(--red)}#tf-requirement-monitor .coverage-counts{display:flex;gap:.45rem;margin-top:.25rem;font-size:.48rem;font-weight:700;color:var(--muted)}#tf-requirement-monitor .coverage-counts .pass{color:var(--green)}#tf-requirement-monitor .coverage-counts .fail,#tf-requirement-monitor .coverage-counts .missing{color:var(--red)}#tf-requirement-monitor .metric-values{display:grid;grid-template-columns:1fr 1fr;gap:.28rem;margin-top:.32rem}#tf-requirement-monitor .metric-values div{padding:.28rem .32rem;border-radius:.3rem;background:var(--surface)}#tf-requirement-monitor .metric-values span{display:block;font-size:.49rem;color:var(--muted);text-transform:uppercase}#tf-requirement-monitor .metric-values strong{display:block;font-size:.78rem;margin-top:.05rem}#tf-requirement-monitor .state-lane{display:flex;gap:.22rem;flex-wrap:wrap;margin-top:.32rem}#tf-requirement-monitor .state-option{display:inline-flex;align-items:center;gap:.22rem;padding:.2rem .3rem;border:1px solid var(--line);border-radius:.3rem;background:var(--surface);font-size:.55rem;color:var(--muted)}#tf-requirement-monitor .state-option.selected{color:var(--text);border-color:var(--blue)}#tf-requirement-monitor .marker{font-size:.43rem;font-weight:900;padding:.08rem .16rem;border-radius:.2rem;white-space:nowrap}#tf-requirement-monitor .marker.both{background:color-mix(in srgb,var(--blue) 13%,var(--surface));color:var(--blue)}#tf-requirement-monitor .marker.actual{background:color-mix(in srgb,var(--green) 12%,var(--surface));color:var(--green)}#tf-requirement-monitor .marker.target{background:color-mix(in srgb,var(--blue) 12%,var(--surface));color:var(--blue)}#tf-requirement-monitor .marker.inactive{background:color-mix(in srgb,var(--muted) 12%,var(--surface));color:var(--muted)}\n#tf-requirement-monitor .help{position:relative;display:inline-grid;place-items:center;width:.82rem;height:.82rem;border:1px solid var(--line);border-radius:50%;font-size:.5rem;color:var(--muted);cursor:help;vertical-align:.08rem;text-transform:none;letter-spacing:normal}#tf-requirement-monitor .help-tip{position:absolute;z-index:50;left:50%;bottom:1rem;transform:translateX(-50%);width:15rem;max-width:calc(100vw - 2rem);padding:.36rem .42rem;border:1px solid color-mix(in srgb,var(--line) 82%,var(--text));border-radius:.3rem;background:var(--pst-color-background);box-shadow:0 .45rem 1.4rem rgba(0,0,0,.28);font-size:.55rem;font-weight:600;color:var(--text);line-height:1.35;text-transform:none;letter-spacing:normal;opacity:0;visibility:hidden;pointer-events:none}#tf-requirement-monitor .help:hover .help-tip,#tf-requirement-monitor .help:focus .help-tip{opacity:1;visibility:visible}#tf-requirement-monitor .signal-group-head>.help .help-tip{left:auto;right:0;transform:none}#tf-requirement-monitor .tile-metrics .help{display:inline-grid;font-size:.5rem;color:var(--muted)}#tf-requirement-monitor .tile-metrics .help-tip{font-size:.55rem;color:var(--text)}#tf-requirement-monitor .drilldowns{display:flex;justify-content:flex-end;gap:.55rem;margin-top:.45rem;padding-top:.4rem;border-top:1px solid var(--line)}\n#tf-requirement-monitor .fault-layout{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(19rem,.95fr);gap:.55rem;align-items:start}#tf-requirement-monitor .fault-layout>*{min-width:0}#tf-requirement-monitor .inspector-head>div{min-width:0}#tf-requirement-monitor .inspector-head h3{overflow-wrap:anywhere}#tf-requirement-monitor .fault-layout.no-inspector{grid-template-columns:1fr}#tf-requirement-monitor .fault-layout.no-inspector .fault-grid{grid-template-columns:repeat(5,minmax(0,1fr))}#tf-requirement-monitor .fault-grid{display:grid;grid-template-columns:1fr 1fr;gap:.38rem}#tf-requirement-monitor .fault-tile{min-height:5.3rem;padding:.48rem;border:1px solid var(--line);border-radius:.42rem;background:var(--surface);text-align:left}#tf-requirement-monitor button.fault-tile{cursor:pointer}#tf-requirement-monitor button.fault-tile:hover,#tf-requirement-monitor button.fault-tile.selected{outline:2px solid color-mix(in srgb,var(--blue) 55%,transparent);outline-offset:1px}#tf-requirement-monitor .fault-tile.not-met{border-color:color-mix(in srgb,var(--red) 55%,var(--line))}#tf-requirement-monitor .fault-tile.met{border-color:color-mix(in srgb,var(--green) 50%,var(--line))}#tf-requirement-monitor .fault-tile.na{background:color-mix(in srgb,var(--surface2) 45%,transparent);color:var(--muted);border-style:dashed}#tf-requirement-monitor .tile-head{display:flex;align-items:start;justify-content:space-between;gap:.4rem;font-size:.61rem}#tf-requirement-monitor .tile-metrics{display:grid;grid-template-columns:1fr 1fr;gap:.28rem;margin-top:.5rem}#tf-requirement-monitor .tile-metrics div{padding:.28rem .32rem;border-radius:.3rem;background:var(--surface2)}#tf-requirement-monitor .tile-metrics span{display:block;font-size:.49rem;color:var(--muted)}#tf-requirement-monitor .tile-metrics strong{font-size:.72rem}#tf-requirement-monitor .tile-metrics i{font-size:.49rem;color:var(--muted);font-style:normal;margin-left:.16rem}#tf-requirement-monitor .tile-metrics .not-met strong{color:var(--red)}#tf-requirement-monitor .na-center{display:flex;align-items:center;justify-content:center;gap:.4rem;height:3rem;font-size:.61rem;color:var(--muted)}#tf-requirement-monitor .fault-signals{grid-template-columns:1fr}#tf-requirement-monitor .fault-chain{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr) auto minmax(0,1fr);align-items:stretch;gap:.28rem}\n#tf-requirement-monitor .fault-chain.mutant-tally{grid-template-columns:repeat(auto-fit,minmax(4.6rem,1fr))}\n#tf-requirement-monitor .history-changes{grid-column:1/-1;color:var(--muted);font-size:.72rem;min-height:1.1em}#tf-requirement-monitor .fault-chain>i{align-self:center;color:var(--muted);font-style:normal;font-weight:800}#tf-requirement-monitor .fault-stage{display:grid;grid-template-columns:1fr auto;gap:.12rem .35rem;align-items:center;padding:.36rem .42rem;border:1px solid var(--line);border-radius:.38rem;background:var(--surface)}#tf-requirement-monitor .fault-stage>span{font-size:.5rem;color:var(--muted)}#tf-requirement-monitor .fault-stage>strong{font-size:.82rem}#tf-requirement-monitor .fault-stage>small{grid-column:1/-1;font-size:.47rem;color:var(--muted)}#tf-requirement-monitor .fault-stage>.status{justify-self:end}#tf-requirement-monitor .fault-stage.met{border-color:color-mix(in srgb,var(--green) 42%,var(--line))}#tf-requirement-monitor .fault-stage.not-met{border-color:color-mix(in srgb,var(--red) 50%,var(--line))}#tf-requirement-monitor .fault-stage.unknown{border-color:color-mix(in srgb,var(--amber) 45%,var(--line))}\n#tf-requirement-monitor .history{display:flex;align-items:center;gap:.55rem;padding:.55rem .65rem}#tf-requirement-monitor .history-line{flex:1;height:2px;background:var(--line);position:relative}#tf-requirement-monitor .history-point{position:absolute;right:0;top:50%;transform:translate(50%,-50%);width:.5rem;height:.5rem;border-radius:50%;background:var(--muted);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--muted) 12%,transparent)}#tf-requirement-monitor .history-point.not-met{background:var(--red);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--red) 12%,transparent)}#tf-requirement-monitor .history-point.met{background:var(--green);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--green) 12%,transparent)}#tf-requirement-monitor .history-point.unknown{background:var(--amber);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--amber) 12%,transparent)}#tf-requirement-monitor .history strong{font-size:.67rem}#tf-requirement-monitor .linked-note{display:grid;gap:.18rem;margin:.35rem .25rem .15rem;padding:.38rem .45rem;border:1px dashed var(--line);border-radius:.38rem;font-size:.58rem;color:var(--muted)}#tf-requirement-monitor .linked-note strong{font-weight:700;color:var(--text)}#tf-requirement-monitor .linked-note.not-met{border-style:solid;border-color:color-mix(in srgb,var(--red) 55%,var(--line))}#tf-requirement-monitor .linked-note.not-met strong{color:var(--red)}\n@media(max-width:1200px){#tf-requirement-monitor .dashboard-layout,#tf-requirement-monitor .fault-layout{grid-template-columns:1fr}#tf-requirement-monitor .confidence-grid{grid-template-columns:repeat(3,minmax(0,1fr))}#tf-requirement-monitor .fault-grid,#tf-requirement-monitor .fault-layout.no-inspector .fault-grid{grid-template-columns:repeat(3,1fr)}#tf-requirement-monitor .fault-tile:nth-child(3n+1) .tile-metrics .help-tip{left:0;transform:none}}@media(max-width:760px){#tf-requirement-monitor .domain-strip,#tf-requirement-monitor .domain-strip.with-support{grid-template-columns:1fr}#tf-requirement-monitor .confidence-grid{grid-template-columns:1fr}#tf-requirement-monitor .fault-grid,#tf-requirement-monitor .fault-layout.no-inspector .fault-grid{grid-template-columns:1fr 1fr}#tf-requirement-monitor .fault-signals{grid-template-columns:1fr}#tf-requirement-monitor .help-tip{position:fixed;left:1rem!important;right:1rem!important;bottom:1rem!important;width:auto;max-width:none;transform:none!important}#tf-requirement-monitor .fault-tile:nth-child(odd) .tile-metrics .help-tip{left:1rem;transform:none}}\n</style>'

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
# Readable sizes, the matrix cell's count and cause, detail cards that keep their tallest height.
READABLE_STYLE = r"""
/* round 4 · readable sizes: nothing on the monitor below ~10px */
#tf-requirement-monitor{font-size:.9rem}
#tf-requirement-monitor .kicker,#tf-requirement-monitor .eyebrow{font-size:.66rem}
#tf-requirement-monitor .verdict h2{font-size:1.14rem;line-height:1.25;margin-top:.12rem}
#tf-requirement-monitor .verdict-id{display:flex;flex-wrap:wrap;align-items:baseline;gap:.15rem .7rem;margin-top:.2rem;font-size:.72rem;color:var(--muted)}
#tf-requirement-monitor .verdict-id code{padding:.05rem .35rem;border:1px solid var(--line);border-radius:.3rem;background:var(--surface);color:var(--text);font-size:.7rem}
#tf-requirement-monitor .verdict-id .section-link{font-size:.72rem}
#tf-requirement-monitor .overall{font-size:.95rem}
#tf-requirement-monitor .domain strong{font-size:.7rem}
#tf-requirement-monitor .domain-meta{font-size:.74rem}
#tf-requirement-monitor .status{font-size:.7rem}
#tf-requirement-monitor .status.big{font-size:.8rem}
#tf-requirement-monitor h3{font-size:.9rem}
#tf-requirement-monitor .section-link,#tf-requirement-monitor .drilldowns a{font-size:.72rem}
#tf-requirement-monitor th{font-size:.72rem}
#tf-requirement-monitor .signal-group-head>strong,#tf-requirement-monitor .signal-group-head>div>strong,#tf-requirement-monitor .subgroup-head strong{font-size:.64rem}
#tf-requirement-monitor .group-scope{font-size:.66rem}
#tf-requirement-monitor .signal-head{font-size:.78rem}
#tf-requirement-monitor .scope-count b{font-size:.68rem}
#tf-requirement-monitor .scope-count small{font-size:.6rem}
#tf-requirement-monitor .coverage-summary>strong{font-size:1.2rem}
#tf-requirement-monitor .coverage-summary small{font-size:.7rem}
#tf-requirement-monitor .coverage-counts{font-size:.66rem;flex-wrap:wrap}
#tf-requirement-monitor .state-option{font-size:.68rem;padding:.24rem .36rem}
#tf-requirement-monitor .marker{font-size:.56rem}
#tf-requirement-monitor .help{width:.95rem;height:.95rem;font-size:.6rem}
#tf-requirement-monitor .help-tip{font-size:.72rem;width:17rem}
#tf-requirement-monitor .tile-head{font-size:.76rem}
#tf-requirement-monitor .tile-metrics span{font-size:.64rem}
#tf-requirement-monitor .tile-metrics strong{font-size:.95rem}
#tf-requirement-monitor .tile-metrics i{font-size:.66rem}
#tf-requirement-monitor .tile-metrics .unknown strong{color:var(--amber)}
#tf-requirement-monitor .fault-stage>span{font-size:.66rem}
#tf-requirement-monitor .fault-stage>strong{font-size:.95rem}
#tf-requirement-monitor .fault-stage>small{font-size:.6rem}
#tf-requirement-monitor .history strong{font-size:.78rem}
#tf-requirement-monitor .linked-note{font-size:.72rem}
/* the matrix cell: its verdict, its count, and a word only when the count does not explain the verdict */
#tf-requirement-monitor .matrix-cell{height:auto;min-height:4rem;min-width:4.6rem}
#tf-requirement-monitor tbody th{white-space:normal;min-width:5.6rem;line-height:1.2}
#tf-requirement-monitor .cell-count{display:flex;align-items:baseline;gap:.3rem}
#tf-requirement-monitor .cell-count strong{font-size:1.15rem;line-height:1}
#tf-requirement-monitor .cell-count strong span{color:var(--muted);font-size:.8rem;margin:0 .04rem}
#tf-requirement-monitor .cell-count small{font-size:.68rem;color:var(--muted)}
#tf-requirement-monitor .cell-cause{display:block;margin-top:.22rem;font-size:.66rem;font-weight:800}
/* nothing jumps: an inspector keeps the height of its tallest selection */
#tf-requirement-monitor .inspector.stack{display:grid}
#tf-requirement-monitor .inspector.stack>.ins-layer{grid-area:1/1;min-width:0}
#tf-requirement-monitor .inspector.stack>.ins-layer:not(.on){visibility:hidden}
#tf-requirement-monitor .unknown.attn,#tf-requirement-monitor .unknown-signal.attn{--attn:var(--amber)}
#tf-requirement-monitor .drilldowns{flex-wrap:wrap;row-gap:.25rem}
#tf-requirement-monitor .section-head{flex-wrap:wrap;row-gap:.2rem}
#tf-requirement-monitor .section-links{flex-wrap:wrap;justify-content:flex-end;row-gap:.15rem}
#tf-requirement-monitor .section-link{white-space:nowrap}
@media(max-width:760px){#tf-requirement-monitor .matrix-cell{min-width:3.3rem;padding:.3rem}#tf-requirement-monitor tbody th{min-width:4.4rem;font-size:.66rem}#tf-requirement-monitor .cell-count small{display:none}#tf-requirement-monitor table{border-spacing:.18rem}}
#tf-requirement-monitor .drilldowns a{white-space:nowrap}
#tf-requirement-monitor .fault-chain.mutant-tally{grid-template-columns:repeat(auto-fit,minmax(6.4rem,1fr))}
/* air: the slots the profile leaves empty */
#tf-requirement-monitor .fault-tile.air .na-center{height:2.4rem}
"""
# A scale as one track, low to high.
TRACK_STYLE = r"""
#tf-requirement-monitor .track-row{display:flex;flex-wrap:wrap;align-items:stretch;gap:.3rem .4rem;margin-top:.38rem}
#tf-requirement-monitor .track{flex:1 1 100%;display:grid;grid-template-columns:repeat(var(--n),minmax(0,1fr));border:1px solid var(--line);border-radius:.5rem;overflow:hidden}
#tf-requirement-monitor .seg{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.1rem;min-height:2rem;padding:.22rem .25rem;border-left:1px solid var(--line);font-size:.66rem;line-height:1.15;text-align:center;color:var(--muted)}
#tf-requirement-monitor .seg:first-child{border-left:0}
#tf-requirement-monitor .seg.actual,#tf-requirement-monitor .seg.target,#tf-requirement-monitor .off.actual,#tf-requirement-monitor .off.target{color:var(--pst-color-text-base);font-weight:700}
#tf-requirement-monitor .met-signal .actual{background:color-mix(in srgb,var(--green) 18%,transparent)}
#tf-requirement-monitor .not-met-signal .actual{background:color-mix(in srgb,var(--red) 18%,transparent)}
#tf-requirement-monitor .unknown-signal .actual{background:color-mix(in srgb,var(--amber) 20%,transparent)}
#tf-requirement-monitor .seg.target,#tf-requirement-monitor .off.target{box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--pst-color-text-base) 60%,transparent)}
#tf-requirement-monitor .tmark{font-style:normal;font-size:.5rem;font-weight:800;letter-spacing:.05em;opacity:.75;line-height:1.1}
#tf-requirement-monitor .track-off{display:flex;flex-wrap:wrap;align-items:stretch;gap:.25rem}
#tf-requirement-monitor .track-off:empty{display:none}
#tf-requirement-monitor .off{display:inline-flex;align-items:center;justify-content:center;gap:.35rem;min-height:1.45rem;padding:.08rem .45rem;border:1px dashed var(--line);border-radius:.5rem;font-size:.6rem;color:var(--muted)}
#tf-requirement-monitor .off.actual,#tf-requirement-monitor .off.target,#tf-requirement-monitor .off.inactive{border-style:solid}
#tf-requirement-monitor .off.inactive{background:color-mix(in srgb,var(--pst-color-text-base) 7%,transparent)}
#tf-requirement-monitor .na-signal .track{opacity:.55}
"""
# The look: the Health Map's sizes, lines and colours; a quiet pass, a loud failure.
LOOK_STYLE = r"""
#tf-requirement-monitor{--line:color-mix(in srgb,var(--pst-color-text-base) 13%,transparent);--line-strong:color-mix(in srgb,var(--pst-color-text-base) 28%,transparent);--surface:color-mix(in srgb,var(--pst-color-text-base) 4.5%,var(--pst-color-background));--raised:color-mix(in srgb,var(--pst-color-text-base) 8%,var(--pst-color-background));--surface2:var(--raised);--muted:var(--pst-color-text-muted);--blue:color-mix(in srgb,var(--pst-color-text-base) 55%,transparent);--green:#1f7a3f;--red:#c42b34;--amber:#8f5f00;--fill-pass:#8ed3a2;--fill-fail:#dc3f47;--fill-unknown:#f0bf4c;--fill-na:#dde0e5;--gap:var(--pst-color-background);--shadow:none;font-size:.8rem;font-variant-numeric:tabular-nums}
html[data-theme=dark] #tf-requirement-monitor{--green:#5fcf85;--red:#ff6b70;--amber:#f0b64a;--fill-pass:#22603a;--fill-fail:#e5484d;--fill-unknown:#a8761a;--fill-na:#2f353d}
/* type: the map's scale; titles and labels in sentence case, as in A */
#tf-requirement-monitor h3,#tf-requirement-monitor .kicker,#tf-requirement-monitor .eyebrow,#tf-requirement-monitor .signal-group-head>strong,#tf-requirement-monitor .signal-group-head>div>strong,#tf-requirement-monitor .subgroup-head strong,#tf-requirement-monitor .domain strong,#tf-requirement-monitor .inspector-head h3{text-transform:none;letter-spacing:0}
#tf-requirement-monitor h3{font-size:.92rem;font-weight:700}
#tf-requirement-monitor .kicker,#tf-requirement-monitor .eyebrow{font-size:.72rem;font-weight:600;color:var(--muted)}
#tf-requirement-monitor .verdict h2{margin-top:.1rem;font-size:1.18rem;font-weight:700;line-height:1.25}
#tf-requirement-monitor .verdict-id{gap:.15rem .8rem;margin-top:.25rem;font-size:.72rem}
#tf-requirement-monitor .verdict-id code{padding:.06rem .4rem;border:1px solid var(--line);border-radius:5px;background:var(--surface);font-size:.68rem}
#tf-requirement-monitor .signal-group-head>strong,#tf-requirement-monitor .signal-group-head>div>strong,#tf-requirement-monitor .subgroup-head strong{font-size:.72rem;font-weight:650;color:var(--muted)}
#tf-requirement-monitor .group-scope{font-size:.72rem;font-weight:600;color:var(--muted)}
#tf-requirement-monitor .signal-head{font-size:.78rem}
#tf-requirement-monitor .signal-head strong{font-weight:650}
#tf-requirement-monitor .inspector-head h3{font-size:.98rem;font-weight:700}
#tf-requirement-monitor thead th{font-size:.66rem;font-weight:700;color:var(--muted)}
#tf-requirement-monitor tbody th{font-size:.7rem;font-weight:650;color:var(--pst-color-text-base)}
#tf-requirement-monitor .section-link,#tf-requirement-monitor .drilldowns a{font-size:.72rem;color:var(--muted);transition:color .15s ease}
#tf-requirement-monitor .section-link:hover,#tf-requirement-monitor .drilldowns a:hover{color:var(--pst-color-text-base)}
#tf-requirement-monitor .help{width:.9rem;height:.9rem;border-color:var(--line);font-size:.56rem}
#tf-requirement-monitor .help-tip{font-size:.72rem}
/* verdicts: a pass is quiet, a failure is the loudest thing on the page, each with the map's glyph */
#tf-requirement-monitor .status{display:inline-flex;align-items:center;gap:.3rem;font-size:.7rem;font-weight:750;letter-spacing:.02em}
#tf-requirement-monitor .status.met{color:var(--green);font-weight:650}
#tf-requirement-monitor .status.not-met{padding:.08rem .48rem;border-radius:999px;background:color-mix(in srgb,var(--fill-fail) 18%,transparent);color:var(--red)}
#tf-requirement-monitor .status.unknown{padding:.08rem .48rem;border-radius:999px;background:color-mix(in srgb,var(--fill-unknown) 22%,transparent);color:var(--amber)}
#tf-requirement-monitor .status.na{color:var(--muted);font-weight:600}
#tf-requirement-monitor .status.big{font-size:.72rem}
#tf-requirement-monitor .overall{display:inline-flex;align-items:center;gap:.45rem;padding:.36rem .8rem;border:0;border-radius:999px;font-size:.84rem;font-weight:800;letter-spacing:.03em}
#tf-requirement-monitor .overall.not-met{background:color-mix(in srgb,var(--fill-fail) 20%,transparent);color:var(--red)}
#tf-requirement-monitor .overall.met{background:color-mix(in srgb,var(--fill-pass) 24%,transparent);color:var(--green)}
#tf-requirement-monitor .overall.unknown{background:color-mix(in srgb,var(--fill-unknown) 24%,transparent);color:var(--amber)}
/* the verdict: one card; its domains split by hairlines, each with the picture of its section */
#tf-requirement-monitor .verdict{padding:.85rem 1rem .7rem;border:1px solid var(--line);border-radius:12px;background:color-mix(in srgb,var(--pst-color-background) 93%,transparent);box-shadow:0 8px 24px rgba(0,0,0,.12)}
#tf-requirement-monitor .domain-strip,#tf-requirement-monitor .domain-strip.with-support{gap:0;margin-top:.7rem;padding-top:.15rem;border-top:1px solid var(--line)}
#tf-requirement-monitor .domain{grid-template-columns:minmax(0,1fr) auto;grid-template-rows:auto auto auto;column-gap:.8rem;row-gap:.12rem;padding:.5rem .7rem .42rem;border:0;border-radius:10px;background:transparent;transition:background-color .18s ease}
#tf-requirement-monitor .domain+.domain{border-radius:0 10px 10px 0;box-shadow:inset 1px 0 0 var(--line)}
#tf-requirement-monitor .domain:hover{border:0;background:var(--surface)}
#tf-requirement-monitor .domain strong{grid-column:1;font-size:.78rem;font-weight:650;color:var(--pst-color-text-base)}
#tf-requirement-monitor .domain .status{grid-column:1;justify-self:start}
#tf-requirement-monitor .domain-meta{grid-column:1;font-size:.72rem;color:var(--muted)}
#tf-requirement-monitor .domain .thumb{grid-column:2;grid-row:1/span 3;align-self:center}
#tf-requirement-monitor .thumb{display:grid;gap:2px}
#tf-requirement-monitor .thumb-matrix{grid-template-columns:repeat(4,11px);grid-auto-rows:7px}
#tf-requirement-monitor .thumb-strip{grid-template-columns:repeat(var(--n),11px);grid-auto-rows:22px}
#tf-requirement-monitor .thumb i,#tf-requirement-monitor .thumb .t{border-radius:2px;background:color-mix(in srgb,var(--pst-color-text-base) 9%,transparent)}
#tf-requirement-monitor .thumb .met{background:var(--fill-pass)}
#tf-requirement-monitor .thumb .not-met{background:var(--fill-fail)}
#tf-requirement-monitor .thumb .unknown{background:var(--fill-unknown)}
/* the map's legend under a section */
#tf-requirement-monitor .map-legend{display:flex;flex-wrap:wrap;align-items:center;gap:.25rem .9rem;margin:.5rem .25rem .1rem;font-size:.72rem;color:var(--muted)}
#tf-requirement-monitor .map-legend .q{margin-right:.2rem;color:var(--pst-color-text-base);font-weight:600}
#tf-requirement-monitor .map-legend span{display:inline-flex;align-items:center;gap:.35rem}
#tf-requirement-monitor .map-legend b{color:var(--pst-color-text-base)}
#tf-requirement-monitor .map-legend i{display:inline-block;width:4px;height:.8rem;border-radius:2px;background:var(--line-strong)}
#tf-requirement-monitor .map-legend i.met{background:var(--fill-pass)}
#tf-requirement-monitor .map-legend i.not-met{background:var(--fill-fail)}
#tf-requirement-monitor .map-legend i.unknown{background:var(--fill-unknown)}
#tf-requirement-monitor .map-legend i.na{width:5px;height:5px;margin:0 .1rem;border-radius:50%;background:color-mix(in srgb,var(--pst-color-text-base) 26%,transparent)}
/* blocks: one quiet surface each, hairlines inside, no box in a box */
#tf-requirement-monitor .section{margin-top:1.15rem;border-radius:14px}
#tf-requirement-monitor .section-head{margin-bottom:.5rem}
#tf-requirement-monitor .panel,#tf-requirement-monitor .history{border:1px solid var(--line);border-radius:12px;background:var(--surface);box-shadow:none}
#tf-requirement-monitor .inspector{padding:.75rem .85rem .6rem;border:1px solid var(--line);border-radius:12px;background:var(--surface);box-shadow:none}
#tf-requirement-monitor .inspector-head{margin-bottom:.45rem}
#tf-requirement-monitor .signal-grid{gap:0}
#tf-requirement-monitor .signal-group{gap:.1rem;padding:.55rem 0 .3rem;border:0;border-top:1px solid var(--line);border-radius:0;background:transparent}
#tf-requirement-monitor .signal-group-head{padding:0 0 .2rem;border:0}
#tf-requirement-monitor .signal-card,#tf-requirement-monitor .signal-card.na-signal,#tf-requirement-monitor .dependent-signal{padding:.38rem 0;border:0;border-radius:0;background:transparent}
#tf-requirement-monitor .confidence-subgroup{margin-top:.15rem;padding-top:.45rem;border-top:1px solid var(--line)}
#tf-requirement-monitor .dependent-wrap{margin-left:.3rem;padding-left:.75rem;border-left:2px solid var(--line)}
#tf-requirement-monitor .scope-count,#tf-requirement-monitor .scope-count.met,#tf-requirement-monitor .scope-count.not-met,#tf-requirement-monitor .scope-count.unknown{padding:0;border:0;background:transparent;color:var(--muted)}
#tf-requirement-monitor .scope-count b{font-size:.74rem;color:var(--pst-color-text-base)}
#tf-requirement-monitor .scope-count small{font-size:.66rem}
#tf-requirement-monitor .coverage-summary>strong{font-size:1rem;font-weight:750}
#tf-requirement-monitor .coverage-summary small{font-size:.7rem}
#tf-requirement-monitor .coverage-strip{gap:.2rem}
#tf-requirement-monitor .coverage-segment{height:4px}
#tf-requirement-monitor .coverage-counts{font-size:.66rem}
#tf-requirement-monitor .fault-stage{border:0;border-radius:8px;background:var(--raised)}
#tf-requirement-monitor .fault-stage>strong{font-size:.95rem;font-weight:750}
#tf-requirement-monitor .fault-stage>span{font-size:.66rem;color:var(--muted)}
#tf-requirement-monitor .fault-stage.met,#tf-requirement-monitor .fault-stage.not-met,#tf-requirement-monitor .fault-stage.unknown{border:0}
#tf-requirement-monitor .fault-stage.not-met{box-shadow:inset 3px 0 0 var(--fill-fail)}
#tf-requirement-monitor .fault-stage.unknown{box-shadow:inset 3px 0 0 var(--fill-unknown)}
#tf-requirement-monitor .fault-stage.met{box-shadow:inset 3px 0 0 var(--fill-pass)}
#tf-requirement-monitor .drilldowns{margin-top:.5rem;border-top:1px solid var(--line)}
#tf-requirement-monitor .linked-note{border-color:var(--line);border-radius:8px;font-size:.72rem}
#tf-requirement-monitor .history{padding:.6rem .75rem}
#tf-requirement-monitor .history strong{font-size:.78rem}
#tf-requirement-monitor .history-changes{font-size:.74rem}
/* the matrix: an asked cell is the map's matrix cell, with its verdict's bar on the left; the rest is a lattice of dots */
#tf-requirement-monitor .matrix-wrap{--gap:var(--surface);padding:.45rem}
#tf-requirement-monitor table{border-spacing:4px}
#tf-requirement-monitor .matrix-cell{position:relative;min-height:58px;padding:.32rem .4rem .38rem .62rem;border:1px solid var(--line);border-radius:7px;background:var(--pst-color-background);overflow:hidden}
#tf-requirement-monitor button.matrix-cell::before,#tf-requirement-monitor button.fault-tile::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--bar,var(--line-strong))}
#tf-requirement-monitor .matrix-cell.met,#tf-requirement-monitor .fault-tile.met{--bar:var(--fill-pass);--tone:var(--fill-pass);--ink:var(--green)}
#tf-requirement-monitor .matrix-cell.not-met,#tf-requirement-monitor .fault-tile.not-met{--bar:var(--fill-fail);--tone:var(--fill-fail);--ink:var(--red)}
#tf-requirement-monitor .matrix-cell.unknown,#tf-requirement-monitor .fault-tile.unknown{--bar:var(--fill-unknown);--tone:var(--fill-unknown);--ink:var(--amber)}
#tf-requirement-monitor .matrix-cell.met,#tf-requirement-monitor .matrix-cell.not-met,#tf-requirement-monitor .matrix-cell.unknown{border-color:var(--line);background:var(--pst-color-background)}
#tf-requirement-monitor .cell-status{margin-bottom:.14rem}
#tf-requirement-monitor .cell-count strong{font-size:1rem;font-weight:750}
#tf-requirement-monitor .cell-count strong span{font-size:.64rem;font-weight:500;color:var(--muted)}
#tf-requirement-monitor .cell-count small{font-size:.62rem;color:var(--muted)}
#tf-requirement-monitor .cell-cause{font-size:.62rem}
#tf-requirement-monitor .matrix-cell.na.air{border:0;background:transparent}
#tf-requirement-monitor .matrix-cell.na.air::after{content:"";position:absolute;left:50%;top:50%;width:5px;height:5px;margin:-2.5px 0 0 -2.5px;border-radius:50%;background:color-mix(in srgb,var(--pst-color-text-base) 26%,transparent)}
/* the fault groups: the map's cards with the same verdict bar; a group the profile does not ask is an outline */
#tf-requirement-monitor .fault-grid{gap:.45rem}
#tf-requirement-monitor .fault-tile{position:relative;min-height:4.3rem;padding:.5rem .6rem .5rem .8rem;border:1px solid var(--line);border-radius:10px;background:var(--surface);overflow:hidden}
#tf-requirement-monitor .fault-tile.met,#tf-requirement-monitor .fault-tile.not-met,#tf-requirement-monitor .fault-tile.unknown{border-color:var(--line);background:var(--surface)}
#tf-requirement-monitor .fault-tile.na.air{border:1px dashed var(--line);background:transparent}
#tf-requirement-monitor .fault-tile.na.air .tile-head strong{color:var(--muted);font-weight:600}
#tf-requirement-monitor .tile-head{font-size:.78rem}
#tf-requirement-monitor .tile-head strong{font-weight:650}
#tf-requirement-monitor .tile-metrics{gap:.9rem;margin-top:.5rem}
#tf-requirement-monitor .tile-metrics div{padding:0;background:transparent}
#tf-requirement-monitor .tile-metrics span{font-size:.66rem;color:var(--muted)}
#tf-requirement-monitor .tile-metrics strong{font-size:.95rem;font-weight:750}
#tf-requirement-monitor .tile-metrics i{font-size:.66rem;color:var(--muted)}
#tf-requirement-monitor .tile-metrics .not-met strong{color:var(--red)}
/* scales: what is reached is tinted by its verdict; the target is marked from above, never with a white ring */
#tf-requirement-monitor .seg{position:relative}
#tf-requirement-monitor .seg.target,#tf-requirement-monitor .off.target{box-shadow:none}
#tf-requirement-monitor .seg.target::before,#tf-requirement-monitor .off.target::before{content:"";position:absolute;top:0;left:50%;margin-left:-5px;border:5px solid transparent;border-top-color:var(--muted)}
#tf-requirement-monitor .off{position:relative}
#tf-requirement-monitor .met-signal .actual{background:color-mix(in srgb,var(--fill-pass) 34%,transparent)}
#tf-requirement-monitor .not-met-signal .actual{background:color-mix(in srgb,var(--fill-fail) 26%,transparent)}
#tf-requirement-monitor .unknown-signal .actual{background:color-mix(in srgb,var(--fill-unknown) 30%,transparent)}
@media(max-width:760px){#tf-requirement-monitor .fault-chain:not(.mutant-tally){grid-template-columns:1fr}#tf-requirement-monitor .fault-chain:not(.mutant-tally)>i{display:none}}
"""
# A status word's glyph.
GLYPH_STYLE = r"""
/* a status word carries the map's glyph: the theme's own Font Awesome shapes, drawn as a mask in the word's colour */
#tf-requirement-monitor .status:not(.cell-cause)::before,#tf-requirement-monitor .overall::before{content:"";display:block;flex:none;width:1.25em;height:1em;background:currentColor;-webkit-mask:var(--glyph) center/contain no-repeat;mask:var(--glyph) center/contain no-repeat}
#tf-requirement-monitor .status.met,#tf-requirement-monitor .overall.met{--glyph:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'%3E%3Cpath d='M256 512a256 256 0 1 1 0-512 256 256 0 1 1 0 512zM374 145.7c-10.7-7.8-25.7-5.4-33.5 5.3L221.1 315.2 169 263.1c-9.4-9.4-24.6-9.4-33.9 0s-9.4 24.6 0 33.9l72 72c5 5 11.8 7.5 18.8 7s13.4-4.1 17.5-9.8L379.3 179.2c7.8-10.7 5.4-25.7-5.3-33.5z'/%3E%3C/svg%3E")}
#tf-requirement-monitor .status.not-met,#tf-requirement-monitor .overall.not-met{--glyph:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'%3E%3Cpath d='M256 512a256 256 0 1 0 0-512 256 256 0 1 0 0 512zM167 167c9.4-9.4 24.6-9.4 33.9 0l55 55 55-55c9.4-9.4 24.6-9.4 33.9 0s9.4 24.6 0 33.9l-55 55 55 55c9.4 9.4 9.4 24.6 0 33.9s-24.6 9.4-33.9 0l-55-55-55 55c-9.4 9.4-24.6 9.4-33.9 0s-9.4-24.6 0-33.9l55-55-55-55c-9.4-9.4-9.4-24.6 0-33.9z'/%3E%3C/svg%3E")}
#tf-requirement-monitor .status.unknown,#tf-requirement-monitor .overall.unknown{--glyph:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'%3E%3Cpath d='M256 512a256 256 0 1 0 0-512 256 256 0 1 0 0 512zm0-336c-17.7 0-32 14.3-32 32 0 13.3-10.7 24-24 24s-24-10.7-24-24c0-44.2 35.8-80 80-80s80 35.8 80 80c0 47.2-36 67.2-56 74.5l0 3.8c0 13.3-10.7 24-24 24s-24-10.7-24-24l0-8.1c0-20.5 14.8-35.2 30.1-40.2 6.4-2.1 13.2-5.5 18.2-10.3 4.3-4.2 7.7-10 7.7-19.6 0-17.7-14.3-32-32-32zM224 368a32 32 0 1 1 64 0 32 32 0 1 1 -64 0z'/%3E%3C/svg%3E")}
#tf-requirement-monitor .status.na,#tf-requirement-monitor .overall.na{--glyph:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'%3E%3Cpath d='M256 512a256 256 0 1 0 0-512 256 256 0 1 0 0 512zM168 232l176 0c13.3 0 24 10.7 24 24s-10.7 24-24 24l-176 0c-13.3 0-24-10.7-24-24s10.7-24 24-24z'/%3E%3C/svg%3E")}
"""
# Selecting: a tint of the verdict, a detail that changes softly.
SELECTION_STYLE = r"""
#tf-requirement-monitor button.matrix-cell,#tf-requirement-monitor button.fault-tile{outline:none!important;transition:background-color .22s ease,border-color .22s ease,box-shadow .22s ease,transform .22s ease}
#tf-requirement-monitor button.matrix-cell:hover:not(.selected),#tf-requirement-monitor button.fault-tile:hover:not(.selected){border-color:var(--line-strong);background:var(--raised)}
#tf-requirement-monitor button.matrix-cell.selected,#tf-requirement-monitor button.fault-tile.selected{border-color:color-mix(in srgb,var(--ink,var(--line-strong)) 55%,transparent);background:color-mix(in srgb,var(--tone,var(--line)) 15%,var(--pst-color-background));box-shadow:0 6px 18px rgba(0,0,0,.18);transform:translateY(-1px)}
#tf-requirement-monitor button.fault-tile.selected{background:color-mix(in srgb,var(--tone,var(--line)) 13%,var(--surface))}
#tf-requirement-monitor button.matrix-cell:focus-visible,#tf-requirement-monitor button.fault-tile:focus-visible{box-shadow:0 0 0 2px var(--gap),0 0 0 3.5px color-mix(in srgb,var(--ink,var(--blue)) 70%,transparent)}
/* the detail changes softly: the old fades, the new rises in, a thin line of its verdict draws under its title */
#tf-requirement-monitor .inspector.stack>.ins-layer{transition:opacity .24s ease,transform .24s ease}
#tf-requirement-monitor .inspector.stack>.ins-layer:not(.on){opacity:0;transform:translateY(6px);pointer-events:none;transition:opacity .14s ease,transform .14s ease,visibility 0s linear .14s}
#tf-requirement-monitor .ins-layer .inspector-head{position:relative;padding-bottom:.45rem}
#tf-requirement-monitor .ins-layer .inspector-head::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;border-radius:2px;background:var(--accent,var(--line-strong));transform:scaleX(0);transform-origin:left;transition:transform .42s cubic-bezier(.2,.8,.2,1) .06s}
#tf-requirement-monitor .ins-layer.on .inspector-head::after{transform:scaleX(1)}
#tf-requirement-monitor .ins-layer:has(.inspector-head .status.met){--accent:var(--fill-pass)}
#tf-requirement-monitor .ins-layer:has(.inspector-head .status.not-met){--accent:var(--fill-fail)}
#tf-requirement-monitor .ins-layer:has(.inspector-head .status.unknown){--accent:var(--fill-unknown)}
/* a block is addressed below the header */
#tf-requirement-monitor .section{position:relative;scroll-margin-top:calc(var(--sticky-top) + var(--verdict-h,8rem) + .9rem)}
#tf-requirement-monitor .unknown.attn,#tf-requirement-monitor .unknown-signal.attn{--attn:var(--fill-unknown)}
@keyframes tf-ripple{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--attn,var(--fill-fail)) 45%,transparent)}100%{box-shadow:0 0 0 12px color-mix(in srgb,var(--attn,var(--fill-fail)) 0%,transparent)}}
@media(prefers-reduced-motion:reduce){#tf-requirement-monitor button.matrix-cell,#tf-requirement-monitor button.fault-tile,#tf-requirement-monitor .inspector.stack>.ins-layer,#tf-requirement-monitor .ins-layer .inspector-head::after{transition:none!important;transform:none!important}}
"""
# The lens that glides to the selection and the detail's edge that points at it.
LENS_STYLE = r"""
#tf-requirement-monitor .matrix-wrap,#tf-requirement-monitor .fault-grid{position:relative}
#tf-requirement-monitor button.matrix-cell.selected,#tf-requirement-monitor button.fault-tile.selected{border-color:transparent;transform:none}
#tf-requirement-monitor .glide{position:absolute;left:0;top:0;z-index:3;border-radius:7px;pointer-events:none;--ring:var(--green);box-shadow:0 0 0 1.5px color-mix(in srgb,var(--ring) 70%,transparent),0 0 0 5px color-mix(in srgb,var(--ring) 16%,transparent)}
#tf-requirement-monitor .fault-grid>.glide{border-radius:10px}
#tf-requirement-monitor .glide.not-met{--ring:var(--red)}
#tf-requirement-monitor .glide.unknown{--ring:var(--amber)}
#tf-requirement-monitor .glide.ready{transition:transform .34s cubic-bezier(.2,.8,.2,1),width .34s cubic-bezier(.2,.8,.2,1),height .34s cubic-bezier(.2,.8,.2,1),box-shadow .25s ease}
#tf-requirement-monitor .inspector{position:relative}
#tf-requirement-monitor .pointer{position:absolute;left:-7px;top:0;z-index:2;width:13px;height:13px;border-left:1px solid var(--line);border-bottom:1px solid var(--line);background:var(--surface);pointer-events:none}
#tf-requirement-monitor .pointer.ready{transition:transform .34s cubic-bezier(.2,.8,.2,1)}
@media(max-width:1200px){#tf-requirement-monitor .pointer{display:none}}
@media(prefers-reduced-motion:reduce){#tf-requirement-monitor .glide.ready,#tf-requirement-monitor .pointer.ready{transition:none}}
"""
# The header's pictures pick what to look at below.
NAVIGATOR_STYLE = r"""
#tf-requirement-monitor .domain.with-nav{display:grid;padding:0;cursor:default}
#tf-requirement-monitor .domain.with-nav .domain-link{display:grid;grid-template-rows:auto auto auto;row-gap:.12rem;padding:.5rem .2rem .42rem .7rem;color:inherit;text-decoration:none}
#tf-requirement-monitor .domain.with-nav .thumb{grid-column:2;grid-row:1;align-self:center;margin:.45rem .7rem .45rem 0}
#tf-requirement-monitor .thumb.nav{gap:3px}
#tf-requirement-monitor .thumb-matrix.nav{grid-template-columns:repeat(4,14px);grid-auto-rows:9px}
#tf-requirement-monitor .thumb-strip.nav{grid-template-columns:repeat(var(--n),14px);grid-auto-rows:24px}
#tf-requirement-monitor .thumb.nav button.t{padding:0;border:0;cursor:pointer;transition:transform .15s ease,box-shadow .15s ease}
#tf-requirement-monitor .thumb.nav button.t:hover{transform:scale(1.15)}
#tf-requirement-monitor .thumb.nav button.t.current{box-shadow:0 0 0 1.5px var(--pst-color-background),0 0 0 3px color-mix(in srgb,var(--pst-color-text-base) 45%,transparent)}
#tf-requirement-monitor .peek{border-color:var(--line-strong)!important;background:var(--raised)!important}
"""
# The matrix and the fault groups stay in sight beside a long detail.
PANEL_STICKY_STYLE = r"""
@media(min-width:1201px){#tf-requirement-monitor .dashboard-layout>.matrix-wrap,#tf-requirement-monitor .fault-layout>.fault-side,#tf-requirement-monitor .fault-layout>.fault-grid,#tf-requirement-monitor .fault-layout>.signal-grid{position:sticky;top:calc(var(--sticky-top) + var(--verdict-h,8rem) + .9rem)}}
"""
# A matrix cell's path properties as small bars.
CELL_PROPERTY_STYLE = r"""
#tf-requirement-monitor .cell-props{display:flex;gap:2px;margin-top:.28rem}
#tf-requirement-monitor .cell-props i{display:block;width:11px;height:4px;border-radius:2px;background:color-mix(in srgb,var(--pst-color-text-base) 14%,transparent)}
#tf-requirement-monitor .cell-props i.met{background:var(--fill-pass)}
#tf-requirement-monitor .cell-props i.not-met{background:var(--fill-fail)}
#tf-requirement-monitor .cell-props i.unknown{background:var(--fill-unknown)}
#tf-requirement-monitor .cell-props i.na{background:color-mix(in srgb,var(--pst-color-text-base) 14%,transparent)}
"""
# Arriving at a block.
ARRIVAL_STYLE = r"""
#tf-requirement-monitor .section.nav-flash{animation:none}
/* arriving at a block: a line of its verdict's colour runs once round it, a few pixels off its edge, and is gone */
#tf-requirement-monitor .section>.arrive{position:absolute;z-index:6;overflow:visible;pointer-events:none;opacity:0;--ink:var(--green)}
#tf-requirement-monitor .section>.arrive[data-tone=fail]{--ink:var(--red)}
#tf-requirement-monitor .section>.arrive[data-tone=unknown]{--ink:var(--amber)}
#tf-requirement-monitor .section>.arrive[data-tone=na]{--ink:var(--muted)}
#tf-requirement-monitor .arrive rect{fill:none;stroke:var(--ink);stroke-linecap:round}
@keyframes tf-arrive-still{0%{opacity:0}15%{opacity:.8}100%{opacity:0}}
"""
# A fault group's classes, and zeros made quiet.
CLASS_STYLE = r"""
/* the group's classes: boxes like the chain's, the verdict as the same left bar; a class not asked is an outline */
#tf-requirement-monitor .class-boxes{display:grid;grid-template-columns:repeat(auto-fill,minmax(6.6rem,1fr));gap:.3rem;margin:.05rem 0 .45rem}
#tf-requirement-monitor .class-box{display:grid;gap:.06rem;min-height:2.55rem;padding:.32rem .5rem .32rem .6rem;border-radius:8px;background:var(--raised);box-shadow:inset 3px 0 0 var(--bar,transparent)}
#tf-requirement-monitor .class-box strong{font-size:.72rem;font-weight:650;line-height:1.2}
#tf-requirement-monitor .class-box small{font-size:.62rem;color:var(--muted)}
#tf-requirement-monitor .class-box.met{--bar:var(--fill-pass)}
#tf-requirement-monitor .class-box.not-met{--bar:var(--fill-fail)}
#tf-requirement-monitor .class-box.not-met small{color:var(--red)}
#tf-requirement-monitor .class-box.unknown{--bar:var(--fill-unknown)}
#tf-requirement-monitor .class-box.unknown small{color:var(--amber)}
#tf-requirement-monitor .class-box.air{background:transparent;box-shadow:inset 0 0 0 1px var(--line);border:0}
#tf-requirement-monitor .class-box.air strong{color:var(--muted);font-weight:500}
#tf-requirement-monitor .class-box.optional{background:transparent;box-shadow:inset 0 0 0 1px var(--line-strong)}
/* a zero is a fact, not a signal: it stays, quiet */
#tf-requirement-monitor .fault-stage.zero>strong{color:var(--muted);font-weight:500}
#tf-requirement-monitor .coverage-counts .zero{color:var(--muted);font-weight:500}
"""
# A detail card as the hierarchy of its verdict: the checks it combines, then their details.
LEVEL_STYLE = r"""
#tf-requirement-monitor .ins-layer{--verdict:4.3rem;--step:1.05rem;--gap:.45rem}
/* groups: a label and a hairline, air above; they group, they do not judge */
#tf-requirement-monitor .ins-layer .signal-group{gap:0;padding:.85rem 0 .1rem;border-top:0}
#tf-requirement-monitor .ins-layer .signal-group:first-child{padding-top:.55rem}
#tf-requirement-monitor .ins-layer .signal-group-head,#tf-requirement-monitor .ins-layer .subgroup-head{display:flex;align-items:center;gap:.6rem;padding:0 0 .3rem;border:0}
#tf-requirement-monitor .ins-layer .signal-group-head>strong{flex:none;font-size:.7rem;font-weight:600;color:var(--muted)}
#tf-requirement-monitor .ins-layer .signal-group-head::after{content:"";flex:1;height:1px;background:var(--line);order:1}
#tf-requirement-monitor .ins-layer .group-scope{order:2;font-size:.7rem;font-weight:600}
/* a sub-group inside a group: a lighter label, no rule */
#tf-requirement-monitor .ins-layer .confidence-subgroup{gap:0;margin-top:.35rem;padding-top:0;border-top:0}
#tf-requirement-monitor .ins-layer .subgroup-head{padding:.15rem 0 .1rem}
#tf-requirement-monitor .ins-layer .subgroup-head strong{font-size:.66rem;font-weight:600;font-style:italic;color:var(--muted)}
#tf-requirement-monitor .ins-layer .confidence-grid,#tf-requirement-monitor .ins-layer .representation-stack{gap:0}
/* a check: one row (name, count, verdict), its detail under it one step in; the verdicts make one column down the
   card, the counts stand right-aligned against it */
#tf-requirement-monitor .ins-layer .signal-card{display:grid;grid-template-columns:minmax(0,1fr) auto var(--verdict);column-gap:var(--gap);align-items:baseline;padding:.34rem 0 .42rem}
#tf-requirement-monitor .ins-layer .signal-card>.signal-head,#tf-requirement-monitor .ins-layer .signal-card .signal-rule{display:contents}
#tf-requirement-monitor .ins-layer .signal-card .signal-head>strong{grid-column:1;grid-row:1;font-size:.86rem;font-weight:700;line-height:1.25}
#tf-requirement-monitor .ins-layer .signal-card .scope-count{grid-column:2;grid-row:1;justify-self:end;white-space:nowrap}
#tf-requirement-monitor .ins-layer .signal-card .scope-count b{font-size:.84rem;font-weight:700}
#tf-requirement-monitor .ins-layer .signal-card .scope-count small{font-size:.7rem}
#tf-requirement-monitor .ins-layer .signal-card .signal-head>.status,#tf-requirement-monitor .ins-layer .signal-card .signal-rule>.status{grid-column:3;grid-row:1;justify-self:end}
#tf-requirement-monitor .ins-layer .coverage-summary{grid-column:2;grid-row:1;justify-self:end;align-items:baseline;gap:.25rem;margin:0;white-space:nowrap}
#tf-requirement-monitor .ins-layer .coverage-summary>strong{font-size:.84rem;font-weight:700}
#tf-requirement-monitor .ins-layer .coverage-summary>strong span{font-size:.84rem;margin:0}
#tf-requirement-monitor .ins-layer .coverage-summary small{font-size:.7rem}
#tf-requirement-monitor .ins-layer .track-row,#tf-requirement-monitor .ins-layer .coverage-strip,#tf-requirement-monitor .ins-layer .coverage-counts{grid-column:1/-1;margin-left:var(--step)}
/* a detail: one step in, smaller and quieter than its check; a pass stays quiet, a failure keeps its full colour */
#tf-requirement-monitor .ins-layer .coverage-strip{margin-top:.38rem;gap:2px}
#tf-requirement-monitor .ins-layer .coverage-segment{height:3px}
#tf-requirement-monitor .ins-layer .coverage-segment.pass{background:color-mix(in srgb,var(--green) 55%,transparent)}
#tf-requirement-monitor .ins-layer .coverage-counts{gap:.15rem .7rem;flex-wrap:wrap;margin-top:.3rem;font-size:.66rem}
#tf-requirement-monitor .ins-layer .coverage-counts .pass{font-weight:600}
#tf-requirement-monitor .ins-layer .track-row{flex-wrap:wrap;align-items:stretch;gap:.25rem .3rem;margin-top:.32rem}
#tf-requirement-monitor .ins-layer .track{flex:1 1 100%;gap:2px;border:0;border-radius:6px;background:transparent}
#tf-requirement-monitor .ins-layer .track[style="--n:2"]{flex-basis:12rem}
#tf-requirement-monitor .ins-layer .seg{min-height:1.45rem;padding:.1rem .25rem;border:0;border-radius:4px;background:color-mix(in srgb,var(--pst-color-text-base) 5%,transparent);font-size:.62rem;font-weight:500;color:var(--muted)}
#tf-requirement-monitor .ins-layer .seg.actual,#tf-requirement-monitor .ins-layer .seg.target{font-weight:650}
#tf-requirement-monitor .ins-layer .met-signal .seg.actual,#tf-requirement-monitor .ins-layer .met-signal .off.actual{background:color-mix(in srgb,var(--green) 13%,transparent);color:var(--green)}
#tf-requirement-monitor .ins-layer .not-met-signal .seg.actual,#tf-requirement-monitor .ins-layer .not-met-signal .off.actual{background:var(--fill-fail);color:#fff}
#tf-requirement-monitor .ins-layer .unknown-signal .seg.actual,#tf-requirement-monitor .ins-layer .unknown-signal .off.actual{background:color-mix(in srgb,var(--fill-unknown) 40%,transparent);color:var(--pst-color-text-base)}
#tf-requirement-monitor .ins-layer .not-met-signal .seg.target:not(.actual),#tf-requirement-monitor .ins-layer .unknown-signal .seg.target:not(.actual){outline:1.5px dashed currentColor;outline-offset:-2px;color:var(--pst-color-text-base)}
#tf-requirement-monitor .ins-layer .tmark{font-size:.46rem;opacity:.9}
#tf-requirement-monitor .ins-layer .seg.target{padding-top:.32rem}
#tf-requirement-monitor .ins-layer .seg.target::before{margin-left:-4px;border-width:4px}
/* states outside a scale: faint dashed steps after it, on its line when there is room */
#tf-requirement-monitor .ins-layer .track-off{flex:0 1 auto;gap:2px .3rem;align-items:stretch}
#tf-requirement-monitor .ins-layer .off{min-height:1.45rem;padding:0 .4rem;border:1px dashed var(--line);border-radius:4px;background:transparent;font-size:.6rem;font-weight:500;color:var(--muted)}
#tf-requirement-monitor .ins-layer .off.inactive{border-style:solid;background:color-mix(in srgb,var(--pst-color-text-base) 6%,transparent)}
/* the dependent check: its row and verdict in the same columns, its name and detail one step further in */
#tf-requirement-monitor .ins-layer .dependent-wrap{margin:0;padding:0;border:0}
#tf-requirement-monitor .ins-layer .dependent-wrap .signal-head>strong{padding-left:var(--step);font-size:.82rem}
#tf-requirement-monitor .ins-layer .dependent-wrap .track-row{margin-left:calc(var(--step) * 2)}
/* the fault card: the chain read downwards, a step per row and the arrow between them, in the same columns; the
   classes it counts under it, one step in; the mutants under the classes; their judgement under them */
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain{display:grid;grid-template-columns:var(--step) minmax(0,1fr) auto var(--verdict);column-gap:var(--gap);row-gap:0;align-items:baseline;padding:.2rem 0 .05rem}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>.fault-stage{display:contents}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>.fault-stage>span:first-child{grid-column:2;padding:.12rem 0;font-size:.86rem;font-weight:700;color:var(--pst-color-text-base)}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>.fault-stage>strong{grid-column:3;justify-self:end;font-size:.84rem;font-weight:700}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>.fault-stage>.status{grid-column:4;justify-self:end}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>.fault-stage.zero>strong{color:var(--muted)}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>i{grid-column:1/-1;justify-self:start;width:var(--step);margin:-.12rem 0;transform:rotate(90deg);font-size:.62rem;line-height:.78rem;text-align:center;color:var(--muted)}
#tf-requirement-monitor .ins-layer .fault-class-group>.class-boxes{grid-template-columns:repeat(auto-fill,minmax(7.2rem,1fr));gap:.25rem .6rem;margin:.5rem 0 0 calc(var(--step) + var(--gap))}
#tf-requirement-monitor .ins-layer .class-box{position:relative;min-height:0;padding:.05rem 0 .05rem .8rem;border:0;border-radius:0;background:transparent;box-shadow:none}
#tf-requirement-monitor .ins-layer .class-box::before{content:"";position:absolute;left:0;top:.42rem;width:7px;height:7px;border-radius:50%;background:var(--dot,var(--line-strong))}
#tf-requirement-monitor .ins-layer .class-box.met{--dot:color-mix(in srgb,var(--green) 75%,transparent)}
#tf-requirement-monitor .ins-layer .class-box.not-met{--dot:var(--fill-fail)}
#tf-requirement-monitor .ins-layer .class-box.unknown{--dot:var(--fill-unknown)}
#tf-requirement-monitor .ins-layer .class-box.air::before,#tf-requirement-monitor .ins-layer .class-box.optional::before{background:transparent;box-shadow:inset 0 0 0 1.5px var(--line-strong)}
#tf-requirement-monitor .ins-layer .class-box.air,#tf-requirement-monitor .ins-layer .class-box.optional{box-shadow:none;background:transparent}
#tf-requirement-monitor .ins-layer .class-box strong{font-size:.74rem;font-weight:600}
#tf-requirement-monitor .ins-layer .class-box small{font-size:.64rem}
#tf-requirement-monitor .ins-layer .class-box.met small{color:var(--muted)}
/* counts under the classes: number over word, quiet at zero, no tiles */
#tf-requirement-monitor .ins-layer .mutant-group{padding-top:.75rem}
#tf-requirement-monitor .ins-layer .mutants-group,#tf-requirement-monitor .ins-layer .generation-group{margin-left:calc(var(--step) + var(--gap))}
#tf-requirement-monitor .ins-layer .judgement-group{margin-left:calc(var(--step) * 2 + var(--gap));padding-top:.55rem}
#tf-requirement-monitor .ins-layer .fault-chain.mutant-tally{grid-template-columns:repeat(4,minmax(0,1fr));gap:.35rem .6rem}
#tf-requirement-monitor .ins-layer .mutant-tally .fault-stage{display:grid;grid-template-columns:minmax(0,1fr);gap:0;padding:0;border:0;border-radius:0;background:transparent;box-shadow:none;align-content:start}
#tf-requirement-monitor .ins-layer .mutant-tally .fault-stage>strong{order:-1;font-size:.95rem;font-weight:700;line-height:1.2}
#tf-requirement-monitor .ins-layer .mutant-tally .fault-stage>span{font-size:.64rem;line-height:1.2}
#tf-requirement-monitor .ins-layer .mutant-tally .fault-stage.zero>strong{color:var(--muted);font-weight:500}
#tf-requirement-monitor .ins-layer .mutant-tally .fault-stage.not-met>strong{color:var(--red)}
#tf-requirement-monitor .ins-layer .mutant-tally .fault-stage.unknown>strong{color:var(--amber)}
#tf-requirement-monitor .ins-layer .mutant-tally .fault-stage>.status{justify-self:start;margin-top:.1rem}
#tf-requirement-monitor .ins-layer .judgement-group .signal-group-head>strong{font-size:.66rem}
#tf-requirement-monitor .ins-layer .judgement-group .mutant-tally .fault-stage>strong{font-size:.84rem}
#tf-requirement-monitor .ins-layer .drilldowns{margin-top:.85rem}
@media(max-width:760px){#tf-requirement-monitor .ins-layer .fault-chain.mutant-tally{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""
# The rail: the checks are its stops in their verdict's colour, the levels below hang off it.
RAIL_STYLE = r"""
#tf-requirement-monitor .ins-layer{--rail:calc(var(--step) / 2);--stop:9px;--rail-ink:var(--line-strong)}
#tf-requirement-monitor .ins-layer .signal-card{position:relative;padding-left:var(--step)}
#tf-requirement-monitor .ins-layer .signal-card .track-row,#tf-requirement-monitor .ins-layer .signal-card .coverage-strip,#tf-requirement-monitor .ins-layer .signal-card .coverage-counts{margin-left:0}
#tf-requirement-monitor .ins-layer .dependent-wrap .signal-card .track-row{margin-left:var(--step)}
#tf-requirement-monitor .ins-layer .subgroup-head{padding-left:var(--step)}
/* the rail through a group's checks: from the first stop to the last, through the sub-group's label */
#tf-requirement-monitor .ins-layer .path-properties .signal-card::after,#tf-requirement-monitor .ins-layer .path-properties .dependent-wrap::after,#tf-requirement-monitor .ins-layer .path-properties .subgroup-head{position:relative}
#tf-requirement-monitor .ins-layer .path-properties .signal-card:not(.dependent-signal)::after,#tf-requirement-monitor .ins-layer .path-properties .dependent-wrap::after,#tf-requirement-monitor .ins-layer .path-properties .subgroup-head::before{content:"";position:absolute;left:var(--rail);top:0;bottom:0;width:1.5px;margin-left:-.75px;background:var(--rail-ink)}
#tf-requirement-monitor .ins-layer .path-properties .dependent-wrap,#tf-requirement-monitor .ins-layer .path-properties .subgroup-head{position:relative}
#tf-requirement-monitor .ins-layer .path-properties .representation-stack>.signal-card:first-child::after{top:.85rem}
#tf-requirement-monitor .ins-layer .path-properties .confidence-grid>.signal-card:last-child::after{bottom:auto;height:.85rem}
/* its stops: the verdict's colour, a ring where nothing is judged */
#tf-requirement-monitor .ins-layer .signal-card>.signal-head>strong{position:relative}
#tf-requirement-monitor .ins-layer .signal-card>.signal-head>strong::before{content:"";position:absolute;z-index:1;left:calc(var(--rail) - var(--step) - var(--stop) / 2);top:.36em;width:var(--stop);height:var(--stop);border-radius:50%;background:var(--stop-fill,var(--surface));box-shadow:0 0 0 2.5px var(--surface),inset 0 0 0 1.5px var(--stop-edge,var(--line-strong))}
#tf-requirement-monitor .ins-layer .met-signal,#tf-requirement-monitor .ins-layer .fault-stage.met{--stop-fill:var(--fill-pass);--stop-edge:var(--fill-pass)}
html[data-theme=dark] #tf-requirement-monitor .ins-layer .met-signal,html[data-theme=dark] #tf-requirement-monitor .ins-layer .fault-stage.met{--stop-fill:var(--green);--stop-edge:var(--green)}
#tf-requirement-monitor .ins-layer .not-met-signal,#tf-requirement-monitor .ins-layer .fault-stage.not-met{--stop-fill:var(--fill-fail);--stop-edge:var(--fill-fail)}
#tf-requirement-monitor .ins-layer .unknown-signal,#tf-requirement-monitor .ins-layer .fault-stage.unknown{--stop-fill:var(--fill-unknown);--stop-edge:var(--fill-unknown)}
/* the dependent check branches off its parent's stop */
#tf-requirement-monitor .ins-layer .dependent-wrap::before{content:"";position:absolute;z-index:1;left:var(--rail);top:-.1rem;width:var(--step);height:.95rem;margin-left:-.75px;border-left:1.5px solid var(--rail-ink);border-bottom:1.5px solid var(--rail-ink);border-bottom-left-radius:7px}
#tf-requirement-monitor .ins-layer .dependent-wrap .signal-head>strong::before{left:calc(var(--rail) - var(--stop) / 2)}
/* the fault chain is the rail: a stop per step, the arrows on the rail between them */
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain{position:relative}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain::before{content:"";position:absolute;left:var(--rail);top:.75rem;bottom:.75rem;width:1.5px;margin-left:-.75px;background:var(--rail-ink)}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>i{position:relative;z-index:1}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>i::before{content:"";position:absolute;inset:.18rem .26rem;z-index:-1;border-radius:50%;background:var(--surface)}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>.fault-stage>span:first-child{position:relative}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>.fault-stage>span:first-child::before{content:"";position:absolute;z-index:1;left:calc(var(--gap) * -1 - var(--step) / 2 - var(--stop) / 2);top:calc(.12rem + .36em);width:var(--stop);height:var(--stop);border-radius:50%;background:var(--stop-fill,var(--surface));box-shadow:0 0 0 2.5px var(--surface),inset 0 0 0 1.5px var(--stop-edge,var(--line-strong))}
/* what hangs off the chain: a bracket to each level below it */
#tf-requirement-monitor .ins-layer .fault-class-group>.class-boxes,#tf-requirement-monitor .ins-layer .mutants-group,#tf-requirement-monitor .ins-layer .generation-group,#tf-requirement-monitor .ins-layer .judgement-group{position:relative}
#tf-requirement-monitor .ins-layer .fault-class-group>.class-boxes::before,#tf-requirement-monitor .ins-layer .mutants-group::before,#tf-requirement-monitor .ins-layer .generation-group::before,#tf-requirement-monitor .ins-layer .judgement-group::before{content:"";position:absolute;width:.62rem;border-left:1.5px solid var(--line);border-bottom:1.5px solid var(--line);border-bottom-left-radius:6px}
#tf-requirement-monitor .ins-layer .fault-class-group>.class-boxes::before{left:calc(var(--step) / -2 - var(--gap) - .75px);top:-.55rem;height:1rem}
#tf-requirement-monitor .ins-layer .mutants-group::before,#tf-requirement-monitor .ins-layer .generation-group::before{left:calc(var(--step) / -2 - var(--gap) - .75px);top:.05rem;height:1.25rem}
#tf-requirement-monitor .ins-layer .judgement-group::before{left:calc(var(--step) / -2 - .75px);top:-.15rem;height:1.2rem}
#tf-requirement-monitor .ins-layer .mutants-group .signal-group-head,#tf-requirement-monitor .ins-layer .generation-group .signal-group-head,#tf-requirement-monitor .ins-layer .judgement-group .signal-group-head{padding-left:.3rem}
"""
# The blocks in two equal columns; a little air in the cards.
COLUMN_STYLE = r"""
@media(min-width:1201px){#tf-requirement-monitor .dashboard-layout,#tf-requirement-monitor .fault-layout:not(.no-inspector){grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:.75rem}}
#tf-requirement-monitor .inspector{padding:.9rem 1rem .7rem}
#tf-requirement-monitor .ins-layer{--row-top:.44rem}
#tf-requirement-monitor .ins-layer .signal-group{padding-top:1.05rem}
#tf-requirement-monitor .ins-layer .signal-group:first-child{padding-top:.7rem}
#tf-requirement-monitor .ins-layer .signal-group-head{padding-bottom:.4rem}
#tf-requirement-monitor .ins-layer .signal-card{padding:var(--row-top) 0 .55rem var(--step)}
#tf-requirement-monitor .ins-layer .track-row{margin-top:.42rem}
#tf-requirement-monitor .ins-layer .coverage-strip{margin-top:.48rem}
#tf-requirement-monitor .ins-layer .coverage-counts{margin-top:.38rem}
#tf-requirement-monitor .ins-layer .confidence-subgroup{margin-top:.5rem}
#tf-requirement-monitor .ins-layer .subgroup-head{padding:.2rem 0 .15rem var(--step)}
#tf-requirement-monitor .ins-layer .path-properties .representation-stack>.signal-card:first-child::after{top:calc(var(--row-top) + .55rem)}
#tf-requirement-monitor .ins-layer .path-properties .confidence-grid>.signal-card:last-child::after{height:calc(var(--row-top) + .55rem)}
#tf-requirement-monitor .ins-layer .dependent-wrap::before{height:calc(var(--row-top) + .58rem)}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>.fault-stage>span:first-child{padding:.2rem 0}
#tf-requirement-monitor .ins-layer .fault-class-group>.fault-chain>.fault-stage>span:first-child::before{top:calc(.2rem + .36em)}
#tf-requirement-monitor .ins-layer .fault-class-group>.class-boxes{gap:.45rem .7rem;margin-top:.65rem}
#tf-requirement-monitor .ins-layer .mutant-group{padding-top:1rem}
#tf-requirement-monitor .ins-layer .judgement-group{padding-top:.75rem}
#tf-requirement-monitor .ins-layer .fault-chain.mutant-tally{gap:.55rem .7rem}
#tf-requirement-monitor .ins-layer .drilldowns{margin-top:1rem;padding-top:.55rem}
"""
# The header lifts off the page and settles while it is stuck.
HEADER_STYLE = r"""
/* the shell sticks and keeps the header's full height; the card in it settles; nothing under it moves */
#tf-requirement-monitor{--settle:.34s cubic-bezier(.2,.8,.2,1)}
#tf-requirement-monitor .verdict-shell{position:sticky;top:var(--sticky-top);z-index:24;margin:.35rem 0 1rem;pointer-events:none}
#tf-requirement-monitor .verdict-shell>.verdict{position:relative;top:auto;z-index:auto;margin:0;pointer-events:auto;transition:padding var(--settle),background-color var(--settle),border-color var(--settle),box-shadow var(--settle)}
/* while it is stuck it lifts off the page: a lighter surface and a soft shadow, never a hard edge */
#tf-requirement-monitor .verdict-shell.stuck>.verdict{background:color-mix(in srgb,var(--pst-color-background) 97%,transparent);border-color:color-mix(in srgb,var(--pst-color-text-base) 16%,transparent);box-shadow:0 14px 30px -16px rgba(15,23,42,.30),0 3px 8px -4px rgba(15,23,42,.12)}
html[data-theme=dark] #tf-requirement-monitor .verdict-shell.stuck>.verdict{background:color-mix(in srgb,var(--pst-color-text-base) 5.5%,var(--pst-color-background));border-color:color-mix(in srgb,var(--pst-color-text-base) 17%,transparent);box-shadow:0 16px 34px -14px rgba(0,0,0,.72),0 2px 6px -2px rgba(0,0,0,.4)}
/* and settles: the kicker and the identifier line fold away, the title and the pictures shrink a little */
#tf-requirement-monitor .verdict .kicker,#tf-requirement-monitor .verdict .verdict-id{max-height:2rem;overflow:hidden;transition:max-height var(--settle),opacity .2s ease,margin var(--settle)}
#tf-requirement-monitor .verdict.settled .kicker,#tf-requirement-monitor .verdict.settled .verdict-id{max-height:0;margin-top:0;opacity:0}
#tf-requirement-monitor .verdict h2{transition:font-size var(--settle),margin var(--settle)}
#tf-requirement-monitor .verdict.settled h2{margin-top:0;font-size:1.02rem}
#tf-requirement-monitor .verdict .overall{transition:padding var(--settle),font-size var(--settle)}
#tf-requirement-monitor .verdict.settled .overall{padding:.26rem .7rem;font-size:.76rem}
#tf-requirement-monitor .verdict.settled{padding:.55rem .95rem .45rem}
#tf-requirement-monitor .verdict .domain-strip{transition:margin var(--settle),padding var(--settle)}
#tf-requirement-monitor .verdict.settled .domain-strip{margin-top:.45rem;padding-top:.05rem}
#tf-requirement-monitor .verdict .domain.with-nav .domain-link{transition:padding var(--settle)}
#tf-requirement-monitor .verdict.settled .domain.with-nav .domain-link{padding-top:.32rem;padding-bottom:.28rem}
#tf-requirement-monitor .verdict .domain .thumb{transition:transform var(--settle),margin var(--settle)}
#tf-requirement-monitor .verdict.settled .domain .thumb{transform:scale(.82);margin-top:calc(.45rem - 6px);margin-bottom:calc(.45rem - 6px)}
#tf-requirement-monitor .verdict.measuring,#tf-requirement-monitor .verdict.measuring *{transition:none!important}
@media(prefers-reduced-motion:reduce){#tf-requirement-monitor .verdict,#tf-requirement-monitor .verdict *{transition:none!important}}
"""
# The arrival beam, drawn per frame.
BEAM_STYLE = r"""
/* the beam, drawn per frame: a halo for the fast pass, the afterglow, the line on top */
#tf-requirement-monitor .section>.arrive{opacity:1}
#tf-requirement-monitor .arrive rect{opacity:0;stroke-dasharray:0 100}
#tf-requirement-monitor .arrive .glow{stroke-width:7px;filter:blur(3.5px)}
#tf-requirement-monitor .arrive .trail{stroke-width:1.4px;stroke-linecap:butt}
#tf-requirement-monitor .arrive .line{stroke-width:1.3px}
#tf-requirement-monitor .section>.arrive.still{animation:tf-arrive-still .9s ease forwards}
/* what does not pass inside answers as the beam comes round */
#tf-requirement-monitor .attn{animation:tf-ripple .8s ease-out .7s}
@media(prefers-reduced-motion:reduce){#tf-requirement-monitor .attn{animation:none}}
"""
MONITOR_STYLE = MONITOR_STYLE.replace(
    "</style>",
    ASSURANCE_NAV_STYLE + READABLE_STYLE + TRACK_STYLE + LOOK_STYLE + GLYPH_STYLE + SELECTION_STYLE + LENS_STYLE + NAVIGATOR_STYLE + PANEL_STICKY_STYLE + CELL_PROPERTY_STYLE + ARRIVAL_STYLE + CLASS_STYLE + LEVEL_STYLE + RAIL_STYLE + COLUMN_STYLE + HEADER_STYLE + BEAM_STYLE + "</style>",
)
