#!/usr/bin/env python3
"""Adversarial regression suite for the citation gate.

Every case here is an attack that ONCE WORKED, or a false positive that once
fired. Three rounds of independent red-team review produced this list. Run it
before trusting any change to check_citations.py or visible_text.py:

    python3 scripts/test_gate.py

Exit 0 = all cases behave correctly. Exit 1 = a regression.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_citations.py")

# (name, html, scenario) -- the gate MUST reject these.
MUST_BLOCK = [
    ("wrong fact ID", "<p>lookup must complete in 100 ms [C360-F03].</p>", "customer-360"),
    ("one ID launders many values",
     "<p>Requirement: 100 ms reads, 200 ms writes, $2M savings [C360-F03].</p>", "customer-360"),
    ("unknown cited as requirement",
     "<p>lookup must complete in 100 ms [C360-U01].</p>", "customer-360"),
    ("'example' sentence escape hatch",
     "<p>Requirement example: complete in 100 ms always.</p>", "customer-360"),
    ("teaching example cited as fact",
     "<p>must guarantee zero event loss [RIOT-X01].</p>", "retail-iot"),
    ("HTML comment stuffing",
     "<!-- 100 ms --><p>Reads must finish in 100 ms.</p>", "customer-360"),
    ("scaled count uncited", "<p>We must serve 20M customers daily.</p>", "customer-360"),
    ("daily rate uncited", "<p>Ingest 5M interactions/day at peak.</p>", "customer-360"),
    ("clock time uncited", "<p>Dashboards must be ready by 7 AM sharp.</p>", "customer-360"),
    ("site count uncited", "<p>Must cover 500 stores nationwide.</p>", "retail-iot"),
    ("full-width digits", "<p>Uptime of \uff19\uff19\uff05 is required.</p>", "customer-360"),
    ("RTL override char", "<p>Uptime of 99\u202e% is required.</p>", "customer-360"),
    ("zero-width split value", "<p>Uptime of 9\u200b9% is required.</p>", "customer-360"),
    ("value written in words",
     "<p>Must sustain ninety-nine percent availability.</p>", "customer-360"),
    ("CSS ::before content injection",
     '<style>.f::before{content:"99% availability"}</style><div class="f"></div>', "customer-360"),
    ("semantic laundering (right number, wrong subject)",
     "<p>The data retention period for the archive tier is set to 15 minutes "
     "[C360-F03] before deletion.</p>", "customer-360"),
]

# The gate MUST NOT fire on these. A gate that cries wolf gets overridden,
# which is worse than the gap it closes.
MUST_ALLOW = [
    ("copyright footer", "<p>Copyright 2026 Slalom. All rights reserved.</p>", "customer-360"),
    ("changelog quarter reference",
     "<p>Changelog entry from the Q3 2026 revision of this document.</p>", "customer-360"),
]


def run(html, scenario):
    fd, path = tempfile.mkstemp(suffix=".html")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(html)
        return subprocess.run([sys.executable, CHECKER, path, "--scenario", scenario],
                              capture_output=True).returncode
    finally:
        os.unlink(path)


def main():
    bad = 0
    print("Adversarial regression suite\n")
    for name, html, scen in MUST_BLOCK:
        good = run(html, scen) != 0
        print(f"  {'ok  ' if good else 'FAIL'} block  {name}")
        bad += 0 if good else 1
    for name, html, scen in MUST_ALLOW:
        good = run(html, scen) == 0
        print(f"  {'ok  ' if good else 'FAIL'} allow  {name}")
        bad += 0 if good else 1

    total = len(MUST_BLOCK) + len(MUST_ALLOW)
    print(f"\n{total - bad}/{total} cases correct")
    if bad:
        print("REGRESSION: the gate no longer behaves as verified.")
        return 1
    print("All adversarial cases behave as verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
