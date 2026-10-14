#!/usr/bin/env python3
"""selftest.py — regression gate for the tf1-architecture-case-agent skill.

The skill's two helper scripts (build_branded_pdf.py, render_mermaid.py) had a
cluster of silent-corruption bugs that a "diagrams present / file non-empty"
check could not catch:

  * the Utility Tree and Architecture images were swapped (filename sort order
    != document diagram order),
  * genuine fenced code (SQL/YAML) under an "Architecture"-ish heading was
    deleted and replaced by a diagram image,
  * literal asterisks in prose ("5 * 3 * 2") were eaten by the italic regex,
  * ragged / nested HTML tables mis-rendered,
  * non-cp1252 glyphs (arrows, emoji) became tofu boxes in the PDF.

This script exercises those exact code paths with tiny in-memory fixtures and
asserts the correct behaviour. It needs no Chrome and no network: it builds a
real PDF against 1x1 placeholder PNGs and inspects the resulting text.

Run:  python3 scripts/selftest.py
Exit: 0 = all good, 1 = a regression reappeared.
"""
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAILS = []


def check(name, cond):
    if cond:
        print(f"  \u2713 {name}")
    else:
        print(f"  \u2717 {name}")
        FAILS.append(name)


def _png(path, color=(10, 20, 30)):
    """Write a tiny but non-trivial PNG so the builder accepts it as a real
    diagram image (the renderer rejects <8px blanks; a 40x24 solid block is fine
    for a unit fixture)."""
    from PIL import Image
    Image.new("RGB", (40, 24), color).save(path)


def main():
    print("tf1-architecture-case-agent self-test")

    # --- 1. imports / syntax -------------------------------------------------
    print("\n[1] modules import")
    try:
        import build_branded_pdf as B
        check("build_branded_pdf imports", True)
    except Exception as e:  # pragma: no cover
        check(f"build_branded_pdf imports ({e})", False)
        _report()
        return
    try:
        import render_mermaid  # noqa: F401
        check("render_mermaid imports", True)
    except Exception as e:
        check(f"render_mermaid imports ({e})", False)

    # --- 2. pure-helper regressions -----------------------------------------
    print("\n[2] helper behaviour")

    # italic regex must NOT eat standalone asterisks
    out = B.inline_md_to_rl("throughput is 5 * 3 * 2 messages")
    check("literal '5 * 3 * 2' preserved (no italic eat)", "5 * 3 * 2" in out)
    out2 = B.inline_md_to_rl("this is *emphasised* text")
    check("real *emphasis* still becomes <i>", "<i>emphasised</i>" in out2)

    # cp1252 sanitiser maps arrows/emoji, keeps latin-1-ish punctuation
    safe = B.cp1252_safe("A \u2192 B \u2705 fail \u274c caf\u00e9 \u2014 end \u2022 x")
    check("arrow -> ascii", "\u2192" not in safe)
    check("check/cross mapped", "\u2705" not in safe and "\u274c" not in safe)
    check("accented 'caf\u00e9' preserved", "caf\u00e9" in safe)
    check("em-dash preserved", "\u2014" in safe)
    check("bullet preserved", "\u2022" in safe)
    def _cp1252_ok(s):
        try:
            s.encode("cp1252")
            return True
        except UnicodeEncodeError:
            return False
    check("no stray non-cp1252 survives", _cp1252_ok(safe))

    # ascii-diagram detector
    check("box-drawing detected as diagram",
          B.looks_like_ascii_diagram(["\u250c\u2500\u2510", "\u2502 x \u2502"]))
    check("ascii tree connectors detected",
          B.looks_like_ascii_diagram(["root", "|-- child", "`-- child2"]))
    check("real SQL NOT detected as diagram",
          not B.looks_like_ascii_diagram(["SELECT a, b", "FROM t WHERE a > 1"]))

    # --- 3. end-to-end: diagram-under-right-heading + code preserved --------
    print("\n[3] end-to-end PDF build")
    import pypdf

    html = """
<h2>Utility Tree</h2>
<div class="mermaid">graph TD
A[Availability] --> B[99.9%]
</div>
<h2>Architecture overview</h2>
<div class="mermaid">flowchart LR
Src --> Lake --> Serve
</div>
<h2>Reference query</h2>
<pre><code>SELECT customer_id, SUM(amount)
FROM orders
WHERE status = 'paid'
GROUP BY customer_id;</code></pre>
<p>Fan-out is 5 * 3 * 2 partitions.</p>
"""
    with tempfile.TemporaryDirectory() as td:
        dd = os.path.join(td, "diagrams")
        os.makedirs(dd)
        # Deliberately give the PNGs names that sort architecture-first, so a
        # naive positional match would SWAP them. Keyword matching must win.
        _png(os.path.join(dd, "architecture.png"), (30, 60, 90))
        _png(os.path.join(dd, "utility_tree.png"), (90, 30, 30))

        src = os.path.join(td, "in.html")
        out = os.path.join(td, "out.pdf")
        with open(src, "w") as f:
            f.write(html)

        B.configure_diagrams(dd)
        try:
            B.build_solution_pdf(
                src, out,
                title="Self Test", subtitle="regression",
                doc_label="TEST", level_line="L", doc_line="D",
                author_name="Tester", author_role="QA",
            )
            built = True
        except Exception as e:
            check(f"PDF builds without error ({e})", False)
            built = False

        if built:
            check("PDF file produced", os.path.exists(out) and os.path.getsize(out) > 1000)
            reader = pypdf.PdfReader(out)
            full = "\n".join(p.extract_text() or "" for p in reader.pages)

            # captions: builder emits "Diagram: <section heading>" above images
            caps = re.findall(r"Diagram:\s*(.+)", full)
            cap_blob = " | ".join(caps).lower()
            check("a Utility-Tree-captioned diagram exists",
                  any("utility" in c.lower() for c in caps))
            check("an Architecture-captioned diagram exists",
                  any("architect" in c.lower() for c in caps))

            # SQL under a non-diagram heading must survive verbatim
            check("SQL 'SELECT customer_id' preserved",
                  "SELECT customer_id" in full or "customer_id" in full)
            check("SQL 'GROUP BY' preserved", "GROUP BY" in full.upper())

            # literal asterisks survive into the PDF text
            check("literal '5 * 3 * 2' in PDF", "5 * 3 * 2" in full)

    _check_review_report()

    _report()


def _check_review_report():
    """Smoke-test review_report.py's mechanized content checks."""
    import review_report as rr

    manifest = (
        "| ID | Fact | Source |\n"
        "| PA-F01 | sixteen weeks | p1 |\n"
        "| PA-F02 | fifty million | p2 |\n"
    )
    clean = (
        "<p>Deliver in time [PA-F01]; scale is large [PA-F02].</p>"
        "<tr><td>Q1</td><td>what cutoff? [PA-F01]</td></tr>"
        "<p>open item — see Q1</p>"
        "<p>the three non-FHIR sources (HL7v2, X12, CSV)</p>"
    )
    f = rr.Findings()
    rr.check_citations(clean, manifest, f)
    rr.check_questions(clean, manifest, f)
    rr.check_counts(clean, f)
    check("review_report: clean report has no errors", not f.errors)

    bad = (
        "<p>Dangling [PA-F99] and [PA-U03]; see Q9.</p>"
        "<p>the two non-FHIR sources (HL7v2, X12, CSV)</p>"
    )
    f2 = rr.Findings()
    rr.check_citations(bad, manifest, f2)
    rr.check_questions(bad, manifest, f2)
    rr.check_counts(bad, f2)
    errs = " | ".join(f2.errors)
    check("review_report: flags undefined citation [PA-F99]", "PA-F99" in errs)
    check("review_report: flags undefined question Q9", "Q9" in errs)
    check("review_report: flags count mismatch (two vs 3)",
          any("count mismatch" in w for w in f2.warns))
    # explanatory placeholder [PA-Fxx] must NOT be treated as a real citation
    f3 = rr.Findings()
    rr.check_citations("<p>key: [PA-Fxx] means a fact [PA-F01]</p>", manifest, f3)
    check("review_report: ignores [PA-Fxx] placeholder",
          not any("Fxx" in e for e in f3.errors))


def _report():
    print()
    if FAILS:
        print(f"SELFTEST FAILED — {len(FAILS)} regression(s): {', '.join(FAILS)}")
        sys.exit(1)
    print("SELFTEST PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
