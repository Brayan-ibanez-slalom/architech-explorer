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

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MANIFEST = os.path.join(REPO, "knowledge-base", "scenario-facts.yml")

# Visible-text extraction is deliberately NOT reimplemented here.
# An earlier version kept a private copy, so every hardening fix applied to
# visible_text.py (CSS-class hiding, nested-hidden depth tracking, block-level
# separators) silently did not protect this gate. One extractor, one place.
sys.path.insert(0, HERE)
from visible_text import extract as _extract  # noqa: E402


def visible_text(path):
    # Mermaid diagram bodies ARE requirements text and must be included. A fabricated
    # "99%" once survived precisely because diagrams were excluded as noise.
    return re.sub(r"[ \t]+", " ", _extract(path))


# ---------------------------------------------------------------------------
# Minimal manifest reader (no PyYAML dependency — CI must not silently skip)
# ---------------------------------------------------------------------------
def load_manifest(path):
    """Parse ids AND their `matches:` patterns. A citation is only valid if the
    cited fact's pattern matches the value it is attached to — an earlier version
    accepted any nearby valid ID, so `100 ms [C360-F03]` passed even though F03
    means 15 minutes."""
    if not os.path.exists(path):
        print(f"ERROR: manifest not found: {path}", file=sys.stderr)
        sys.exit(2)
    scenarios, cur, section, fid = {}, None, None, None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            st = line.strip()
            if re.match(r"^  - id:", line):
                cur = st.split("id:", 1)[1].strip()
                scenarios[cur] = {"facts": set(), "examples": set(),
                                  "unknowns": set(), "matches": {}}
                section = None
            elif st in ("facts:", "teaching_examples:", "unknowns:"):
                section = {"facts:": "facts", "teaching_examples:": "examples",
                           "unknowns:": "unknowns"}[st]
            elif re.match(r"^      - id:", line) and cur and section:
                fid = st.split("id:", 1)[1].strip()
                scenarios[cur][section].add(fid)
            elif st.startswith("matches:") and cur and fid:
                pat = st.split("matches:", 1)[1].strip().strip('"').strip("'")
                if pat:
                    scenarios[cur]["matches"][fid] = pat
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
        \b100\s?%\b                                     |
        # --- added after red-team finding A: the grammar missed whole
        # classes of quantities that carry just as much requirement weight ---
        \b\d+\s?[\u2013\u2014-]\s?\d+\s+(?!objectives|ecosystems|scenarios|decisions|ASRs|constraints|alternatives|options|paragraphs|sentences|bullets)\w+ |  # ranges: 2-4 sources
        \b\d+\+\s*(?!objectives|ecosystems|scenarios|decisions|ASRs|constraints|alternatives|options|full|distinct)\w+ | # 4+ sources
        \b\d+\s?x\b                                     |  # 3x growth
        \b\d+(?:\.\d+)?\s?(?:[KMGTP]i?B|[KMGT]B/s|GB/s|MB/s|TB)\b |  # 2 GB/s, 5 TB
        \bwithin\s+\d+\s+\w+                            |  # within 2 years
        \b\d+\s+(?:engineers?|people|FTEs?|staff|developers?|analysts?|teams?) |
        \b\d+\s+(?:source\s+systems?|sources?|systems?|regions?|zones?|replicas?|nodes?|clusters?)\b |
        \bQ[1-4]\s?(?:20\d\d)?\b                        |  # Q3 2026
        \b20\d\d\b                                         # bare years
    )""",
    re.VERBOSE | re.IGNORECASE,
)

CITE_RE = re.compile(r"\b([A-Z0-9]{3,6}-(?:F|U|X)\d{2})\b")

# How far after a value we look for its citation.
CITE_WINDOW = 40  # citation must sit close after the value, not anywhere in the sentence

# Phrases that scope a value as explicitly unsourced rather than asserted.
OPENQ_RE = re.compile(r"open question|not specified|not given|unknown|to be confirmed|\bTBD\b", re.IGNORECASE)

UNSOURCED_RE = re.compile(
    # Deliberately NARROW. An earlier version scoped a whole sentence if it merely
    # contained the word "example" or "assumption", so a hard fabricated requirement
    # could be smuggled in by writing "Requirement example: ...". Only explicit,
    # deliberate markers count now.
    r"\(assumption\)|\(not given\)|\(unsourced\)|"
    r"not specified|was not specified|was not given|not stated in the scenario|"
    r"see Open Questions|is an open question|remains an open question|"
    r"illustrative measure|is not a requirement|to be confirmed|\bTBD\b|"
    r"fabricated|were removed",
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
        patterns = scenarios[sid].get("matches", {})

        # Sentence splitting loses section context, so locate the Open Questions
        # region by document offset and treat everything after it as open-question
        # scope. This is what makes -U## citations legal there and nowhere else.
        oq = re.search(r"Open Questions", text, re.IGNORECASE)
        oq_start = oq.start() if oq else len(text) + 1

        print(f"\n=== {path}  (scenario: {sid}) ===")
        fails, ok, scoped = [], 0, 0

        cursor = 0
        for sent in sentences(text):
            sent_at = text.find(sent, cursor)
            if sent_at >= 0:
                cursor = sent_at
            matches_ = list(VALUE_RE.finditer(sent))
            if not matches_:
                continue

            in_open_q = bool(OPENQ_RE.search(sent)) or cursor >= oq_start

            for m in matches_:
                val = m.group(0)
                # Citation must sit IMMEDIATELY after the value. A wide window let
                # one ID launder several unrelated values in the same sentence.
                window = sent[m.end():m.end() + CITE_WINDOW]
                ids = CITE_RE.findall(window)
                cid = ids[0] if ids else None

                if cid is None:
                    # Per-value opt-out only; a sentence-level keyword such as
                    # "example" previously scoped every value in the sentence.
                    if UNSOURCED_RE.search(sent[max(0, m.start() - 90):m.end() + 90]):
                        scoped += 1
                    else:
                        fails.append((sent, [val], "no citation immediately after value"))
                    continue

                if cid in examples:
                    if in_open_q or UNSOURCED_RE.search(sent):
                        scoped += 1
                    else:
                        fails.append((sent, [val],
                                      f"cites TEACHING EXAMPLE {cid} as a scenario fact"))
                    continue

                if cid in unknowns:
                    # Unknowns support open questions, never settled requirements.
                    if in_open_q or UNSOURCED_RE.search(sent):
                        scoped += 1
                    else:
                        fails.append((sent, [val],
                                      f"cites UNKNOWN {cid} outside an Open Questions context"))
                    continue

                if cid not in facts:
                    fails.append((sent, [val],
                                  f"cites unknown id {cid} not in the manifest"))
                    continue

                pat = patterns.get(cid)
                if pat and not re.search(pat, val, re.IGNORECASE):
                    fails.append((sent, [val],
                                  f"{cid} does not support this value "
                                  f"(expects /{pat}/)"))
                    continue

                ok += 1

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
