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
import sys
from html.parser import HTMLParser

HIDDEN_TAGS = {"script", "style", "template", "noscript"}


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip, self.hidden = [], 0, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in HIDDEN_TAGS:
            self.skip += 1
            return
        style = (a.get("style") or "").replace(" ", "").lower()
        if "hidden" in a or a.get("aria-hidden") == "true" \
           or "display:none" in style or "visibility:hidden" in style:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in HIDDEN_TAGS and self.skip:
            self.skip -= 1
        elif self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.skip and not self.hidden:
            self.parts.append(data)


def extract(path):
    p = VisibleText()
    with open(path, encoding="utf-8") as fh:
        p.feed(fh.read())
    return "".join(p.parts)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: visible_text.py <file.html>", file=sys.stderr)
        sys.exit(2)
    sys.stdout.write(extract(sys.argv[1]))
