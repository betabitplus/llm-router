"""Markup, styles and scripts of the Verification Health Map and Depth Map pages.

Presentation only: the builder computes every fact and passes it in as a JSON payload. The
file stays outside the evidence-producer qualification fingerprint on purpose, because no
qualification control exercises page rendering; the structural gate checks the rendered pages.
"""

HEALTH_MAP_TEMPLATE = r"""<section id="verification-health-map">
<h1>Verification Health Map<a class="headerlink" href="#verification-health-map" title="Link to this heading">#</a></h1>
<style id="tf-health-map-style">
#verification-health-map{--tf-radius-sm:6px;--tf-radius-md:10px;--tf-duration-fast:120ms;--tf-duration-medium:180ms;--tf-ease:cubic-bezier(.2,0,0,1);--tf-hm-pass:#8ed3a2;--tf-hm-fail:#dc3f47;--tf-hm-na:#dde0e5;--tf-hm-pass-ink:#1f7a3f;--tf-hm-fail-ink:#c42b34;--tf-hm-pass-hover:color-mix(in srgb,var(--tf-hm-pass) 91%,#000);--tf-hm-fail-hover:color-mix(in srgb,var(--tf-hm-fail) 90%,#000);--tf-hm-na-hover:color-mix(in srgb,var(--tf-hm-na) 92%,#000);--tf-hm-na-strong:color-mix(in srgb,var(--tf-hm-na) 86%,#000);--tf-hm-goal:color-mix(in srgb,var(--pst-color-text-base) 4.5%,var(--pst-color-background));--tf-hm-feature:var(--pst-color-background);--tf-hm-raised:color-mix(in srgb,var(--pst-color-text-base) 8%,var(--pst-color-background));--tf-hm-line:color-mix(in srgb,var(--pst-color-text-base) 13%,transparent);--tf-hm-line-strong:color-mix(in srgb,var(--pst-color-text-base) 28%,transparent);--tf-hm-lineage:color-mix(in srgb,var(--pst-color-text-base) 40%,transparent);--tf-hm-selected:color-mix(in srgb,var(--pst-color-text-base) 55%,transparent);--tf-hm-ring:color-mix(in srgb,var(--pst-color-text-base) 78%,transparent)}
html[data-theme=dark] #verification-health-map{--tf-hm-pass:#22603a;--tf-hm-fail:#e5484d;--tf-hm-na:#2f353d;--tf-hm-pass-ink:#5fcf85;--tf-hm-fail-ink:#ff6b70;--tf-hm-pass-hover:color-mix(in srgb,var(--tf-hm-pass) 84%,#fff);--tf-hm-fail-hover:color-mix(in srgb,var(--tf-hm-fail) 86%,#fff);--tf-hm-na-hover:color-mix(in srgb,var(--tf-hm-na) 84%,#fff);--tf-hm-na-strong:color-mix(in srgb,var(--tf-hm-na) 78%,#fff);--tf-hm-goal:color-mix(in srgb,var(--pst-color-text-base) 5%,var(--pst-color-background));--tf-hm-feature:color-mix(in srgb,var(--pst-color-text-base) 10%,var(--pst-color-background));--tf-hm-raised:color-mix(in srgb,var(--pst-color-text-base) 10%,var(--pst-color-background));--tf-hm-ring:color-mix(in srgb,var(--pst-color-text-base) 92%,transparent)}
#verification-health-map{--tf-hm-radial-goal:color-mix(in srgb,var(--pst-color-text-base) 12%,var(--pst-color-background));--tf-hm-radial-feature:color-mix(in srgb,var(--pst-color-text-base) 7%,var(--pst-color-background))}
html[data-theme=dark] #verification-health-map{--tf-hm-radial-goal:color-mix(in srgb,var(--pst-color-text-base) 17%,var(--pst-color-background));--tf-hm-radial-feature:color-mix(in srgb,var(--pst-color-text-base) 11%,var(--pst-color-background))}
.tf-sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.tf-health-layerbar{position:relative;margin:.6rem 0 .55rem}
.tf-health-scroller{padding:3px 0;overflow-x:auto;overflow-y:hidden;overscroll-behavior-x:contain;scrollbar-width:none}
.tf-health-scroller::-webkit-scrollbar{display:none}
.tf-health-layers{position:relative;display:flex;align-items:stretch;gap:8px;width:max-content;min-width:100%}
.tf-health-group{position:relative;display:flex;flex:1 0 auto;flex-direction:column;gap:5px;min-width:0}
.tf-health-group-cards{display:flex;flex:1 1 auto;gap:8px}
.tf-health-group-cards>.tf-health-tab{flex:1 0 206px}
.tf-health-group-head{display:flex;align-items:center;height:20px;min-width:0;font-size:.64rem;font-weight:750;letter-spacing:.06em;text-transform:uppercase}
.tf-health-group-head::after{content:"";flex:1 1 auto;height:1px;background:currentColor;opacity:.38}
.tf-health-group.pinned .tf-health-group-head::after{content:none}
.tf-health-group-label{position:sticky;left:var(--tf-label-left,0px);z-index:1;display:inline-flex;align-items:center;gap:.35rem;padding-right:.5rem;background:var(--pst-color-background);white-space:nowrap}
.tf-health-group.failed .tf-health-group-head{color:var(--tf-hm-fail-ink)}
.tf-health-group.passed .tf-health-group-head{color:var(--tf-hm-pass-ink)}
.tf-health-group.failed+.tf-health-group.passed{margin-left:12px}
.tf-health-group.failed+.tf-health-group.passed::before{content:"";position:absolute;top:0;bottom:2px;left:-11px;width:1px;background:linear-gradient(transparent,var(--tf-hm-line-strong) 16%,var(--tf-hm-line-strong) 84%,transparent)}
.tf-health-pin .tf-health-group.pinned{position:sticky;left:0;z-index:3;margin-right:-8px;padding-right:8px;background:var(--pst-color-background)}
.tf-health-edge{position:absolute;top:28px;bottom:3px;z-index:4;display:flex;align-items:center;width:72px;opacity:0;visibility:hidden;pointer-events:none;transition:opacity var(--tf-duration-medium) var(--tf-ease),visibility var(--tf-duration-medium) linear}
.tf-health-edge.left{left:var(--tf-pin,0px);justify-content:flex-start;background:linear-gradient(90deg,var(--pst-color-background) 38%,transparent)}
.tf-health-edge.right{right:0;justify-content:flex-end;background:linear-gradient(270deg,var(--pst-color-background) 38%,transparent)}
.tf-health-edge.on{opacity:1;visibility:visible}
.tf-health-edge button{pointer-events:auto;display:inline-flex;align-items:center;gap:.4rem;height:26px;padding:0 .55rem;border:1px solid var(--tf-hm-line-strong);border-radius:999px;background:var(--tf-hm-raised);color:var(--pst-color-text-muted);font:inherit;font-size:.72rem;font-weight:700;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.14);transition:border-color var(--tf-duration-fast) var(--tf-ease),color var(--tf-duration-fast) var(--tf-ease)}
.tf-health-edge button:hover{border-color:var(--tf-hm-selected);color:var(--pst-color-text-base)}
.tf-health-edge-note{display:inline-flex;align-items:center;gap:.25rem}
.tf-health-edge-note.failed{color:var(--tf-hm-fail-ink)}.tf-health-edge-note.passed{color:var(--tf-hm-pass-ink)}
.tf-health-table-toggle{position:absolute;top:3px;left:0;z-index:5;display:inline-flex;align-items:center;gap:.4rem;height:20px;padding:0 .45rem 0 .5rem;border:1px solid var(--tf-hm-line);border-radius:6px;background:var(--pst-color-background);box-shadow:8px 0 0 var(--pst-color-background);color:var(--pst-color-text-muted);font:inherit;font-size:.68rem;font-weight:650;white-space:nowrap;cursor:pointer;transition:border-color var(--tf-duration-medium) var(--tf-ease),color var(--tf-duration-medium) var(--tf-ease)}
.tf-health-table-toggle:hover{border-color:var(--tf-hm-line-strong);color:var(--pst-color-text-base)}
.tf-health-table-toggle[aria-expanded=true]{border-color:var(--tf-hm-selected);background:var(--tf-hm-raised);color:var(--pst-color-text-base)}
.tf-health-table-toggle:focus-visible{outline:2px solid var(--tf-hm-ring);outline-offset:2px}
.tf-health-chevron{font-size:.6rem;transition:transform var(--tf-duration-medium) var(--tf-ease)}
.tf-health-table-toggle[aria-expanded=true] .tf-health-chevron{transform:rotate(180deg)}
.tf-health-tab{display:grid;grid-template-columns:minmax(0,1fr) auto;grid-template-rows:auto auto auto;column-gap:.5rem;align-items:center;min-width:0;padding:.5rem .45rem .5rem .7rem;border:1px solid var(--tf-hm-line);border-radius:var(--tf-radius-md);background:var(--tf-hm-goal);color:inherit;font:inherit;text-align:left;cursor:pointer;transition:border-color var(--tf-duration-medium) var(--tf-ease),background-color var(--tf-duration-medium) var(--tf-ease)}
.tf-health-tab:hover{border-color:var(--tf-hm-line-strong)}
.tf-health-tab[aria-selected=true]{border-color:var(--tf-hm-selected);background:var(--tf-hm-raised)}
.tf-health-tab:focus-visible{outline:2px solid var(--tf-hm-ring);outline-offset:-2px}
.tf-health-tab-title{min-width:0;font-size:.78rem;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-health-tab-status{display:flex;align-items:center;gap:.4rem;min-width:0}
.tf-health-help{display:inline-grid;place-items:center;flex:0 0 auto;width:1rem;height:1rem;border:1px solid var(--tf-hm-line-strong);border-radius:50%;font-size:.64rem;font-weight:700;color:var(--pst-color-text-muted);cursor:help}
.tf-health-hint{position:fixed;z-index:1250;max-width:16rem;padding:.4rem .55rem;border:1px solid var(--tf-hm-line-strong);border-radius:.45rem;background:var(--pst-color-surface);color:var(--pst-color-text-base);font-size:.72rem;font-weight:500;line-height:1.35;box-shadow:0 6px 18px rgba(0,0,0,.16);opacity:0;visibility:hidden;transform:translateY(3px);transition:opacity var(--tf-duration-fast) var(--tf-ease),transform var(--tf-duration-fast) var(--tf-ease),visibility var(--tf-duration-fast) linear;pointer-events:none}
.tf-health-hint.visible{opacity:1;visibility:visible;transform:none}
.tf-health-verdict{font-size:.78rem;font-weight:700;letter-spacing:.02em}
.tf-health-verdict.failed{color:var(--tf-hm-fail-ink)}.tf-health-verdict.passed{color:var(--tf-hm-pass-ink)}
.tf-health-count{min-width:0;font-size:.72rem;color:var(--pst-color-text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-health-count b{color:var(--pst-color-text-base);font-weight:700}
.tf-health-thumb{grid-column:2;grid-row:1/span 3;display:block;width:76px;height:auto}
.tf-health-legend{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem 1.1rem;margin:0 0 .6rem;font-size:.74rem;color:var(--pst-color-text-muted)}
.tf-health-legend>span{display:inline-flex;align-items:center;gap:.4rem}
.tf-health-swatch{display:inline-block;flex:0 0 auto;width:12px;height:12px;border-radius:3px}
.tf-health-swatch.passed{background:var(--tf-hm-pass)}.tf-health-swatch.failed{background:var(--tf-hm-fail)}.tf-health-swatch.na{background:var(--tf-hm-na)}
.tf-health-swatch.own{position:relative;border:1.5px solid var(--tf-hm-fail);border-radius:4px}
.tf-health-swatch.own::after{content:"";position:absolute;left:2px;top:2px;width:5px;height:5px;border-radius:50%;background:var(--tf-hm-fail)}
.tf-health-glyph{display:block;width:21px;height:12px;fill:color-mix(in srgb,var(--pst-color-text-muted) 70%,transparent)}
.tf-health-map-wrap{position:relative;border-radius:14px}
.tf-health-map-wrap.tf-health-product-failed{box-shadow:0 0 0 1.5px var(--tf-hm-fail)}
.tf-health-map{display:block;width:100%;animation:tf-health-in 260ms var(--tf-ease) both}
@keyframes tf-health-in{from{opacity:0}to{opacity:1}}
.tf-health-map a,.tf-health-map a:hover{cursor:pointer;outline:none;text-decoration:none}
.tf-health-map text{pointer-events:none}
#verification-health-map .tf-health-goal{fill:var(--tf-hm-goal);stroke:var(--tf-hm-line);stroke-width:1;transition:stroke var(--tf-duration-medium) var(--tf-ease)}
#verification-health-map .tf-health-feature{fill:var(--tf-hm-feature);stroke:var(--tf-hm-line);stroke-width:1;transition:stroke var(--tf-duration-medium) var(--tf-ease)}
#verification-health-map .tf-health-tile{transition:fill 120ms var(--tf-ease)}
#verification-health-map .tf-health-tile.passed{fill:var(--tf-hm-pass)}
#verification-health-map .tf-health-tile.failed{fill:var(--tf-hm-fail)}
#verification-health-map .tf-health-tile.na{fill:var(--tf-hm-na)}
#verification-health-map .tf-health-tile.passed.tf-hover{fill:var(--tf-hm-pass-hover)}
#verification-health-map .tf-health-tile.failed.tf-hover{fill:var(--tf-hm-fail-hover)}
#verification-health-map .tf-health-tile.na.tf-hover{fill:var(--tf-hm-na-hover)}
#verification-health-map .tf-health-own-failed{stroke:var(--tf-hm-fail);stroke-width:1.6}
#verification-health-map .tf-health-map rect.tf-lineage:not(.tf-health-own-failed){stroke:var(--tf-hm-lineage)}
.tf-health-dot{transition:opacity var(--tf-duration-medium) var(--tf-ease),fill var(--tf-duration-medium) var(--tf-ease)}
#verification-health-map .tf-health-dot.passed{fill:var(--tf-hm-pass-ink)}
#verification-health-map .tf-health-dot.failed{fill:var(--tf-hm-fail)}
#verification-health-map .tf-health-dot.na{opacity:0}
.tf-health-label-goal{font-size:13px;font-weight:650;fill:var(--pst-color-text-base)}
.tf-health-label-feature{font-size:12px;font-weight:500;fill:var(--pst-color-text-muted)}
.tf-health-ring{fill:none;stroke:var(--tf-hm-ring);stroke-width:1.5;opacity:0;pointer-events:none;transition:opacity 140ms var(--tf-ease),transform 150ms var(--tf-ease),width 150ms var(--tf-ease),height 150ms var(--tf-ease)}
.tf-health-ring.visible{opacity:1}
.tf-health-ring.instant{transition:opacity 140ms var(--tf-ease)}
.tf-health-tooltip{position:fixed;z-index:1200;width:292px;max-width:calc(100vw - 20px);padding:.66rem .76rem .6rem;border:1px solid var(--tf-hm-line-strong);border-radius:var(--tf-radius-md);background:color-mix(in srgb,var(--pst-color-surface) 96%,var(--pst-color-text-base) 4%);color:var(--pst-color-text-base);box-shadow:0 12px 32px rgba(0,0,0,.18),0 2px 6px rgba(0,0,0,.08);font-size:.75rem;line-height:1.35;text-align:left;opacity:0;visibility:hidden;transform:translateY(4px);transition:opacity var(--tf-duration-medium) var(--tf-ease),transform var(--tf-duration-medium) var(--tf-ease),visibility var(--tf-duration-medium) linear,left 120ms var(--tf-ease),top 120ms var(--tf-ease);pointer-events:none}
.tf-health-tooltip.visible{opacity:1;visibility:visible;transform:none}
.tf-health-tooltip.instant{transition:opacity var(--tf-duration-medium) var(--tf-ease),transform var(--tf-duration-medium) var(--tf-ease),visibility var(--tf-duration-medium) linear}
.tf-health-tooltip-head{display:flex;align-items:center;justify-content:space-between;gap:.5rem;margin-bottom:.3rem}
.tf-health-tooltip-kind{font-size:.64rem;font-weight:800;letter-spacing:.055em;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-health-pill{padding:.05rem .45rem;border-radius:999px;font-size:.66rem;font-weight:750;white-space:nowrap}
.tf-health-pill.failed{color:var(--tf-hm-fail-ink);background:color-mix(in srgb,var(--tf-hm-fail) 16%,transparent)}
.tf-health-pill.passed{color:var(--tf-hm-pass-ink);background:color-mix(in srgb,var(--tf-hm-pass) 24%,transparent)}
.tf-health-pill.na{color:var(--pst-color-text-muted);background:color-mix(in srgb,var(--pst-color-text-base) 8%,transparent)}
.tf-health-tooltip-title{font-size:.84rem;font-weight:650;line-height:1.28}
.tf-health-tooltip-path{margin:.15rem 0 0;color:var(--pst-color-text-muted)}
.tf-health-tooltip-rows{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.18rem 1rem;margin-top:.45rem;padding-top:.42rem;border-top:1px solid var(--tf-hm-line)}
.tf-health-tooltip-rows .sub{grid-column:1/-1;margin-top:.12rem;font-size:.64rem;font-weight:650;letter-spacing:.05em;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-health-tooltip-rows .sub:first-child{margin-top:0}
.tf-health-tooltip-rows .note{grid-column:1/-1;color:var(--pst-color-text-muted)}
.tf-health-tooltip-rows .value{font-weight:700;font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
.tf-health-tooltip-rows .value.failed{color:var(--tf-hm-fail-ink)}.tf-health-tooltip-rows .value.passed{color:var(--tf-hm-pass-ink)}
.tf-health-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.25rem;margin-top:.45rem;padding-top:.45rem;border-top:1px solid var(--tf-hm-line)}
.tf-health-chip{padding:.12rem .2rem;border:1px solid transparent;border-radius:5px;font-size:.64rem;font-weight:650;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--pst-color-text-muted);background:color-mix(in srgb,var(--pst-color-text-base) 6%,transparent)}
.tf-health-chip.current{border-color:var(--tf-hm-selected)}
.tf-health-chip.failed{color:var(--tf-hm-fail-ink);background:color-mix(in srgb,var(--tf-hm-fail) 16%,transparent)}
.tf-health-chip.passed{color:var(--tf-hm-pass-ink);background:color-mix(in srgb,var(--tf-hm-pass) 24%,transparent)}
.tf-health-go{margin-top:.45rem;color:var(--pst-color-text-muted)}
.tf-health-go b{font-weight:650;color:var(--pst-color-text-base)}
.tf-health-table{position:absolute;top:calc(100% + 6px);left:0;right:0;z-index:40;display:grid;gap:.55rem;max-height:min(72vh,640px);overflow:auto;padding:.7rem .8rem .65rem;border:1px solid var(--tf-hm-line-strong);border-radius:var(--tf-radius-md);background:color-mix(in srgb,var(--pst-color-surface) 97%,var(--pst-color-text-base) 3%);box-shadow:0 18px 44px rgba(0,0,0,.22),0 2px 6px rgba(0,0,0,.08);container-type:inline-size;animation:tf-health-drop var(--tf-duration-medium) var(--tf-ease) both}
.tf-health-table[hidden]{display:none}
@keyframes tf-health-drop{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.tf-health-table-head{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem 1rem}
.tf-health-table-title{font-size:.8rem;font-weight:700}
.tf-health-table-legend{display:flex;flex-wrap:wrap;align-items:center;gap:.25rem .9rem;font-size:.7rem;color:var(--pst-color-text-muted)}
.tf-health-table-legend>span{display:inline-flex;align-items:center;gap:.35rem}
.tf-health-table-close{display:inline-grid;place-items:center;width:24px;height:24px;margin-left:auto;padding:0;border:1px solid transparent;border-radius:6px;background:none;color:var(--pst-color-text-muted);font:inherit;font-size:1rem;line-height:1;cursor:pointer}
.tf-health-table-close:hover{border-color:var(--tf-hm-line-strong);color:var(--pst-color-text-base)}
.tf-health-table-close:focus-visible{outline:2px solid var(--tf-hm-ring);outline-offset:1px}
.tf-health-rows{position:relative;display:grid;gap:2px}
.tf-health-rows-group{display:grid;gap:2px}
.tf-health-rows-label{display:flex;align-items:center;gap:.35rem;margin:.5rem 0 .15rem;padding:0 8px;font-size:.64rem;font-weight:750;letter-spacing:.06em;text-transform:uppercase}
.tf-health-rows-label::after{content:"";flex:1 1 auto;height:1px;background:currentColor;opacity:.38}
.tf-health-rows-label.failed{color:var(--tf-hm-fail-ink)}.tf-health-rows-label.passed{color:var(--tf-hm-pass-ink)}
.tf-health-row{display:grid;grid-template-columns:var(--tf-row-head,250px) minmax(0,1fr);align-items:center;column-gap:14px;min-width:0;padding:4px 8px;border:1px solid transparent;border-radius:8px;outline:none;cursor:pointer;transition:border-color var(--tf-duration-fast) var(--tf-ease),background-color var(--tf-duration-fast) var(--tf-ease)}
.tf-health-row:hover{border-color:var(--tf-hm-line);background:var(--tf-hm-goal)}
.tf-health-row[aria-selected=true]{border-color:var(--tf-hm-selected);background:var(--tf-hm-raised)}
.tf-health-row:focus-visible{box-shadow:0 0 0 2px var(--tf-hm-ring)}
.tf-health-row-head{display:grid;grid-template-columns:minmax(0,1fr) auto 3.6rem;align-items:center;column-gap:.55rem;min-width:0;font-size:.76rem}
.tf-health-row-name{min-width:0;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-health-row .tf-health-verdict{font-size:.72rem}
.tf-health-row-count{font-size:.7rem;font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap;color:var(--pst-color-text-muted)}
.tf-health-row-count b{color:var(--pst-color-text-base);font-weight:700}
.tf-health-row-strip{display:block;width:100%;height:16px}
#verification-health-map .tf-health-row-strip .tf-health-tile.na,#verification-health-map .tf-health-table .tf-health-swatch.na{fill:var(--tf-hm-na-strong);background:var(--tf-hm-na-strong)}
.tf-health-band{position:absolute;top:0;bottom:0;border-radius:3px;background:color-mix(in srgb,var(--tf-hm-ring) 14%,transparent);box-shadow:0 0 0 1px color-mix(in srgb,var(--tf-hm-ring) 65%,transparent);opacity:0;pointer-events:none;transition:opacity var(--tf-duration-fast) var(--tf-ease)}
.tf-health-band.visible{opacity:1}
.tf-health-table-foot{min-height:2.7em;font-size:.72rem;line-height:1.35;color:var(--pst-color-text-muted)}
.tf-health-table-foot b{font-weight:650;color:var(--pst-color-text-base)}
.tf-health-mark{white-space:nowrap}
.tf-health-mark.failed{color:var(--tf-hm-fail-ink)}.tf-health-mark.passed{color:var(--tf-hm-pass-ink)}
@container (max-width:760px){.tf-health-row{--tf-row-head:176px}.tf-health-row-word{display:none}}
@container (max-width:600px){.tf-health-table-legend{order:3;flex-basis:100%}}
@container (max-width:480px){.tf-health-row{--tf-row-head:118px}.tf-health-row-count{display:none}.tf-health-row-head{grid-template-columns:minmax(0,1fr) auto}}
.tf-health-thumb.tf-health-thumb-radial{width:54px;height:54px;justify-self:center}
.tf-health-radial{position:absolute;inset:0;display:block;width:100%;height:100%;overflow:visible;visibility:hidden}
#verification-health-map[data-view=radial] .tf-health-radial{visibility:visible;animation:tf-health-in 260ms var(--tf-ease) both}
#verification-health-map[data-view=radial] .tf-health-map{visibility:hidden;animation:none}
#verification-health-map[data-view=radial] .tf-health-legend-tree,#verification-health-map:not([data-view=radial]) .tf-health-legend-rings{display:none}
.tf-health-radial a,.tf-health-radial a:hover{cursor:pointer;outline:none;text-decoration:none}
.tf-health-radial text{pointer-events:none}
.tf-health-radial .tf-health-radial-goal,.tf-health-radial [data-health-ring]{pointer-events:auto}
#verification-health-map .tf-health-radial .tf-health-goal,#verification-health-map .tf-health-thumb-radial .tf-health-goal{fill:var(--tf-hm-radial-goal)}
#verification-health-map .tf-health-radial .tf-health-feature,#verification-health-map .tf-health-thumb-radial .tf-health-feature{fill:var(--tf-hm-radial-feature)}
#verification-health-map .tf-health-radial-center{fill:var(--tf-hm-goal);stroke:var(--tf-hm-line);stroke-width:1}
#verification-health-map .tf-health-radial path.tf-lineage:not(.tf-health-own-failed){stroke:var(--tf-hm-lineage)}
.tf-health-radial-own{pointer-events:none}
.tf-health-radial-kicker{font-size:10px;font-weight:750;letter-spacing:.08em;fill:var(--pst-color-text-muted);text-anchor:middle}
.tf-health-radial-verdict{font-weight:800;letter-spacing:.02em;text-anchor:middle}
.tf-health-radial-verdict.failed{fill:var(--tf-hm-fail-ink)}.tf-health-radial-verdict.passed{fill:var(--tf-hm-pass-ink)}
.tf-health-radial-count{font-size:11.5px;fill:var(--pst-color-text-muted);text-anchor:middle}
.tf-health-radial-name{font-size:9.5px;font-weight:650;letter-spacing:.02em;fill:var(--pst-color-text-muted);text-anchor:middle}
.tf-health-radial-name.current{fill:var(--pst-color-text-base)}
.tf-health-radial-name.failed{fill:var(--tf-hm-fail-ink)}.tf-health-radial-name.passed{fill:var(--tf-hm-pass-ink)}
.tf-health-radial-name[data-health-ring]{cursor:pointer;outline:none}
.tf-health-radial-name[data-health-ring]:hover,.tf-health-radial-name[data-health-ring]:focus-visible{text-decoration:underline}
.tf-health-radial-leader{fill:none;stroke:var(--tf-hm-line-strong);stroke-width:1}
.tf-health-radial-passline{fill:none;stroke:var(--tf-hm-line-strong);stroke-width:1;stroke-dasharray:2 3}
.tf-health-radial-ring{fill:none;stroke:var(--tf-hm-ring);stroke-width:1.5;opacity:0;pointer-events:none;transition:opacity 140ms var(--tf-ease)}
.tf-health-radial-ring.visible{opacity:1}
.tf-health-tools{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.35rem 1rem;margin:-.2rem 0 .25rem;font-size:.74rem;color:var(--pst-color-text-muted)}
.tf-health-stamp b{font-weight:650;color:var(--pst-color-text-base)}
.tf-health-stamp code{padding:0 .3rem;border:0;border-radius:4px;background:var(--tf-hm-goal);color:inherit;font-size:.7rem}
.tf-health-stamp .passed{font-weight:650;color:var(--tf-hm-pass-ink)}.tf-health-stamp .failed{font-weight:650;color:var(--tf-hm-fail-ink)}
.tf-health-actions{display:inline-flex;flex-wrap:wrap;gap:.35rem}
.tf-health-action{display:inline-flex;align-items:center;gap:.4rem;height:26px;padding:0 .6rem;border:1px solid var(--tf-hm-line);border-radius:7px;background:var(--pst-color-background);color:var(--pst-color-text-base);font:inherit;font-size:.74rem;font-weight:600;cursor:pointer;transition:border-color var(--tf-duration-medium) var(--tf-ease),background-color var(--tf-duration-medium) var(--tf-ease)}
.tf-health-action:hover{border-color:var(--tf-hm-line-strong)}
.tf-health-action[aria-pressed=true]{border-color:var(--tf-hm-selected);background:var(--tf-hm-raised)}
.tf-health-action[aria-disabled=true]{color:var(--pst-color-text-muted);cursor:default}
.tf-health-action[aria-disabled=true]:hover{border-color:var(--tf-hm-line)}
.tf-health-action:focus-visible{outline:2px solid var(--tf-hm-ring);outline-offset:2px}
.tf-health-action i{font-size:.72rem;color:var(--pst-color-text-muted)}
.tf-health-action kbd{padding:0 .3rem;border:1px solid var(--tf-hm-line-strong);border-radius:4px;background:none;box-shadow:none;color:var(--pst-color-text-muted);font:inherit;font-size:.66rem}
.tf-health-causes{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem .45rem;min-height:28px;margin:.05rem 0 .5rem;font-size:.74rem}
.tf-health-causes-title{margin-right:.15rem;font-size:.64rem;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-health-causes-none{font-weight:600;color:var(--tf-hm-pass-ink)}
.tf-health-cause{display:inline-flex;align-items:center;gap:.35rem;height:26px;padding:0 .65rem;border:1px solid color-mix(in srgb,var(--tf-hm-fail) 42%,transparent);border-radius:999px;background:color-mix(in srgb,var(--tf-hm-fail) 8%,transparent);color:var(--pst-color-text-base);font:inherit;font-size:.74rem;cursor:pointer;transition:background-color var(--tf-duration-fast) var(--tf-ease),border-color var(--tf-duration-fast) var(--tf-ease)}
.tf-health-cause b{font-weight:750;color:var(--tf-hm-fail-ink)}
.tf-health-cause:hover{border-color:var(--tf-hm-fail)}
.tf-health-cause[aria-pressed=true]{border-color:var(--tf-hm-fail);background:color-mix(in srgb,var(--tf-hm-fail) 22%,transparent)}
.tf-health-cause:focus-visible,.tf-health-cause-clear:focus-visible{outline:2px solid var(--tf-hm-ring);outline-offset:2px}
.tf-health-cause-clear{padding:0 .2rem;border:0;background:none;color:var(--pst-color-text-muted);font:inherit;font-size:.74rem;text-decoration:underline;cursor:pointer}
.tf-health-changes-key{display:inline-flex;align-items:center;gap:.35rem;margin-left:.35rem;font-size:.72rem;color:var(--pst-color-text-muted)}
.tf-health-changes-key i{display:inline-block;width:11px;height:11px;margin-left:.3rem;border-radius:3px}
.tf-health-changes-key i.new{box-shadow:inset 0 0 0 2.5px var(--tf-hm-fail-ink)}.tf-health-changes-key i.fixed{box-shadow:inset 0 0 0 2.5px var(--tf-hm-pass-ink)}
#verification-health-map .tf-health-dim{opacity:.13}
#verification-health-map path.tf-health-hit,#verification-health-map rect.tf-health-hit{stroke:var(--tf-hm-ring);stroke-width:2.4}
#verification-health-map .tf-health-new{stroke:var(--tf-hm-fail-ink);stroke-width:3.5}
#verification-health-map .tf-health-fixed{stroke:var(--tf-hm-pass-ink);stroke-width:3.5}
.tf-health-delta{display:inline-flex;gap:.3rem;margin-left:.4rem;font-weight:750}
.tf-health-delta .up{color:var(--tf-hm-fail-ink)}.tf-health-delta .down{color:var(--tf-hm-pass-ink)}
.tf-health-why{margin-top:.45rem;padding-top:.4rem;border-top:1px solid var(--tf-hm-line)}
.tf-health-why b{font-weight:700}
.tf-health-dashline{display:inline-block;width:18px;border-top:1.5px dashed var(--tf-hm-line-strong)}
.tf-health-find{position:fixed;inset:0;z-index:1400;display:grid;align-items:start;justify-items:center;padding-top:11vh;background:rgba(0,0,0,.38)}
.tf-health-find[hidden]{display:none}
.tf-health-find-box{display:grid;grid-template-rows:auto minmax(0,1fr) auto;width:min(660px,calc(100vw - 24px));max-height:72vh;overflow:hidden;border:1px solid var(--tf-hm-line-strong);border-radius:var(--tf-radius-md);background:var(--pst-color-surface);box-shadow:0 24px 60px rgba(0,0,0,.35)}
.tf-health-find-input{width:100%;padding:.85rem 1rem;border:0;border-bottom:1px solid var(--tf-hm-line);background:none;color:var(--pst-color-text-base);font:inherit;font-size:.95rem;outline:none}
.tf-health-find-list{overflow:auto;padding:.35rem}
.tf-health-find-item{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:.75rem;padding:.42rem .6rem;border-radius:8px;cursor:pointer}
.tf-health-find-item[aria-selected=true]{background:var(--tf-hm-raised)}
.tf-health-find-marks{display:inline-flex;gap:2px}
.tf-health-find-marks i{width:9px;height:9px;border-radius:2px;background:var(--tf-hm-na-strong)}
.tf-health-find-marks i.passed{background:var(--tf-hm-pass)}.tf-health-find-marks i.failed{background:var(--tf-hm-fail)}
.tf-health-find-marks i.first{margin-right:3px}
.tf-health-find-text{min-width:0}
.tf-health-find-name{display:block;font-size:.82rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-health-find-path{display:block;font-size:.7rem;color:var(--pst-color-text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-health-find-id{font-family:var(--pst-font-family-monospace);font-size:.66rem;color:var(--pst-color-text-muted)}
.tf-health-find-empty{padding:1rem;text-align:center;font-size:.82rem;color:var(--pst-color-text-muted)}
.tf-health-find-foot{padding:.45rem .9rem;border-top:1px solid var(--tf-hm-line);font-size:.7rem;color:var(--pst-color-text-muted)}
@media(prefers-reduced-motion:reduce){.tf-health-cause,.tf-health-action,.tf-health-radial,.tf-health-radial-ring,.tf-health-tab,.tf-health-hint,.tf-health-edge,.tf-health-edge button,.tf-health-table,.tf-health-table-toggle,.tf-health-chevron,.tf-health-row,.tf-health-band,.tf-health-map,.tf-health-map rect,.tf-health-dot,.tf-health-ring,.tf-health-tooltip{animation:none!important;transition:none!important}}
</style>
<div class="tf-health-tools" id="tf-health-tools"><span class="tf-health-stamp" id="tf-health-stamp"></span><span class="tf-health-actions"><button type="button" class="tf-health-action" id="tf-health-find-open" aria-haspopup="dialog" aria-controls="tf-health-find" data-tip="Find a goal, capability or contract and show it on the map. Shortcut: /"><i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>Find<kbd>/</kbd></button><button type="button" class="tf-health-action" id="tf-health-changes" aria-pressed="false"><i class="fa-solid fa-code-compare" aria-hidden="true"></i>Changes</button><button type="button" class="tf-health-action" id="tf-health-copy" data-tip="Copy a link to this layer and the selected contract."><i class="fa-solid fa-link" aria-hidden="true"></i><span>Copy link</span></button></span></div>
<div class="tf-health-layerbar" id="tf-health-layerbar">
<div class="tf-health-scroller" id="tf-health-scroller"><div class="tf-health-layers" id="tf-health-tabs" role="tablist" aria-label="Health layer"></div></div>
<div class="tf-health-edge left" aria-hidden="true"><button type="button" tabindex="-1" data-health-scroll="-1"></button></div>
<div class="tf-health-edge right" aria-hidden="true"><button type="button" tabindex="-1" data-health-scroll="1"></button></div>
<button type="button" class="tf-health-table-toggle" id="tf-health-table-toggle" aria-expanded="false" aria-controls="tf-health-table" aria-haspopup="dialog" data-tip="Every layer as one row, every contract as one column. A row opens its map."><i class="fa-solid fa-table-list" aria-hidden="true"></i>All layers<i class="fa-solid fa-chevron-down tf-health-chevron" aria-hidden="true"></i></button>
<div class="tf-health-table" id="tf-health-table" role="dialog" aria-label="All health layers" hidden>
<div class="tf-health-table-head"><span class="tf-health-table-title">All layers</span><span class="tf-health-table-legend" aria-hidden="true"><span><i class="tf-health-swatch passed"></i>Pass</span><span><i class="tf-health-swatch failed"></i>Fail</span><span><i class="tf-health-swatch na"></i>N/A</span><span><i class="tf-health-swatch own"></i>Goal or capability fails its own check</span></span><button type="button" class="tf-health-table-close" aria-label="Close">&times;</button></div>
<div class="tf-health-rows" id="tf-health-rows" role="listbox" aria-label="Health layer"></div>
<div class="tf-health-table-foot" id="tf-health-table-foot"></div>
</div>
</div>
<div id="tf-health-hint" class="tf-health-hint" role="tooltip" aria-hidden="true"></div>
<div class="tf-health-causes" id="tf-health-causes"></div>
<div class="tf-health-find" id="tf-health-find" role="dialog" aria-modal="true" aria-label="Find on the map" hidden><div class="tf-health-find-box"><input class="tf-health-find-input" id="tf-health-find-input" type="search" placeholder="Find a goal, capability or contract by name or ID" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="true" aria-controls="tf-health-find-list"><div class="tf-health-find-list" id="tf-health-find-list" role="listbox" aria-label="Matches"></div><div class="tf-health-find-foot">↑ ↓ move · Enter shows it on the map · Esc closes</div></div></div>
<div class="tf-health-legend" aria-hidden="true"><span><i class="tf-health-swatch passed"></i>Pass</span><span><i class="tf-health-swatch failed"></i>Fail</span><span><i class="tf-health-swatch na"></i>N/A: no checks</span><span><i class="tf-health-swatch own"></i>Goal or capability fails its own check</span><span class="tf-health-legend-rings"><svg class="tf-health-glyph" viewBox="0 0 21 12"><path d="M.5 12a10 10 0 0 1 20 0h-2.6a7.4 7.4 0 0 0-14.8 0z"/><path d="M5 12a5.5 5.5 0 0 1 11 0h-2.6a2.9 2.9 0 0 0-5.8 0z"/></svg>Inside out: goals, capabilities, contracts, then one ring per layer</span><span class="tf-health-legend-rings"><i class="tf-health-dashline"></i>Dashed line: failing layers inside, passing outside</span><span class="tf-health-legend-tree"><svg class="tf-health-glyph" viewBox="0 0 21 12"><rect width="5" height="12" rx="1.5"/><rect x="7" width="6" height="5" rx="1.5"/><rect x="15" width="6" height="5" rx="1.5"/><rect x="7" y="7" width="6" height="5" rx="1.5"/><rect x="15" y="7" width="6" height="5" rx="1.5"/></svg>Requirement and its technical requirements</span></div>
<div class="tf-health-map-wrap" id="tf-health-map-wrap"><svg class="tf-health-map" id="tf-health-map" role="group" aria-label="Verification health by goal, capability, and contract"></svg><svg class="tf-health-radial" id="tf-health-radial" role="group" aria-label="Overall health: goals, capabilities and contracts inside, one ring per layer outside"></svg></div>
<div id="tf-health-tooltip" class="tf-health-tooltip" role="tooltip" aria-hidden="true"></div>
<script>__D3_HIERARCHY__</script>
<script>
(()=>{
const model=__MODEL__;
const LAYERS=[
 ["overall","Overall","Final verdict; the rings show which layers fail where."],
 ["execution","Execution","Did the tests and scenarios that ran pass?"],
 ["coverage","Coverage","Does every required case have a passing test?"],
 ["faults","Fault model","Do the tests catch the errors they should?"],
 ["evidence","Evidence quality","Is the evidence realistic, traceable, qualified, up to date?"],
 ["assurance","Assurance","Do goals and capabilities pass their integration and validation checks?"]
];
const METRIC_LABELS={
 "Tests":"Tests passed",
 "Scenarios":"Scenarios passed",
 "Required scenarios":"Required scenarios passing",
 "Targets":"Required cases covered",
 "Fault groups":"Fault checks passed",
 "Representation":"Right kind of target",
 "Provenance":"Traceable to its run",
 "Producers":"Made by qualified tools",
 "Freshness":"Up to date",
 "M&S":"Model validated",
 "Integration":"Integration checks",
 "Validation":"Validation checks",
 "Unattributed failure":"Fails for an unclear reason",
 "Assurance profile":"Assurance plan exists"
};
const KIND={product:"Product / System",goal:"Goal",feature:"Capability",requirement:"Requirement",treq:"Technical requirement"};
const DESTINATION={product:"Product assurance",goal:"Outcome assurance",feature:"Capability assurance",requirement:"Contract evidence",treq:"Technical assurance"};
const PAD={product:[14,0,0],goal:[8,30,8],feature:[5,24,6],cluster:[2,0,0]};
const HEAD_UNITS={goal:1,feature:1.6};
const RADIUS={goal:12,feature:8,leaf:3.5};
const root=model.root,rows=[root,...model.items];
const rowById=new Map(rows.map(row=>[row.id,row]));
const children=new Map();
model.items.forEach(row=>{if(!children.has(row.parent))children.set(row.parent,[]);children.get(row.parent).push(row)});
const svg=document.getElementById("tf-health-map"),wrap=document.getElementById("tf-health-map-wrap");
const radial=document.getElementById("tf-health-radial"),section=document.getElementById("verification-health-map");
const tabs=document.getElementById("tf-health-tabs"),tooltip=document.getElementById("tf-health-tooltip");
const bar=document.getElementById("tf-health-layerbar"),scroller=document.getElementById("tf-health-scroller"),hint=document.getElementById("tf-health-hint");
const tableToggle=document.getElementById("tf-health-table-toggle"),table=document.getElementById("tf-health-table");
const rowsBox=document.getElementById("tf-health-rows"),tableFoot=document.getElementById("tf-health-table-foot");
const edges={left:bar.querySelector(".tf-health-edge.left"),right:bar.querySelector(".tf-health-edge.right")};
const toolsRow=document.getElementById("tf-health-tools"),stamp=document.getElementById("tf-health-stamp"),causesRow=document.getElementById("tf-health-causes");
const findBox=document.getElementById("tf-health-find"),findInput=document.getElementById("tf-health-find-input"),findList=document.getElementById("tf-health-find-list");
const changesButton=document.getElementById("tf-health-changes"),copyButton=document.getElementById("tf-health-copy");
const NS="http://www.w3.org/2000/svg",measure=document.createElement("canvas").getContext("2d");
let mode="overall",width=0,height=0,entries=[],entryById=new Map(),ring=null,showTimer=null,hideTimer=null,hoveredId=null,frame=0,pendingForce=false;
const compact=new Set();
const escapeHtml=value=>String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const status=(row,key=mode)=>row?.own?.[key]?.status||"na";
const word=value=>value==="passed"?"PASS":value==="failed"?"FAIL":"N/A";
const mark=value=>value==="failed"?"✕":"✓";
const clip=(text,max)=>{text=String(text||"");if(text.length<=max)return text;const cut=text.slice(0,max);return cut.slice(0,Math.max(cut.lastIndexOf(" "),max-12)).trimEnd()+"…"};
const isContainer=row=>row.level==="goal"||row.level==="feature"||row.level==="product";
function build(row){
 const kids=children.get(row.id)||[];
 if(row.level==="requirement"&&kids.length)return{kind:"cluster",row,children:[{kind:"leaf",row},...kids.map(child=>({kind:"leaf",row:child}))]};
 if(!kids.length)return{kind:"leaf",row};
 return{kind:row.level,row,children:kids.map(build)};
}
const hierarchy=d3.hierarchy(build(root)).sum(node=>node.kind==="leaf"?1:(HEAD_UNITS[node.kind]||0));
const pad=(node,index)=>(PAD[node.data.kind]||[0,0,0])[index];
function tile(parent,x0,y0,x1,y1){
 const kids=parent.children,total=kids.reduce((sum,child)=>sum+child.value,0);
 if(parent.data.kind!=="cluster")return d3.treemapBinary({children:kids,value:total},x0,y0,x1,y1);
 const[self,...rest]=kids,split=x0+(x1-x0)*self.value/total;
 Object.assign(self,{x0,y0,x1:split,y1});
 if(rest.length)d3.treemapBinary({children:rest,value:total-self.value},split,y0,x1,y1);
}
function element(tag,attrs,parent){
 const node=document.createElementNS(NS,tag);
 for(const key in attrs)node.setAttribute(key,attrs[key]);
 parent?.appendChild(node);
 return node;
}
function box(node){return{x:node.x0,y:node.y0,width:Math.max(0,node.x1-node.x0),height:Math.max(0,node.y1-node.y0)}}
function fitLabel(label,max,font){
 measure.font=font;
 const measureWidth=text=>measure.measureText(text).width;
 if(measureWidth(label)<=max)return label;
 const words=label.split(" ");
 for(let count=words.length-1;count>0;count--){
   const candidate=words.slice(0,count).join(" ")+"…";
   if(candidate.length>=7&&measureWidth(candidate)<=max)return candidate;
 }
 return"";
}
function ancestors(row){
 const out=[];
 let current=rowById.get(row.parent);
 while(current&&current.level!=="product"){out.unshift(current);current=rowById.get(current.parent)}
 return out;
}
function contractsInside(row){
 const out=[];
 const walk=item=>{(children.get(item.id)||[]).forEach(child=>{if(child.level==="requirement"||child.level==="treq")out.push(child);walk(child)})};
 walk(row);
 return out;
}
function targetHref(row,key=mode){
 const own=row.own?.[key],canonical=row.layers?.[key],fallback=row.layers?.overall?.href;
 if(isContainer(row))return own?.status==="failed"&&own.href?own.href:fallback;
 if(own&&own.status!=="na"&&own.href)return own.href;
 return canonical?.href||fallback;
}
function destination(row,href){
 const anchor=String(href||"").split("#")[1]||"";
 const section=anchor.includes("-faults-")?"Faults":anchor.includes("technical-support")?"Technical requirements":anchor.includes("-coverage-")?"Coverage":anchor.includes("validation")?"Validation":anchor.includes("integration")?"Integration":"";
 return DESTINATION[row.level]+(section?" › "+section:"");
}
function ariaLabel(row){
 const own=status(row);
 return KIND[row.level]+": "+row.label+", "+(isContainer(row)?(own==="na"?"no own checks":"own checks "+(own==="failed"?"fail":"pass")):word(own));
}
function layerSummary(layer){
 const metrics=(layer?.metrics||[]).filter(metric=>metric.total);
 if(metrics.length===1)return metrics[0].passed+"/"+metrics[0].total;
 return word(layer.status);
}
function valueCell(passed,total){return'<span class="value '+(passed<total?"failed":"passed")+'">'+passed+"/"+total+"</span>"}
function tooltipHtml(row){
 const own=row.own?.[mode]||{status:"na",metrics:[]},container=isContainer(row),path=ancestors(row);
 let body="";
 if(mode==="overall"){
   const parts=LAYERS.slice(1).map(([key,label])=>{
     const layer=row.own?.[key];
     if(!layer||layer.status==="na")return"";
     return'<span>'+label+'</span><span class="value '+layer.status+'">'+mark(layer.status)+" "+layerSummary(layer)+"</span>";
   }).join("");
   if(parts)body+='<div class="sub">'+(container?"Own checks by layer":"By layer")+"</div>"+parts;
 }else{
   const metrics=(own.metrics||[]).filter(metric=>metric.total);
   if(metrics.length)body+='<div class="sub">'+(container?"Own checks":"Checks")+"</div>"+metrics.map(metric=>'<span>'+escapeHtml(METRIC_LABELS[metric.label]||metric.label)+"</span>"+valueCell(metric.passed,metric.total)).join("");
   const unbound=Number(own.unbound_tests||0);
   if(mode==="coverage"&&unbound)body+='<span class="note">'+unbound+(unbound===1?" linked test is":" linked tests are")+" not tied to a required case</span>";
 }
 if(row.level==="requirement"&&(mode==="overall"||mode==="assurance")){
   const support=(row.layers?.assurance?.metrics||[]).find(metric=>metric.label==="TREQ support"&&metric.total);
   if(support)body+='<div class="sub">Technical requirements</div><span>Passing</span>'+valueCell(support.passed,support.total);
 }
 if(container){
   const key=mode==="assurance"?"overall":mode;
   const applicable=contractsInside(row).filter(item=>status(item,key)!=="na"),failing=applicable.filter(item=>status(item,key)==="failed");
   body+='<div class="sub">Contracts inside</div><span>'+(mode==="assurance"?"Failing overall":"Failing")+'</span><span class="value '+(failing.length?"failed":"passed")+'">'+(applicable.length?failing.length+" of "+applicable.length:"none")+"</span>";
 }
 if(!body)body='<span class="note">No checks here</span>';
 const pill=container?(own.status==="na"?"No own checks":own.status==="failed"?"Own checks fail":"Own checks pass"):word(own.status);
 const strip=mode==="overall"?"":'<div class="tf-health-strip">'+LAYERS.map(([key,label])=>'<span class="tf-health-chip '+status(row,key)+(key===mode?" current":"")+'">'+label+"</span>").join("")+"</div>";
 return'<div class="tf-health-tooltip-head"><span class="tf-health-tooltip-kind">'+KIND[row.level]+'</span><span class="tf-health-pill '+own.status+'">'+pill+"</span></div>"
   +'<div class="tf-health-tooltip-title">'+escapeHtml(row.label)+"</div>"
   +(path.length?'<div class="tf-health-tooltip-path">'+path.map(item=>escapeHtml(clip(item.short||item.label,42))).join(" › ")+"</div>":"")
   +'<div class="tf-health-tooltip-rows">'+body+"</div>"
   +strip
   +whyLine(row)
   +'<div class="tf-health-go">Opens <b>'+escapeHtml(destination(row,targetHref(row)))+"</b></div>";
}
function instantly(node,apply){
 node.classList.add("instant");
 apply();
 node.getBoundingClientRect();
 node.classList.remove("instant");
}
function moveRing(entry){
 if(!ring)return;
 const inset=entry.kind==="leaf"?1:1.25,area=entry.area;
 const place=()=>{
   ring.setAttribute("rx",Math.max(0,RADIUS[entry.kind]-inset));
   ring.style.transform="translate("+(area.x+inset)+"px,"+(area.y+inset)+"px)";
   ring.style.width=Math.max(0,area.width-2*inset)+"px";
   ring.style.height=Math.max(0,area.height-2*inset)+"px";
 };
 const previous=ring.dataset.center?ring.dataset.center.split(",").map(Number):null;
 const center=[area.x+area.width/2,area.y+area.height/2];
 const near=previous&&Math.hypot(center[0]-previous[0],center[1]-previous[1])<240;
 ring.dataset.center=center.join(",");
 if(ring.classList.contains("visible")&&near)place();else instantly(ring,place);
 ring.classList.add("visible");
}
function clearHighlight(){
 [svg,radial].forEach(canvas=>canvas.querySelectorAll(".tf-hover,.tf-lineage").forEach(node=>node.classList.remove("tf-hover","tf-lineage")));
 radialRing?.classList.remove("visible");
}
function highlight(entry){
 clearHighlight();
 if(entry.radial)return radialHighlight(entry);
 if(entry.kind==="leaf")entry.shape.classList.add("tf-hover");
 ancestors(entry.row).forEach(item=>{const parent=entryById.get(item.id);if(parent&&parent.kind!=="leaf")parent.shape.classList.add("tf-lineage")});
 moveRing(entry);
}
function placeTooltip(rect){
 const gap=12,margin=10,size=tooltip.getBoundingClientRect();
 let left=rect.right+gap;
 if(left+size.width>window.innerWidth-margin)left=rect.left-size.width-gap;
 left=Math.max(margin,Math.min(left,window.innerWidth-size.width-margin));
 let top=rect.top+Math.min(8,Math.max(0,(rect.height-size.height)/2));
 if(top+size.height>window.innerHeight-margin)top=window.innerHeight-size.height-margin;
 tooltip.style.left=Math.round(left)+"px";
 tooltip.style.top=Math.round(Math.max(margin,top))+"px";
}
function showTooltip(entry,immediate){
 clearTimeout(hideTimer);
 highlight(entry);
 if(hoveredId===hoverKey(entry)&&tooltip.classList.contains("visible"))return;
 clearTimeout(showTimer);
 const show=()=>{
   const visible=tooltip.classList.contains("visible");
   hoveredId=hoverKey(entry);
   tooltipEntry=entry;
   tooltip.innerHTML=entry.layer?withMode(entry.layer,()=>tooltipHtml(entry.row)):tooltipHtml(entry.row);
   tooltip.setAttribute("aria-hidden","false");
   const rect=entry.shape.getBoundingClientRect();
   if(visible)placeTooltip(rect);else instantly(tooltip,()=>placeTooltip(rect));
   tooltip.classList.add("visible");
 };
 if(immediate||tooltip.classList.contains("visible"))show();else showTimer=setTimeout(show,110);
}
function hideTooltip(immediate){
 clearTimeout(showTimer);clearTimeout(hideTimer);
 const hide=()=>{hoveredId=null;tooltipEntry=null;clearHighlight();ring?.classList.remove("visible");tooltip.classList.remove("visible");tooltip.setAttribute("aria-hidden","true")};
 if(immediate)hide();else hideTimer=setTimeout(hide,90);
}
// After a pick in the layer table the map sits under a still pointer: hover waits until the pointer moves.
function holdsHover(event){
 if(!hoverHold)return false;
 if(Math.hypot(event.clientX-hoverHold.x,event.clientY-hoverHold.y)<6)return true;
 hoverHold=null;
 return false;
}
function bind(entry){
 entry.link.addEventListener("pointerenter",event=>{if(!holdsHover(event))showTooltip(entry,false)});
 entry.link.addEventListener("pointerleave",event=>{if(!holdsHover(event))hideTooltip(false)});
 entry.link.addEventListener("focus",()=>showTooltip(entry,true));
 entry.link.addEventListener("blur",()=>hideTooltip(true));
}
function headerLabel(node,family){
 const goal=node.data.kind==="goal",x=node.x0+(goal?11:9);
 return fitLabel(node.data.row.short||node.data.row.label,node.x1-x-21,(goal?"650 13px ":"500 12px ")+family);
}
function draw(){
 hideTooltip(true);
 svg.replaceChildren();
 entries=[];entryById=new Map();
 const family=getComputedStyle(document.body).fontFamily;
 hierarchy.eachBefore(node=>{
   const kind=node.data.kind,row=node.data.row;
   if(kind!=="goal"&&kind!=="feature"&&kind!=="leaf")return;
   const area=box(node),link=element("a",{},svg);
   const shape=element("rect",{...area,rx:RADIUS[kind],class:kind==="leaf"?"tf-health-tile na":"tf-health-"+kind},link);
   let dot=null;
   if(kind!=="leaf"&&!compact.has(row.id)){
     const goal=kind==="goal",x=node.x0+(goal?11:9),y=node.y0+(goal?19.5:16.5);
     dot=element("circle",{cx:x+3.5,cy:y-4.3,r:goal?4:3.5,class:"tf-health-dot na"},link);
     const text=headerLabel(node,family);
     if(text)element("text",{x:x+12,y,class:goal?"tf-health-label-goal":"tf-health-label-feature"},link).textContent=text;
   }
   const entry={row,kind,area,link,shape,dot};
   entries.push(entry);
   entryById.set(row.id,entry);
   bind(entry);
 });
 ring=element("rect",{class:"tf-health-ring",width:0,height:0},svg);
 paint();
}
function paint(animated){
 const through=[];
 for(const entry of entries){
   const value=status(entry.row);
   if(entry.kind==="leaf"){
     // Red and green never blend directly: a changing tile passes through the neutral midpoint.
     const neutral=animated&&entry.value&&entry.value!==value&&entry.value!=="na"&&value!=="na";
     entry.shape.setAttribute("class","tf-health-tile "+(neutral?"na":value));
     entry.value=value;
     if(neutral)through.push(entry);
   }else{
     entry.shape.classList.toggle("tf-health-own-failed",value==="failed");
     entry.dot?.setAttribute("class","tf-health-dot "+value);
   }
   entry.link.setAttribute("href",targetHref(entry.row));
   entry.link.setAttribute("aria-label",ariaLabel(entry.row));
 }
 wrap.classList.toggle("tf-health-product-failed",mode!=="overall"&&status(root)==="failed");
 section.dataset.view=mode==="overall"?"radial":"tree";
 applyFocus();
 if(through.length)setTimeout(()=>{through.forEach(entry=>entry.shape.setAttribute("class","tf-health-tile "+entry.value));applyFocus()},120);
}
function thumbnail(key){
 let out="";
 hierarchy.eachBefore(node=>{
   const kind=node.data.kind,row=node.data.row,area=box(node);
   const geometry='x="'+area.x+'" y="'+area.y+'" width="'+area.width+'" height="'+area.height+'"';
   if(kind==="goal")out+="<rect "+geometry+' rx="14" class="tf-health-goal'+(status(row,key)==="failed"?" tf-health-own-failed":"")+'" vector-effect="non-scaling-stroke"/>';
   else if(kind==="feature"&&status(row,key)==="failed")out+="<rect "+geometry+' rx="10" fill="none" class="tf-health-own-failed" vector-effect="non-scaling-stroke"/>';
   else if(kind==="leaf")out+="<rect "+geometry+' class="tf-health-tile '+status(row,key)+'"/>';
 });
 return'<svg class="tf-health-thumb" viewBox="0 0 '+width+" "+height+'" aria-hidden="true" focusable="false">'+out+"</svg>";
}
const layerByKey=new Map(LAYERS.map(layer=>[layer[0],layer]));
const summaryOf=key=>model.summary.layers[key]||{};
const verdictOf=key=>summaryOf(key).status==="passed"?"passed":"failed";
const failingOf=key=>Number(summaryOf(key).failing||0);
// Overall stays first; failing layers follow, most red marks first; passing layers keep their default order.
function layerOrder(){
 const[first,...rest]=LAYERS.map(layer=>layer[0]);
 return{first,failing:rest.filter(key=>verdictOf(key)==="failed").sort((a,b)=>failingOf(b)-failingOf(a)),passing:rest.filter(key=>verdictOf(key)==="passed")};
}
function visualOrder(){const order=layerOrder();return[order.first,...order.failing,...order.passing]}
function tabHtml(key){
 const[,label,tip]=layerByKey.get(key),summary=summaryOf(key),failing=Number(summary.failing||0),applicable=Number(summary.applicable||0);
 const verdict=verdictOf(key);
 const count=failing?"<b>"+failing+"</b> of "+applicable+" fail":"all "+applicable+" pass";
 const name=label+": "+word(verdict)+", "+(failing?failing+" of "+applicable+" fail":"all "+applicable+" pass");
 return'<button type="button" role="tab" class="tf-health-tab" id="tf-health-tab-'+key+'" data-health-mode="'+key+'" aria-label="'+escapeHtml(name)+'" aria-controls="tf-health-map" aria-describedby="tf-health-tip-'+key+'">'
   +'<span class="tf-health-tab-title">'+label+"</span>"
   +(key==="overall"?radialThumb():thumbnail(key))
   +'<span class="tf-health-tab-status"><span class="tf-health-verdict '+verdict+'"><i class="fa-solid '+(verdict==="passed"?"fa-circle-check":"fa-circle-xmark")+'" aria-hidden="true"></i> '+word(verdict)+'</span><span class="tf-health-help" aria-hidden="true" data-tip="'+escapeHtml(tip)+'">?</span></span>'
   +'<span class="tf-health-count">'+count+deltaBadge(key)+"</span>"
   +'<span class="tf-sr-only" id="tf-health-tip-'+key+'">'+escapeHtml(tip)+"</span></button>";
}
function groupHtml(kind,keys){
 if(!keys.length)return"";
 const failed=kind==="failed";
 return'<div class="tf-health-group '+kind+'" role="none" style="flex-grow:'+keys.length+'">'
   +'<div class="tf-health-group-head" aria-hidden="true"><span class="tf-health-group-label"><i class="fa-solid '+(failed?"fa-circle-xmark":"fa-circle-check")+'"></i>'+(failed?"Failing":"Passing")+" · "+keys.length+"</span></div>"
   +'<div class="tf-health-group-cards" role="none">'+keys.map(tabHtml).join("")+"</div></div>";
}
// Overall shows the whole system at once: the product verdict in the centre, goal and capability rings,
// the overall contract ring, then one ring per layer in strip order. Columns follow the all-layers table.
let radialGap=.46,radialEntries=[],radialById=new Map(),radialRing=null,radialGeometry=null;
const hoverKey=entry=>entry.row.id+(entry.layer?"@"+entry.layer:"");
function withMode(key,render){const saved=mode;mode=key;try{return render()}finally{mode=saved}}
const polar=(cx,cy,r,a)=>[cx+r*Math.sin(a),cy-r*Math.cos(a)];
const fixed=value=>Math.round(value*100)/100;
function arcPath(cx,cy,r0,r1,a0,a1){
 const large=a1-a0>Math.PI?1:0,p0=polar(cx,cy,r1,a0),p1=polar(cx,cy,r1,a1),p2=polar(cx,cy,r0,a1),p3=polar(cx,cy,r0,a0);
 return"M"+fixed(p0[0])+","+fixed(p0[1])+"A"+fixed(r1)+","+fixed(r1)+" 0 "+large+" 1 "+fixed(p1[0])+","+fixed(p1[1])
   +"L"+fixed(p2[0])+","+fixed(p2[1])+"A"+fixed(r0)+","+fixed(r0)+" 0 "+large+" 0 "+fixed(p3[0])+","+fixed(p3[1])+"Z";
}
function circlePath(cx,cy,r){return"M"+fixed(cx-r)+","+fixed(cy)+"a"+fixed(r)+","+fixed(r)+" 0 1,0 "+fixed(2*r)+",0a"+fixed(r)+","+fixed(r)+" 0 1,0 "+fixed(-2*r)+",0"}
const angleAt=(unit,gap=radialGap)=>gap/2+unit/tableUnits*(2*Math.PI-gap);
function radialRings(outer){
 const order=layerOrder(),keys=[...order.failing,...order.passing];
 const split=order.failing.length&&order.passing.length?order.failing.length:0;
 const start=.655*outer,gap=Math.max(1.2,.008*outer),passGap=split?Math.max(3,.024*outer):0;
 const thick=(outer-start-passGap-gap*(keys.length-1))/keys.length;
 let radius=start;
 const tracks=keys.map((key,index)=>{
   if(index&&index===split)radius+=passGap;
   const band=[radius,radius+thick];
   radius+=thick+gap;
   return{key,band};
 });
 const passRadius=split?(tracks[split-1].band[1]+tracks[split].band[0])/2:0;
 return{center:.27*outer,goal:[.29*outer,.355*outer],feature:[.365*outer,.425*outer],leaf:[.44*outer,.62*outer],tracks,passRadius};
}
function radialThumb(){
 tableColumns();
 const rings=radialRings(48);
 let out='<circle cx="0" cy="0" r="'+fixed(rings.center)+'" class="tf-health-radial-center"/>';
 tableGroups.forEach(group=>{
   if(group.end<=group.start)return;
   const kind=group.row.level==="goal"?"goal":"feature",band=rings[kind];
   out+='<path d="'+arcPath(0,0,band[0],band[1],angleAt(group.start,.36),angleAt(group.end,.36))+'" class="tf-health-'+kind+(status(group.row,"overall")==="failed"?" tf-health-own-failed":"")+'"/>';
 });
 tableLeaves.forEach(leaf=>{
   const a0=angleAt(leaf.x+.8,.36),a1=angleAt(leaf.x+CELL-.8,.36);
   out+='<path d="'+arcPath(0,0,rings.leaf[0],rings.leaf[1],a0,a1)+'" class="tf-health-tile '+status(leaf.row,"overall")+'"/>';
   rings.tracks.forEach(track=>{out+='<path d="'+arcPath(0,0,track.band[0],track.band[1],a0,a1)+'" class="tf-health-tile '+status(leaf.row,track.key)+'"/>'});
 });
 return'<svg class="tf-health-thumb tf-health-thumb-radial" viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">'+out+"</svg>";
}
function radialEntry(entry){
 entry.radial=true;
 radialEntries.push(entry);
 if(!entry.layer)radialById.set(entry.row.id,entry);
 bind(entry);
}
function drawRadial(){
 tableColumns();
 radial.replaceChildren();
 radialEntries=[];radialById=new Map();
 radial.setAttribute("viewBox","0 0 "+width+" "+height);
 const labelled=width>=720,outer=Math.max(80,Math.min(height/2-(labelled?24:12),width/2-(labelled?210:12)));
 const cx=width/2,cy=height/2,rings=radialRings(outer),family=getComputedStyle(document.body).fontFamily;
 radialGap=Math.min(.8,Math.max(.46,2*Math.asin(Math.min(1,42/(rings.tracks[0]?.band[0]||rings.leaf[1])))));
 radialGeometry={cx,cy,outer,rings};
 const leafAt=new Map(tableLeaves.map(leaf=>[leaf.row.id,leaf])),groupAt=new Map(tableGroups.map(group=>[group.row.id,group])),goals=[];
 // Centre: the product verdict, the same numbers as the Overall card.
 const summary=summaryOf("overall"),verdict=verdictOf("overall"),failing=failingOf("overall"),applicable=Number(summary.applicable||0);
 const counted=failing?failing+" of "+applicable+" fail":"all "+applicable+" pass";
 const centre=element("a",{href:targetHref(root,"overall"),"aria-label":"Product: "+word(verdict)+", "+counted},radial);
 const disc=element("circle",{cx,cy,r:fixed(rings.center),class:"tf-health-radial-center"+(status(root,"overall")==="failed"?" tf-health-own-failed":"")},centre);
 const size=Math.max(15,Math.min(32,rings.center*.4));
 element("text",{x:cx,y:fixed(cy-size*.95),class:"tf-health-radial-kicker"},centre).textContent="OVERALL";
 element("text",{x:cx,y:fixed(cy+size*.36),"font-size":fixed(size),class:"tf-health-radial-verdict "+verdict},centre).textContent=word(verdict);
 element("text",{x:cx,y:fixed(cy+size*.36+16),class:"tf-health-radial-count"},centre).textContent=counted;
 radialEntry({row:root,kind:"product",link:centre,shape:disc,band:[0,rings.center]});
 // Goals, capabilities and contracts in tree order, so keyboard focus walks the tree like on the other maps.
 const drawRow=row=>{
   const group=groupAt.get(row.id),leaf=leafAt.get(row.id);
   if(group&&group.end>group.start){
     const kind=row.level==="goal"?"goal":"feature",band=rings[kind],a0=angleAt(group.start),a1=angleAt(group.end);
     const link=element("a",{href:targetHref(row,"overall"),"aria-label":withMode("overall",()=>ariaLabel(row))},radial);
     const shape=element("path",{d:arcPath(cx,cy,band[0],band[1],a0,a1),class:"tf-health-"+kind+(status(row,"overall")==="failed"?" tf-health-own-failed":"")},link);
     const entry={row,kind,link,shape,band,angles:[a0,a1]};
     if(kind==="goal")goals.push(entry);
     radialEntry(entry);
   }else if(leaf){
     const a0=angleAt(leaf.x+.8),a1=angleAt(leaf.x+CELL-.8);
     const link=element("a",{href:targetHref(row,"overall"),"aria-label":withMode("overall",()=>ariaLabel(row))},radial);
     const shape=element("path",{d:arcPath(cx,cy,rings.leaf[0],rings.leaf[1],a0,a1),class:"tf-health-tile "+status(row,"overall")},link);
     radialEntry({row,kind:"leaf",link,shape,band:rings.leaf,angles:[a0,a1]});
   }
   (children.get(row.id)||[]).forEach(drawRow);
 };
 (children.get(root.id)||[]).forEach(drawRow);
 // One ring per layer: every contract's own status in that layer, and the goal or capability that fails its own check there.
 const cells=element("g",{class:"tf-health-radial-tracks"},radial);
 rings.tracks.forEach(track=>{
   tableLeaves.forEach(leaf=>{
     const a0=angleAt(leaf.x+.8),a1=angleAt(leaf.x+CELL-.8);
     const link=element("a",{href:targetHref(leaf.row,track.key),tabindex:"-1","aria-hidden":"true"},cells);
     const shape=element("path",{d:arcPath(cx,cy,track.band[0],track.band[1],a0,a1),class:"tf-health-tile "+status(leaf.row,track.key)},link);
     radialEntry({row:leaf.row,kind:"track",layer:track.key,link,shape,band:track.band,angles:[a0,a1]});
   });
   tableGroups.forEach(group=>{
     if(group.end<=group.start||status(group.row,track.key)!=="failed")return;
     element("path",{d:arcPath(cx,cy,track.band[0]-1,track.band[1]+1,angleAt(group.start)-.004,angleAt(group.end)+.004),fill:"none",class:"tf-health-own-failed tf-health-radial-own"},cells);
   });
 });
 // The pass line: failing layers inside it, passing layers outside, like the strip's two groups.
 if(rings.passRadius){
   const a0=angleAt(0)-.02,a1=angleAt(tableUnits)+.02,p0=polar(cx,cy,rings.passRadius,a0),p1=polar(cx,cy,rings.passRadius,a1);
   element("path",{d:"M"+fixed(p0[0])+","+fixed(p0[1])+"A"+fixed(rings.passRadius)+","+fixed(rings.passRadius)+" 0 1 1 "+fixed(p1[0])+","+fixed(p1[1]),class:"tf-health-radial-passline"},radial);
 }
 // Ring names sit in the open gap at twelve o'clock; a layer's name opens that layer's map.
 const name=(label,radius,kind,key)=>{
   const fitted=fitLabel(label,2*radius*Math.sin(radialGap/2)-4,"650 9.5px "+family);
   if(!fitted)return;
   const node=element("text",{x:fixed(cx),y:fixed(cy-radius+3.4),class:"tf-health-radial-name "+kind},radial);
   node.textContent=fitted;
   if(!key)return;
   const count=failingOf(key),total=Number(summaryOf(key).applicable||0),title=layerByKey.get(key)[1];
   node.setAttribute("data-health-ring",key);
   node.setAttribute("tabindex","0");
   node.setAttribute("role","button");
   node.setAttribute("aria-label","Open the "+title+" map");
   node.setAttribute("data-tip",title+": "+(count?count+" of "+total+" fail":"all "+total+" pass")+". Opens its map.");
 };
 name("Overall",(rings.leaf[0]+rings.leaf[1])/2,"current",null);
 rings.tracks.forEach(track=>name(layerByKey.get(track.key)[1],(track.band[0]+track.band[1])/2,verdictOf(track.key),track.key));
 if(labelled)placeGoalLabels(goals,cx,cy,outer,family);
 radialRing=element("path",{class:"tf-health-radial-ring",d:""},radial);
 applyFocus();
}
// Goal names in two aligned columns beside the circle; each name belongs to its goal's link.
function placeGoalLabels(goals,cx,cy,outer,family){
 const column=outer+34,spacing=18,room=Math.max(60,width/2-column-14);
 const items=goals.map(entry=>{
   const angle=(entry.angles[0]+entry.angles[1])/2;
   return{entry,angle,side:Math.sin(angle)>=0?1:-1,y:cy-(outer+14)*Math.cos(angle)};
 });
 [1,-1].forEach(side=>{
   const list=items.filter(item=>item.side===side).sort((a,b)=>a.y-b.y);
   list.forEach((item,index)=>{if(index)item.y=Math.max(item.y,list[index-1].y+spacing)});
   let limit=height-10;
   for(let index=list.length-1;index>=0;index--){list[index].y=Math.min(list[index].y,limit);limit=list[index].y-spacing}
 });
 items.forEach(item=>{
   const link=item.entry.link,x=cx+item.side*column,p0=polar(cx,cy,outer+4,item.angle),p1=polar(cx,cy,outer+14,item.angle);
   element("polyline",{points:fixed(p0[0])+","+fixed(p0[1])+" "+fixed(p1[0])+","+fixed(p1[1])+" "+fixed(x-item.side*7)+","+fixed(item.y),class:"tf-health-radial-leader"},link);
   element("circle",{cx:fixed(x),cy:fixed(item.y),r:3.5,class:"tf-health-dot "+status(item.entry.row,"overall")},link);
   const label=fitLabel(item.entry.row.short||item.entry.row.label,room,"650 13px "+family);
   if(!label)return;
   const node=element("text",{x:fixed(x+item.side*9),y:fixed(item.y+4.4),"text-anchor":item.side>0?"start":"end",class:"tf-health-label-goal tf-health-radial-goal"},link);
   node.textContent=label;
 });
}
// Hover: a contract lights its whole ray through every layer ring; containers light their own arc; the centre its disc.
function radialHighlight(entry){
 const{cx,cy,outer,rings}=radialGeometry;
 let path;
 if(entry.kind==="product")path=circlePath(cx,cy,rings.center+1.5);
 else if(entry.kind==="leaf"||entry.kind==="track"){
   path=arcPath(cx,cy,rings.leaf[0]-1.5,outer+1.5,entry.angles[0]-.004,entry.angles[1]+.004);
   radialById.get(entry.row.id)?.shape.classList.add("tf-hover");
   entry.shape.classList.add("tf-hover");
 }else path=arcPath(cx,cy,entry.band[0]-1.5,entry.band[1]+1.5,entry.angles[0]-.004,entry.angles[1]+.004);
 ancestors(entry.row).forEach(item=>{const parent=radialById.get(item.id);if(parent&&parent.kind!=="leaf")parent.shape.classList.add("tf-lineage")});
 radialRing.setAttribute("d",path);
 radialRing.classList.add("visible");
}
function showRingBand(key){
 const track=radialGeometry?.rings.tracks.find(item=>item.key===key);
 if(!track)return;
 const{cx,cy}=radialGeometry;
 hideTooltip(true);
 radialRing.setAttribute("d",arcPath(cx,cy,track.band[0]-1.5,track.band[1]+1.5,angleAt(0)-.01,angleAt(tableUnits)+.01));
 radialRing.classList.add("visible");
}
// Why a layer fails, what changed since the previous retained run, and which run the page shows.
const insights=model.insights||{},layerCauses=insights.causes||{},runDelta=insights.delta||{};
let causeFilter="",changesOn=false,focusedId="",tooltipEntry=null,anchorFrame=0;
const causesOf=(id,key)=>(layerCauses[key]||[]).filter(cause=>cause.ids.includes(id));
const deltaOf=key=>(runDelta.layers||{})[key]||{new:[],fixed:[]};
function runLabel(iso){
 const date=new Date(iso);
 return Number.isNaN(date.getTime())?"":new Intl.DateTimeFormat("en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}).format(date);
}
function runAge(iso){
 const hours=(Date.now()-new Date(iso).getTime())/36e5;
 if(!(hours>=0))return"";
 return hours<1?Math.max(1,Math.round(hours*60))+" min ago":hours<48?Math.round(hours)+" h ago":Math.round(hours/24)+" days ago";
}
function whyLine(row){
 const reasons=causesOf(row.id,mode);
 return reasons.length?'<div class="tf-health-why"><b>Why:</b> '+reasons.map(cause=>escapeHtml(cause.label)).join(" · ")+"</div>":"";
}
function deltaBadge(key){
 const change=deltaOf(key);
 if(!runDelta.baseline||!(change.new.length||change.fixed.length))return"";
 return'<span class="tf-health-delta" data-tip="Since the run of '+escapeHtml(runLabel(runDelta.baseline.started_at))+": "+change.new.length+" new failing, "+change.fixed.length+' fixed">'
   +(change.new.length?'<span class="up">▲'+change.new.length+"</span>":"")+(change.fixed.length?'<span class="down">▼'+change.fixed.length+"</span>":"")+"</span>";
}
function renderStamp(){
 const run=insights.run||{};
 if(!run.started_at)return;
 const fresh=run.fresh,stale=fresh?fresh.total-fresh.passed:0;
 stamp.innerHTML="Retained run <b>"+escapeHtml(runLabel(run.started_at))+"</b> ("+runAge(run.started_at)+")"
   +(run.checks?" · "+run.checks+" checks":"")
   +(run.commit?" · commit <code>"+escapeHtml(run.commit)+"</code>":"")
   +(fresh?' · evidence <span class="'+(stale?"failed":"passed")+'">'+(stale?stale+" stale":"all current")+"</span>":"");
}
function renderCauses(){
 const list=layerCauses[mode]||[],name=mode==="overall"?"Overall":layerByKey.get(mode)[1];
 if(!list.length){causesRow.innerHTML='<span class="tf-health-causes-title">'+escapeHtml(name)+'</span><span class="tf-health-causes-none">Nothing fails here.</span>';return}
 causesRow.innerHTML='<span class="tf-health-causes-title" data-tip="One red mark can have several causes.">Why '+escapeHtml(name)+" fails</span>"
   +list.map(cause=>'<button type="button" class="tf-health-cause" data-cause="'+escapeHtml(cause.id)+'" aria-pressed="'+(causeFilter===cause.id)+'" data-tip="'+escapeHtml(cause.hint)+'"><b>'+cause.ids.length+"</b>"+escapeHtml(cause.label)+"</button>").join("")
   +(causeFilter?'<button type="button" class="tf-health-cause-clear" data-cause="">Show all</button>':"")
   +(changesOn&&runDelta.baseline?'<span class="tf-health-changes-key"><i class="new"></i>new failure<i class="fixed"></i>fixed since '+escapeHtml(runLabel(runDelta.baseline.started_at))+"</span>":"");
}
// A cause keeps only its marks lit; Changes outlines new failures and fixes. Both survive redraws.
function applyFocus(){
 const cause=causeFilter&&(layerCauses[mode]||[]).find(item=>item.id===causeFilter),ids=cause?new Set(cause.ids):null;
 const changes=changesOn&&runDelta.baseline;
 [...entries,...radialEntries].forEach(entry=>{
   const leaf=entry.kind==="leaf"||entry.kind==="track",hit=!!ids&&ids.has(entry.row.id);
   entry.shape.classList.toggle("tf-health-dim",!!ids&&leaf&&!hit);
   entry.shape.classList.toggle("tf-health-hit",!!ids&&!leaf&&entry.kind!=="product"&&hit);
   const change=changes&&leaf?deltaOf(entry.layer||(entry.radial?"overall":mode)):null;
   entry.shape.classList.toggle("tf-health-new",!!change&&change.new.includes(entry.row.id));
   entry.shape.classList.toggle("tf-health-fixed",!!change&&change.fixed.includes(entry.row.id));
 });
}
// The view has an address: #layer or #layer:ID. Back from a contract page and shared links return here.
function writeHash(){
 const hash="#"+mode+(focusedId?":"+focusedId:"");
 if(location.hash!==hash)history.replaceState(history.state,"",hash);
}
function focusRow(id){
 const entry=(mode==="overall"?radialById:entryById).get(id);
 if(!entry)return;
 focusedId=id;
 writeHash();
 entry.link.focus();
 // focus() is silent when the link already has focus or the window has none; the hover card listens for the event.
 if(!tooltip.classList.contains("visible"))entry.link.dispatchEvent(new FocusEvent("focus"));
}
function readHash(){
 const[key,id]=decodeURIComponent(location.hash.slice(1)).split(":");
 if(!layerByKey.has(key))return;
 select(key,false);
 if(id)requestAnimationFrame(()=>focusRow(id));
}
// Find: every goal, capability and contract, most failing first; Enter shows it on the current map.
let findIndex=null,findResults=[],findActive=0,findReturn=null;
function findItems(){
 return rows.filter(row=>row.level!=="product").map(row=>{
   const path=ancestors(row).map(item=>item.short||item.label).join(" › ");
   return{row,path,fails:LAYERS.slice(1).filter(layer=>status(row,layer[0])==="failed").length,text:(row.label+" "+(row.short||"")+" "+row.id+" "+path).toLowerCase()};
 });
}
function renderFind(){
 findIndex=findIndex||findItems();
 const words=findInput.value.trim().toLowerCase().split(/\s+/).filter(Boolean),keys=visualOrder();
 findResults=findIndex.filter(item=>words.every(word=>item.text.includes(word))).sort((a,b)=>b.fails-a.fails||a.row.label.localeCompare(b.row.label)).slice(0,80);
 findActive=Math.min(findActive,Math.max(0,findResults.length-1));
 findList.innerHTML=findResults.length?findResults.map((item,index)=>'<div class="tf-health-find-item" role="option" id="tf-health-find-'+index+'" data-index="'+index+'" aria-selected="'+(index===findActive)+'">'
   +'<span class="tf-health-find-marks" aria-hidden="true">'+keys.map((key,position)=>'<i class="'+status(item.row,key)+(position?"":" first")+'" title="'+escapeHtml(layerByKey.get(key)[1])+'"></i>').join("")+"</span>"
   +'<span class="tf-health-find-text"><span class="tf-health-find-name">'+escapeHtml(item.row.label)+'</span><span class="tf-health-find-path">'+escapeHtml(item.path||KIND[item.row.level])+"</span></span>"
   +'<span class="tf-health-find-id">'+escapeHtml(item.row.id)+"</span></div>").join(""):'<div class="tf-health-find-empty">Nothing matches.</div>';
 findInput.setAttribute("aria-activedescendant",findResults.length?"tf-health-find-"+findActive:"");
 findList.querySelector('[aria-selected="true"]')?.scrollIntoView({block:"nearest"});
}
function openFind(){
 findReturn=document.activeElement;
 hideHint();
 findBox.hidden=false;
 findInput.value="";
 findActive=0;
 renderFind();
 findInput.focus();
}
function closeFind(restore){
 if(findBox.hidden)return;
 findBox.hidden=true;
 if(restore)findReturn?.focus?.({preventScroll:true});
}
function pickFind(index){
 const item=findResults[index];
 if(!item)return;
 closeFind(false);
 focusRow(item.row.id);
}
function buildTabs(){
 const order=layerOrder(),left=scroller.scrollLeft;
 tabs.innerHTML='<div class="tf-health-group pinned" role="none" style="flex-grow:1"><div class="tf-health-group-head" aria-hidden="true"></div><div class="tf-health-group-cards" role="none">'+tabHtml(order.first)+"</div></div>"
   +groupHtml("failed",order.failing)+groupHtml("passed",order.passing);
 scroller.scrollLeft=left;
 syncTabs();
 syncBar();
}
function syncTabs(){
 tabs.querySelectorAll("[data-health-mode]").forEach(button=>{
   const active=button.dataset.healthMode===mode;
   button.setAttribute("aria-selected",String(active));
   button.tabIndex=active?0:-1;
 });
}
function select(key,focus){
 const changed=key!==mode;
 if(key!==mode){mode=key;hideTooltip(true);syncTabs();paint(true)}
 if(changed){focusedId="";causeFilter="";renderCauses();applyFocus();writeHash()}
 const tab=document.getElementById("tf-health-tab-"+key);
 if(!tab)return;
 reveal(tab);
 if(focus)tab.focus({preventScroll:true});
}
const motion=()=>window.matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth";
let pinWidth=0,edgeFrame=0,hintTarget=null,hoverHold=null;
function reveal(tab){
 if(pinWidth&&tab.closest(".pinned"))return;
 const view=scroller.getBoundingClientRect(),box=tab.getBoundingClientRect(),room=64;
 const left=box.left-view.left,right=box.right-view.left;
 const delta=left<pinWidth+room?left-pinWidth-room:right>view.width-room?right-view.width+room:0;
 if(delta)scroller.scrollBy({left:delta,behavior:motion()});
}
// Overall is pinned only when the strip scrolls and there is room left for other layers.
function syncBar(){
 const pinned=scroller.scrollWidth>scroller.clientWidth+1&&scroller.clientWidth>=600;
 bar.classList.toggle("tf-health-pin",pinned);
 const first=tabs.querySelector(".tf-health-group.pinned");
 pinWidth=pinned&&first?Math.round(first.getBoundingClientRect().width):0;
 bar.style.setProperty("--tf-pin",pinWidth+"px");
 // Group names stick next to the pinned Overall, or next to the table toggle when Overall scrolls away.
 bar.style.setProperty("--tf-label-left",(pinWidth||Math.round(tableToggle.getBoundingClientRect().width)+10)+"px");
 updateEdges();
}
function edgeNote(counts,side){
 const arrow='<i class="fa-solid fa-chevron-'+side+'" aria-hidden="true"></i>';
 const note=counts.failed?'<span class="tf-health-edge-note failed"><i class="fa-solid fa-circle-xmark" aria-hidden="true"></i>'+counts.failed+"</span>"
   :counts.passed?'<span class="tf-health-edge-note passed"><i class="fa-solid fa-circle-check" aria-hidden="true"></i>'+counts.passed+"</span>":"";
 return side==="left"?arrow+note:note+arrow;
}
function edgeTip(counts,side){
 const where=side==="left"?"to the left":"to the right";
 if(counts.failed)return counts.failed+(counts.failed===1?" failing layer ":" failing layers ")+where;
 return counts.passed?"Only passing layers "+where:"";
}
// Each scroll edge counts the layers it hides, failing first: red until the pass line is in view.
function updateEdges(){
 const view=scroller.getBoundingClientRect(),at=scroller.scrollLeft,max=scroller.scrollWidth-scroller.clientWidth;
 const hidden={left:{failed:0,passed:0},right:{failed:0,passed:0}};
 tabs.querySelectorAll("[data-health-mode]").forEach(tab=>{
   if(pinWidth&&tab.closest(".pinned"))return;
   const box=tab.getBoundingClientRect(),middle=box.left+box.width/2-view.left;
   const side=middle<pinWidth?"left":middle>view.width?"right":"";
   if(side)hidden[side][verdictOf(tab.dataset.healthMode)]++;
 });
 Object.entries(edges).forEach(([side,node])=>{
   const on=side==="left"?at>1:at<max-1,button=node.firstElementChild;
   node.classList.toggle("on",on);
   button.innerHTML=edgeNote(hidden[side],side);
   button.dataset.tip=on?edgeTip(hidden[side],side):"";
 });
}
function showHint(target){
 hintTarget=target;
 hint.textContent=target.dataset.tip;
 hint.setAttribute("aria-hidden","false");
 const box=target.getBoundingClientRect(),size=hint.getBoundingClientRect();
 const left=Math.max(8,Math.min(window.innerWidth-size.width-8,box.left+box.width/2-size.width/2));
 let top=box.top-size.height-8;
 if(top<8)top=box.bottom+8;
 hint.style.left=Math.round(left)+"px";
 hint.style.top=Math.round(top)+"px";
 hint.classList.add("visible");
}
function hideHint(){hintTarget=null;hint.classList.remove("visible");hint.setAttribute("aria-hidden","true")}
// The all-layers table: one row per layer in strip order, one column per contract in tree order.
const CELL=10,FOOT_IDLE="Pick a row to open its map. Each column is one contract, grouped by goal: point at it to compare layers.";
let tableUnits=0;
const tableLeaves=[],tableGroups=[];
function tableColumns(){
 if(tableLeaves.length)return;
 const walk=row=>{
   const start=tableUnits;
   if(row.level==="requirement"||row.level==="treq"){tableLeaves.push({row,x:tableUnits});tableUnits+=CELL}
   (children.get(row.id)||[]).forEach((child,index)=>{if(index&&child.level==="feature")tableUnits+=4;walk(child)});
   if(row.level==="goal"||row.level==="feature")tableGroups.push({row,start,end:tableUnits});
 };
 (children.get(root.id)||[]).forEach((goal,index)=>{if(index)tableUnits+=14;walk(goal)});
}
function stripSvg(key){
 let out="";
 tableLeaves.forEach((leaf,index)=>{out+='<rect data-leaf="'+index+'" x="'+(leaf.x+1)+'" y="2" width="'+(CELL-2)+'" height="12" class="tf-health-tile '+status(leaf.row,key)+'"/>'});
 tableGroups.forEach(group=>{
   if(status(group.row,key)!=="failed")return;
   const goal=group.row.level==="goal";
   out+='<rect x="'+(group.start-(goal?4:2))+'" y="'+(goal?.5:1.5)+'" width="'+(group.end-group.start+(goal?8:4))+'" height="'+(goal?15:13)+'" rx="2" fill="none" class="tf-health-own-failed" vector-effect="non-scaling-stroke"/>';
 });
 return'<svg class="tf-health-row-strip" viewBox="0 0 '+tableUnits+' 16" preserveAspectRatio="none" aria-hidden="true" focusable="false">'+out+"</svg>";
}
function rowHtml(key){
 const label=layerByKey.get(key)[1],applicable=Number(summaryOf(key).applicable||0),verdict=verdictOf(key),failing=failingOf(key),selected=key===mode;
 const name=label+": "+word(verdict)+", "+(failing?failing+" of "+applicable+" fail":"all "+applicable+" pass");
 return'<div class="tf-health-row" role="option" data-health-row="'+key+'" aria-selected="'+selected+'" tabindex="'+(selected?0:-1)+'" aria-label="'+escapeHtml(name)+'">'
   +'<span class="tf-health-row-head"><span class="tf-health-row-name">'+label+'</span><span class="tf-health-verdict '+verdict+'"><i class="fa-solid '+(verdict==="passed"?"fa-circle-check":"fa-circle-xmark")+'" aria-hidden="true"></i><span class="tf-health-row-word"> '+word(verdict)+"</span></span>"
   +'<span class="tf-health-row-count">'+(failing?"<b>"+failing+"</b>/"+applicable:"all "+applicable)+"</span></span>"
   +stripSvg(key)+"</div>";
}
function rowsGroup(kind,keys){
 if(!keys.length)return"";
 const failed=kind==="failed";
 return'<div class="tf-health-rows-group" role="group" aria-label="'+(failed?"Failing":"Passing")+' layers">'
   +'<div class="tf-health-rows-label '+kind+'" aria-hidden="true"><i class="fa-solid '+(failed?"fa-circle-xmark":"fa-circle-check")+'"></i>'+(failed?"Failing":"Passing")+" · "+keys.length+"</div>"
   +keys.map(rowHtml).join("")+"</div>";
}
function resetFoot(){
 tableFoot.textContent=FOOT_IDLE;
 rowsBox.querySelector(".tf-health-band")?.classList.remove("visible");
}
function renderTable(){
 tableColumns();
 const order=layerOrder();
 rowsBox.innerHTML=rowHtml(order.first)+rowsGroup("failed",order.failing)+rowsGroup("passed",order.passing)+'<div class="tf-health-band" aria-hidden="true"></div>';
 resetFoot();
}
function openTable(){
 renderTable();
 hideHint();
 table.hidden=false;
 tableToggle.setAttribute("aria-expanded","true");
 rowsBox.querySelector('[aria-selected="true"]')?.focus({preventScroll:true});
}
function closeTable(returnFocus){
 if(table.hidden)return;
 table.hidden=true;
 tableToggle.setAttribute("aria-expanded","false");
 if(returnFocus)tableToggle.focus({preventScroll:true});
}
// A row opens its layer; a contract cell also puts that contract under the map's ring and hover card.
function pick(key,leaf,pointer){
 hoverHold=pointer?{x:pointer.clientX,y:pointer.clientY}:null;
 closeTable(false);
 select(key,!leaf);
 if(leaf)focusRow(leaf.row.id);
}
function headerHeight(node){
 const kind=node.data.kind;
 if((kind==="goal"||kind==="feature")&&compact.has(node.data.row.id))return pad(node,2);
 return pad(node,1);
}
function computeLayout(){
 d3.treemap().size([width,height]).tile(tile)
   .paddingInner(node=>pad(node,0)).paddingTop(headerHeight)
   .paddingRight(node=>pad(node,2)).paddingBottom(node=>pad(node,2)).paddingLeft(node=>pad(node,2))(hierarchy);
}
function layout(force){
 const rect=wrap.getBoundingClientRect(),w=Math.round(rect.width);
 const h=Math.round(Math.min(880,Math.max(460,window.innerHeight-(rect.top+window.scrollY)-20)));
 if(!w||(!force&&w===width&&h===height))return;
 width=w;height=h;
 svg.setAttribute("viewBox","0 0 "+width+" "+height);
 svg.setAttribute("width",width);
 svg.setAttribute("height",height);
 compact.clear();
 computeLayout();
 const family=getComputedStyle(document.body).fontFamily;
 hierarchy.each(node=>{
   const kind=node.data.kind;
   if(kind!=="goal"&&kind!=="feature")return;
   const room=node.y1-node.y0-pad(node,1)-pad(node,2);
   if(!headerLabel(node,family)||room<(kind==="goal"?40:22))compact.add(node.data.row.id);
 });
 if(compact.size)computeLayout();
 buildTabs();
 draw();
 drawRadial();
}
function scheduleLayout(force){
 pendingForce=pendingForce||force;
 if(frame)return;
 frame=requestAnimationFrame(()=>{frame=0;const next=pendingForce;pendingForce=false;layout(next)});
}
document.addEventListener("keydown",event=>{if(event.key==="Escape"){hideTooltip(true);closeTable(true)}});
tabs.addEventListener("click",event=>{const button=event.target.closest("[data-health-mode]");if(button)select(button.dataset.healthMode,false)});
tabs.addEventListener("keydown",event=>{
 const button=event.target.closest("[data-health-mode]");
 if(!button)return;
 const keys=visualOrder(),index=keys.indexOf(button.dataset.healthMode);
 const next={ArrowRight:index+1,ArrowLeft:index-1,Home:0,End:keys.length-1}[event.key];
 if(next===undefined)return;
 event.preventDefault();
 select(keys[(next+keys.length)%keys.length],true);
});
scroller.addEventListener("scroll",()=>{hideHint();if(!edgeFrame)edgeFrame=requestAnimationFrame(()=>{edgeFrame=0;updateEdges()})},{passive:true});
bar.addEventListener("click",event=>{
 const button=event.target.closest("[data-health-scroll]");
 if(button)scroller.scrollBy({left:Number(button.dataset.healthScroll)*Math.max(180,(scroller.clientWidth-pinWidth)*.8),behavior:motion()});
});
bar.addEventListener("pointerover",event=>{
 const target=event.target.closest("[data-tip]");
 if(target&&target.dataset.tip&&!table.contains(target)){if(target!==hintTarget)showHint(target)}
 else if(hintTarget)hideHint();
});
bar.addEventListener("pointerleave",hideHint);
window.addEventListener("scroll",hideHint,{passive:true});
tableToggle.addEventListener("click",()=>{if(table.hidden)openTable();else closeTable(false)});
table.querySelector(".tf-health-table-close").addEventListener("click",()=>closeTable(true));
table.addEventListener("focusout",event=>{if(event.relatedTarget&&!table.contains(event.relatedTarget)&&event.relatedTarget!==tableToggle)closeTable(false)});
document.addEventListener("pointerdown",event=>{if(!table.hidden&&!table.contains(event.target)&&!tableToggle.contains(event.target))closeTable(false)});
rowsBox.addEventListener("click",event=>{
 const row=event.target.closest("[data-health-row]");
 if(!row)return;
 const cell=event.target.closest("[data-leaf]");
 pick(row.dataset.healthRow,cell?tableLeaves[Number(cell.dataset.leaf)]:null,event.detail?event:null);
});
rowsBox.addEventListener("keydown",event=>{
 const row=event.target.closest("[data-health-row]");
 if(!row)return;
 if(event.key==="Enter"||event.key===" "){event.preventDefault();pick(row.dataset.healthRow,null);return}
 const list=[...rowsBox.querySelectorAll("[data-health-row]")],index=list.indexOf(row);
 const next={ArrowDown:index+1,ArrowUp:index-1,Home:0,End:list.length-1}[event.key];
 if(next===undefined)return;
 event.preventDefault();
 const target=list[Math.max(0,Math.min(list.length-1,next))];
 list.forEach(item=>{item.tabIndex=item===target?0:-1});
 target.focus();
});
rowsBox.addEventListener("pointermove",event=>{
 const strip=rowsBox.querySelector(".tf-health-row-strip"),band=rowsBox.querySelector(".tf-health-band");
 if(!strip||!band)return;
 const box=strip.getBoundingClientRect(),outer=rowsBox.getBoundingClientRect(),unit=(event.clientX-box.left)/box.width*tableUnits;
 const leaf=event.clientX>=box.left&&event.clientX<=box.right?tableLeaves.find(item=>unit>=item.x-1&&unit<item.x+CELL+1):null;
 if(!leaf)return resetFoot();
 const scale=box.width/tableUnits;
 band.style.left=(box.left-outer.left+leaf.x*scale-1)+"px";
 band.style.width=(CELL*scale+2)+"px";
 band.classList.add("visible");
 tableFoot.innerHTML="<b>"+escapeHtml(leaf.row.short||leaf.row.label)+"</b> · "+escapeHtml(leaf.row.id)+": "+visualOrder().map(key=>{
   const value=status(leaf.row,key);
   return'<span class="tf-health-mark '+value+'">'+escapeHtml(layerByKey.get(key)[1])+" "+(value==="failed"?"✕":value==="passed"?"✓":"–")+"</span>";
 }).join(" · ");
});
rowsBox.addEventListener("pointerleave",resetFoot);
new ResizeObserver(()=>syncBar()).observe(scroller);
wrap.addEventListener("click",event=>{
 const link=event.target.closest("a"),entry=link&&[...entries,...radialEntries].find(item=>item.link===link);
 if(entry&&entry.row.level!=="product"){focusedId=entry.row.id;writeHash()}
},true);
window.addEventListener("hashchange",readHash);
window.addEventListener("scroll",()=>{
 if(anchorFrame||!tooltipEntry)return;
 anchorFrame=requestAnimationFrame(()=>{
   anchorFrame=0;
   if(!tooltipEntry||!tooltip.classList.contains("visible"))return;
   const rect=tooltipEntry.shape.getBoundingClientRect();
   if(rect.bottom<0||rect.top>window.innerHeight)hideTooltip(true);else placeTooltip(rect);
 });
},{passive:true});
causesRow.addEventListener("click",event=>{
 const button=event.target.closest("[data-cause]");
 if(!button)return;
 causeFilter=causeFilter===button.dataset.cause?"":button.dataset.cause;
 renderCauses();
 applyFocus();
});
[toolsRow,causesRow].forEach(node=>{
 node.addEventListener("pointerover",event=>{
   const target=event.target.closest("[data-tip]");
   if(target&&target.dataset.tip){if(target!==hintTarget)showHint(target)}
   else if(hintTarget)hideHint();
 });
 node.addEventListener("pointerleave",hideHint);
});
document.getElementById("tf-health-find-open").addEventListener("click",openFind);
findInput.addEventListener("input",()=>{findActive=0;renderFind()});
findInput.addEventListener("keydown",event=>{
 if(event.key==="ArrowDown"||event.key==="ArrowUp"){
   event.preventDefault();
   findActive=Math.max(0,Math.min(findResults.length-1,findActive+(event.key==="ArrowDown"?1:-1)));
   renderFind();
 }else if(event.key==="Enter"){event.preventDefault();pickFind(findActive)}
 else if(event.key==="Escape"){event.preventDefault();event.stopPropagation();closeFind(true)}
});
findList.addEventListener("click",event=>{const item=event.target.closest("[data-index]");if(item)pickFind(Number(item.dataset.index))});
findBox.addEventListener("pointerdown",event=>{if(event.target===findBox)closeFind(true)});
if(runDelta.baseline)changesButton.dataset.tip="Outline what changed since the run of "+runLabel(runDelta.baseline.started_at)+".";
else{changesButton.setAttribute("aria-disabled","true");changesButton.dataset.tip="No earlier retained run to compare with yet."}
changesButton.addEventListener("click",()=>{
 if(!runDelta.baseline)return;
 changesOn=!changesOn;
 changesButton.setAttribute("aria-pressed",String(changesOn));
 renderCauses();
 applyFocus();
});
copyButton.addEventListener("click",()=>{
 writeHash();
 const label=copyButton.querySelector("span");
 navigator.clipboard?.writeText(location.href).then(()=>{label.textContent="Copied";setTimeout(()=>{label.textContent="Copy link"},1400)},()=>{});
});
// Keys: / find, 1–9 layers in strip order, T the all-layers table.
document.addEventListener("keydown",event=>{
 if(event.defaultPrevented||event.metaKey||event.ctrlKey||event.altKey||!findBox.hidden)return;
 if(event.target.closest?.("input,textarea,select,[contenteditable]"))return;
 if(event.key==="/"){event.preventDefault();openFind();return}
 if(/^[1-9]$/.test(event.key)){const key=visualOrder()[Number(event.key)-1];if(key){event.preventDefault();select(key,true)}return}
 if(event.key==="t"||event.key==="T"){event.preventDefault();tableToggle.click()}
});
radial.addEventListener("pointerover",event=>{const name=event.target.closest("[data-health-ring]");if(name){showRingBand(name.dataset.healthRing);showHint(name)}});
radial.addEventListener("pointerout",event=>{const name=event.target.closest("[data-health-ring]");if(name&&!name.contains(event.relatedTarget)){radialRing?.classList.remove("visible");hideHint()}});
radial.addEventListener("click",event=>{const name=event.target.closest("[data-health-ring]");if(name)select(name.dataset.healthRing,false)});
radial.addEventListener("keydown",event=>{const name=event.target.closest("[data-health-ring]");if(name&&(event.key==="Enter"||event.key===" ")){event.preventDefault();select(name.dataset.healthRing,true)}});
window.addEventListener("resize",()=>scheduleLayout(false));
new ResizeObserver(()=>scheduleLayout(false)).observe(wrap);
layout(true);
renderStamp();
renderCauses();
readHash();
document.fonts?.ready?.then(()=>scheduleLayout(true));
})();
</script>
</section>"""

DEPTH_MAP_TEMPLATE = r"""<section id="verification-depth-map">
<h1>Verification Depth Map<a class="headerlink" href="#verification-depth-map" title="Link to this heading">#</a></h1>
<p class="tf-map-intro">One specification treemap, three selectable projections: standard ISTQB <strong>Test Level</strong>, observed <strong>Boundary Reality</strong>, and mutation-based <strong>Test Strength</strong>. Boundary Reality is an exposure mode, not a universal weak→strong score. <strong>Representation Fidelity</strong> now qualifies each concrete evidence path together with producer/M&amp;S credibility rather than acting as a separate map axis.</p>
<style id="tf-depth-map-style">
.tf-map-intro{max-width:82rem;margin:.15rem 0 .75rem;color:var(--pst-color-text-muted)}
.tf-depth-status{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.55rem;margin:.6rem 0 .8rem}.tf-depth-dimension{border:1px solid var(--pst-color-border);border-radius:.55rem;background:var(--pst-color-surface);color:inherit;text-align:left;padding:.58rem .68rem;cursor:pointer;min-width:0}.tf-depth-dimension.active{outline:2px solid var(--pst-color-primary);outline-offset:-2px}.tf-depth-dimension>span{display:flex;justify-content:space-between;gap:.35rem;font-size:.76rem;font-weight:700}.tf-depth-direction{font-style:normal;color:var(--pst-color-text-muted);font-weight:500}.tf-depth-dimension>strong{display:block;margin:.12rem 0 .38rem;font-size:1rem}.tf-depth-rail{display:flex;height:1.28rem;border-radius:.3rem;overflow:hidden;background:var(--pst-color-border)}.tf-depth-rail span{display:flex;align-items:center;justify-content:center;min-width:8px;color:#fff;font-size:.62rem;font-weight:700;overflow:hidden}.tf-depth-note{display:block;color:var(--pst-color-text-muted);font-size:.68rem;margin-top:.32rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ternforge-verification-depth-map-shell{border:1px solid var(--pst-color-border);border-radius:.6rem;background:var(--pst-color-surface);padding:.35rem;min-height:500px}.ternforge-verification-depth-map{width:100%;min-height:500px}.tf-depth-credibility{margin-top:.65rem;border:1px solid var(--pst-color-border);border-radius:.5rem;padding:.5rem .7rem;background:var(--pst-color-surface)}.tf-depth-credibility summary{cursor:pointer;font-weight:700}.tf-depth-credibility p{margin:.45rem 0 .1rem;color:var(--pst-color-text-muted)}
@media(max-width:900px){.tf-depth-status{grid-template-columns:1fr}.ternforge-verification-depth-map-shell,.ternforge-verification-depth-map{min-height:430px}}
</style>
<div class="tf-depth-status">
<button class="tf-depth-dimension active" type="button" data-depth-mode="reach"><span>Test Level <em class="tf-depth-direction">component → system</em></span><strong id="tf-reach-headline">Loading</strong><div class="tf-depth-rail" id="tf-reach-rail"></div><small class="tf-depth-note">Observed test-object reach</small></button>
<button class="tf-depth-dimension" type="button" data-depth-mode="boundary"><span>Boundary Reality <em class="tf-depth-direction">local → live</em></span><strong id="tf-boundary-headline">Loading</strong><div class="tf-depth-rail" id="tf-boundary-rail"></div><small class="tf-depth-note">Exposure mode; Assurance Target decides sufficiency</small></button>
<button class="tf-depth-dimension" type="button" data-depth-mode="strength"><span>Test Strength <em class="tf-depth-direction">measured mutation sensitivity</em></span><strong id="tf-strength-headline">Loading</strong><div class="tf-depth-rail" id="tf-strength-rail"></div><small class="tf-depth-note">Current snapshot · click measured contract → changes / history</small></button>
</div>
<div class="ternforge-verification-depth-map-shell"><div id="ternforge-verification-depth-map" class="ternforge-verification-depth-map"></div></div>
<details class="tf-depth-credibility"><summary>Evidence Producer Credibility / Representation qualifiers</summary><p><strong>Same-path representation qualifiers</strong> remain attached to each concrete Boundary Reality observation. Producer qualification and M&amp;S validation are orthogonal trust gates; inspect <a href="evidence-producers.html">Evidence Producers</a> for the producer-level proof.</p></details>
<!-- DEPTH-P30-BOUNDARY-MODEL -->
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script>
(()=>{
const model=__MODEL__;
const REACH={none:{rank:-1,label:"No evidence",short:"—",color:"#667085"},component:{rank:0,label:"Component",short:"Comp",color:"#d49a32"},component_integration:{rank:1,label:"Component integration",short:"C.Int",color:"#3b82f6"},system:{rank:2,label:"System",short:"Sys",color:"#14b8a6"},system_integration:{rank:3,label:"System integration",short:"S.Int",color:"#2f8f5b"}};
const BOUNDARY={no_evidence:{rank:-1,label:"No evidence",short:"—",color:"#667085"},none:{rank:0,label:"Local only",short:"Local",color:"#d49a32"},substitute:{rank:1,label:"Substitute",short:"Sub",color:"#3b82f6"},replay:{rank:2,label:"Replay",short:"Replay",color:"#14b8a6"},direct:{rank:3,label:"Direct live",short:"Live",color:"#2f8f5b"}};
const STRENGTH={na:{rank:-1,label:"N/A / unmeasured",short:"N/A",color:"#667085"},low:{rank:0,label:"Low <60%",short:"Low",color:"#c2413b"},moderate:{rank:1,label:"Moderate 60–79.9%",short:"Mod",color:"#d49a32"},high:{rank:2,label:"High ≥80%",short:"High",color:"#2f8f5b"}};
const REACH_ORDER=["none","component","component_integration","system","system_integration"];
const BOUNDARY_ORDER=["no_evidence","none","substitute","replay","direct"];
const STRENGTH_ORDER=["na","low","moderate","high"];
const escapeHtml=value=>String(value??"").replace(/[&<>\"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;","'":"&#39;"}[ch]));
const root=model.root, rows=[{...root,kind:"Overview",reach:"none",boundary:"no_evidence",qualifiers:[],strength:{state:"na"},persistent_label:true},...model.items];
const element=document.getElementById("ternforge-verification-depth-map");let mode="reach";
function dict(){return mode==="reach"?REACH:mode==="boundary"?BOUNDARY:STRENGTH}
function order(){return mode==="reach"?REACH_ORDER:mode==="boundary"?BOUNDARY_ORDER:STRENGTH_ORDER}
function key(row){return mode==="reach"?row.reach:mode==="boundary"?row.boundary:row.strength?.state||"na"}
function rail(id,dist,definitions,keys){const el=document.getElementById(id);const total=Object.values(dist).reduce((a,b)=>a+Number(b||0),0)||1;el.innerHTML=keys.map(k=>{const count=Number(dist[k]||0);const width=Math.max(8,100*count/total);return `<span style="width:${width}%;background:${definitions[k].color}" title="${escapeHtml(definitions[k].label)} · ${count} contracts">${count?definitions[k].short+" "+count:""}</span>`}).join("")}
function strongest(dist,definitions,keys){for(let i=keys.length-1;i>=0;i--){if(Number(dist[keys[i]]||0)>0)return definitions[keys[i]].label}return "No evidence"}
rail("tf-reach-rail",model.summary.reach,REACH,REACH_ORDER);rail("tf-boundary-rail",model.summary.boundary,BOUNDARY,BOUNDARY_ORDER);rail("tf-strength-rail",model.summary.strength,STRENGTH,STRENGTH_ORDER);
document.getElementById("tf-reach-headline").textContent="Max · "+strongest(model.summary.reach,REACH,REACH_ORDER);document.getElementById("tf-boundary-headline").textContent="Max observed · "+strongest(model.summary.boundary,BOUNDARY,BOUNDARY_ORDER);document.getElementById("tf-strength-headline").textContent=model.summary.measured+" / "+model.summary.contracts+" measured";
function hover(row){if(row.id===root.id)return `<b>${escapeHtml(row.label)}</b><br>Product / System overview`;
 if(mode==="reach")return `<b>${escapeHtml(row.label)}</b><br>${escapeHtml(row.kind)} · <b>Test Level</b> · ${escapeHtml(REACH[row.reach]?.label||row.reach)}<br><b>Click → Traceability</b>`;
 if(mode==="boundary"){const qualifiers=(row.qualifiers||[]).map(q=>`${BOUNDARY[q.boundary]?.label||q.boundary} · ${String(q.representation||"").replaceAll("_"," ")} · ${q.tests} test${q.tests===1?"":"s"}`).join("<br>");return `<b>${escapeHtml(row.label)}</b><br>${escapeHtml(row.kind)} · <b>Boundary Reality</b> · ${escapeHtml(BOUNDARY[row.boundary]?.label||row.boundary)}<br><span>Exposure mode only · the Assurance Target decides whether live interaction is required.</span>${qualifiers?"<br><b>Same-path representation qualifiers</b><br>"+escapeHtml(qualifiers).replaceAll("&lt;br&gt;","<br>"):""}<br><b>Click → Traceability</b>`}
 const fact=row.strength||{};if(fact.state==="na")return `<b>${escapeHtml(row.label)}</b><br>${escapeHtml(row.kind)} · <b>Test Strength</b> · N/A / unmeasured`;
 const delta=fact.delta===null||fact.delta===undefined?"Δ n/a":`Δ ${Number(fact.delta)>=0?"+":""}${Number(fact.delta).toFixed(1)} pp`;const missed=fact.example?`<br><b>Missed example</b> · ${escapeHtml(fact.example)}`:"";return `<b>${escapeHtml(row.label)}</b><br>${escapeHtml(row.kind)} · <b>Test Strength</b> · ${Number(fact.score).toFixed(1)}% · ${escapeHtml(STRENGTH[fact.state].label)}<br>${fact.killed} killed · ${fact.survived} survived<br><b>${fact.fresh===false?"STALE":"Fresh"}</b> · New ${fact.new} · Debt ${fact.debt} · ${delta}${missed}<br><b>Click → changes / history</b>`}
function target(row){if(row.id===root.id)return null;if(mode==="strength"){return row.strength?.state!=="na"?"mutation-analysis.html#mutation-"+row.id.toLowerCase():null}return "traceability-reader.html#review-"+row.id}
function render(){const definitions=dict();const ids=rows.map(r=>r.id),labels=rows.map(r=>r.label),parents=rows.map(r=>r.id===root.id?"":r.parent),values=rows.map(r=>r.value),colors=rows.map(r=>definitions[key(r)]?.color||"#667085"),text=rows.map(r=>r.id===root.id||r.persistent_label?r.label:"");const custom=rows.map(r=>[hover(r),target(r)]);const data=[{type:"treemap",ids,labels,parents,values,branchvalues:"total",text,textinfo:"text",textfont:{size:14},marker:{colors,line:{width:2,color:"rgba(255,255,255,.72)"}},customdata:custom,hovertemplate:"%{customdata[0]}<extra></extra>",pathbar:{visible:false},sort:false}];const layout={margin:{t:8,l:8,r:8,b:8},paper_bgcolor:"rgba(0,0,0,0)",plot_bgcolor:"rgba(0,0,0,0)",font:{family:"system-ui,-apple-system,BlinkMacSystemFont,sans-serif",color:getComputedStyle(document.body).color},uirevision:"ternforge-verification-depth-map-"+mode};const config={responsive:true,displayModeBar:false,displaylogo:false};element.style.height=Math.max(430,window.innerHeight-element.getBoundingClientRect().top-20)+"px";Plotly.react(element,data,layout,config).then(()=>{element.removeAllListeners?.("plotly_treemapclick");element.on("plotly_treemapclick",event=>{const href=event?.points?.[0]?.customdata?.[1];if(href)window.location.href=href;return false})})}
document.querySelectorAll(".tf-depth-dimension").forEach(button=>button.addEventListener("click",()=>{mode=button.dataset.depthMode;document.querySelectorAll(".tf-depth-dimension").forEach(node=>node.classList.toggle("active",node===button));render()}));window.addEventListener("resize",()=>{element.style.height=Math.max(430,window.innerHeight-element.getBoundingClientRect().top-20)+"px";Plotly.Plots.resize(element)});if(typeof Plotly!=="undefined")render();else document.querySelector('script[src*="plotly"]')?.addEventListener("load",render,{once:true});
})();
</script>
</section>"""


def health_map_article(model_json: str, d3_hierarchy: str) -> str:
    return HEALTH_MAP_TEMPLATE.replace("__D3_HIERARCHY__", d3_hierarchy).replace("__MODEL__", model_json)


def depth_map_article(model_json: str) -> str:
    return DEPTH_MAP_TEMPLATE.replace("__MODEL__", model_json)
