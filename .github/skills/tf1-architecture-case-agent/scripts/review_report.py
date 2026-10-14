#!/usr/bin/env python3
"""Mechanized slice of the Step-8 adversarial content self-review.

This gate automates the *checkable* parts of the self-review so a human (or a
fresh review agent) can spend their attention on the judgment calls. It does
NOT replace the judgment-based checks in SKILL.md step 8 (does the cited fact
actually say it? is a trade-off a genuine in-bounds tension? is an impact
rating honest?) — those still need eyes.

What it mechanizes
------------------
  1. Citation integrity, both ways. Every ``[NS-xxx]`` citation in a report
     must be defined in the facts manifest (ERROR if not). Every manifest fact
     ideally gets used (WARN if not — unused facts are a smell, not a bug).
  2. Single citation namespace. A second, never-defined namespace (the classic
     ``[PA-Uxx]`` dangling-id defect) is flagged. Any citation whose namespace
     prefix is absent from the manifest is reported.
  3. Discovery-question integrity. Every ``Qn`` referenced is defined, and
     (WARN) every defined ``Qn`` is referenced.
  4. Numeric-count heuristic. ``two/three/.. (a, b, c)`` where the spelled
     count disagrees with the parenthesised list length — the
     "two non-FHIR sources (HL7v2, X12, CSV)" self-contradiction.
  5. Cross-file consistency. The same citation id and the same ``Qn`` set
     should appear across HTML + workbook + checklist; ids present in one
     deliverable but missing from another are flagged (WARN).

Usage
-----
    python3 review_report.py --manifest validation-checklist.md \
        --report Solution.html [--also Workbook.md --also checklist.md]

Exit code is non-zero if any ERROR-level finding is raised, so it can gate a
pipeline the same way ``selftest.py`` does.
"""
import argparse
import re
import sys
from pathlib import Path

# A citation is a bracketed NAMESPACE-TOKEN, e.g. [PA-F18], [DX-A3].
CITE_RE = re.compile(r'\[([A-Z0-9]+)-([A-Za-z0-9]+)\]')
# A manifest may DEFINE ids bare (markdown/HTML table cell): | PA-F01 | ... |
BARE_DEF_RE = re.compile(r'(?:^|>|\|)\s*([A-Z0-9]+)-([A-Za-z0-9]*\d[A-Za-z0-9]*)\s*(?:<|\|)')
QREF_RE = re.compile(r'\bQ(\d+)\b')
# A placeholder like [PA-Fxx] / [XX-nn] is an explanatory key, not a real id.
PLACEHOLDER_RE = re.compile(r'(x{2,}|nn|yy|\bN\b)', re.IGNORECASE)
NUM_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
}
# "two non-FHIR sources (HL7v2, X12, CSV)" -> ('two', 'HL7v2, X12, CSV').
# Require a comma inside the parens so a non-list aside like "(resources and
# fields)" is not mistaken for an enumeration.
COUNT_LIST_RE = re.compile(
    r'\b(' + '|'.join(NUM_WORDS) + r')\b[^.()\n]{0,60}?\(([^()\n]*,[^()\n]*)\)',
    re.IGNORECASE,
)


class Findings:
    def __init__(self):
        self.errors = []
        self.warns = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warns.append(msg)

    def report(self):
        for m in self.warns:
            print(f"  WARN  {m}")
        for m in self.errors:
            print(f"  ERROR {m}")
        print(
            f"\nreview_report: {len(self.errors)} error(s), "
            f"{len(self.warns)} warning(s)."
        )
        return 1 if self.errors else 0


def read(path):
    return Path(path).read_text(encoding='utf-8', errors='replace')


def citations(text):
    """Return set of (namespace, token) bracketed citations, excluding
    explanatory placeholders like [PA-Fxx]."""
    out = set()
    for ns, tok in CITE_RE.findall(text):
        if PLACEHOLDER_RE.search(tok) or PLACEHOLDER_RE.search(ns):
            continue
        out.add((ns, tok))
    return out


def manifest_defined(text):
    """Ids the manifest DEFINES. Citations in a facts manifest are usually
    written bare in a table cell (``| PA-F01 | ... |``), not bracketed, so
    accept both the bracketed and the bare table-cell forms."""
    out = set(citations(text))
    for ns, tok in BARE_DEF_RE.findall(text):
        out.add((ns, tok))
    return out


def qrefs(text):
    return set(int(n) for n in QREF_RE.findall(text))


def qdefs(text):
    """A discovery question is DEFINED when it stands alone in a table cell
    (``<td>Q4</td>`` or ``| Q4 |``) or is introduced as ``Q4:`` / ``Q4 -``."""
    out = set()
    for m in re.finditer(r'(?:^|>|\|)\s*Q(\d+)\s*(?:<|\|)', text):
        out.add(int(m.group(1)))
    for m in re.finditer(r'\bQ(\d+)\s*[:\-\u2013\u2014]', text):
        out.add(int(m.group(1)))
    return out


def check_citations(report_text, manifest_text, f):
    defined = manifest_defined(manifest_text)
    used = citations(report_text)
    defined_ns = {ns for ns, _ in defined}

    for ns, tok in sorted(used):
        if (ns, tok) not in defined:
            if ns not in defined_ns:
                f.error(
                    f"citation [{ns}-{tok}] uses namespace '{ns}-' that the "
                    f"manifest never defines (dangling second namespace?)"
                )
            else:
                f.error(f"citation [{ns}-{tok}] is not defined in the manifest")
    for ns, tok in sorted(defined):
        if (ns, tok) not in used:
            f.warn(f"manifest fact [{ns}-{tok}] is defined but never cited")


def check_questions(report_text, manifest_text, f):
    both = report_text + "\n" + manifest_text
    defined = qdefs(both)
    referenced = qrefs(report_text)
    for q in sorted(referenced - defined):
        f.error(f"discovery question Q{q} is referenced but never defined")
    for q in sorted(defined - referenced):
        f.warn(f"discovery question Q{q} is defined but never referenced")


def check_counts(report_text, f):
    clause_words = re.compile(
        r'\b(if|when|because|since|unless|while|so that|which|whether|'
        r'although|though|after|before)\b', re.IGNORECASE)
    for m in COUNT_LIST_RE.finditer(report_text):
        word, listing = m.group(1).lower(), m.group(2)
        # A clause in the parens (…, if no source onboards) is prose, not a list.
        if clause_words.search(listing):
            continue
        parts = [p for p in re.split(r',|;', listing) if p.strip()]
        if len(parts) < 2:
            continue
        spelled = NUM_WORDS[word]
        if spelled != len(parts):
            snippet = m.group(0).strip()
            f.warn(
                f"count mismatch: \"{snippet[:70]}\" says '{word}' "
                f"({spelled}) but lists {len(parts)} items"
            )


def check_cross_file(files, f):
    """files: list of (label, text) for the DELIVERABLES only (not the
    manifest). Flag citation ids present in some but not all deliverables."""
    if len(files) < 2:
        return
    cite_sets = {lab: citations(t) for lab, t in files}
    all_cites = set().union(*cite_sets.values())
    for ns, tok in sorted(all_cites):
        present = [lab for lab, s in cite_sets.items() if (ns, tok) in s]
        missing = [lab for lab, _ in files if lab not in present]
        if missing and len(present) == len(files) - len(missing) and len(present) > 1:
            f.warn(
                f"[{ns}-{tok}] appears in {present} but not in {missing} "
                f"(cross-file consistency)"
            )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--manifest', required=True,
                    help='facts manifest / validation checklist that DEFINES citations')
    ap.add_argument('--report', required=True,
                    help='primary deliverable (HTML or Markdown) to check')
    ap.add_argument('--also', action='append', default=[],
                    help='additional deliverable(s) for cross-file consistency')
    args = ap.parse_args(argv)

    manifest_text = read(args.manifest)
    report_text = read(args.report)

    f = Findings()
    print(f"review_report: manifest={args.manifest} report={args.report}")
    check_citations(report_text, manifest_text, f)
    check_questions(report_text, manifest_text, f)
    check_counts(report_text, f)

    cross = [(Path(args.report).name, report_text)]
    for extra in args.also:
        cross.append((Path(extra).name, read(extra)))
    check_cross_file(cross, f)

    rc = f.report()
    if rc == 0:
        print("REVIEW_REPORT PASSED (mechanical checks only — judgment checks still required)")
    return rc


if __name__ == '__main__':
    sys.exit(main())
