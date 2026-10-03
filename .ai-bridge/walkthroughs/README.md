# Walkthroughs

The report of a direction of the [monitor plan](../development-history/monitor-plan.md) is the path a
person walks on the portal: one folder per working direction, its screenshots in viewing order, each
with a caption that says where to look and what it answers (history 060).

- `walk.py` walks the paths on the local portal, frames what to look at and captions each step.
- `plan_paths.py` holds the paths of the plan's working directions.

Serve `docs/_build/html` on port 8765, then run it with a Python that has Playwright and Chromium:

```bash
python .ai-bridge/walkthroughs/walk.py .ai-bridge/walkthroughs/plan_paths.py .ai-bridge/development-history/entries/060-screens
```

A step marked `keep` is a snapshot of a state that no longer exists; the run leaves its image as it is.
