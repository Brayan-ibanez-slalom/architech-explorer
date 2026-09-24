#!/usr/bin/env python3
"""
visible_text.py — print only the text a human actually reads in a report.

Exists because the grep-based gate was bypassable: a red-team test passed all
eleven section checks with the required keywords hidden in an HTML comment, and
passed the vendor-balance audit by padding open-source names into a comment while
the prose recommended a single cloud.

Excludes: HTML comments, <script>, <style>, <template>, <noscript>,
elements with hidden / aria-hidden="true" / display:none / visibility:hidden.

Includes: Mermaid diagram bodies. Diagrams state requirements, and a fabricated
"99%" once survived a cleanup because an earlier script treated them as noise.
"""
import re
import sys
import unicodedata
from html.parser import HTMLParser

HIDDEN_TAGS = {"script", "style", "template", "noscript"}
VOID = {"meta", "br", "hr", "img", "link", "input", "source", "area",
        "base", "col", "embed", "track", "wbr"}
# Block-level boundaries must emit whitespace, otherwise adjacent table cells
# concatenate ("within 1 day" + "Operational" -> "within 1 dayOperational"),
# which corrupts both value detection and citation-adjacency windows.
BLOCK = {"p", "div", "td", "th", "tr", "li", "ul", "ol", "table", "thead",
         "tbody", "section", "article", "header", "footer", "br", "hr",
         "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "dt", "dd"}


class VisibleText(HTMLParser):
    """Depth-tracked visibility.

    Two bugs a red team found in the previous version:
      1. Hidden state used a single counter decremented on ANY end tag, so
         `<div style="display:none"><span>x</span>AFTER</div>` leaked "AFTER".
         State is now a stack keyed to element depth.
      2. Only inline style attributes were inspected, so a class defined in
         <style> as .stealth{display:none} hid content from humans while the
         gate still counted it. Class-based display:none/visibility:hidden
         rules are now parsed from <style> blocks and honoured.
    """

    def __init__(self, hidden_classes=frozenset(), hidden_ids=frozenset()):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []          # one entry per open element: True if it hides
        self.hidden_depth = 0
        self.skip_depth = 0
        self.hidden_classes = hidden_classes
        self.hidden_ids = hidden_ids

    def _hides(self, tag, a):
        if tag in HIDDEN_TAGS:
            return "skip"
        style = (a.get("style") or "").replace(" ", "").lower()
        if ("hidden" in a or a.get("aria-hidden") == "true"
                or "display:none" in style or "visibility:hidden" in style
                or "visibility:collapse" in style or "opacity:0" in style
                or re.search(r"font-size:0(px|em|rem|%)?\b", style)):
            return "hide"
        classes = set((a.get("class") or "").split())
        if classes & self.hidden_classes:
            return "hide"
        if a.get("id") and a["id"] in self.hidden_ids:
            return "hide"
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        state = self._hides(tag, a)
        if tag in BLOCK:
            self.parts.append("\n")
        if tag in VOID:
            return                      # void elements never open a scope
        self.stack.append(state)
        if state == "skip":
            self.skip_depth += 1
        elif state == "hide":
            self.hidden_depth += 1

    def handle_startendtag(self, tag, attrs):
        return                          # self-closing: no scope

    def handle_endtag(self, tag):
        if not self.stack:
            return
        if tag in BLOCK:
            self.parts.append("\n")
        state = self.stack.pop()
        if state == "skip" and self.skip_depth:
            self.skip_depth -= 1
        elif state == "hide" and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.skip_depth and not self.hidden_depth:
            self.parts.append(data)


HIDING_CSS = re.compile(
    r"([^{}]+)\{[^}]*?(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse)"
    r"|opacity\s*:\s*0(?!\.)|font-size\s*:\s*0)[^}]*\}",
    re.IGNORECASE | re.DOTALL,
)


CONTENT_CSS = re.compile(r"content\s*:\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)


def generated_content(raw):
    """CSS ::before/::after `content:` renders to the reader but is not in the DOM
    text. A red team used `.fab::before{content:"99% availability"}` to show a
    fabricated number to a human while staying invisible to the gate. Treat it
    as visible text."""
    out = []
    for block in re.findall(r"(?is)<style.*?>(.*?)</style>", raw):
        for _, val in CONTENT_CSS.findall(block):
            val = val.strip()
            if val and val not in ("", " ", "\\201C", "\\201D"):
                out.append(val)
    return out


# Characters that let a value render normally to a human while defeating naive
# pattern matching: bidi overrides, zero-width joiners, soft hyphens, BOM.
INVISIBLE = dict.fromkeys(map(ord,
    "\u200b\u200c\u200d\u2060\ufeff\u00ad"
    "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"), None)


def normalize_text(t):
    """NFKC folds full-width digits and symbols to ASCII, so U+FF19 U+FF05
    ("９％") is seen as "9%". Invisible/bidi characters are stripped
    outright rather than preserved."""
    return unicodedata.normalize("NFKC", t.translate(INVISIBLE))


def hiding_selectors(raw):
    """Collect class/id selectors whose rules hide content."""
    classes, ids = set(), set()
    for block in re.findall(r"(?is)<style.*?>(.*?)</style>", raw):
        for sel in HIDING_CSS.findall(block):
            for part in sel.split(","):
                part = part.strip()
                for c in re.findall(r"\.([A-Za-z0-9_-]+)", part):
                    classes.add(c)
                for i in re.findall(r"#([A-Za-z0-9_-]+)", part):
                    ids.add(i)
    return classes, ids


def extract(path):
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    classes, ids = hiding_selectors(raw)
    p = VisibleText(hidden_classes=classes, hidden_ids=ids)
    p.feed(raw)
    parts = p.parts + ["\n" + c for c in generated_content(raw)]
    return normalize_text("".join(parts))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: visible_text.py <file.html>", file=sys.stderr)
        sys.exit(2)
    sys.stdout.write(extract(sys.argv[1]))
