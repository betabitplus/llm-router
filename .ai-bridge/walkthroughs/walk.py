"""Walk a direction's path on the local portal, frame what to look at and caption each step in Russian.

The report of a direction of the monitor plan (`.ai-bridge/development-history/monitor-plan.md`) is
the path a person walks on the portal: one folder per direction, its screenshots in the order they
are seen, each with a caption that says where to look and what it answers (history 060).

    python walk.py <items module> <out root> [folder ...]

It needs the portal served at BASE and Playwright with Chromium (the project's browser checks run
it from a separate Python). Each item: {"folder", "title", "pain", "answer", "steps": [step, ...]};
each step:
  url           open this page first (relative to the portal; "file:<repo path>.md" renders a file
                of the repository as the code host shows it), else stay on the current one
  actions       [("click"|"hover"|"click_box"|"hover_box"|"scroll"|"press"|"js", target), ...]
  view          a CSS selector, or view_locator a locator, brought near the top before the shot
  marks         [(locator, "1"), ...] framed and numbered on the shot
  title, text   the caption: the step and what to look at; circled digits match the frames
  file          the image name without its number
  keep          an earlier image of the folder, kept as it is (a snapshot of a state that is gone)
"""
import importlib.util
import io
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
# The browser runs from a separate Python with Playwright and Chromium, not the project's environment.
from playwright.sync_api import sync_playwright  # ty: ignore[unresolved-import]

BASE = "http://127.0.0.1:8765/"
ROOT = Path(__file__).resolve().parents[2]
RENDER = """
import sys
from pathlib import Path
from markdown_it import MarkdownIt
body = MarkdownIt("commonmark").render(Path(sys.argv[1]).read_text())
crumbs = " / ".join(Path(sys.argv[1]).relative_to(sys.argv[3]).parts)
style = ("body{margin:0;background:#fff;font:16px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#1f2328}"
  ".bar{background:#f6f8fa;border-bottom:1px solid #d0d7de;padding:14px 32px;font-size:14px;color:#57606a}"
  "main{max-width:980px;margin:24px auto;padding:0 32px}h1{font-size:30px;border-bottom:1px solid #d8dee4;padding-bottom:8px}"
  "h2{font-size:22px;border-bottom:1px solid #d8dee4;padding-bottom:6px;margin-top:28px}"
  "code{background:#eff1f3;border-radius:6px;padding:2px 5px;font-size:85%}li{margin:4px 0}")
Path(sys.argv[2]).write_text(f"<!doctype html><html lang=ru><head><meta charset=utf-8><style>{style}</style></head>"
  f"<body><div class=bar>llm-router / {crumbs}</div><main>{body}</main></body></html>")
"""


def rendered(path):
    """A Markdown file of the repository as an HTML page, rendered with the project's markdown-it."""
    out = Path(tempfile.mkdtemp()) / (Path(path).stem + ".html")
    subprocess.run([str(ROOT / ".venv/bin/python"), "-c", RENDER, str(ROOT / path), str(out), str(ROOT)], check=True)
    return out.as_uri()
ACCENT = (232, 89, 12)
BAND = (255, 244, 230)
INK = (33, 37, 41)
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
title_font = ImageFont.truetype(BOLD, 28)
text_font = ImageFont.truetype(FONT, 21)
badge_font = ImageFont.truetype(BOLD, 20)


BADGES = {chr(0x2460 + index): str(index + 1) for index in range(9)}
BADGE = 30


def token_width(token, font):
    return BADGE if token in BADGES else font.getlength(token)


def wrap(text, font, width):
    """Lines of tokens; a circled digit is drawn as the same orange badge as on the shot."""
    lines = []
    space = font.getlength(" ")
    for paragraph in text.split("\n"):
        line, used = [], 0.0
        for token in paragraph.split():
            extra = token_width(token, font) + (space if line else 0)
            if line and used + extra > width:
                lines.append(line)
                line, used = [token], token_width(token, font)
            else:
                line.append(token)
                used += extra
        lines.append(line)
    return lines


def draw_line(draw, x, y, tokens, font):
    space = font.getlength(" ")
    for index, token in enumerate(tokens):
        if index:
            x += space
        if token in BADGES:
            cx, cy = x + BADGE / 2, y + 13
            draw.ellipse((cx - 13, cy - 13, cx + 13, cy + 13), fill=ACCENT)
            draw.text((cx, cy), BADGES[token], font=badge_font, fill=(255, 255, 255), anchor="mm")
            x += BADGE
        else:
            draw.text((x, y), token, font=font, fill=INK)
            x += font.getlength(token)


def annotate(png, boxes, title, text):
    shot = Image.open(io.BytesIO(png)).convert("RGB") if isinstance(png, bytes) else Image.open(png).convert("RGB")
    draw = ImageDraw.Draw(shot)
    for box, label in boxes:
        if not box:
            continue
        x0, y0 = box["x"] - 6, box["y"] - 6
        x1, y1 = box["x"] + box["width"] + 6, box["y"] + box["height"] + 6
        x0, y0 = max(x0, 2), max(y0, 2)
        x1, y1 = min(x1, shot.width - 3), min(y1, shot.height - 3)
        if x1 - x0 < 8 or y1 - y0 < 8:
            print(f"   a mark is off the screen: {label}")
            continue
        draw.rounded_rectangle((x0, y0, x1, y1), radius=8, outline=ACCENT, width=4)
        if label:
            cx, cy = max(x0, 20), max(y0, 20)
            draw.ellipse((cx - 17, cy - 17, cx + 17, cy + 17), fill=ACCENT, outline=(255, 255, 255), width=2)
            draw.text((cx, cy), label, font=badge_font, fill=(255, 255, 255), anchor="mm")
    width = shot.width
    lines = wrap(text, text_font, width - 60)
    band = 30 + 38 + len(lines) * 31 + 22
    out = Image.new("RGB", (width, shot.height + band), BAND)
    draw = ImageDraw.Draw(out)
    draw.rectangle((0, 0, 8, band), fill=ACCENT)
    draw.text((30, 24), title, font=title_font, fill=INK)
    for index, line in enumerate(lines):
        draw_line(draw, 30, 24 + 44 + index * 31, line, text_font)
    draw.line((0, band - 1, width, band - 1), fill=(222, 210, 196), width=2)
    out.paste(shot, (0, band))
    return out


def locate(page, target):
    return page.locator(target).first


def box_of(page, target):
    """The element's box on screen as the page lays it out; SVG links that Playwright counts as
    invisible still have one."""
    # Hidden views keep their own copies of an element: the first one laid out on screen counts.
    boxes = page.locator(target).evaluate_all(
        "els => els.map(e => { const r = e.getBoundingClientRect(); return {x: r.left, y: r.top, width: r.width, height: r.height}; })"
    )
    laid_out = [box for box in boxes if box["width"] and box["height"]]
    # A list repeats an element: the first one on screen is the one the reader sees.
    on_screen = [box for box in laid_out if box["y"] + box["height"] > 90 and box["y"] < 880]
    return (on_screen or laid_out or [None])[0]


def run_item(page, item, root):
    folder = root / item["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    readme = [f"# {item['title']}", "", f"**Боль.** {item['pain']}", "", "**Путь.**", ""]
    for number, step in enumerate(item["steps"], 1):
        name = f"{number}-{step['file']}.png"
        if step.get("keep"):
            if not (folder / name).is_file():
                raise SystemExit(f"{item['folder']}: the kept image {name} is missing")
            image = None
        else:
            # The pointer rests away from the page, unless a step hovers on purpose.
            page.mouse.move(2, 2)
            if step.get("url"):
                # A file of the repository is shown as rendered Markdown, as the code host shows it.
                target = rendered(step["url"][5:]) if step["url"].startswith("file:") else BASE + step["url"]
                page.goto(target, wait_until="networkidle")
                page.wait_for_timeout(step.get("wait", 2200))
            for kind, target in step.get("actions") or []:
                if kind == "click":
                    locate(page, target).click()
                elif kind == "hover":
                    locate(page, target).hover()
                elif kind in ("hover_box", "click_box"):
                    # An SVG tile: its link is not a box Playwright can act on, its shape is.
                    box = box_of(page, target)
                    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    if kind == "click_box":
                        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                        page.wait_for_load_state("networkidle")
                elif kind == "scroll":
                    locate(page, target).scroll_into_view_if_needed()
                elif kind == "press":
                    page.keyboard.press(target)
                elif kind == "js":
                    page.evaluate(target)
                page.wait_for_timeout(900)
            if step.get("view"):
                page.evaluate("([target, offset]) => { const el = document.querySelector(target); if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - offset); }", [step["view"], step.get("offset", 130)])
                page.wait_for_timeout(700)
            elif step.get("view_locator"):
                box = box_of(page, step["view_locator"])
                if box:
                    page.evaluate("y => window.scrollBy(0, y)", box["y"] - step.get("offset", 130))
                    page.wait_for_timeout(700)
            boxes = []
            for target, label in step.get("marks") or []:
                boxes.append((box_of(page, target), label))
            missing = [label for box, label in boxes if not box]
            if missing:
                print(f"   {item['folder']} step {number}: no box for marks {missing}")
            image = annotate(page.screenshot(), boxes, f"Шаг {number}. {step['title']}", step["text"])
        # A palette of 256 colours keeps a screenshot as sharp at a third of the size.
        if image is not None:
            image.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(folder / name, optimize=True)
        readme += [f"{number}. **{step['title']}** {step['text']}", "", f"   ![Шаг {number}]({name})", ""]
    readme += [f"**Что получаю.** {item['answer']}", ""]
    (folder / "README.md").write_text("\n".join(readme))
    print("done", item["folder"], len(item["steps"]))


def main():
    spec = importlib.util.spec_from_file_location("items", sys.argv[1])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = Path(sys.argv[2])
    wanted = set(sys.argv[3:])
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, color_scheme="light")
        for item in module.ITEMS:
            if wanted and item["folder"] not in wanted:
                continue
            run_item(page, item, root)
        browser.close()


if __name__ == "__main__":
    main()
