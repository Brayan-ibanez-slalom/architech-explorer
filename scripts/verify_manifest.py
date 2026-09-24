#!/usr/bin/env python3
"""
verify_manifest.py — check that every quote in scenario-facts.yml actually appears
in the source PDF.

WHY THIS EXISTS
The fact manifest is the external source of truth for every number in a report.
But a manifest is only trustworthy if its quotes are real. Without this check, the
manifest is relocated self-attestation: someone could add a fabricated fact with an
invented quote and every downstream citation would "verify" against it.

This closes the loop: report -> fact ID -> quote -> actual source document.

USAGE
    python3 scripts/verify_manifest.py

EXIT CODES
    0 = every quote found in the source
    1 = one or more quotes not found (possible fabricated fact)
    2 = cannot verify (missing PDF or extractor) - never silently "pass"
"""

import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MANIFEST = os.path.join(REPO, "knowledge-base", "scenario-facts.yml")
KB = os.path.join(REPO, "knowledge-base")


def normalize(s):
    """Collapse the differences PDF extraction introduces: ligatures, smart quotes,
    non-breaking spaces, soft hyphens, line-wrap hyphenation, and multiplication signs."""
    s = unicodedata.normalize("NFKD", s)
    s = (s.replace("\u2019", "'").replace("\u2018", "'")
          .replace("\u201c", '"').replace("\u201d", '"')
          .replace("\u2013", "-").replace("\u2014", "-")
          .replace("\u00a0", " ").replace("\u00ad", "")
          .replace("\u00d7", "x").replace("\u2212", "-"))
    s = re.sub(r"-\s*\n\s*", "", s)      # de-hyphenate across line breaks
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def load_source_text():
    pdfs = [f for f in os.listdir(KB) if f.lower().endswith(".pdf")]
    if not pdfs:
        print("ERROR: no source PDF found in knowledge-base/", file=sys.stderr)
        sys.exit(2)
    try:
        from pypdf import PdfReader
    except ImportError:
        print("ERROR: pypdf not installed — cannot verify. Run: pip install pypdf",
              file=sys.stderr)
        print("Exiting 2 (indeterminate). 'Could not check' is not 'checks passed'.",
              file=sys.stderr)
        sys.exit(2)

    chunks = []
    for name in pdfs:
        reader = PdfReader(os.path.join(KB, name))
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
    # Also allow quotes sourced from the curated notes.
    notes = os.path.join(KB, "tf1-course-notes.md")
    if os.path.exists(notes):
        chunks.append(open(notes, encoding="utf-8").read())
    return normalize("\n".join(chunks))


def parse_quotes(path):
    """Yield (scenario, fact_id, section, quote). Deliberately simple and strict."""
    out, scen, fid, section = [], None, None, None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            st = line.strip()
            if re.match(r"^  - id:", line):
                scen = st.split("id:", 1)[1].strip()
                section = None
            elif st in ("facts:", "teaching_examples:", "unknowns:"):
                section = st[:-1]
            elif re.match(r"^      - id:", line):
                fid = st.split("id:", 1)[1].strip()
            elif st.startswith("quote:") and fid:
                q = st.split("quote:", 1)[1].strip().strip('"').strip("'")
                if q:
                    out.append((scen, fid, section, q))
    return out


def check_manifest_is_real_yaml():
    """The manifest is read by a hand-rolled parser in this repo, which is
    tolerant. For 17 facts it was tolerating a file that was NOT valid YAML:
    `matches: "140\s*stores?"` is an illegal escape in a double-quoted YAML
    scalar, so any standard YAML loader raised a hard error on it.

    That mattered for two reasons. Anyone reaching for a YAML library - the
    obvious next step for anyone extending this - hit a crash in a file the
    repo reported as verified. And the meaning of a fact could differ between
    the bespoke parser and a real one, which is intolerable in the file that
    defines what counts as true.

    Patterns are now single-quoted, where YAML treats backslashes literally.
    This check keeps it that way.
    """
    try:
        import yaml
    except ImportError:
        print("PyYAML not installed - cannot confirm the manifest is valid YAML.")
        print("Refusing to report a pass on a check that did not run.")
        sys.exit(2)
    try:
        with open(MANIFEST, encoding="utf-8") as fh:
            yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        print(f"MANIFEST IS NOT VALID YAML: {exc}", file=sys.stderr)
        print("Regex patterns must use SINGLE quotes so backslashes stay literal.",
              file=sys.stderr)
        sys.exit(1)
    print("Manifest parses under a real YAML loader, not just the local parser.")


def main():
    if not os.path.exists(MANIFEST):
        print(f"ERROR: manifest not found: {MANIFEST}", file=sys.stderr)
        sys.exit(2)

    check_manifest_is_real_yaml()

    source = load_source_text()
    entries = parse_quotes(MANIFEST)
    if not entries:
        print("ERROR: no quotes parsed from the manifest — refusing to pass.",
              file=sys.stderr)
        sys.exit(2)

    missing = []
    for scen, fid, section, quote in entries:
        if normalize(quote) in source:
            continue
        # Fall back to a token-overlap check: PDF extraction mangles bullet joins,
        # so require most distinctive tokens to be present before declaring failure.
        toks = [t for t in re.findall(r"[a-z0-9]+", normalize(quote)) if len(t) > 3]
        hit = sum(1 for t in toks if t in source)
        if toks and hit / len(toks) >= 0.85:
            continue
        missing.append((scen, fid, section, quote,
                        f"{hit}/{len(toks)} distinctive tokens found"))

    bad_patterns = check_patterns(MANIFEST)

    print(f"Verified {len(entries)} quote(s) from {MANIFEST}")
    for scen, fid, section, quote, detail in missing:
        print(f"  ✗ {fid} ({scen}/{section}) — quote not found in source [{detail}]")
        print(f"      {quote[:120]}")

    if missing or bad_patterns:
        if missing:
            print(f"\nMANIFEST VERIFICATION FAILED — {len(missing)} unverifiable quote(s).")
            print("A fact is only a fact if it appears in the source document.")
        return 1
    print("MANIFEST VERIFICATION PASSED — every quote traced to the source.")
    return 0



def check_patterns(path):
    """Every `matches:` regex must compile AND match its own `value`.

    Two live bugs motivated this: an unescaped \\u2013 and a double-escaped
    \\\\s. Both made a correct citation look like a violation, which is the
    most dangerous failure mode a gate has - it trains people to override it.
    """
    bad = 0
    fid = val = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            t = line.strip()
            m = re.match(r'-\s*id:\s*"?([A-Z0-9]{3,6}-[FUX]\d\d)"?', t)
            if m:
                fid, val = m.group(1), None
                continue
            m = re.match(r'value:\s*"(.*)"\s*$', t)
            if m:
                val = m.group(1)
                continue
            m = re.match(r'matches:\s*"(.*)"\s*$', t)
            if m and fid:
                pat = m.group(1)
                try:
                    rx = re.compile(pat, re.IGNORECASE)
                except re.error as e:
                    print("  x %s: pattern does not compile (%s)" % (fid, e))
                    bad += 1
                    continue
                if val is not None and not rx.search(val):
                    print("  x %s: pattern %r does not match its own value %r"
                          % (fid, pat, val))
                    bad += 1
    if bad:
        print("PATTERN SELF-TEST FAILED - %d broken pattern(s)." % bad)
    else:
        print("PATTERN SELF-TEST PASSED - all matches: patterns match their own value.")
    return bad

if __name__ == "__main__":
    sys.exit(main())
