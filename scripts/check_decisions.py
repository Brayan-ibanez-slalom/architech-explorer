#!/usr/bin/env python3
"""Decision-quality check.

Three rounds of independent review landed on the same finding: the reports were
"the same conclusions with fact IDs appended". Citation checks prove a number
came from the source; they prove nothing about whether a DECISION was reasoned.

A FOURTH round then broke the first version of this checker. It matched bare
keywords, so all of these passed:

    "There is no rejected alternative. Nothing is viable.
     The choice makes no sacrifice and provides no gain.
     Never revisit this decision."          <- negation passed
    "Rejected alternative: the moon. It is viable because cheese."  <- nonsense
    "Rejected alternative. Instead of."      <- empty labels

This version therefore requires each field to be a LABELLED block with
substantive, non-negated content, and requires the two fields the first
version forgot entirely: chosen approach and unresolved fact.

What it still cannot do: judge whether the content is TRUE or WISE. It raises
the floor; it does not certify reasoning. Only a reviewer can do that, and the
final message says so.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from visible_text import extract  # noqa: E402

MIN_WORDS = 12  # a field shorter than this is a label, not an argument

# Each field must appear as an explicit label. Matching a bare keyword anywhere
# in the block was the flaw that let unlabelled prose pass.
FIELDS = [
    ("chosen approach",
     r"chosen approach|provisional direction|decision status|we will|adopt a|adopt the|use a |use the |design the |split into"),
    ("rejected alternative",
     r"rejected alternative|alternative rejected|option rejected|instead of(?! )"),
    ("why the alternative is viable",
     r"why (?:that|the) (?:rejected )?alternative is (?:genuinely )?viable|why that option is credible|is genuinely viable"),
    ("what is sacrificed",
     r"what (?:is|the chosen approach) sacrific\w*|sacrificed\.|sacrifice[sd]?\b"),
    ("what is gained",
     r"what (?:is|the chosen approach) gain\w*|gained\.|\bgains?\b"),
    ("reversal condition",
     r"reversal condition|revisit this|would reverse|revisit and|would flip"),
    ("unresolved fact",
     r"unresolved fact|unresolved input|missing input|open question that could"),
]

# Polarity guards. The checker cannot parse meaning, but it can refuse text that
# explicitly denies the field it claims to provide.
NEGATED = re.compile(
    r"\b(?:there is |there are )?(?:no|not any|nothing|none)\s+"
    r"(?:rejected\s+)?(?:alternative|alternatives|sacrifice|sacrifices|gain|gains|"
    r"trade-?offs?|unresolved|viable\s+option)\b"
    r"|\bnever\s+revisit\b"
    r"|\bnothing\s+is\s+viable\b"
    r"|\bmakes?\s+no\s+sacrifice\b"
    r"|\bprovides?\s+no\s+gain\b",
    re.IGNORECASE,
)

VACUOUS = re.compile(
    r"^\s*trade-?off:?\s*(higher|increased|more|additional)\s+\w+\s+"
    r"(vs\.?|versus|against)\s+\w+(\s+\w+){0,3}\.?\s*$", re.IGNORECASE)

FACT_RE = re.compile(r"\b[A-Z0-9]{3,6}-F\d{2}\b")
UNKNOWN_RE = re.compile(r"\b[A-Z0-9]{3,6}-U\d{2}\b")

# Matches "Decision 3 —" and sub-decisions "3a." / "3b." so that bundled
# independent choices are checked separately rather than covering for each other.
SPLIT_RE = re.compile(r"(?im)^\s*(?:Decision\s+\d+\s*[—\-–:]|\d+[a-z]\.\s+)")


def field_span(body, pat, own=None):
    """Return the text belonging to a labelled field: from the label to the next
    label or paragraph break. Content is measured, not merely detected."""
    m = re.search(pat, body, re.IGNORECASE)
    if not m:
        return None
    tail = body[m.end():]
    stop = len(tail)
    for oname, other in FIELDS:
        if oname == own:
            continue  # a field's own alternate wording must not truncate itself
        o = re.search(other, tail, re.IGNORECASE)
        if o and 0 < o.start() < stop:
            stop = o.start()
    nl = tail.find("\n\n")
    if 0 < nl < stop:
        stop = nl
    return tail[:stop].strip(" .:—-\n\t")


def check_block(label, body, strict_citations=True):
    problems = []
    for name, pat in FIELDS:
        span = field_span(body, pat, own=name)
        if span is None:
            problems.append(f"missing: {name}")
            continue
        words = len(re.findall(r"[A-Za-z][A-Za-z'-]+", span))
        if words < MIN_WORDS:
            problems.append(f"too thin ({words} words, need {MIN_WORDS}): {name}")
        if NEGATED.search(span):
            problems.append(f"negated (states the field does not exist): {name}")

    if NEGATED.search(body):
        problems.append("block contains an explicit denial of a required field")
    for ln in body.splitlines():
        if VACUOUS.match(ln):
            problems.append(f"vacuous trade-off: {ln.strip()[:70]}")

    if strict_citations:
        unresolved = field_span(body, FIELDS[-1][1], own=FIELDS[-1][0]) or ""
        if not UNKNOWN_RE.search(unresolved):
            problems.append("unresolved fact does not cite a -U## unknown")
        gain = field_span(body, FIELDS[4][1], own=FIELDS[4][0]) or ""
        if not FACT_RE.search(gain):
            problems.append("gain is not tied to a cited -F## requirement")
    return problems


def main():
    files = sys.argv[1:]
    if not files:
        print("usage: check_decisions.py <report.html> [...]", file=sys.stderr)
        return 2

    total = 0
    for path in files:
        text = extract(path)
        blocks = SPLIT_RE.split(text)[1:]
        blocks = [b for b in blocks if len(b.strip()) > 40]
        print(f"\n=== {path} ===")
        if not blocks:
            print("  !    no decision blocks found; cannot assess decision quality")
            total += 1
            continue
        for i, body in enumerate(blocks, 1):
            head = " ".join(body.split())[:58]
            problems = check_block(i, body)
            if not problems:
                print(f"  ok   Decision block {i}: {head}...")
                continue
            total += 1
            print(f"  FAIL Decision block {i}: {head}...")
            for p in problems:
                print(f"         {p}")

    print()
    if total:
        print(f"DECISION QUALITY: {total} decision block(s) are not reviewable.")
        print("A decision is reviewable only if a reader can tell what was rejected,")
        print("why that option was credible, what was given up, what was gained")
        print("against a cited requirement, and what would reverse the choice.")
        return 1
    print("DECISION QUALITY: every decision block carries labelled, substantive,")
    print("non-negated content in all seven fields.")
    print("NOTE: this proves the fields are PRESENT, SUBSTANTIVE and not self-")
    print("denying. It does NOT prove the reasoning is correct or wise. A fluent")
    print("author can still write plausible nonsense. Only a reviewer can judge that.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
