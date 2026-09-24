#!/usr/bin/env python3
"""Decision-quality check.

Three rounds of independent review all landed on the same finding:

    "the architecture conclusions are the same conclusions with fact IDs
     appended"

Citation checks prove a number came from the source. They prove nothing about
whether a DECISION was actually reasoned. A report could pass every other gate
while every trade-off reads "higher cost vs better capability".

This check requires each decision to expose the fields that make a choice
reviewable. It enforces that the fields EXIST and are non-trivial. It cannot
judge whether they are true or wise - only a human or an independent reviewer
can. That limitation is the point of the warning printed at the end.
"""
import re
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from visible_text import extract  # noqa: E402

REQUIRED = [
    ("rejected alternative", r"rejected alternative|alternative considered|option rejected|instead of"),
    ("why the alternative is viable", r"genuinely viable|is viable|credible architecture|not a straw man|could also meet"),
    ("what is sacrificed", r"sacrific|gives up|at the cost of|loses|downside|weaker"),
    ("what is gained", r"gains?|in exchange for|benefit|buys us|advantage"),
    ("reversal condition", r"revers|revisit this|would change this|re-?open this|if .{0,60}(then )?(move|switch|adopt)"),
]

# A trade-off made only of these generic words is not a trade-off.
VACUOUS = re.compile(
    r"^\s*trade-?off:?\s*(higher|increased|more|additional)\s+\w+\s+"
    r"(vs\.?|versus|against)\s+\w+(\s+\w+){0,3}\.?\s*$", re.IGNORECASE)


def split_decisions(text):
    parts = re.split(r"(?im)^\s*Decision\s+\d+\s*[—\-–:]", text)
    return [p for p in parts[1:] if p.strip()]


def main():
    files = sys.argv[1:]
    if not files:
        print("usage: check_decisions.py <report.html> [...]", file=sys.stderr)
        return 2

    total_fail = 0
    for path in files:
        text = extract(path)
        decisions = split_decisions(text)
        print(f"\n=== {path} ===")
        if not decisions:
            print("  ! no 'Decision N —' blocks found; cannot assess decision quality")
            total_fail += 1
            continue

        for i, body in enumerate(decisions, 1):
            head = " ".join(body.split())[:60]
            body_l = body.lower()
            missing = [label for label, pat in REQUIRED
                       if not re.search(pat, body_l, re.IGNORECASE)]
            vacuous = [ln.strip() for ln in body.splitlines() if VACUOUS.match(ln)]

            if not missing and not vacuous:
                print(f"  ok   Decision {i}: {head}...")
                continue
            total_fail += 1
            print(f"  FAIL Decision {i}: {head}...")
            for m in missing:
                print(f"         missing: {m}")
            for v in vacuous:
                print(f"         vacuous trade-off: {v[:80]}")

    print()
    if total_fail:
        print(f"DECISION QUALITY: {total_fail} decision(s) are not reviewable.")
        print("A decision is reviewable only if a reader can tell what was rejected,")
        print("why that option was credible, what was given up, and what would")
        print("reverse the choice.")
        return 1
    print("DECISION QUALITY: every decision exposes the reviewable fields.")
    print("NOTE: this proves the fields are PRESENT and non-generic. It does not")
    print("prove the reasoning is correct. Only a reviewer can judge that.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
