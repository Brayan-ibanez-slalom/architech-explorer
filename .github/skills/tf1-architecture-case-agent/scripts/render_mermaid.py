#!/usr/bin/env python3
"""
Render a single Mermaid diagram definition to a cropped PNG using headless
Google Chrome + the mermaid.js CDN bundle. No npm/mermaid-cli dependency
required (useful on machines where npm is pinned to a private/broken
registry).

Usage:
    python3 render_mermaid.py INPUT.mmd OUTPUT.png [--width 1800] [--height 1400]

INPUT.mmd must contain raw Mermaid source (e.g. a `graph TD` or
`flowchart LR` block, with no surrounding HTML/markdown fences).
"""
import argparse
import os
import subprocess
import sys
import tempfile

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

# Pin a specific mermaid version for reproducible rendering (floating "@10"
# can change behavior/output between runs as new 10.x releases ship).
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"

# NOTE: the Mermaid source is injected via a literal placeholder replace (not
# str.format), because flowchart syntax uses '{' and '}' (e.g. A{Decision})
# which would otherwise break .format() / be misread as fields.
PAGE_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="__MERMAID_CDN__"></script>
<style>body{margin:0;background:#fff;} .mermaid{background:#fff;}</style>
</head><body>
<div class="mermaid">
__MERMAID_SOURCE__
</div>
<script>mermaid.initialize({startOnLoad:true, theme:'default'});</script>
</body></html>"""


def _build_page(source_text):
    return (PAGE_TEMPLATE
            .replace("__MERMAID_CDN__", MERMAID_CDN)
            .replace("__MERMAID_SOURCE__", source_text.strip()))


def find_chrome():
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    raise RuntimeError(
        "Could not find a Chrome/Chromium/Edge binary. Checked: " + ", ".join(CHROME_CANDIDATES)
    )


def render(source_text, out_png, width=1800, height=1400, virtual_time_budget=8000, timeout=60):
    chrome = find_chrome()
    with tempfile.TemporaryDirectory() as td:
        html_path = os.path.join(td, "diagram.html")
        raw_png = os.path.join(td, "raw.png")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(_build_page(source_text))

        cmd = [
            chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
            f"--window-size={width},{height}",
            f"--virtual-time-budget={virtual_time_budget}",
            f"--screenshot={raw_png}",
            f"file://{html_path}",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Chrome timed out after {timeout}s rendering the diagram "
                f"(possible hang or an unreachable CDN: {MERMAID_CDN})."
            )
        if not os.path.exists(raw_png):
            raise RuntimeError(
                "Chrome screenshot failed.\nstdout: %s\nstderr: %s" % (result.stdout, result.stderr)
            )

        try:
            from PIL import Image, ImageChops
        except ImportError:
            raise RuntimeError("Pillow is required: pip3 install pillow")

        im = Image.open(raw_png).convert("RGB")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        diff = ImageChops.difference(im, bg)
        bbox = diff.getbbox()
        # Fail loudly instead of silently saving a blank white PNG — a missing
        # bbox (or a trivially small drawn area) means mermaid did not render
        # (syntax error, CDN unreachable, or a hang that still screenshotted).
        if not bbox:
            raise RuntimeError(
                "Diagram rendered BLANK (no non-white pixels). Likely a Mermaid "
                "syntax error or the CDN did not load. Not writing an empty PNG."
            )
        l, t, r, b = bbox
        if (r - l) < 8 or (b - t) < 8:
            raise RuntimeError(
                f"Diagram rendered too small to be real ({r - l}x{b - t}px). "
                "Treating as a failed render; not writing output."
            )
        pad = 20
        l = max(0, l - pad)
        t = max(0, t - pad)
        r = min(im.size[0], r + pad)
        b = min(im.size[1], b + pad)
        im = im.crop((l, t, r, b))
        os.makedirs(os.path.dirname(os.path.abspath(out_png)) or ".", exist_ok=True)
        im.save(out_png)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="Path to a .mmd file (or any text file) containing raw Mermaid source")
    ap.add_argument("output", help="Output PNG path")
    ap.add_argument("--width", type=int, default=1800)
    ap.add_argument("--height", type=int, default=1400)
    ap.add_argument("--timeout", type=int, default=60, help="Max seconds to wait for Chrome")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        source = f.read()
    render(source, args.output, width=args.width, height=args.height, timeout=args.timeout)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
