"""Markup, styles and scripts of the Verification Health Map and the Verification Explorer.

Presentation only: the builder computes every fact and passes it in as a JSON payload. The
file stays outside the evidence-producer qualification fingerprint on purpose, because no
qualification control exercises page rendering; the structural gate checks the rendered page.

The page is one map: one section, one markup (tools line, layer strip with its All layers table,
side panel, rings and map views, contracts table, hover card and Find) and one shared script that
runs it. Health judges every layer (healthMap: failing or passing); beside it the measures say how
deep, how realistic and how strong the evidence is (depthMap, once the Verification Depth Map); and
pairsMap puts each layer's health and its measures on the layer's card.

The Verification Explorer is where a monitor sends a reader for the items behind its counts: every
evidence path, fault class, mutant, own check, support and evidence producer, one row each, with
what it is, how it stands, why it fails and where the details are. It runs on the map's tools line,
filters panel, hints and Find, so both pages filter, link and speak alike.
"""

MAP_SHARED_CSS = r"""/* The Verification Health Map's shared styles: the tools line, hints, the layer strip, both views, the side panel,
   the table, the hover card and Find. Health and the measures add only their palettes and what they judge or
   measure: the tone of a group, the colour of a mark, the words of a status. */
#verification-health-map{--tf-map-ease:cubic-bezier(.2,0,0,1);--tf-map-fast:120ms;--tf-map-medium:180ms;--tf-map-radius:10px;--tf-map-line:color-mix(in srgb,var(--pst-color-text-base) 13%,transparent);--tf-map-line-strong:color-mix(in srgb,var(--pst-color-text-base) 28%,transparent);--tf-map-lineage:color-mix(in srgb,var(--pst-color-text-base) 40%,transparent);--tf-map-selected:color-mix(in srgb,var(--pst-color-text-base) 55%,transparent);--tf-map-ring:color-mix(in srgb,var(--pst-color-text-base) 78%,transparent);--tf-map-goal:color-mix(in srgb,var(--pst-color-text-base) 4.5%,var(--pst-color-background));--tf-map-feature:var(--pst-color-background);--tf-map-radial-goal:color-mix(in srgb,var(--pst-color-text-base) 12%,var(--pst-color-background));--tf-map-radial-feature:color-mix(in srgb,var(--pst-color-text-base) 7%,var(--pst-color-background));--tf-map-raised:color-mix(in srgb,var(--pst-color-text-base) 8%,var(--pst-color-background));--tf-map-up:var(--tf-map-ring);--tf-map-down:var(--tf-map-ring);--tf-map-lift:var(--pst-color-background)}
html[data-theme=dark] #verification-health-map{--tf-map-ring:color-mix(in srgb,var(--pst-color-text-base) 92%,transparent);--tf-map-goal:color-mix(in srgb,var(--pst-color-text-base) 5%,var(--pst-color-background));--tf-map-feature:color-mix(in srgb,var(--pst-color-text-base) 10%,var(--pst-color-background));--tf-map-radial-goal:color-mix(in srgb,var(--pst-color-text-base) 17%,var(--pst-color-background));--tf-map-radial-feature:color-mix(in srgb,var(--pst-color-text-base) 11%,var(--pst-color-background));--tf-map-raised:color-mix(in srgb,var(--pst-color-text-base) 10%,var(--pst-color-background));--tf-map-lift:color-mix(in srgb,var(--pst-color-text-base) 15%,var(--pst-color-background))}
.tf-sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.tf-map-tools{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.35rem 1rem;margin:-.2rem 0 .25rem;font-size:.74rem;color:var(--pst-color-text-muted)}
.tf-map-lead{display:flex;align-items:center;gap:.4rem;flex:1 1 12rem;min-width:0;height:28px;white-space:nowrap}
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
.tf-map-group-cards>.tf-map-tab-wrap{display:flex;flex:1 0 auto;min-width:206px}
.tf-map-tab-wrap>.tf-map-tab{flex:1 0 206px;min-width:0}
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
.tf-map-tab-status{display:grid;min-width:0;font-size:.78rem;white-space:nowrap}
.tf-map-tab-status b{font-weight:750}
.tf-map-count{display:grid;min-width:0;font-size:.72rem;color:var(--pst-color-text-muted);white-space:nowrap}
.tf-map-count-text{min-width:0;overflow:hidden;text-overflow:ellipsis}
/* The lines of every view a card can show sit in one cell, one over the other: only the view its layer opens in is
   seen, and the card is as wide as its widest view, so it keeps its size when the view changes. */
.tf-map-variant{grid-area:1/1;display:flex;align-items:center;min-width:0}
.tf-map-tab-status>.tf-map-variant{gap:.4rem}
.tf-map-variant:not(.on){visibility:hidden}
.tf-map-count b{color:var(--pst-color-text-base);font-weight:700}
.tf-map-thumb{grid-column:2;grid-row:1/span 3;display:block;width:76px;height:auto}
.tf-map-thumb.radial{width:54px;height:54px;justify-self:center}
.tf-map-delta{display:inline-flex;flex:none;gap:.3rem;margin-left:.4rem;font-weight:750}
.tf-map-delta .up{color:var(--tf-map-up,var(--pst-color-text-base))}.tf-map-delta .down{color:var(--tf-map-down,var(--pst-color-text-muted))}
/* A layer with several views shows them on its open card: a slider of their thumbnails grows out of the card, the
   chosen view on a knob that glides between them. Only the slider's two ends are rounded; a view between them is
   square. */
.tf-map-tab-wrap.open>.tf-map-tab{border-top-right-radius:0;border-bottom-right-radius:0;border-right-color:var(--tf-map-line)}
.tf-map-views{position:relative;display:flex;flex:none;align-items:stretch;max-width:0;overflow:hidden;opacity:0;padding:5px 0;border:1px solid transparent;border-left:0;border-radius:0 var(--tf-map-radius) var(--tf-map-radius) 0;transition:max-width 360ms var(--tf-map-ease),opacity 220ms var(--tf-map-ease),padding 360ms var(--tf-map-ease),border-color var(--tf-map-medium) var(--tf-map-ease),background-color var(--tf-map-medium) var(--tf-map-ease)}
/* The open slider is as wide as its track, its 5 + 6 px padding and its 1 px border, so it grows and folds over the
   whole transition. */
.tf-map-tab-wrap.open>.tf-map-views{max-width:calc(var(--tf-map-track-w,508px) + 12px);opacity:1;padding:5px 6px 5px 5px;border-color:var(--tf-map-selected);background:var(--tf-map-raised)}
/* Three views or more open part way: one and a half of them in sight (the slider's padding and border added), and
   the cut one fades under a +N that shows them all. The fade is the button, with no pill of its own, so it cannot be
   taken for the strip's scroll edges. */
.tf-map-tab-wrap.open.peek>.tf-map-views{max-width:calc(var(--tf-map-peek-w,120px) + 6px)}
.tf-map-views-more{position:absolute;top:5px;right:0;bottom:5px;z-index:3;display:flex;flex-direction:column;align-items:flex-end;justify-content:center;gap:3px;width:42px;padding:0 7px 0 0;border:0;border-radius:0 var(--tf-map-radius) var(--tf-map-radius) 0;background:linear-gradient(90deg,transparent 10%,var(--tf-map-raised) 80%);color:var(--pst-color-text-muted);font:inherit;font-size:.66rem;font-weight:750;line-height:1;cursor:pointer;opacity:0;visibility:hidden;transition:opacity var(--tf-map-medium) var(--tf-map-ease),visibility var(--tf-map-medium) linear,color var(--tf-map-medium) var(--tf-map-ease)}
.tf-map-views-more i{font-size:.74rem;transition:transform var(--tf-map-medium) var(--tf-map-ease)}
.tf-map-tab-wrap.peek .tf-map-views-more{opacity:1;visibility:visible}
.tf-map-views-more:hover{color:var(--pst-color-text-base)}
.tf-map-views-more:hover i{transform:translateX(2px)}
.tf-map-views-more:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:-2px}
.tf-map-views-track{position:relative;flex:none;display:grid;grid-auto-flow:column;grid-auto-columns:1fr;-webkit-user-select:none;user-select:none;border:1px solid var(--tf-map-line-strong);border-radius:8px;background:color-mix(in srgb,var(--pst-color-text-base) 5%,var(--pst-color-background));box-shadow:inset 0 1px 2px rgba(0,0,0,.28)}
html:not([data-theme=dark]) .tf-map-views-track{box-shadow:inset 0 1px 2px rgba(0,0,0,.1)}
.tf-map-choice{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;min-width:74px;padding:3px 10px;border:0;border-left:1px solid var(--tf-map-line);background:none;color:var(--pst-color-text-muted);font:inherit;font-size:.68rem;font-weight:650;line-height:1.15;white-space:nowrap;cursor:pointer;transition:color var(--tf-map-medium) var(--tf-map-ease)}
.tf-map-knob+.tf-map-choice{border-left:0}
.tf-map-choice:hover{color:var(--pst-color-text-base)}
.tf-map-choice[aria-checked=true],.tf-map-choice.near{color:var(--pst-color-text-base)}
.tf-map-choice[aria-checked=true]{font-weight:750}
/* The chosen name is bolder: every name keeps room for its bold width, so the slider never changes width. */
.tf-map-choice-name{display:inline-grid;justify-items:center}
.tf-map-choice-name::after{content:attr(data-name);height:0;overflow:hidden;visibility:hidden;font-weight:750}
.tf-map-choice:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:-2px}
.tf-map-choice .tf-map-thumb{width:54px;height:30px}
/* A view with nothing to show under the filters stays in its place, faded; its hint says why. */
.tf-map-choice.idle .tf-map-thumb{opacity:.28;filter:grayscale(1)}
.tf-map-choice.idle .tf-map-choice-name{opacity:.6}
.tf-map-knob{position:absolute;top:0;bottom:0;left:0;width:0;border:1px solid var(--tf-map-selected);border-radius:0;background:var(--tf-map-lift);box-shadow:0 1px 3px rgba(0,0,0,.28);transition:transform 280ms var(--tf-map-ease),width 280ms var(--tf-map-ease),border-radius 280ms var(--tf-map-ease),scale 120ms var(--tf-map-ease);pointer-events:none}
.tf-map-knob.first{border-radius:7px 0 0 7px}
.tf-map-knob.last{border-radius:0 7px 7px 0}
.tf-map-knob.only{border-radius:7px}
.tf-map-knob.instant{transition:none}
/* The chosen view can be dragged along the track: pressed, the knob shrinks a little; dragged, it follows the pointer
   and takes the shape of the place it would land in. */
.tf-map-knob.pressed{scale:.94}
.tf-map-views.dragging .tf-map-knob{transition:border-radius 280ms var(--tf-map-ease),scale 120ms var(--tf-map-ease)}
.tf-map-views:not(.lone) .tf-map-choice[aria-checked=true]{cursor:grab;touch-action:pan-y}
.tf-map-views.dragging,.tf-map-views.dragging .tf-map-choice{cursor:grabbing}
/* A closed card with several views shows a dot for each under its mini-map, the one it opens in filled. */
.tf-map-dots{grid-column:2;grid-row:3;align-self:end;justify-self:center;display:flex;gap:3px;margin-bottom:-5px;transition:opacity var(--tf-map-medium) var(--tf-map-ease)}
.tf-map-dots>i{width:4px;height:4px;border-radius:50%;background:var(--tf-map-line-strong)}
.tf-map-dots>i.on{background:var(--pst-color-text-muted)}
.tf-map-tab:hover>.tf-map-dots>i.on{background:var(--pst-color-text-base)}
.tf-map-tab-wrap.open .tf-map-dots{opacity:0}
@media(max-width:640px){.tf-map-tab[aria-selected=true]>.tf-map-dots{opacity:0}}
/* A narrow page has no room beside the open card: the open layer's views take a row of their own under the strip,
   a lone view too, so the row keeps its height from layer to layer. */
.tf-map-views-row{display:none}
@media(max-width:640px){
.tf-map-views-row{display:flex;height:60px;margin:-.2rem 0 .7rem}
.tf-map-views-row>.tf-map-views{flex:1 1 auto;max-width:none;opacity:1;padding:0;border:0;background:none}
.tf-map-views-row .tf-map-views-track{flex:1 1 auto}
.tf-map-views-row .tf-map-choice{min-width:0}
}
.tf-map-thumb.tabular .tf-map-thumb-name{fill:var(--pst-color-text-muted);opacity:.6}
.tf-map-thumb.tabular .tf-map-thumb-cell{fill:var(--tf-map-line-strong)}
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
/* A layer's other views are rows below it in the All layers table. */
.tf-map-row.sub .tf-map-row-name{padding-left:.9rem;font-weight:550;color:var(--pst-color-text-muted)}
.tf-map-row.sub .tf-map-row-name::before{content:"↳ ";opacity:.6}
.tf-map-band{position:absolute;top:0;bottom:0;border-radius:3px;background:color-mix(in srgb,var(--tf-map-ring) 14%,transparent);box-shadow:0 0 0 1px color-mix(in srgb,var(--tf-map-ring) 65%,transparent);opacity:0;pointer-events:none;transition:opacity var(--tf-map-fast) var(--tf-map-ease)}
.tf-map-band.visible{opacity:1}
.tf-map-table-foot{min-height:2.7em;font-size:.72rem;line-height:1.35;color:var(--pst-color-text-muted)}
.tf-map-table-foot b{font-weight:650;color:var(--pst-color-text-base)}
.tf-map-mark{white-space:nowrap}
@container (max-width:760px){.tf-map-row{--tf-row-head:176px}.tf-map-row-word{display:none}}
@container (max-width:600px){.tf-map-table-legend{order:3;flex-basis:100%}}
@container (max-width:480px){.tf-map-row{--tf-row-head:118px}.tf-map-row-count{display:none}.tf-map-row-head{grid-template-columns:minmax(0,1fr) auto}}
@media(prefers-reduced-motion:reduce){.tf-map-action,.tf-map-tab,.tf-map-hint,.tf-map-edge,.tf-map-edge button,.tf-map-table,.tf-map-table-toggle,.tf-map-chevron,.tf-map-row,.tf-map-band{animation:none!important;transition:none!important}}
/* The view: the legend bar with the count and Rings/Table, the side panel with its filters, the stage
   with one height for every view, and the contracts table. */
#verification-health-map{--tf-map-panel:400px}
.bd-article-container:has(#verification-health-map){overflow:visible}
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
/* The legend bar is one line in every view, so nothing below it ever moves: aligned with the view it explains (it
   slides with the view when the panel opens beside it), it keeps what fits and opens the rest from a +N. */
.tf-map-legendbar{position:relative;display:flex;align-items:center;height:30px;margin:0 0 .65rem;padding-left:0;transition:padding-left 240ms var(--tf-map-ease)}
@media(min-width:961px){.tf-map-legendbar:has(+ .tf-map-body.panel-open){padding-left:calc(var(--tf-map-panel) + 16px)}}
.tf-map-legendbar:has(+ .tf-map-still){transition:none}
.tf-map-legendbar>.tf-map-legend{flex:1 1 auto}
.tf-map-legend{display:flex;align-items:center;gap:1rem;height:22px;min-width:0;overflow:hidden;white-space:nowrap;font-size:.74rem;color:var(--pst-color-text-muted);transition:opacity var(--tf-map-fast) var(--tf-map-ease)}
.tf-map-legend>span{display:inline-flex;flex:none;align-items:center;gap:.38rem}
.tf-map-legend b,.tf-map-more-pop b{font-weight:700;color:var(--pst-color-text-base);font-variant-numeric:tabular-nums}
.tf-map-legend>.tf-map-help{display:inline-grid}
.tf-map-legend>.tf-map-over{display:none}
.tf-map-legend>.tf-map-ask{display:block;flex:none;overflow:hidden;text-overflow:ellipsis;font-weight:500;color:var(--pst-color-text-base)}
.tf-map-legend.tight>.tf-map-ask{flex:0 1 auto;min-width:4rem}
.tf-map-more{flex:none;height:20px;padding:0 .5rem;border:1px solid var(--tf-map-line-strong);border-radius:999px;background:var(--tf-map-goal);color:var(--pst-color-text-base);font:inherit;font-size:.7rem;font-weight:700;cursor:pointer;transition:border-color var(--tf-map-fast) var(--tf-map-ease),background-color var(--tf-map-fast) var(--tf-map-ease)}
.tf-map-more:hover,.tf-map-more[aria-expanded=true]{border-color:var(--tf-map-selected);background:var(--tf-map-raised)}
.tf-map-more-pop{position:absolute;top:calc(100% + 4px);z-index:30;display:flex;flex-wrap:wrap;gap:.35rem 1rem;max-width:min(26rem,100%);padding:.5rem .7rem;border:1px solid var(--tf-map-line-strong);border-radius:8px;background:var(--pst-color-surface);box-shadow:0 10px 28px rgba(0,0,0,.2);font-size:.74rem;color:var(--pst-color-text-muted);animation:tf-map-drop var(--tf-map-fast) var(--tf-map-ease) both}
.tf-map-more-pop[hidden]{display:none}
.tf-map-more-pop>span{display:inline-flex;align-items:center;gap:.38rem;white-space:nowrap}
/* How many contracts the filters keep, beside their chips. */
.tf-map-filters .tf-map-total{flex:none;color:var(--pst-color-text-muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.tf-map-total b{color:var(--pst-color-text-base)}
/* Kind opens the side panel, the same in every view and apart from the view's own filters below it: each kind a tile
   with its glyph, its name and how many contracts it holds. */
.tf-map-panel-kinds{margin:0 0 .7rem;padding:0 0 .7rem;border-bottom:1px solid var(--tf-map-line-strong)}
.tf-map-panel-top{display:flex;align-items:center;justify-content:space-between;margin:-.15rem 0 .3rem}
.tf-map-panel-top .tf-map-facet-title{margin:0}
.tf-map-kinds{display:flex;gap:2px;padding:2px;border:1px solid var(--tf-map-line);border-radius:9px;background:var(--pst-color-background)}
.tf-map-kind{display:flex;flex:1 1 auto;flex-direction:column;align-items:flex-start;gap:.05rem;min-width:0;padding:.25rem .55rem .3rem;border:1px solid transparent;border-radius:7px;background:none;color:var(--pst-color-text-muted);font:inherit;font-size:.7rem;font-weight:600;text-align:left;cursor:pointer;transition:background-color var(--tf-map-fast) var(--tf-map-ease),color var(--tf-map-fast) var(--tf-map-ease)}
.tf-map-kind-name{display:inline-flex;align-items:center;gap:.35rem;max-width:100%;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.tf-map-kind-name>i,.tf-map-kind-name>svg{flex:none;font-size:.7rem}
.tf-map-kind b{font-size:.9rem;font-weight:750;line-height:1.15;color:var(--pst-color-text-base);font-variant-numeric:tabular-nums}
.tf-map-kind:hover{color:var(--pst-color-text-base)}
.tf-map-kind[aria-pressed=true]{border-color:var(--tf-map-selected);background:var(--tf-map-lift);color:var(--pst-color-text-base);box-shadow:0 1px 3px rgba(0,0,0,.14)}
.tf-map-kind:disabled{opacity:.4;cursor:default}
.tf-map-kind:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:1px}
.tf-map-kind.hit{border-color:var(--tf-map-ring);box-shadow:inset 0 0 0 1.5px var(--tf-map-ring)}
/* How marks split over a view's colours: a view's tab and the group rows of the contracts table. */
.tf-map-spread{display:flex;gap:1px;height:4px;min-width:0;overflow:hidden;border-radius:2px;background:var(--tf-map-line)}
.tf-map-spread>i{flex:1 1 0;min-width:1px}
.tf-map-list-group .tf-map-spread{width:4rem;height:6px}
/* A kind's glyph wherever a mark is named. */
.tf-map-kind-icon{flex:none;width:1.1em;font-size:.86em;text-align:center;color:var(--pst-color-text-muted)}
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
#verification-health-map .tf-map-goal{fill:var(--tf-map-goal);stroke:var(--tf-map-line);stroke-width:1;transition:stroke var(--tf-map-medium) var(--tf-map-ease)}
#verification-health-map .tf-map-feature{fill:var(--tf-map-feature);stroke:var(--tf-map-line);stroke-width:1;transition:stroke var(--tf-map-medium) var(--tf-map-ease)}
#verification-health-map :is(.tf-map-rings,.tf-map-thumb.radial) .tf-map-goal{fill:var(--tf-map-radial-goal)}
#verification-health-map :is(.tf-map-rings,.tf-map-thumb.radial) .tf-map-feature{fill:var(--tf-map-radial-feature)}
.tf-map-tile{transition:fill 120ms var(--tf-map-ease)}
#verification-health-map .tf-map-lineage{stroke:var(--tf-map-lineage)}
#verification-health-map .tf-map-dim{opacity:.13}
#verification-health-map :is(path,rect).tf-map-hit{stroke:var(--tf-map-ring);stroke-width:2.4}
#verification-health-map .tf-map-up{stroke:var(--tf-map-up);stroke-width:3}
#verification-health-map .tf-map-down{stroke:var(--tf-map-down);stroke-width:3;stroke-dasharray:3 2}
.tf-map-sw{display:inline-block;flex:0 0 auto;width:12px;height:12px;border-radius:3px;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--pst-color-text-base) 10%,transparent)}
.tf-map-option .tf-map-sw{width:10px;height:10px}
.tf-map-dot{fill:var(--pst-color-text-muted);transition:opacity var(--tf-map-medium) var(--tf-map-ease),fill var(--tf-map-medium) var(--tf-map-ease)}
.tf-map-label-goal{font-size:13px;font-weight:650;fill:var(--pst-color-text-base)}
.tf-map-label-feature{font-size:12px;font-weight:500;fill:var(--pst-color-text-muted)}
#verification-health-map .tf-map-ring-center{fill:var(--tf-map-goal);stroke:var(--tf-map-line);stroke-width:1}
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
.tf-map-list-bar{display:flex;align-items:center;gap:.9rem;height:28px;margin:0 0 .5rem;font-size:.74rem}
.tf-map-list-bar>.tf-map-seg{flex:0 1 auto;flex-wrap:nowrap;min-width:0;overflow-x:auto;overscroll-behavior-x:contain;scrollbar-width:none}
.tf-map-list-bar>.tf-map-seg::-webkit-scrollbar{display:none}
.tf-map-list-bar>.tf-map-seg button,.tf-map-list-bar>.tf-map-action,.tf-map-list-bar-label{flex:none;white-space:nowrap}
.tf-map-list-bar-label{font-size:.64rem;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-map-summary{flex:1 1 0;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--pst-color-text-muted);font-variant-numeric:tabular-nums}
.tf-map-list-wrap{overflow:auto;border:1px solid var(--tf-map-line);border-radius:10px;animation:tf-map-in 220ms var(--tf-map-ease) both}
.tf-map-list-table{width:100%;border-collapse:separate;border-spacing:0;font-size:.74rem}
.tf-map-list-table th{position:sticky;top:0;z-index:2;padding:.4rem .45rem;border-bottom:1px solid var(--tf-map-line-strong);background:var(--pst-color-background);font-size:.66rem;font-weight:750;text-align:left;white-space:nowrap}
.tf-map-list-table th button{display:inline-flex;align-items:center;gap:.25rem;padding:0;border:0;background:none;color:inherit;font:inherit;cursor:pointer}
.tf-map-list-table th button:hover{text-decoration:underline}
.tf-map-list-table th button:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:2px}
.tf-map-list-table th .dir{font-size:.6rem;color:var(--pst-color-text-muted)}
.tf-map-list-table th.void{color:var(--pst-color-text-muted);font-weight:600}
.tf-map-list-table th.tf-map-th-group{border-bottom-color:var(--tf-map-line);font-size:.62rem;letter-spacing:.06em;text-align:center;text-transform:uppercase;color:var(--pst-color-text-muted)}
.tf-map-list-table.grouped th[rowspan]{vertical-align:bottom}
.tf-map-list-table th.tf-map-th-group.inner{font-size:.6rem;font-weight:650;letter-spacing:.04em}
.tf-map-list-table .tf-map-gs{border-left:1px solid var(--tf-map-line-strong)}
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
.tf-map-list-table .name{position:sticky;left:0;z-index:1;min-width:12rem;max-width:18rem;background:var(--pst-color-background)}
.tf-map-list-table th.name{z-index:3}
.tf-map-list-table tr.tf-map-list-group.sub td.name{background:var(--pst-color-background)}
.tf-map-name{display:flex;align-items:center;gap:.5rem;min-width:0}
.tf-map-name>span{min-width:0}
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
/* The hover card, the outline of a hovered mark, the arc of a hovered ray and Find. */
.tf-map-card{position:fixed;z-index:1200;width:300px;max-width:calc(100vw - 20px);padding:.66rem .76rem .6rem;border:1px solid var(--tf-map-line-strong);border-radius:var(--tf-map-radius);background:color-mix(in srgb,var(--pst-color-surface) 96%,var(--pst-color-text-base) 4%);color:var(--pst-color-text-base);box-shadow:0 12px 32px rgba(0,0,0,.18),0 2px 6px rgba(0,0,0,.08);font-size:.75rem;line-height:1.35;text-align:left;opacity:0;visibility:hidden;transform:translateY(4px);transition:opacity var(--tf-map-medium) var(--tf-map-ease),transform var(--tf-map-medium) var(--tf-map-ease),visibility var(--tf-map-medium) linear,left 120ms var(--tf-map-ease),top 120ms var(--tf-map-ease);pointer-events:none}
.tf-map-card.visible{opacity:1;visibility:visible;transform:none}
.tf-map-card.instant{transition:opacity var(--tf-map-medium) var(--tf-map-ease),transform var(--tf-map-medium) var(--tf-map-ease),visibility var(--tf-map-medium) linear}
.tf-map-card-head{display:flex;align-items:center;justify-content:space-between;gap:.5rem;margin-bottom:.3rem}
.tf-map-card-kind{display:inline-flex;align-items:center;gap:.35rem;font-size:.64rem;font-weight:800;letter-spacing:.055em;text-transform:uppercase;color:var(--pst-color-text-muted)}
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
@media(prefers-reduced-motion:reduce){#verification-health-map *,.tf-map-card{animation:none!important;transition:none!important}}"""

MAP_SHARED_JS = r"""// The Verification Health Map's runtime: the tree, both views, the layer strip, the filters, the table, the hover
// card, Find, Changes, the address and the keys. mapPage runs the map; the page describes its layers and draws what
// only it knows: healthMap judges each layer and depthMap measures it (the measures that were the Depth Map).
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
// Swatches and legend items look the same in every view; the page gives the colour (a class or a CSS colour).
const mapSwatch=(cls,color)=>'<i class="tf-map-sw'+(cls?" "+cls:"")+'"'+(color?' style="background:'+color+'"':"")+"></i>";
const mapLegendItem=(swatch,label,count,extra)=>"<span"+(extra?' class="extra"':"")+">"+swatch+label+(count===undefined?"":" <b>"+count+"</b>")+"</span>";
// How a set of marks splits over a view's colours: one bar, a segment per colour in legend order, as wide as its count.
// tone(row) is {key,fill,rank,label,cls} in that view, or null where the view says nothing about the row.
function mapSpread(rows,tone,titled){
 const parts=new Map();
 rows.forEach(row=>{const said=tone(row);if(!said)return;const part=parts.get(said.key)||{...said,count:0};part.count++;parts.set(said.key,part)});
 const list=[...parts.values()].sort((a,b)=>a.rank-b.rank);
 const title=titled&&list.length?' title="'+escapeHtml(list.map(part=>part.label+" "+part.count).join(" · "))+'"':"";
 return'<span class="tf-map-spread"'+title+' aria-hidden="true">'+list.map(part=>'<i'+(part.cls?' class="'+part.cls+'"':"")+' style="flex-grow:'+part.count+(part.fill?";background:"+part.fill:"")+'"></i>').join("")+"</span>";
}
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
// The All layers table and the rings use the same columns, so a contract keeps its place.
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
// The tree the map draws, from rows in tree order with the product first: goals, capabilities and contracts.
const MAP_KIND={product:"Product / System",goal:"Goal",feature:"Capability",requirement:"Requirement",treq:"Technical requirement"};
// The health layers and the question each answers: the Health Map judges them and the Verification Explorer files its
// items under them.
const MAP_HEALTH_LAYERS=[
 ["overall","Overall","Overall health; the rings show which layers fail where."],
 ["execution","Execution","Did the tests and scenarios that ran pass?"],
 ["coverage","Coverage","Does every required case have a passing test?"],
 ["faults","Fault model","Do the tests catch the errors they should?"],
 ["evidence","Evidence quality","Is the evidence realistic, traceable, qualified, up to date?"],
 ["assurance","Assurance","Do goals and capabilities pass their integration and validation checks?"]
];
// Every kind has its glyph wherever a mark is named: the Kind switch, the card, the contracts table and Find.
const MAP_KIND_ICON={product:"fa-cubes",goal:"fa-bullseye",feature:"fa-puzzle-piece",requirement:"fa-file-contract",treq:"fa-gear"};
const mapKindIcon=level=>'<i class="fa-solid '+MAP_KIND_ICON[level]+' tf-map-kind-icon" aria-hidden="true"></i>';
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
//   subrows(key) the other views of a layer, as rows below it: row(view) then gives {label,sub} as well
//   views(key,lone) the slider of a layer's views ("" for a layer with one view, unless lone asks for it too)
//   thumb(key), currentView(key) a card's mini-map of the view its layer opens in, and that view's key
//   viewList(key) the layer's views as [{key,label}]: a closed card shows a dot for each
//   viewTip(key), viewNote(key) a view's own hint, and why it has nothing to show under the filters ("" when it has)
//   current(), currentRow(), select(key,focus), selectView(key), focus(id)
function mapStrip(o){
 const $=id=>document.getElementById(id);
 const bar=$("tf-map-layerbar"),scroller=$("tf-map-scroller"),tabs=$("tf-map-tabs"),toggle=$("tf-map-table-toggle");
 const table=$("tf-map-table"),rowsBox=$("tf-map-rows"),foot=$("tf-map-table-foot"),viewsRow=$("tf-map-views-row");
 // A narrow page has no room beside the open card: the open layer's views take the row under the strip instead.
 const narrow=matchMedia("(max-width:640px)");
 const edges={left:bar.querySelector(".tf-map-edge.left"),right:bar.querySelector(".tf-map-edge.right")};
 const byKey=new Map(o.layers.map(layer=>[layer[0],layer]));
 const FOOT_IDLE="Pick a row to open its map. Each column is one contract, grouped by goal: point at it to compare layers.";
 const motion=()=>matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth";
 let pinWidth=0,edgeFrame=0,hold=null,picked=null,drag=null,dropped=false,folded=null,full=null,lastLayer=null;
 const order=()=>o.groups().flatMap(group=>group.keys);
 const toneOf=key=>o.groups().find(group=>group.keys.includes(key))?.tone||"";
 // A card's second and third lines say what the view its layer opens in says: health's verdict and count, or the
 // measure's line under the view's name. The lines of every view sit one over the other and the one in view shows,
 // so the card is as wide as its widest view and keeps its size when the view changes.
 const cardsOf=key=>o.cards?.(key)||[o.card(key)];
 const variant=(card,view,html)=>'<span class="tf-map-variant'+(card.view===view?" on":"")+'" data-variant="'+escapeHtml(card.view||"")+'"'+(card.view===view?"":' aria-hidden="true"')+">"+html+"</span>";
 const linesHtml=(key,cards,view)=>
   '<span class="tf-map-tab-status">'+cards.map(card=>variant(card,view,card.status+'<span class="tf-map-help" aria-hidden="true" data-tip="'+escapeHtml(card.help||byKey.get(key)[2])+'">?</span>')).join("")+"</span>"
   +'<span class="tf-map-count">'+cards.map(card=>variant(card,view,'<span class="tf-map-count-text"'+(card.tip?' data-tip="'+escapeHtml(card.tip)+'"':"")+">"+card.count+"</span>"+card.delta)).join("")+"</span>";
 // A card and, for a layer with several views, the slider of their thumbnails that the open card shows beside it.
 function tabHtml(key){
   const[,label,help]=byKey.get(key),card=o.card(key),views=o.views?.(key)||"",list=views?o.viewList(key):[];
   // A closed card with several views shows a dot for each under its mini-map, the one it opens in filled.
   const dots=list.length?'<span class="tf-map-dots" aria-hidden="true">'+list.map(view=>'<i data-dot="'+view.key+'"></i>').join("")+"</span>":"";
   const spoken=escapeHtml(help)+(list.length?" Views: "+list.map(view=>escapeHtml(view.label)).join(", ")+".":"");
   return'<div class="tf-map-tab-wrap" data-map-wrap="'+key+'">'
     +'<button type="button" role="tab" class="tf-map-tab'+(views?" has-views":"")+(card.health?" measure":"")+'" id="tf-map-tab-'+key+'" data-map-layer="'+key+'" data-view="'+escapeHtml(card.view||"")+'" aria-label="'+escapeHtml(card.name)+'" aria-controls="tf-map-stage" aria-describedby="tf-map-help-'+key+'">'
     +'<span class="tf-map-tab-title">'+label+"</span>"+card.thumb
     +linesHtml(key,cardsOf(key),card.view)
     +dots+'<span class="tf-sr-only" id="tf-map-help-'+key+'">'+spoken+"</span></button>"+views+"</div>";
 }
 // A card whose layer now opens in another view shows that view's lines and says them aloud.
 function refill(tab,key){
   const card=o.card(key);
   tab.dataset.view=card.view||"";
   tab.classList.toggle("measure",!!card.health);
   tab.setAttribute("aria-label",card.name);
   tab.querySelectorAll("[data-variant]").forEach(line=>{const on=line.dataset.variant===card.view;line.classList.toggle("on",on);line.toggleAttribute("aria-hidden",!on)});
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
   sync(true);syncBar();
   // A rebuild (fonts, a resize) stops a scroll on its way: put the current layer in sight at once, and its views
   // once they have grown.
   const tab=$("tf-map-tab-"+o.current());
   if(tab){reveal(tab,true);revealGrown(o.current())}
 }
 // The views are a radio group: the chosen one is checked and, where the views can be used, the one Tab stops at. A
 // view with nothing to show under the filters stays in its place, faded, and its hint says why; it can still be
 // chosen, and its panel still says why each contract is blank.
 const press=(views,view,active)=>views.querySelectorAll("[data-map-view]").forEach(button=>{
   const on=button.dataset.mapView===view,note=o.viewNote?.(button.dataset.mapView)||"";
   button.setAttribute("aria-checked",String(on));
   button.tabIndex=on&&active?0:-1;
   button.classList.toggle("idle",!!note);
   const tip=[o.viewTip?.(button.dataset.mapView)||"",note].filter(Boolean).join(" ");
   if(tip)button.dataset.tip=tip;else delete button.dataset.tip;
   if(note)button.setAttribute("aria-description",note);else button.removeAttribute("aria-description");
 });
 const knobShape=(at,count)=>count===1?" only":at===0?" first":at===count-1?" last":"";
 // The knob sits under the chosen view and takes the shape of its place: only the ends of the slider are rounded.
 function placeKnob(views,instant){
   const knob=views.querySelector(".tf-map-knob"),buttons=[...views.querySelectorAll("[data-map-view]")];
   const at=buttons.findIndex(button=>button.getAttribute("aria-checked")==="true"),chosen=buttons[at];
   if(!knob||!chosen||drag?.views===views)return;
   const apply=()=>{
     knob.style.width=chosen.offsetWidth+"px";
     knob.style.transform="translateX("+chosen.offsetLeft+"px)";
     knob.className="tf-map-knob"+knobShape(at,buttons.length);
   };
   if(instant)mapInstantly(knob,apply);else apply();
 }
 function sync(instant){
   const current=o.current();
   // Another layer starts afresh: its views open, one and a half of them in sight.
   if(current!==lastLayer){lastLayer=current;folded=null;full=null}
   tabs.querySelectorAll("[data-map-layer]").forEach(button=>{
     const active=button.dataset.mapLayer===current;
     button.setAttribute("aria-selected",String(active));
     button.tabIndex=active?0:-1;
   });
   // The open card shows its views and the thumbnail of the one in view; the others fold theirs away at once, and a
   // second click on the open card folds its own until the next click. A slider grows and folds to its own width, so
   // both take the whole transition. Three views or more open with one and a half of them in sight, faded at the cut,
   // and a +N that shows them all; choosing a view past the first shows them all too, until the card folds or another
   // card opens.
   tabs.querySelectorAll("[data-map-wrap]").forEach(wrap=>{
     const key=wrap.dataset.mapWrap,views=wrap.querySelector(".tf-map-views"),open=!!views&&key===current&&!narrow.matches&&folded!==key;
     wrap.classList.toggle("open",open);
     const thumb=wrap.querySelector(".tf-map-tab>.tf-map-thumb"),view=o.currentView(key);
     if(thumb&&thumb.dataset.view!==view)thumb.outerHTML=o.thumb(key);
     const tab=wrap.querySelector(".tf-map-tab");
     if(tab.dataset.view&&tab.dataset.view!==view)refill(tab,key);
     wrap.querySelectorAll("[data-dot]").forEach(dot=>dot.classList.toggle("on",dot.dataset.dot===view));
     if(!views)return;
     wrap.querySelector(".tf-map-tab").setAttribute("aria-expanded",String(open||narrow.matches&&key===current));
     const track=views.firstElementChild,buttons=[...track.querySelectorAll("[data-map-view]")];
     if(open&&buttons.findIndex(button=>button.dataset.mapView===view)>0)full=key;
     // Overall, first in the strip, always shows all its views.
     const peek=open&&buttons.length>2&&full!==key&&!wrap.closest(".tf-map-group.pinned");
     wrap.classList.toggle("peek",peek);
     views.style.setProperty("--tf-map-track-w",track.offsetWidth+"px");
     if(buttons.length>2)views.style.setProperty("--tf-map-peek-w",Math.round(buttons[1].offsetLeft+buttons[1].offsetWidth/2+1)+"px");
     const more=views.querySelector("[data-map-more]");
     if(more){more.tabIndex=peek?0:-1;more.setAttribute("aria-expanded",String(!peek))}
     views.inert=!open;
     press(views,view,open);
     placeKnob(views,instant||!open);
   });
   // The row under the strip always holds the open layer's views, a lone one too, so it never comes and goes.
   if(viewsRow){
     const key=o.current(),fresh=viewsRow.dataset.layer!==key;
     if(fresh){viewsRow.dataset.layer=key;viewsRow.innerHTML=o.views(key,true)}
     const views=viewsRow.firstElementChild;
     if(views){views.inert=!narrow.matches;press(views,o.currentView(key),narrow.matches);placeKnob(views,instant||fresh)}
   }
   rowsBox.querySelectorAll("[data-map-row]").forEach(row=>row.setAttribute("aria-selected",String(row.dataset.mapRow===currentRow())));
 }
 function reveal(tab,instant){
   if(!scroller.contains(tab)||pinWidth&&tab.closest(".pinned"))return;
   // The first card goes back to the very start of the strip.
   if(tab.closest(".pinned")){if(scroller.scrollLeft)scroller.scrollTo({left:0,behavior:instant?"auto":motion()});return}
   const view=scroller.getBoundingClientRect(),box=tab.getBoundingClientRect(),room=80;
   const start=pinWidth+room,end=view.width-room,left=box.left-view.left,right=box.right-view.left;
   // The room keeps a card clear of the 72 px scroll edges. Too wide to show whole, a card and its views show their start:
   // the card never leaves sight for its views.
   const delta=left<start||right-left>end-start?left-start:right>end?right-end:0;
   if(delta)scroller.scrollBy({left:delta,behavior:instant?"auto":motion()});
 }
 if(viewsRow)new ResizeObserver(()=>{const views=viewsRow.firstElementChild;if(views)placeKnob(views,true)}).observe(viewsRow);
 narrow.addEventListener("change",()=>{sync(true);show(o.current())});
 // Late fonts change the width of the views' names: the sliders take their new width.
 document.fonts?.ready?.then(()=>sync(true));
 // The open card grows to show its views: bring the whole of it into sight once it has, and once the views it
 // replaced have folded, Overall's among them, so the pinned width is measured again first. A rebuild may have
 // replaced the card by then, so it is looked up again.
 let grown=0;
 function revealGrown(key){
   clearTimeout(grown);
   grown=setTimeout(()=>{syncBar();const tab=$("tf-map-tab-"+key);if(tab)reveal(tab.closest(".tf-map-tab-wrap")||tab)},380);
 }
 function show(key,focus){
   const tab=$("tf-map-tab-"+key);
   if(!tab)return;
   // A view picked on a slider keeps the strip where it is, only bringing that view into sight.
   if(picked){reveal(picked);return}
   // A card out of sight comes into sight at once; one in sight waits until the views have grown and folded, so the
   // strip moves once, to where everything ends up.
   const view=scroller.getBoundingClientRect(),box=tab.getBoundingClientRect();
   if(box.right<=view.left+pinWidth||box.left>=view.right)reveal(tab);
   revealGrown(key);
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
 const currentRow=()=>o.currentRow?.()||o.current();
 const withViews=keys=>keys.flatMap(key=>[key,...(o.subrows?.(key)||[])]);
 function rowHtml(key){
   const row=o.row(key),label=row.label||byKey.get(key)[1],selected=key===currentRow();
   return'<div class="tf-map-row'+(row.sub?" sub":"")+'" role="option" data-map-row="'+key+'" aria-selected="'+selected+'" tabindex="'+(selected?0:-1)+'" aria-label="'+escapeHtml(row.name)+'">'
     +'<span class="tf-map-row-head"><span class="tf-map-row-name">'+label+"</span>"+row.status+'<span class="tf-map-row-count">'+row.count+"</span></span>"
     +'<svg class="tf-map-row-strip" viewBox="0 0 '+o.columns.units+' 16" preserveAspectRatio="none" aria-hidden="true" focusable="false">'+o.cells(key)+"</svg></div>";
 }
 function rowsGroup(group){
   if(!group.keys.length)return"";
   return'<div class="tf-map-rows-group" role="group" aria-label="'+escapeHtml(group.label)+' layers">'
     +'<div class="tf-map-rows-label'+(group.tone?" "+group.tone:"")+'" aria-hidden="true">'+(group.icon?'<i class="fa-solid '+group.icon+'"></i>':"")+escapeHtml(group.label)+" · "+group.keys.length+"</div>"
     +withViews(group.keys).map(rowHtml).join("")+"</div>";
 }
 function resetFoot(){
   foot.textContent=FOOT_IDLE;
   rowsBox.querySelector(".tf-map-band")?.classList.remove("visible");
 }
 function renderTable(){
   const[first,...rest]=o.groups();
   rowsBox.innerHTML=withViews(first.keys).map(rowHtml).join("")+rest.map(rowsGroup).join("")+'<div class="tf-map-band" aria-hidden="true"></div>';
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
 // A click on a view's thumbnail picks it. The views are a radio group: the arrow keys move the knob round them, Home
 // and End to either end.
 function pickView(event){
   const view=event.target.closest("[data-map-view]");
   if(!view)return false;
   // The click that ends a drag of the knob is not a pick: the drag has picked already.
   if(event.type==="click"&&dropped){dropped=false;return true}
   let next=view;
   if(event.type==="keydown"){
     const list=[...view.parentElement.querySelectorAll("[data-map-view]")],at=list.indexOf(view);
     const step={ArrowRight:at+1,ArrowDown:at+1,ArrowLeft:at-1,ArrowUp:at-1,Home:0,End:list.length-1}[event.key];
     if(step===undefined)return true;
     event.preventDefault();
     next=list[(step+list.length)%list.length];
   }
   picked=next;
   try{o.selectView(next.dataset.mapView)}finally{picked=null}
   if(next!==view)next.focus({preventScroll:true});
   return true;
 }
 // The knob can be dragged: press the chosen view, slide along the track and let go over another view.
 const centerOf=button=>button.offsetLeft+button.offsetWidth/2;
 const nearest=(buttons,x)=>buttons.reduce((best,button,index)=>Math.abs(centerOf(button)-x)<Math.abs(centerOf(buttons[best])-x)?index:best,0);
 function knobDown(event){
   const button=event.target.closest('[data-map-view][aria-checked="true"]'),views=button?.closest(".tf-map-views");
   dropped=false;
   if(!button||event.button!==0||views.classList.contains("lone"))return;
   const knob=views.querySelector(".tf-map-knob"),buttons=[...views.querySelectorAll("[data-map-view]")];
   drag={id:event.pointerId,x:event.clientX,button,views,knob,buttons,from:button.offsetLeft,at:buttons.indexOf(button),moved:false};
   knob.classList.add("pressed");
 }
 function knobMove(event){
   if(!drag||event.pointerId!==drag.id)return;
   const{knob,buttons,views}=drag,dx=event.clientX-drag.x;
   if(!drag.moved){
     if(Math.abs(dx)<4)return;
     drag.moved=true;
     try{drag.button.setPointerCapture(event.pointerId)}catch{}
     views.classList.add("dragging");
     const cut=views.closest(".tf-map-tab-wrap.peek");
     if(cut){full=cut.dataset.mapWrap;cut.classList.remove("peek");revealGrown(full)}
   }
   const x=Math.max(0,Math.min(knob.parentElement.clientWidth-knob.offsetWidth,drag.from+dx));
   drag.at=nearest(buttons,x+knob.offsetWidth/2);
   knob.style.transform="translateX("+x+"px)";
   knob.className="tf-map-knob pressed"+knobShape(drag.at,buttons.length);
   buttons.forEach((button,index)=>button.classList.toggle("near",index===drag.at));
 }
 function knobUp(event){
   if(!drag||event.pointerId!==drag.id)return;
   const{moved,views,knob,buttons,button,at}=drag;
   drag=null;
   knob.classList.remove("pressed");
   views.classList.remove("dragging");
   buttons.forEach(item=>item.classList.remove("near"));
   if(!moved)return;
   if(event.type==="pointerup"){dropped=true;setTimeout(()=>{dropped=false},0)}
   const target=event.type==="pointercancel"?button:buttons[at];
   if(target===button){placeKnob(views);return}
   picked=target;
   try{o.selectView(target.dataset.mapView)}finally{picked=null}
   if(document.activeElement===button)target.focus({preventScroll:true});
 }
 [tabs,viewsRow].forEach(box=>{
   if(!box)return;
   box.addEventListener("pointerdown",knobDown);
   box.addEventListener("pointermove",knobMove);
   box.addEventListener("pointerup",knobUp);
   box.addEventListener("pointercancel",knobUp);
 });
 viewsRow?.addEventListener("click",pickView);
 viewsRow?.addEventListener("keydown",pickView);
 tabs.addEventListener("click",event=>{
   const more=event.target.closest("[data-map-more]");
   if(more){full=more.dataset.mapMore;sync();revealGrown(full);return}
   if(pickView(event))return;
   const button=event.target.closest("[data-map-layer]");
   if(!button)return;
   const key=button.dataset.mapLayer;
   // A second click on the open card folds its views and the next click opens them again; the layer stays in view.
   if(key===o.current()&&!narrow.matches&&button.closest(".tf-map-tab-wrap").querySelector(".tf-map-views")){
     folded=folded===key?null:key;
     full=null;
     sync();
     revealGrown(key);
     return;
   }
   o.select(key,false);
 });
 tabs.addEventListener("keydown",event=>{
   if(pickView(event))return;
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
// The treemap: goals, capabilities and contracts with the same padding and binary tiling. The page
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
// The treemap view: one link per goal, capability and contract with its shape and its name, in tree
// order. A new tiling draws them again; a narrower view only moves them, so hover and focus stay put.
//   dots: goals and capabilities carry a dot before their name (health's own verdict); bind(entry); drawn()
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
// The rings follow the height and sit in the middle, so a narrower view only moves them; the goal
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
// The rings view. The core is the same in every ring set: the centre, then goals, then capabilities; each
// contract is one ray from there to the edge through the page's own rings. Radii are shares of the outer radius.
//   bands(outer): the page's rings, with names [{labels,band,cls,key,aria,tip}] (a key opens that layer) and
//     gap [radius,room]: the innermost named ring and the half width its names need at twelve o'clock
//   centre(): {href,label,cls,kicker,big,tone,small}; container(row): the class a goal or capability arc adds
//   ray(link,row,a0,a1,geometry): draws a contract's ray and returns the shape its card sits beside
//   after(body,geometry,rings): what the page draws over the rays; rayThumb(row,a0,a1,geometry): the card's version
//   dot(row): the class a goal name's dot adds (health's verdict); href(row), aria(row), bind(entry), drawn()
const RING_CORE={center:.27,goal:[.29,.355],feature:[.365,.425],rays:.44};
const mapRingGap=(radius,room)=>Math.min(.95,Math.max(.46,2*Math.asin(Math.min(1,room/Math.max(1,radius)))));
const circlePath=r=>"M"+fixed(-r)+",0a"+fixed(r)+","+fixed(r)+" 0 1,0 "+fixed(2*r)+",0a"+fixed(r)+","+fixed(r)+" 0 1,0 "+fixed(-2*r)+",0";
function mapRings(svg,tree,o){
 const columns=tree.columns;
 const rings={svg,entries:[],byId:new Map(),bands:new Map(),geometry:null,gap:.5,arc:null};
 let width=0,height=0,outer=0,body=null;
 const coreAt=radius=>({center:RING_CORE.center*radius,goal:RING_CORE.goal.map(share=>share*radius),feature:RING_CORE.feature.map(share=>share*radius),rays:RING_CORE.rays*radius});
 rings.angleAt=(unit,gap=rings.gap)=>gap/2+unit/columns.units*(2*Math.PI-gap);
 rings.add=entry=>{entry.radial=true;entry.set=rings;rings.entries.push(entry);if(!entry.layer)rings.byId.set(entry.row.id,entry);o.bind(entry);return entry};
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
// The view frame: a legend bar of one line in every view, the side panel and the stage below it, one
// height for every view (the rest of the first screen), and a stage that follows its own width frame by frame while
// the panel slides, then settles.
//   layout(force), follow(width); setLegend(html) on the frame shows a view's legend
function mapFrame(o){
 const $=id=>document.getElementById(id);
 const body=$("tf-map-body"),stage=$("tf-map-stage"),bar=$("tf-map-legendbar"),legend=$("tf-map-legend"),pop=$("tf-map-more-pop");
 const frame={pageWidth:0,viewH:0,body,stage,legend};
 let settle=0;
 frame.stageWidth=()=>Math.round(stage.getBoundingClientRect().width);
 // Every view has one height: the rest of the first screen below the legend. The panel, a filter or another view never changes it.
 const firstScreen=()=>Math.round(innerHeight-(body.getBoundingClientRect().top+scrollY)-20);
 const heightFor=width=>Math.round(width<600?Math.min(600,Math.max(320,width)):Math.min(760,Math.max(440,Math.min(width*.8,firstScreen()))));
 // The legend is one line in every view, so nothing below it ever moves: what does not fit hides behind a +N at its
 // end, and pointing at or clicking the +N opens the rest below it. The question a view answers opens the line and the
 // ? closes it; both stay.
 const hidePop=()=>{pop.hidden=true;legend.querySelector(".tf-map-more")?.setAttribute("aria-expanded","false")};
 function fitLegend(){
   hidePop();
   legend.querySelector(".tf-map-more")?.remove();
   legend.classList.remove("tight");
   const items=[...legend.children].filter(node=>!node.matches(".tf-map-ask,.tf-map-help"));
   items.forEach(node=>node.classList.remove("tf-map-over"));
   if(legend.scrollWidth<=legend.clientWidth+1)return;
   const more=document.createElement("button");
   more.type="button";more.className="tf-map-more";more.tabIndex=-1;more.textContent="+"+items.length;
   legend.insertBefore(more,legend.querySelector(".tf-map-help"));
   const hidden=[];
   for(let index=items.length-1;index>0&&legend.scrollWidth>legend.clientWidth+1;index--){items[index].classList.add("tf-map-over");hidden.unshift(items[index])}
   // Only when a single colour is left does the question give way, cut short with its full text as the hint.
   legend.classList.toggle("tight",legend.scrollWidth>legend.clientWidth+1);
   more.textContent="+"+hidden.length;
   more.setAttribute("aria-expanded","false");
   pop.innerHTML=hidden.map(node=>{const copy=node.cloneNode(true);copy.classList.remove("tf-map-over");return copy.outerHTML}).join("");
 }
 function showPop(){
   const more=legend.querySelector(".tf-map-more");
   if(!more)return;
   const box=bar.getBoundingClientRect(),at=more.getBoundingClientRect();
   pop.hidden=false;
   pop.style.left=Math.max(0,Math.min(box.width-pop.offsetWidth,at.left-box.left))+"px";
   more.setAttribute("aria-expanded","true");
 }
 let pinned=false;
 legend.addEventListener("click",event=>{if(!event.target.closest(".tf-map-more"))return;pinned=!pinned||pop.hidden;if(pinned)showPop();else hidePop()});
 legend.addEventListener("pointerover",event=>{if(event.target.closest(".tf-map-more"))showPop()});
 bar.addEventListener("pointerleave",()=>{if(!pinned)hidePop()});
 document.addEventListener("pointerdown",event=>{if(pinned&&!bar.contains(event.target)){pinned=false;hidePop()}});
 document.addEventListener("keydown",event=>{if(event.key==="Escape"&&!pop.hidden){pinned=false;hidePop()}});
 // A new legend fades in like the view it explains; the same legend again changes nothing.
 let shownLegend="";
 frame.setLegend=html=>{
   pinned=false;
   if(html===shownLegend)return;
   shownLegend=html;
   legend.innerHTML=html;
   fitLegend();
   legend.classList.remove("tf-map-fresh");void legend.offsetWidth;legend.classList.add("tf-map-fresh");
 };
 // The legend refits whenever its room changes: a new page width, or the panel opening beside it.
 new ResizeObserver(()=>fitLegend()).observe(legend);
 frame.layout=force=>{
   const page=Math.round(body.getBoundingClientRect().width);
   if(!page)return;
   if(force||page!==frame.pageWidth){frame.pageWidth=page;fitLegend()}
   frame.viewH=heightFor(frame.pageWidth);
   body.style.setProperty("--tf-map-view-h",frame.viewH+"px");
   o.layout(force);
 };
 new ResizeObserver(()=>{o.follow(frame.stageWidth());clearTimeout(settle);settle=setTimeout(()=>frame.layout(false),160)}).observe(stage);
 addEventListener("resize",()=>{clearTimeout(settle);settle=setTimeout(()=>frame.layout(false),160)});
 return frame;
}
// Filters: OR inside a facet, AND across facets; every view reads the same set, the table too. A facet is
// {label, options or name and valid, test(row,value), swatch(value), tip(value), keepEmpty(value), title, help,
// empty, pipe, panel(), switch: one value or none, where the empty value is all of them}. The side panel follows the view and shows only the facets that fit it, so pointing at an
// option always lights something; the table previews nothing and a click filters it.
//   rows: what the filters keep or dim; leaves: what the count counts, named by noun (contracts on the map);
//   view(), panel(view), previews(view)
//   rendered(): the page redraws its own switches; changed(): the page redraws what depends on the filters
//   mark(row,panel): page marks for a hovered contract
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
 // A previewed option shows what it holds with the other facets, as its count says, even where its own facet already
 // holds another value.
 f.shown=withPreview=>{
   if(!f.active()&&!(withPreview&&f.preview))return null;
   const preview=withPreview&&f.preview;
   return new Set(o.rows.filter(row=>preview?f.matches(row,preview.facet)&&facets[preview.facet].test(row,preview.value):f.matches(row)).map(row=>row.id));
 };
 const lead=$("tf-map-lead"),box=$("tf-map-filters"),chips=$("tf-map-chips"),badge=$("tf-map-filter-badge"),count=$("tf-map-total");
 const body=$("tf-map-body"),panel=$("tf-map-panel"),toggleButton=$("tf-map-panel-toggle"),panelBody=$("tf-map-panel-body");
 const help=text=>' <span class="tf-map-help" aria-hidden="true" data-tip="'+escapeHtml(text)+'">?</span>';
 const counted=o.leaves.length,noun=o.noun||"contracts";
 let chipsHtml="";
 // Chips and how many rows they keep in place of the run stamp, and the badge on Filters.
 f.render=()=>{
   const list=[];
   for(const key in sets)for(const value of sets[key]){
     const text=facets[key].label+": "+facets[key].name(value);
     list.push('<button type="button" class="tf-map-chip" data-facet="'+key+'" data-value="'+escapeHtml(value)+'" aria-label="Remove filter '+escapeHtml(text)+'">'+escapeHtml(text)+'<i class="fa-solid fa-xmark" aria-hidden="true"></i></button>');
   }
   lead.classList.toggle("filtered",list.length>0);
   box.hidden=!list.length;
   if(list.join("")!==chipsHtml){chipsHtml=list.join("");chips.innerHTML=chipsHtml}
   const shown=f.shown(false);
   count.innerHTML=shown?"<b>"+o.leaves.filter(row=>shown.has(row.id)).length+"</b> of "+counted+" "+noun:"<b>"+counted+"</b> "+noun;
   badge.hidden=!list.length;
   badge.textContent=list.length;
   o.rendered();
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
 // One value alone, or none when it is empty or already alone: a switch rather than a set of options.
 f.only=(key,value)=>{const set=sets[key],alone=set.size===1&&set.has(value);set.clear();if(value&&!alone)set.add(value);changed()};
 // Pointing at an option lights its marks where the view previews; the table previews nothing.
 f.setPreview=next=>{
   if(next&&!o.previews(o.view()))next=null;
   if(JSON.stringify(next)===JSON.stringify(f.preview))return;
   f.preview=next;
   o.previewed();
 };
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
 // An option, a matrix cell, a substitute or a kind: every control in the panel is a facet and a value. A switch facet
 // keeps one value (or none), every other facet toggles the value.
 panel.addEventListener("click",event=>{
   const target=event.target.closest("button[data-facet]:not(:disabled)");
   if(target)(facets[target.dataset.facet].switch?f.only:f.toggle)(target.dataset.facet,target.dataset.value);
 });
 panel.addEventListener("pointerover",event=>{
   const target=event.target.closest("button[data-facet]:not(:disabled)");
   f.setPreview(target?{facet:target.dataset.facet,value:target.dataset.value}:null);
 });
 panel.addEventListener("pointerleave",()=>f.setPreview(null));
 let startOpen=false;
 try{startOpen=localStorage.getItem("tf-map-panel")==="1"}catch(error){}
 f.startOpen=startOpen;
 return f;
}
// Kind: the map's contracts are requirements and technical requirements. The switch opens the side panel, the same
// in every view, above the view's own filters: each kind with its glyph, its name and how many contracts it holds under
// the other filters. Its tiles are the kind facet's options, so pointing at one lights its contracts and a click
// chooses it like any option (one kind, or all); a chosen kind shows as a chip like every filter. The same glyphs name
// a kind in the card, the table and Find.
//   leaves, filters
function mapKinds(o){
 const box=document.getElementById("tf-map-kinds");
 const KINDS=[["","fa-list-check","All","Every contract: requirements and technical requirements."],
   ["requirement",MAP_KIND_ICON.requirement,"Requirements","Only requirements: what the product must do for the people who use it."],
   ["treq",MAP_KIND_ICON.treq,"Technical requirements","Only technical requirements: the engineering rules behind the requirements."]];
 // The switch is drawn once; a filter changes only its counts and which kind is chosen, so it never shifts.
 box.innerHTML=KINDS.map(([value,icon,name,tip])=>'<button type="button" class="tf-map-kind" data-facet="kind" data-value="'+value+'" aria-pressed="false" data-tip="'+escapeHtml(tip)+'">'
   +'<span class="tf-map-kind-name"><i class="fa-solid '+icon+'" aria-hidden="true"></i>'+name+"</span><b></b></button>").join("");
 const buttons=[...box.querySelectorAll("[data-facet]")];
 const k={};
 k.render=()=>{
   const set=o.filters.sets.kind,chosen=set.size===1?[...set][0]:"",others=o.leaves.filter(row=>o.filters.matches(row,"kind"));
   buttons.forEach(button=>{
     const value=button.dataset.value,found=value?others.filter(row=>row.level===value).length:others.length,pressed=value===chosen;
     button.setAttribute("aria-pressed",String(pressed));
     button.disabled=!found&&!pressed;
     button.querySelector("b").textContent=found;
   });
 };
 return k;
}
// The matrix of Overall's panel. A cell counts the marks it holds with the filters (and of how many
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
//   columns [[key,label,tip,class,groups]]: groups is a header path (a name, or names from the outside in), and
//   neighbours on one path share its headers above their own; groups
//   [[key,label]], the first one is tree; keys(row), name(key), order(keys); sortValue(row,key), stats(list), cells(row)
//   groupCells(list): a group row's own cell under every column, or the group's stats in one line without it
//   href(row), csv: {file, head, line(row)}, height(), changed()
function mapTable(o){
 const $=id=>document.getElementById(id);
 const view=$("tf-map-list-view"),box=$("tf-map-list"),groupBox=$("tf-map-group-by"),summary=$("tf-map-summary");
 const t={group:o.groups[0][0],sort:{key:"",dir:1}};
 const syncGroups=()=>groupBox.querySelectorAll("[data-group]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.group===t.group)));
 groupBox.innerHTML=o.groups.map(([key,label])=>'<button type="button" data-group="'+key+'" aria-pressed="'+(key===t.group)+'">'+label+"</button>").join("");
 const sorted=list=>!t.sort.key?list:[...list].sort((a,b)=>{const x=o.sortValue(a,t.sort.key),y=o.sortValue(b,t.sort.key);return(x<y?-1:x>y?1:0)*t.sort.dir||a.label.localeCompare(b.label)});
 const rowHtml=row=>'<tr class="tf-map-list-row '+row.level+'" data-id="'+row.id+'"><td class="name"><span class="tf-map-name">'+mapKindIcon(row.level)+'<span><a href="'+escapeHtml(o.href(row))+'">'+escapeHtml(row.short||row.label)+"</a><small>"+row.id+"</small></span></span></td>"+o.cells(row)+"</tr>";
 const groupRow=(name,list,sub)=>'<tr class="tf-map-list-group'+(sub?" sub":"")+'">'+(o.groupCells
   ?'<td class="name"><span class="tf-map-list-group-name">'+escapeHtml(name)+'</span><span class="tf-map-list-group-stats">'+list.length+"</span></td>"+o.groupCells(list)
   :'<td colspan="'+o.columns.length+'"><span class="tf-map-list-group-name">'+escapeHtml(name)+'</span><span class="tf-map-list-group-stats">'+o.stats(list)+"</span></td>")+"</tr>";
 // Header paths: neighbours on one path share its headers. A column group starts where the outermost name changes; a
 // line on its left keeps each group apart from the header down.
 const pathOf=column=>Array.isArray(column[4])?column[4]:column[4]?[column[4]]:[];
 const depth=Math.max(...o.columns.map(column=>pathOf(column).length))+1;
 const starts=o.columns.map((column,index)=>index>0&&pathOf(column)[0]!==pathOf(o.columns[index-1])[0]);
 const sortButton=(key,label)=>'<button type="button" data-sort="'+key+'">'+label+'<span class="dir">'+(t.sort.key===key?(t.sort.dir>0?"▲":"▼"):"")+"</span></button>";
 const classes=(...names)=>names.filter(Boolean).join(" ");
 function headerHtml(){
   const rows=Array.from({length:depth},()=>"");
   o.columns.forEach((column,index)=>{
     const[key,label,tip,cls]=column,path=pathOf(column);
     path.forEach((name,level)=>{
       const same=other=>!!other&&pathOf(other).slice(0,level+1).join("\u0001")===path.slice(0,level+1).join("\u0001");
       if(same(o.columns[index-1]))return;
       let span=1;
       while(same(o.columns[index+span]))span++;
       rows[level]+='<th colspan="'+span+'" class="'+classes("tf-map-th-group",level?"inner":"",starts[index]&&"tf-map-gs")+'">'+escapeHtml(name)+"</th>";
     });
     const rest=depth-path.length;
     rows[path.length]+="<th"+(rest>1?' rowspan="'+rest+'"':"")+' class="'+classes(cls,starts[index]&&"tf-map-gs")+'" title="'+escapeHtml(tip||label)+'">'+sortButton(key,label)+"</th>";
   });
   return rows.map(row=>"<tr>"+row+"</tr>").join("");
 }
 // A redraw keeps the table where the reader left it: sideways always, and down unless the grouping changes.
 t.render=fresh=>{
   const left=box.scrollLeft,top=fresh?0:box.scrollTop,visible=o.rows();
   summary.textContent=visible.length?o.stats(visible):"";
   summary.title=summary.textContent;
   const header=headerHtml();
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
   box.innerHTML='<table class="tf-map-list-table'+(depth>1?" grouped":"")+'"><thead>'+header+"</thead><tbody>"+html+"</tbody></table>";
   starts.forEach((start,index)=>{if(start)box.querySelectorAll("tbody tr:not(:has(td[colspan])) > td:nth-child("+(index+1)+")").forEach(cell=>cell.classList.add("tf-map-gs"))});
   t.fit();
   box.scrollLeft=left;box.scrollTop=top;
 };
 // The table fills the same height as the other views: its own bar first, then the rows. Each header row sticks
 // below the ones above it.
 t.fit=()=>{
   if(view.hidden||!o.height())return;
   const bar=view.firstElementChild.getBoundingClientRect().height+8;
   box.style.height=Math.max(200,o.height()-bar)+"px";
   let top=0;
   box.querySelectorAll("thead tr").forEach(row=>{row.querySelectorAll("th").forEach(cell=>{cell.style.top=top+"px"});top+=row.getBoundingClientRect().height});
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
   syncGroups();t.render(true);o.changed();
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
// The hover card: it waits a moment before it first shows, then follows from mark to mark at once,
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
     +'<span class="tf-map-find-text"><span class="tf-map-find-name">'+mapKindIcon(item.row.level)+escapeHtml(item.row.label)+'</span><span class="tf-map-find-path">'+escapeHtml(item.path||item.kind)+"</span></span>"
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
// A map: the page runs this. It shows one view at a time and keeps the address, the hover card with its outline,
// arc and lineage, the filters and Changes on every view, keyboard focus and the keys. A view is one layer seen one way:
// as rings, as a map of tiles or as the contracts table. The page describes its layers and draws what only it knows:
//   tree, layers [[key,label,help]], insights {run,delta}, words(projection): what up and down mean for Changes
//   views [{key,layer,projection,form,ring,label,tip,ask}]: every view of every layer, form rings, tiles or table, a
//     layer's first view first. A layer with several views shows them on its open card as a slider of their
//     thumbnails; tip or ask is a thumbnail's hint, and ask is the question a view's legend opens with
//   href(row,projection); says(row,projection): {text,tone}, what a view says about a mark (its spoken name, the
//     card's pill, the All layers foot), or null; describe(row,projection,entry): {body,extra}, the rest of its card
//   paint(entries,projection,animated): the tiles in a projection's colours; legend(projection): {items,help};
//     tone(row,projection): {key,fill,rank,label,cls}, the colour a view gives a mark, or null, for the bars that
//     split marks over a view's colours; blank(row,projection): the mark has nothing to show in that view (not
//     measured, no tests, N/A), so a map view whose every mark the filters keep is blank fades on its slider
//   facets, panels {view key or projection: {title,help,before,facets}}, filterRows, markPanel(row,panel); Goal closes
//     every panel and Kind opens it (mapKinds). A ring segment names the facet it shows, or the facet and the value, in
//     data-seg
//   strip {groups,card,row,cells}; table {columns,groups,keys,name,order,sortValue,stats,cells,groupCells,csv}, after
//     the contract name, the goal and the capability that every table starts with
//   tiles {dots,leaf(row,projection),mark(row,projection)}; ringSets {name: rings}, the set a rings view names
//   find(row): {rank,badge}; selected(view): the page follows the view; attach(page): the page keeps what
//     mapPage returns for its own drawing
// Nothing runs until start().
const MAP_TABLE_HELP="Click a cell or an option to narrow the table; the same filters apply to every layer.";
const MAP_TILE_HELP="Each tile is a contract with its technical requirements beside it; ";
function mapPage(o){
 const $=id=>document.getElementById(id);
 const tree=o.tree,delta=o.insights?.delta||{};
 const LAYER_KEYS=o.layers.map(layer=>layer[0]);
 const VIEWS=o.views;
 const VIEW_KEYS=VIEWS.map(view=>view.key);
 const viewOf=key=>VIEWS.find(view=>view.key===key);
 const lensesOf=layer=>VIEWS.filter(view=>view.layer===layer);
 // view is what the stage shows; layer is the strip card it belongs to; projection is what it colours by; tiled is
 // the projection the tiles carry now.
 const page={tree,view:VIEWS[0].key,layer:VIEWS[0].layer,projection:VIEWS[0].projection,tiled:"",last:{},focusedId:"",pendingFocus:"",changesOn:false};
 // A strip card or a table row names a layer, which opens as the reader left it, or one view of it.
 const opening=key=>LAYER_KEYS.includes(key)?page.last[key]||lensesOf(key)[0].key:key;
 const card=mapCard($("tf-map-card")),hint=mapHint($("tf-map-hint"));
 const deltaOf=key=>(delta.layers||{})[key]||{up:[],down:[]};
 const labelOf=key=>o.layers.find(layer=>layer[0]===key)[1];
 const ariaOf=(row,projection)=>{const says=o.says(row,projection);return MAP_KIND[row.level]+": "+row.label+(says?", "+says.text:"")};
 // What a mark shows: a ring cell its own layer, a ring its ring set's projection, a tile the projection of the tiles.
 const projectionOf=entry=>entry.layer||(entry.radial?entry.set.projection:page.tiled);
 // Hover and focus: the outline or the arc and the lineage show at once and stay while the card is open; the card
 // waits a moment before it first shows.
 function clearHighlight(){
   [tiles,...ringList].forEach(view=>view.svg.querySelectorAll(".tf-map-lineage").forEach(node=>node.classList.remove("tf-map-lineage")));
   tiles.outline?.hide();
   ringList.forEach(rings=>rings.clear());
 }
 function highlight(entry){
   clearHighlight();
   if(entry.radial)entry.set.highlight(entry);else tiles.outline.move(entry);
   const byId=entry.radial?entry.set.byId:tiles.byId;
   tree.ancestors(entry.row).forEach(item=>{const parent=byId.get(item.id);if(parent&&parent.kind!=="leaf")parent.shape.classList.add("tf-map-lineage")});
 }
 const hideTip=immediate=>card.hide(immediate,clearHighlight);
 const hoverKey=entry=>(entry.radial?"rings:"+entry.set.name+":":"map:")+entry.row.id+(entry.layer?"@"+entry.layer:"");
 // The card: kind and what the view says, the name and where it sits, the page's rows, and where a click goes.
 function cardHtml(entry){
   const row=entry.row,projection=projectionOf(entry),says=o.says(row,projection),part=o.describe(row,projection,entry),path=tree.ancestors(row);
   return'<div class="tf-map-card-head"><span class="tf-map-card-kind">'+mapKindIcon(row.level)+MAP_KIND[row.level]+"</span>"+(says?'<span class="tf-map-pill'+(says.tone?" "+says.tone:"")+'">'+escapeHtml(says.text)+"</span>":"")+"</div>"
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
 // One set of rings per rings view; the first uses the page's rings view, the others get their own beside it.
 const firstRings=$("tf-map-rings"),ringSets={};
 Object.entries(o.ringSets).forEach(([name,config],index)=>{
   let svg=firstRings;
   if(index){
     svg=firstRings.cloneNode(false);
     svg.id="tf-map-rings-"+name;
     if(config.label)svg.setAttribute("aria-label",config.label);
     svg.setAttribute("hidden","");
     firstRings.after(svg);
   }
   const projection=VIEWS.find(view=>view.ring===name)?.projection||name;
   ringSets[name]=Object.assign(mapRings(svg,tree,{...config,href:row=>o.href(row,projection),aria:row=>ariaOf(row,projection),bind,drawn:applyFocus}),{name,projection});
 });
 const ringList=Object.values(ringSets);
 // The tiles take the colours of the projection they show; links and names follow it.
 function paint(animated){
   const projection=page.tiled;
   if(!projection)return;
   tiles.entries.forEach(entry=>{entry.link.setAttribute("href",o.href(entry.row,projection));entry.link.setAttribute("aria-label",ariaOf(entry.row,projection))});
   o.paint(tiles.entries,projection,animated);
   applyFocus();
 }
 // Filters keep their marks lit and dim the rest; Changes outlines what went up and what went down. Both survive
 // redraws and apply to every view.
 function applyFocus(){
   const ids=filters.shown(true),changes=page.changesOn&&delta.baseline,view=viewOf(page.view);
   // A previewed option that the rings show as segments keeps only its own segments lit inside the rays it keeps.
   const preview=view.form==="rings"?filters.preview:null,marks=preview?[preview.facet,preview.facet+"="+preview.value]:[];
   ringList.forEach(rings=>{
     const segments=[...rings.svg.querySelectorAll("[data-seg]")],lit=segments.some(node=>marks.includes(node.dataset.seg));
     segments.forEach(node=>node.classList.toggle("tf-map-seg-dim",lit&&!marks.includes(node.dataset.seg)));
   });
   [...tiles.entries,...ringList.flatMap(rings=>rings.entries)].forEach(entry=>{
     const leaf=entry.kind==="leaf"||entry.kind==="track",hit=!!ids&&ids.has(entry.row.id);
     entry.link.classList.toggle("tf-map-dim",!!ids&&leaf&&!hit);
     entry.shape.classList.toggle("tf-map-hit",!!ids&&!leaf&&entry.kind!=="product"&&hit);
     const change=changes&&leaf?deltaOf(projectionOf(entry)):null;
     entry.shape.classList.toggle("tf-map-up",!!change&&change.up.includes(entry.row.id));
     entry.shape.classList.toggle("tf-map-down",!!change&&change.down.includes(entry.row.id));
   });
 }
 // The legend of each view: the question it answers where it has one, the page's colours, the Changes key whenever
 // Changes is on, and one sentence behind the ?. The table keeps the legend of the view it tabulates.
 function legendFor(key){
   const view=viewOf(key),words=o.words(view.projection),legend=o.legend(view.projection);
   return(view.ask?'<span class="tf-map-ask" title="'+escapeHtml(view.ask)+'">'+escapeHtml(view.ask)+"</span>":"")+legend.items
     +(page.changesOn&&delta.baseline?'<span class="tf-map-changes-key"><i class="up"></i>'+escapeHtml(words[0])+'<i class="down"></i>'+escapeHtml(words[1])+" since "+escapeHtml(mapRunLabel(delta.baseline.started_at))+"</span>":"")
     +'<span class="tf-map-help" data-tip="'+escapeHtml((view.form==="tiles"?MAP_TILE_HELP:"")+legend.help)+'">?</span>';
 }
 // Kind and goal narrow the contracts in every view: kind opens every panel as a switch and goal closes it. The panel
 // follows the view; the table keeps the panel of the view it tabulates, and only its hint says a click narrows the
 // table.
 const facets={...o.facets,
   kind:{label:"Kind",switch:true,options:[["requirement","Requirement"],["treq","Technical requirement"]],test:(row,value)=>tree.isLeaf(row)&&(!value||row.level===value)},
   goal:{label:"Goal",options:tree.goals.map(goal=>[goal.id,goal.short||goal.label]),test:(row,value)=>tree.isLeaf(row)&&tree.goalOf.get(row.id)===value}};
 const panelOf=key=>{
   const view=viewOf(key),panel=o.panels[view.key]||(view.form==="table"?{...o.panels[view.projection],help:MAP_TABLE_HELP}:o.panels[view.projection]);
   return{...panel,facets:[...panel.facets,"goal"]};
 };
 const filters=mapFilters({facets,rows:o.filterRows,leaves:tree.leaves,view:()=>page.view,panel:panelOf,previews:key=>viewOf(key).form!=="table",rendered:()=>kinds.render(),
   changed:()=>{applyFocus();if(viewOf(page.view).form==="table")table.render();strip.sync();writeHash()},previewed:applyFocus,mark:o.markPanel,hideTip:()=>hideTip(true)});
 const kinds=mapKinds({leaves:tree.leaves,filters});
 // Every table starts with the contract, groups it by goal and capability, by goal or not at all, and downloads the same
 // first columns; the page adds its own columns and groups.
 const goalName=key=>tree.rowById.get(key)?.short||tree.rowById.get(key)?.label||"No goal";
 const table=mapTable({...o.table,
   columns:[["name","Contract","Contract, grouped as chosen","name"],...o.table.columns],
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
 // the mini-map, a row's marks (one per contract, in the view's colours) and the foot are the same in every layer. The
 // All layers table lists a layer's other views as rows below it.
 const plain=html=>String(html).replace(/<[^>]+>/g,"").replace(/\s+/g," ").trim();
 // A card in a measure says the measure in full, then the verdict it keeps.
 const spoken=(key,card)=>labelOf(key)+": "+plain(card.status)+", "+(card.tip||plain(card.count))+(card.health?" Health: "+plain(card.health.status)+", "+plain(card.health.count)+".":"");
 const projectionOfRow=key=>viewOf(key)?.projection??key;
 function stripCells(projection){
   let out="";
   tree.columns.leaves.forEach((leaf,index)=>{out+='<rect data-leaf="'+index+'" x="'+(leaf.x+1)+'" y="2" width="'+(MAP_CELL-2)+'" height="12" '+o.tiles.leaf(leaf.row,projection)+"/>"});
   if(o.tiles.mark)tree.columns.groups.forEach(group=>{
     const mark=o.tiles.mark(group.row,projection),goal=group.row.level==="goal";
     if(mark)out+='<rect x="'+(group.start-(goal?4:2))+'" y="'+(goal?.5:1.5)+'" width="'+(group.end-group.start+(goal?8:4))+'" height="'+(goal?15:13)+'" rx="2" fill="none" class="'+mark+'" vector-effect="non-scaling-stroke"/>';
   });
   return out;
 }
 // A view's thumbnail: its rings, its map in its colours, or a table. A card shows the thumbnail of the view its layer
 // opens in; the open card shows every view's thumbnail on its slider.
 // Its class is not table: the theme gives .table a margin.
 function tableThumb(){
   let out="";
   for(let line=0;line<6;line++){
     const y=2+line*6;
     out+='<rect x="2" y="'+y+'" width="24" height="3.4" rx="1" class="tf-map-thumb-name"/>';
     for(let cell=0;cell<4;cell++)out+='<rect x="'+(31+cell*9)+'" y="'+(y-.6)+'" width="5.4" height="4.6" rx="1" class="tf-map-thumb-cell"/>';
   }
   return'<svg class="tf-map-thumb tabular" viewBox="0 0 68 38" aria-hidden="true" focusable="false">'+out+"</svg>";
 }
 function viewThumb(view){
   if(view.form==="rings")return ringSets[view.ring].thumb();
   if(view.form==="table")return tableThumb();
   return tiles.thumb(row=>o.tiles.leaf(row,view.projection),o.tiles.mark&&(row=>o.tiles.mark(row,view.projection)));
 }
 const openingView=key=>viewOf(opening(key));
 // A map view has nothing to show when every contract the filters keep is blank in it. Overall's rings and table always
 // show the tree, and no contract kept at all is the filters' doing, which the count already says.
 function idleNote(view){
   if(!view||view.form!=="tiles"||!o.blank)return"";
   const shown=filters.shown(false),rows=tree.leaves.filter(row=>!shown||shown.has(row.id));
   if(!rows.length||!rows.every(row=>o.blank(row,view.projection)))return"";
   const label=o.tone?.(rows[0],view.projection)?.label||"blank";
   const kept=rows.length===1?"the one contract they keep is":rows.length===2?"both contracts they keep are":"all "+rows.length+" contracts they keep are";
   return"Nothing to show under the filters: "+kept+" “"+label+"”.";
 }
 function thumbOf(key){const view=openingView(key);return viewThumb(view).replace("<svg ",'<svg data-view="'+view.key+'" ')}
 function viewsHtml(key,lone){
   const views=lensesOf(key);
   if(views.length<2&&!lone)return"";
   const more=views.length>2&&key!==o.layers[0][0]?'<button type="button" class="tf-map-views-more" data-map-more="'+key+'" tabindex="-1" aria-expanded="false" aria-label="Show all '+views.length+' views"><i class="fa-solid fa-chevron-right" aria-hidden="true"></i>+'+(views.length-1)+"</button>":"";
   return'<span class="tf-map-views'+(views.length<2?" lone":"")+'" inert><span class="tf-map-views-track" role="radiogroup" aria-label="Views of '+escapeHtml(labelOf(key))+'"><span class="tf-map-knob" aria-hidden="true"></span>'
     +views.map(view=>{const tip=view.ask||view.tip,name=view.label||labelOf(view.layer);return'<button type="button" role="radio" class="tf-map-choice" data-map-view="'+view.key+'" aria-checked="false" tabindex="-1"'+(tip?' data-tip="'+escapeHtml(tip)+'"':"")+">"+viewThumb(view)+'<span class="tf-map-choice-name" data-name="'+escapeHtml(name)+'">'+escapeHtml(name)+"</span></button>"}).join("")
     +"</span>"+more+"</span>";
 }
 // A card's lines in one of its layer's views: health's verdict and count with its changes, or, where the page pairs a
 // measure with the verdict, the measure's line with the measure's changes; the "?" asks that view's question.
 function cardOf(key,view){
   const lines=o.strip.viewCard?.(key,view)||o.strip.card(key),changes=lines.changes||key;
   return{...lines,view:view.key,help:lines.health?view.ask:"",name:spoken(key,lines),delta:mapDelta(delta,changes,o.words(changes)),thumb:thumbOf(key)};
 }
 const strip=mapStrip({groups:o.strip.groups,layers:o.layers,columns:tree.columns,hint,views:viewsHtml,viewTip:key=>{const view=viewOf(key);return view?.ask||view?.tip||""},viewNote:key=>idleNote(viewOf(key)),viewList:key=>lensesOf(key).map(view=>({key:view.key,label:view.label||labelOf(view.layer)})),thumb:thumbOf,currentView:key=>openingView(key).key,selectView:key=>select(key,false),
   // A card speaks for the view its layer opens in: health's verdict, or the line of the measure in view. It holds the
   // lines of all its views, so it keeps its size when the view changes.
   card:key=>cardOf(key,openingView(key)),cards:key=>lensesOf(key).map(view=>cardOf(key,view)),
   row:key=>{
     if(LAYER_KEYS.includes(key))return{...o.strip.row(key),name:spoken(key,o.strip.card(key))};
     const view=viewOf(key),row=o.strip.row(view.projection);
     return{...row,label:view.label,sub:true,name:labelOf(view.layer)+", "+view.label+": "+plain(row.status)};
   },
   cells:key=>{const projection=projectionOfRow(key);return o.strip.cells?.(projection)??stripCells(projection)},
   subrows:key=>lensesOf(key).filter(view=>view.key!==key&&view.form!=="table").map(view=>view.key),
   foot:row=>strip.order().map(key=>{const says=o.says(row,key);return'<span class="tf-map-mark'+(says?.tone?" "+says.tone:"")+'">'+escapeHtml(labelOf(key))+": "+escapeHtml(says?.text||"–")+"</span>"}).join(" · "),
   current:()=>page.layer,currentRow:()=>viewOf(page.view).form==="table"||LAYER_KEYS.includes(page.view)?page.layer:page.view,
   select:(key,focus)=>select(opening(key),focus),focus:focusRow});
 const find=mapFind({hint,pick:focusRow,items:()=>tree.rows.filter(row=>row.level!=="product").map(row=>({row,path:tree.ancestors(row).map(item=>item.short||item.label).join(" › "),kind:MAP_KIND[row.level],...o.find(row)}))});
 function select(key,focus,keepFocus){
   const view=viewOf(key);
   if(!view)return;
   const changed=key!==page.view;
   Object.assign(page,{view:key,layer:view.layer,projection:view.projection});
   page.last[view.layer]=key;
   hideTip(true);
   // SVG elements have no hidden property: toggle the attribute itself.
   ringList.forEach(rings=>rings.svg.toggleAttribute("hidden",!(view.form==="rings"&&rings===ringSets[view.ring])));
   tiles.svg.toggleAttribute("hidden",view.form!=="tiles");
   $("tf-map-list-view").hidden=view.form!=="table";
   if(view.form==="tiles"&&view.projection!==page.tiled){page.tiled=view.projection;paint(true)}
   if(view.form==="rings")ringSets[view.ring].draw(frame,false);
   else if(view.form==="table")table.render();
   else tiles.layout(frame,false);
   o.selected?.(view);
   frame.setLegend(legendFor(key));
   filters.preview=null;
   filters.renderPanel(changed);
   // Nothing above the view changes height between views; this only catches a late font or window change.
   setTimeout(()=>frame.layout(false),0);
   strip.sync();
   if(changed&&!keepFocus)page.focusedId="";
   applyFocus();
   writeHash();
   strip.show(view.layer,focus);
 }
 // The view has an address: #view, #view:ID and ?filters. Back from a contract page and shared links return here.
 function writeHash(){
   const params=new URLSearchParams();
   filters.write(params);
   if(viewOf(page.view).form==="table")table.write(params);
   const query=params.toString(),hash="#"+page.view+(page.focusedId?":"+page.focusedId:"")+(query?"?"+query:"");
   if(location.hash!==hash)history.replaceState(history.state,"",hash);
 }
 function focusRow(id){
   const row=tree.rowById.get(id),view=viewOf(page.view);
   if(!row)return;
   page.focusedId=id;
   if(view.form==="table"){
     const shown=filters.shown(false);
     if(tree.isLeaf(row)&&shown&&!shown.has(id))filters.clear();
     table.render();
     const target=tree.isLeaf(row)?table.row(id):null;
     if(target){target.scrollIntoView({block:"center"});target.classList.add("flash");setTimeout(()=>target.classList.remove("flash"),1700)}
     writeHash();
     return;
   }
   const entry=(view.form==="rings"?ringSets[view.ring].byId:tiles.byId).get(id);
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
   const view=viewOf(page.view);
   // A redraw replaces the shapes: the hover card follows the focused mark to its new shape.
   const refocus=card.visible()&&page.focusedId&&view.form!=="table"?page.focusedId:"";
   const moved=tiles.layout(frame,force),redrawn=ringList.map(rings=>rings.draw(frame,force)).some(Boolean);
   if(view.form==="table")table.fit();
   if(moved)strip.build();
   keepCard();
   const target=page.pendingFocus||(moved||redrawn?refocus:"");
   if(target&&view.form!=="table")focusRow(target);
 }
 function followStage(width){
   if(!width)return;
   const view=viewOf(page.view);
   if(view.form==="rings")ringSets[view.ring].squeeze(width);
   else if(view.form==="tiles")tiles.layout(frame,false);
   keepCard();
 }
 const frame=mapFrame({layout:layoutViews,follow:followStage});
 Object.assign(page,{card,hint,tiles,rings:ringSets[Object.keys(ringSets)[0]],ringSets,filters,kinds,table,strip,find,frame,select,focusRow});
 page.start=()=>{
   frame.stage.addEventListener("click",event=>{
     const link=event.target.closest("a"),entry=link&&[...tiles.entries,...ringList.flatMap(rings=>rings.entries)].find(item=>item.link===link);
     if(entry&&entry.row.level!=="product"){page.focusedId=entry.row.id;writeHash()}
   },true);
   window.addEventListener("hashchange",readHash);
   ["tf-map-tools","tf-map-panel","tf-map-legendbar"].forEach(id=>hint.watch($(id)));
   mapChanges($("tf-map-changes"),delta,on=>{page.changesOn=on;frame.setLegend(legendFor(page.view));applyFocus()});
   mapCopy($("tf-map-copy"),writeHash);
   // Keys: Esc closes the card, / find, F filters, 1–9 layers in strip order, V the next view of the layer, T the All
   // layers table.
   document.addEventListener("keydown",event=>{
     if(event.key==="Escape"){hideTip(true);return}
     if(event.defaultPrevented||event.metaKey||event.ctrlKey||event.altKey||find.isOpen())return;
     if(event.target.closest?.("input,textarea,select,[contenteditable]"))return;
     if(event.key==="/"){event.preventDefault();find.open();return}
     if(event.key==="f"||event.key==="F"){event.preventDefault();filters.setPanel(!filters.open,true);return}
     if(/^[1-9]$/.test(event.key)){const key=strip.order()[Number(event.key)-1];if(key){event.preventDefault();select(opening(key),true)}return}
     if(event.key==="v"||event.key==="V"){const lenses=lensesOf(page.layer);if(lenses.length>1){event.preventDefault();select(lenses[(lenses.findIndex(view=>view.key===page.view)+1)%lenses.length].key,false)}return}
     if(event.key==="t"||event.key==="T"){event.preventDefault();strip.toggleTable()}
   });
   // A ring's name opens its layer; pointing at it shows the ring.
   const ringName=event=>event.target.closest?.("[data-map-ring]");
   ringList.forEach(rings=>{
     rings.svg.addEventListener("pointerover",event=>{const name=ringName(event);if(name){hideTip(true);rings.showBand(name.dataset.mapRing);hint.show(name)}});
     rings.svg.addEventListener("pointerout",event=>{const name=ringName(event);if(name&&!name.contains(event.relatedTarget)){rings.clear();hint.hide()}});
     rings.svg.addEventListener("click",event=>{const name=ringName(event);if(name)select(opening(name.dataset.mapRing),false)});
     rings.svg.addEventListener("keydown",event=>{const name=ringName(event);if(name&&(event.key==="Enter"||event.key===" ")){event.preventDefault();select(opening(name.dataset.mapRing),true)}});
   });
   // The first view first; the panel opens as the reader left it, without sliding in.
   frame.body.classList.add("tf-map-still");
   filters.setPanel(filters.startOpen,false);
   $("tf-map-stamp").innerHTML=mapStamp(o.insights?.run);
   strip.build();
   frame.layout(true);
   filters.render();
   if(!readHash())select(VIEWS[0].key,false);
   setTimeout(()=>frame.body.classList.remove("tf-map-still"),200);
   document.fonts?.ready?.then(()=>frame.layout(true));
 };
 o.attach?.(page);
 return page;
}"""


def map_tools(
    about: str,
    *,
    filters_tip: str = "Open the filters that fit the current layer beside it (F).",
    find_tip: str = "Find a goal, capability or contract and show it in the current layer (/).",
    copy_tip: str = "Copy a link to this layer, its filters and the selected contract.",
    changes: bool = True,
) -> str:
    """The tools line: the retained run, or the active filters and how many rows they keep in its
    place, and the actions. A page without an earlier run to compare with leaves Changes out."""
    return (
        '<div class="tf-map-tools" id="tf-map-tools"><span class="tf-map-lead" id="tf-map-lead">'
        '<span class="tf-map-stamp" id="tf-map-stamp"></span>'
        f'<span class="tf-map-help" aria-hidden="true" data-tip="{about}">?</span>'
        '<span class="tf-map-filters" id="tf-map-filters" role="group" aria-label="Active filters" hidden>'
        '<span class="tf-map-chips" id="tf-map-chips"></span>'
        '<span class="tf-map-total" id="tf-map-total" aria-live="polite"></span>'
        '<button type="button" class="tf-map-clear" data-clear>Clear all</button></span></span>'
        '<span class="tf-map-actions">'
        '<button type="button" class="tf-map-action" id="tf-map-panel-toggle" aria-expanded="false" '
        f'aria-controls="tf-map-panel" data-tip="{filters_tip}">'
        '<i class="fa-solid fa-filter" aria-hidden="true"></i>Filters'
        '<span class="tf-map-badge" id="tf-map-filter-badge" hidden></span><kbd>F</kbd></button>'
        '<button type="button" class="tf-map-action" id="tf-map-find-open" aria-haspopup="dialog" '
        f'aria-controls="tf-map-find" data-tip="{find_tip}">'
        '<i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>Find<kbd>/</kbd></button>'
        + (
            '<button type="button" class="tf-map-action" id="tf-map-changes" aria-pressed="false">'
            '<i class="fa-solid fa-code-compare" aria-hidden="true"></i>Changes</button>'
            if changes
            else ""
        )
        + f'<button type="button" class="tf-map-action" id="tf-map-copy" data-tip="{copy_tip}">'
        '<i class="fa-solid fa-link" aria-hidden="true"></i><span>Copy link</span></button>'
        "</span></div>"
    )


def map_panel(title: str, kinds_label: str, label: str) -> str:
    """The side panel: the kind switch under its title, the same in every view, then the view's own filters."""
    return (
        f'<aside class="tf-map-panel" id="tf-map-panel" aria-label="{label}" inert>'
        '<div class="tf-map-panel-inner"><div class="tf-map-panel-kinds">'
        f'<div class="tf-map-panel-top"><span class="tf-map-facet-title">{title}</span>'
        '<button type="button" class="tf-map-close" id="tf-map-panel-close" aria-label="Close the filters">&times;</button></div>'
        f'<span class="tf-map-kinds" id="tf-map-kinds" role="group" aria-label="{kinds_label}"></span></div>'
        '<div class="tf-map-panel-head"><span class="tf-map-panel-title" id="tf-map-panel-title"></span></div>'
        '<div id="tf-map-panel-body"></div></div></aside>'
    )


def map_find(label: str, placeholder: str, foot: str) -> str:
    """Find: a dialog over the page that picks a goal, capability or contract by name or ID."""
    return (
        f'<div class="tf-map-find" id="tf-map-find" role="dialog" aria-modal="true" aria-label="{label}" hidden>'
        '<div class="tf-map-find-box"><input class="tf-map-find-input" id="tf-map-find-input" type="search" '
        f'placeholder="{placeholder}" autocomplete="off" spellcheck="false" '
        'role="combobox" aria-expanded="true" aria-controls="tf-map-find-list">'
        '<div class="tf-map-find-list" id="tf-map-find-list" role="listbox" aria-label="Matches"></div>'
        f'<div class="tf-map-find-foot">{foot}</div></div></div>'
    )


def map_frame(rings_label: str, tiles_label: str) -> str:
    """The legend bar and the body: the side panel, then the stage with the rings, the map and the
    contracts table; then Find and the hover card. The legend bar is one line aligned with the view, whose overflow
    opens from a +N at its end; a layer's views are on its open card in the strip. The side panel starts with the
    Kind switch, the same in every view, above the view's own filters."""
    return (
        '<div class="tf-map-legendbar" id="tf-map-legendbar">'
        '<div class="tf-map-legend" id="tf-map-legend" aria-hidden="true"></div>'
        '<div class="tf-map-more-pop" id="tf-map-more-pop" aria-hidden="true" hidden></div></div>'
        '<div class="tf-map-body" id="tf-map-body">'
        + map_panel("Contracts", "Contracts by kind", "Filters for the current layer")
        + '<div class="tf-map-stage" id="tf-map-stage">'
        f'<svg class="tf-map-view tf-map-rings" id="tf-map-rings" role="group" aria-label="{rings_label}"></svg>'
        f'<svg class="tf-map-view tf-map-tiles" id="tf-map-tiles" role="group" aria-label="{tiles_label}" hidden></svg>'
        '<div class="tf-map-list-view" id="tf-map-list-view" hidden><div class="tf-map-list-bar">'
        '<span class="tf-map-list-bar-label">Group by</span><span class="tf-map-seg" id="tf-map-group-by"></span>'
        '<span class="tf-map-summary" id="tf-map-summary"></span>'
        '<button type="button" class="tf-map-action" id="tf-map-csv">'
        '<i class="fa-solid fa-download" aria-hidden="true"></i>CSV</button></div>'
        '<div class="tf-map-list-wrap" id="tf-map-list"></div></div>'
        "</div></div>"
        + map_find(
            "Find on the map",
            "Find a goal, capability or contract by name or ID",
            "↑ ↓ move · Enter shows it in the current layer · Esc closes",
        )
        + '<div id="tf-map-card" class="tf-map-card" role="tooltip" aria-hidden="true"></div>'
    )


def map_strip(page: str, legend: str) -> str:
    """The layer strip: cards, scroll edges, the All layers table and a narrow page's views row."""
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
        '<div class="tf-map-views-row" id="tf-map-views-row"></div>'
        '<div id="tf-map-hint" class="tf-map-hint" role="tooltip" aria-hidden="true"></div>'
    )


HEALTH_MAP_CSS = r"""/* Health's palette: pass, fail and not applicable, and the ink of their words. The shared map does the rest. */
#verification-health-map{--tf-hm-pass:#8ed3a2;--tf-hm-fail:#dc3f47;--tf-hm-na:#dde0e5;--tf-hm-pass-ink:#1f7a3f;--tf-hm-fail-ink:#c42b34;--tf-hm-na-strong:color-mix(in srgb,var(--tf-hm-na) 86%,#000)}
html[data-theme=dark] #verification-health-map{--tf-hm-pass:#22603a;--tf-hm-fail:#e5484d;--tf-hm-na:#2f353d;--tf-hm-pass-ink:#5fcf85;--tf-hm-fail-ink:#ff6b70;--tf-hm-na-strong:color-mix(in srgb,var(--tf-hm-na) 78%,#fff)}
.tf-health-verdict{font-size:.78rem;font-weight:700;letter-spacing:.02em}
.tf-health-verdict.failed{color:var(--tf-hm-fail-ink)}.tf-health-verdict.passed{color:var(--tf-hm-pass-ink)}
.tf-map-sw.passed{background:var(--tf-hm-pass)}.tf-map-sw.failed{background:var(--tf-hm-fail)}.tf-map-sw.na{background:var(--tf-hm-na)}
.tf-map-sw.own{position:relative;border:1.5px solid var(--tf-hm-fail);border-radius:4px;box-shadow:none}
.tf-map-sw.own::after{content:"";position:absolute;left:2px;top:2px;width:5px;height:5px;border-radius:50%;background:var(--tf-hm-fail)}
/* What health judges on both views: contracts in their verdict, goals and capabilities outlined red where their
   own check fails, the verdict dot before a name, the product verdict and the ring names in their verdict. */
#verification-health-map .tf-map-tile.passed{fill:var(--tf-hm-pass)}
#verification-health-map .tf-map-tile.failed{fill:var(--tf-hm-fail)}
#verification-health-map .tf-map-tile.na{fill:var(--tf-hm-na)}
#verification-health-map .tf-health-own-failed{stroke:var(--tf-hm-fail);stroke-width:1.6}
#verification-health-map .tf-map-dot.passed{fill:var(--tf-hm-pass-ink)}
#verification-health-map .tf-map-dot.failed{fill:var(--tf-hm-fail)}
#verification-health-map .tf-map-dot.na{opacity:0}
#verification-health-map .tf-map-tiles.tf-health-product-failed{border-radius:14px;box-shadow:0 0 0 1.5px var(--tf-hm-fail)}
/* A failure among few draws the eye without shouting: the failing dot sends out a slow ring that fades, like a
   beacon, and the failing outline turns amber and back with a soft glow. Passing marks stay still. Where more fail,
   the red is plain enough and nothing moves; with reduced motion a still halo takes the ring's place. */
#verification-health-map{--tf-hm-alert:#b45309}
html[data-theme=dark] #verification-health-map{--tf-hm-alert:#f59e0b}
#verification-health-map .tf-health-alert .tf-map-dot.failed{stroke:var(--tf-hm-fail);stroke-width:0;animation:tf-health-ping 2.6s cubic-bezier(.2,.6,.35,1) infinite}
#verification-health-map .tf-health-alert .tf-health-own-failed{animation:tf-health-amber 3.2s ease-in-out infinite}
@keyframes tf-health-ping{0%{stroke-width:0;stroke-opacity:.8}75%,100%{stroke-width:8px;stroke-opacity:0}}
@keyframes tf-health-amber{0%,100%{stroke:var(--tf-hm-fail);filter:none}50%{stroke:var(--tf-hm-alert);filter:drop-shadow(0 0 3px color-mix(in srgb,var(--tf-hm-alert) 70%,transparent))}}
@media(prefers-reduced-motion:reduce){#verification-health-map .tf-health-alert .tf-map-dot.failed{stroke-width:5px;stroke-opacity:.35}#verification-health-map .tf-health-alert .tf-health-own-failed{stroke:var(--tf-hm-alert);stroke-width:2.2}}
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
/* A layer panel opens its items in the explorer: one quiet line above its filters, in the same place on every layer. */
.tf-health-items{display:inline-block;margin:0 0 .7rem;font-size:.8rem;font-weight:600;color:var(--tf-map-link,var(--pst-color-link));text-decoration:none}
.tf-health-items:hover,.tf-health-items:focus-visible{text-decoration:underline}
.tf-health-why b{font-weight:700}
.tf-health-find-marks{display:inline-flex;gap:2px}
.tf-health-find-marks i{width:9px;height:9px;border-radius:2px;background:var(--tf-hm-na-strong)}
.tf-health-find-marks i.passed{background:var(--tf-hm-pass)}.tf-health-find-marks i.failed{background:var(--tf-hm-fail)}
.tf-health-find-marks i.first{margin-right:3px}
/* What health judges in the strip: the failing and passing tones, and the colours of Changes. */
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
.tf-health-cell{width:1%;white-space:nowrap}
.tf-health-checks{margin-left:.35rem;font-size:.66rem;font-variant-numeric:tabular-nums;color:var(--pst-color-text-muted)}
.tf-health-fails{font-size:.7rem;font-weight:750;white-space:nowrap;color:var(--tf-hm-fail-ink)}
.tf-health-why-cell{min-width:14rem;font-size:.7rem;color:var(--pst-color-text-muted)}"""

HEALTH_MAP_JS = r"""// Health judges: every layer says whether each contract's evidence is enough. It is every layer's first view.
function healthMap(model){
let map=null;
const LAYERS=MAP_HEALTH_LAYERS;
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
// What health judges: the verdict of every goal, capability and contract in every layer.
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
 const svg=document.getElementById("tf-map-tiles");
 svg.classList.toggle("tf-health-product-failed",key!=="overall"&&status(root,key)==="failed");
 // A goal or capability that fails its own check draws the eye while few do, at most three or a quarter of those
 // judged: its dot sends out a slow ring and its outline turns amber and back. Where more fail, the red is plain enough.
 const judged=entries.filter(entry=>entry.kind!=="leaf"&&status(entry.row,key)!=="na");
 const failing=judged.filter(entry=>status(entry.row,key)==="failed").length;
 svg.classList.toggle("tf-health-alert",failing>0&&failing<=Math.max(3,judged.length/4));
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
// The verdict as a mark alone, for a card that shows one of its layer's measures: the card keeps its place among the
// failing or passing layers, and the mark's hint says the verdict it keeps.
function layerMark(key){
 const verdict=verdictOf(key);
 return'<span class="tf-health-verdict '+verdict+' tf-map-mark-only" data-tip="Health: '+word(verdict)+", "+countLine(key)+'"><i class="fa-solid '+(verdict==="passed"?"fa-circle-check":"fa-circle-xmark")+'" aria-hidden="true"></i></span>';
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
// The colour a layer gives a mark, in legend order, for the bars that split marks over a layer's colours.
function toneOf(row,key){
 if(row.level==="product")return null;
 const value=status(row,key),index=VERDICTS.findIndex(item=>item[0]===value);
 return{key:value,fill:VERDICT_FILL[value],rank:index,label:VERDICTS[index][1]};
}
const FACETS={};
LAYERS.forEach(([key,label])=>{
 const causes=layerCauses[key]||[],ids=new Map(causes.map(cause=>[cause.id,new Set(cause.ids)]));
 FACETS[key]={label,options:VERDICTS,swatch:value=>mapSwatch(value),test:(row,value)=>status(row,key)===value};
 FACETS["why-"+key]={label:"Why "+label+" fails",title:"Why it fails",help:"One red mark can have several causes.",empty:"Nothing fails here.",options:causes.map(cause=>[cause.id,cause.label]),tip:value=>causes.find(cause=>cause.id===value)?.hint||"",test:(row,value)=>!!ids.get(value)?.has(row.id)};
});
// The panel follows the layer. Overall shows the layer × verdict matrix, health's counterpart of the depth rings'
// test level × boundary: one row per ring, one column per colour.
// The items behind a layer's red marks, one row each in the Verification Explorer: the layer's failing and unknown
// items, narrowed to the causes chosen here.
function explorerLink(key){
 const chosen=[...(map.filters.sets["why-"+key]||[])];
 const params=new URLSearchParams({layer:key,status:"fail,unknown"});
 if(chosen.length)params.set("cause",chosen.join(","));
 return '<a class="tf-health-items" href="verification-explorer.html#'+escapeHtml(params.toString())+'" data-tip="'+escapeHtml((chosen.length?"The items with the causes chosen here":"The failing and unknown items of this layer")+", one row each: what each one is, why it fails and how to fix it.")+'">Items in the explorer ↗</a>';
}
const PANELS=Object.fromEntries(LAYERS.map(([key,label])=>[key,{title:label,help:"Point at Fail, Pass, N/A or a cause to light its marks on the map, or click it to keep only them.",before:()=>explorerLink(key),facets:[key,"why-"+key]}]));
PANELS.overall={title:"Layer × health",help:"Point at a cell to light its ring in every ray, or click it to keep only those marks there.",before:()=>matrixHtml(),facets:[]};
function matrixHtml(){
 const filters=map.filters;
 return mapMatrix({label:"Marks by layer and health",template:"6.6rem repeat(3,minmax(0,1fr))",
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
   help:key==="overall"?"Inside out: goals, capabilities and contracts, then one ring per layer; failing layers sit inside the dashed line, passing ones outside, and the table shows the same health per layer.":"its colour is its health in this layer, and a red outline marks a goal or capability that fails its own check."};
}
// The contracts table: the rings unrolled, one column per layer in the strip's order, each contract's verdict there
// with what it counts (the mark opens that layer's evidence), then why it fails. A layer that judges no contract keeps
// its column, empty, as its ring does. A group row counts what fails in every column.
const tableOrder=()=>{const order=layerOrder();return[order.first,...order.failing,...order.passing]};
const failsIn=row=>LAYERS.slice(1).filter(([key])=>status(row,key)==="failed").map(([key])=>key);
const allCauses=row=>LAYERS.slice(1).flatMap(([key])=>causesOf(row.id,key));
const countOfChecks=(row,key)=>{const own=row.own?.[key];return key!=="overall"&&own?.total?own.passed+"/"+own.total:""};
const markHtml=(row,key)=>{const value=status(row,key),detail=key==="overall"?"":row.own?.[key]?.detail;return'<a class="tf-health-mark '+value+'" href="'+escapeHtml(hrefFor(row,key))+'" title="'+escapeHtml(layerByKey.get(key)[1]+": "+word(value)+(detail?", "+detail:""))+'">'+(value==="failed"?"✕":value==="passed"?"✓":"–")+"</a>"};
function tableCell(row,key){
 if(key==="why")return'<td class="tf-health-why-cell">'+escapeHtml(allCauses(row).map(cause=>cause.label).join(" · "))+"</td>";
 const checks=countOfChecks(row,key);
 return'<td class="tf-health-cell">'+markHtml(row,key)+(checks?'<span class="tf-health-checks">'+checks+"</span>":"")+"</td>";
}
function groupCell(list,key){
 if(key==="why")return"<td></td>";
 const judged=list.filter(row=>status(row,key)!=="na"),failing=judged.filter(row=>status(row,key)==="failed").length;
 return'<td class="tf-health-cell">'+(failing?'<span class="tf-health-fails" title="'+escapeHtml(failing+" of "+judged.length+" fail")+'">✕ '+failing+"</span>":judged.length?'<span class="tf-map-muted" title="All pass">✓</span>':'<span class="tf-map-muted" title="Judges no contract">–</span>')+"</td>";
}
const TABLE={
 columns:[...tableOrder().map(key=>{const[,label,help]=layerByKey.get(key);return[key,label,help]}),["why","Why it fails","The causes of its red marks in every layer"]],
 groups:[["verdict","Health"],["fails","Fails in"]],
 keys:(row,group)=>group==="verdict"?[status(row,"overall")]:failsIn(row).length?failsIn(row):["none"],
 name:(group,key)=>group==="verdict"?({failed:"Fail",passed:"Pass",na:"N/A"}[key]||key):key==="none"?"Fails nowhere":layerByKey.get(key)[1],
 order:(group,keys)=>(group==="verdict"?["failed","passed","na"]:[...map.strip.order(),"none"]).filter(key=>keys.includes(key)),
 sortValue:(row,key)=>key==="why"?allCauses(row).length:{failed:2,passed:1,na:0}[status(row,key)],
 stats:list=>{
   const failing=list.filter(row=>status(row,"overall")==="failed").length;
   const by=LAYERS.slice(1).map(([key,label])=>[label,list.filter(row=>status(row,key)==="failed").length]).filter(([,count])=>count).sort((a,b)=>b[1]-a[1]);
   return(failing?failing+" fail":"all pass")+(by.length?" · "+by.map(([label,count])=>label+" "+count).join(", "):"");
 },
 csv:{head:[...tableOrder(),"why"],line:row=>[...tableOrder().map(key=>word(status(row,key))),allCauses(row).map(cause=>cause.label).join("; ")]}
};
// Health for the map. Find lists what fails in most layers first and shows each item's verdict per layer.
return{
 tree,layers:LAYERS,insights,words:()=>["newly failing","fixed"],
 href:hrefFor,says,describe,paint,legend:legendHtml,tone:toneOf,blank:(row,key)=>status(row,key)==="na",
 facets:FACETS,panels:PANELS,filterRows:marked,
 strip:{groups:layerGroups,card:layerCard,row:layerRow,mark:layerMark},
 table:TABLE,tableCell,groupCell,
 tiles:{leaf:(row,key)=>'class="tf-map-tile '+status(row,key)+'"',mark:(row,key)=>status(row,key)==="failed"?"tf-health-own-failed":""},
 rings:RINGS,
 find:row=>({rank:-LAYERS.slice(1).filter(layer=>status(row,layer[0])==="failed").length,
   badge:()=>'<span class="tf-health-find-marks">'+map.strip.order().map((key,position)=>'<i class="'+status(row,key)+(position?"":" first")+'" title="'+escapeHtml(layerByKey.get(key)[1])+'"></i>').join("")+"</span>"}),
 attach:page=>{map=page}
};
}"""

DEPTH_MAP_CSS = r"""/* The measures' palette: sequential scales for test levels, boundaries, model validation and mutants caught, with no
   red or green because a measure does not judge. The shared map does the rest. */
#verification-health-map{--tf-dm-empty:#e9ecf0;--tf-dm-track:color-mix(in srgb,var(--pst-color-text-base) 5%,transparent);--tf-dm-hatch:color-mix(in srgb,var(--pst-color-text-base) 20%,transparent);--tf-dm-lv-0:#c6dbef;--tf-dm-lv-1:#9ecae1;--tf-dm-lv-2:#6baed6;--tf-dm-lv-3:#3182bd;--tf-dm-lv-4:#08519c;--tf-dm-local:#c2c9d2;--tf-dm-sub:#cbb6e8;--tf-dm-rep:#9a7ccf;--tf-dm-live:#5a3aa3;--tf-dm-t0:#ecdcbd;--tf-dm-t1:#dcc398;--tf-dm-t2:#c29e5c;--tf-dm-t3:#957541;--tf-dm-t4:#5f4a27;--tf-dm-det-lo:#e1f3ee;--tf-dm-det-hi:#12776a}
html[data-theme=dark] #verification-health-map{--tf-dm-empty:#2b3038;--tf-dm-track:color-mix(in srgb,var(--pst-color-text-base) 6%,transparent);--tf-dm-lv-0:#22405f;--tf-dm-lv-1:#244d74;--tf-dm-lv-2:#2c6aa0;--tf-dm-lv-3:#468fcf;--tf-dm-lv-4:#8cc2f2;--tf-dm-local:#4b5360;--tf-dm-sub:#4a3a70;--tf-dm-rep:#7157ad;--tf-dm-live:#ad91e6;--tf-dm-t0:#4d4331;--tf-dm-t1:#67583a;--tf-dm-t2:#8f7543;--tf-dm-t3:#b6975b;--tf-dm-t4:#ddc28c;--tf-dm-det-lo:#1b3935;--tf-dm-det-hi:#52cbb7}
.tf-map-sw.pale{opacity:.45}
.tf-map-sw.hatch{background:repeating-linear-gradient(45deg,var(--tf-dm-empty) 0 3px,var(--tf-dm-hatch) 3px 4.5px)}
.tf-map-spread>i.hatch{background:repeating-linear-gradient(45deg,var(--tf-dm-empty) 0 2px,var(--tf-dm-hatch) 2px 3px)}
.tf-map-sw.gap{background:none;box-shadow:none;border:1.5px dashed var(--tf-map-ring)}
.tf-depth-grad{display:inline-block;width:92px;height:10px;border-radius:3px;background:linear-gradient(90deg,var(--tf-dm-det-lo),var(--tf-dm-det-hi))}
/* What the depth rings show: a level without tests and a required cell without a test. */
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
/* A measure as one value in a table cell: its colour and its words. */
.tf-depth-token{display:inline-flex;align-items:center;gap:.4rem;white-space:nowrap}
.tf-depth-value{white-space:nowrap}
.tf-depth-token .tf-map-sw{width:10px;height:10px}
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

DEPTH_MAP_JS = r"""// The measures (once the Depth Map) judge nothing: they say how deep, how realistic and how strong each contract's
// evidence is, beside each layer's health.
function depthMap(model){
let map=null;
const LEVELS=["component","component_integration","system","system_integration","acceptance"];
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
const DETECT_FILL={low:"color-mix(in oklab, var(--tf-dm-det-hi) 30%, var(--tf-dm-det-lo))",mid:"color-mix(in oklab, var(--tf-dm-det-hi) 65%, var(--tf-dm-det-lo))",high:"color-mix(in oklab, var(--tf-dm-det-hi) 92%, var(--tf-dm-det-lo))"};
const DETECT_NAME={high:"80% and more",mid:"50–79%",low:"Below 50%",none:"Not measured"};
const TRUST_ORDER=["na","l0","l1","l2","l3","l4"];
// The swatch of an option matches the colour it has in the layer, so the panel reads as the layer's legend.
const swatchHtml=style=>!style?"":style==="hatch"||style==="gap"?mapSwatch(style):style==="pale"?mapSwatch("pale","var(--tf-dm-sub)"):mapSwatch("",style);
const FACETS={
 cell:{label:"Cell",pipe:true,name:key=>{const[level,bound]=key.split("|");return LEVEL_NAME[level]+" × "+BOUND_NAME[bound]},valid:key=>key.includes("|"),test:(row,key)=>C[row.id].cells.some(cell=>cellKey(cell[0],cell[1])===key)},
 producer:{label:"Substitute or recording",title:"Substitutes and recordings",help:"The tools that stand in for real services in the tests, with how well each one has been checked against the real thing.",name:key=>P[key]?.title||key,valid:key=>key in P,test:(row,key)=>C[row.id].producers.includes(key),panel:()=>leversHtml()},
 profile:{label:"Against the profile",help:"Whether a contract's tests sit exactly where its verification profile asks, somewhere else too, or are missing where it asks.",options:[["exact","As the profile asks"],["beyond","Beyond the profile"],["missing","Required cell without tests"]],test:(row,key)=>profileStates(C[row.id]).includes(key),swatch:value=>swatchHtml({exact:cssVar("--tf-dm-sub"),beyond:"pale",missing:"gap"}[value])},
 detect:{label:"Mutants caught",help:"Share of small deliberate bugs in the contract's own code that its own tests catch.",options:Object.entries(DETECT_NAME),test:(row,key)=>detectBand(C[row.id])===key,swatch:value=>swatchHtml(DETECT_FILL[value]||"hatch")},
 // Empty levels and boundaries stay (disabled) because they show the ceiling.
 deepest:{label:"Deepest test level",keepEmpty:value=>value!=="notests",options:[...LEVELS.map(level=>[level,LEVEL_NAME[level]]),["notests","No passing tests"]],test:(row,key)=>(C[row.id].deepest||"notests")===key,swatch:value=>swatchHtml(value==="notests"?cssVar("--tf-dm-empty"):cssVar("--tf-dm-lv-"+LEVELS.indexOf(value)))},
 real:{label:"Most realistic boundary",keepEmpty:value=>value!=="notests",options:[...BOUNDS.map(bound=>[bound,BOUND_NAME[bound]]),["notests","No passing tests"]],test:(row,key)=>(C[row.id].real||"notests")===key,swatch:value=>swatchHtml(value==="notests"?cssVar("--tf-dm-empty"):cssVar(BOUND_VAR[value]))},
 trust:{label:"Model validation",options:TRUST_ORDER.map(level=>[level,TRUST_NAME[level]]),test:(row,key)=>C[row.id].trust===key,swatch:value=>swatchHtml(cssVar(TRUST_VAR[value]))},
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
 if(c.failing)body+='<span class="note">'+plural(c.failing,"failing test is","failing tests are")+" left out here; the Health view shows failures.</span>";
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
// The colour a layer gives a contract, in legend order, for the bars that split contracts over a layer's colours.
// Overall has no one colour per contract; its bars take the boundary, the colour its rings and legend show.
function tone(row,key){
 if(!isLeaf(row))return null;
 const c=C[row.id],none={key:"notests",fill:cssVar("--tf-dm-empty"),rank:LEVELS.length+BOUNDS.length,label:"No passing tests"};
 if(key==="overall"||key==="boundary")return c.real?{key:c.real,fill:cssVar(BOUND_VAR[c.real]),rank:BOUNDS.indexOf(c.real),label:BOUND_NAME[c.real]}:none;
 if(key==="level")return c.deepest?{key:c.deepest,fill:cssVar("--tf-dm-lv-"+LEVELS.indexOf(c.deepest)),rank:LEVELS.indexOf(c.deepest),label:LEVEL_NAME[c.deepest]}:none;
 if(key==="trust")return{key:c.trust,fill:cssVar(TRUST_VAR[c.trust]||"--tf-dm-local"),rank:TRUST_ORDER.indexOf(c.trust),label:TRUST_NAME[c.trust]||c.trust};
 const band=detectBand(c);
 return{key:band,fill:DETECT_FILL[band],cls:band==="none"?"hatch":"",rank:["low","mid","high","none"].indexOf(band),label:DETECT_NAME[band]};
}
// Whether a contract has nothing to show in a layer: no passing tests, no substitute behind it, or no mutants measured.
// Local tests are something: the boundary's own "none" is its Local colour.
function blank(row,key){
 const said=tone(row,key);
 return!!said&&(said.key==="notests"||key==="trust"&&said.key==="na"||key==="detect"&&said.key==="none");
}
// A measure as one value in a table cell: its colour and its words, the model check as its level, and the share of
// mutants caught as a bar that opens its fault model, or why it is not measured.
function measureHtml(row,key){
 const c=C[row.id],value=ratio(c);
 if(key==="trust")return c.trust==="na"?'<span class="tf-map-muted" title="No substitute or recording">—</span>':'<span class="tf-depth-trust" style="background:var('+TRUST_VAR[c.trust]+')" title="'+escapeHtml(TRUST_NAME[c.trust])+'">'+c.trust.toUpperCase()+"</span>";
 if(key==="detect")return value===null?'<span class="tf-map-muted" title="'+escapeHtml((REASON[c.reason]||["",c.reason])[1])+'">'+escapeHtml((REASON[c.reason]||[c.reason])[0])+"</span>"
   :'<a href="'+escapeHtml(c.fault_href)+'" class="tf-map-muted"><span class="tf-depth-detbar"><i style="width:'+pct(value)+'"></i></span>'+pct(value)+" · "+c.detect[0]+"/"+c.detect[1]+"</a>";
 const said=tone(row,key);
 return said.key==="notests"?'<span class="tf-map-muted" title="No passing tests">No tests</span>':'<span class="tf-depth-token">'+mapSwatch("",said.fill)+escapeHtml(key==="level"?LEVEL_SHORT[said.key]:said.label)+"</span>";
}
// A group of contracts in one measure: how it splits over the measure's colours, or the median share of mutants caught.
function measureGroupHtml(list,key){
 if(key!=="detect")return mapSpread(list,row=>tone(row,key),true);
 const measured=list.map(row=>C[row.id]).filter(c=>c.detect),middle=median(measured.map(ratio));
 return middle===null?'<span class="tf-map-muted">—</span>':'<span class="tf-map-muted" title="Median of '+plural(measured.length,"measured contract","measured contracts")+'">median <b>'+pct(middle)+"</b></span>";
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
// substitutes are the measures' own sections; the shared filters draw the rest.
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

// The contracts table: the measures' columns and groups.
function sortValue(row,key){
 const c=C[row.id];
 if(LEVELS.includes(key))return c.cells.filter(cell=>cell[0]===key).reduce((sum,cell)=>sum+cell[2],0);
 if(key==="trust")return["na","l4","l3","l2","l1","l0"].indexOf(c.trust);
 if(key==="detect"){const value=ratio(c);return value===null?-1:value}
 if(key==="classes")return c.classes.required?(c.classes.caught||0)/c.classes.required:-1;
 return c.tests;
}
// One cell of the contracts table per column: a level's cells (covered of required cases, tests beyond the profile or
// a required cell without a test), the weakest model check, the share of mutants caught, the required fault classes
// detected and the own passing tests.
function tableCell(row,key){
 const c=C[row.id];
 if(LEVELS.includes(key)){
   let chips="";
   BOUNDS.forEach(bound=>{
     const cell=cellOf(c,key,bound),req=wants(c,key,bound),cases=caseOf(c,key,bound);
     if(req&&cell)chips+='<span class="tf-depth-cchip" style="background:'+shade(bound,true)+'" title="'+escapeHtml(BOUND_NAME[bound]+": "+(cases?cases[2]+" of "+cases[3]+" required cases covered by ":"")+plural(cell[2],"test","tests"))+'">'+BOUND_SHORT[bound]+" "+(cases?cases[2]+"/"+cases[3]:cell[2])+"</span>";
     else if(cell)chips+='<span class="tf-depth-cchip extra" style="background:'+shade(bound,false)+'" title="'+escapeHtml(BOUND_NAME[bound]+": "+plural(cell[2],"test","tests")+" beyond the profile")+'">'+BOUND_SHORT[bound]+" +"+cell[2]+"</span>";
     else if(req)chips+='<span class="tf-depth-cchip gap" title="'+escapeHtml(BOUND_NAME[bound]+": required by the profile, no passing test")+'">'+BOUND_SHORT[bound]+" "+(cases?"0/"+cases[3]:"0")+"</span>";
   });
   return'<td class="lv'+(levelUsed(key)?"":" void")+'">'+chips+"</td>";
 }
 if(key==="classes")return'<td class="tf-map-num">'+(c.classes.required?(c.classes.caught||0)+"/"+c.classes.required:'<span class="tf-map-muted">—</span>')+"</td>";
 if(key==="tests")return'<td class="tf-map-num">'+c.tests+"</td>";
 return'<td class="tf-depth-value">'+measureHtml(row,key)+"</td>";
}
// A group row sums every column: how the contracts that reach a level split over its boundaries, a measure's colours,
// the median share of mutants caught, and the fault classes detected and the own tests added up.
function groupCell(list,key){
 const cs=list.map(row=>C[row.id]);
 if(LEVELS.includes(key))return'<td class="lv'+(levelUsed(key)?"":" void")+'">'+(levelUsed(key)?mapSpread(list,row=>{const at=BOUNDS.filter(bound=>cellOf(C[row.id],key,bound)),bound=at[at.length-1];return bound?{key:bound,fill:cssVar(BOUND_VAR[bound]),rank:BOUNDS.indexOf(bound),label:BOUND_NAME[bound]}:null},true):"")+"</td>";
 if(key==="classes"){const required=cs.reduce((sum,c)=>sum+(c.classes.required||0),0),caught=cs.reduce((sum,c)=>sum+(c.classes.caught||0),0);return'<td class="tf-map-num">'+(required?caught+"/"+required:'<span class="tf-map-muted">—</span>')+"</td>"}
 if(key==="tests")return'<td class="tf-map-num">'+cs.reduce((sum,c)=>sum+c.tests,0)+"</td>";
 return'<td class="tf-depth-value">'+measureGroupHtml(list,key)+"</td>";
}
function groupKeys(row,group){
 const c=C[row.id];
 if(group==="level")return[c.deepest||"notests"];
 if(group==="boundary")return[c.real||"notests"];
 if(group==="producer")return c.producers.length?c.producers:["none"];
 return[detectBand(c)];
}
function groupName(group,key){
 if(group==="level")return LEVEL_NAME[key]||"No passing tests";
 if(group==="boundary")return key==="notests"?"No passing tests":BOUND_NAME[key];
 if(group==="producer")return key==="none"?"No substitute":(P[key]?.title||key)+" · "+String(P[key]?.level||"").toUpperCase();
 return DETECT_NAME[key];
}
function groupOrder(group,keys){
 const order={level:[...LEVELS,"notests"].reverse(),boundary:[...BOUNDS,"notests"].reverse(),producer:[...Object.keys(P).sort((a,b)=>P[b].tests-P[a].tests),"none"],detect:["high","mid","low","none"]}[group];
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
 keys:groupKeys,name:groupName,order:groupOrder,sortValue,
 csv:{head:["tests_per_cell","required_cases_per_cell","required_cases_covered","required_cases","deepest_level","most_realistic_boundary","model_validation","substitutes_and_recordings","mutants_caught","mutants_judged","share_caught","not_measured_reason","required_fault_classes","detected_fault_classes","own_passing_tests"],line:csvLine}
};

// What a measure says in one line, on its layer's card and in its row of the All layers table: the one number that
// matters most in it, counted in contracts and never a score, short enough for the card; the hint says it in full.
function measureLine(key){
 const all=leaves.map(row=>C[row.id]),count=test=>all.filter(test).length,total=all.length;
 const lines={
   overall:()=>{
     const states=all.map(profileStates),missing=states.filter(state=>state.includes("missing")).length,beyond=states.filter(state=>state.includes("beyond")).length;
     const also=beyond?"; "+beyond+" also have tests beyond it":"";
     return missing
       ?{short:"<b>"+missing+"</b> miss a cell",tip:missing+" of "+total+" contracts have no test in a cell their profile asks for"+also+"."}
       :{short:"all as asked",tip:"All "+total+" contracts have tests in every cell their profile asks for"+also+"."};
   },
   level:()=>{
     const reached=count(c=>c.deepest===topLevel),none=LEVELS.slice(LEVELS.indexOf(topLevel)+1).map(level=>LEVEL_NAME[level].toLowerCase());
     return{short:"<b>"+reached+"</b> at "+LEVEL_SHORT[topLevel].toLowerCase(),tip:reached+" of "+total+" contracts reach "+LEVEL_NAME[topLevel].toLowerCase()+", the deepest level any test reaches"+(none.length?"; none reach "+listed(none):"")+"."};
   },
   boundary:()=>{
     const at=bound=>count(c=>c.real===bound),untested=count(c=>!c.real);
     return{short:"<b>"+at("direct")+"</b> live · "+at("replay")+" replay",
       tip:at("direct")+" of "+total+" contracts have tests that talk to the live service; "+at("replay")+" use recordings, "+at("substitute")+" substitutes and "+at("none")+" stay local"+(untested?"; "+untested+" have no passing tests":"")+"."};
   },
   trust:()=>{
     const backed=count(c=>c.trust&&c.trust!=="na"),unchecked=count(c=>c.trust==="l0");
     if(!backed)return{short:"no substitutes",tip:"No contract's tests rest on a substitute or a recording."};
     return{short:"<b>"+unchecked+"</b>/"+backed+" unchecked",tip:unchecked+" of the "+backed+" contracts whose tests rest on substitutes or recordings use models not checked against the real service (L0); "+(backed-unchecked)+" are checked at L1 or above."};
   },
   detect:()=>{
     const measured=all.filter(c=>c.detect),full=measured.filter(c=>c.detect[0]===c.detect[1]).length,left=total-measured.length;
     if(!measured.length)return{short:"none measured",tip:"No contract has its mutants measured."};
     return{short:"<b>"+full+"</b>/"+measured.length+" catch all",tip:full+" of the "+measured.length+" measured contracts catch every planted bug"+(left?"; "+left+" are not measured":"")+"."};
   }
 };
 return lines[key]();
}
// A measure's row in the All layers table: its line, which folds away on narrow screens like the verdict word in a
// health row.
function layerRow(key){
 return{status:'<span class="tf-map-row-word">'+measureLine(key).short+"</span>",count:""};
}
// A measure on its layer's card: its line, and the sentence behind it for the hint and for what the card says aloud.
function layerCard(key){
 const line=measureLine(key);
 return{count:line.short,tip:line.tip};
}
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

// A number per contract to sort a measure by: deeper, more realistic, better checked, more caught is larger.
function measure(row,key){
 const c=C[row.id];
 if(!c)return-1;
 const level=c.deepest?LEVELS.indexOf(c.deepest):-1,bound=c.real?BOUNDS.indexOf(c.real):-1;
 return{overall:level*10+bound,level,boundary:bound,trust:["na","l0","l1","l2","l3","l4"].indexOf(c.trust)-1,detect:ratio(c)??-1}[key];
}
// The measures for the map. Find shows what Overall's depth says about each contract.
return{
 tree,insights:model.insights,words:key=>CHANGE_WORDS[key],
 href:hrefFor,says,describe,paint,legend:legendHtml,tone,blank,measure,measureHtml,measureGroupHtml,tableCell,groupCell,levels:LEVELS,
 facets:FACETS,panels:PANELS,markPanel:markCells,
 strip:{row:layerRow,cells:key=>key==="overall"?overallCells():undefined,card:layerCard},
 table:TABLE,
 tiles:{leaf:(row,key)=>'style="fill:'+FILL[key](C[row.id])+'"'},
 rings:RINGS,
 find:row=>({badge:()=>{const pill=says(row,"overall");return pill?'<span class="tf-map-pill">'+escapeHtml(pill.text)+"</span>":""}}),
 attach:page=>{map=page}
};
}"""

PAIRS_MAP_CSS = r"""/* Health beside its measures. A measure judges nothing, so its Changes are outlined
   without red or green; the card shows the other half of a pair beside the one in view. */
#verification-health-map.tf-pairs-measuring{--tf-map-up:var(--tf-map-ring);--tf-map-down:var(--tf-map-ring)}
/* A card shown in one of its measures: the view's name beside the mark of the verdict the card keeps, then the
   measure's line. A measure judges nothing, so its changes there carry no red or green either. */
.tf-map-tab.measure .tf-map-mark-only{opacity:.75}
.tf-pairs-view-name{min-width:0;overflow:hidden;text-overflow:ellipsis;font-weight:650}
.tf-map-tab.measure .tf-map-delta{--tf-map-up:var(--tf-map-ring);--tf-map-down:var(--tf-map-ring)}
.tf-pairs-other{display:flex;flex-wrap:wrap;gap:.1rem .6rem;margin-top:.45rem;padding-top:.4rem;border-top:1px solid var(--tf-map-line);color:var(--pst-color-text-muted)}
.tf-pairs-other b{font-weight:650;color:var(--pst-color-text-base)}
/* The contracts table: a measure's one value, and how a group's contracts split over its colours. */
.tf-pairs-cell{white-space:nowrap}
/* Every column of health and the measures: narrower name, bar and cause columns than either table alone would need. */
#verification-health-map .tf-map-list-table .name{max-width:16rem}
#verification-health-map .tf-depth-detbar{width:36px}
#verification-health-map .tf-health-why-cell{min-width:11rem}"""

PAIRS_MAP_JS = r"""// The Verification Health Map: every layer's health, and beside it what the layer measures. A layer is one question:
// its first view says whether the evidence is enough (health), its other views say how much of it there is (the
// measures).
function pairsMap(H,D){
 // The measures, and the depth layer each one shows; every other projection is health's.
 const MEASURE={depth:"overall",level:"level",boundary:"boundary",trust:"trust",detect:"detect"};
 const measured=projection=>projection in MEASURE;
 const side=projection=>measured(projection)?D:H;
 const own=projection=>MEASURE[projection]||projection;
 // Health and the measures hold the same tree; a mark from one tree reads its facts from the other by ID.
 const depthRow=row=>D.tree.rowById.get(row.id)||row,healthRow=row=>H.tree.rowById.get(row.id)||row;
 const as=(row,projection)=>measured(projection)?depthRow(row):healthRow(row);
 // Each layer's views: the verdict first, then its measures. Overall adds the contracts table. A view's question is what
 // its tab says, so a reader knows what a view answers before opening it.
 const VIEWS=[
  {key:"overall",layer:"overall",projection:"overall",form:"rings",ring:"overall",label:"Health",ask:"Where does each contract fail?"},
  {key:"overall/depth",layer:"overall",projection:"depth",form:"rings",ring:"depth",label:"Depth",ask:"How deep do its own tests go?"},
  {key:"table",layer:"overall",projection:"overall",form:"table",label:"Table",ask:"Health and measures per contract"},
  {key:"execution",layer:"execution",projection:"execution",form:"tiles",label:"Health",ask:"Did its tests and scenarios pass?"},
  {key:"coverage",layer:"coverage",projection:"coverage",form:"tiles",label:"Health",ask:"Is every required case tested?"},
  {key:"coverage/level",layer:"coverage",projection:"level",form:"tiles",label:"Test level",ask:"How far do its tests reach?"},
  {key:"coverage/boundary",layer:"coverage",projection:"boundary",form:"tiles",label:"Boundary",ask:"What do its tests talk to?"},
  {key:"faults",layer:"faults",projection:"faults",form:"tiles",label:"Health",ask:"Are its required faults caught?"},
  {key:"faults/detect",layer:"faults",projection:"detect",form:"tiles",label:"Mutants caught",ask:"How many planted bugs are caught?"},
  {key:"evidence",layer:"evidence",projection:"evidence",form:"tiles",label:"Health",ask:"Is its evidence sound and fresh?"},
  {key:"evidence/trust",layer:"evidence",projection:"trust",form:"tiles",label:"Model validation",ask:"How well are its substitutes checked?"},
  {key:"assurance",layer:"assurance",projection:"assurance",form:"tiles",label:"Health",ask:"Do goals and capabilities pass?"}
 ];
 // A measure is named by its view, a verdict by its layer: "Test level: System", "Coverage: PASS".
 const nameOf=projection=>measured(projection)?VIEWS.find(view=>view.projection===projection).label:H.layers.find(layer=>layer[0]===projection)[1];
 const measuresOf=layer=>VIEWS.filter(view=>view.layer===layer&&measured(view.projection)).map(view=>view.projection);
 const listed=items=>items.length<2?items.join(""):items.slice(0,-1).join(", ")+" and "+items[items.length-1];
 // A layer's card help names the measures it also shows.
 const layers=H.layers.map(([key,label,help])=>{const more=measuresOf(key).map(nameOf);return[key,label,help+(more.length?" Also shown as "+listed(more)+".":"")]});
 // Changes: verdicts from the health snapshots, measures from the depth snapshots, since the same earlier run.
 const healthDelta=H.insights?.delta||{},depthDelta=D.insights?.delta||{};
 const measureChanges=Object.fromEntries(Object.entries(depthDelta.layers||{}).map(([key,value])=>[key==="overall"?"depth":key,value]));
 const insights={run:H.insights?.run,delta:{baseline:healthDelta.baseline||depthDelta.baseline||null,layers:{...(healthDelta.layers||{}),...measureChanges}}};
 // The card of a verdict names its measures and the card of a measure names the verdict: the other half of the pair.
 const VERDICT_OF=Object.fromEntries(VIEWS.filter(view=>measured(view.projection)).map(view=>[view.projection,view.layer]));
 function pairLine(row,projection){
   const others=measured(projection)?[VERDICT_OF[projection]]:measuresOf(projection);
   const parts=others.map(other=>{const said=side(other).says(as(row,other),own(other));return said?"<span>"+escapeHtml(nameOf(other))+": <b>"+escapeHtml(said.text)+"</b></span>":""}).filter(Boolean);
   return parts.length?'<div class="tf-pairs-other">'+parts.join(" · ")+"</div>":"";
 }
 // A measure colours contracts only: goals, capabilities and the product carry no verdict there.
 function paint(entries,projection,animated){
   if(!measured(projection)){
     entries.forEach(entry=>{entry.shape.style.fill=""});
     H.paint(entries,projection,animated);
     return;
   }
   entries.forEach(entry=>{
     if(entry.kind==="leaf")return;
     entry.shape.classList.remove("tf-health-own-failed");
     entry.dot?.classList.remove("passed","failed");
     entry.dot?.classList.add("na");
   });
   document.getElementById("tf-map-tiles").classList.remove("tf-health-product-failed");
   D.paint(entries,own(projection));
 }
 // Health's filters and the measures' apply together: a verdict and a measure narrow the same contracts.
 const facets={};
 Object.entries(H.facets).forEach(([key,facet])=>{facets[key]={...facet,test:(row,value)=>facet.test(healthRow(row),value)}});
 Object.entries(D.facets).forEach(([key,facet])=>{facets[key]={...facet,test:(row,value)=>H.tree.isLeaf(row)&&facet.test(depthRow(row),value)}});
 const panels={...H.panels,depth:D.panels.overall,level:D.panels.level,boundary:D.panels.boundary,trust:D.panels.trust,detect:D.panels.detect,
   table:{...H.panels.overall,help:MAP_TABLE_HELP,facets:["deepest","real","detect"]}};
 // The contracts table is Overall's rings unrolled: a group of columns per layer in the strip's order, each layer's
 // views in their order on its card (its health, then its measures), with every column of both tables. Overall's
 // depth is the own evidence by test level and the own tests; Fault model adds the fault classes it detects.
 // Why it fails closes the row, and a group row sums every column.
 const DEPTH_COLUMNS=new Map(D.table.columns.map(column=>[column[0],column]));
 const depthColumn=(key,path)=>{const[,label,tip,cls]=DEPTH_COLUMNS.get(key);return[key,label,tip,cls,path]};
 const VIEW_ASK=Object.fromEntries(VIEWS.map(view=>[view.projection,view.ask]));
 const layerOf=key=>H.layers.find(layer=>layer[0]===key);
 function tableColumns(){
   const columns=[];
   H.strip.groups().flatMap(group=>group.keys).forEach(key=>{
     const[,label,help]=layerOf(key);
     columns.push([key,"Health",label+": "+help,"",[label]]);
     if(key==="overall")[...D.levels,"tests"].forEach(column=>columns.push(depthColumn(column,[label,"Depth"])));
     measuresOf(key).filter(projection=>projection!=="depth").forEach(projection=>columns.push([projection,nameOf(projection),nameOf(projection)+": "+VIEW_ASK[projection],"",[label]]));
     if(key==="faults")columns.push(depthColumn("classes",[label]));
   });
   return[...columns,H.table.columns.find(column=>column[0]==="why")];
 }
 const columns=tableColumns();
 const fromDepth=key=>DEPTH_COLUMNS.has(key);
 const groupLabel={verdict:"Overall health"};
 const DEPTH_GROUPS=new Set(D.table.groups.map(group=>group[0]));
 const TABLE={
   columns,
   groups:[...H.table.groups.map(([key,label])=>[key,groupLabel[key]||label]),...D.table.groups],
   keys:(row,group)=>DEPTH_GROUPS.has(group)?D.table.keys(depthRow(row),group):H.table.keys(row,group),
   name:(group,key)=>DEPTH_GROUPS.has(group)?D.table.name(group,key):H.table.name(group,key),
   order:(group,keys)=>DEPTH_GROUPS.has(group)?D.table.order(group,keys):H.table.order(group,keys),
   sortValue:(row,key)=>fromDepth(key)?D.table.sortValue(depthRow(row),key):measured(key)?D.measure(depthRow(row),own(key)):H.table.sortValue(row,key),
   stats:H.table.stats,
   cells:row=>columns.map(([key])=>fromDepth(key)?D.tableCell(depthRow(row),key):measured(key)?'<td class="tf-pairs-cell">'+D.measureHtml(depthRow(row),own(key))+"</td>":H.tableCell(row,key)).join(""),
   groupCells:list=>columns.map(([key])=>fromDepth(key)?D.groupCell(list.map(depthRow),key):measured(key)?'<td class="tf-pairs-cell">'+D.measureGroupHtml(list.map(depthRow),own(key))+"</td>":H.groupCell(list,key)).join(""),
   csv:{file:"verification-health.csv",head:[...H.table.csv.head,...D.table.csv.head],line:row=>[...H.table.csv.line(row),...D.table.csv.line(depthRow(row))]}
 };
 return{
   tree:H.tree,layers,views:VIEWS,insights,
   words:projection=>side(projection).words(own(projection)),
   href:(row,projection)=>side(projection).href(as(row,projection),own(projection)),
   says:(row,projection)=>side(projection).says(as(row,projection),own(projection)),
   describe:(row,projection,entry)=>{const part=side(projection).describe(as(row,projection),own(projection),entry);return{body:part.body,extra:pairLine(row,projection)+(part.extra||"")}},
   paint,legend:projection=>side(projection).legend(own(projection)),tone:(row,projection)=>side(projection).tone(as(row,projection),own(projection)),
   blank:(row,projection)=>side(projection).blank(as(row,projection),own(projection)),
   facets,panels,filterRows:H.filterRows,markPanel:D.markPanel,
   strip:{groups:H.strip.groups,card:H.strip.card,
     // A card shown in one of its measures says what that measure says: the view's name beside the mark of the verdict
     // the card keeps, and the measure's line. Its changes are the measure's.
     viewCard:(key,view)=>measured(view.projection)?{...D.strip.card(own(view.projection)),status:H.strip.mark(key)+'<span class="tf-pairs-view-name">'+escapeHtml(view.label)+"</span>",health:H.strip.card(key),changes:view.projection}:null,
     row:projection=>measured(projection)?D.strip.row(own(projection)):H.strip.row(projection),
     cells:projection=>measured(projection)?D.strip.cells(own(projection)):undefined},
   table:TABLE,
   tiles:{dots:true,leaf:(row,projection)=>side(projection).tiles.leaf(as(row,projection),own(projection)),mark:(row,projection)=>measured(projection)?"":H.tiles.mark(healthRow(row),projection)},
   ringSets:{overall:H.rings,depth:{...D.rings,label:"Overall depth: goals, capabilities and contracts inside, one ring per test level and the share of mutants caught outside"}},
   find:row=>{const verdict=H.find(row),depth=D.find(depthRow(row));return{rank:verdict.rank,badge:()=>verdict.badge()+depth.badge()}},
   // A measure judges nothing, so its Changes are outlined without red or green.
   selected:view=>document.getElementById("verification-health-map")?.classList.toggle("tf-pairs-measuring",measured(view.projection)),
   attach:page=>{H.attach(page);D.attach(page)}
 };
}"""

# A contract a measure does not reach is hatched.
DEPTH_HATCH = (
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>'
    '<pattern id="tf-depth-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    '<rect width="6" height="6" style="fill:var(--tf-dm-empty)"/><rect width="1.6" height="6" style="fill:var(--tf-dm-hatch)"/>'
    "</pattern></defs></svg>"
)


def health_map_article(model_json: str, d3_hierarchy: str) -> str:
    """The Verification Health Map: every layer's health first and, beside it, what the layer measures (how deep, how
    realistic and how strong its evidence is). One section holds the heading, the shared styles then the page's own,
    the markup (tools line, layer strip, frame with the views), d3-hierarchy and one script: the shared map, the facts
    (health and depth side by side), health, the measures and the pairing that runs them as one map."""
    legend = (
        '<span><i class="tf-map-sw failed"></i>Fail</span>'
        '<span><i class="tf-map-sw passed"></i>Pass</span>'
        '<span><i class="tf-map-sw na"></i>N/A</span>'
        '<span><i class="tf-map-sw own"></i>Own check fails</span>'
        '<span class="tf-map-help" data-tip="A layer\'s measures are the rows below it, each in its own colours.">?</span>'
    )
    markup = (
        DEPTH_HATCH
        + map_tools(
            "Where verification fails, layer by layer, and beside each layer's health how deep, how realistic and how "
            "strong its evidence is."
        )
        + map_strip("Health", legend)
        + map_frame(
            "Overall health: goals, capabilities and contracts inside, one ring per layer outside",
            "Verification health by goal, capability and contract",
        )
    )
    css = "\n".join((MAP_SHARED_CSS, HEALTH_MAP_CSS, DEPTH_MAP_CSS, PAIRS_MAP_CSS))
    script = "\n".join(
        (
            MAP_SHARED_JS,
            f"const model={model_json};",
            HEALTH_MAP_JS,
            DEPTH_MAP_JS,
            PAIRS_MAP_JS,
            "mapPage(pairsMap(healthMap(model.health),depthMap(model.depth))).start();",
        )
    )
    return (
        '<section id="verification-health-map">\n<h1>Verification Health Map'
        '<a class="headerlink" href="#verification-health-map" title="Link to this heading">#</a></h1>\n'
        f'<style id="tf-health-map-style">\n{css}\n</style>\n'
        f"{markup}\n<script>{d3_hierarchy}</script>\n"
        f"<script>\n(()=>{{\n{script}\n}})();\n</script>\n</section>"
    )


EXPLORER_CSS = r"""/* The explorer's own layout: the list beside the shared filters panel, then groups, blocks, objects and rows. The
   shared map styles give the tools line, the panel, chips, options, hints and Find; the health palette gives the marks. */
#verification-explorer .tf-ex-main{flex:1 1 auto;min-width:0}
#verification-explorer .tf-ex-bar{gap:.7rem}
#verification-explorer .tf-ex-search{flex:0 1 15rem;min-width:6rem;height:26px;padding:0 .55rem;border:1px solid var(--tf-map-line);border-radius:7px;background:var(--pst-color-background);color:var(--pst-color-text-base);font:inherit;font-size:.74rem}
#verification-explorer .tf-ex-search:hover{border-color:var(--tf-map-line-strong)}
#verification-explorer .tf-ex-search:focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:1px}
#verification-explorer .tf-map-summary b{font-weight:650}
#verification-explorer .tf-map-kinds{flex-wrap:wrap}
#verification-explorer .tf-map-kind{flex:1 1 calc(25% - 2px);padding-left:.4rem;padding-right:.4rem}
#verification-explorer .tf-map-sw.unknown{background:repeating-linear-gradient(45deg,var(--tf-hm-fail) 0 2px,transparent 2px 4px)}
#verification-explorer .tf-ex-define{margin:0 0 .6rem;padding:.5rem .75rem;border:1px solid var(--tf-map-line);border-radius:10px;background:var(--tf-map-goal);font-size:.78rem}
#verification-explorer .tf-ex-define[hidden]{display:none}
#verification-explorer :is(.tf-ex-define,.tf-ex-define-body) p{margin:.15rem 0 0;max-width:80ch}
#verification-explorer .tf-ex-define-body{padding:.4rem .75rem .5rem;border-bottom:1px solid var(--tf-map-line);font-size:.76rem;color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-define-body b,#verification-explorer .tf-ex-define p b{color:var(--pst-color-text-base);font-weight:650}
#verification-explorer .tf-ex-list{min-height:12rem}
#verification-explorer .tf-ex-group{margin:0 0 .9rem;border:1px solid var(--tf-map-line);border-radius:12px;background:var(--tf-map-goal);overflow:hidden}
#verification-explorer .tf-ex-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:.15rem .6rem;padding:.55rem .75rem .5rem;border-bottom:1px solid var(--tf-map-line)}
#verification-explorer .tf-ex-title{display:inline-flex;align-items:baseline;gap:.4rem;min-width:0;font-size:.88rem;font-weight:700;overflow-wrap:anywhere}
#verification-explorer .tf-ex-head code,#verification-explorer .tf-ex-object-head code,#verification-explorer .tf-ex-context code{padding:0 .3rem;border:0;border-radius:4px;background:var(--tf-map-feature);color:inherit;font-size:.68rem;overflow-wrap:anywhere}
#verification-explorer .tf-ex-path{flex:1 1 12rem;min-width:0;font-size:.72rem;color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-tally{font-size:.72rem;color:var(--pst-color-text-muted);font-variant-numeric:tabular-nums;white-space:nowrap}
#verification-explorer :is(.tf-ex-tally,.tf-map-summary) :is(.failed,.unknown){color:var(--tf-hm-fail-ink);font-weight:650}
#verification-explorer :is(.tf-ex-tally,.tf-map-summary) .passed{color:var(--tf-hm-pass-ink);font-weight:650}
#verification-explorer .tf-ex-open{font-size:.74rem;font-weight:600;white-space:nowrap}
#verification-explorer .tf-ex-block{padding:.45rem .75rem .55rem;background:var(--pst-color-background)}
#verification-explorer .tf-ex-block+.tf-ex-block{border-top:1px solid var(--tf-map-line)}
#verification-explorer .tf-ex-block-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:.1rem .5rem;margin:.1rem 0 .3rem;font-size:.62rem;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-block-head span{font-size:.72rem;font-weight:500;letter-spacing:0;text-transform:none}
#verification-explorer .tf-ex-object{margin:.3rem 0 .55rem}
#verification-explorer .tf-ex-object:last-child{margin-bottom:.1rem}
#verification-explorer .tf-ex-object-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:.1rem .6rem;font-size:.76rem}
#verification-explorer .tf-ex-object-head>span{color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-object-links{display:inline-flex;flex-wrap:wrap;gap:.1rem .55rem;margin-left:auto;font-size:.72rem}
#verification-explorer .tf-ex-object-what{margin:.1rem 0 .2rem;max-width:80ch;font-size:.76rem;color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-rows{margin:0;padding:0;list-style:none}
#verification-explorer .tf-ex-row{display:grid;grid-template-columns:1rem 7.5rem minmax(0,1fr) auto;align-items:baseline;gap:.05rem .5rem;padding:.28rem .4rem;border-radius:7px;font-size:.78rem}
#verification-explorer .tf-ex-row:hover{background:var(--tf-map-goal)}
#verification-explorer .tf-ex-mark{font-weight:800;text-align:center}
#verification-explorer .tf-ex-mark:is(.failed,.unknown),#verification-explorer .tf-ex-row:is(.failed,.unknown) .tf-ex-state{color:var(--tf-hm-fail-ink)}
#verification-explorer .tf-ex-mark.passed,#verification-explorer .tf-ex-row.passed .tf-ex-state{color:var(--tf-hm-pass-ink)}
#verification-explorer .tf-ex-mark.na,#verification-explorer .tf-ex-row.na .tf-ex-state{color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-row.na .tf-ex-name{font-weight:550}
#verification-explorer .tf-ex-state{font-size:.72rem;font-weight:650;line-height:1.3}
#verification-explorer .tf-ex-body{min-width:0}
#verification-explorer .tf-ex-line{display:block}
#verification-explorer .tf-ex-kind{margin-right:.35rem;font-size:.7rem;color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-name{font-weight:650;overflow-wrap:anywhere}
#verification-explorer .tf-ex-meta{margin-left:.55rem;font-size:.7rem;color:var(--pst-color-text-muted)}
#verification-explorer :is(.tf-ex-what,.tf-ex-why,.tf-ex-context){display:block;max-width:90ch;font-size:.74rem}
#verification-explorer .tf-ex-what{color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-context{margin-bottom:.05rem;font-size:.7rem;color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-context .tf-map-kind-icon{margin-right:.25rem}
#verification-explorer .tf-ex-note{color:var(--pst-color-text-base)}
#verification-explorer :is(.tf-ex-cause,.tf-ex-for){display:inline;margin:0 .35rem 0 0;padding:0 .4rem;border:1px solid var(--tf-map-line-strong);border-radius:999px;background:var(--pst-color-background);color:var(--pst-color-text-base);font:inherit;font-size:.7rem;font-weight:600;line-height:1.5;cursor:pointer}
#verification-explorer .tf-ex-cause{border-color:color-mix(in srgb,var(--tf-hm-fail) 55%,transparent)}
#verification-explorer .tf-ex-for{margin:0 .15rem 0 0;padding:0 .3rem;border-color:transparent;background:none;font-weight:600;color:inherit}
#verification-explorer :is(.tf-ex-cause,.tf-ex-for):hover{border-color:var(--tf-map-selected)}
#verification-explorer :is(.tf-ex-cause,.tf-ex-for):focus-visible{outline:2px solid var(--tf-map-ring);outline-offset:1px}
#verification-explorer .tf-ex-links{display:inline-flex;flex-wrap:wrap;justify-content:flex-end;gap:.1rem .55rem;font-size:.72rem;white-space:nowrap}
#verification-explorer .tf-ex-links a.raw{color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-nest{padding:0}
#verification-explorer .tf-ex-rows.nested{margin:.05rem 0 .25rem 1.5rem;padding-left:.5rem;border-left:1px solid var(--tf-map-line)}
#verification-explorer .tf-ex-rows.nested .tf-ex-row{padding-top:.18rem;padding-bottom:.18rem;font-size:.75rem}
#verification-explorer .tf-ex-change{font-size:.66rem;font-weight:800;cursor:help}
#verification-explorer .tf-ex-change.up{color:var(--tf-hm-fail-ink)}
#verification-explorer .tf-ex-change.down{color:var(--tf-hm-pass-ink)}
#verification-explorer .tf-ex-change.new{color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-badge{font-size:.72rem;font-weight:700;font-variant-numeric:tabular-nums}
#verification-explorer .tf-ex-badge.failed{color:var(--tf-hm-fail-ink)}
#verification-explorer .tf-ex-badge.passed{color:var(--tf-hm-pass-ink)}
#verification-explorer .tf-ex-empty{padding:1.4rem;border:1px dashed var(--tf-map-line-strong);border-radius:12px;text-align:center;font-size:.8rem;color:var(--pst-color-text-muted)}
#verification-explorer .tf-ex-more{margin:.3rem 0 1rem;font-size:.74rem;color:var(--pst-color-text-muted)}
@media(max-width:640px){
 #verification-explorer .tf-ex-bar{flex-wrap:wrap;height:auto}
 #verification-explorer .tf-ex-search{flex:1 1 100%}
 #verification-explorer .tf-map-kind{flex-basis:calc(50% - 2px)}
 #verification-explorer .tf-ex-row{grid-template-columns:1rem minmax(0,1fr)}
 #verification-explorer :is(.tf-ex-state,.tf-ex-body,.tf-ex-links){grid-column:2}
 #verification-explorer .tf-ex-links{justify-content:flex-start;white-space:normal}
 #verification-explorer .tf-ex-object-links{margin-left:0}
}"""

EXPLORER_JS = r"""// The Verification Explorer: every item behind the monitors, one row each. A monitor judges and counts; here each
// item says what it is, how it stands, why it fails and where its details are. The tools line, the filters panel,
// chips, hints, Find and the address are the map's own, so a list is narrowed, shared and read like the map.
function explorerPage(model){
 const $=id=>document.getElementById(id);
 const tree=mapTree(model.rows),{rowById}=tree;
 const items=model.items,objects=model.objects,CAUSES=model.causes,itemById=new Map(items.map(item=>[item.id,item]));
 // Each kind of item: its key, glyph, name on the kind switch, plural, singular and what it is in one sentence.
 const KINDS=[
  ["path","fa-route","Paths","Evidence paths","Evidence path","One way a criterion of a verification profile must be proven, such as one provider family. It passes when its own retained test passed and its evidence is sound."],
  ["unbound","fa-link-slash","Unbound","Tests outside the profiles","Test outside the profile","A test that verifies a contract outside every case its profile requires. It proves no case, but its failure fails the contract."],
  ["fault","fa-shield-halved","Faults","Fault classes","Fault class","A kind of defect a contract's tests must be able to catch, as its verification profile requires."],
  ["mutant","fa-bug","Mutants","Mutants","Mutant","A small change planted in a contract's own code. Its tests should fail on it and so catch it."],
  ["check","fa-diagram-project","Checks","Assurance checks","Assurance check","A goal's or capability's own integration or validation scenario: what its contracts cannot prove one by one."],
  ["support","fa-sitemap","Support","Support","Support","A contract, capability or goal this one rests on. It cannot pass while that fails."],
  ["producer","fa-industry","Producers","Evidence producers","Evidence producer","A tool that captures or judges evidence. Qualified means a control showed it does not turn a wrong result into a pass."]
 ];
 const KIND=Object.fromEntries(KINDS.map(([key,icon,short,many,one,what])=>[key,{icon,short,many,one,what}]));
 // How to fix what a cause says; what it means is the Health Map's own sentence.
 const FIX={
  uncovered:"Write a test for this case at the required level and boundary and bind it to the case with coverage_item.",
  scenario:"Make the required scenario pass, or write it if it does not exist yet.",
  unbound:"Name in the profile the case this test proves, or make the test pass.",
  unexpected:"Declare the path in the profile, or bind the test to a path the profile declares.",
  unchallenged:"Add a test that injects this fault for the contract (fault_item) and fails when the fault goes unnoticed.",
  shared:"Give the contract its own, narrower @impl scope, so that no other contract claims its code.",
  survivors:"Add or sharpen an assertion on what the mutant changes, so that a test fails on it; if no input can tell it apart, suppress it as equivalent with the reason.",
  notreached:"Add a test that runs this code through the contract's public path, or narrow the @impl scope to the code the contract owns.",
  unproven:"Find an input on which the original and the mutant differ and pin it in a test, or record the mutant as equivalent with the proof.",
  generate:"Generate the semantic mutants for this target (--generate-semantic-mutants). If the budget deferred them, wait for the plan's usage window to reset; if no model was available, sign in to a backend the Test Plan lists.",
  regenerate:"Generate the semantic mutants again for the current code and requirement (--generate-semantic-mutants); the run judges them with the cascade.",
  suppressed:"Review the suppression pragmas: a class whose every mutant is suppressed proves nothing; keep only the ones whose reason holds.",
  invalid:"Make the mutated code importable or narrow the scope: a mutant that breaks test collection cannot be judged.",
  nosite:"Check the profile's fault applicability; if the class still applies, mark the code where the fault can occur with @impl.",
  noimpl:"Mark the code that implements the contract with @impl.",
  notests:"Make the contract's own tests pass: faults are judged only with passing tests.",
  missed:"Strengthen the assertions so that the injected fault fails a test.",
  campaign:"Run the implementation fault campaign again.",
  blocked:"Find out why the campaign could not run for this contract, then run it again.",
  support:"Open the supporting item and fix what fails there.",
  pending:"Open the supporting item and decide what it still leaves open.",
  "metric:Representation":"Run the case against the kind of target the profile requires.",
  "metric:Provenance":"Retain the evidence again, so that its result, source and artifacts belong to one run.",
  "metric:Producers":"Qualify the evidence producers again.",
  "metric:Freshness":"Run the evidence again: its inputs changed after the retained run.",
  "metric:M&S":"Validate the model behind the evidence against its referent to the required level.",
  "metric:Integration":"Make the integration scenario pass.",
  "metric:Validation":"Make the validation scenario pass."
 };
 // What a link opens, in one sentence.
 const LINK_TIP={
  Spec:"The scenario in the Living Specification: what this behaviour is.",
  Evidence:"The test's evidence record: what it checked, how far it reached and what was real.",
  Allure:"This test's result in Allure: steps, attachments and timing.",
  Source:"The code at the commit of the retained run.",
  Profile:"The verification or assurance profile that asks for this.",
  "Test model":"The Test Plan model this criterion follows.",
  "Test plan":"What each fault class means, in the Test Plan's fault model.",
  Opens:"The monitor of the item this one rests on.",
  "Evidence trust":"What the tool is for, what it risks and how it is qualified.",
  Qualification:"The retained qualification record, as raw JSON.",
  Items:"The items of the item this one rests on, here."
 };
 const STATUS={fail:{mark:"✕",word:"Fail",cls:"failed"},unknown:{mark:"?",word:"Unknown",cls:"unknown"},pass:{mark:"✓",word:"Pass",cls:"passed"},na:{mark:"–",word:"N/A",cls:"na"}};
 const STATUS_ORDER=["fail","unknown","pass","na"];
 const LAYERS=MAP_HEALTH_LAYERS.filter(([key])=>key!=="overall");
 const LAYER=Object.fromEntries(LAYERS.map(([key,label,ask])=>[key,{label,ask}]));
 const LEVEL=Object.fromEntries(model.levels),BOUND=Object.fromEntries(model.boundaries);
 const REPRESENTATION={synthetic_abstract:"Synthetic",surrogate_simulated:"Surrogate",representative:"Representative",actual:"Actual"};
 const OWNERS=[["requirement","Requirements"],["treq","Technical requirements"],["feature","Capabilities"],["goal","Goals"],["product","Product / System"]];
 const GROUPS=["Implementation","Runtime / dependency","Interface / protocol","Architecture","Specification / model"];
 // The engine's operators, most productive first, and what each one changes.
 const OPERATORS=[["comparison","Comparison"],["boolean","Boolean"],["condition","Condition operand removed"],["arithmetic","Arithmetic"],["statement","Statement removed"],["argument","Argument removed"],["return","Return value"],["negation","Condition negated"],["conversion","Conversion removed"],["container","Container element removed"],["boundary","Boundary"],["method","Method call removed"],["attribute","Other attribute read"],["conditional","Condition replaced"],["body","Body replaced"],["semantic","Semantic"]];
 const OPERATOR_TIP={
  comparison:"Swaps a comparison operator, such as < for <=.",
  boolean:"Swaps and for or, drops a not, or flips True and False.",
  statement:"Removes a statement with an effect: a call, a write, a raise.",
  return:"Replaces a returned value with None or its negation.",
  boundary:"Shifts a compared constant by one.",
  body:"Replaces a whole function body with a default of its return type.",
  arithmetic:"Swaps an arithmetic operator, such as + for -.",
  condition:"Removes one operand of an and or an or.",
  argument:"Removes an optional keyword argument of a call.",
  negation:"Negates a condition that is a plain value.",
  conversion:"Removes a built-in conversion such as int() around a value.",
  container:"Removes an element of a list, tuple, set or dict literal.",
  method:"Leaves out a method call whose value the code uses.",
  attribute:"Reads another attribute the same code reads on the same object.",
  conditional:"Replaces a condition with True or False.",
  semantic:"A realistic defect proposed for the risk the profile names."
 };
 const GROUP_BY=[
  ["owner","Contract","One group per contract, capability or goal in the order of the tree; the evidence producers last."],
  ["cause","Cause","One group per reason for failing, most items first, with what it means and how to fix it."],
  ["kind","Kind","One group per kind of item, with what that kind is."]
 ];
 const ownerOf=item=>rowById.get(item.owner);
 const goalOf=id=>id?tree.goalOf.get(id)||"":"";
 const capabilityOf=id=>{const row=rowById.get(id);if(!row)return"";if(row.level==="feature")return row.id;return tree.ancestors(row).find(up=>up.level==="feature")?.id||""};
 // A producer belongs to no contract, but For keeps it with every item whose evidence it made; the goal and capability
 // filters follow the item's own owner only, or the producers every goal shares would count in each of them.
 const holders=item=>item.owner?[item.owner]:item.attrs?.users||[];
 const searchText=item=>item.search??=[item.name,item.what,item.note,item.state,item.owner,ownerOf(item)?.label,objects[item.object]?.name,...item.causes.map(cause=>CAUSES[cause]?.label)].filter(Boolean).join(" ").toLowerCase();
 // What changed since the previous retained run: up fails now, down passes now, new was not there. Each run keeps one
 // snapshot of its items, so drawing the same run again never moves the baseline.
 const delta=model.delta||{},changes=(delta.layers||{}).items||{up:[],down:[],new:[],gone:0};
 const CHANGED={up:new Set(changes.up),down:new Set(changes.down),new:new Set(changes.new)};
 const changeOf=item=>CHANGED.up.has(item.id)?"up":CHANGED.down.has(item.id)?"down":CHANGED.new.has(item.id)?"new":"";
 const since=delta.baseline?"the run of "+mapRunLabel(delta.baseline.started_at):"";
 const CHANGE_WORDS={up:["▲","Fails now","It did not fail in "],down:["▼","Passes now","It failed in "],new:["+","New","It was not there in "]};
 const causeCount=id=>items.filter(item=>item.causes.includes(id)).length;
 const causeIds=[...new Set(items.flatMap(item=>item.causes))].sort((a,b)=>causeCount(b)-causeCount(a));
 const facets={
  kind:{label:"Kind",switch:true,options:KINDS.map(([key,,,many])=>[key,many]),test:(item,value)=>item.kind===value},
  status:{label:"Status",options:STATUS_ORDER.map(key=>[key,STATUS[key].word]),test:(item,value)=>item.status===value,swatch:value=>mapSwatch(STATUS[value].cls)},
  cause:{label:"Why it fails",options:causeIds.map(id=>[id,CAUSES[id]?.label||id]),test:(item,value)=>item.causes.includes(value),tip:value=>CAUSES[value]?.hint||""},
  layer:{label:"Layer",options:LAYERS.map(([key,label])=>[key,label]),test:(item,value)=>item.layers.includes(value),tip:value=>LAYER[value].ask},
  owner:{label:"Belongs to",options:OWNERS,test:(item,value)=>ownerOf(item)?.level===value},
  goal:{label:"Goal",options:tree.goals.map(row=>[row.id,row.short||row.label]),test:(item,value)=>goalOf(item.owner)===value},
  capability:{label:"Capability",options:tree.rows.filter(row=>row.level==="feature").map(row=>[row.id,row.short||row.label]),test:(item,value)=>capabilityOf(item.owner)===value},
  contract:{label:"For",options:tree.rows.map(row=>[row.id,row.short||row.label]),test:(item,value)=>holders(item).includes(value)},
  level:{label:"Test level",options:model.levels,test:(item,value)=>item.attrs?.level===value},
  boundary:{label:"Boundary",options:model.boundaries,test:(item,value)=>item.attrs?.boundary===value},
  group:{label:"Fault group",options:GROUPS.map(group=>[group,group]),test:(item,value)=>item.attrs?.group===value},
  klass:{label:"Fault class",options:[...new Set(items.filter(item=>item.kind==="mutant").map(item=>item.attrs?.class))].filter(Boolean).sort().map(value=>[value,value]),test:(item,value)=>item.attrs?.class===value},
  operator:{label:"Operator",options:OPERATORS.filter(([key])=>items.some(item=>item.attrs?.operator===key)),test:(item,value)=>item.attrs?.operator===value,tip:value=>OPERATOR_TIP[value]||""},
  origin:{label:"Origin",options:[["rule","Rule operator"],["semantic","Semantic mutant"]],test:(item,value)=>item.attrs?.origin===value,
   tip:value=>value==="rule"?"Planted by a rule operator of the engine.":"Proposed by a generator for a risk the profile names, frozen as a patch and filtered by the cascade."},
  diff:{label:"In this change",options:[["yes","Changed lines"]],test:(item,value)=>item.attrs?.diff===value,
   help:model.change_base?.merge_base?"Mutants on lines this branch changes against "+model.change_base.base+".":"No merge base with main, so no change to compare."},
  change:{label:"Since the previous run",options:[["any","Any change"],["up","Fails now"],["down","Passes now"],["new","New"]],keepEmpty:()=>true,test:(item,value)=>value==="any"?changeOf(item)!=="":changeOf(item)===value,
   help:delta.baseline?"Compared with "+since+".":"No earlier retained run to compare with yet: changes show here after the next retained run."},
  q:{label:"Text",switch:true,name:value=>"“"+value+"”",valid:value=>value.length>0,test:(item,value)=>searchText(item).includes(value.toLowerCase())}
 };
 // The panel shows the filters that fit the kind on the switch.
 const PANEL_FACETS={
  "":["status","cause","change","layer","owner","goal","capability","level","boundary","group"],
  path:["status","cause","change","layer","owner","goal","capability","level","boundary"],
  unbound:["status","cause","change","owner","goal","capability"],
  fault:["status","cause","change","owner","goal","capability","group"],
  mutant:["status","cause","change","diff","origin","klass","operator","owner","goal","capability"],
  check:["status","cause","change","owner","goal","capability","level","boundary"],
  support:["status","change","owner","goal","capability"],
  producer:["status","cause","change","goal","capability"]
 };
 const hint=mapHint($("tf-map-hint"));
 const listBox=$("tf-ex-list"),groupBox=$("tf-ex-group-by"),search=$("tf-ex-search"),kindBox=$("tf-map-kinds");
 let groupBy="owner",filters=null;
 const chosen=key=>{const set=filters.sets[key];return set.size===1?[...set][0]:""};
 filters=mapFilters({
  facets,rows:items,leaves:items,noun:"items",
  view:()=>"items",
  panel:()=>({title:"Filters",help:"Point at an option to see what it keeps; a click keeps only those items. Options of one filter add up, filters narrow each other.",before:()=>"",facets:PANEL_FACETS[chosen("kind")]||PANEL_FACETS[""]}),
  previews:()=>false,previewed:()=>{},
  hideTip:()=>hint.hide(),
  rendered:()=>renderKinds(),
  changed:()=>{syncSearch();render();writeHash()}
 });
 // The kind switch at the top of the panel: each kind with its glyph and how many items it holds under the other
 // filters. It is drawn once; a filter changes only its numbers and which kind is chosen.
 kindBox.innerHTML=[["","fa-list-check","All","Every item of every kind."],...KINDS.map(([key,icon,short,,,what])=>[key,icon,short,what])]
  .map(([value,icon,name,tip])=>'<button type="button" class="tf-map-kind" data-facet="kind" data-value="'+value+'" aria-pressed="false" data-tip="'+escapeHtml(tip)+'">'
   +'<span class="tf-map-kind-name"><i class="fa-solid '+icon+'" aria-hidden="true"></i>'+name+"</span><b></b></button>").join("");
 const kindButtons=[...kindBox.querySelectorAll("[data-facet]")];
 function renderKinds(){
  const kind=chosen("kind"),others=items.filter(item=>filters.matches(item,"kind"));
  kindButtons.forEach(button=>{
   const value=button.dataset.value,found=value?others.filter(item=>item.kind===value).length:others.length,pressed=value===kind;
   button.setAttribute("aria-pressed",String(pressed));
   button.disabled=!found&&!pressed;
   button.querySelector("b").textContent=found;
  });
 }
 groupBox.innerHTML=GROUP_BY.map(([key,label,tip])=>'<button type="button" data-group="'+key+'" aria-pressed="'+(key===groupBy)+'" data-tip="'+escapeHtml(tip)+'">'+label+"</button>").join("");
 function setGroup(key){
  groupBy=GROUP_BY.some(([value])=>value===key)?key:"owner";
  groupBox.querySelectorAll("[data-group]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.group===groupBy)));
 }
 groupBox.addEventListener("click",event=>{const button=event.target.closest("[data-group]");if(button){setGroup(button.dataset.group);render();writeHash()}});
 // Text narrows like any filter and shows as a chip; commas would split it in the address, so they become spaces.
 const typed=()=>search.value.replace(/,/g," ").trim();
 function syncSearch(){const value=[...filters.sets.q][0]||"";if(typed()!==value)search.value=value}
 let searchTimer=0;
 search.addEventListener("input",()=>{
  clearTimeout(searchTimer);
  searchTimer=setTimeout(()=>{
   const value=typed(),set=filters.sets.q;
   if(value===([...set][0]||""))return;
   set.clear();
   if(value)set.add(value);
   filters.render();filters.renderPanel(false);render();writeHash();
  },160);
 });
 const tally=list=>{
  const counts={};
  list.forEach(item=>{counts[item.status]=(counts[item.status]||0)+1});
  return STATUS_ORDER.filter(key=>counts[key]).map(key=>'<span class="'+STATUS[key].cls+'">'+counts[key]+" "+STATUS[key].word.toLowerCase()+"</span>").join(" · ");
 };
 const cellName=(level,bound)=>level?(LEVEL[level]||level)+(bound?" × "+(BOUND[bound]||bound):""):"";
 function metaOf(item,context){
  const a=item.attrs||{},parts=[];
  // Under its criterion a path does not repeat the criterion's cell.
  const cell=cellName(a.level,a.boundary);
  if(cell&&(context||item.kind!=="path"))parts.push(cell);
  if(a.representation)parts.push(REPRESENTATION[a.representation]||a.representation);
  if(a.ms&&a.representation==="surrogate_simulated")parts.push("M&S "+String(a.ms).toUpperCase());
  // Current evidence is the norm and stays silent.
  if(a.freshness&&a.freshness!=="CURRENT")parts.push(String(a.freshness));
  if(a.operator)parts.push(a.operator);
  if(item.kind==="producer"){
   const users=(a.users||[]).map(id=>rowById.get(id)).filter(Boolean),contracts=users.filter(row=>row.level==="requirement"||row.level==="treq").length;
   parts.push("evidence for "+plural(contracts,"contract","contracts")+(users.length>contracts?" and "+plural(users.length-contracts,"goal or capability","goals or capabilities"):""));
  }
  return parts.join(" · ");
 }
 const linkHtml=([label,href,kind])=>'<a class="'+kind+'" href="'+escapeHtml(href)+'" data-tip="'+escapeHtml(LINK_TIP[label]||"")+'">'+escapeHtml(label)+(kind==="explorer"?" ›":" ↗")+"</a>";
 function linksHtml(item){
  const links=item.links.filter(link=>link[1]);
  if(item.kind==="support"&&item.attrs?.child)links.push(["Items","#contract="+encodeURIComponent(item.attrs.child),"explorer"]);
  return links.map(linkHtml).join("");
 }
 function contextHtml(item){
  const row=ownerOf(item),object=objects[item.object]||itemById.get(item.object);
  if(!row)return'<span class="tf-ex-context">'+escapeHtml(KIND.producer.many)+"</span>";
  return'<span class="tf-ex-context">'+mapKindIcon(row.level)+'<button type="button" class="tf-ex-for" data-for="'+escapeHtml(row.id)+'" data-tip="Show only the items of '+escapeHtml(row.short||row.label)+'.">'+escapeHtml(row.short||row.label)+"</button><code>"+escapeHtml(row.id)+"</code>"+(object?" › "+escapeHtml(object.name):"")+"</span>";
 }
 function changeMark(item){
  const change=changeOf(item);
  if(!change)return"";
  const [mark,word,before]=CHANGE_WORDS[change];
  // A row that failed and now counts for nothing (suppressed by a verdict or a pragma, invalid) does not pass.
  const said=change==="down"&&item.status==="na"?"No longer counts":word;
  return' <span class="tf-ex-change '+change+'" data-tip="'+escapeHtml(said+". "+before+since+".")+'" aria-label="'+escapeHtml(said)+'">'+mark+"</span>";
 }
 function rowHtml(item,context,shownCause){
  const status=STATUS[item.status]||STATUS.unknown,kind=KIND[item.kind],meta=metaOf(item,context);
  const causes=item.causes.filter(cause=>cause!==shownCause).map(cause=>'<button type="button" class="tf-ex-cause" data-cause="'+escapeHtml(cause)+'" data-tip="'+escapeHtml((CAUSES[cause]?.hint||"")+" A click shows every item with this cause.")+'">'+escapeHtml(CAUSES[cause]?.label||cause)+"</button>").join("");
  return'<li class="tf-ex-row '+status.cls+'" data-id="'+escapeHtml(item.id)+'">'
   +'<span class="tf-ex-mark '+status.cls+'" aria-label="'+status.word+'">'+status.mark+"</span>"
   +'<span class="tf-ex-state">'+escapeHtml(item.state)+changeMark(item)+"</span>"
   +'<span class="tf-ex-body">'+(context?contextHtml(item):"")
   +'<span class="tf-ex-line">'+(context?'<i class="fa-solid '+kind.icon+' tf-ex-kind" aria-hidden="true"></i>':"")+'<span class="tf-ex-name">'+escapeHtml(item.name)+"</span>"+(meta?'<span class="tf-ex-meta">'+escapeHtml(meta)+"</span>":"")+"</span>"
   +(item.what?'<span class="tf-ex-what">'+escapeHtml(item.what)+"</span>":"")
   +(causes||item.note?'<span class="tf-ex-why">'+causes+(item.note?'<span class="tf-ex-note">'+escapeHtml(item.note)+"</span>":"")+"</span>":"")
   +"</span>"
   +'<span class="tf-ex-links">'+linksHtml(item)+"</span></li>";
 }
 const byObject=list=>{const groups=new Map();list.forEach(item=>{if(!groups.has(item.object))groups.set(item.object,[]);groups.get(item.object).push(item)});return[...groups.entries()]};
 const ranked=list=>list.map((item,index)=>[item,index]).sort((a,b)=>STATUS_ORDER.indexOf(a[0].status)-STATUS_ORDER.indexOf(b[0].status)||a[1]-b[1]).map(([item])=>item);
 const rows=(list,context,shownCause)=>'<ul class="tf-ex-rows">'+list.map(item=>rowHtml(item,context,shownCause)).join("")+"</ul>";
 // An object is what a few rows share: a criterion and its paths, a fault group and its classes, a section of checks.
 function objectHtml(objectId,list,inner){
  const object=objects[objectId]||{},links=(object.links||[]).map(([label,href,kind])=>linkHtml([label,href,kind||"semantic"])).join("");
  let head;
  if(object.kind==="criterion"){
   const all=items.filter(item=>item.object===objectId),passing=all.filter(item=>item.status==="pass").length;
   head="<code>"+escapeHtml(object.name)+"</code><span>"+escapeHtml(cellName(object.level,object.boundary))+'</span><span class="tf-ex-tally">'+passing+" of "+plural(all.length,"path","paths")+" pass</span>";
  }else head="<b>"+escapeHtml(object.name||"")+"</b>";
  return'<div class="tf-ex-object"><div class="tf-ex-object-head">'+head+(links?'<span class="tf-ex-object-links">'+links+"</span>":"")+"</div>"
   +(object.what?'<p class="tf-ex-object-what">'+escapeHtml(object.what)+"</p>":"")+(inner??rows(list))+"</div>";
 }
 // Mutants sit under their fault class; the ones whose class the filters leave out show under its name.
 function faultsHtml(list){
  const classes=list.filter(item=>item.kind==="fault"),mutants=ranked(list.filter(item=>item.kind==="mutant"));
  const shown=new Set(classes.map(item=>item.id));
  // A mutant under its class does not repeat the cause its class already names.
  const nested=parent=>{const inside=mutants.filter(item=>item.object===parent.id);return inside.length?'<li class="tf-ex-nest"><ul class="tf-ex-rows nested">'+inside.map(item=>rowHtml(item,false,parent.causes[0])).join("")+"</ul></li>":""};
  let html=byObject(classes).map(([objectId,group])=>objectHtml(objectId,group,'<ul class="tf-ex-rows">'+group.map(item=>rowHtml(item)+nested(item)).join("")+"</ul>")).join("");
  byObject(mutants.filter(item=>!shown.has(item.object))).forEach(([classId,group])=>{
   const parent=items.find(item=>item.id===classId);
   html+='<div class="tf-ex-object"><div class="tf-ex-object-head"><code>'+escapeHtml(parent?.name||"")+"</code><span>"+escapeHtml(parent?.what||"")+"</span></div>"+rows(group)+"</div>";
  });
  return html;
 }
 const BLOCKS=[
  ["coverage","Coverage",["path","unbound"]],
  ["faults","Fault model",["fault","mutant"]],
  ["assurance","Assurance",["check"]],
  ["support","Support",["support"]]
 ];
 const blockAsk={coverage:LAYER.coverage.ask,faults:LAYER.faults.ask,assurance:LAYER.assurance.ask,support:"What does it rest on, and does that pass?"};
 function blocksHtml(list){
  return BLOCKS.map(([key,label,kinds])=>{
   const inside=list.filter(item=>kinds.includes(item.kind));
   if(!inside.length)return"";
   let body;
   if(key==="coverage"){
    const unbound=inside.filter(item=>item.kind==="unbound");
    body=byObject(inside.filter(item=>item.kind==="path")).map(([objectId,group])=>objectHtml(objectId,group)).join("")
     +(unbound.length?'<div class="tf-ex-object"><div class="tf-ex-object-head"><b>'+escapeHtml(KIND.unbound.many)+'</b></div><p class="tf-ex-object-what">'+escapeHtml(KIND.unbound.what)+"</p>"+rows(unbound)+"</div>":"");
   }else if(key==="faults")body=faultsHtml(inside);
   else if(key==="assurance")body=byObject(inside).map(([objectId,group])=>objectHtml(objectId,group)).join("");
   else body=rows(inside);
   return'<div class="tf-ex-block"><h3 class="tf-ex-block-head">'+label+"<span>"+escapeHtml(blockAsk[key])+"</span></h3>"+body+"</div>";
  }).join("");
 }
 function ownerGroups(list){
  const groups=new Map();
  list.forEach(item=>{const key=item.owner||"";if(!groups.has(key))groups.set(key,[]);groups.get(key).push(item)});
  const order=[...tree.rows.filter(row=>row.level!=="product"),tree.root].map(row=>row.id).filter(id=>groups.has(id));
  if(groups.has(""))order.push("");
  return order.map(id=>{
   const row=rowById.get(id),group=groups.get(id);
   if(!row)return'<section class="tf-ex-group"><header class="tf-ex-head"><span class="tf-ex-title"><i class="fa-solid '+KIND.producer.icon+' tf-map-kind-icon" aria-hidden="true"></i>'+escapeHtml(KIND.producer.many)+'</span><span class="tf-ex-path">'+escapeHtml(KIND.producer.what)+'</span><span class="tf-ex-tally">'+tally(group)+'</span></header><div class="tf-ex-block">'+rows(group)+"</div></section>";
   const path=tree.ancestors(row).map(up=>up.short||up.label).join(" › ");
   return'<section class="tf-ex-group" data-owner="'+escapeHtml(id)+'"><header class="tf-ex-head"><span class="tf-ex-title">'+mapKindIcon(row.level)+escapeHtml(row.label)+"</span><code>"+escapeHtml(row.id)+"</code>"
    +'<span class="tf-ex-path">'+escapeHtml(path)+'</span><span class="tf-ex-tally">'+tally(group)+'</span><a class="tf-ex-open" href="'+escapeHtml(row.href)+'" data-tip="Its monitor: the verdict and the counts these items add up to.">'+escapeHtml(mapOpens(row,row.href))+" ↗</a></header>"
    +blocksHtml(group)+"</section>";
  }).join("");
 }
 const causeDefinition=id=>"<p><b>What it means.</b> "+escapeHtml(CAUSES[id]?.hint||"")+"</p>"+(FIX[id]?"<p><b>How to fix.</b> "+escapeHtml(FIX[id])+"</p>":"");
 function causeGroups(list){
  const judged=list.filter(item=>item.causes.length),rest=list.length-judged.length;
  const ids=[...new Set(judged.flatMap(item=>item.causes))];
  const counts=Object.fromEntries(ids.map(id=>[id,judged.filter(item=>item.causes.includes(id)).length]));
  ids.sort((a,b)=>counts[b]-counts[a]);
  return ids.map(id=>'<section class="tf-ex-group"><header class="tf-ex-head"><span class="tf-ex-title">'+escapeHtml(CAUSES[id]?.label||id)+'</span><span class="tf-ex-tally">'+plural(counts[id],"item","items")+"</span></header>"
   +'<div class="tf-ex-define-body">'+causeDefinition(id)+'</div><div class="tf-ex-block">'+rows(ranked(judged.filter(item=>item.causes.includes(id))),true,id)+"</div></section>").join("")
   +(rest?'<p class="tf-ex-more">'+plural(rest,"item passes","items pass")+" or "+(rest===1?"is":"are")+" not judged, so "+(rest===1?"it has":"they have")+" no cause. Group by contract or kind to see "+(rest===1?"it":"them")+".</p>":"");
 }
 function kindGroups(list){
  return KINDS.map(([key])=>{
   const group=list.filter(item=>item.kind===key),kind=KIND[key];
   if(!group.length)return"";
   return'<section class="tf-ex-group"><header class="tf-ex-head"><span class="tf-ex-title"><i class="fa-solid '+kind.icon+' tf-map-kind-icon" aria-hidden="true"></i>'+escapeHtml(kind.many)+'</span><span class="tf-ex-tally">'+tally(group)+"</span></header>"
    +'<div class="tf-ex-define-body"><p>'+escapeHtml(kind.what)+'</p></div><div class="tf-ex-block">'+rows(ranked(group),true)+"</div></section>";
  }).join("");
 }
 // Grouped by contract, a chosen cause or kind says first what it is: the cause and kind groups already say so.
 function definition(){
  if(filters.sets.change.size&&delta.baseline)return"<b>Since "+escapeHtml(since)+"</b><p>"+[[changes.up.length,"fails now","fail now"],[changes.down.length,"passes now","pass now"],[changes.new.length,"is new","are new"]].map(([count,one,many])=>plural(count,"item","items")+" "+(count===1?one:many)).join(" · ")+(changes.gone?" · "+plural(changes.gone,"item","items")+" of that run "+(changes.gone===1?"is":"are")+" gone":"")+".</p>";
  if(groupBy!=="owner")return"";
  const cause=chosen("cause"),kind=chosen("kind");
  if(cause)return"<b>"+escapeHtml(CAUSES[cause]?.label||cause)+"</b>"+causeDefinition(cause);
  if(kind)return"<b>"+escapeHtml(KIND[kind].many)+"</b><p>"+escapeHtml(KIND[kind].what)+"</p>";
  return"";
 }
 function render(){
  const shown=filters.shown(false),list=shown?items.filter(item=>shown.has(item.id)):items;
  $("tf-ex-summary").innerHTML=tally(list);
  const define=definition(),box=$("tf-ex-define");
  box.hidden=!define;
  box.innerHTML=define;
  syncChanges();
  listBox.innerHTML=!list.length
   ?(filters.sets.change.size
    ?'<div class="tf-ex-empty">'+(delta.baseline?"Nothing here changed since "+escapeHtml(since)+".":"No earlier retained run to compare with yet: what changes shows here after the next retained run.")
     +' <button type="button" class="tf-map-clear" data-ex-unchange>Show all these items</button></div>'
    :'<div class="tf-ex-empty">No items match these filters. <button type="button" class="tf-map-clear" data-ex-clear>Clear all</button></div>')
   :groupBy==="cause"?causeGroups(list):groupBy==="kind"?kindGroups(list):ownerGroups(list);
 }
 // The list has an address: its filters and, when not by contract, its grouping. A monitor opens it with the contract.
 function writeHash(){
  const params=new URLSearchParams();
  filters.write(params);
  if(groupBy!=="owner")params.set("group",groupBy);
  const query=params.toString();
  if(location.hash.slice(1)!==query)history.replaceState(history.state,"",query?"#"+query:location.pathname+location.search);
 }
 function readHash(){
  const params=new URLSearchParams(location.hash.slice(1));
  setGroup(params.get("group")||"owner");
  filters.read(params);
  syncSearch();
  render();
 }
 listBox.addEventListener("click",event=>{
  const cause=event.target.closest("[data-cause]");
  if(cause){filters.only("cause",cause.dataset.cause);return}
  const holder=event.target.closest("[data-for]");
  if(holder){filters.only("contract",holder.dataset.for);return}
  if(event.target.closest("[data-ex-clear]"))filters.clear();
  if(event.target.closest("[data-ex-unchange]")){filters.sets.change.clear();filters.render();filters.renderPanel(false);render();writeHash()}
 });
 // Changes keeps only what changed since the previous retained run: the same button as on the map, which outlines them.
 const changesButton=$("tf-map-changes");
 if(delta.baseline)changesButton.dataset.tip="Keep only what changed since "+since+".";
 else{changesButton.setAttribute("aria-disabled","true");changesButton.dataset.tip="No earlier retained run to compare with yet."}
 changesButton.addEventListener("click",()=>{
  if(!delta.baseline)return;
  const set=filters.sets.change,on=set.size>0;
  set.clear();
  if(!on)set.add("any");
  filters.render();filters.renderPanel(false);render();writeHash();
 });
 function syncChanges(){changesButton.setAttribute("aria-pressed",String(filters.sets.change.size>0))}
 // Find picks a goal, capability or contract and keeps its items, most failing first.
 const find=mapFind({
  hint,
  items:()=>tree.rows.filter(row=>row.level!=="product").map(row=>{
   const fails=items.filter(item=>item.owner===row.id&&(item.status==="fail"||item.status==="unknown")).length;
   return{row,path:tree.ancestors(row).map(up=>up.short||up.label).join(" › "),kind:MAP_KIND[row.level],rank:-fails,
    badge:()=>fails?'<span class="tf-ex-badge failed">✕ '+fails+"</span>":'<span class="tf-ex-badge passed">✓</span>'};
  }),
  pick:id=>{
   const row=rowById.get(id);
   if(!row)return;
   ["goal","capability","contract"].forEach(key=>filters.sets[key].clear());
   filters.sets[row.level==="goal"?"goal":row.level==="feature"?"capability":"contract"].add(id);
   filters.render();filters.renderPanel(false);render();writeHash();
  }
 });
 const page={filters,find,render};
 page.start=()=>{
  $("tf-map-stamp").innerHTML=mapStamp(model.run);
  ["tf-map-tools","tf-map-panel","tf-ex-main"].forEach(id=>hint.watch($(id)));
  mapCopy($("tf-map-copy"),writeHash);
  window.addEventListener("hashchange",readHash);
  // Keys: / finds, F opens the filters, Esc closes a hint.
  document.addEventListener("keydown",event=>{
   if(event.key==="Escape"){hint.hide();return}
   if(event.defaultPrevented||event.metaKey||event.ctrlKey||event.altKey||find.isOpen())return;
   if(event.target.closest?.("input,textarea,select,[contenteditable]"))return;
   if(event.key==="/"){event.preventDefault();find.open();return}
   if(event.key==="f"||event.key==="F"){event.preventDefault();filters.setPanel(!filters.open,true)}
  });
  // The panel opens as the reader left it, without sliding in.
  const body=$("tf-map-body");
  body.classList.add("tf-map-still");
  filters.setPanel(filters.startOpen,false);
  readHash();
  filters.render();
  setTimeout(()=>body.classList.remove("tf-map-still"),200);
 };
 return page;
}"""


def explorer_article(model_json: str) -> str:
    """The Verification Explorer: every item behind the monitors, one row each, on the map's tools line, filters
    panel, hints and Find. One section holds the heading, the map's shared styles and health palette scoped to the
    explorer, then its own, the markup and one script: the shared runtime, the facts and the explorer."""
    scope = "#verification-explorer"
    css = "\n".join(
        (
            MAP_SHARED_CSS.replace("#verification-health-map", scope),
            HEALTH_MAP_CSS.replace("#verification-health-map", scope),
            EXPLORER_CSS,
        )
    )
    markup = (
        map_tools(
            "Every item behind the monitors, one row each: what it is, how it stands, why it fails and where its "
            "details are.",
            filters_tip="Open the filters beside the list (F).",
            find_tip="Find a goal, capability or contract and keep only its items (/).",
            copy_tip="Copy a link to this list with its filters and grouping.",
        )
        + '<div class="tf-map-body" id="tf-map-body">'
        + map_panel("Items", "Items by kind", "Filters for the list")
        + '<div class="tf-ex-main" id="tf-ex-main"><div class="tf-map-list-bar tf-ex-bar">'
        '<span class="tf-map-list-bar-label">Group by</span><span class="tf-map-seg" id="tf-ex-group-by"></span>'
        '<input class="tf-ex-search" id="tf-ex-search" type="search" placeholder="Filter by text" '
        'aria-label="Filter the items by text" autocomplete="off" spellcheck="false">'
        '<span class="tf-map-summary" id="tf-ex-summary" aria-live="polite"></span></div>'
        '<div class="tf-ex-define" id="tf-ex-define" hidden></div>'
        '<div class="tf-ex-list" id="tf-ex-list"></div></div></div>'
        + map_find(
            "Find in the explorer",
            "Find a goal, capability or contract by name or ID",
            "↑ ↓ move · Enter keeps its items · Esc closes",
        )
        + '<div id="tf-map-hint" class="tf-map-hint" role="tooltip" aria-hidden="true"></div>'
    )
    script = "\n".join((MAP_SHARED_JS, f"const model={model_json};", EXPLORER_JS, "explorerPage(model).start();"))
    return (
        '<section id="verification-explorer">\n<h1>Verification Explorer'
        '<a class="headerlink" href="#verification-explorer" title="Link to this heading">#</a></h1>\n'
        f'<style id="tf-explorer-style">\n{css}\n</style>\n'
        f"{markup}\n"
        f"<script>\n(()=>{{\n{script}\n}})();\n</script>\n</section>"
    )


MODEL_ROLES_CSS = r"""#model-roles{font-variant-numeric:tabular-nums}
#model-roles .tf-mr-lead{max-width:82ch;color:var(--pst-color-text-muted)}
#model-roles .tf-mr-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));gap:.6rem;margin:.8rem 0 1.4rem}
#model-roles .tf-mr-card{border:1px solid var(--tf-map-line);border-radius:var(--tf-map-radius);background:var(--tf-map-goal);padding:.6rem .8rem}
#model-roles .tf-mr-card .tf-mr-label{display:block;font-size:.74rem;color:var(--pst-color-text-muted)}
#model-roles .tf-mr-card b{display:block;margin:.1rem 0;font-size:1.3rem;font-weight:700}
#model-roles .tf-mr-card p{margin:0;font-size:.76rem;color:var(--pst-color-text-muted)}
#model-roles .tf-mr-card.pass b{color:var(--tf-hm-pass-ink)}
#model-roles .tf-mr-card.fail b{color:var(--tf-hm-fail-ink)}
#model-roles .tf-mr-card.fail{border-color:color-mix(in srgb,var(--tf-hm-fail) 55%,transparent)}
#model-roles .tf-mr-card.unknown b{color:var(--pst-color-text-muted)}
#model-roles .tf-mr-bar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--tf-hm-na);margin:.4rem 0 .3rem}
#model-roles .tf-mr-bar i{display:block;height:100%}
#model-roles .tf-mr-legend{display:flex;flex-wrap:wrap;gap:.2rem .9rem;margin:0 0 .8rem;font-size:.76rem;color:var(--pst-color-text-muted)}
#model-roles .tf-mr-legend i{display:inline-block;width:.7rem;height:.7rem;border-radius:2px;margin-right:.3rem;vertical-align:-1px}
#model-roles .tf-mr-table{overflow-x:auto}
#model-roles table{width:100%;border-collapse:collapse;font-size:.8rem;margin:.3rem 0 1.1rem}
#model-roles th,#model-roles td{padding:.3rem .5rem;border-bottom:1px solid var(--tf-map-line);text-align:left;vertical-align:top}
#model-roles th{font-weight:650;color:var(--pst-color-text-muted)}
#model-roles .num,#model-roles .nowrap{text-align:right;white-space:nowrap}
#model-roles .nowrap{text-align:left}
#model-roles td.fail{color:var(--tf-hm-fail-ink)}
#model-roles td.pass{color:var(--tf-hm-pass-ink)}
#model-roles code{font-size:.74rem;overflow-wrap:anywhere}
#model-roles .tf-mr-note{max-width:82ch;font-size:.78rem;color:var(--pst-color-text-muted)}"""

# The tone of each cause on the bar: the health palette only, kept in the pass colour and every
# rejection in the fail colour, the stronger the more it says the question lacked something.
MODEL_ROLES_TONES = {
    "kept": "var(--tf-hm-pass)",
    "grounding": "var(--tf-hm-fail)",
    "runtime-api": "color-mix(in srgb,var(--tf-hm-fail) 78%,var(--tf-hm-na))",
    "syntax": "color-mix(in srgb,var(--tf-hm-fail) 64%,var(--tf-hm-na))",
    "behaviour": "color-mix(in srgb,var(--tf-hm-fail) 50%,var(--tf-hm-na))",
    # Apart from the fail tones by pattern, not only by strength: its test runs, it only misses.
    "weak": "repeating-linear-gradient(45deg,color-mix(in srgb,var(--tf-hm-fail) 55%,var(--tf-hm-na)) 0 3px,var(--tf-hm-na) 3px 6px)",
    "rules": "var(--tf-hm-na-strong)",
    "lint": "var(--tf-hm-na-strong)",
    # Kept alone, failed in the full run: a runtime fault, patterned as the weak one is.
    "suite": "repeating-linear-gradient(-45deg,color-mix(in srgb,var(--tf-hm-fail) 78%,var(--tf-hm-na)) 0 3px,var(--tf-hm-na) 3px 6px)",
    "unknown": "var(--tf-hm-na)",
}


def _palette(scope: str) -> str:
    """The map's own variables and health palette, scoped to another page: its declarations only."""
    return "\n".join(
        line.replace("#verification-health-map", scope)
        for css in (MAP_SHARED_CSS, HEALTH_MAP_CSS)
        for line in css.splitlines()
        if line.startswith(("#verification-health-map{--", "html[data-theme=dark] #verification-health-map{--"))
    )


def model_roles_article(facts: dict, facts_json: str) -> str:
    """The Model roles page: whether the models the pipeline asks do their job, and when a draft fails,
    whether the model misread or the question lacked what it needed. Static, from the builder's facts,
    which the page also carries for the gate to recount."""
    from html import escape

    draft = facts["draft"]
    causes = facts["causes"]
    # A reason quoting markup must not close the facts' script element.
    embedded = facts_json.replace("</", "<\\/")

    def share(part: int, whole: int) -> str:
        return f"{part / whole:.0%}" if whole else "—"

    def card(label: str, value: str, tone: str, note: str) -> str:
        return (f'<div class="tf-mr-card {tone}"><span class="tf-mr-label">{escape(label)}</span><b>{escape(value)}</b>'
                f"<p>{escape(note)}</p></div>")

    def table(head: list[str], rows: list[list[tuple[str, str]]], numeric: frozenset[int] | set[int] = frozenset(),
              nowrap: frozenset[int] | set[int] = frozenset()) -> str:
        def kind(index: int) -> str:
            return "num " if index in numeric else "nowrap " if index in nowrap else ""

        cells = "".join(
            "<tr>" + "".join(f'<td class="{kind(index)}{tone}">{value}</td>' for index, (value, tone) in enumerate(row)) + "</tr>"
            for row in rows
        )
        return ('<div class="tf-mr-table"><table><thead><tr>'
                + "".join(f'<th class="{"num" if index in numeric else ""}">{escape(name)}</th>' for index, name in enumerate(head))
                + f"</tr></thead><tbody>{cells}</tbody></table></div>")

    def plain(value) -> tuple[str, str]:
        return escape(str(value)), ""

    word = {"pass": "healthy", "fail": "failing", "unknown": "too few recorded drafts"}[draft["status"]]
    health_note = (
        f"{draft['kept']} of its last {draft['recent']} recorded drafts kept ({share(draft['kept'], draft['recent'])}); "
        f"failing below {draft['floor']:.0%} of the last {draft['window']}, judged from {draft['minimum']} on."
    )
    invented = draft["invented"]
    canaries_failed = [row for row in facts["canaries"] if not row["passed"]]
    calibration = facts["calibration"]
    judging = facts["judging"]
    judged_answers = sum(row["answers"] for row in judging["roles"])
    judged_troubled = sum(row["troubled"] for row in judging["roles"])
    caps: dict = facts.get("caps") or {"factor": 3, "roles": [], "capped": 0}
    cards = "".join((
        card("Draft author", word, draft["status"], health_note),
        card("Invented project API", str(len(invented)), "fail" if invented else "pass" if draft["recent"] else "unknown",
             "names, members or arguments the project does not define, in the recent drafts: the question lacked them"
             if invented else "no recent draft used a name the project does not define"),
        card("Context gaps", str(len(draft["gaps"])), "fail" if draft["gaps"] else "pass" if draft["recorded"] else "unknown",
             "project names drafts used that their question did not show" if draft["gaps"] else "every project name a draft used was in its question"),
        card("Canaries", f"{len(facts['canaries']) - len(canaries_failed)} of {len(facts['canaries'])}", "fail" if canaries_failed else "pass",
             "every model the Test Plan lists passed its canaries for the current questions" if not canaries_failed
             else "models that have not passed their canaries for the current questions do not answer"),
        card("Assessor calibration", "calibrated" if calibration["calibrated"] else "not calibrated", "pass" if calibration["calibrated"] else "fail",
             f"threshold {calibration['threshold']}, {len(calibration['usable'])} usable models" if calibration["calibrated"] else str(calibration["reason"])),
        card("Judges' sources", f"{judged_answers - judged_troubled} of {judged_answers}", "fail" if judged_troubled else "pass" if judged_answers else "unknown",
             "verdicts, reviews and assessor answers whose sources are found in their own question"
             + (": the others do not count and are asked again" if judged_troubled else "")),
        card("Price caps", f"{caps['capped']} stopped", "fail" if caps["capped"] else "pass",
             "calls that reached their price cap: each was asked once more at twice the cap, then of the next model"
             if caps["capped"] else "no call has reached its price cap; each cap follows its role's most expensive answered call"),
    ))
    total = sum(draft["causes"].values())
    order = [cause for cause in causes if draft["causes"].get(cause)]
    bar = "".join(
        f'<i style="width:{draft["causes"][cause] / total * 100:.2f}%;background:{MODEL_ROLES_TONES[cause]}" title="{escape(causes[cause])}: {draft["causes"][cause]}"></i>'
        for cause in order
    ) if total else ""
    legend = "".join(
        f'<span><i style="background:{MODEL_ROLES_TONES[cause]}"></i>{escape(causes[cause])} · {draft["causes"][cause]}</span>' for cause in order
    )
    models = table(
        ["Model", "Recorded drafts", "Kept", "Kept share", "Why the others were not kept", "Earlier drafts", "Earlier kept", "Earlier with invented API"],
        [
            [
                plain(row["model"]), plain(sum(row["recorded"].values())), plain(row["recorded"].get("kept", 0)),
                plain(share(row["recorded"].get("kept", 0), sum(row["recorded"].values()))),
                plain("; ".join(f"{causes[cause]}: {count}" for cause, count in sorted(row["recorded"].items(), key=lambda item: -item[1]) if cause != "kept") or "—"),
                plain(sum(row["earlier"].values())), plain(row["earlier"].get("kept", 0)),
                (escape(str(row["earlier"].get("grounding", 0))), "fail" if row["earlier"].get("grounding") else ""),
            ]
            for row in draft["models"]
        ],
        numeric={1, 2, 3, 5, 6, 7},
    )
    rejected = table(
        ["When", "Contract", "Mutant", "Model", "Cause", "Why"],
        [
            [
                plain(str(row.get("at") or "")[:16].replace("T", " ")), plain(row.get("contract_id")), (f"<code>{escape(str(row.get('key')))}</code>", ""),
                plain(row.get("model")), (escape(causes.get(str(row.get("cause")), str(row.get("cause")))), "fail" if row.get("cause") == "grounding" else ""),
                (escape(str(row.get("reason") or "")) + (f' <a href="{escape(str(row["answer"]))}">Question and answer</a>' if row.get("answer") else ""), ""),
            ]
            for row in draft["rejected"]
        ],
        nowrap={0, 2},
    ) if draft["rejected"] else "<p>No recorded draft has been rejected yet.</p>"
    gaps = table(
        ["Project name a draft used that its question did not show", "Drafts"],
        [[(f"<code>{escape(name)}</code>", ""), plain(count)] for name, count in draft["gaps"]],
        numeric={1},
    ) if draft["gaps"] else "<p>Every project name a recorded draft used was in its question.</p>"
    canaries = table(
        ["Role · backend · model", "Passed", "When", "What failed", "Questions and answers"],
        [[plain(row["entry"]), ("yes", "pass") if row["passed"] else ("no", "fail"), plain(row["ran_at"][:16].replace("T", " ")), plain(row["detail"] or "—"),
          (" ".join(f'<a href="{escape(str(path))}">{escape(str(case))}</a>' for case, path in row.get("answers") or []) or "—", "")]
         for row in facts["canaries"]],
    )
    rungs = {1: "without tools", 2: "the draft author with tools", 3: "the last resort, the verdict's own model with tools"}
    ladder = table(
        ["Rung", "Recorded drafts", "Kept"],
        [[plain(f"{level} · {rungs[level]}"), plain(draft["levels"][str(level)]["attempts"]), plain(draft["levels"][str(level)]["kept"])] for level in (1, 2, 3)],
        numeric={1, 2},
    )
    efforts = table(
        ["Rung", "Model", "Level", "Recorded drafts", "Kept", "Kept share"],
        [[plain(f"{row['rung']} · {rungs.get(row['rung'], '')}"), plain(row["model"]), plain(row["shown"]), plain(row["attempts"]), plain(row["kept"]),
          plain(share(row["kept"], row["attempts"]))] for row in draft.get("efforts") or []],
        numeric={3, 4, 5},
    ) if draft.get("efforts") else "<p>No draft has been recorded with its level yet.</p>"
    last_resort = table(
        ["Contract", "Mutant", "Model", "Pin", "When"],
        [[plain(row.get("contract_id")), (f"<code>{escape(str(row.get('key')))}</code>", ""), plain(row.get("model")),
          (f"<code>{escape(str(row.get('path')))}</code>" + (f' <a href="{escape(str(row["answer"]))}">Question and answer</a>' if row.get("answer") else ""), ""),
          plain(str(row.get("at") or "")[:16].replace("T", " "))] for row in draft["last_resort"]],
        nowrap={1, 4},
    ) if draft["last_resort"] else "<p>The last resort has written no pin.</p>"
    roles_cite = table(
        ["Role", "Answers that cite", "Sources not found in the question"],
        [[plain(row["role"]), plain(row["answers"]), (escape(str(row["troubled"])), "fail" if row["troubled"] else "")] for row in judging["roles"]],
        numeric={1, 2},
    ) if judging["roles"] else "<p>No current verdict, review or assessor answer cites its sources yet.</p>"
    troubled = table(
        ["Role", "Contract", "Survivor", "Model", "What does not hold up"],
        [[plain(row["role"]), plain(row["contract_id"]), (f"<code>{escape(str(row['key']))}</code>", ""), plain(row["model"]),
          (escape("; ".join(row["problems"])) + (f' <a href="{escape(str(row["answer"]))}">Question and answer</a>' if row.get("answer") else ""), "fail")]
         for row in judging["troubled"]],
        nowrap={2},
    ) if judging["troubled"] else "<p>Every current answer's sources are found in its own question.</p>"
    calls = table(
        ["Role", "Model", "Level", "Last call", "Calls made", "Deferred", "Unavailable", "Failed", "Stopped by the cap", "List price"],
        [[plain(row["role"]), plain(row["model"]), plain(row.get("level") or "—"), plain(str(row.get("last") or "")[:10]), plain(row["calls"]), plain(row["deferred"]),
          plain(row["unavailable"]), (escape(str(row["failed"])), "fail" if row["failed"] else ""),
          (escape(str(row.get("capped", 0))), "fail" if row.get("capped") else ""), plain(f"${row['usd']:.2f}")]
         for row in facts["calls"]],
        numeric={4, 5, 6, 7, 8, 9},
        nowrap={3},
    )
    cap_table = table(
        ["Role", "Tools", "Cap now", "Test Plan's cap", "Most expensive answered call", "Stopped by the cap", "Last stopped"],
        [[plain(row["role"]), plain("with tools" if row["tools"] else "without"), plain(f"${row['cap']:.2f}"), plain(f"${row['floor']:.2f}"),
          plain(f"${row['highest']:.3f}"), (escape(str(row["capped"])), "fail" if row["capped"] else ""),
          plain(str(row.get("last_capped") or "—")[:16].replace("T", " "))]
         for row in caps["roles"]],
        numeric={2, 3, 4, 5},
        nowrap={6},
    ) if caps["roles"] else "<p>No call has reported its list price yet.</p>"
    rechecks = facts["rechecks"]
    recheck_groups = table(
        ["Role", "Answered by", "Asked now of", "Suppressions", "Sampled", "Re-checked", "Upheld"],
        [[plain(row["role"]), plain(row["answered"]), plain(row["now"]), plain(row["suppressions"]), plain(row["sampled"]), plain(row["asked"]),
          (escape(str(row["upheld"])), "fail" if row["upheld"] < row["asked"] else "")] for row in rechecks["groups"]],
        numeric={3, 4, 5, 6},
    ) if rechecks["groups"] else "<p>Every suppression that counts was answered by the model and level its role asks now.</p>"
    recheck_rows = table(
        ["Role", "Contract", "Mutant", "Was", "Now", "Reason"],
        [[plain(row["role"]), plain(row["contract_id"]), (f"<code>{escape(str(row['key']))}</code>", ""), plain(row["suppressed"]),
          (escape(str(row["verdict"])), "" if row["verdict"] in ("equivalent", "irrelevant") else "fail"),
          (escape(str(row["reason"])) + (f' <a href="{escape(str(row["answer"]))}">Question and answer</a>' if row.get("answer") else ""), "")]
         for row in rechecks["rows"]],
        nowrap={2},
    ) if rechecks["rows"] else "<p>No suppression has been re-checked yet.</p>"
    waiting = table(
        ["Contract", "Mutant", "Kind", "Recorded drafts", "Where it stands"],
        [[plain(row["contract_id"]), (f"<code>{escape(str(row['key']))}</code>", ""), plain(row["kind"]), plain(row["drafts"]), plain(row["stage"])]
         for row in facts["waiting"]],
        numeric={3},
        nowrap={1},
    ) if facts["waiting"] else "<p>Every pin verdict that counts has its pin.</p>"
    subsumed = facts["subsumed"]
    subsumed_table = table(
        ["Contract", "Pins removed", "Kept pins that kill their mutants"],
        [[plain(row["contract_id"]), plain(row["removed"]), plain(row["by"])] for row in subsumed["contracts"]],
        numeric={1, 2},
    ) if subsumed["contracts"] else "<p>No pin has been removed as redundant.</p>"
    return (
        '<section id="model-roles">\n<h1>Model roles<a class="headerlink" href="#model-roles" title="Link to this heading">#</a></h1>\n'
        f'<style id="tf-model-roles-style">\n{_palette("#model-roles")}\n{MODEL_ROLES_CSS}\n</style>\n'
        '<p class="tf-mr-lead">Whether the models the mutation pipeline asks do their job: the generator writes mutants, the '
        "draft author writes the tests that pin survivors, the assessors and the verdict judge survivors. A draft counts only "
        "when the cascade keeps it: in the project's style, passing on the original five times and failing on the mutant. When "
        "one is not kept, the cause says whether the model misread the task or its question lacked what it needed.</p>\n"
        f'<div class="tf-mr-cards">{cards}</div>\n'
        '<h2 id="draft-author">Draft author</h2>\n'
        f"<p>{draft['recorded']} drafts recorded with their cause, {draft['earlier']} earlier drafts read back from their stored "
        f"answers ({draft['earlier_invented']} of them use a name the project does not define).</p>\n"
        f'<div class="tf-mr-bar" role="img" aria-label="Recorded drafts by cause">{bar}</div><div class="tf-mr-legend">{legend}</div>\n'
        f"{models}\n<h3>Latest rejected drafts</h3>\n{rejected}\n<h3>Context gaps</h3>\n{gaps}\n"
        '<h3 id="ladder">The ladder</h3>\n<p class="tf-mr-note">A mutant every draft without tools missed gets drafts from the '
        "draft author with tools, working in a copy of the project where it reads the code and runs the cascade's own check, and "
        "then from the last resort, the verdict's own model with the same tools: one at each level of the rung's ladder of levels, "
        "the next level only after the cascade rejected the draft below. A pin the last resort wrote says so in its "
        "header, so a later verdict model can look at it again.</p>\n"
        f"{ladder}\n"
        '<h3 id="levels">Levels</h3>\n<p class="tf-mr-note">How often each model kept its draft at each level: the data a ladder '
        "of levels starts from. A level no attempt recorded is read from its call's sign-in: before 2026-09-29 no call recorded one.</p>\n"
        f"{efforts}\n<h3>Pins the last resort wrote</h3>\n{last_resort}\n"
        '<h3 id="waiting">Waiting for a pin</h3>\n<p class="tf-mr-note">Every mutant whose verdict that counts is pin and that has '
        "no pin yet, and where its ladder stands. A mutant every rung missed has its verdict asked again with the project's callers "
        "in view; one that stays pin then waits for the person.</p>\n"
        f"{waiting}\n"
        '<h3 id="subsumed">Pins other pins made redundant</h3>\n<p class="tf-mr-note">A pin whose mutant other pins of its contract '
        "kill, by the kill matrix of the contract's pins against its pinned mutants, is removed and waits beside its record; it comes "
        f"back when the campaign shows the removal cost a kill. {sum(row['removed'] for row in subsumed['contracts'])} removed, "
        f"{subsumed['pins']} pins now.</p>\n"
        f"{subsumed_table}\n"
        '<h2 id="judging">Judges\' sources</h2>\n<p class="tf-mr-note">The verdict, its review and every assessor cite what their '
        "answer rests on, copied word for word from their question: a line the change touches and, for a verdict, the words of the "
        "requirement. An answer whose sources are not in its question does not count and is asked again.</p>\n"
        f"{roles_cite}\n<h3>Latest answers whose sources do not hold up</h3>\n{troubled}\n"
        '<h3 id="rechecks">Re-checks of suppressions</h3>\n<p class="tf-mr-note">When the model or level a verdict role asks first '
        f"is not the one that answered a suppression that counts, one in {rechecks['one_in']} of that answerer's suppressions, chosen "
        "by key, is asked again of the role as it now stands; an answer that does not uphold one pins its mutant.</p>\n"
        f"{recheck_groups}\n{recheck_rows}\n"
        '<h2 id="canaries">Canaries</h2>\n<p class="tf-mr-note">Each model a role lists answers in earnest only after it '
        "passes its canaries, the role's very question on cases whose outcome is known.</p>\n"
        f"{canaries}\n"
        '<h2 id="calls">Calls by role and model</h2>\n<p class="tf-mr-note">From the consumption ledger: every call made, and every '
        "call the budget deferred or no backend could take, by the level it answered at. A Claude call sets its level by flag and "
        "reads none of the person's settings; before 2026-09-29 calls recorded no level, and the level shown is the one its sign-in "
        "gave it: a level saved in that sign-in's settings, else the model's default in Claude Code. An Antigravity model names its "
        "level in its id.</p>\n"
        f"{calls}\n"
        '<h2 id="price-caps">Price caps</h2>\n<p class="tf-mr-note">A call that reports its list price stops at its cap, a fuse '
        f"against a call that runs away: the Test Plan's cap, or {caps['factor']} times the role's most expensive answered call, "
        "whichever is larger, so the cap follows the models' prices when they change. A call that reaches it is asked once more at "
        "twice the cap; one that reaches that too is asked of the role's next model, and a rung of the ladder climbs.</p>\n"
        f"{cap_table}\n"
        '<p class="tf-mr-note">Read from the retained records only: each contract\'s drafts.json and stored answers under '
        ".ai-bridge/survivor-verdicts, the survivor triage, the canary results, the assessors' calibration and the model ledger. "
        "Every stored question and answer a record names is published beside this page, and the explorer links each survivor's.</p>\n"
        f'<script type="application/json" id="tf-model-roles-facts">{embedded}</script>\n</section>'
    )
