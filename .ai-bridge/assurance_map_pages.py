"""Markup, styles and scripts of the Verification Health Map and Depth Map pages.

Presentation only: the builder computes every fact and passes it in as a JSON payload. The
file stays outside the evidence-producer qualification fingerprint on purpose, because no
qualification control exercises page rendering; the structural gate checks the rendered pages.

Both maps are one page: the same section, the same markup (tools line, layer strip with its All
layers table, side panel, rings and map views, contracts table, hover card and Find) and one shared
script that runs the map. Each page adds only its styles and a script that describes what it alone
knows: the Health Map judges its layers (failing or passing), the Depth Map measures them.
"""

MAP_SHARED_CSS = r"""/* Shared by the Health and Depth maps: the tools line, hints, the layer strip, both views, the side panel, the
   table, the hover card and Find. Each page adds only its palette and what it judges or measures: the tone of a
   group, the colour of a mark, the words of a status. */
#verification-health-map,#verification-depth-map{--tf-map-ease:cubic-bezier(.2,0,0,1);--tf-map-fast:120ms;--tf-map-medium:180ms;--tf-map-radius:10px;--tf-map-line:color-mix(in srgb,var(--pst-color-text-base) 13%,transparent);--tf-map-line-strong:color-mix(in srgb,var(--pst-color-text-base) 28%,transparent);--tf-map-lineage:color-mix(in srgb,var(--pst-color-text-base) 40%,transparent);--tf-map-selected:color-mix(in srgb,var(--pst-color-text-base) 55%,transparent);--tf-map-ring:color-mix(in srgb,var(--pst-color-text-base) 78%,transparent);--tf-map-goal:color-mix(in srgb,var(--pst-color-text-base) 4.5%,var(--pst-color-background));--tf-map-feature:var(--pst-color-background);--tf-map-radial-goal:color-mix(in srgb,var(--pst-color-text-base) 12%,var(--pst-color-background));--tf-map-radial-feature:color-mix(in srgb,var(--pst-color-text-base) 7%,var(--pst-color-background));--tf-map-raised:color-mix(in srgb,var(--pst-color-text-base) 8%,var(--pst-color-background));--tf-map-up:var(--tf-map-ring);--tf-map-down:var(--tf-map-ring)}
html[data-theme=dark] #verification-health-map,html[data-theme=dark] #verification-depth-map{--tf-map-ring:color-mix(in srgb,var(--pst-color-text-base) 92%,transparent);--tf-map-goal:color-mix(in srgb,var(--pst-color-text-base) 5%,var(--pst-color-background));--tf-map-feature:color-mix(in srgb,var(--pst-color-text-base) 10%,var(--pst-color-background));--tf-map-radial-goal:color-mix(in srgb,var(--pst-color-text-base) 17%,var(--pst-color-background));--tf-map-radial-feature:color-mix(in srgb,var(--pst-color-text-base) 11%,var(--pst-color-background));--tf-map-raised:color-mix(in srgb,var(--pst-color-text-base) 10%,var(--pst-color-background))}
.tf-sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.tf-map-tools{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.35rem 1rem;margin:-.2rem 0 .25rem;font-size:.74rem;color:var(--pst-color-text-muted)}
.tf-map-lead{display:flex;align-items:center;gap:.4rem;flex:1 1 20rem;min-width:0;height:28px;white-space:nowrap}
.tf-map-stamp{min-width:0;overflow:hidden;text-overflow:ellipsis}
.tf-map-stamp b{font-weight:650;color:var(--pst-color-text-base)}
.tf-map-stamp code{padding:0 .3rem;border:0;border-radius:4px;background:var(--tf-map-goal);color:inherit;font-size:.7rem}
.tf-map-stamp .passed,.tf-map-stamp .failed{font-weight:650;color:var(--pst-color-text-base)}
.tf-map-actions{display:inline-flex;flex:0 1 auto;flex-wrap:wrap;justify-content:flex-end;gap:.35rem;margin-left:auto}
.tf-map-action{display:inline-flex;align-items:center;gap:.4rem;height:26px;padding:0 .6rem;border:1px solid var(--tf-map-line);border-radius:7px;background:var(--pst-color-background);color:var(--pst-color-text-base);font:inherit;font-size:.74rem;font-weight:600;cursor:pointer;transition:border-color var(--tf-map-medium) var(--tf-map-ease),background-color var(--tf-map-medium) var(--tf-map-ease)}
.tf-map-action:hover{border-color:var(--tf-map-line-strong)}
.tf-map-action[aria-pressed=true],.tf-map-action[aria-expanded=true]{border-color:var(--tf-map-selected);background:var(--tf-map-raised)}
.tf-map-action[aria-disabled=true]{color:var(--pst-color-text-muted);cursor:default}
.tf-map-action[aria-disabled=true]:hover{border-color:var(--tf-map-line)}
.tf-map-action:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:2px}
.tf-map-action i{font-size:.72rem;color:var(--pst-color-text-muted)}
.tf-map-action kbd{padding:0 .3rem;border:1px solid var(--tf-map-line-strong);border-radius:4px;background:none;box-shadow:none;color:var(--pst-color-text-muted);font:inherit;font-size:.66rem}
.tf-map-help{display:inline-grid;place-items:center;flex:0 0 auto;width:1rem;height:1rem;border:1px solid var(--tf-map-line-strong);border-radius:50%;font-size:.64rem;font-weight:700;color:var(--pst-color-text-muted);cursor:help}
.tf-map-hint{position:fixed;z-index:1250;max-width:17rem;padding:.4rem .55rem;border:1px solid var(--tf-map-line-strong);border-radius:.45rem;background:var(--pst-color-surface);color:var(--pst-color-text-base);font-size:.72rem;font-weight:500;line-height:1.35;box-shadow:0 6px 18px rgba(0,0,0,.16);opacity:0;visibility:hidden;transform:translateY(3px);transition:opacity var(--tf-map-fast) var(--tf-map-ease),transform var(--tf-map-fast) var(--tf-map-ease),visibility var(--tf-map-fast) linear;pointer-events:none}
.tf-map-hint.visible{opacity:1;visibility:visible;transform:none}
.tf-map-layerbar{position:relative;margin:.6rem 0 .55rem}
.tf-map-scroller{padding:3px 0;overflow-x:auto;overflow-y:hidden;overscroll-behavior-x:contain;scrollbar-width:none}
.tf-map-scroller::-webkit-scrollbar{display:none}
.tf-map-layers{position:relative;display:flex;align-items:stretch;gap:8px;width:max-content;min-width:100%}
.tf-map-group{position:relative;display:flex;flex:1 0 auto;flex-direction:column;gap:5px;min-width:0}
.tf-map-group-cards{display:flex;flex:1 1 auto;gap:8px}
.tf-map-group-cards>.tf-map-tab{flex:1 0 206px}
.tf-map-group-head{display:flex;align-items:center;height:20px;min-width:0;font-size:.64rem;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-map-group-head::after{content:"";flex:1 1 auto;height:1px;background:currentColor;opacity:.38}
.tf-map-group.pinned .tf-map-group-head::after{content:none}
.tf-map-group-label{position:sticky;left:var(--tf-label-left,0px);z-index:1;display:inline-flex;align-items:center;gap:.35rem;padding-right:.5rem;background:var(--pst-color-background);white-space:nowrap}
.tf-map-group:not(.pinned)+.tf-map-group{margin-left:12px}
.tf-map-group:not(.pinned)+.tf-map-group::before{content:"";position:absolute;top:0;bottom:2px;left:-11px;width:1px;background:linear-gradient(transparent,var(--tf-map-line-strong) 16%,var(--tf-map-line-strong) 84%,transparent)}
.tf-map-pin .tf-map-group.pinned{position:sticky;left:0;z-index:3;margin-right:-8px;padding-right:8px;background:var(--pst-color-background)}
.tf-map-edge{position:absolute;top:28px;bottom:3px;z-index:4;display:flex;align-items:center;width:72px;opacity:0;visibility:hidden;pointer-events:none;transition:opacity var(--tf-map-medium) var(--tf-map-ease),visibility var(--tf-map-medium) linear}
.tf-map-edge.left{left:var(--tf-pin,0px);justify-content:flex-start;background:linear-gradient(90deg,var(--pst-color-background) 38%,transparent)}
.tf-map-edge.right{right:0;justify-content:flex-end;background:linear-gradient(270deg,var(--pst-color-background) 38%,transparent)}
.tf-map-edge.on{opacity:1;visibility:visible}
.tf-map-edge button{pointer-events:auto;display:inline-flex;align-items:center;gap:.4rem;height:26px;padding:0 .55rem;border:1px solid var(--tf-map-line-strong);border-radius:999px;background:var(--tf-map-raised);color:var(--pst-color-text-muted);font:inherit;font-size:.72rem;font-weight:700;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.14);transition:border-color var(--tf-map-fast) var(--tf-map-ease),color var(--tf-map-fast) var(--tf-map-ease)}
.tf-map-edge button:hover{border-color:var(--tf-map-selected);color:var(--pst-color-text-base)}
.tf-map-edge-note{display:inline-flex;align-items:center;gap:.25rem}
.tf-map-table-toggle{position:absolute;top:3px;left:0;z-index:5;display:inline-flex;align-items:center;gap:.4rem;height:20px;padding:0 .45rem 0 .5rem;border:1px solid var(--tf-map-line);border-radius:6px;background:var(--pst-color-background);box-shadow:8px 0 0 var(--pst-color-background);color:var(--pst-color-text-muted);font:inherit;font-size:.68rem;font-weight:650;white-space:nowrap;cursor:pointer;transition:border-color var(--tf-map-medium) var(--tf-map-ease),color var(--tf-map-medium) var(--tf-map-ease)}
.tf-map-table-toggle:hover{border-color:var(--tf-map-line-strong);color:var(--pst-color-text-base)}
.tf-map-table-toggle[aria-expanded=true]{border-color:var(--tf-map-selected);background:var(--tf-map-raised);color:var(--pst-color-text-base)}
.tf-map-table-toggle:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:2px}
.tf-map-chevron{font-size:.6rem;transition:transform var(--tf-map-medium) var(--tf-map-ease)}
.tf-map-table-toggle[aria-expanded=true] .tf-map-chevron{transform:rotate(180deg)}
.tf-map-tab{display:grid;grid-template-columns:minmax(0,1fr) auto;grid-template-rows:auto auto auto;column-gap:.5rem;align-items:center;min-width:0;padding:.5rem .45rem .5rem .7rem;border:1px solid var(--tf-map-line);border-radius:var(--tf-map-radius);background:var(--tf-map-goal);color:inherit;font:inherit;text-align:left;cursor:pointer;transition:border-color var(--tf-map-medium) var(--tf-map-ease),background-color var(--tf-map-medium) var(--tf-map-ease)}
.tf-map-tab:hover{border-color:var(--tf-map-line-strong)}
.tf-map-tab[aria-selected=true]{border-color:var(--tf-map-selected);background:var(--tf-map-raised)}
.tf-map-tab:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:-2px}
.tf-map-tab-title{min-width:0;font-size:.78rem;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-map-tab-status{display:flex;align-items:center;gap:.4rem;min-width:0;font-size:.78rem;white-space:nowrap}
.tf-map-tab-status b{font-weight:750}
.tf-map-count{display:flex;align-items:center;min-width:0;font-size:.72rem;color:var(--pst-color-text-muted);white-space:nowrap}
.tf-map-count-text{min-width:0;overflow:hidden;text-overflow:ellipsis}
.tf-map-count b{color:var(--pst-color-text-base);font-weight:700}
.tf-map-thumb{grid-column:2;grid-row:1/span 3;display:block;width:76px;height:auto}
.tf-map-thumb.radial{width:54px;height:54px;justify-self:center}
.tf-map-delta{display:inline-flex;flex:none;gap:.3rem;margin-left:.4rem;font-weight:750}
.tf-map-delta .up{color:var(--tf-map-up,var(--pst-color-text-base))}.tf-map-delta .down{color:var(--tf-map-down,var(--pst-color-text-muted))}
.tf-map-table{position:absolute;top:calc(100% + 6px);left:0;right:0;z-index:40;display:grid;gap:.55rem;max-height:min(72vh,640px);overflow:auto;padding:.7rem .8rem .65rem;border:1px solid var(--tf-map-line-strong);border-radius:var(--tf-map-radius);background:color-mix(in srgb,var(--pst-color-surface) 97%,var(--pst-color-text-base) 3%);box-shadow:0 18px 44px rgba(0,0,0,.22),0 2px 6px rgba(0,0,0,.08);container-type:inline-size;animation:tf-map-drop var(--tf-map-medium) var(--tf-map-ease) both}
.tf-map-table[hidden]{display:none}
@keyframes tf-map-drop{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.tf-map-table-head{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem 1rem}
.tf-map-table-title{font-size:.8rem;font-weight:700}
.tf-map-table-legend{display:flex;flex-wrap:wrap;align-items:center;gap:.25rem .9rem;font-size:.7rem;color:var(--pst-color-text-muted)}
.tf-map-table-legend>span{display:inline-flex;align-items:center;gap:.35rem}
.tf-map-table-close{display:inline-grid;place-items:center;width:24px;height:24px;margin-left:auto;padding:0;border:1px solid transparent;border-radius:6px;background:none;color:var(--pst-color-text-muted);font:inherit;font-size:1rem;line-height:1;cursor:pointer}
.tf-map-table-close:hover{border-color:var(--tf-map-line-strong);color:var(--pst-color-text-base)}
.tf-map-table-close:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:1px}
.tf-map-rows{position:relative;display:grid;gap:2px}
.tf-map-rows-group{display:grid;gap:2px}
.tf-map-rows-label{display:flex;align-items:center;gap:.35rem;margin:.5rem 0 .15rem;padding:0 8px;font-size:.64rem;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-map-rows-label::after{content:"";flex:1 1 auto;height:1px;background:currentColor;opacity:.38}
.tf-map-row{display:grid;grid-template-columns:var(--tf-row-head,250px) minmax(0,1fr);align-items:center;column-gap:14px;min-width:0;padding:4px 8px;border:1px solid transparent;border-radius:8px;outline:none;cursor:pointer;transition:border-color var(--tf-map-fast) var(--tf-map-ease),background-color var(--tf-map-fast) var(--tf-map-ease)}
.tf-map-row:hover{border-color:var(--tf-map-line);background:var(--tf-map-goal)}
.tf-map-row[aria-selected=true]{border-color:var(--tf-map-selected);background:var(--tf-map-raised)}
.tf-map-row:focus-visible{box-shadow:0 0 0 2px var(--tf-map-ring)}
.tf-map-row-head{display:grid;grid-template-columns:minmax(0,1fr) auto 3.6rem;align-items:center;column-gap:.55rem;min-width:0;font-size:.76rem}
.tf-map-row-name{min-width:0;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-map-row-head>:nth-child(2){font-size:.72rem;white-space:nowrap}
.tf-map-row-count{font-size:.7rem;font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap;color:var(--pst-color-text-muted)}
.tf-map-row-count b{color:var(--pst-color-text-base);font-weight:700}
.tf-map-row-strip{display:block;width:100%;height:16px}
.tf-map-band{position:absolute;top:0;bottom:0;border-radius:3px;background:color-mix(in srgb,var(--tf-map-ring) 14%,transparent);box-shadow:0 0 0 1px color-mix(in srgb,var(--tf-map-ring) 65%,transparent);opacity:0;pointer-events:none;transition:opacity var(--tf-map-fast) var(--tf-map-ease)}
.tf-map-band.visible{opacity:1}
.tf-map-table-foot{min-height:2.7em;font-size:.72rem;line-height:1.35;color:var(--pst-color-text-muted)}
.tf-map-table-foot b{font-weight:650;color:var(--pst-color-text-base)}
.tf-map-mark{white-space:nowrap}
@container (max-width:760px){.tf-map-row{--tf-row-head:176px}.tf-map-row-word{display:none}}
@container (max-width:600px){.tf-map-table-legend{order:3;flex-basis:100%}}
@container (max-width:480px){.tf-map-row{--tf-row-head:118px}.tf-map-row-count{display:none}.tf-map-row-head{grid-template-columns:minmax(0,1fr) auto}}
@media(prefers-reduced-motion:reduce){.tf-map-action,.tf-map-tab,.tf-map-hint,.tf-map-edge,.tf-map-edge button,.tf-map-table,.tf-map-table-toggle,.tf-map-chevron,.tf-map-row,.tf-map-band{animation:none!important;transition:none!important}}
/* The view both maps share: the legend bar with the count and Rings/Table, the side panel with its filters, the stage
   with one height for every view, and the contracts table. */
#verification-health-map,#verification-depth-map{--tf-map-panel:400px}
.bd-article-container:has(#verification-health-map),.bd-article-container:has(#verification-depth-map){overflow:visible}
.tf-map-badge{display:inline-grid;place-items:center;min-width:1.1rem;height:1.1rem;padding:0 .25rem;border-radius:999px;background:var(--pst-color-text-base);color:var(--pst-color-background);font-size:.62rem;font-weight:800}
.tf-map-badge[hidden],.tf-map-filters[hidden],.tf-map-seg[hidden]{display:none}
.tf-map-lead.filtered>.tf-map-stamp,.tf-map-lead.filtered>.tf-map-help{display:none}
.tf-map-filters{display:flex;align-items:center;gap:.5rem;min-width:0;font-size:.74rem}
.tf-map-chips{display:flex;align-items:center;gap:.35rem;min-width:0;overflow-x:auto;overscroll-behavior-x:contain;scrollbar-width:none}
.tf-map-chips::-webkit-scrollbar{display:none}
.tf-map-chip{flex:none;display:inline-flex;align-items:center;gap:.35rem;height:26px;padding:0 .35rem 0 .65rem;border:1px solid var(--tf-map-selected);border-radius:999px;background:var(--tf-map-raised);color:var(--pst-color-text-base);font:inherit;font-size:.74rem;cursor:pointer}
.tf-map-chip i{font-size:.66rem;color:var(--pst-color-text-muted)}
.tf-map-chip:hover i{color:var(--pst-color-text-base)}
.tf-map-chip:focus-visible,.tf-map-clear:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:2px}
.tf-map-clear{flex:none;white-space:nowrap;padding:0 .2rem;border:0;background:none;color:var(--pst-color-text-muted);font:inherit;font-size:.74rem;text-decoration:underline;cursor:pointer}
.tf-map-legendbar{display:flex;flex-wrap:wrap;align-content:flex-start;align-items:center;justify-content:space-between;gap:.35rem 1.2rem;min-height:26px;margin:0 0 .6rem}
.tf-map-legend{display:flex;flex:1 1 0;flex-wrap:wrap;align-items:center;align-content:flex-start;gap:.3rem 1rem;min-width:0;font-size:.74rem;color:var(--pst-color-text-muted)}
.tf-map-legend>span{display:inline-flex;align-items:center;gap:.38rem}
.tf-map-legend b{font-weight:700;color:var(--pst-color-text-base);font-variant-numeric:tabular-nums}
.tf-map-legend>.tf-map-help{display:inline-grid}
/* Rings/Table and the count keep one place: beside the legend on wide screens, on their own line below it on narrow ones. */
@media(max-width:760px){.tf-map-legend .extra{display:none}.tf-map-side{flex-basis:100%}}
.tf-map-side{display:inline-flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:.4rem .8rem;margin-left:auto}
.tf-map-total{color:var(--pst-color-text-muted);font-size:.74rem;font-variant-numeric:tabular-nums;white-space:nowrap}
.tf-map-total b{color:var(--pst-color-text-base)}
.tf-map-seg{display:inline-flex;flex-wrap:wrap;gap:.25rem}
.tf-map-seg.off{visibility:hidden}
.tf-map-seg button{font:inherit;font-size:.74rem;padding:.14rem .58rem;border:1px solid var(--tf-map-line);border-radius:999px;background:var(--tf-map-goal);color:var(--pst-color-text-base);cursor:pointer}
.tf-map-seg button:hover{border-color:var(--tf-map-line-strong)}
.tf-map-seg button[aria-pressed=true]{border-color:var(--tf-map-selected);background:var(--tf-map-raised);box-shadow:inset 0 0 0 1px var(--tf-map-selected)}
.tf-map-seg button:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:2px}
.tf-map-body{display:flex;align-items:flex-start}
.tf-map-panel{position:sticky;top:calc(var(--pst-header-height,4rem) + 8px);flex:0 0 auto;width:0;max-height:min(calc(100vh - var(--pst-header-height,4rem) - 16px),var(--tf-map-view-h,100vh));overflow:hidden;transition:width 240ms var(--tf-map-ease)}
.tf-map-body.panel-open .tf-map-panel{width:calc(var(--tf-map-panel) + 16px);overflow:auto;overscroll-behavior:contain;scrollbar-width:thin}
.tf-map-panel-inner{container:tf-map-panel/inline-size;width:var(--tf-map-panel);margin-right:16px;padding:.6rem .65rem .7rem;border:1px solid var(--tf-map-line);border-radius:12px;background:var(--tf-map-goal);transition:opacity 200ms var(--tf-map-ease)}
.tf-map-body:not(.panel-open) .tf-map-panel-inner{opacity:0}
.tf-map-still .tf-map-panel,.tf-map-still .tf-map-panel-inner{transition:none}
.tf-map-fresh{animation:tf-map-in 180ms var(--tf-map-ease) both}
.tf-map-panel-head{display:flex;align-items:center;justify-content:space-between;gap:.5rem;margin-bottom:.5rem}
.tf-map-panel-title{display:inline-flex;align-items:center;gap:.4rem;font-size:.78rem;font-weight:750}
.tf-map-close{display:inline-grid;place-items:center;width:24px;height:24px;padding:0;border:1px solid transparent;border-radius:6px;background:none;color:var(--pst-color-text-muted);font:inherit;font-size:1rem;line-height:1;cursor:pointer}
.tf-map-close:hover{border-color:var(--tf-map-line-strong);color:var(--pst-color-text-base)}
.tf-map-close:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:1px}
/* The view sticks beside the sticky panel, so both stay in sight while the page scrolls. */
.tf-map-stage{position:sticky;top:calc(var(--pst-header-height,4rem) + 8px);flex:1 1 auto;min-width:0}
.tf-map-stage [hidden]{display:none!important}
.tf-map-view{display:block;width:100%;height:var(--tf-map-view-h,auto);animation:tf-map-in 220ms var(--tf-map-ease) both}
.tf-map-view a,.tf-map-view a:hover{cursor:pointer;outline:none;text-decoration:none}
.tf-map-view a{transition:opacity 160ms var(--tf-map-ease)}
.tf-map-view text{pointer-events:none}
.tf-map-rings{overflow:visible}
/* What both views draw: goals and capabilities in neutral grey, contracts in the page's colours, the names, the
   lineage of a hovered mark, the marks the filters keep or dim, and what Changes outlines. */
#verification-health-map .tf-map-goal,#verification-depth-map .tf-map-goal{fill:var(--tf-map-goal);stroke:var(--tf-map-line);stroke-width:1;transition:stroke var(--tf-map-medium) var(--tf-map-ease)}
#verification-health-map .tf-map-feature,#verification-depth-map .tf-map-feature{fill:var(--tf-map-feature);stroke:var(--tf-map-line);stroke-width:1;transition:stroke var(--tf-map-medium) var(--tf-map-ease)}
#verification-health-map :is(.tf-map-rings,.tf-map-thumb.radial) .tf-map-goal,#verification-depth-map :is(.tf-map-rings,.tf-map-thumb.radial) .tf-map-goal{fill:var(--tf-map-radial-goal)}
#verification-health-map :is(.tf-map-rings,.tf-map-thumb.radial) .tf-map-feature,#verification-depth-map :is(.tf-map-rings,.tf-map-thumb.radial) .tf-map-feature{fill:var(--tf-map-radial-feature)}
.tf-map-tile{transition:fill 120ms var(--tf-map-ease)}
#verification-health-map .tf-map-lineage,#verification-depth-map .tf-map-lineage{stroke:var(--tf-map-lineage)}
#verification-health-map .tf-map-dim,#verification-depth-map .tf-map-dim{opacity:.13}
#verification-health-map :is(path,rect).tf-map-hit,#verification-depth-map :is(path,rect).tf-map-hit{stroke:var(--tf-map-ring);stroke-width:2.4}
#verification-health-map .tf-map-up,#verification-depth-map .tf-map-up{stroke:var(--tf-map-up);stroke-width:3}
#verification-health-map .tf-map-down,#verification-depth-map .tf-map-down{stroke:var(--tf-map-down);stroke-width:3;stroke-dasharray:3 2}
.tf-map-sw{display:inline-block;flex:0 0 auto;width:12px;height:12px;border-radius:3px;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--pst-color-text-base) 10%,transparent)}
.tf-map-option .tf-map-sw{width:10px;height:10px}
.tf-map-dot{fill:var(--pst-color-text-muted);transition:opacity var(--tf-map-medium) var(--tf-map-ease),fill var(--tf-map-medium) var(--tf-map-ease)}
.tf-map-label-goal{font-size:13px;font-weight:650;fill:var(--pst-color-text-base)}
.tf-map-label-feature{font-size:12px;font-weight:500;fill:var(--pst-color-text-muted)}
#verification-health-map .tf-map-ring-center,#verification-depth-map .tf-map-ring-center{fill:var(--tf-map-goal);stroke:var(--tf-map-line);stroke-width:1}
.tf-map-ring-kicker{font-size:10px;font-weight:750;letter-spacing:.08em;fill:var(--pst-color-text-muted);text-anchor:middle}
.tf-map-ring-big{font-weight:800;letter-spacing:.02em;fill:var(--pst-color-text-base);text-anchor:middle}
.tf-map-ring-small{font-size:11.5px;fill:var(--pst-color-text-muted);text-anchor:middle}
.tf-map-ring-name{font-size:9.5px;font-weight:650;letter-spacing:.02em;fill:var(--pst-color-text-muted);text-anchor:middle}
.tf-map-ring-name.current{fill:var(--pst-color-text-base)}
.tf-map-view .tf-map-ring-name[data-map-ring]{cursor:pointer;outline:none;pointer-events:auto}
.tf-map-ring-name[data-map-ring]:hover,.tf-map-ring-name[data-map-ring]:focus-visible{text-decoration:underline}
.tf-map-changes-key{display:inline-flex;align-items:center;gap:.35rem;margin-left:.35rem;font-size:.72rem;color:var(--pst-color-text-muted)}
.tf-map-changes-key i{display:inline-block;width:11px;height:11px;margin-left:.3rem;border-radius:3px;box-shadow:inset 0 0 0 2.5px var(--tf-map-up)}
.tf-map-changes-key i.down{box-shadow:none;border:2px dashed var(--tf-map-down)}
@keyframes tf-map-in{from{opacity:0}to{opacity:1}}
/* On narrow screens the panel sits above the view with one height for every layer, so the view below never moves. */
@media(max-width:960px){.tf-map-stage{position:relative;top:auto}.tf-map-body{display:block}.tf-map-panel{position:static;width:auto;max-height:none;display:none}.tf-map-body.panel-open .tf-map-panel{display:block;width:auto;height:min(55vh,26rem);margin-bottom:.7rem;overflow:auto;overscroll-behavior:contain}.tf-map-panel-inner{width:auto;min-height:100%;margin-right:0}}
.tf-map-facet{margin-top:.75rem}
.tf-map-facet.own{margin-top:.1rem}
.tf-map-facet-title{display:flex;align-items:center;gap:.4rem;margin-bottom:.3rem;font-size:.62rem;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-map-facet-title.first{margin:0 0 .35rem}
.tf-map-facet-empty{margin:0;font-size:.72rem;font-weight:600;color:var(--pst-color-text-muted)}
.tf-map-options{display:flex;flex-wrap:wrap;gap:.3rem}
.tf-map-option{display:inline-flex;align-items:center;gap:.35rem;min-height:24px;padding:.1rem .55rem;border:1px solid var(--tf-map-line);border-radius:999px;background:var(--pst-color-background);color:var(--pst-color-text-base);font:inherit;font-size:.72rem;text-align:left;cursor:pointer}
.tf-map-option b{display:inline-block;min-width:2ch;text-align:right;font-weight:700;font-variant-numeric:tabular-nums;color:var(--pst-color-text-muted)}
.tf-map-option:hover{border-color:var(--tf-map-line-strong)}
.tf-map-option[aria-pressed=true]{border-color:var(--tf-map-selected);background:var(--tf-map-raised);box-shadow:inset 0 0 0 1px var(--tf-map-selected)}
.tf-map-option[aria-pressed=true] b{color:var(--pst-color-text-base)}
.tf-map-option:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:1px}
.tf-map-option:disabled{opacity:.38;cursor:default}
.tf-map-option:disabled:hover{border-color:var(--tf-map-line)}
.tf-map-option.hit{border-color:var(--tf-map-ring);box-shadow:inset 0 0 0 1.5px var(--tf-map-ring)}
.tf-map-list-bar{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem .9rem;margin:0 0 .5rem;font-size:.74rem}
.tf-map-list-bar-label{font-size:.64rem;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-map-summary{flex:1 1 12rem;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--pst-color-text-muted);font-variant-numeric:tabular-nums}
.tf-map-list-wrap{overflow:auto;border:1px solid var(--tf-map-line);border-radius:10px;animation:tf-map-in 220ms var(--tf-map-ease) both}
.tf-map-list-table{width:100%;border-collapse:separate;border-spacing:0;font-size:.74rem}
.tf-map-list-table th{position:sticky;top:0;z-index:2;padding:.4rem .45rem;border-bottom:1px solid var(--tf-map-line-strong);background:var(--pst-color-surface);font-size:.66rem;font-weight:750;text-align:left;white-space:nowrap}
.tf-map-list-table th button{display:inline-flex;align-items:center;gap:.25rem;padding:0;border:0;background:none;color:inherit;font:inherit;cursor:pointer}
.tf-map-list-table th button:hover{text-decoration:underline}
.tf-map-list-table th button:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:2px}
.tf-map-list-table th .dir{font-size:.6rem;color:var(--pst-color-text-muted)}
.tf-map-list-table th.void{color:var(--pst-color-text-muted);font-weight:600}
.tf-map-list-table td{padding:.26rem .45rem;border-bottom:1px solid var(--tf-map-line);vertical-align:middle}
.tf-map-list-table tr.tf-map-list-group td{padding-top:.6rem;border-bottom:1px solid var(--tf-map-line);background:var(--tf-map-goal)}
.tf-map-list-table tr.tf-map-list-group.sub td{padding-top:.35rem;background:none}
.tf-map-list-group-name{font-size:.72rem;font-weight:750}
.tf-map-list-table tr.tf-map-list-group.sub .tf-map-list-group-name{font-weight:650;color:var(--pst-color-text-muted)}
.tf-map-list-group-stats{margin-left:.6rem;font-size:.68rem;color:var(--pst-color-text-muted);font-variant-numeric:tabular-nums}
.tf-map-list-table tr.tf-map-list-row{cursor:pointer}
.tf-map-list-table tr.tf-map-list-row:hover td{background:var(--tf-map-goal)}
.tf-map-list-table tr.tf-map-list-row.flash td{animation:tf-map-flash 1.6s var(--tf-map-ease)}
@keyframes tf-map-flash{0%,40%{background:var(--tf-map-raised)}100%{background:transparent}}
.tf-map-list-table .name{min-width:12rem;max-width:18rem}
.tf-map-list-table .name a{display:block;font-weight:600;color:var(--pst-color-text-base);text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-map-list-table .name a:hover{text-decoration:underline}
.tf-map-list-table .name small{display:block;color:var(--pst-color-text-muted);font-family:var(--pst-font-family-monospace);font-size:.62rem}
.tf-map-list-table tr.treq .name{padding-left:1.25rem}
.tf-map-muted{color:var(--pst-color-text-muted)}
.tf-map-num{font-variant-numeric:tabular-nums;text-align:right}
.tf-map-list-empty{padding:1.2rem;text-align:center;color:var(--pst-color-text-muted)}
.tf-map-goal-label{transition:opacity 160ms var(--tf-map-ease)}
.tf-map-nolabels .tf-map-goal-label{opacity:0}
.tf-map-goal-label.enter{animation:tf-map-in 240ms var(--tf-map-ease) both}
.tf-map-leader{fill:none;stroke:var(--tf-map-line-strong);stroke-width:1}
.tf-map-view text.tf-map-goal-name{font-size:13px;font-weight:650;fill:var(--pst-color-text-base);pointer-events:auto;cursor:pointer}
@media(prefers-reduced-motion:reduce){.tf-map-panel,.tf-map-panel-inner,.tf-map-fresh,.tf-map-view,.tf-map-list-wrap,.tf-map-goal-label,.tf-map-list-table tr{animation:none!important;transition:none!important}}
.tf-map-mx{display:grid;gap:3px;font-size:.7rem}
.tf-map-mx-h{display:flex;align-items:center;justify-content:center;gap:.25rem;min-height:22px;font-size:.66rem;font-weight:700;color:var(--pst-color-text-muted);text-align:center}
.tf-map-mx-h.void,.tf-map-mx-r.void{opacity:.55}
.tf-map-mx-r{display:flex;flex-direction:column;justify-content:center;padding-right:.2rem;font-size:.68rem;font-weight:650;line-height:1.15}
.tf-map-mx-r small{font-size:.62rem;font-weight:500;color:var(--pst-color-text-muted);white-space:nowrap}
.tf-map-mx-r.void{min-height:26px}
.tf-map-mx-cell{position:relative;display:flex;flex-direction:column;align-items:flex-start;gap:0;min-width:0;min-height:58px;padding:.3rem .35rem .4rem .45rem;border:1px solid var(--tf-map-line);border-radius:7px;background:var(--pst-color-background);color:inherit;font:inherit;text-align:left;cursor:pointer;transition:border-color 140ms var(--tf-map-ease),box-shadow 140ms var(--tf-map-ease),opacity 160ms var(--tf-map-ease)}
.tf-map-mx-cell::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;border-radius:7px 0 0 7px;background:var(--fill)}
.tf-map-mx-cell b{font-variant-numeric:tabular-nums;font-size:1rem;font-weight:750;line-height:1.1}
.tf-map-mx-cell b span{margin-left:.25rem;font-size:.64rem;font-weight:500;color:var(--pst-color-text-muted)}
.tf-map-mx-cell small{max-width:100%;font-size:.62rem;line-height:1.3;color:var(--pst-color-text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-map-mx-cell:hover{border-color:var(--tf-map-selected)}
.tf-map-mx-cell[aria-pressed=true]{border-color:var(--tf-map-selected);box-shadow:inset 0 0 0 1.5px var(--tf-map-selected)}
.tf-map-mx-cell:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:1px}
.tf-map-mx-cell.empty{align-items:center;justify-content:center;border-style:dashed;background:none;color:var(--pst-color-text-muted);font-weight:800;cursor:default}
.tf-map-mx-cell.empty::before{content:none}
.tf-map-mx-cell.void{min-height:0;border-color:color-mix(in srgb,var(--pst-color-text-base) 9%,transparent)}
.tf-map-mx-cell.hit{border-color:var(--tf-map-ring);box-shadow:inset 0 0 0 1.5px var(--tf-map-ring)}
.tf-map-mx-cell.gapcell{border:1.5px dashed var(--tf-map-ring)}
.tf-map-mx-cell:disabled{opacity:.38;cursor:default}
.tf-map-mx-cell:disabled:hover{border-color:var(--tf-map-line)}
.tf-map-seg-dim{opacity:.28}
/* The hover card, the outline of a hovered mark, the arc of a hovered ray and Find, shared by both maps. */
.tf-map-card{position:fixed;z-index:1200;width:300px;max-width:calc(100vw - 20px);padding:.66rem .76rem .6rem;border:1px solid var(--tf-map-line-strong);border-radius:var(--tf-map-radius);background:color-mix(in srgb,var(--pst-color-surface) 96%,var(--pst-color-text-base) 4%);color:var(--pst-color-text-base);box-shadow:0 12px 32px rgba(0,0,0,.18),0 2px 6px rgba(0,0,0,.08);font-size:.75rem;line-height:1.35;text-align:left;opacity:0;visibility:hidden;transform:translateY(4px);transition:opacity var(--tf-map-medium) var(--tf-map-ease),transform var(--tf-map-medium) var(--tf-map-ease),visibility var(--tf-map-medium) linear,left 120ms var(--tf-map-ease),top 120ms var(--tf-map-ease);pointer-events:none}
.tf-map-card.visible{opacity:1;visibility:visible;transform:none}
.tf-map-card.instant{transition:opacity var(--tf-map-medium) var(--tf-map-ease),transform var(--tf-map-medium) var(--tf-map-ease),visibility var(--tf-map-medium) linear}
.tf-map-card-head{display:flex;align-items:center;justify-content:space-between;gap:.5rem;margin-bottom:.3rem}
.tf-map-card-kind{font-size:.64rem;font-weight:800;letter-spacing:.055em;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-map-pill{padding:.05rem .45rem;border-radius:999px;font-size:.66rem;font-weight:750;white-space:nowrap;color:var(--pst-color-text-base);background:color-mix(in srgb,var(--pst-color-text-base) 8%,transparent)}
.tf-map-card-title{font-size:.84rem;font-weight:650;line-height:1.28}
.tf-map-card-path{margin:.15rem 0 0;color:var(--pst-color-text-muted)}
.tf-map-card-rows{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.2rem 1rem;margin-top:.45rem;padding-top:.42rem;border-top:1px solid var(--tf-map-line)}
.tf-map-card-rows .sub{grid-column:1/-1;margin-top:.12rem;font-size:.64rem;font-weight:650;letter-spacing:.05em;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-map-card-rows .sub:first-child{margin-top:0}
.tf-map-card-rows .note{grid-column:1/-1;color:var(--pst-color-text-muted)}
.tf-map-card-rows .value{font-weight:700;font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
.tf-map-card-go{margin-top:.45rem;color:var(--pst-color-text-muted)}
.tf-map-card-go b{font-weight:650;color:var(--pst-color-text-base)}
.tf-map-outline{fill:none;stroke:var(--tf-map-ring);stroke-width:1.5;opacity:0;pointer-events:none;transition:opacity 140ms var(--tf-map-ease),transform 150ms var(--tf-map-ease),width 150ms var(--tf-map-ease),height 150ms var(--tf-map-ease)}
.tf-map-outline.visible{opacity:1}
.tf-map-outline.instant{transition:opacity 140ms var(--tf-map-ease)}
.tf-map-arc{fill:none;stroke:var(--tf-map-ring);stroke-width:1.5;opacity:0;pointer-events:none;transition:opacity 140ms var(--tf-map-ease)}
.tf-map-arc.visible{opacity:1}
.tf-map-find{position:fixed;inset:0;z-index:1400;display:grid;align-items:start;justify-items:center;padding-top:11vh;background:rgba(0,0,0,.38)}
.tf-map-find[hidden]{display:none}
.tf-map-find-box{display:grid;grid-template-rows:auto minmax(0,1fr) auto;width:min(660px,calc(100vw - 24px));max-height:72vh;overflow:hidden;border:1px solid var(--tf-map-line-strong);border-radius:var(--tf-map-radius);background:var(--pst-color-surface);box-shadow:0 24px 60px rgba(0,0,0,.35)}
.tf-map-find-input{width:100%;padding:.85rem 1rem;border:0;border-bottom:1px solid var(--tf-map-line);background:none;color:var(--pst-color-text-base);font:inherit;font-size:.95rem;outline:none}
.tf-map-find-list{overflow:auto;padding:.35rem}
.tf-map-find-item{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:.75rem;padding:.42rem .6rem;border-radius:8px;cursor:pointer}
.tf-map-find-item[aria-selected=true]{background:var(--tf-map-raised)}
.tf-map-find-badge{display:inline-flex;align-items:center}
.tf-map-find-text{min-width:0}
.tf-map-find-name{display:block;font-size:.82rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-map-find-path{display:block;font-size:.7rem;color:var(--pst-color-text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tf-map-find-id{font-family:var(--pst-font-family-monospace);font-size:.66rem;color:var(--pst-color-text-muted)}
.tf-map-find-empty{padding:1rem;text-align:center;font-size:.82rem;color:var(--pst-color-text-muted)}
.tf-map-find-foot{padding:.45rem .9rem;border-top:1px solid var(--tf-map-line);font-size:.7rem;color:var(--pst-color-text-muted)}
@media(prefers-reduced-motion:reduce){#verification-health-map *,#verification-depth-map *,.tf-map-card{animation:none!important;transition:none!important}}"""

MAP_SHARED_JS = r"""// Shared by the Health and Depth maps: the tree, both views, the layer strip, the filters, the table, the hover card,
// Find, Changes, the address and the keys. mapPage runs a map; the page describes its layers and draws what only it
// knows: the Health Map judges each layer, the Depth Map measures it.
const MAP_CELL=10;
const escapeHtml=value=>String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const NS="http://www.w3.org/2000/svg";
function el(tag,attrs,parent){const node=document.createElementNS(NS,tag);for(const key in attrs)node.setAttribute(key,attrs[key]);parent?.appendChild(node);return node}
const measure=document.createElement("canvas").getContext("2d");
const family=()=>getComputedStyle(document.body).fontFamily;
// The longest label that fits, cut at a word with an ellipsis; nothing when not even a short one fits.
function fitLabel(label,max,font){
 measure.font=font;
 const width=text=>measure.measureText(text).width;
 if(width(label)<=max)return label;
 const words=label.split(" ");
 for(let count=words.length-1;count>0;count--){const candidate=words.slice(0,count).join(" ")+"…";if(candidate.length>=7&&width(candidate)<=max)return candidate}
 return"";
}
const polar=(cx,cy,r,a)=>[cx+r*Math.sin(a),cy-r*Math.cos(a)];
const fixed=value=>Math.round(value*100)/100;
function arcPath(cx,cy,r0,r1,a0,a1){
 const large=a1-a0>Math.PI?1:0,p0=polar(cx,cy,r1,a0),p1=polar(cx,cy,r1,a1),p2=polar(cx,cy,r0,a1),p3=polar(cx,cy,r0,a0);
 return"M"+fixed(p0[0])+","+fixed(p0[1])+"A"+fixed(r1)+","+fixed(r1)+" 0 "+large+" 1 "+fixed(p1[0])+","+fixed(p1[1])
   +"L"+fixed(p2[0])+","+fixed(p2[1])+"A"+fixed(r0)+","+fixed(r0)+" 0 "+large+" 0 "+fixed(p3[0])+","+fixed(p3[1])+"Z";
}
const plural=(count,one,many)=>count+" "+(count===1?one:many);
const clip=(text,max)=>{text=String(text||"");if(text.length<=max)return text;const cut=text.slice(0,max);return cut.slice(0,Math.max(cut.lastIndexOf(" "),max-12)).trimEnd()+"…"};
// Swatches and legend items look the same on both maps; the page gives the colour (a class or a CSS colour).
const mapSwatch=(cls,color)=>'<i class="tf-map-sw'+(cls?" "+cls:"")+'"'+(color?' style="background:'+color+'"':"")+"></i>";
const mapLegendItem=(swatch,label,count,extra)=>"<span"+(extra?' class="extra"':"")+">"+swatch+label+(count===undefined?"":" <b>"+count+"</b>")+"</span>";
// Where a link goes: the page for the row's kind and the section its anchor opens, named as on that page.
const MAP_OPENS={product:"Product / System assurance",goal:"Outcome assurance",feature:"Capability assurance",requirement:"Contract evidence",treq:"Technical assurance"};
const MAP_SECTIONS=[["cross-capability-integration","Cross-capability integration"],["capability-integration","Capability integration"],["outcome-validation","Outcome validation"],["requirement-support","Requirement support"],["capability-support","Capability support"],["goal-support","Goal support"],["technical-support","Technical support"],["ce-coverage-","Verification matrix"],["ce-faults-","Fault model"]];
function mapOpens(row,href){
 const anchor=String(href||"").split("#")[1]||"",section=MAP_SECTIONS.find(([mark])=>anchor.includes(mark));
 return MAP_OPENS[row.level]+(section?" › "+section[1]:"");
}
function mapRunLabel(iso){
 const date=new Date(iso);
 return Number.isNaN(date.getTime())?"":new Intl.DateTimeFormat("en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}).format(date);
}
function mapRunAge(iso){
 const hours=(Date.now()-new Date(iso).getTime())/36e5;
 if(!(hours>=0))return"";
 return hours<1?Math.max(1,Math.round(hours*60))+" min ago":hours<48?Math.round(hours)+" h ago":Math.round(hours/24)+" days ago";
}
// The retained run a page shows: when it ran, how many checks, which commit, and whether its evidence is current.
function mapStamp(run){
 if(!run?.started_at)return"";
 const fresh=run.fresh,stale=fresh?fresh.total-fresh.passed:0;
 return"Retained run <b>"+escapeHtml(mapRunLabel(run.started_at))+"</b> ("+mapRunAge(run.started_at)+")"
   +(run.checks?" · "+run.checks+" checks":"")
   +(run.commit?" · commit <code>"+escapeHtml(run.commit)+"</code>":"")
   +(fresh?' · evidence <span class="'+(stale?"failed":"passed")+'">'+(stale?stale+" stale":"all current")+"</span>":"");
}
// Hints: one plain sentence for anything with data-tip, above it, or below it when there is no room.
function mapHint(hint){
 let target=null;
 function show(node){
   target=node;
   hint.textContent=node.dataset.tip;
   hint.setAttribute("aria-hidden","false");
   const box=node.getBoundingClientRect(),size=hint.getBoundingClientRect();
   const left=Math.max(8,Math.min(innerWidth-size.width-8,box.left+box.width/2-size.width/2));
   let top=box.top-size.height-8;
   if(top<8)top=box.bottom+8;
   hint.style.left=Math.round(left)+"px";hint.style.top=Math.round(top)+"px";
   hint.classList.add("visible");
 }
 function hide(){target=null;hint.classList.remove("visible");hint.setAttribute("aria-hidden","true")}
 function watch(node,skip){
   node.addEventListener("pointerover",event=>{
     const tip=event.target.closest("[data-tip]");
     if(tip&&tip.dataset.tip&&!skip?.contains(tip)){if(tip!==target)show(tip)}
     else if(target)hide();
   });
   node.addEventListener("pointerleave",hide);
 }
 addEventListener("scroll",hide,{passive:true});
 return{show,hide,watch};
}
// One column per contract in tree order, with a gap between capabilities and a wider one between goals.
// The All layers table and the rings of both maps use the same columns, so a contract keeps its place.
function mapColumns(root,children,isLeaf){
 const leaves=[],groups=[];
 let units=0;
 const walk=row=>{
   const start=units;
   if(isLeaf(row)){leaves.push({row,x:units});units+=MAP_CELL}
   (children.get(row.id)||[]).forEach((child,index)=>{if(index&&child.level==="feature")units+=4;walk(child)});
   if(row.level==="goal"||row.level==="feature")groups.push({row,start,end:units});
 };
 (children.get(root.id)||[]).forEach((goal,index)=>{if(index)units+=14;walk(goal)});
 return{leaves,groups,units};
}
// The tree both maps draw, from rows in tree order with the product first: goals, capabilities and contracts.
const MAP_KIND={product:"Product / System",goal:"Goal",feature:"Capability",requirement:"Requirement",treq:"Technical requirement"};
function mapTree(rows){
 const root=rows[0],rowById=new Map(rows.map(row=>[row.id,row])),children=new Map();
 rows.slice(1).forEach(row=>{if(!children.has(row.parent))children.set(row.parent,[]);children.get(row.parent).push(row)});
 const isLeaf=row=>row.level==="requirement"||row.level==="treq";
 const ancestors=row=>{const out=[];let current=rowById.get(row.parent);while(current&&current.level!=="product"){out.unshift(current);current=rowById.get(current.parent)}return out};
 const inside=row=>{const out=[];const walk=item=>(children.get(item.id)||[]).forEach(child=>{if(isLeaf(child))out.push(child);walk(child)});walk(row);return out};
 const goalOf=new Map(rows.map(row=>[row.id,row.level==="goal"?row.id:ancestors(row).find(item=>item.level==="goal")?.id||""]));
 return{root,rows,rowById,children,isLeaf,ancestors,inside,goalOf,leaves:rows.filter(isLeaf),goals:rows.filter(row=>row.level==="goal"),columns:mapColumns(root,children,isLeaf)};
}
// Changes since the previous retained run: a card counts what went up and what went down in its layer.
// The page names what up and down mean and colours them only where it judges.
function mapDelta(delta,key,words){
 const change=(delta.layers||{})[key]||{up:[],down:[]};
 if(!delta.baseline||!(change.up.length||change.down.length))return"";
 return'<span class="tf-map-delta" data-tip="Since the run of '+escapeHtml(mapRunLabel(delta.baseline.started_at))+": "+change.up.length+" "+words[0]+", "+change.down.length+" "+words[1]+'">'
   +(change.up.length?'<span class="up">▲'+change.up.length+"</span>":"")+(change.down.length?'<span class="down">▼'+change.down.length+"</span>":"")+"</span>";
}
function mapChanges(button,delta,apply){
 let on=false;
 if(delta.baseline)button.dataset.tip="Outline what changed since the run of "+mapRunLabel(delta.baseline.started_at)+".";
 else{button.setAttribute("aria-disabled","true");button.dataset.tip="No earlier retained run to compare with yet."}
 button.addEventListener("click",()=>{if(!delta.baseline)return;on=!on;button.setAttribute("aria-pressed",String(on));apply(on)});
 return{on:()=>on};
}
// Copy link writes the address first, and keeps its width while it says Copied.
function mapCopy(button,write){
 button.addEventListener("click",()=>{
   write();
   const label=button.querySelector("span");
   button.style.minWidth=button.offsetWidth+"px";
   navigator.clipboard?.writeText(location.href).then(()=>{label.textContent="Copied";setTimeout(()=>{label.textContent="Copy link";button.style.minWidth=""},1400)},()=>{});
 });
}
// The layer strip. Overall comes first and stays pinned while the strip scrolls; the page's groups follow,
// each with a name and a count. The scroll edges count the layers they hide, and All layers opens every
// layer as one row with one column per contract.
//   layers   [[key,label,help]] in the page's default order
//   groups() [{tone,label,icon,keys}], the first one is Overall; tone colours a group only where the page judges
//   card(key)  {status,count,delta,thumb,name}: the second and third lines of a card, what changed, its mini-map
//              and its spoken name
//   row(key)   {status,count,name}: the same facts, short, for the table row
//   cells(key) the table row's marks, one per contract column (data-leaf on the one that can be picked)
//   foot(row)  what every layer says about the contract under the pointer
//   current(), select(key,focus), focus(id)
function mapStrip(o){
 const $=id=>document.getElementById(id);
 const bar=$("tf-map-layerbar"),scroller=$("tf-map-scroller"),tabs=$("tf-map-tabs"),toggle=$("tf-map-table-toggle");
 const table=$("tf-map-table"),rowsBox=$("tf-map-rows"),foot=$("tf-map-table-foot");
 const edges={left:bar.querySelector(".tf-map-edge.left"),right:bar.querySelector(".tf-map-edge.right")};
 const byKey=new Map(o.layers.map(layer=>[layer[0],layer]));
 const FOOT_IDLE="Pick a row to open its map. Each column is one contract, grouped by goal: point at it to compare layers.";
 const motion=()=>matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth";
 let pinWidth=0,edgeFrame=0,hold=null;
 const order=()=>o.groups().flatMap(group=>group.keys);
 const toneOf=key=>o.groups().find(group=>group.keys.includes(key))?.tone||"";
 function tabHtml(key){
   const[,label,help]=byKey.get(key),card=o.card(key);
   return'<button type="button" role="tab" class="tf-map-tab" id="tf-map-tab-'+key+'" data-map-layer="'+key+'" aria-label="'+escapeHtml(card.name)+'" aria-controls="tf-map-stage" aria-describedby="tf-map-help-'+key+'">'
     +'<span class="tf-map-tab-title">'+label+"</span>"+card.thumb
     +'<span class="tf-map-tab-status">'+card.status+'<span class="tf-map-help" aria-hidden="true" data-tip="'+escapeHtml(help)+'">?</span></span>'
     +'<span class="tf-map-count"><span class="tf-map-count-text">'+card.count+"</span>"+card.delta+"</span>"
     +'<span class="tf-sr-only" id="tf-map-help-'+key+'">'+escapeHtml(help)+"</span></button>";
 }
 function groupHtml(group,index){
   if(!group.keys.length)return"";
   const cards='<div class="tf-map-group-cards" role="none">'+group.keys.map(tabHtml).join("")+"</div>";
   if(!index)return'<div class="tf-map-group pinned" role="none" style="flex-grow:1"><div class="tf-map-group-head" aria-hidden="true"></div>'+cards+"</div>";
   return'<div class="tf-map-group'+(group.tone?" "+group.tone:"")+'" role="none" style="flex-grow:'+group.keys.length+'">'
     +'<div class="tf-map-group-head" aria-hidden="true"><span class="tf-map-group-label">'+(group.icon?'<i class="fa-solid '+group.icon+'"></i>':"")+escapeHtml(group.label)+" · "+group.keys.length+"</span></div>"+cards+"</div>";
 }
 function build(){
   const left=scroller.scrollLeft;
   tabs.innerHTML=o.groups().map(groupHtml).join("");
   scroller.scrollLeft=left;
   sync();syncBar();
   // A rebuild (fonts, a resize) stops a scroll on its way: put the current layer in sight at once.
   const tab=$("tf-map-tab-"+o.current());
   if(tab)reveal(tab,true);
 }
 function sync(){
   tabs.querySelectorAll("[data-map-layer]").forEach(button=>{
     const active=button.dataset.mapLayer===o.current();
     button.setAttribute("aria-selected",String(active));
     button.tabIndex=active?0:-1;
   });
   rowsBox.querySelectorAll("[data-map-row]").forEach(row=>row.setAttribute("aria-selected",String(row.dataset.mapRow===o.current())));
 }
 function reveal(tab,instant){
   if(pinWidth&&tab.closest(".pinned"))return;
   // The first card goes back to the very start of the strip.
   if(tab.closest(".pinned")){if(scroller.scrollLeft)scroller.scrollTo({left:0,behavior:instant?"auto":motion()});return}
   const view=scroller.getBoundingClientRect(),box=tab.getBoundingClientRect(),room=64;
   const left=box.left-view.left,right=box.right-view.left;
   const delta=left<pinWidth+room?left-pinWidth-room:right>view.width-room?right-view.width+room:0;
   if(delta)scroller.scrollBy({left:delta,behavior:instant?"auto":motion()});
 }
 function show(key,focus){
   const tab=$("tf-map-tab-"+key);
   if(!tab)return;
   reveal(tab);
   if(focus)tab.focus({preventScroll:true});
 }
 // Overall is pinned only when the strip scrolls and there is room left for other layers.
 function syncBar(){
   const pinned=scroller.scrollWidth>scroller.clientWidth+1&&scroller.clientWidth>=600;
   bar.classList.toggle("tf-map-pin",pinned);
   const first=tabs.querySelector(".tf-map-group.pinned");
   pinWidth=pinned&&first?Math.round(first.getBoundingClientRect().width):0;
   bar.style.setProperty("--tf-pin",pinWidth+"px");
   // Group names stick next to the pinned Overall, or next to the table toggle when Overall scrolls away.
   bar.style.setProperty("--tf-label-left",(pinWidth||Math.round(toggle.getBoundingClientRect().width)+10)+"px");
   updateEdges();
 }
 function edgeNote(counts,side){
   const arrow='<i class="fa-solid fa-chevron-'+side+'" aria-hidden="true"></i>';
   const note=counts.failed?'<span class="tf-map-edge-note failed"><i class="fa-solid fa-circle-xmark" aria-hidden="true"></i>'+counts.failed+"</span>"
     :counts.passed?'<span class="tf-map-edge-note passed"><i class="fa-solid fa-circle-check" aria-hidden="true"></i>'+counts.passed+"</span>"
     :counts.other?'<span class="tf-map-edge-note">'+counts.other+"</span>":"";
   return side==="left"?arrow+note:note+arrow;
 }
 function edgeTip(counts,side){
   const where=side==="left"?"to the left":"to the right";
   if(counts.failed)return counts.failed+(counts.failed===1?" failing layer ":" failing layers ")+where;
   if(counts.passed)return"Only passing layers "+where;
   return counts.other?counts.other+(counts.other===1?" more layer ":" more layers ")+where:"";
 }
 // Each scroll edge counts the layers it hides, failing first where the page judges them.
 function updateEdges(){
   const view=scroller.getBoundingClientRect(),at=scroller.scrollLeft,max=scroller.scrollWidth-scroller.clientWidth;
   const hidden={left:{failed:0,passed:0,other:0},right:{failed:0,passed:0,other:0}};
   tabs.querySelectorAll("[data-map-layer]").forEach(tab=>{
     if(pinWidth&&tab.closest(".pinned"))return;
     const box=tab.getBoundingClientRect(),middle=box.left+box.width/2-view.left;
     const side=middle<pinWidth?"left":middle>view.width?"right":"";
     if(side)hidden[side][toneOf(tab.dataset.mapLayer)||"other"]++;
   });
   Object.entries(edges).forEach(([side,node])=>{
     const on=side==="left"?at>1:at<max-1,button=node.firstElementChild;
     node.classList.toggle("on",on);
     button.innerHTML=edgeNote(hidden[side],side);
     button.dataset.tip=on?edgeTip(hidden[side],side):"";
   });
 }
 // The All layers table: one row per layer in strip order, one column per contract in tree order.
 function rowHtml(key){
   const label=byKey.get(key)[1],row=o.row(key),selected=key===o.current();
   return'<div class="tf-map-row" role="option" data-map-row="'+key+'" aria-selected="'+selected+'" tabindex="'+(selected?0:-1)+'" aria-label="'+escapeHtml(row.name)+'">'
     +'<span class="tf-map-row-head"><span class="tf-map-row-name">'+label+"</span>"+row.status+'<span class="tf-map-row-count">'+row.count+"</span></span>"
     +'<svg class="tf-map-row-strip" viewBox="0 0 '+o.columns.units+' 16" preserveAspectRatio="none" aria-hidden="true" focusable="false">'+o.cells(key)+"</svg></div>";
 }
 function rowsGroup(group){
   if(!group.keys.length)return"";
   return'<div class="tf-map-rows-group" role="group" aria-label="'+escapeHtml(group.label)+' layers">'
     +'<div class="tf-map-rows-label'+(group.tone?" "+group.tone:"")+'" aria-hidden="true">'+(group.icon?'<i class="fa-solid '+group.icon+'"></i>':"")+escapeHtml(group.label)+" · "+group.keys.length+"</div>"
     +group.keys.map(rowHtml).join("")+"</div>";
 }
 function resetFoot(){
   foot.textContent=FOOT_IDLE;
   rowsBox.querySelector(".tf-map-band")?.classList.remove("visible");
 }
 function renderTable(){
   const[first,...rest]=o.groups();
   rowsBox.innerHTML=first.keys.map(rowHtml).join("")+rest.map(rowsGroup).join("")+'<div class="tf-map-band" aria-hidden="true"></div>';
   resetFoot();
 }
 function openTable(){
   renderTable();
   o.hint.hide();
   table.hidden=false;
   toggle.setAttribute("aria-expanded","true");
   rowsBox.querySelector('[aria-selected="true"]')?.focus({preventScroll:true});
 }
 function closeTable(returnFocus){
   if(table.hidden)return;
   table.hidden=true;
   toggle.setAttribute("aria-expanded","false");
   if(returnFocus)toggle.focus({preventScroll:true});
 }
 // A row opens its layer; a contract cell also opens that contract in it.
 function pick(key,leaf,pointer){
   hold=pointer?{x:pointer.clientX,y:pointer.clientY}:null;
   closeTable(false);
   o.select(key,!leaf);
   if(leaf)o.focus(leaf.row.id);
 }
 // After a pick the view sits under a still pointer: its hover waits until the pointer moves.
 function holds(event){
   if(!hold)return false;
   if(Math.hypot(event.clientX-hold.x,event.clientY-hold.y)<6)return true;
   hold=null;
   return false;
 }
 tabs.addEventListener("click",event=>{const button=event.target.closest("[data-map-layer]");if(button)o.select(button.dataset.mapLayer,false)});
 tabs.addEventListener("keydown",event=>{
   const button=event.target.closest("[data-map-layer]");
   if(!button)return;
   const keys=order(),index=keys.indexOf(button.dataset.mapLayer);
   const next={ArrowRight:index+1,ArrowLeft:index-1,Home:0,End:keys.length-1}[event.key];
   if(next===undefined)return;
   event.preventDefault();
   o.select(keys[(next+keys.length)%keys.length],true);
 });
 scroller.addEventListener("scroll",()=>{o.hint.hide();if(!edgeFrame)edgeFrame=requestAnimationFrame(()=>{edgeFrame=0;updateEdges()})},{passive:true});
 bar.addEventListener("click",event=>{
   const button=event.target.closest("[data-map-scroll]");
   if(button)scroller.scrollBy({left:Number(button.dataset.mapScroll)*Math.max(180,(scroller.clientWidth-pinWidth)*.8),behavior:motion()});
 });
 o.hint.watch(bar,rowsBox);
 toggle.addEventListener("click",()=>{if(table.hidden)openTable();else closeTable(false)});
 table.querySelector(".tf-map-table-close").addEventListener("click",()=>closeTable(true));
 table.addEventListener("focusout",event=>{if(event.relatedTarget&&!table.contains(event.relatedTarget)&&event.relatedTarget!==toggle)closeTable(false)});
 document.addEventListener("pointerdown",event=>{if(!table.hidden&&!table.contains(event.target)&&!toggle.contains(event.target))closeTable(false)});
 document.addEventListener("keydown",event=>{if(event.key==="Escape"&&!table.hidden)closeTable(true)});
 rowsBox.addEventListener("click",event=>{
   const row=event.target.closest("[data-map-row]");
   if(!row)return;
   const cell=event.target.closest("[data-leaf]");
   pick(row.dataset.mapRow,cell?o.columns.leaves[Number(cell.dataset.leaf)]:null,event.detail?event:null);
 });
 rowsBox.addEventListener("keydown",event=>{
   const row=event.target.closest("[data-map-row]");
   if(!row)return;
   if(event.key==="Enter"||event.key===" "){event.preventDefault();pick(row.dataset.mapRow,null);return}
   const list=[...rowsBox.querySelectorAll("[data-map-row]")],index=list.indexOf(row);
   const next={ArrowDown:index+1,ArrowUp:index-1,Home:0,End:list.length-1}[event.key];
   if(next===undefined)return;
   event.preventDefault();
   const target=list[Math.max(0,Math.min(list.length-1,next))];
   list.forEach(item=>{item.tabIndex=item===target?0:-1});
   target.focus();
 });
 rowsBox.addEventListener("pointermove",event=>{
   const strip=rowsBox.querySelector(".tf-map-row-strip"),band=rowsBox.querySelector(".tf-map-band");
   if(!strip||!band)return;
   const box=strip.getBoundingClientRect(),outer=rowsBox.getBoundingClientRect(),units=o.columns.units,unit=(event.clientX-box.left)/box.width*units;
   const leaf=event.clientX>=box.left&&event.clientX<=box.right?o.columns.leaves.find(item=>unit>=item.x-1&&unit<item.x+MAP_CELL+1):null;
   if(!leaf)return resetFoot();
   const scale=box.width/units;
   band.style.left=(box.left-outer.left+leaf.x*scale-1)+"px";
   band.style.width=(MAP_CELL*scale+2)+"px";
   band.classList.add("visible");
   foot.innerHTML="<b>"+escapeHtml(leaf.row.short||leaf.row.label)+"</b> · "+escapeHtml(leaf.row.id)+": "+o.foot(leaf.row);
 });
 rowsBox.addEventListener("pointerleave",resetFoot);
 new ResizeObserver(()=>syncBar()).observe(scroller);
 return{build,sync,show,order,holds,toggleTable:()=>{if(table.hidden)openTable();else closeTable(false)},closeTable};
}
// The treemap both maps draw: goals, capabilities and contracts with the same padding and binary tiling. The page
// width decides every split; a narrower view keeps the splits and only narrows the tiles, so no contract moves to
// another place while the side panel slides in or out. inset is the room a header keeps beside its name.
const PAD={product:[14,0,0],goal:[8,30,8],feature:[5,24,6],cluster:[2,0,0]};
const HEAD_UNITS={goal:1,feature:1.6};
const RADIUS={goal:12,feature:8,leaf:3.5};
function mapTreemap(root,children,inset){
 const build=row=>{
   const kids=children.get(row.id)||[];
   if(row.level==="requirement"&&kids.length)return{kind:"cluster",row,children:[{kind:"leaf",row},...kids.map(child=>({kind:"leaf",row:child}))]};
   if(!kids.length)return{kind:"leaf",row};
   return{kind:row.level,row,children:kids.map(build)};
 };
 const hierarchy=d3.hierarchy(build(root)).sum(node=>node.kind==="leaf"?1:(HEAD_UNITS[node.kind]||0));
 const map={hierarchy,compact:new Set(),tiled:0,width:0,height:0};
 const splits=new Map();
 let squeeze=1,record=false;
 const pad=(node,index)=>(PAD[node.data.kind]||[0,0,0])[index];
 const headerHeight=node=>{const kind=node.data.kind;return(kind==="goal"||kind==="feature")&&map.compact.has(node.data.row.id)?pad(node,2):pad(node,1)};
 map.label=node=>{const goal=node.data.kind==="goal",x=node.x0+(goal?11:9);return fitLabel(node.data.row.short||node.data.row.label,node.x1-x-inset,(goal?"650 13px ":"500 12px ")+family())};
 map.box=node=>({x:node.x0,y:node.y0,width:Math.max(0,node.x1-node.x0),height:Math.max(0,node.y1-node.y0)});
 function binary(key,nodes,value,x0,y0,x1,y1){
   // d3.treemapBinary, except that each split keeps the direction it had at the page width.
   const sums=[0];
   nodes.forEach(node=>sums.push(sums[sums.length-1]+node.value));
   (function part(i,j,total,x0,y0,x1,y1){
     if(i>=j-1){Object.assign(nodes[i],{x0,y0,x1,y1});return}
     const offset=sums[i],target=total/2+offset;
     let k=i+1,hi=j-1;
     while(k<hi){const mid=k+hi>>>1;if(sums[mid]<target)k=mid+1;else hi=mid}
     if(target-sums[k-1]<sums[k]-target&&i+1<k)--k;
     const left=sums[k]-offset,right=total-left,id=key+":"+i+":"+j;
     let wide=splits.get(id);
     if(record||wide===undefined){wide=(x1-x0)/squeeze>y1-y0;splits.set(id,wide)}
     if(wide){const xk=total?(x0*right+x1*left)/total:x1;part(i,k,left,x0,y0,xk,y1);part(k,j,right,xk,y0,x1,y1)}
     else{const yk=total?(y0*right+y1*left)/total:y1;part(i,k,left,x0,y0,x1,yk);part(k,j,right,x0,yk,x1,y1)}
   })(0,nodes.length,value,x0,y0,x1,y1);
 }
 function tile(parent,x0,y0,x1,y1){
   const kids=parent.children,total=kids.reduce((sum,child)=>sum+child.value,0),key=parent.data.row.id;
   if(parent.data.kind!=="cluster")return binary(key,kids,total,x0,y0,x1,y1);
   const[self,...rest]=kids,split=x0+(x1-x0)*self.value/total;
   Object.assign(self,{x0,y0,x1:split,y1});
   if(rest.length)binary(key+"+",rest,total-self.value,split,y0,x1,y1);
 }
 const compute=width=>d3.treemap().size([width,map.height]).tile(tile).paddingInner(node=>pad(node,0)).paddingTop(headerHeight).paddingRight(node=>pad(node,2)).paddingBottom(node=>pad(node,2)).paddingLeft(node=>pad(node,2))(hierarchy);
 // "retile" when the page width or the height changed (the page draws its shapes again), "squeeze" when only the
 // view's own width changed (the page moves the shapes it has), "" when nothing changed.
 map.layout=(page,height,width,force)=>{
   if(!page||!height||!width)return"";
   const retile=force||page!==map.tiled||height!==map.height;
   if(!retile&&width===map.width)return"";
   if(retile){
     map.tiled=page;map.height=height;squeeze=1;record=true;splits.clear();map.compact.clear();
     compute(page);
     hierarchy.each(node=>{const kind=node.data.kind;if(kind!=="goal"&&kind!=="feature")return;const room=node.y1-node.y0-pad(node,1)-pad(node,2);if(!map.label(node)||room<(kind==="goal"?40:22))map.compact.add(node.data.row.id)});
     if(map.compact.size)compute(page);
     record=false;
     hierarchy.each(node=>{node.page=[node.x0,node.y0,node.x1,node.y1]});
   }
   map.width=width;squeeze=width/map.tiled;
   if(!retile||width!==map.tiled)compute(width);
   return retile?"retile":"squeeze";
 };
 // Card thumbnails show the page-width tiling, so a card never changes while the panel opens.
 map.thumb=draw=>{
   if(!map.tiled)return'<svg class="tf-map-thumb" viewBox="0 0 76 29" aria-hidden="true" focusable="false"></svg>';
   let out="";
   hierarchy.eachBefore(node=>{if(node.page){const[x0,y0,x1,y1]=node.page;out+=draw(node,'x="'+fixed(x0)+'" y="'+fixed(y0)+'" width="'+fixed(Math.max(0,x1-x0))+'" height="'+fixed(Math.max(0,y1-y0))+'"')||""}});
   return'<svg class="tf-map-thumb" viewBox="0 0 '+map.tiled+" "+map.height+'" aria-hidden="true" focusable="false">'+out+"</svg>";
 };
 return map;
}
// The treemap view both maps draw: one link per goal, capability and contract with its shape and its name, in tree
// order. A new tiling draws them again; a narrower view only moves them, so hover and focus stay put.
//   dots: goals and capabilities carry a dot before their name (the Health Map's own verdict); bind(entry); drawn()
function mapTiles(svg,tree,o){
 const map=mapTreemap(tree.root,tree.children,o.dots?21:10);
 const tiles={svg,map,entries:[],byId:new Map(),outline:null};
 function draw(){
   svg.replaceChildren();
   tiles.entries=[];tiles.byId=new Map();
   map.hierarchy.eachBefore(node=>{
     const kind=node.data.kind,row=node.data.row;
     if(kind!=="goal"&&kind!=="feature"&&kind!=="leaf")return;
     const link=el("a",{},svg);
     const shape=el("rect",{rx:RADIUS[kind],class:kind==="leaf"?"tf-map-tile":"tf-map-"+kind},link);
     const named=kind!=="leaf"&&!map.compact.has(row.id);
     const dot=named&&o.dots?el("circle",{r:kind==="goal"?4:3.5,class:"tf-map-dot"},link):null;
     const label=named?el("text",{class:"tf-map-label-"+kind},link):null;
     const entry={row,kind,node,area:null,link,shape,anchor:shape,dot,label};
     tiles.entries.push(entry);
     tiles.byId.set(row.id,entry);
     o.bind(entry);
   });
   tiles.outline=mapOutline(svg);
   place();
   o.drawn();
 }
 // Moves the drawn shapes to the current layout without replacing them.
 function place(){
   svg.setAttribute("viewBox","0 0 "+map.width+" "+map.height);
   tiles.entries.forEach(entry=>{
     const node=entry.node,area=map.box(node);
     entry.area=area;
     for(const key in area)entry.shape.setAttribute(key,fixed(area[key]));
     if(!entry.label)return;
     const goal=entry.kind==="goal",x=node.x0+(goal?11:9),y=node.y0+(goal?19.5:16.5);
     if(entry.dot){entry.dot.setAttribute("cx",fixed(x+3.5));entry.dot.setAttribute("cy",fixed(y-4.3))}
     entry.label.setAttribute("x",fixed(entry.dot?x+12:x));entry.label.setAttribute("y",fixed(y));
     entry.label.textContent=map.label(node);
   });
   if(tiles.outline.entry)tiles.outline.move(tiles.outline.entry,true);
 }
 // True when the shapes were drawn again.
 tiles.layout=(frame,force)=>{
   const change=map.layout(frame.pageWidth,frame.viewH,frame.stageWidth(),force);
   if(change==="retile")draw();else if(change==="squeeze")place();
   return change==="retile";
 };
 // A card's mini-map in one layer's colours. leaf(row): the tile's attributes; mark(row): the class of a goal or
 // capability that fails its own check.
 tiles.thumb=(leaf,mark)=>map.thumb((node,geometry)=>{
   const kind=node.data.kind,row=node.data.row,extra=mark?.(row)||"";
   if(kind==="goal")return"<rect "+geometry+' rx="14" class="tf-map-goal'+(extra?" "+extra:"")+'" vector-effect="non-scaling-stroke"/>';
   if(kind==="feature"&&extra)return"<rect "+geometry+' rx="10" fill="none" class="'+extra+'" vector-effect="non-scaling-stroke"/>';
   if(kind==="leaf")return"<rect "+geometry+" "+leaf(row)+"/>";
 });
 return tiles;
}
// The rings of both maps follow the height and sit in the middle, so a narrower view only moves them; the goal
// names beside them show while there is room.
const LABEL_ROOM=100;
const mapRingFrame=(w,h)=>{const outer=Math.max(90,Math.min(h/2-20,w/2-8));return{cx:w/2,cy:h/2,outer,room:w/2-outer-46}};
// Goal names in two aligned columns beside the rings; each belongs to its goal's link, dot included.
function mapGoalLabels(goals,outer,height,room,enter,dotClass){
 const column=outer+32,spacing=18;
 const items=goals.map(entry=>{const angle=(entry.angles[0]+entry.angles[1])/2;return{entry,angle,side:Math.sin(angle)>=0?1:-1,y:-(outer+14)*Math.cos(angle)}});
 [1,-1].forEach(side=>{
   const list=items.filter(item=>item.side===side).sort((a,b)=>a.y-b.y);
   list.forEach((item,index)=>{if(index)item.y=Math.max(item.y,list[index-1].y+spacing)});
   let limit=height/2-10;
   for(let index=list.length-1;index>=0;index--){list[index].y=Math.min(list[index].y,limit);limit=list[index].y-spacing}
 });
 items.forEach(item=>{
   const x=item.side*column,p0=polar(0,0,outer+4,item.angle),p1=polar(0,0,outer+14,item.angle);
   // A name that appears after the panel closes fades in; one that was already there stays still.
   const group=el("g",{class:"tf-map-goal-label"+(enter?" enter":"")},item.entry.link);
   el("polyline",{points:fixed(p0[0])+","+fixed(p0[1])+" "+fixed(p1[0])+","+fixed(p1[1])+" "+fixed(x-item.side*7)+","+fixed(item.y),class:"tf-map-leader"},group);
   el("circle",{cx:fixed(x),cy:fixed(item.y),r:3.5,class:dotClass(item.entry.row)},group);
   const label=fitLabel(item.entry.row.short||item.entry.row.label,room,"650 13px "+family());
   if(label)el("text",{x:fixed(x+item.side*9),y:fixed(item.y+4.4),"text-anchor":item.side>0?"start":"end",class:"tf-map-goal-name"},group).textContent=label;
 });
}
// The rings view both maps draw. The core is the same on both: the centre, then goals, then capabilities; each
// contract is one ray from there to the edge through the page's own rings. Radii are shares of the outer radius.
//   bands(outer): the page's rings, with names [{labels,band,cls,key,aria,tip}] (a key opens that layer) and
//     gap [radius,room]: the innermost named ring and the half width its names need at twelve o'clock
//   centre(): {href,label,cls,kicker,big,tone,small}; container(row): the class a goal or capability arc adds
//   ray(link,row,a0,a1,geometry): draws a contract's ray and returns the shape its card sits beside
//   after(body,geometry,rings): what the page draws over the rays; rayThumb(row,a0,a1,geometry): the card's version
//   dot(row): the class a goal name's dot adds (the Health Map's verdict); href(row), aria(row), bind(entry), drawn()
const RING_CORE={center:.27,goal:[.29,.355],feature:[.365,.425],rays:.44};
const mapRingGap=(radius,room)=>Math.min(.95,Math.max(.46,2*Math.asin(Math.min(1,room/Math.max(1,radius)))));
const circlePath=r=>"M"+fixed(-r)+",0a"+fixed(r)+","+fixed(r)+" 0 1,0 "+fixed(2*r)+",0a"+fixed(r)+","+fixed(r)+" 0 1,0 "+fixed(-2*r)+",0";
function mapRings(svg,tree,o){
 const columns=tree.columns;
 const rings={svg,entries:[],byId:new Map(),bands:new Map(),geometry:null,gap:.5,arc:null};
 let width=0,height=0,outer=0,body=null;
 const coreAt=radius=>({center:RING_CORE.center*radius,goal:RING_CORE.goal.map(share=>share*radius),feature:RING_CORE.feature.map(share=>share*radius),rays:RING_CORE.rays*radius});
 rings.angleAt=(unit,gap=rings.gap)=>gap/2+unit/columns.units*(2*Math.PI-gap);
 rings.add=entry=>{entry.radial=true;rings.entries.push(entry);if(!entry.layer)rings.byId.set(entry.row.id,entry);o.bind(entry);return entry};
 // The centre says what the Overall card says; its kicker and small line need room.
 function centre(core){
   const c=o.centre(),link=el("a",{href:c.href,"aria-label":c.label},body);
   const disc=el("circle",{cx:0,cy:0,r:fixed(core.center),class:"tf-map-ring-center"+(c.cls?" "+c.cls:"")},link);
   let size=Math.max(14,Math.min(32,core.center*.4));
   measure.font="800 "+size+"px "+family();
   size=Math.min(size,size*1.6*core.center/Math.max(1,measure.measureText(c.big).width));
   const roomy=core.center>=40;
   if(roomy)el("text",{x:0,y:fixed(-size*.95),class:"tf-map-ring-kicker"},link).textContent=c.kicker;
   el("text",{x:0,y:fixed(size*.36),"font-size":fixed(size),class:"tf-map-ring-big"+(c.tone?" "+c.tone:"")},link).textContent=c.big;
   if(roomy)el("text",{x:0,y:fixed(size*.36+16),class:"tf-map-ring-small"},link).textContent=c.small;
   rings.add({row:tree.root,kind:"product",link,shape:disc,anchor:disc,band:[0,core.center]});
 }
 // Ring names sit in the open gap at twelve o'clock; a shorter name is used where the long one does not fit.
 function name(item){
   const radius=(item.band[0]+item.band[1])/2,room=2*radius*Math.sin(rings.gap/2)-6,font="650 9.5px "+family();
   measure.font=font;
   const fitted=item.labels.find(label=>measure.measureText(label).width<=room)||fitLabel(item.labels[item.labels.length-1],room,font);
   if(!fitted)return;
   const node=el("text",{x:0,y:fixed(-radius+3.4),class:"tf-map-ring-name"+(item.cls?" "+item.cls:"")},body);
   node.textContent=fitted;
   if(!item.key)return;
   rings.bands.set(item.key,item.band);
   for(const[key,value]of Object.entries({"data-map-ring":item.key,tabindex:"0",role:"button","aria-label":item.aria,"data-tip":item.tip}))node.setAttribute(key,value);
 }
 rings.draw=(frame,force)=>{
   const w=frame.stageWidth(),h=frame.viewH;
   if(!w||!h||(!force&&w===width&&h===height))return false;
   const hadLabels=!!svg.querySelector(".tf-map-goal-label");
   width=w;height=h;
   svg.replaceChildren();
   rings.entries=[];rings.byId=new Map();rings.bands=new Map();
   svg.setAttribute("viewBox","0 0 "+w+" "+h);
   svg.classList.remove("tf-map-nolabels");
   const place=mapRingFrame(w,h),core=coreAt(place.outer),bands=o.bands(place.outer);
   outer=place.outer;
   rings.gap=mapRingGap(...bands.gap);
   rings.geometry={outer,core,bands};
   body=el("g",{transform:"translate("+fixed(place.cx)+","+fixed(place.cy)+")"},svg);
   centre(core);
   // Goals, capabilities and contracts in tree order, so keyboard focus walks the tree.
   const leafAt=new Map(columns.leaves.map(leaf=>[leaf.row.id,leaf])),groupAt=new Map(columns.groups.map(group=>[group.row.id,group])),goals=[];
   const walk=row=>{
     const group=groupAt.get(row.id),leaf=leafAt.get(row.id);
     if(group&&group.end>group.start){
       const kind=row.level==="goal"?"goal":"feature",band=core[kind],angles=[rings.angleAt(group.start),rings.angleAt(group.end)],extra=o.container?.(row)||"";
       const link=el("a",{href:o.href(row),"aria-label":o.aria(row)},body);
       const shape=el("path",{d:arcPath(0,0,band[0],band[1],angles[0],angles[1]),class:"tf-map-"+kind+(extra?" "+extra:"")},link);
       const entry=rings.add({row,kind,link,shape,anchor:shape,band,angles});
       if(kind==="goal")goals.push(entry);
     }else if(leaf){
       const angles=[rings.angleAt(leaf.x+.8),rings.angleAt(leaf.x+MAP_CELL-.8)];
       const link=el("a",{href:o.href(row),"aria-label":o.aria(row)},body);
       const shape=o.ray(link,row,angles[0],angles[1],rings.geometry);
       rings.add({row,kind:"leaf",link,shape,anchor:shape,angles});
     }
     (tree.children.get(row.id)||[]).forEach(walk);
   };
   (tree.children.get(tree.root.id)||[]).forEach(walk);
   o.after?.(body,rings.geometry,rings);
   bands.names.forEach(name);
   if(place.room>=LABEL_ROOM)mapGoalLabels(goals,outer,h,place.room,!hadLabels,row=>"tf-map-dot"+(o.dot?" "+o.dot(row):""));
   rings.arc=el("path",{class:"tf-map-arc",d:""},body);
   o.drawn();
   return true;
 };
 // While the view changes width the rings only move, and shrink only if the width limits them.
 rings.squeeze=w=>{
   if(!body||!height)return;
   const place=mapRingFrame(w,height),scale=place.outer/outer;
   svg.setAttribute("viewBox","0 0 "+w+" "+height);
   body.setAttribute("transform","translate("+fixed(place.cx)+","+fixed(place.cy)+")"+(Math.abs(scale-1)>.001?" scale("+scale.toFixed(4)+")":""));
   svg.classList.toggle("tf-map-nolabels",place.room<LABEL_ROOM);
 };
 // Hover: a contract lights its whole ray, a goal or capability its arc, the centre its disc; a ring name its ring.
 rings.highlight=entry=>{
   const{core}=rings.geometry,[a0,a1]=entry.angles||[0,0];
   rings.arc.setAttribute("d",entry.kind==="product"?circlePath(core.center+1.5)
     :entry.kind==="leaf"||entry.kind==="track"?arcPath(0,0,core.rays-1.5,outer+1.5,a0-.004,a1+.004)
     :arcPath(0,0,entry.band[0]-1.5,entry.band[1]+1.5,a0-.004,a1+.004));
   rings.arc.classList.add("visible");
 };
 rings.showBand=key=>{
   const band=rings.bands.get(key);
   if(!band||!rings.arc)return;
   rings.arc.setAttribute("d",arcPath(0,0,band[0]-1.5,band[1]+1.5,rings.angleAt(0)-.01,rings.angleAt(columns.units)+.01));
   rings.arc.classList.add("visible");
 };
 rings.clear=()=>rings.arc?.classList.remove("visible");
 // The Overall card's mini-map: the same rings, small.
 rings.thumb=()=>{
   const radius=48,core=coreAt(radius),geometry={outer:radius,core,bands:o.bands(radius)},angle=unit=>rings.angleAt(unit,.4);
   let out='<circle cx="0" cy="0" r="'+fixed(core.center)+'" class="tf-map-ring-center"/>';
   columns.groups.forEach(group=>{
     if(group.end<=group.start)return;
     const kind=group.row.level==="goal"?"goal":"feature",extra=o.container?.(group.row)||"";
     out+='<path d="'+arcPath(0,0,core[kind][0],core[kind][1],angle(group.start),angle(group.end))+'" class="tf-map-'+kind+(extra?" "+extra:"")+'"/>';
   });
   columns.leaves.forEach(leaf=>{out+=o.rayThumb(leaf.row,angle(leaf.x+.8),angle(leaf.x+MAP_CELL-.8),geometry)});
   return'<svg class="tf-map-thumb radial" viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">'+out+"</svg>";
 };
 return rings;
}
// The view frame both maps share: a legend bar that keeps the height of its tallest view, the side panel and the
// stage below it, one height for every view (the rest of the first screen), and a stage that follows its own width
// frame by frame while the panel slides, then settles.
//   views, legend(key), modes(key): the views, what each one's legend says, whether it shows Rings/Table
//   longest(): the widest count text; layout(force), follow(width): the page's drawing
function mapFrame(o){
 const $=id=>document.getElementById(id);
 const body=$("tf-map-body"),stage=$("tf-map-stage"),legend=$("tf-map-legend"),count=$("tf-map-total"),modeBox=$("tf-map-mode");
 const frame={pageWidth:0,viewH:0,body,stage,legend,modeBox};
 let settle=0;
 frame.stageWidth=()=>Math.round(stage.getBoundingClientRect().width);
 // Every view has one height: the rest of the first screen below the legend. The panel, a filter or another view never changes it.
 const firstScreen=()=>Math.round(innerHeight-(body.getBoundingClientRect().top+scrollY)-20);
 const heightFor=width=>Math.round(width<600?Math.min(600,Math.max(320,width)):Math.min(760,Math.max(440,Math.min(width*.8,firstScreen()))));
 function fitLegend(){
   // The legend keeps the height of its tallest view (with the longest count beside it), so switching views never
   // moves Rings/Table, the count or anything below them.
   const saved=[legend.innerHTML,count.innerHTML];
   legend.style.minHeight="";
   count.innerHTML=o.longest();
   let tallest=0;
   o.views.forEach(key=>{legend.innerHTML=o.legend(key,true);tallest=Math.max(tallest,legend.getBoundingClientRect().height)});
   [legend.innerHTML,count.innerHTML]=saved;
   legend.style.minHeight=Math.ceil(tallest)+"px";
 }
 frame.layout=force=>{
   const page=Math.round(body.getBoundingClientRect().width);
   if(!page)return;
   if(force||page!==frame.pageWidth){frame.pageWidth=page;fitLegend()}
   frame.viewH=heightFor(frame.pageWidth);
   body.style.setProperty("--tf-map-view-h",frame.viewH+"px");
   o.layout(force);
 };
 // Rings or Table: the Overall layer's two views. The switch keeps its place in every view, so nothing beside it moves.
 frame.showMode=view=>{
   const on=o.modes(view);
   modeBox.classList.toggle("off",!on);
   modeBox.setAttribute("aria-hidden",String(!on));
   modeBox.querySelectorAll("[data-mode]").forEach(button=>{button.setAttribute("aria-pressed",String(button.dataset.mode===view));button.tabIndex=on?0:-1});
 };
 modeBox.addEventListener("click",event=>{const button=event.target.closest("[data-mode]");if(button)o.mode(button.dataset.mode)});
 new ResizeObserver(()=>{o.follow(frame.stageWidth());clearTimeout(settle);settle=setTimeout(()=>frame.layout(false),160)}).observe(stage);
 addEventListener("resize",()=>{clearTimeout(settle);settle=setTimeout(()=>frame.layout(false),160)});
 return frame;
}
// Filters: OR inside a facet, AND across facets; every view reads the same set, the table too. A facet is
// {label, options or name and valid, test(row,value), swatch(value), tip(value), keepEmpty(value), title, help,
// empty, pipe, panel()}. The side panel follows the view and shows only the facets that fit it, so pointing at an
// option always lights something; the table previews nothing and a click filters it.
//   rows: what the filters keep or dim; leaves: what the count counts; view(), panel(view), previews(view)
//   changed(): the page redraws what depends on the filters; mark(row,panel): page marks for a hovered contract
function mapFilters(o){
 const $=id=>document.getElementById(id);
 const facets=o.facets;
 Object.values(facets).forEach(facet=>{if(facet.options){const names=new Map(facet.options);facet.name=value=>names.get(value)||value;facet.valid=value=>names.has(value)}});
 const sets=Object.fromEntries(Object.keys(facets).map(key=>[key,new Set()]));
 const f={sets,preview:null,open:false};
 f.matches=(row,skip)=>{
   for(const key in sets){
     if(key===skip||!sets[key].size)continue;
     let hit=false;
     for(const value of sets[key])if(facets[key].test(row,value)){hit=true;break}
     if(!hit)return false;
   }
   return true;
 };
 f.active=()=>Object.values(sets).reduce((sum,set)=>sum+set.size,0);
 f.shown=withPreview=>{
   if(!f.active()&&!(withPreview&&f.preview))return null;
   const preview=withPreview&&f.preview;
   return new Set(o.rows.filter(row=>f.matches(row)&&(!preview||facets[preview.facet].test(row,preview.value))).map(row=>row.id));
 };
 const lead=$("tf-map-lead"),box=$("tf-map-filters"),chips=$("tf-map-chips"),badge=$("tf-map-filter-badge"),count=$("tf-map-total");
 const body=$("tf-map-body"),panel=$("tf-map-panel"),toggleButton=$("tf-map-panel-toggle"),panelBody=$("tf-map-panel-body");
 const help=text=>' <span class="tf-map-help" aria-hidden="true" data-tip="'+escapeHtml(text)+'">?</span>';
 const counted=o.leaves.length;
 f.longest=()=>"<b>"+counted+"</b> of "+counted+" contracts";
 // Chips in place of the run stamp, the badge on Filters and the count above the view.
 f.render=()=>{
   const list=[];
   for(const key in sets)for(const value of sets[key]){
     const text=facets[key].label+": "+facets[key].name(value);
     list.push('<button type="button" class="tf-map-chip" data-facet="'+key+'" data-value="'+escapeHtml(value)+'" aria-label="Remove filter '+escapeHtml(text)+'">'+escapeHtml(text)+'<i class="fa-solid fa-xmark" aria-hidden="true"></i></button>');
   }
   lead.classList.toggle("filtered",list.length>0);
   box.hidden=!list.length;
   chips.innerHTML=list.join("");
   const shown=f.shown(false);
   count.innerHTML=shown?"<b>"+o.leaves.filter(row=>shown.has(row.id)).length+"</b> of "+counted+" contracts":"<b>"+counted+"</b> contracts";
   badge.hidden=!list.length;
   badge.textContent=list.length;
 };
 f.options=key=>{
   const facet=facets[key];
   return facet.options.map(([value,label])=>{
     const found=o.rows.filter(row=>f.matches(row,key)&&facet.test(row,value)).length,pressed=sets[key].has(value);
     // An empty option stays (disabled) where it shows a ceiling; otherwise it is left out.
     if(!pressed&&!facet.keepEmpty?.(value)&&!o.rows.some(row=>facet.test(row,value)))return"";
     return'<button type="button" class="tf-map-option" data-facet="'+key+'" data-value="'+escapeHtml(value)+'" aria-pressed="'+pressed+'"'+(found||pressed?"":" disabled")
       +(facet.tip?' data-tip="'+escapeHtml(facet.tip(value))+'"':"")+">"+(facet.swatch?.(value)||"")+escapeHtml(label)+" <b>"+found+"</b></button>";
   }).join("");
 };
 f.renderPanel=fresh=>{
   if(!f.open)return;
   const view=o.view(),config=o.panel(view);
   // The same control keeps keyboard focus when the panel redraws after a click.
   const active=panel.contains(document.activeElement)?document.activeElement:null;
   const again=active?.dataset.facet?'[data-facet="'+active.dataset.facet+'"][data-value="'+CSS.escape(active.dataset.value)+'"]':"";
   $("tf-map-panel-title").innerHTML=escapeHtml(config.title)+help(config.help);
   let html=config.before?config.before():"";
   config.facets.forEach((key,index)=>{
     // The view's own facet needs no second title: the panel title already names it.
     const facet=facets[key],own=!config.before&&index===0;
     const title=own?"":'<div class="tf-map-facet-title">'+escapeHtml(facet.title||facet.label)+(facet.help?help(facet.help):"")+"</div>";
     const inner=facet.panel?facet.panel():facet.options.length?'<div class="tf-map-options">'+f.options(key)+"</div>":'<p class="tf-map-facet-empty">'+escapeHtml(facet.empty||"Nothing here.")+"</p>";
     html+='<div class="tf-map-facet'+(own?" own":"")+'">'+title+inner+"</div>";
   });
   panelBody.innerHTML=html;
   if(again)panelBody.querySelector(again)?.focus({preventScroll:true});
   // Another view brings other controls: they fade in from the top instead of popping in.
   if(fresh){panel.scrollTop=0;panelBody.classList.remove("tf-map-fresh");void panelBody.offsetWidth;panelBody.classList.add("tf-map-fresh")}
 };
 // Pointing at a mark marks what it belongs to in the panel; what the filters do not hold marks nothing.
 const held=new Set(o.rows.map(row=>row.id));
 f.mark=row=>{
   if(!f.open)return;
   if(row&&!held.has(row.id))row=null;
   o.mark?.(row,panel);
   panel.querySelectorAll("button[data-facet]").forEach(node=>node.classList.toggle("hit",!!row&&facets[node.dataset.facet].test(row,node.dataset.value)));
 };
 f.setPanel=(open,persist)=>{
   f.open=open;
   o.hideTip();
   body.classList.toggle("panel-open",open);
   panel.inert=!open;
   toggleButton.setAttribute("aria-expanded",String(open));
   if(open)f.renderPanel(false);
   if(persist)try{localStorage.setItem("tf-map-panel",open?"1":"0")}catch(error){}
 };
 const changed=()=>{f.preview=null;f.render();f.renderPanel(false);o.changed()};
 f.toggle=(key,value)=>{const set=sets[key];if(set.has(value))set.delete(value);else set.add(value);changed()};
 f.clear=()=>{Object.values(sets).forEach(set=>set.clear());changed()};
 // The address keeps the filters: facet=value,value.
 f.write=params=>{for(const key in sets)if(sets[key].size)params.set(key,[...sets[key]].map(value=>facets[key].pipe?value.replace("|","."):value).join(","))};
 f.read=params=>{
   Object.values(sets).forEach(set=>set.clear());
   for(const key in facets){
     const value=params.get(key);
     if(!value)continue;
     value.split(",").map(item=>facets[key].pipe?item.replace(".","|"):item).filter(item=>facets[key].valid(item)).forEach(item=>sets[key].add(item));
   }
   f.render();f.renderPanel(false);
 };
 box.addEventListener("click",event=>{
   if(event.target.closest("[data-clear]")){f.clear();return}
   const chip=event.target.closest(".tf-map-chip");
   if(chip)f.toggle(chip.dataset.facet,chip.dataset.value);
 });
 toggleButton.addEventListener("click",()=>f.setPanel(!f.open,true));
 $("tf-map-panel-close").addEventListener("click",()=>{f.setPanel(false,true);toggleButton.focus({preventScroll:true})});
 // An option, a matrix cell or a substitute: every control in the panel is a facet and a value.
 panel.addEventListener("click",event=>{
   const target=event.target.closest("button[data-facet]:not(:disabled)");
   if(target)f.toggle(target.dataset.facet,target.dataset.value);
 });
 panel.addEventListener("pointerover",event=>{
   if(!o.previews(o.view()))return;
   const target=event.target.closest("button[data-facet]:not(:disabled)");
   const next=target?{facet:target.dataset.facet,value:target.dataset.value}:null;
   if(JSON.stringify(next)===JSON.stringify(f.preview))return;
   f.preview=next;
   o.previewed();
 });
 panel.addEventListener("pointerleave",()=>{if(f.preview){f.preview=null;o.previewed()}});
 let startOpen=false;
 try{startOpen=localStorage.getItem("tf-map-panel")==="1"}catch(error){}
 f.startOpen=startOpen;
 return f;
}
// The matrix of Overall's panel on both maps. A cell counts the marks it holds with the filters (and of how many
// without them); pointing at it lights them, a click keeps only them. Its lines depend on the unfiltered cell, so a
// filter changes the numbers but never the height.
//   label, template: the grid's name and columns; columns [{label,swatch,void,title}]; rows [{label,small,void}]
//   cell(row,column): {facet,value,pressed,hits,all,fill,tip,lines,extra}, or {empty:true,title,mark,void}
function mapMatrix(o){
 let html="<span></span>"+o.columns.map(column=>'<span class="tf-map-mx-h'+(column.void?" void":"")+'"'+(column.title?' title="'+escapeHtml(column.title)+'"':"")+">"+column.swatch+(column.void?"":column.label)+"</span>").join("");
 o.rows.forEach(row=>{
   html+='<span class="tf-map-mx-r'+(row.void?" void":"")+'">'+row.label+"<small>"+row.small+"</small></span>";
   o.columns.forEach(column=>{
     const cell=o.cell(row,column);
     if(cell.empty){html+='<span class="tf-map-mx-cell empty'+(cell.void?" void":"")+'" title="'+escapeHtml(cell.title)+'">'+(cell.mark||"")+"</span>";return}
     html+='<button type="button" class="tf-map-mx-cell" data-facet="'+cell.facet+'" data-value="'+escapeHtml(cell.value)+'" aria-pressed="'+cell.pressed+'"'+(cell.hits||cell.pressed?"":" disabled")+' style="--fill:'+cell.fill+'" data-tip="'+escapeHtml(cell.tip)+'" aria-label="'+escapeHtml(cell.tip)+'">'
       +"<b>"+cell.hits+(cell.hits!==cell.all?"<span>of "+cell.all+"</span>":"")+"</b>"+cell.lines.map(line=>"<small>"+line+"</small>").join("")+(cell.extra||"")+"</button>";
   });
 });
 return'<div class="tf-map-mx" role="group" aria-label="'+escapeHtml(o.label)+'" style="grid-template-columns:'+o.template+'">'+html+"</div>";
}
// The contracts table, the Overall layer's second view: every contract in one table that the filters narrow and
// that groups, sorts and downloads. The page names its columns, its groups and what a row says.
//   rows(): the contracts the filters keep, in tree order; tree: goals, features(goal), inside(feature)
//   columns [[key,label,tip,class]]; groups [[key,label]], the first one is tree; keys(row), name(key), order(keys)
//   sortValue(row,key), stats(list), cells(row), href(row), csv: {file, head, line(row)}, height(), changed()
function mapTable(o){
 const $=id=>document.getElementById(id);
 const view=$("tf-map-list-view"),box=$("tf-map-list"),groupBox=$("tf-map-group-by"),summary=$("tf-map-summary");
 const t={group:o.groups[0][0],sort:{key:"",dir:1}};
 const syncGroups=()=>groupBox.querySelectorAll("[data-group]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.group===t.group)));
 groupBox.innerHTML=o.groups.map(([key,label])=>'<button type="button" data-group="'+key+'" aria-pressed="'+(key===t.group)+'">'+label+"</button>").join("");
 const sorted=list=>!t.sort.key?list:[...list].sort((a,b)=>{const x=o.sortValue(a,t.sort.key),y=o.sortValue(b,t.sort.key);return(x<y?-1:x>y?1:0)*t.sort.dir||a.label.localeCompare(b.label)});
 const rowHtml=row=>'<tr class="tf-map-list-row '+row.level+'" data-id="'+row.id+'"><td class="name"><a href="'+escapeHtml(o.href(row))+'">'+escapeHtml(row.short||row.label)+"</a><small>"+row.id+"</small></td>"+o.cells(row)+"</tr>";
 const groupRow=(name,list,sub)=>'<tr class="tf-map-list-group'+(sub?" sub":"")+'"><td colspan="'+o.columns.length+'"><span class="tf-map-list-group-name">'+escapeHtml(name)+'</span><span class="tf-map-list-group-stats">'+o.stats(list)+"</span></td></tr>";
 t.render=()=>{
   const visible=o.rows();
   summary.textContent=visible.length?o.stats(visible):"";
   summary.title=summary.textContent;
   const header="<tr>"+o.columns.map(([key,label,tip,cls])=>'<th class="'+(cls||"")+'" title="'+escapeHtml(tip||label)+'"><button type="button" data-sort="'+key+'">'+label+'<span class="dir">'+(t.sort.key===key?(t.sort.dir>0?"▲":"▼"):"")+"</span></button></th>").join("")+"</tr>";
   let html="";
   if(!visible.length)html='<tr><td colspan="'+o.columns.length+'" class="tf-map-list-empty">No contract matches the filters.</td></tr>';
   else if(t.group==="tree"){
     o.tree.goals.forEach(goal=>{
       const inGoal=visible.filter(row=>o.tree.goalOf(row)===goal.id);
       if(!inGoal.length)return;
       html+=groupRow(goal.short||goal.label,inGoal,false);
       const covered=new Set();
       o.tree.features(goal).forEach(feature=>{
         const ids=o.tree.inside(feature),inFeature=inGoal.filter(row=>ids.has(row.id));
         inFeature.forEach(row=>covered.add(row.id));
         if(!inFeature.length)return;
         html+=groupRow(feature.short||feature.label,inFeature,true)+sorted(inFeature).map(rowHtml).join("");
       });
       const rest=inGoal.filter(row=>!covered.has(row.id));
       if(rest.length)html+=sorted(rest).map(rowHtml).join("");
     });
   }else if(t.group==="none")html=sorted(visible).map(rowHtml).join("");
   else{
     const buckets=new Map();
     visible.forEach(row=>o.keys(row,t.group).forEach(key=>{if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(row)}));
     o.order(t.group,[...buckets.keys()]).forEach(key=>{const list=buckets.get(key);html+=groupRow(o.name(t.group,key),list,false)+sorted(list).map(rowHtml).join("")});
   }
   box.innerHTML='<table class="tf-map-list-table"><thead>'+header+"</thead><tbody>"+html+"</tbody></table>";
   t.fit();
 };
 // The table fills the same height as the other views: its own bar first, then the rows.
 t.fit=()=>{
   if(view.hidden||!o.height())return;
   const bar=view.firstElementChild.getBoundingClientRect().height+8;
   box.style.height=Math.max(200,o.height()-bar)+"px";
 };
 t.row=id=>box.querySelector('tr[data-id="'+id+'"]');
 t.csv=()=>{
   const quote=value=>{const text=String(value??"");return/[",\n]/.test(text)?'"'+text.replace(/"/g,'""')+'"':text};
   const blob=new Blob([[o.csv.head.join(","),...o.rows().map(row=>o.csv.line(row).map(quote).join(","))].join("\n")+"\n"],{type:"text/csv"});
   const link=document.createElement("a");
   link.href=URL.createObjectURL(blob);link.download=o.csv.file;
   document.body.appendChild(link);link.click();link.remove();
   setTimeout(()=>URL.revokeObjectURL(link.href),1000);
 };
 t.write=params=>{
   if(t.group!==o.groups[0][0])params.set("group",t.group);
   if(t.sort.key)params.set("sort",t.sort.key+(t.sort.dir<0?"-desc":""));
 };
 t.read=params=>{
   const requested=params.get("group");
   t.group=o.groups.some(item=>item[0]===requested)?requested:o.groups[0][0];
   const order=params.get("sort");
   t.sort={key:"",dir:1};
   if(order){const[key,direction]=order.split("-");if(o.columns.some(item=>item[0]===key))t.sort={key,dir:direction==="desc"?-1:1}}
   syncGroups();
 };
 groupBox.addEventListener("click",event=>{
   const button=event.target.closest("[data-group]");
   if(!button)return;
   t.group=button.dataset.group;
   syncGroups();t.render();o.changed();
 });
 box.addEventListener("click",event=>{
   const header=event.target.closest("[data-sort]");
   if(header){const key=header.dataset.sort;t.sort=t.sort.key===key?{key,dir:-t.sort.dir}:{key,dir:key==="name"?1:-1};t.render();o.changed();return}
   if(event.target.closest("a"))return;
   const row=event.target.closest("tr[data-id]");
   if(row){o.open(row.dataset.id)}
 });
 $("tf-map-csv").addEventListener("click",t.csv);
 return t;
}
// A change of position that should not animate: the next frame starts from where it is put.
function mapInstantly(node,apply){node.classList.add("instant");apply();node.getBoundingClientRect();node.classList.remove("instant")}
// The hover card both maps share: it waits a moment before it first shows, then follows from mark to mark at once,
// stays beside its mark while the page scrolls, and closes when the mark leaves the screen or is drawn again.
function mapCard(node){
 let showTimer=0,hideTimer=0,scrollFrame=0;
 const card={node,key:null,anchor:null,entry:null};
 card.visible=()=>node.classList.contains("visible");
 function place(rect){
   const gap=12,margin=10,size=node.getBoundingClientRect();
   let left=rect.right+gap;
   if(left+size.width>innerWidth-margin)left=rect.left-size.width-gap;
   left=Math.max(margin,Math.min(left,innerWidth-size.width-margin));
   let top=rect.top+Math.min(8,Math.max(0,(rect.height-size.height)/2));
   if(top+size.height>innerHeight-margin)top=innerHeight-size.height-margin;
   node.style.left=Math.round(left)+"px";node.style.top=Math.round(Math.max(margin,top))+"px";
 }
 card.show=(key,html,anchor,entry,immediate)=>{
   clearTimeout(hideTimer);
   if(card.key===key&&card.visible())return;
   clearTimeout(showTimer);
   const show=()=>{
     const was=card.visible();
     card.key=key;card.anchor=anchor;card.entry=entry;
     node.innerHTML=html();
     node.setAttribute("aria-hidden","false");
     const rect=anchor.getBoundingClientRect();
     if(was)place(rect);else mapInstantly(node,()=>place(rect));
     node.classList.add("visible");
   };
   if(immediate||card.visible())show();else showTimer=setTimeout(show,110);
 };
 card.hide=(immediate,after)=>{
   clearTimeout(showTimer);clearTimeout(hideTimer);
   const hide=()=>{card.key=null;card.anchor=null;card.entry=null;node.classList.remove("visible");node.setAttribute("aria-hidden","true");after?.()};
   if(immediate)hide();else hideTimer=setTimeout(hide,90);
 };
 card.follow=()=>{
   if(!card.anchor||!card.visible())return;
   if(!card.anchor.isConnected){card.hide(true);return}
   const rect=card.anchor.getBoundingClientRect();
   if(rect.bottom<0||rect.top>innerHeight)card.hide(true);else place(rect);
 };
 addEventListener("scroll",()=>{if(!scrollFrame&&card.anchor)scrollFrame=requestAnimationFrame(()=>{scrollFrame=0;card.follow()})},{passive:true});
 return card;
}
// The hover outline of the treemap: it glides to a nearby mark and jumps to a far one.
function mapOutline(svg){
 const ring=el("rect",{class:"tf-map-outline",width:0,height:0},svg);
 const outline={ring,entry:null};
 outline.move=(entry,instant)=>{
   const inset=entry.kind==="leaf"?1:1.25,area=entry.area;
   const put=()=>{
     ring.setAttribute("rx",Math.max(0,RADIUS[entry.kind]-inset));
     ring.style.transform="translate("+(area.x+inset)+"px,"+(area.y+inset)+"px)";
     ring.style.width=Math.max(0,area.width-2*inset)+"px";
     ring.style.height=Math.max(0,area.height-2*inset)+"px";
   };
   const previous=ring.dataset.center?ring.dataset.center.split(",").map(Number):null,center=[area.x+area.width/2,area.y+area.height/2];
   const near=!instant&&previous&&Math.hypot(center[0]-previous[0],center[1]-previous[1])<240;
   ring.dataset.center=center.join(",");
   if(ring.classList.contains("visible")&&near)put();else mapInstantly(ring,put);
   ring.classList.add("visible");
   outline.entry=entry;
 };
 outline.hide=()=>{ring.classList.remove("visible");outline.entry=null};
 return outline;
}
// Find: every goal, capability and contract by name, short name, ID or path; Enter shows it in the current layer.
//   items(): [{row,path,badge,rank}] with the page's own badge, lower rank first; pick(id); hint
function mapFind(o){
 const $=id=>document.getElementById(id);
 const box=$("tf-map-find"),input=$("tf-map-find-input"),list=$("tf-map-find-list");
 let index=null,results=[],active=0,back=null;
 function render(){
   index=index||o.items().map(item=>({...item,text:(item.row.label+" "+(item.row.short||"")+" "+item.row.id+" "+item.path).toLowerCase()}));
   const words=input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
   results=index.filter(item=>words.every(word=>item.text.includes(word))).sort((a,b)=>a.rank-b.rank||a.row.label.localeCompare(b.row.label)).slice(0,80);
   active=Math.min(active,Math.max(0,results.length-1));
   list.innerHTML=results.length?results.map((item,position)=>'<div class="tf-map-find-item" role="option" id="tf-map-find-'+position+'" data-index="'+position+'" aria-selected="'+(position===active)+'">'
     +'<span class="tf-map-find-badge" aria-hidden="true">'+item.badge()+"</span>"
     +'<span class="tf-map-find-text"><span class="tf-map-find-name">'+escapeHtml(item.row.label)+'</span><span class="tf-map-find-path">'+escapeHtml(item.path||item.kind)+"</span></span>"
     +'<span class="tf-map-find-id">'+escapeHtml(item.row.id)+"</span></div>").join(""):'<div class="tf-map-find-empty">Nothing matches.</div>';
   input.setAttribute("aria-activedescendant",results.length?"tf-map-find-"+active:"");
   list.querySelector('[aria-selected="true"]')?.scrollIntoView({block:"nearest"});
 }
 const find={open:()=>{back=document.activeElement;o.hint.hide();box.hidden=false;input.value="";active=0;render();input.focus()},isOpen:()=>!box.hidden};
 find.close=restore=>{if(box.hidden)return;box.hidden=true;if(restore)back?.focus?.({preventScroll:true})};
 const pick=position=>{const item=results[position];if(!item)return;find.close(false);o.pick(item.row.id)};
 input.addEventListener("input",()=>{active=0;render()});
 input.addEventListener("keydown",event=>{
   if(event.key==="ArrowDown"||event.key==="ArrowUp"){event.preventDefault();active=Math.max(0,Math.min(results.length-1,active+(event.key==="ArrowDown"?1:-1)));render()}
   else if(event.key==="Enter"){event.preventDefault();pick(active)}
   else if(event.key==="Escape"){event.preventDefault();event.stopPropagation();find.close(true)}
 });
 list.addEventListener("click",event=>{const item=event.target.closest("[data-index]");if(item)pick(Number(item.dataset.index))});
 box.addEventListener("pointerdown",event=>{if(event.target===box)find.close(true)});
 $("tf-map-find-open").addEventListener("click",find.open);
 return find;
}
// A map: both pages run this. It shows one view at a time (Overall as rings or as the table, or one layer's map),
// keeps the address, the hover card with its outline, arc and lineage, the filters and Changes on every view,
// keyboard focus and the keys. The page describes its layers and draws what only it knows:
//   tree, layers [[key,label,help]], insights {run,delta}, words(layer): what up and down mean for Changes
//   href(row,layer); says(row,layer): {text,tone}, what a layer says about a mark (its spoken name, the card's pill,
//     the All layers foot), or null; describe(row,layer,entry): {body,extra}, the rest of its card
//   paint(entries,layer,animated): the tiles in a layer's colours; legend(layer): {items,help}
//   facets, panels {layer: {title,help,before,facets}}, filterRows, markPanel(row,panel); Kind and Goal close every
//     panel. A ring segment names the facet it shows, or the facet and the value, in data-seg
//   strip {groups,card,row,cells}; table {columns,groups,keys,name,order,sortValue,stats,cells,csv}, after the
//     contract name, the goal and the capability that both tables start with
//   tiles {dots,leaf(row,layer),mark(row,layer)}; rings (see mapRings); find(row,index): {rank,badge}
// Nothing runs until start(), so the page can keep what mapPage returns for its own drawing first.
const MAP_TABLE_HELP="Click a cell or an option to narrow the table; the same filters apply to every layer.";
const MAP_TILE_HELP="Each tile is a contract with its technical requirements beside it; ";
function mapPage(o){
 const $=id=>document.getElementById(id);
 const tree=o.tree,delta=o.insights?.delta||{};
 const VIEW_KEYS=[...o.layers.map(layer=>layer[0]),"table"];
 const cardOf=key=>key==="table"?"overall":key;
 // view is what the stage shows (a layer, or the table of Overall); layer is the layer it shows.
 const page={tree,view:"overall",layer:"overall",overallMode:"overall",focusedId:"",pendingFocus:"",changesOn:false};
 const card=mapCard($("tf-map-card")),hint=mapHint($("tf-map-hint"));
 const layerOf=entry=>entry.layer||(entry.radial?"overall":page.layer);
 const deltaOf=key=>(delta.layers||{})[key]||{up:[],down:[]};
 const labelOf=key=>o.layers.find(layer=>layer[0]===key)[1];
 const ariaOf=(row,layer)=>{const says=o.says(row,layer);return MAP_KIND[row.level]+": "+row.label+(says?", "+says.text:"")};
 // Hover and focus: the outline or the arc and the lineage show at once and stay while the card is open; the card
 // waits a moment before it first shows.
 function clearHighlight(){
   [tiles.svg,rings.svg].forEach(svg=>svg.querySelectorAll(".tf-map-lineage").forEach(node=>node.classList.remove("tf-map-lineage")));
   tiles.outline?.hide();
   rings.clear();
 }
 function highlight(entry){
   clearHighlight();
   if(entry.radial)rings.highlight(entry);else tiles.outline.move(entry);
   const byId=entry.radial?rings.byId:tiles.byId;
   tree.ancestors(entry.row).forEach(item=>{const parent=byId.get(item.id);if(parent&&parent.kind!=="leaf")parent.shape.classList.add("tf-map-lineage")});
 }
 const hideTip=immediate=>card.hide(immediate,clearHighlight);
 const hoverKey=entry=>(entry.radial?"rings:":"map:")+entry.row.id+(entry.layer?"@"+entry.layer:"");
 // The card: kind and what the layer says, the name and where it sits, the page's rows, and where a click goes.
 function cardHtml(entry){
   const row=entry.row,layer=layerOf(entry),says=o.says(row,layer),part=o.describe(row,layer,entry),path=tree.ancestors(row);
   return'<div class="tf-map-card-head"><span class="tf-map-card-kind">'+MAP_KIND[row.level]+"</span>"+(says?'<span class="tf-map-pill'+(says.tone?" "+says.tone:"")+'">'+escapeHtml(says.text)+"</span>":"")+"</div>"
     +'<div class="tf-map-card-title">'+escapeHtml(row.label)+"</div>"
     +(path.length?'<div class="tf-map-card-path">'+path.map(item=>escapeHtml(clip(item.short||item.label,42))).join(" › ")+"</div>":"")
     +'<div class="tf-map-card-rows">'+part.body+"</div>"+(part.extra||"")
     +'<div class="tf-map-card-go">Opens <b>'+escapeHtml(mapOpens(row,entry.link.getAttribute("href")))+"</b></div>";
 }
 function bind(entry){
   const enter=immediate=>{highlight(entry);card.show(hoverKey(entry),()=>cardHtml(entry),entry.anchor,entry,immediate);filters.mark(entry.row)};
   const leave=immediate=>{hideTip(immediate);filters.mark(null)};
   entry.link.addEventListener("pointerenter",event=>{if(!strip.holds(event))enter(false)});
   entry.link.addEventListener("pointerleave",event=>{if(!strip.holds(event))leave(false)});
   entry.link.addEventListener("focus",()=>enter(true));
   entry.link.addEventListener("blur",()=>leave(true));
 }
 const tiles=mapTiles($("tf-map-tiles"),tree,{dots:!!o.tiles.dots,bind,drawn:()=>paint(false)});
 const rings=mapRings($("tf-map-rings"),tree,{...o.rings,href:row=>o.href(row,"overall"),aria:row=>ariaOf(row,"overall"),bind,drawn:applyFocus});
 // The tiles take the colours of the layer they show; links and names follow it.
 function paint(animated){
   tiles.entries.forEach(entry=>{entry.link.setAttribute("href",o.href(entry.row,page.layer));entry.link.setAttribute("aria-label",ariaOf(entry.row,page.layer))});
   o.paint(tiles.entries,page.layer,animated);
   applyFocus();
 }
 // Filters keep their marks lit and dim the rest; Changes outlines what went up and what went down. Both survive
 // redraws and apply to every view.
 function applyFocus(){
   const ids=filters.shown(true),changes=page.changesOn&&delta.baseline;
   // A previewed option that the rings show as segments keeps only its own segments lit inside the rays it keeps.
   const preview=page.view==="overall"?filters.preview:null,marks=preview?[preview.facet,preview.facet+"="+preview.value]:[];
   const segments=[...rings.svg.querySelectorAll("[data-seg]")],lit=segments.some(node=>marks.includes(node.dataset.seg));
   segments.forEach(node=>node.classList.toggle("tf-map-seg-dim",lit&&!marks.includes(node.dataset.seg)));
   [...tiles.entries,...rings.entries].forEach(entry=>{
     const leaf=entry.kind==="leaf"||entry.kind==="track",hit=!!ids&&ids.has(entry.row.id);
     entry.link.classList.toggle("tf-map-dim",!!ids&&leaf&&!hit);
     entry.shape.classList.toggle("tf-map-hit",!!ids&&!leaf&&entry.kind!=="product"&&hit);
     const change=changes&&leaf?deltaOf(layerOf(entry)):null;
     entry.shape.classList.toggle("tf-map-up",!!change&&change.up.includes(entry.row.id));
     entry.shape.classList.toggle("tf-map-down",!!change&&change.down.includes(entry.row.id));
   });
 }
 // The legend of each view: the page's colours and one sentence behind the ?, then the Changes key whenever there is
 // a run to compare with. The table keeps Overall's.
 function legendFor(key,measuring){
   const layer=cardOf(key),words=o.words(layer),legend=o.legend(layer);
   return legend.items+'<span class="tf-map-help" data-tip="'+escapeHtml((layer==="overall"?"":MAP_TILE_HELP)+legend.help)+'">?</span>'
     +((measuring||page.changesOn)&&delta.baseline?'<span class="tf-map-changes-key"><i class="up"></i>'+escapeHtml(words[0])+'<i class="down"></i>'+escapeHtml(words[1])+" since "+escapeHtml(mapRunLabel(delta.baseline.started_at))+"</span>":"");
 }
 // Kind and goal narrow the contracts on both maps and close every panel. The panel follows the layer; the table
 // keeps Overall's panel, and only its hint says a click narrows the table.
 const facets={...o.facets,
   kind:{label:"Kind",options:[["requirement","Requirement"],["treq","Technical requirement"]],test:(row,value)=>row.level===value},
   goal:{label:"Goal",options:tree.goals.map(goal=>[goal.id,goal.short||goal.label]),test:(row,value)=>tree.isLeaf(row)&&tree.goalOf.get(row.id)===value}};
 const panelOf=key=>{const panel=key==="table"?{...o.panels.overall,help:MAP_TABLE_HELP}:o.panels[key];return{...panel,facets:[...panel.facets,"kind","goal"]}};
 const filters=mapFilters({facets,rows:o.filterRows,leaves:tree.leaves,view:()=>page.view,panel:panelOf,previews:key=>key!=="table",
   changed:()=>{applyFocus();if(page.view==="table")table.render();writeHash()},previewed:applyFocus,mark:o.markPanel,hideTip:()=>hideTip(true)});
 // Both tables start with the contract, group it by goal and capability, by goal or not at all, and download the same
 // first columns; the page adds its own columns and groups.
 const goalName=key=>tree.rowById.get(key)?.short||tree.rowById.get(key)?.label||"No goal";
 const table=mapTable({...o.table,
   columns:[["name","Contract","Contract, grouped as chosen"],...o.table.columns],
   groups:[["tree","Goal › capability"],["goal","Goal"],...o.table.groups,["none","None"]],
   keys:(row,group)=>group==="goal"?[tree.goalOf.get(row.id)]:o.table.keys(row,group),
   name:(group,key)=>group==="goal"?goalName(key):o.table.name(group,key),
   order:(group,keys)=>group==="goal"?tree.goals.map(goal=>goal.id).filter(key=>keys.includes(key)):o.table.order(group,keys),
   sortValue:(row,key)=>key==="name"?(row.short||row.label).toLowerCase():o.table.sortValue(row,key),
   stats:list=>plural(list.length,"contract","contracts")+" · "+o.table.stats(list),
   csv:{file:o.table.csv.file,head:["id","title","kind","goal","capability",...o.table.csv.head],line:row=>{const path=tree.ancestors(row);return[row.id,row.label,MAP_KIND[row.level],path.find(item=>item.level==="goal")?.label||"",path.find(item=>item.level==="feature")?.label||"",...o.table.csv.line(row)]}},
   rows:()=>{const shown=filters.shown(false);return tree.leaves.filter(row=>!shown||shown.has(row.id))},
   tree:{goals:tree.goals,goalOf:row=>tree.goalOf.get(row.id),features:goal=>(tree.children.get(goal.id)||[]).filter(item=>item.level==="feature"),inside:feature=>new Set(tree.inside(feature).map(row=>row.id))},
   href:row=>o.href(row,"overall"),height:()=>frame.viewH,changed:()=>writeHash(),
   open:id=>{page.focusedId=id;writeHash();location.href=o.href(tree.rowById.get(id),"overall")}});
 // The strip: the page gives each card its lines and a table row its short form; the spoken name, the change badge,
 // the mini-map, a row's marks (one per contract, in the layer's colours) and the foot are the same on both maps.
 const plain=html=>String(html).replace(/<[^>]+>/g,"").replace(/\s+/g," ").trim();
 const spoken=(key,card)=>labelOf(key)+": "+plain(card.status)+", "+plain(card.count);
 function stripCells(key){
   let out="";
   tree.columns.leaves.forEach((leaf,index)=>{out+='<rect data-leaf="'+index+'" x="'+(leaf.x+1)+'" y="2" width="'+(MAP_CELL-2)+'" height="12" '+o.tiles.leaf(leaf.row,key)+"/>"});
   if(o.tiles.mark)tree.columns.groups.forEach(group=>{
     const mark=o.tiles.mark(group.row,key),goal=group.row.level==="goal";
     if(mark)out+='<rect x="'+(group.start-(goal?4:2))+'" y="'+(goal?.5:1.5)+'" width="'+(group.end-group.start+(goal?8:4))+'" height="'+(goal?15:13)+'" rx="2" fill="none" class="'+mark+'" vector-effect="non-scaling-stroke"/>';
   });
   return out;
 }
 const strip=mapStrip({groups:o.strip.groups,layers:o.layers,columns:tree.columns,hint,
   card:key=>{const lines=o.strip.card(key);return{...lines,name:spoken(key,lines),delta:mapDelta(delta,key,o.words(key)),thumb:key==="overall"?rings.thumb():tiles.thumb(row=>o.tiles.leaf(row,key),o.tiles.mark&&(row=>o.tiles.mark(row,key)))}},
   row:key=>({...o.strip.row(key),name:spoken(key,o.strip.card(key))}),
   cells:key=>o.strip.cells?.(key)??stripCells(key),
   foot:row=>strip.order().map(key=>{const says=o.says(row,key);return'<span class="tf-map-mark'+(says?.tone?" "+says.tone:"")+'">'+escapeHtml(labelOf(key))+": "+escapeHtml(says?.text||"–")+"</span>"}).join(" · "),
   current:()=>page.layer,select:(key,focus)=>select(key==="overall"?page.overallMode:key,focus),focus:focusRow});
 const find=mapFind({hint,pick:focusRow,items:()=>tree.rows.filter(row=>row.level!=="product").map((row,index)=>({row,path:tree.ancestors(row).map(item=>item.short||item.label).join(" › "),kind:MAP_KIND[row.level],...o.find(row,index)}))});
 function select(key,focus,keepFocus){
   if(!VIEW_KEYS.includes(key))return;
   const changed=key!==page.view,layer=cardOf(key);
   page.view=key;
   if(layer==="overall")page.overallMode=key;
   hideTip(true);
   // SVG elements have no hidden property: toggle the attribute itself.
   rings.svg.toggleAttribute("hidden",key!=="overall");
   tiles.svg.toggleAttribute("hidden",key==="overall"||key==="table");
   $("tf-map-list-view").hidden=key!=="table";
   if(layer!==page.layer){page.layer=layer;paint(true)}
   if(key==="overall")rings.draw(frame,false);
   else if(key==="table")table.render();
   else tiles.layout(frame,false);
   frame.legend.innerHTML=legendFor(key);
   filters.preview=null;
   filters.renderPanel(changed);
   // Nothing above the view changes height between layers; this only catches a late font or window change.
   setTimeout(()=>frame.layout(false),0);
   strip.sync();
   frame.showMode(key);
   if(changed&&!keepFocus)page.focusedId="";
   applyFocus();
   writeHash();
   strip.show(layer,focus);
 }
 // The view has an address: #view, #view:ID and ?filters. Back from a contract page and shared links return here.
 function writeHash(){
   const params=new URLSearchParams();
   filters.write(params);
   if(page.view==="table")table.write(params);
   const query=params.toString(),hash="#"+page.view+(page.focusedId?":"+page.focusedId:"")+(query?"?"+query:"");
   if(location.hash!==hash)history.replaceState(history.state,"",hash);
 }
 function focusRow(id){
   const row=tree.rowById.get(id);
   if(!row)return;
   page.focusedId=id;
   if(page.view==="table"){
     const shown=filters.shown(false);
     if(tree.isLeaf(row)&&shown&&!shown.has(id))filters.clear();
     table.render();
     const target=tree.isLeaf(row)?table.row(id):null;
     if(target){target.scrollIntoView({block:"center"});target.classList.add("flash");setTimeout(()=>target.classList.remove("flash"),1700)}
     writeHash();
     return;
   }
   const entry=(page.view==="overall"?rings.byId:tiles.byId).get(id);
   writeHash();
   // The view may not be drawn yet (no width at start): focus it as soon as it is.
   if(!entry){page.pendingFocus=id;return}
   page.pendingFocus="";
   entry.link.focus();
   // focus() is silent when the link already has focus or the window has none; the hover card listens for the event.
   if(!card.visible())entry.link.dispatchEvent(new FocusEvent("focus"));
 }
 function readHash(){
   const raw=location.hash.slice(1);
   if(!raw)return false;
   const[head,query=""]=raw.split("?");
   let[key,id]=decodeURIComponent(head).split(":");
   if(key==="overview")key="overall";
   if(!VIEW_KEYS.includes(key))return false;
   const params=new URLSearchParams(query);
   filters.read(params);
   table.read(params);
   page.focusedId=id&&tree.rowById.has(id)?id:"";
   select(key,false,true);
   if(page.focusedId)focusRow(page.focusedId);
   return true;
 }
 // Layout: the frame gives every view one size and follows the stage while the panel slides. The card stays beside its
 // mark while the view changes size, and closes when its mark is drawn again.
 const keepCard=()=>{if(card.anchor&&!card.anchor.isConnected)hideTip(true);else card.follow()};
 function layoutViews(force){
   // A redraw replaces the shapes: the hover card follows the focused mark to its new shape.
   const refocus=card.visible()&&page.focusedId&&page.view!=="table"?page.focusedId:"";
   const moved=tiles.layout(frame,force),redrawn=rings.draw(frame,force);
   if(page.view==="table")table.fit();
   if(moved)strip.build();
   keepCard();
   const target=page.pendingFocus||(moved||redrawn?refocus:"");
   if(target&&page.view!=="table")focusRow(target);
 }
 function followStage(width){
   if(!width)return;
   if(page.view==="overall")rings.squeeze(width);
   else if(page.view!=="table")tiles.layout(frame,false);
   keepCard();
 }
 const frame=mapFrame({views:VIEW_KEYS,legend:legendFor,modes:key=>cardOf(key)==="overall",longest:()=>filters.longest(),layout:layoutViews,follow:followStage,mode:key=>select(key,false)});
 Object.assign(page,{card,hint,tiles,rings,filters,table,strip,find,frame,select,focusRow});
 page.start=()=>{
   frame.stage.addEventListener("click",event=>{
     const link=event.target.closest("a"),entry=link&&[...tiles.entries,...rings.entries].find(item=>item.link===link);
     if(entry&&entry.row.level!=="product"){page.focusedId=entry.row.id;writeHash()}
   },true);
   window.addEventListener("hashchange",readHash);
   ["tf-map-tools","tf-map-panel","tf-map-legendbar"].forEach(id=>hint.watch($(id)));
   mapChanges($("tf-map-changes"),delta,on=>{page.changesOn=on;frame.legend.innerHTML=legendFor(page.view);applyFocus()});
   mapCopy($("tf-map-copy"),writeHash);
   // Keys: Esc closes the card, / find, F filters, 1–9 layers in strip order, T the All layers table.
   document.addEventListener("keydown",event=>{
     if(event.key==="Escape"){hideTip(true);return}
     if(event.defaultPrevented||event.metaKey||event.ctrlKey||event.altKey||find.isOpen())return;
     if(event.target.closest?.("input,textarea,select,[contenteditable]"))return;
     if(event.key==="/"){event.preventDefault();find.open();return}
     if(event.key==="f"||event.key==="F"){event.preventDefault();filters.setPanel(!filters.open,true);return}
     if(/^[1-9]$/.test(event.key)){const key=strip.order()[Number(event.key)-1];if(key){event.preventDefault();select(key==="overall"?page.overallMode:key,true)}return}
     if(event.key==="t"||event.key==="T"){event.preventDefault();strip.toggleTable()}
   });
   // A ring's name opens its layer; pointing at it shows the ring.
   const ringName=event=>event.target.closest?.("[data-map-ring]");
   rings.svg.addEventListener("pointerover",event=>{const name=ringName(event);if(name){hideTip(true);rings.showBand(name.dataset.mapRing);hint.show(name)}});
   rings.svg.addEventListener("pointerout",event=>{const name=ringName(event);if(name&&!name.contains(event.relatedTarget)){rings.clear();hint.hide()}});
   rings.svg.addEventListener("click",event=>{const name=ringName(event);if(name)select(name.dataset.mapRing,false)});
   rings.svg.addEventListener("keydown",event=>{const name=ringName(event);if(name&&(event.key==="Enter"||event.key===" ")){event.preventDefault();select(name.dataset.mapRing,true)}});
   // Overall first; the panel opens as the reader left it, without sliding in.
   frame.body.classList.add("tf-map-still");
   filters.setPanel(filters.startOpen,false);
   $("tf-map-stamp").innerHTML=mapStamp(o.insights?.run);
   strip.build();
   frame.layout(true);
   filters.render();
   if(!readHash())select("overall",false);
   setTimeout(()=>frame.body.classList.remove("tf-map-still"),200);
   document.fonts?.ready?.then(()=>frame.layout(true));
 };
 return page;
}"""


def map_tools(about: str) -> str:
    """The tools line both maps share: the retained run, or the active filters in its place, and the actions."""
    return (
        '<div class="tf-map-tools" id="tf-map-tools"><span class="tf-map-lead" id="tf-map-lead">'
        '<span class="tf-map-stamp" id="tf-map-stamp"></span>'
        f'<span class="tf-map-help" aria-hidden="true" data-tip="{about}">?</span>'
        '<span class="tf-map-filters" id="tf-map-filters" role="group" aria-label="Active filters" hidden>'
        '<span class="tf-map-chips" id="tf-map-chips"></span>'
        '<button type="button" class="tf-map-clear" data-clear>Clear all</button></span></span>'
        '<span class="tf-map-actions">'
        '<button type="button" class="tf-map-action" id="tf-map-panel-toggle" aria-expanded="false" '
        'aria-controls="tf-map-panel" data-tip="Open the filters that fit the current layer beside it (F).">'
        '<i class="fa-solid fa-filter" aria-hidden="true"></i>Filters'
        '<span class="tf-map-badge" id="tf-map-filter-badge" hidden></span><kbd>F</kbd></button>'
        '<button type="button" class="tf-map-action" id="tf-map-find-open" aria-haspopup="dialog" '
        'aria-controls="tf-map-find" data-tip="Find a goal, capability or contract and show it in the current layer (/).">'
        '<i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>Find<kbd>/</kbd></button>'
        '<button type="button" class="tf-map-action" id="tf-map-changes" aria-pressed="false">'
        '<i class="fa-solid fa-code-compare" aria-hidden="true"></i>Changes</button>'
        '<button type="button" class="tf-map-action" id="tf-map-copy" data-tip="Copy a link to this layer, its filters and the selected contract.">'
        '<i class="fa-solid fa-link" aria-hidden="true"></i><span>Copy link</span></button>'
        "</span></div>"
    )


def map_frame(rings: str, rings_label: str, tiles_label: str) -> str:
    """The legend bar and the body both maps share: the side panel, then the stage with the rings, the map and the
    contracts table; then Find and the hover card."""
    return (
        '<div class="tf-map-legendbar" id="tf-map-legendbar">'
        '<div class="tf-map-legend" id="tf-map-legend" aria-hidden="true"></div>'
        '<div class="tf-map-side">'
        '<span class="tf-map-seg" id="tf-map-mode" role="group" aria-label="Show Overall as">'
        f'<button type="button" data-mode="overall" aria-pressed="true" data-tip="{rings}">Rings</button>'
        '<button type="button" data-mode="table" aria-pressed="false" '
        'data-tip="Every contract in one table that you can filter, group, sort and download.">Table</button>'
        '</span><span class="tf-map-total" id="tf-map-total"></span>'
        "</div></div>"
        '<div class="tf-map-body" id="tf-map-body">'
        '<aside class="tf-map-panel" id="tf-map-panel" aria-label="Filters for the current layer" inert>'
        '<div class="tf-map-panel-inner"><div class="tf-map-panel-head">'
        '<span class="tf-map-panel-title" id="tf-map-panel-title"></span>'
        '<button type="button" class="tf-map-close" id="tf-map-panel-close" aria-label="Close the filters">&times;</button>'
        '</div><div id="tf-map-panel-body"></div></div></aside>'
        '<div class="tf-map-stage" id="tf-map-stage">'
        f'<svg class="tf-map-view tf-map-rings" id="tf-map-rings" role="group" aria-label="{rings_label}"></svg>'
        f'<svg class="tf-map-view tf-map-tiles" id="tf-map-tiles" role="group" aria-label="{tiles_label}" hidden></svg>'
        '<div class="tf-map-list-view" id="tf-map-list-view" hidden><div class="tf-map-list-bar">'
        '<span class="tf-map-list-bar-label">Group by</span><span class="tf-map-seg" id="tf-map-group-by"></span>'
        '<span class="tf-map-summary" id="tf-map-summary"></span>'
        '<button type="button" class="tf-map-action" id="tf-map-csv">'
        '<i class="fa-solid fa-download" aria-hidden="true"></i>CSV</button></div>'
        '<div class="tf-map-list-wrap" id="tf-map-list"></div></div>'
        "</div></div>"
        '<div class="tf-map-find" id="tf-map-find" role="dialog" aria-modal="true" aria-label="Find on the map" hidden>'
        '<div class="tf-map-find-box"><input class="tf-map-find-input" id="tf-map-find-input" type="search" '
        'placeholder="Find a goal, capability or contract by name or ID" autocomplete="off" spellcheck="false" '
        'role="combobox" aria-expanded="true" aria-controls="tf-map-find-list">'
        '<div class="tf-map-find-list" id="tf-map-find-list" role="listbox" aria-label="Matches"></div>'
        '<div class="tf-map-find-foot">↑ ↓ move · Enter shows it in the current layer · Esc closes</div></div></div>'
        '<div id="tf-map-card" class="tf-map-card" role="tooltip" aria-hidden="true"></div>'
    )


def map_strip(page: str, legend: str) -> str:
    """The layer strip both maps share: cards in a scroller, scroll edges and the All layers table."""
    return (
        '<div class="tf-map-layerbar" id="tf-map-layerbar">'
        '<div class="tf-map-scroller" id="tf-map-scroller">'
        f'<div class="tf-map-layers" id="tf-map-tabs" role="tablist" aria-label="{page} layer"></div></div>'
        '<div class="tf-map-edge left" aria-hidden="true">'
        '<button type="button" tabindex="-1" data-map-scroll="-1"></button></div>'
        '<div class="tf-map-edge right" aria-hidden="true">'
        '<button type="button" tabindex="-1" data-map-scroll="1"></button></div>'
        '<button type="button" class="tf-map-table-toggle" id="tf-map-table-toggle" aria-expanded="false" '
        'aria-controls="tf-map-table" aria-haspopup="dialog" '
        'data-tip="Every layer as one row and every contract as one column; a row opens its map (T).">'
        '<i class="fa-solid fa-table-list" aria-hidden="true"></i>All layers'
        '<i class="fa-solid fa-chevron-down tf-map-chevron" aria-hidden="true"></i></button>'
        f'<div class="tf-map-table" id="tf-map-table" role="dialog" aria-label="All {page.lower()} layers" hidden>'
        '<div class="tf-map-table-head"><span class="tf-map-table-title">All layers</span>'
        f'<span class="tf-map-table-legend" aria-hidden="true">{legend}</span>'
        '<button type="button" class="tf-map-table-close" aria-label="Close">&times;</button></div>'
        f'<div class="tf-map-rows" id="tf-map-rows" role="listbox" aria-label="{page} layer"></div>'
        '<div class="tf-map-table-foot" id="tf-map-table-foot"></div>'
        "</div></div>"
        '<div id="tf-map-hint" class="tf-map-hint" role="tooltip" aria-hidden="true"></div>'
    )


HEALTH_MAP_CSS = r"""/* The Health Map's palette: pass, fail and not applicable, and the ink of their words. The shared map does the rest. */
#verification-health-map{--tf-hm-pass:#8ed3a2;--tf-hm-fail:#dc3f47;--tf-hm-na:#dde0e5;--tf-hm-pass-ink:#1f7a3f;--tf-hm-fail-ink:#c42b34;--tf-hm-na-strong:color-mix(in srgb,var(--tf-hm-na) 86%,#000)}
html[data-theme=dark] #verification-health-map{--tf-hm-pass:#22603a;--tf-hm-fail:#e5484d;--tf-hm-na:#2f353d;--tf-hm-pass-ink:#5fcf85;--tf-hm-fail-ink:#ff6b70;--tf-hm-na-strong:color-mix(in srgb,var(--tf-hm-na) 78%,#fff)}
.tf-health-verdict{font-size:.78rem;font-weight:700;letter-spacing:.02em}
.tf-health-verdict.failed{color:var(--tf-hm-fail-ink)}.tf-health-verdict.passed{color:var(--tf-hm-pass-ink)}
.tf-map-sw.passed{background:var(--tf-hm-pass)}.tf-map-sw.failed{background:var(--tf-hm-fail)}.tf-map-sw.na{background:var(--tf-hm-na)}
.tf-map-sw.own{position:relative;border:1.5px solid var(--tf-hm-fail);border-radius:4px;box-shadow:none}
.tf-map-sw.own::after{content:"";position:absolute;left:2px;top:2px;width:5px;height:5px;border-radius:50%;background:var(--tf-hm-fail)}
/* What the Health Map judges on both views: contracts in their verdict, goals and capabilities outlined red where their
   own check fails, the verdict dot before a name, the product verdict and the ring names in their verdict. */
#verification-health-map .tf-map-tile.passed{fill:var(--tf-hm-pass)}
#verification-health-map .tf-map-tile.failed{fill:var(--tf-hm-fail)}
#verification-health-map .tf-map-tile.na{fill:var(--tf-hm-na)}
#verification-health-map .tf-health-own-failed{stroke:var(--tf-hm-fail);stroke-width:1.6}
#verification-health-map .tf-map-dot.passed{fill:var(--tf-hm-pass-ink)}
#verification-health-map .tf-map-dot.failed{fill:var(--tf-hm-fail)}
#verification-health-map .tf-map-dot.na{opacity:0}
#verification-health-map .tf-map-tiles.tf-health-product-failed{border-radius:14px;box-shadow:0 0 0 1.5px var(--tf-hm-fail)}
.tf-map-ring-big.failed{fill:var(--tf-hm-fail-ink)}.tf-map-ring-big.passed{fill:var(--tf-hm-pass-ink)}
.tf-map-ring-name.failed{fill:var(--tf-hm-fail-ink)}.tf-map-ring-name.passed{fill:var(--tf-hm-pass-ink)}
.tf-health-track-own{pointer-events:none}
.tf-health-passline{fill:none;stroke:var(--tf-map-line-strong);stroke-width:1;stroke-dasharray:2 3}
/* The hover card: the verdict pill, failing or passing values, the verdict in every layer and why it fails. */
#verification-health-map .tf-map-pill.failed{color:var(--tf-hm-fail-ink);background:color-mix(in srgb,var(--tf-hm-fail) 16%,transparent)}
#verification-health-map .tf-map-pill.passed{color:var(--tf-hm-pass-ink);background:color-mix(in srgb,var(--tf-hm-pass) 24%,transparent)}
#verification-health-map .tf-map-pill.na{color:var(--pst-color-text-muted)}
#verification-health-map .tf-map-card-rows .value.failed{color:var(--tf-hm-fail-ink)}
#verification-health-map .tf-map-card-rows .value.passed{color:var(--tf-hm-pass-ink)}
.tf-health-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.25rem;margin-top:.45rem;padding-top:.45rem;border-top:1px solid var(--tf-map-line)}
.tf-health-chip{padding:.12rem .2rem;border:1px solid transparent;border-radius:5px;font-size:.64rem;font-weight:650;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--pst-color-text-muted);background:color-mix(in srgb,var(--pst-color-text-base) 6%,transparent)}
.tf-health-chip.current{border-color:var(--tf-map-selected)}
.tf-health-chip.failed{color:var(--tf-hm-fail-ink);background:color-mix(in srgb,var(--tf-hm-fail) 16%,transparent)}
.tf-health-chip.passed{color:var(--tf-hm-pass-ink);background:color-mix(in srgb,var(--tf-hm-pass) 24%,transparent)}
.tf-health-why{margin-top:.45rem;padding-top:.4rem;border-top:1px solid var(--tf-map-line)}
.tf-health-why b{font-weight:700}
.tf-health-find-marks{display:inline-flex;gap:2px}
.tf-health-find-marks i{width:9px;height:9px;border-radius:2px;background:var(--tf-hm-na-strong)}
.tf-health-find-marks i.passed{background:var(--tf-hm-pass)}.tf-health-find-marks i.failed{background:var(--tf-hm-fail)}
.tf-health-find-marks i.first{margin-right:3px}
/* What the Health Map judges in the shared strip: the failing and passing tones, and the colours of Changes. */
#verification-health-map{--tf-map-up:var(--tf-hm-fail-ink);--tf-map-down:var(--tf-hm-pass-ink)}
#verification-health-map .tf-map-group.failed .tf-map-group-head,#verification-health-map .tf-map-rows-label.failed,#verification-health-map .tf-map-edge-note.failed,#verification-health-map .tf-map-mark.failed,#verification-health-map .tf-map-stamp .failed{color:var(--tf-hm-fail-ink)}
#verification-health-map .tf-map-group.passed .tf-map-group-head,#verification-health-map .tf-map-rows-label.passed,#verification-health-map .tf-map-edge-note.passed,#verification-health-map .tf-map-mark.passed,#verification-health-map .tf-map-stamp .passed{color:var(--tf-hm-pass-ink)}
#verification-health-map .tf-map-row-strip .tf-map-tile.na,#verification-health-map .tf-map-table .tf-map-sw.na{fill:var(--tf-hm-na-strong);background:var(--tf-hm-na-strong)}
/* The verdict marks of the contracts table: each opens that layer's evidence for the contract. */
.tf-health-mark{display:inline-grid;place-items:center;width:1.35rem;height:1.35rem;border-radius:5px;font-size:.72rem;font-weight:800;text-decoration:none}
.tf-health-mark.failed{color:var(--tf-hm-fail-ink);background:color-mix(in srgb,var(--tf-hm-fail) 16%,transparent)}
.tf-health-mark.passed{color:var(--tf-hm-pass-ink);background:color-mix(in srgb,var(--tf-hm-pass) 24%,transparent)}
.tf-health-mark.na{color:var(--pst-color-text-muted)}
.tf-health-mark:hover{box-shadow:inset 0 0 0 1.5px currentColor}
.tf-health-cell{width:1%;text-align:center}
.tf-health-why-cell{min-width:14rem;font-size:.7rem;color:var(--pst-color-text-muted)}"""

HEALTH_MAP_JS = r"""const LAYERS=[
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
const tree=mapTree(model.rows),{root,rows,isLeaf}=tree;
const insights=model.insights||{},layerCauses=insights.causes||{};
const layerByKey=new Map(LAYERS.map(layer=>[layer[0],layer]));
// What the Health Map judges: the verdict of every goal, capability and contract in every layer.
const status=(row,key)=>row?.own?.[key]?.status||"na";
const word=value=>value==="passed"?"PASS":value==="failed"?"FAIL":"N/A";
const mark=value=>value==="failed"?"✕":"✓";
const isContainer=row=>row.level==="goal"||row.level==="feature"||row.level==="product";
const marked=rows.filter(row=>row.level!=="product");
function hrefFor(row,key){
 const own=row.own?.[key],canonical=row.layers?.[key],fallback=row.layers?.overall?.href;
 if(isContainer(row))return own?.status==="failed"&&own.href?own.href:fallback;
 if(own&&own.status!=="na"&&own.href)return own.href;
 return canonical?.href||fallback;
}
// What a layer says about a mark: its verdict, or for a goal or capability the verdict of its own checks.
function says(row,key){
 const value=status(row,key);
 return{text:isContainer(row)?(value==="na"?"No own checks":value==="failed"?"Own checks fail":"Own checks pass"):word(value),tone:value};
}
function layerSummary(layer){
 const metrics=(layer?.metrics||[]).filter(metric=>metric.total);
 if(metrics.length===1)return metrics[0].passed+"/"+metrics[0].total;
 return word(layer.status);
}
function valueCell(passed,total){return'<span class="value '+(passed<total?"failed":"passed")+'">'+passed+"/"+total+"</span>"}
// The hover card: what a mark says in one layer, its verdict in every other layer and why it fails.
function describe(row,key){
 const own=row.own?.[key]||{status:"na",metrics:[]},container=isContainer(row);
 let body="";
 if(key==="overall"){
   const parts=LAYERS.slice(1).map(([layerKey,label])=>{
     const layer=row.own?.[layerKey];
     if(!layer||layer.status==="na")return"";
     return'<span>'+label+'</span><span class="value '+layer.status+'">'+mark(layer.status)+" "+layerSummary(layer)+"</span>";
   }).join("");
   if(parts)body+='<div class="sub">'+(container?"Own checks by layer":"By layer")+"</div>"+parts;
 }else{
   const metrics=(own.metrics||[]).filter(metric=>metric.total);
   if(metrics.length)body+='<div class="sub">'+(container?"Own checks":"Checks")+"</div>"+metrics.map(metric=>'<span>'+escapeHtml(METRIC_LABELS[metric.label]||metric.label)+"</span>"+valueCell(metric.passed,metric.total)).join("");
   const unbound=Number(own.unbound_tests||0);
   if(key==="coverage"&&unbound)body+='<span class="note">'+unbound+(unbound===1?" linked test is":" linked tests are")+" not tied to a required case</span>";
 }
 if(row.level==="requirement"&&(key==="overall"||key==="assurance")){
   const support=(row.layers?.assurance?.metrics||[]).find(metric=>metric.label==="TREQ support"&&metric.total);
   if(support)body+='<div class="sub">Technical requirements</div><span>Passing</span>'+valueCell(support.passed,support.total);
 }
 if(container){
   const within=key==="assurance"?"overall":key;
   const applicable=tree.inside(row).filter(item=>status(item,within)!=="na"),failing=applicable.filter(item=>status(item,within)==="failed");
   body+='<div class="sub">Contracts inside</div><span>'+(key==="assurance"?"Failing overall":"Failing")+'</span><span class="value '+(failing.length?"failed":"passed")+'">'+(applicable.length?failing.length+" of "+applicable.length:"none")+"</span>";
 }
 const chips=key==="overall"?"":'<div class="tf-health-strip">'+LAYERS.map(([layerKey,label])=>'<span class="tf-health-chip '+status(row,layerKey)+(layerKey===key?" current":"")+'">'+label+"</span>").join("")+"</div>";
 return{body:body||'<span class="note">No checks here</span>',extra:chips+whyLine(row,key)};
}
// A layer's colours on the map: contracts in their verdict, goals and capabilities outlined red where their own
// check fails. Red and green never blend directly: a changing tile passes through the neutral midpoint.
const tone=(node,value)=>{node.classList.remove("passed","failed","na");node.classList.add(value)};
function paint(entries,key,animated){
 const through=[];
 entries.forEach(entry=>{
   const value=status(entry.row,key);
   if(entry.kind!=="leaf"){
     entry.shape.classList.toggle("tf-health-own-failed",value==="failed");
     if(entry.dot)tone(entry.dot,value);
     return;
   }
   const neutral=animated&&entry.value&&entry.value!==value&&entry.value!=="na"&&value!=="na";
   tone(entry.shape,neutral?"na":value);
   entry.value=value;
   if(neutral)through.push(entry);
 });
 document.getElementById("tf-map-tiles").classList.toggle("tf-health-product-failed",key!=="overall"&&status(root,key)==="failed");
 if(through.length)setTimeout(()=>through.forEach(entry=>tone(entry.shape,entry.value)),120);
}
const summaryOf=key=>model.summary.layers[key]||{};
const verdictOf=key=>summaryOf(key).status==="passed"?"passed":"failed";
const failingOf=key=>Number(summaryOf(key).failing||0);
const applicableOf=key=>Number(summaryOf(key).applicable||0);
const countLine=key=>failingOf(key)?failingOf(key)+" of "+applicableOf(key)+" fail":"all "+applicableOf(key)+" pass";
// Overall stays first; failing layers follow, most red marks first; passing layers keep their default order.
function layerOrder(){
 const[first,...rest]=LAYERS.map(layer=>layer[0]);
 return{first,failing:rest.filter(key=>verdictOf(key)==="failed").sort((a,b)=>failingOf(b)-failingOf(a)),passing:rest.filter(key=>verdictOf(key)==="passed")};
}
// What each layer says, for its card and its row in the All layers table.
function verdictHtml(key,row){
 const verdict=verdictOf(key);
 return'<span class="tf-health-verdict '+verdict+'"><i class="fa-solid '+(verdict==="passed"?"fa-circle-check":"fa-circle-xmark")+'" aria-hidden="true"></i>'+(row?'<span class="tf-map-row-word"> '+word(verdict)+"</span>":" "+word(verdict))+"</span>";
}
function layerCard(key){
 const failing=failingOf(key);
 return{status:verdictHtml(key,false),count:failing?"<b>"+failing+"</b> of "+applicableOf(key)+" fail":"all "+applicableOf(key)+" pass"};
}
function layerRow(key){
 const failing=failingOf(key);
 return{status:verdictHtml(key,true),count:failing?"<b>"+failing+"</b>/"+applicableOf(key):"all "+applicableOf(key)};
}
// Overall first, then failing layers and passing layers behind the pass line.
function layerGroups(){
 const order=layerOrder();
 return[{tone:verdictOf(order.first),keys:[order.first]},{tone:"failed",icon:"fa-circle-xmark",label:"Failing",keys:order.failing},{tone:"passed",icon:"fa-circle-check",label:"Passing",keys:order.passing}];
}
// Overall's rings beyond the shared core: each contract's overall verdict, then one ring per layer in strip order,
// failing layers inside the pass line and passing ones outside, like the strip's two groups.
function ringBands(outer){
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
 const leaf=[RING_CORE.rays*outer,.62*outer];
 // A layer's name opens that layer's map.
 const names=[{labels:["Overall"],band:leaf,cls:"current"},...tracks.map(track=>{
   const title=layerByKey.get(track.key)[1];
   return{labels:[title],band:track.band,cls:verdictOf(track.key),key:track.key,aria:"Open the "+title+" map",tip:title+": "+countLine(track.key)+". Opens its map."};
 })];
 return{leaf,tracks,passRadius:split?(tracks[split-1].band[1]+tracks[split].band[0])/2:0,names,gap:[tracks[0]?.band[0]||leaf[1],42]};
}
const RINGS={
 bands:ringBands,
 // The centre: the product verdict, the same words as the Overall card.
 centre:()=>{const verdict=verdictOf("overall");return{href:hrefFor(root,"overall"),label:"Product: "+word(verdict)+", "+countLine("overall"),cls:status(root,"overall")==="failed"?"tf-health-own-failed":"",kicker:"OVERALL",big:word(verdict),tone:verdict,small:countLine("overall")}},
 container:row=>status(row,"overall")==="failed"?"tf-health-own-failed":"",
 dot:row=>status(row,"overall"),
 ray:(link,row,a0,a1,geometry)=>el("path",{d:arcPath(0,0,geometry.bands.leaf[0],geometry.bands.leaf[1],a0,a1),class:"tf-map-tile "+status(row,"overall"),"data-seg":"overall"},link),
 rayThumb:(row,a0,a1,geometry)=>[["overall",geometry.bands.leaf],...geometry.bands.tracks.map(track=>[track.key,track.band])].map(([key,band])=>'<path d="'+arcPath(0,0,band[0],band[1],a0,a1)+'" class="tf-map-tile '+status(row,key)+'"/>').join(""),
 // One ring per layer: every contract's own verdict there (a cell opens that layer's evidence), the goal or
 // capability that fails its own check there, and the pass line.
 after:(body,geometry,rings)=>{
   const cells=el("g",{class:"tf-health-tracks"},body);
   geometry.bands.tracks.forEach(track=>{
     tree.columns.leaves.forEach(leaf=>{
       const a0=rings.angleAt(leaf.x+.8),a1=rings.angleAt(leaf.x+MAP_CELL-.8);
       const link=el("a",{href:hrefFor(leaf.row,track.key),tabindex:"-1","aria-hidden":"true"},cells);
       const shape=el("path",{d:arcPath(0,0,track.band[0],track.band[1],a0,a1),class:"tf-map-tile "+status(leaf.row,track.key),"data-seg":track.key},link);
       rings.add({row:leaf.row,kind:"track",layer:track.key,link,shape,anchor:shape,band:track.band,angles:[a0,a1]});
     });
     tree.columns.groups.forEach(group=>{
       if(group.end<=group.start||status(group.row,track.key)!=="failed")return;
       el("path",{d:arcPath(0,0,track.band[0]-1,track.band[1]+1,rings.angleAt(group.start)-.004,rings.angleAt(group.end)+.004),fill:"none",class:"tf-health-own-failed tf-health-track-own"},cells);
     });
   });
   const pass=geometry.bands.passRadius;
   if(!pass)return;
   const a0=rings.angleAt(0)-.02,a1=rings.angleAt(tree.columns.units)+.02,p0=polar(0,0,pass,a0),p1=polar(0,0,pass,a1);
   el("path",{d:"M"+fixed(p0[0])+","+fixed(p0[1])+"A"+fixed(pass)+","+fixed(pass)+" 0 1 1 "+fixed(p1[0])+","+fixed(p1[1]),class:"tf-health-passline"},body);
 }
};
// Why a layer fails: every red mark has at least one named cause.
const causesOf=(id,key)=>(layerCauses[key]||[]).filter(cause=>cause.ids.includes(id));
function whyLine(row,key){
 const reasons=causesOf(row.id,key);
 return reasons.length?'<div class="tf-health-why"><b>Why:</b> '+reasons.map(cause=>escapeHtml(cause.label)).join(" · ")+"</div>":"";
}
// Facets of the shared filters: the verdict in every layer and why a layer fails. A layer's panel shows its own
// verdict and its causes; the filters stay when another layer opens.
const VERDICTS=[["failed","Fail"],["passed","Pass"],["na","N/A"]],VERDICT_FILL={failed:"var(--tf-hm-fail)",passed:"var(--tf-hm-pass)",na:"var(--tf-hm-na-strong)"};
const FACETS={};
LAYERS.forEach(([key,label])=>{
 const causes=layerCauses[key]||[],ids=new Map(causes.map(cause=>[cause.id,new Set(cause.ids)]));
 FACETS[key]={label,options:VERDICTS,swatch:value=>mapSwatch(value),test:(row,value)=>status(row,key)===value};
 FACETS["why-"+key]={label:"Why "+label+" fails",title:"Why it fails",help:"One red mark can have several causes.",empty:"Nothing fails here.",options:causes.map(cause=>[cause.id,cause.label]),tip:value=>causes.find(cause=>cause.id===value)?.hint||"",test:(row,value)=>!!ids.get(value)?.has(row.id)};
});
// The panel follows the layer. Overall shows the layer × verdict matrix, the Health Map's counterpart of the Depth
// Map's test level × boundary: one row per ring, one column per colour.
const PANELS=Object.fromEntries(LAYERS.map(([key,label])=>[key,{title:label,help:"Point at a verdict or a cause to light its marks on the map, or click it to keep only them.",facets:[key,"why-"+key]}]));
PANELS.overall={title:"Layer × verdict",help:"Point at a cell to light its ring in every ray, or click it to keep only the marks with that verdict there.",before:()=>matrixHtml(),facets:[]};
function matrixHtml(){
 const filters=map.filters;
 return mapMatrix({label:"Marks by layer and verdict",template:"6.6rem repeat(3,minmax(0,1fr))",
   columns:VERDICTS.map(([value,label])=>({value,label,swatch:mapSwatch(value)})),
   rows:map.strip.order().map(key=>({key,label:layerByKey.get(key)[1],small:countLine(key)})),
   cell:(row,column)=>{
     const name=row.label+" × "+column.label,all=marked.filter(item=>status(item,row.key)===column.value),hits=all.filter(item=>filters.matches(item,row.key));
     if(!all.length)return{empty:true,title:name+": none"};
     const contracts=hits.filter(isLeaf).length,own=hits.length-contracts,ownAll=all.some(item=>!isLeaf(item));
     return{facet:row.key,value:column.value,pressed:filters.sets[row.key].has(column.value),hits:hits.length,all:all.length,fill:VERDICT_FILL[column.value],
       tip:name+": "+plural(contracts,"contract","contracts")+(ownAll?" and "+plural(own,"own check","own checks")+" of goals and capabilities":"")+(hits.length!==all.length?", "+hits.length+" of "+all.length+" with the filters":"")+".",
       lines:[plural(contracts,"contract","contracts"),...(ownAll?[plural(own,"own check","own checks")]:[])]};
   }});
}
// The legend of each layer: its colours with their counts.
function legendHtml(key){
 const count=value=>marked.filter(row=>status(row,key)===value).length;
 return{items:VERDICTS.map(([value,label])=>mapLegendItem(mapSwatch(value),label,count(value))).join("")+mapLegendItem(mapSwatch("own"),"Own check fails",undefined,true),
   help:key==="overall"?"Inside out: goals, capabilities and contracts, then one ring per layer; failing layers sit inside the dashed line, passing ones outside, and the table shows the same verdicts per layer.":"its colour is its verdict in this layer, and a red outline marks a goal or capability that fails its own check."};
}
// The contracts table: every layer's verdict for each contract; a mark opens that layer's evidence for it.
const TABLE_LAYERS=LAYERS.filter(([key])=>tree.leaves.some(row=>status(row,key)!=="na"));
const failsIn=row=>LAYERS.slice(1).filter(([key])=>status(row,key)==="failed").map(([key])=>key);
const allCauses=row=>LAYERS.slice(1).flatMap(([key])=>causesOf(row.id,key));
const markHtml=(row,key)=>{const value=status(row,key);return'<a class="tf-health-mark '+value+'" href="'+escapeHtml(hrefFor(row,key))+'" title="'+escapeHtml(layerByKey.get(key)[1]+": "+word(value))+'">'+(value==="failed"?"✕":value==="passed"?"✓":"–")+"</a>"};
const TABLE={
 columns:[...TABLE_LAYERS.map(([key,label,help])=>[key,label,help]),["why","Why it fails","The causes of its red marks in every layer"]],
 groups:[["verdict","Verdict"],["fails","Fails in"]],
 keys:(row,group)=>group==="verdict"?[status(row,"overall")]:failsIn(row).length?failsIn(row):["none"],
 name:(group,key)=>group==="verdict"?({failed:"Fail",passed:"Pass",na:"N/A"}[key]||key):key==="none"?"Fails nowhere":layerByKey.get(key)[1],
 order:(group,keys)=>(group==="verdict"?["failed","passed","na"]:[...map.strip.order(),"none"]).filter(key=>keys.includes(key)),
 sortValue:(row,key)=>key==="why"?allCauses(row).length:{failed:2,passed:1,na:0}[status(row,key)],
 stats:list=>{
   const failing=list.filter(row=>status(row,"overall")==="failed").length;
   const by=LAYERS.slice(1).map(([key,label])=>[label,list.filter(row=>status(row,key)==="failed").length]).filter(([,count])=>count).sort((a,b)=>b[1]-a[1]);
   return(failing?failing+" fail":"all pass")+(by.length?" · "+by.map(([label,count])=>label+" "+count).join(", "):"");
 },
 cells:row=>TABLE_LAYERS.map(([key])=>'<td class="tf-health-cell">'+markHtml(row,key)+"</td>").join("")+'<td class="tf-health-why-cell">'+escapeHtml(allCauses(row).map(cause=>cause.label).join(" · "))+"</td>",
 csv:{file:"verification-health.csv",head:[...TABLE_LAYERS.map(([key])=>key),"why"],line:row=>[...TABLE_LAYERS.map(([key])=>word(status(row,key))),allCauses(row).map(cause=>cause.label).join("; ")]}
};
// The shared map. Find lists what fails in most layers first and shows each item's verdict per layer.
const map=mapPage({
 tree,layers:LAYERS,insights,words:()=>["newly failing","fixed"],
 href:hrefFor,says,describe,paint,legend:legendHtml,
 facets:FACETS,panels:PANELS,filterRows:marked,
 strip:{groups:layerGroups,card:layerCard,row:layerRow},
 table:TABLE,
 tiles:{dots:true,leaf:(row,key)=>'class="tf-map-tile '+status(row,key)+'"',mark:(row,key)=>status(row,key)==="failed"?"tf-health-own-failed":""},
 rings:RINGS,
 find:row=>({rank:-LAYERS.slice(1).filter(layer=>status(row,layer[0])==="failed").length,
   badge:()=>'<span class="tf-health-find-marks">'+map.strip.order().map((key,position)=>'<i class="'+status(row,key)+(position?"":" first")+'" title="'+escapeHtml(layerByKey.get(key)[1])+'"></i>').join("")+"</span>"})
});
map.start();"""

DEPTH_MAP_CSS = r"""/* The Depth Map's palette: sequential scales for test levels, boundaries, model validation and mutants caught, with no
   red or green because this page measures and does not judge. The shared map does the rest. */
#verification-depth-map{--tf-dm-empty:#e9ecf0;--tf-dm-track:color-mix(in srgb,var(--pst-color-text-base) 5%,transparent);--tf-dm-hatch:color-mix(in srgb,var(--pst-color-text-base) 20%,transparent);--tf-dm-lv-0:#c6dbef;--tf-dm-lv-1:#9ecae1;--tf-dm-lv-2:#6baed6;--tf-dm-lv-3:#3182bd;--tf-dm-lv-4:#08519c;--tf-dm-local:#c2c9d2;--tf-dm-sub:#cbb6e8;--tf-dm-rep:#9a7ccf;--tf-dm-live:#5a3aa3;--tf-dm-t0:#ecdcbd;--tf-dm-t1:#dcc398;--tf-dm-t2:#c29e5c;--tf-dm-t3:#957541;--tf-dm-t4:#5f4a27;--tf-dm-det-lo:#e1f3ee;--tf-dm-det-hi:#12776a}
html[data-theme=dark] #verification-depth-map{--tf-dm-empty:#2b3038;--tf-dm-track:color-mix(in srgb,var(--pst-color-text-base) 6%,transparent);--tf-dm-lv-0:#22405f;--tf-dm-lv-1:#244d74;--tf-dm-lv-2:#2c6aa0;--tf-dm-lv-3:#468fcf;--tf-dm-lv-4:#8cc2f2;--tf-dm-local:#4b5360;--tf-dm-sub:#4a3a70;--tf-dm-rep:#7157ad;--tf-dm-live:#ad91e6;--tf-dm-t0:#4d4331;--tf-dm-t1:#67583a;--tf-dm-t2:#8f7543;--tf-dm-t3:#b6975b;--tf-dm-t4:#ddc28c;--tf-dm-det-lo:#1b3935;--tf-dm-det-hi:#52cbb7}
.tf-map-sw.pale{opacity:.45}
.tf-map-sw.hatch{background:repeating-linear-gradient(45deg,var(--tf-dm-empty) 0 3px,var(--tf-dm-hatch) 3px 4.5px)}
.tf-map-sw.gap{background:none;box-shadow:none;border:1.5px dashed var(--tf-map-ring)}
.tf-depth-grad{display:inline-block;width:92px;height:10px;border-radius:3px;background:linear-gradient(90deg,var(--tf-dm-det-lo),var(--tf-dm-det-hi))}
/* What the Depth Map measures in its rings: a level without tests and a required cell without a test. */
.tf-depth-ring-track{fill:var(--tf-dm-track)}
.tf-depth-ring-gap{fill:none;stroke:var(--tf-map-ring);stroke-width:1.2;stroke-dasharray:2.5 2;pointer-events:none}
/* The matrix and the substitutes in the side panel. */
.tf-depth-prod{display:flex;width:100%;height:4px;margin-top:auto;border-radius:3px;overflow:hidden;background:var(--tf-dm-track)}
.tf-depth-prod i{display:block;height:100%}
.tf-depth-fact{display:flex;align-items:center;gap:.45rem;margin:.55rem 0 0;padding:.4rem .6rem;border-radius:8px;background:color-mix(in srgb,var(--tf-dm-rep) 16%,transparent);font-size:.72rem;font-weight:650;line-height:1.35}
.tf-depth-fact i{color:var(--tf-dm-rep)}
.tf-depth-lever{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:.5rem;width:100%;margin-bottom:3px;padding:.32rem .5rem;border:1px solid var(--tf-map-line);border-radius:8px;background:var(--pst-color-background);color:inherit;font:inherit;font-size:.72rem;text-align:left;cursor:pointer}
.tf-depth-lever:hover{border-color:var(--tf-map-line-strong)}
.tf-depth-lever[aria-pressed=true]{border-color:var(--tf-map-selected);box-shadow:inset 0 0 0 1px var(--tf-map-selected)}
.tf-depth-lever:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:1px}
.tf-depth-lever:disabled{opacity:.38;cursor:default}
.tf-depth-lever:disabled:hover{border-color:var(--tf-map-line)}
.tf-depth-lever.hit{border-color:var(--tf-map-ring);box-shadow:inset 0 0 0 1.5px var(--tf-map-ring)}
.tf-depth-lever-name{min-width:0;font-weight:650;line-height:1.25}
.tf-depth-lever-name small{display:block;font-size:.66rem;font-weight:500;line-height:1.3;color:var(--pst-color-text-muted)}
.tf-depth-lever-count{font-size:.68rem;color:var(--pst-color-text-muted);white-space:nowrap;text-align:right}
.tf-depth-lever-count b{display:inline-block;min-width:2ch;text-align:right;font-variant-numeric:tabular-nums;color:var(--pst-color-text-base)}
.tf-depth-trust{padding:.05rem .4rem;border-radius:5px;font-size:.64rem;font-weight:750;color:var(--pst-color-text-base)}
/* The hover card's own matrix: the same grid as the Contract Evidence page. */
.tf-depth-mm{grid-column:1/-1;display:grid;grid-template-columns:4.4rem repeat(4,minmax(0,1fr));gap:2px;margin:.1rem 0 .15rem;font-size:.6rem;font-variant-numeric:tabular-nums}
.tf-depth-mm span{display:grid;place-items:center;min-height:15px;border-radius:3px}
.tf-depth-mm .h{font-weight:700;color:var(--pst-color-text-muted)}
.tf-depth-mm .r{justify-content:start;font-weight:650;color:var(--pst-color-text-muted)}
.tf-depth-mm .c{background:var(--tf-dm-track);font-weight:700}
.tf-depth-mm .c.gap{background:none;outline:1.5px dashed var(--tf-map-ring);outline-offset:-1.5px}
.tf-depth-mm-note{grid-column:1/-1;font-size:.64rem;color:var(--pst-color-text-muted)}
/* The contracts table: cells per test level, model validation and the share of mutants caught. */
.tf-map-list-table .lv{min-width:3.6rem}
.tf-map-list-table .lv.void{width:1.6rem;min-width:0;background:repeating-linear-gradient(45deg,transparent 0 5px,var(--tf-dm-track) 5px 7px)}
.tf-depth-cchip{display:inline-flex;align-items:center;margin:1px 2px 1px 0;padding:.05rem .35rem;border-radius:5px;font-size:.66rem;font-weight:700;white-space:nowrap}
.tf-depth-cchip.extra{color:var(--pst-color-text-muted)}
.tf-depth-cchip.gap{border:1.5px dashed var(--tf-map-ring);color:var(--pst-color-text-muted);font-weight:600}
.tf-depth-detbar{display:inline-block;width:56px;height:8px;margin-right:.4rem;vertical-align:middle;border-radius:3px;background:var(--tf-dm-track);overflow:hidden}
.tf-depth-detbar i{display:block;height:100%;background:var(--tf-dm-det-hi)}"""

DEPTH_MAP_JS = r"""const LEVELS=["component","component_integration","system","system_integration","acceptance"];
const LEVEL_NAME={component:"Component",component_integration:"Component integration",system:"System",system_integration:"System integration",acceptance:"Acceptance"};
const LEVEL_SHORT={component:"Component",component_integration:"Comp. int.",system:"System",system_integration:"Sys. int.",acceptance:"Acceptance"};
const LEVEL_RING={component:"Component",component_integration:"Comp. integration",system:"System",system_integration:"Sys. integration",acceptance:"Acceptance"};
const BOUNDS=["none","substitute","replay","direct"];
const BOUND_NAME={none:"Local",substitute:"Substitute",replay:"Replay",direct:"Direct live"};
const BOUND_SHORT={none:"Local",substitute:"Sub",replay:"Replay",direct:"Live"};
const BOUND_VAR={none:"--tf-dm-local",substitute:"--tf-dm-sub",replay:"--tf-dm-rep",direct:"--tf-dm-live"};
const TRUST_NAME={na:"No substitute",l0:"L0 · not checked",l1:"L1",l2:"L2 · checked by an experiment",l3:"L3",l4:"L4"};
const TRUST_VAR={na:"--tf-dm-local",l0:"--tf-dm-t0",l1:"--tf-dm-t1",l2:"--tf-dm-t2",l3:"--tf-dm-t3",l4:"--tf-dm-t4"};
const REASON={
 not_asked:["Not asked by the profile","The verification profile does not ask for implementation faults."],
 shared:["Shared @impl","Its code is also claimed by other contracts, so a fault there cannot be pinned on this one."],
 noimpl:["No @impl","No code is annotated as implementing it, so implementation faults have no target."],
 notests:["No passing tests","No passing test to judge its faults with."],
 nosite:["No fault site","Its code has no site where the engine can inject a fault."],
 campaign:["Campaign not current","The implementation fault campaign result is stale or failed; run it again."]
};
// One sentence of plain language per layer; the card "?" shows it.
const LAYERS=[
 ["overall","Overall","Every contract at once: each ray is one contract, and its rings go from component tests at the centre to acceptance tests at the edge."],
 ["level","Test level","How much of the system the contract's deepest own test runs, from one component up to the whole system with its integrations."],
 ["boundary","Boundary","What the contract's most realistic test talks to at the edge of the system: nothing, a substitute, a recording or the live service, which is a way of testing and not a score."],
 ["trust","Model validation","How well the model behind a substitute or recording has been checked against the real service: L0 not checked, L2 checked by an experiment."],
 ["detect","Mutants caught","Share of small deliberate bugs (mutants) planted in the contract's own code that its own tests catch."]
];
const tree=mapTree(model.rows),{root,isLeaf,leaves}=tree;
const C=model.contracts,P=model.producers,CHECKS=model.checks||{},CELLS=model.cells||{};
// What up and down mean in each layer for Changes. Depth judges nothing, so they only say more or less.
const CHANGE_WORDS={overall:["gained a cell","lost a cell"],level:["deeper","shallower"],boundary:["more realistic","less realistic"],trust:["better checked","less checked"],detect:["caught more","caught fewer"]};
const cssVar=name=>"var("+name+")";
const pct=value=>Math.round(100*value)+"%";
const listed=items=>items.length<2?items.join(""):items.slice(0,-1).join(", ")+" and "+items[items.length-1];
const cellKey=(level,bound)=>level+"|"+bound;
const cellOf=(entity,level,bound)=>entity.cells.find(cell=>cell[0]===level&&cell[1]===bound);
const caseOf=(entity,level,bound)=>(entity.cases||[]).find(cell=>cell[0]===level&&cell[1]===bound);
const wants=(entity,level,bound)=>entity.target.some(cell=>cell[0]===level&&cell[1]===bound);
const ratio=c=>c.detect?c.detect[0]/c.detect[1]:null;
const median=values=>{if(!values.length)return null;const sorted=[...values].sort((a,b)=>a-b),mid=sorted.length>>1;return sorted.length%2?sorted[mid]:(sorted[mid-1]+sorted[mid])/2};
// One encoding everywhere: solid = the profile requires the cell, pale = evidence beyond the profile, dashed = required but no test.
const shade=(bound,required)=>required?cssVar(BOUND_VAR[bound]):"color-mix(in srgb,var("+BOUND_VAR[bound]+") 42%,transparent)";
const hrefFor=(row,key)=>isLeaf(row)?(key==="detect"?C[row.id].fault_href:C[row.id].href)||"#":row.href||"#";
const used=key=>(CELLS[key]?.tests||0)>0;
const levelUsed=level=>BOUNDS.some(bound=>used(cellKey(level,bound)));
const boundUsed=bound=>LEVELS.some(level=>used(cellKey(level,bound)));
const topLevel=[...LEVELS].reverse().find(levelUsed)||LEVELS[0];
const topBound=[...BOUNDS].reverse().find(boundUsed)||BOUNDS[0];

// Facets of the shared filters: what a contract can be narrowed by. Each layer's panel shows the ones that fit it.
function profileStates(c){
 const beyond=c.cells.some(([level,bound])=>!wants(c,level,bound)),missing=c.target.some(([level,bound])=>!cellOf(c,level,bound));
 return beyond||missing?[...(beyond?["beyond"]:[]),...(missing?["missing"]:[])]:["exact"];
}
const detectBand=c=>{const value=ratio(c);return value===null?"none":value<.5?"low":value<.8?"mid":"high"};
// The swatch of an option matches the colour it has in the layer, so the panel reads as the layer's legend.
const swatchHtml=style=>!style?"":style==="hatch"||style==="gap"?mapSwatch(style):style==="pale"?mapSwatch("pale","var(--tf-dm-sub)"):mapSwatch("",style);
const FACETS={
 cell:{label:"Cell",pipe:true,name:key=>{const[level,bound]=key.split("|");return LEVEL_NAME[level]+" × "+BOUND_NAME[bound]},valid:key=>key.includes("|"),test:(row,key)=>C[row.id].cells.some(cell=>cellKey(cell[0],cell[1])===key)},
 producer:{label:"Substitute or recording",title:"Substitutes and recordings",help:"The tools that stand in for real services in the tests, with how well each one has been checked against the real thing.",name:key=>P[key]?.title||key,valid:key=>key in P,test:(row,key)=>C[row.id].producers.includes(key),panel:()=>leversHtml()},
 profile:{label:"Against the profile",help:"Whether a contract's tests sit exactly where its verification profile asks, somewhere else too, or are missing where it asks.",options:[["exact","As the profile asks"],["beyond","Beyond the profile"],["missing","Required cell without tests"]],test:(row,key)=>profileStates(C[row.id]).includes(key),swatch:value=>swatchHtml({exact:cssVar("--tf-dm-sub"),beyond:"pale",missing:"gap"}[value])},
 detect:{label:"Mutants caught",help:"Share of small deliberate bugs in the contract's own code that its own tests catch.",options:[["high","80% and more"],["mid","50–79%"],["low","Below 50%"],["none","Not measured"]],test:(row,key)=>detectBand(C[row.id])===key,swatch:value=>swatchHtml({high:"color-mix(in oklab, var(--tf-dm-det-hi) 92%, var(--tf-dm-det-lo))",mid:"color-mix(in oklab, var(--tf-dm-det-hi) 65%, var(--tf-dm-det-lo))",low:"color-mix(in oklab, var(--tf-dm-det-hi) 30%, var(--tf-dm-det-lo))",none:"hatch"}[value])},
 // Empty levels and boundaries stay (disabled) because they show the ceiling.
 deepest:{label:"Deepest test level",keepEmpty:value=>value!=="notests",options:[...LEVELS.map(level=>[level,LEVEL_NAME[level]]),["notests","No passing tests"]],test:(row,key)=>(C[row.id].deepest||"notests")===key,swatch:value=>swatchHtml(value==="notests"?cssVar("--tf-dm-empty"):cssVar("--tf-dm-lv-"+LEVELS.indexOf(value)))},
 real:{label:"Most realistic boundary",keepEmpty:value=>value!=="notests",options:[...BOUNDS.map(bound=>[bound,BOUND_NAME[bound]]),["notests","No passing tests"]],test:(row,key)=>(C[row.id].real||"notests")===key,swatch:value=>swatchHtml(value==="notests"?cssVar("--tf-dm-empty"):cssVar(BOUND_VAR[value]))},
 trust:{label:"Model validation",options:["na","l0","l1","l2","l3","l4"].map(level=>[level,TRUST_NAME[level]]),test:(row,key)=>C[row.id].trust===key,swatch:value=>swatchHtml(cssVar(TRUST_VAR[value]))},
 reason:{label:"Not measured because",options:Object.entries(REASON).map(([key,[label]])=>[key,label]),test:(row,key)=>!C[row.id].detect&&C[row.id].reason===key,swatch:()=>swatchHtml("hatch")}
};

// Hover card: a contract shows its own matrix, the same grid as its Contract Evidence page.
// A required cell shows covered/required cases, exactly as the Contract Evidence matrix counts them;
// a cell beyond the profile shows +tests; goal and capability checks show their passing tests.
function miniMatrix(entity){
 let html='<div class="tf-depth-mm"><span></span>'+BOUNDS.map(bound=>'<span class="h">'+BOUND_SHORT[bound]+"</span>").join("");
 const seen={cases:false,count:false,extra:false,gap:false};
 LEVELS.forEach(level=>{
   html+='<span class="r">'+LEVEL_SHORT[level]+"</span>";
   BOUNDS.forEach(bound=>{
     const cell=cellOf(entity,level,bound),req=wants(entity,level,bound),cases=caseOf(entity,level,bound);
     let text="",style="",cls="c";
     if(req){
       if(cases){text=cases[2]+"/"+cases[3];seen.cases=true}
       else if(cell){text=String(cell[2]);seen.count=true}
       if(cell)style=' style="background:'+shade(bound,true)+'"';else{cls+=" gap";seen.gap=true;if(!cases)text="0"}
     }else if(cell){text="+"+cell[2];style=' style="background:'+shade(bound,false)+'"';seen.extra=true}
     html+='<span class="'+cls+'"'+style+">"+text+"</span>";
   });
 });
 const notes=[seen.cases?"covered/required cases":"",seen.count?"passing checks":"",seen.extra?"+n: tests beyond the profile":"",seen.gap?"dashed: required, no test":""].filter(Boolean);
 return html+'<span class="tf-depth-mm-note">'+notes.join(" · ")+"</span></div>";
}
// What a layer says about a contract: its value there, the card's pill and the All layers foot.
const SAYS={
 overall:c=>c.deepest?LEVEL_SHORT[c.deepest]+" × "+BOUND_NAME[c.real]:"No passing tests",
 level:c=>c.deepest?LEVEL_NAME[c.deepest]:"No passing tests",
 boundary:c=>c.real?BOUND_NAME[c.real]:"No passing tests",
 trust:c=>TRUST_NAME[c.trust]||c.trust,
 detect:c=>c.detect?pct(ratio(c))+" ("+c.detect[0]+"/"+c.detect[1]+")":"Not measured"
};
const says=(row,key)=>isLeaf(row)?{text:SAYS[key](C[row.id]),tone:""}:null;
function contractTip(row){
 const c=C[row.id],kinds=Object.entries(c.kinds).sort((a,b)=>b[1]-a[1]).map(([kind,count])=>count+" "+(kind==="bdd"?"BDD":kind)).join(", ");
 const covered=(c.cases||[]).reduce((sum,cell)=>sum+cell[2],0),required=(c.cases||[]).reduce((sum,cell)=>sum+cell[3],0);
 let body='<div class="sub">Own evidence by test level and boundary</div>'+miniMatrix(c);
 if(required)body+='<span>Required cases covered</span><span class="value">'+covered+" of "+required+"</span>";
 body+='<span>Own passing tests</span><span class="value">'+c.tests+"</span>"+(kinds?'<span class="note">'+kinds+"</span>":"");
 if(c.failing)body+='<span class="note">'+plural(c.failing,"failing test is","failing tests are")+" left out here; the Health Map shows failures.</span>";
 const substitutes={};
 c.cells.forEach(cell=>Object.entries(cell[3]).forEach(([id,count])=>{substitutes[id]=(substitutes[id]||0)+count}));
 const list=Object.entries(substitutes);
 if(list.length)body+='<div class="sub">Substitutes and recordings</div>'+list.map(([id,count])=>"<span>"+escapeHtml(P[id]?.title||id)+" · "+String(P[id]?.level||"").toUpperCase()+'</span><span class="value">'+plural(count,"test","tests")+"</span>").join("");
 const value=ratio(c);
 body+='<div class="sub">Mutants caught</div>'+(value===null?'<span class="note">Not measured: '+escapeHtml((REASON[c.reason]||["",c.reason])[1])+"</span>":"<span>Caught by its own tests</span><span class=\"value\">"+c.detect[0]+" of "+c.detect[1]+" · "+pct(value)+"</span>");
 if(c.classes.required)body+="<span>Required fault classes detected</span><span class=\"value\">"+(c.classes.caught||0)+" of "+c.classes.required+"</span>";
 return body;
}
function containerTip(row){
 const list=tree.inside(row).map(item=>C[item.id]),own=CHECKS[row.id];
 const byLevel=LEVELS.filter(level=>list.some(c=>c.deepest===level)).map(level=>"<span>"+LEVEL_NAME[level]+'</span><span class="value">'+list.filter(c=>c.deepest===level).length+"</span>").join("");
 const byBound=BOUNDS.filter(bound=>list.some(c=>c.real===bound)).map(bound=>"<span>"+BOUND_NAME[bound]+'</span><span class="value">'+list.filter(c=>c.real===bound).length+"</span>").join("");
 const measured=list.filter(c=>c.detect),middle=median(measured.map(ratio));
 let body='<span>Contracts inside</span><span class="value">'+list.length+"</span>";
 if(own&&(own.cells.length||own.target.length))body+='<div class="sub">Its own integration and validation checks</div>'+miniMatrix(own);
 body+='<div class="sub">Deepest level of its contracts</div>'+byLevel+'<div class="sub">Most real boundary</div>'+byBound
   +'<div class="sub">Mutants caught</div><span>Measured</span><span class="value">'+measured.length+" of "+list.length+(middle===null?"":" · median "+pct(middle))+"</span>";
 return body;
}
const describe=row=>({body:isLeaf(row)?contractTip(row):containerTip(row)});

// Projections: sequential scales, no red or green, because this page measures and does not judge.
const FILL={
 level:c=>c.deepest?cssVar("--tf-dm-lv-"+LEVELS.indexOf(c.deepest)):cssVar("--tf-dm-empty"),
 boundary:c=>c.real?cssVar(BOUND_VAR[c.real]):cssVar("--tf-dm-empty"),
 trust:c=>cssVar(TRUST_VAR[c.trust]||"--tf-dm-local"),
 detect:c=>{const value=ratio(c);return value===null?"url(#tf-depth-hatch)":"color-mix(in oklab, var(--tf-dm-det-hi) "+Math.round(100*value)+"%, var(--tf-dm-det-lo))"}
};
// A layer's colours on the map; Overall shows as rings, so the map keeps the colours it has.
function paint(entries,key){
 if(!FILL[key])return;
 entries.forEach(entry=>{if(entry.kind==="leaf")entry.shape.style.fill=FILL[key](C[entry.row.id])});
}
const countOf=test=>leaves.filter(row=>test(C[row.id])).length;
// The legend of each layer: its colours with their counts. On Overall the colour swatches always show; the encoding
// swatches fold into the "?" on narrow screens, and short names keep the legend on one line at desktop widths.
function legendHtml(key){
 const item=(color,label,count,extra)=>mapLegendItem(mapSwatch("",color),label,count,extra);
 if(key==="overall")return{items:BOUNDS.map(bound=>item(cssVar(BOUND_VAR[bound]),BOUND_NAME[bound])).join("")
     +item(cssVar("--tf-dm-sub"),"Required",undefined,true)+mapLegendItem(mapSwatch("pale","var(--tf-dm-sub)"),"Beyond the profile",undefined,true)+mapLegendItem(mapSwatch("gap"),"Missing",undefined,true)
     +item(cssVar("--tf-dm-det-hi"),"Mutants caught",undefined,true)+mapLegendItem(mapSwatch("hatch"),"Not measured",undefined,true),
   help:"Inside out: goals and capabilities, then one ring per test level from component to acceptance, and the share of mutants caught at the edge; solid cells are required by the profile, pale ones go beyond it, dashed ones are required but have no test."};
 if(key==="level")return{items:LEVELS.map((level,index)=>item(cssVar("--tf-dm-lv-"+index),LEVEL_NAME[level],countOf(c=>c.deepest===level))).join(""),help:"its colour is the deepest test level its own tests reach."};
 if(key==="boundary")return{items:BOUNDS.map(bound=>item(cssVar(BOUND_VAR[bound]),BOUND_NAME[bound],countOf(c=>c.real===bound))).join(""),help:"its colour is the most realistic boundary its own tests talk to."};
 if(key==="trust")return{items:["na","l0","l1","l2","l3","l4"].filter(level=>level==="na"||level==="l0"||countOf(c=>c.trust===level)).map(level=>item(cssVar(TRUST_VAR[level]),TRUST_NAME[level],countOf(c=>c.trust===level))).join(""),help:"its colour is how well the models behind its substitutes and recordings have been checked against the real service."};
 const measured=countOf(c=>c.detect);
 return{items:'<span>0% <i class="tf-depth-grad"></i> 100% caught <b>'+measured+"</b></span>"+mapLegendItem(mapSwatch("hatch"),"Not measured",leaves.length-measured),help:"its colour is the share of mutants its own tests catch, hatched where it is not measured."};
}

// Overall's rings beyond the shared core: one ring per test level, where colour is the boundary and saturation the
// profile, and the share of mutants caught at the edge.
function ringBands(outer){
 const lv0=RING_CORE.rays*outer,det=[.905*outer,outer],lvEnd=det[0]-Math.max(4,.028*outer),band=(lvEnd-lv0)/LEVELS.length,sep=Math.max(1,.006*outer);
 const levels=LEVELS.map((level,index)=>[lv0+index*band,lv0+(index+1)*band-sep]);
 return{levels,det,names:[...LEVELS.map((level,index)=>({labels:[LEVEL_RING[level],LEVEL_SHORT[level]],band:levels[index]})),{labels:["Mutants caught","Mutants"],band:det}],gap:[lv0,50]};
}
function drawRay(parent,c,bands,a0,a1){
 LEVELS.forEach((level,index)=>{
   const[r0,r1]=bands.levels[index],present=BOUNDS.filter(bound=>cellOf(c,level,bound));
   if(!present.length)el("path",{d:arcPath(0,0,r0,r1,a0,a1),class:"tf-depth-ring-track"},parent);
   const step=(r1-r0)/Math.max(1,present.length);
   present.forEach((bound,position)=>{
     const s0=r0+position*step,s1=r0+(position+1)*step-(position<present.length-1?.8:0);
     el("path",{d:arcPath(0,0,s0,s1,a0,a1),style:"fill:"+shade(bound,wants(c,level,bound)),class:"tf-map-tile","data-seg":"cell="+cellKey(level,bound)},parent);
   });
   BOUNDS.forEach(bound=>{if(wants(c,level,bound)&&!cellOf(c,level,bound))el("path",{d:arcPath(0,0,r0+.9,r1-.9,a0+.004,a1-.004),class:"tf-depth-ring-gap"},parent)});
 });
 const[d0,d1]=bands.det,value=ratio(c);
 el("path",{d:arcPath(0,0,d0,d1,a0,a1),class:"tf-depth-ring-track"},parent);
 if(value===null)el("path",{d:arcPath(0,0,d0,d1,a0,a1),style:"fill:url(#tf-depth-hatch)"},parent);
 else if(value>0)el("path",{d:arcPath(0,0,d0,d0+(d1-d0)*value,a0,a1),style:"fill:var(--tf-dm-det-hi)"},parent);
}
const RINGS={
 bands:ringBands,
 // The centre: the deepest cell any test reaches, the ceiling the Overall card names.
 centre:()=>({href:hrefFor(root,"overall"),label:"Deepest cell any test reaches: "+LEVEL_NAME[topLevel]+" × "+BOUND_NAME[topBound],kicker:"DEEPEST",big:LEVEL_SHORT[topLevel],small:"× "+BOUND_NAME[topBound]}),
 // A ray is one link; a transparent band over it takes the pointer, the card and the outline of Changes.
 ray:(link,row,a0,a1,geometry)=>{drawRay(link,C[row.id],geometry.bands,a0,a1);return el("path",{d:arcPath(0,0,geometry.core.rays,geometry.outer,a0,a1),fill:"transparent"},link)},
 rayThumb:(row,a0,a1,geometry)=>{const box=document.createElementNS(NS,"g");drawRay(box,C[row.id],geometry.bands,a0,a1);return box.innerHTML}
};

// The side panel follows the layer and shows only the controls that match what it shows. The matrix and the
// substitutes are the Depth Map's own sections; the shared filters draw the rest.
const PANELS={
 overall:{title:"Test level × boundary",help:"Point at a cell to light its part of every ray, or click it to keep only the contracts with tests there.",before:()=>matrixHtml(),facets:["producer","profile","detect"]},
 level:{title:"Test level",help:"Point at a level to light its contracts on the map, or click it to keep only them.",facets:["deepest"]},
 boundary:{title:"Boundary",help:"Point at a boundary or a tool to light its contracts on the map, or click it to keep only them.",facets:["real","producer"]},
 trust:{title:"Model validation",help:"Point at a level or a tool to light its contracts on the map, or click it to keep only them.",facets:["trust","producer"]},
 detect:{title:"Mutants caught",help:"Point at a band or a reason to light its contracts on the map, or click it to keep only them.",facets:["detect","reason"]}
};
function matrixHtml(){
 const filters=map.filters;
 const voidNames=[...BOUNDS.filter(bound=>!boundUsed(bound)).map(bound=>BOUND_NAME[bound]),...LEVELS.filter(level=>!levelUsed(level)).map(level=>LEVEL_NAME[level])];
 // Empty columns and rows stay visible but narrow: they are the ceiling, not noise.
 return mapMatrix({label:"Contracts by test level and boundary",template:"4.9rem "+BOUNDS.map(bound=>boundUsed(bound)?"minmax(0,1fr)":"1.9rem").join(" "),
   columns:BOUNDS.map(bound=>({bound,label:BOUND_SHORT[bound],title:BOUND_NAME[bound],void:!boundUsed(bound),swatch:mapSwatch("",cssVar(BOUND_VAR[bound]))})),
   rows:LEVELS.map(level=>{const reach=leaves.filter(row=>BOUNDS.some(bound=>cellOf(C[row.id],level,bound))).length;return{level,label:LEVEL_NAME[level],small:reach?plural(reach,"contract","contracts"):"none",void:!levelUsed(level)}}),
   cell:({level},{bound})=>{
     const key=cellKey(level,bound),system=CELLS[key],name=LEVEL_NAME[level]+" × "+BOUND_NAME[bound];
     const all=leaves.filter(row=>cellOf(C[row.id],level,bound)),hits=all.filter(row=>filters.matches(row,"cell"));
     const required=hits.filter(row=>wants(C[row.id],level,bound)).length,beyond=hits.length-required,missing=leaves.filter(row=>wants(C[row.id],level,bound)&&!cellOf(C[row.id],level,bound)).length;
     if(!system?.tests&&!all.length)return{empty:true,void:!levelUsed(level)||!boundUsed(bound),title:name+(missing?": required by "+missing+", no tests":": no tests"),mark:missing?"!":""};
     const producers=Object.entries(system?.producers||{}).sort((a,b)=>b[1]-a[1]);
     return{facet:"cell",value:key,pressed:filters.sets.cell.has(key),hits:hits.length,all:all.length,fill:cssVar(BOUND_VAR[bound]),
       tip:name+": "+plural(hits.length,"contract","contracts")+(hits.length!==all.length?" of "+all.length:"")+", "+(beyond?required+" required by their profile and "+beyond+" beyond it":"all required by their profile")+", "+plural(system?.tests||0,"test","tests")+(system?.checks?" including "+plural(system.checks,"goal or capability check","goal or capability checks"):"")
         +(producers.length?", run against "+listed(producers.map(([id])=>(P[id]?.title||id)+" ("+String(P[id]?.level||"").toUpperCase()+")")):"")+".",
       lines:[plural(system?.tests||0,"test","tests"),...(all.some(row=>!wants(C[row.id],level,bound))?[required+" required",beyond+" beyond"]:["all required"])],
       extra:producers.length?'<i class="tf-depth-prod">'+producers.map(([id,count])=>'<i style="width:'+(100*count/system.tests)+"%;background:var("+TRUST_VAR[P[id]?.level]+')"></i>').join("")+"</i>":""};
   }})
   +(voidNames.length?'<p class="tf-depth-fact"><i class="fa-solid fa-circle-info" aria-hidden="true"></i>No test reaches '+escapeHtml(voidNames.join(" or "))+".</p>":"");
}
function leversHtml(){
 const filters=map.filters;
 return Object.entries(P).sort((a,b)=>b[1].tests-a[1].tests).map(([id,p])=>{
   const count=leaves.filter(row=>filters.matches(row,"producer")&&C[row.id].producers.includes(id)).length,pressed=filters.sets.producer.has(id);
   return'<button type="button" class="tf-depth-lever" data-facet="producer" data-value="'+id+'" aria-pressed="'+pressed+'"'+(count||pressed?"":" disabled")+'><span class="tf-depth-trust" style="background:var('+TRUST_VAR[p.level]+')">'+p.level.toUpperCase()+'</span><span class="tf-depth-lever-name">'+escapeHtml(p.title)+"<small>"+escapeHtml(p.referent?"Checked against "+p.referent:"Not checked against the real service")+'</small></span><span class="tf-depth-lever-count"><b>'+p.tests+"</b> tests<br><b>"+count+"</b> contracts</span></button>";
 }).join("");
}
// Pointing at a contract lights its cells and options through the shared filters; the matrix also dashes the cells
// its profile requires where it has no test.
function markCells(row,panel){
 const c=row?C[row.id]:null;
 panel.querySelectorAll('.tf-map-mx-cell[data-facet="cell"]').forEach(node=>{
   const[level,bound]=node.dataset.value.split("|");
   node.classList.toggle("gapcell",!!c&&wants(c,level,bound)&&!cellOf(c,level,bound));
 });
}

// The contracts table: the Depth Map's columns and groups.
function sortValue(row,key){
 const c=C[row.id];
 if(LEVELS.includes(key))return c.cells.filter(cell=>cell[0]===key).reduce((sum,cell)=>sum+cell[2],0);
 if(key==="trust")return["na","l4","l3","l2","l1","l0"].indexOf(c.trust);
 if(key==="detect"){const value=ratio(c);return value===null?-1:value}
 if(key==="classes")return c.classes.required?(c.classes.caught||0)/c.classes.required:-1;
 return c.tests;
}
function stats(list){
 const cs=list.map(row=>C[row.id]),measured=cs.filter(c=>c.detect),middle=median(measured.map(ratio));
 const tests=cs.reduce((sum,c)=>sum+c.tests,0),l0=cs.filter(c=>c.trust==="l0").length,beyond=cs.filter(c=>profileStates(c).includes("beyond")).length;
 return plural(tests,"own test","own tests")+" · mutants caught "+(measured.length?"median "+pct(middle)+" ("+measured.length+" measured)":"not measured")+(l0?" · "+l0+" on L0":"")+(beyond?" · "+beyond+" beyond profile":"");
}
function rowCells(row){
 const c=C[row.id],value=ratio(c);
 const levels=LEVELS.map(level=>{
   let chips="";
   BOUNDS.forEach(bound=>{
     const cell=cellOf(c,level,bound),req=wants(c,level,bound),cases=caseOf(c,level,bound);
     if(req&&cell)chips+='<span class="tf-depth-cchip" style="background:'+shade(bound,true)+'" title="'+escapeHtml(BOUND_NAME[bound]+": "+(cases?cases[2]+" of "+cases[3]+" required cases covered by ":"")+plural(cell[2],"test","tests"))+'">'+BOUND_SHORT[bound]+" "+(cases?cases[2]+"/"+cases[3]:cell[2])+"</span>";
     else if(cell)chips+='<span class="tf-depth-cchip extra" style="background:'+shade(bound,false)+'" title="'+escapeHtml(BOUND_NAME[bound]+": "+plural(cell[2],"test","tests")+" beyond the profile")+'">'+BOUND_SHORT[bound]+" +"+cell[2]+"</span>";
     else if(req)chips+='<span class="tf-depth-cchip gap" title="'+escapeHtml(BOUND_NAME[bound]+": required by the profile, no passing test")+'">'+BOUND_SHORT[bound]+" "+(cases?"0/"+cases[3]:"0")+"</span>";
   });
   return'<td class="lv'+(levelUsed(level)?"":" void")+'">'+chips+"</td>";
 }).join("");
 return levels
   +"<td>"+(c.trust==="na"?'<span class="tf-map-muted">—</span>':'<span class="tf-depth-trust" style="background:var('+TRUST_VAR[c.trust]+')">'+c.trust.toUpperCase()+"</span>")+"</td>"
   +"<td>"+(value===null?'<span class="tf-map-muted" title="'+escapeHtml((REASON[c.reason]||["",c.reason])[1])+'">'+escapeHtml((REASON[c.reason]||[c.reason])[0])+"</span>":'<a href="'+escapeHtml(c.fault_href)+'" class="tf-map-muted"><span class="tf-depth-detbar"><i style="width:'+pct(value)+'"></i></span>'+pct(value)+" · "+c.detect[0]+"/"+c.detect[1]+"</a>")+"</td>"
   +'<td class="tf-map-num">'+(c.classes.required?(c.classes.caught||0)+"/"+c.classes.required:'<span class="tf-map-muted">—</span>')+"</td>"
   +'<td class="tf-map-num">'+c.tests+"</td>";
}
function groupKeys(row,group){
 const c=C[row.id];
 if(group==="level")return[c.deepest||"none"];
 if(group==="boundary")return[c.real||"none"];
 if(group==="producer")return c.producers.length?c.producers:["none"];
 return[detectBand(c)];
}
function groupName(group,key){
 if(group==="level")return LEVEL_NAME[key]||"No passing tests";
 if(group==="boundary")return BOUND_NAME[key]||"No passing tests";
 if(group==="producer")return key==="none"?"No substitute":(P[key]?.title||key)+" · "+String(P[key]?.level||"").toUpperCase();
 return FACETS.detect.name(key);
}
function groupOrder(group,keys){
 const order={level:[...LEVELS,"none"].reverse(),boundary:[...BOUNDS,"none"].reverse(),producer:[...Object.keys(P).sort((a,b)=>P[b].tests-P[a].tests),"none"],detect:["high","mid","low","none"]}[group];
 return order.filter(key=>keys.includes(key));
}
function csvLine(row){
 const c=C[row.id],value=ratio(c);
 return[c.cells.map(cell=>cell[0]+"×"+cell[1]+":"+cell[2]).join("; "),(c.cases||[]).map(cell=>cell[0]+"×"+cell[1]+":"+cell[2]+"/"+cell[3]).join("; "),(c.cases||[]).reduce((sum,cell)=>sum+cell[2],0),(c.cases||[]).reduce((sum,cell)=>sum+cell[3],0),c.deepest||"",c.real||"",c.trust,
   c.producers.map(id=>P[id]?.title||id).join("; "),c.detect?c.detect[0]:"",c.detect?c.detect[1]:"",value===null?"":value.toFixed(3),c.reason?(REASON[c.reason]||[c.reason])[0]:"",c.classes.required||0,c.classes.caught||0,c.tests];
}
const TABLE={
 columns:[...LEVELS.map(level=>[level,LEVEL_SHORT[level],LEVEL_NAME[level]+" tests: covered/required cases, or +tests beyond the profile",levelUsed(level)?"":"void"]),["trust","Model","Weakest check of the models behind its substitutes and recordings"],["detect","Mutants caught","Mutants caught by its own tests"],["classes","Classes","Required fault classes detected","tf-map-num"],["tests","Tests","Its own passing tests","tf-map-num"]],
 groups:[["level","Test level"],["boundary","Boundary"],["producer","Substitute"],["detect","Mutants caught"]],
 keys:groupKeys,name:groupName,order:groupOrder,sortValue,stats,cells:rowCells,
 csv:{file:"verification-depth.csv",head:["tests_per_cell","required_cases_per_cell","required_cases_covered","required_cases","deepest_level","most_realistic_boundary","model_validation","substitutes_and_recordings","mutants_caught","mutants_judged","share_caught","not_measured_reason","required_fault_classes","detected_fault_classes","own_passing_tests"],line:csvLine}
};

// What each layer says, for its card and its row in the All layers table: the number first, then what it counts.
function layerFacts(key){
 const measured=leaves.map(row=>C[row.id]).filter(c=>c.detect),middle=median(measured.map(ratio));
 const usedCells=Object.values(CELLS).filter(cell=>cell.tests).length;
 return{
   overall:["<b>"+usedCells+"</b> of 20 cells","up to "+LEVEL_SHORT[topLevel].toLowerCase()+" × "+BOUND_NAME[topBound].toLowerCase()],
   level:["<b>"+countOf(c=>c.deepest===topLevel)+"</b> at "+LEVEL_SHORT[topLevel].toLowerCase(),"deepest own test"],
   boundary:["<b>"+countOf(c=>c.real==="direct")+"</b> reach live","most realistic test"],
   trust:["<b>"+countOf(c=>c.trust==="l0")+"</b> on L0 models","behind substitutes"],
   detect:["<b>"+(middle===null?"—":pct(middle))+"</b> median",measured.length+" of "+leaves.length+" measured"]
 }[key];
}
function layerCard(key){const[line,note]=layerFacts(key);return{status:line,count:note}}
// In the table row the number folds away on narrow screens, like the verdict word on the Health Map.
function layerRow(key){return{status:'<span class="tf-map-row-word">'+layerFacts(key)[0]+"</span>",count:""}}
// Overall has no single colour per contract, so its row in the All layers table stands each ray upright: as high as
// the contract's deepest level, in the colour of its most realistic boundary. The other rows are the shared ones.
function overallCells(){
 let out="";
 tree.columns.leaves.forEach((leaf,index)=>{
   const c=C[leaf.row.id],x=leaf.x+1,w=MAP_CELL-2,rank=c.deepest?LEVELS.indexOf(c.deepest)+1:0,height=12*rank/LEVELS.length;
   out+='<rect data-leaf="'+index+'" x="'+x+'" y="2" width="'+w+'" height="12" class="tf-depth-ring-track"/>';
   if(rank)out+='<rect x="'+x+'" y="'+fixed(14-height)+'" width="'+w+'" height="'+fixed(height)+'" style="fill:var('+BOUND_VAR[c.real]+')" pointer-events="none"/>';
 });
 return out;
}
// Overall first; the other four measure, so they share one neutral group where the Health Map splits failing from passing.
const layerGroups=()=>[{tone:"",keys:["overall"]},{tone:"",label:"Measured",keys:LAYERS.slice(1).map(layer=>layer[0])}];

// The shared map. Find lists in tree order and shows what Overall says about each contract.
const map=mapPage({
 tree,layers:LAYERS,insights:model.insights,words:key=>CHANGE_WORDS[key],
 href:hrefFor,says,describe,paint,legend:legendHtml,
 facets:FACETS,panels:PANELS,filterRows:leaves,markPanel:markCells,
 strip:{groups:layerGroups,card:layerCard,row:layerRow,cells:key=>key==="overall"?overallCells():undefined},
 table:TABLE,
 tiles:{dots:false,leaf:(row,key)=>'style="fill:'+FILL[key](C[row.id])+'"'},
 rings:RINGS,
 find:(row,index)=>({rank:index,badge:()=>{const pill=says(row,"overall");return pill?'<span class="tf-map-pill">'+escapeHtml(pill.text)+"</span>":""}})
});
map.start();"""

# What the Depth Map does not measure is hatched.
DEPTH_HATCH = (
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>'
    '<pattern id="tf-depth-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    '<rect width="6" height="6" style="fill:var(--tf-dm-empty)"/><rect width="1.6" height="6" style="fill:var(--tf-dm-hatch)"/>'
    "</pattern></defs></svg>"
)


def map_markup(page: str, about: str, legend: str, rings: str, rings_label: str, tiles_label: str) -> str:
    """Everything a map shows: its tools, its layer strip and its frame with both views."""
    return map_tools(about) + map_strip(page, legend) + map_frame(rings, rings_label, tiles_label)


def _article(name: str, title: str, css: str, js: str, markup: str, model_json: str, d3_hierarchy: str) -> str:
    """A map page: its section and heading, the shared styles then its own, its markup, d3-hierarchy, and one script
    with the shared map, the page's facts and the page's description of them."""
    anchor = f"verification-{name}-map"
    return (
        f'<section id="{anchor}">\n'
        f'<h1>{title}<a class="headerlink" href="#{anchor}" title="Link to this heading">#</a></h1>\n'
        f'<style id="tf-{name}-map-style">\n{MAP_SHARED_CSS}\n{css}\n</style>\n'
        f"{markup}\n<script>{d3_hierarchy}</script>\n"
        f"<script>\n(()=>{{\n{MAP_SHARED_JS}\nconst model={model_json};\n{js}\n}})();\n</script>\n</section>"
    )


def health_map_article(model_json: str, d3_hierarchy: str) -> str:
    legend = (
        '<span><i class="tf-map-sw failed"></i>Fail</span>'
        '<span><i class="tf-map-sw passed"></i>Pass</span>'
        '<span><i class="tf-map-sw na"></i>N/A</span>'
        '<span><i class="tf-map-sw own"></i>Own check fails</span>'
    )
    markup = map_markup(
        "Health",
        "This page says whether each contract's evidence is enough; the Depth Map shows how deep it goes.",
        legend,
        "Every contract as a ray through one ring per layer.",
        "Overall health: goals, capabilities and contracts inside, one ring per layer outside",
        "Verification health by goal, capability and contract",
    )
    return _article("health", "Verification Health Map", HEALTH_MAP_CSS, HEALTH_MAP_JS, markup, model_json, d3_hierarchy)


def depth_map_article(model_json: str, d3_hierarchy: str) -> str:
    legend = (
        '<span><i class="tf-map-sw hatch"></i>Not measured</span>'
        '<span class="tf-map-help" data-tip="Every row uses its layer\'s colours; in Overall each bar is as high as '
        'the contract\'s deepest test level and coloured by its most realistic boundary.">?</span>'
    )
    markup = DEPTH_HATCH + map_markup(
        "Depth",
        "This page shows how deep each contract's evidence goes; the Health Map says whether it is enough.",
        legend,
        "Every contract as a ray through one ring per test level.",
        "Overall depth: goals, capabilities and contracts inside, one ring per test level and the share of mutants caught outside",
        "Verification depth by goal, capability and contract",
    )
    return _article("depth", "Verification Depth Map", DEPTH_MAP_CSS, DEPTH_MAP_JS, markup, model_json, d3_hierarchy)
