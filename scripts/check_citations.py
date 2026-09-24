#!/usr/bin/env python3
"""
check_citations.py — enforce that every requirement-like value in a report cites a
fact ID from knowledge-base/scenario-facts.yml.

WHY THIS EXISTS
An earlier gate accepted a bare "(given)" marker written by the report itself. A red
team proved you could append "(given)" to a fabricated requirement and pass. A claim
is not sourced because the document says so; it is sourced because it matches an
entry in an external manifest.

It also reads only VISIBLE text. The earlier grep-based gate could be satisfied by
keywords hidden in HTML comments, <script>, <style>, display:none, or hidden
attributes — all proven bypasses.

USAGE
    python3 scripts/check_citations.py docs/Foo_Solution.html --scenario customer-360
    python3 scripts/check_citations.py docs/Foo_Solution.html          # auto-detect

CITATION SYNTAX (in the HTML)
    15 minutes <cite data-fact="C360-F03">given</cite>
    ... or simply the bare token [C360-F03] anywhere in the same sentence.

EXIT CODES
    0 = all requirement values cited or properly scoped to Open Questions
    1 = uncited or mis-cited values found
    2 = usage / configuration error (never silently "pass")
"""

import argparse
import os
import re
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MANIFEST = os.path.join(REPO, "knowledge-base", "scenario-facts.yml")

HIDDEN_TAGS = {"script", "style", "template", "noscript"}


# ---------------------------------------------------------------------------
# Visible-text extraction (closes the comment / hidden-element bypasses)
# ---------------------------------------------------------------------------
class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in HIDDEN_TAGS:
            self.skip_depth += 1
            return
        style = (a.get("style") or "").replace(" ", "").lower()
        if "hidden" in a or a.get("aria-hidden") == "true" \
           or "display:none" in style or "visibility:hidden" in style:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag in HIDDEN_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        # Comments are never delivered to handle_data, so they are excluded by design.
        if self.skip_depth == 0 and self.hidden_depth == 0:
            self.parts.append(data)

    def text(self):
        return re.sub(r"[ \t]+", " ", "".join(self.parts))


def visible_text(path):
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    # Mermaid diagram bodies ARE requirements text and must be included. A fabricated
    # "99%" once survived precisely because diagrams were excluded as noise.
    p = VisibleText()
    p.feed(raw)
    return p.text()


# ---------------------------------------------------------------------------
# Minimal manifest reader (no PyYAML dependency — CI must not silently skip)
# ---------------------------------------------------------------------------
def load_manifest(path):
    if not os.path.exists(path):
        print(f"ERROR: manifest not found: {path}", file=sys.stderr)
        sys.exit(2)
    scenarios, cur, section = {}, None, None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s.startswith("- id:") and line.startswith("  - id:"):
                cur = s.split("id:", 1)[1].strip()
                scenarios[cur] = {"facts": set(), "examples": set(), "unknowns": set()}
                section = None
            elif s in ("facts:", "teaching_examples:", "unknowns:"):
                section = {"facts:": "facts",
                           "teaching_examples:": "examples",
                           "unknowns:": "unknowns"}[s]
            elif s.startswith("- id:") and cur and section:
                scenarios[cur][section].add(s.split("id:", 1)[1].strip())
    if not scenarios:
        print("ERROR: manifest parsed but contained no scenarios", file=sys.stderr)
        sys.exit(2)
    return scenarios


# ---------------------------------------------------------------------------
# What counts as a requirement-like value
# ---------------------------------------------------------------------------
VALUE_RE = re.compile(
    r"""(
        \d+(?:\.\d+)?\s?%                               |  # 99%, 99.9 %
        \bp9[0-9]\b                                      |  # p95, p99
        \d+(?:\.\d+)?\s?(?:ms|millisecond|sec|second|minute|min|hour|day|week|month|year)s?\b |
        \b\d+(?:[.,]\d+)?\s?[KMB]?\s?(?:events?|records?|rows?|msg|messages)\s*/\s*(?:sec|second|min|hour)\b |
        \$\s?\d+(?:[.,]\d+)?\s?[KMB]?\b                  |  # $2M
        \b(?:four|five|six)\s+nines\b                    |
        \bsub-?second\b                                  |
        \bzero\s+(?:downtime|disruption|data\s+loss|event\s+loss|loss)\b |
        \bno\s+(?:downtime|data\s+loss)\b                |
        \bnever\s+fail\w*\b                              |
        \b100\s?%\b
    )""",
    re.VERBOSE | re.IGNORECASE,
)

CITE_RE = re.compile(r"\b([A-Z0-9]{3,6}-(?:F|U|X)\d{2})\b")

# How far after a value we look for its citation.
CITE_WINDOW = 60

# Phrases that scope a value as explicitly unsourced rather than asserted.
UNSOURCED_RE = re.compile(
    r"not specified|not given|was not|open question|assumption|"
    r"unknown|to be confirmed|tbd|fabricat|removed|illustrativ|example",
    re.IGNORECASE,
)


def sentences(text):
    for chunk in re.split(r"(?<=[.!?])\s+|\n+|(?<=\])\s{2,}", text):
        c = chunk.strip()
        if c:
            yield c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--scenario", help="scenario id from the manifest")
    ap.add_argument("--manifest", default=MANIFEST)
    args = ap.parse_args()

    scenarios = load_manifest(args.manifest)
    total_fail = 0

    for path in args.files:
        if not os.path.exists(path):
            print(f"ERROR: no such file: {path}", file=sys.stderr)
            sys.exit(2)

        text = visible_text(path)

        sid = args.scenario
        if not sid:
            base = os.path.basename(path).lower()
            if "customer360" in base or "customer_360" in base:
                sid = "customer-360"
            elif "retail" in base or "iot" in base:
                sid = "retail-iot"
        if sid not in scenarios:
            print(f"ERROR: cannot determine scenario for {path}. "
                  f"Pass --scenario <{'|'.join(scenarios)}>", file=sys.stderr)
            sys.exit(2)

        facts = scenarios[sid]["facts"]
        examples = scenarios[sid]["examples"]
        unknowns = scenarios[sid]["unknowns"]
        valid = facts | unknowns

        print(f"\n=== {path}  (scenario: {sid}) ===")
        fails, ok, scoped = [], 0, 0

        for sent in sentences(text):
            matches = list(VALUE_RE.finditer(sent))
            if not matches:
                continue
            cites = set(CITE_RE.findall(sent))

            sentence_scoped = bool(UNSOURCED_RE.search(sent))

            bad_examples = cites & examples
            if bad_examples and not sentence_scoped:
                # Citing a teaching example as if it were a scenario fact.
                fails.append((sent, [m.group(0) for m in matches],
                              f"cites TEACHING EXAMPLE {sorted(bad_examples)} as a scenario fact"))
                continue
            if bad_examples and sentence_scoped:
                # Legitimate: the sentence names the example in order to DISCLAIM it
                # ("the course uses X illustratively; it is not a requirement here").
                scoped += len(matches)
                continue

            unknown_ids = cites - valid - examples
            if unknown_ids:
                fails.append((sent, [m.group(0) for m in matches],
                              f"cites unknown id(s) {sorted(unknown_ids)} not in the manifest"))
                continue

            # Each value needs its OWN nearby citation. A single citation must not
            # launder an entire sentence: "50K events/sec [F02] ... zero event loss"
            # previously passed because one sibling value was cited.
            for m in matches:
                window = sent[m.end():m.end() + CITE_WINDOW]
                near = set(CITE_RE.findall(window)) & valid
                if near:
                    ok += 1
                elif sentence_scoped:
                    scoped += 1
                else:
                    fails.append((sent, [m.group(0)],
                                  "value has no adjacent fact citation"))

        for sent, vals, why in fails:
            flat = re.sub(r"\s+", " ", sent).strip()
            print(f"  ✗ {why}")
            print(f"      values: {', '.join(set(v.strip() for v in vals))}")
            print(f"      text:   {flat[:150]}")

        print(f"  cited: {ok}   explicitly-unsourced: {scoped}   violations: {len(fails)}")
        total_fail += len(fails)

    print()
    if total_fail:
        print(f"CITATION CHECK FAILED — {total_fail} uncited requirement value(s).")
        print("Every number must cite a fact ID from knowledge-base/scenario-facts.yml,")
        print("or be explicitly marked as an assumption / open question.")
        return 1
    print("CITATION CHECK PASSED — all requirement values traced to the manifest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
