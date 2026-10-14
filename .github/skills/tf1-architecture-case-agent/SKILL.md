---
name: tf1-architecture-case-agent
description: >
  Solves a TF1 (architecture-reasoning) style business/case scenario end to
  end and produces the standard deliverable set: a full HTML architecture
  report with rendered Mermaid diagrams, a filled workbook (if one was
  supplied), a validation/citation checklist, and branded, paginated PDF
  versions of all of them. Use this skill whenever the user asks to "run the
  architect/TF1 agent", "solve this case/brief", "fill this workbook", or
  provides a business scenario, case brief, GitHub issue, or PDF and wants an
  architecture recommendation produced in report/PDF form. The user only
  needs to supply the context (the scenario text, a brief/workbook file, or a
  pointer to one) plus an output folder; this skill performs the full
  analysis and rendering pipeline without further step-by-step instruction.
license: MIT
---

# TF1 Architecture Case Agent

Turns a business/architecture case (a short scenario, a GitHub issue, or a
PDF case brief + optional workbook) into a complete, validated architecture
recommendation, formatted the same way every time: one self-contained HTML
report (navy/blue "architech-explorer" visual style, Mermaid diagrams), a
filled workbook markdown file (only if an official workbook template was
supplied), a validation/citation checklist, and branded PDF renders of all
three that visually match the style of the *source* case documents when one
was provided (plain academic header/footer, page numbers, "Prepared by"
byline) — or a sensible generic branded style otherwise.

## When to use this skill

Trigger it when the user:
- Says "run the architect agent" / "run the TF1 agent" / "solve this case"
- Gives you a case brief (text, PDF, or GitHub issue) and wants an
  architecture recommendation
- Gives you a workbook/template PDF alongside a brief and wants it filled
- Asks for the "same format as before" for a new scenario (this skill *is*
  that format)

## Required inputs (ask the user only for what's missing)

1. **The case context** — one of:
   - Raw scenario text pasted/typed by the user
   - A GitHub issue URL/number
   - A PDF (case brief), optionally plus a second PDF (participant workbook /
     template defining exactly which sections must be filled)
2. **Output folder** — where to save results. Default to a new subfolder
   named after the case next to other similar work if the user doesn't say
   (e.g. `~/Desktop/Architech Academy/<Case-Name>/`).
3. **Author byline** — ask once per user/session: "What name and role should
   appear on the documents?" Reuse the answer for subsequent cases in the
   same session without re-asking.
4. **Diagram tool** — default to Mermaid (matches the established visual
   style and this skill's rendering pipeline). Only ask if the user names a
   different tool explicitly.

Do not block on anything else — make reasonable, clearly-labeled
architectural judgment calls for everything else, exactly like a senior
architect would, and surface unresolved items as explicit open
questions/assumptions rather than inventing facts.

## Pipeline

### 1. Extract and read all source material
- PDFs: for text extraction use `pypdf` (`PdfReader(path).pages[i].extract_text()`)
  — it needs no extra system libraries and is reliable here. (`pdftotext`
  and `PyPDF2` are typically unavailable. PyMuPDF also works but is mainly
  used later for QA image renders — see Step 7.) Read the *entire* brief and
  workbook before writing anything — do not skim.
- GitHub issues: fetch via `gh issue view` or the GitHub MCP tools.
- If a workbook/template PDF was supplied, extract its exact page/section
  structure — this tells you precisely which sections the final report must
  cover (problem framing, stakeholders, discovery questions, objectives &
  constraints, functional requirements & quality attributes, 2+ quality
  scenarios, 3+ ASRs, utility tree, sources & access, 3+ trade-offs, AI
  evidence, recommendation, etc. — adapt section names to whatever the
  workbook/brief actually calls for).

### 2. Produce the HTML report
- Reuse `templates/report_style.css` (the shared navy/blue card-based
  report CSS used across all prior scenarios) verbatim inside a `<style>`
  block, and follow the section skeleton in
  `templates/report_skeleton.html` as a structural starting point — replace
  every placeholder/comment with real, case-specific content. Keep the
  `<div class="mermaid">...</div>` wrapper exactly as shown for any diagram
  (Utility Tree as a `graph TD`, architecture/box diagrams as a
  `flowchart LR` with `subgraph`s).
- Required content, regardless of case: problem statement + stakeholders;
  objectives/constraints/assumptions (facts vs. assumptions clearly
  separated, each cited back to a source line); 5-7 discovery questions;
  functional requirements + quality attributes; >=2 full six-part quality
  attribute scenarios (source/stimulus/environment/artifact/response/
  response measure); >=3 ASRs (evidence/branch/impact/risk/decision) as a
  table; a Mermaid Utility Tree; >=3 trade-offs (decision area+evidence /
  Option A benefit-cost-risk / Option B / recommendation+consequences /
  reversibility / review trigger); first-release recommendation (scope
  included vs. deferred + reason + review trigger, sources & access
  approach, success measures, risks); an AI-evidence section (planning
  notes, validation checklist, human accountability statement — written
  honestly, since *you* are the AI that proposed the architecture); and a
  closing rubric/requirements self-check table if the brief defines a
  rubric.
- Never invent specific numbers, vendors, regulations, or data fields not
  present in the source material — tag every quantitative/qualitative claim
  with a short citation code (e.g. `[XX-F01]`) back to the source, and leave
  anything unconfirmed as an explicit open question/assumption instead.

### 3. Produce the filled workbook (only if a workbook template exists)
- Write a markdown file organized by the *workbook's own* page/section
  numbers, answering each prompt directly (same substance as the HTML
  report, reorganized to match the template). This is supporting evidence,
  not a duplicate deliverable — most of these academic workbooks are
  explicitly "optional drafting space, not an additional assessed
  deliverable", so frame it that way if the source says so.

### 4. Produce the validation/citation checklist
- A short markdown file: which rubric/requirement areas are covered and
  where; every quantitative/qualitative fact used, cited back to its exact
  source line (treat this as the case's **facts manifest**: each `[XX-Fxx]`
  id maps to a verbatim source quote + page/line, so citations in the report
  can be mechanically checked); the full list of items deliberately left
  open rather than assumed. Also distinguish *source facts* from *design
  decisions/acceptance criteria you introduced* — label the latter as such
  (assumption or acceptance criterion tied to a source fact + review
  trigger), and never claim "no invented facts" if the recommendation states
  engineering choices the brief didn't.

> **Run the text-based half of the step-8 content self-review now**, before
> rendering diagrams or building PDFs — a citation/count/scope fix here costs
> one text edit; the same fix found after step 6 costs a full diagram +
> 3-PDF rebuild. Only the render-dependent checks (diagram-under-right-
> heading, caption/image match) have to wait until after step 6.

### 5. Render the two (or more) Mermaid diagrams to PNG
Mermaid-CLI via `npx`/npm is often broken in these environments (corporate
npm registries with expired tokens are common). Use the bundled
headless-Chrome renderer instead — it has no npm dependency:

```
python3 scripts/render_mermaid.py utility_tree.mmd diagrams/utility_tree.png
python3 scripts/render_mermaid.py architecture.mmd diagrams/architecture.png
```

- Put the raw Mermaid source (just the diagram body, no `<div>`/backticks)
  into each `.mmd` file first.
- **Name each PNG with a keyword that appears in the heading of the section
  it belongs to** (e.g. `utility_tree.png` for a "Utility Tree" section,
  `architecture.png` for an "Architecture overview" section). The PDF
  builder matches each `<div class="mermaid">` block (or ASCII-diagram code
  block) to a PNG **by the surrounding heading text first**, then by the
  mermaid block kind (`graph TD`/`TB` -> tree/utility; `flowchart` ->
  architecture), and only falls back to sorted-filename/encounter order if
  no keyword matches. Keyword naming is strongly preferred because it is
  immune to the order in which diagrams happen to appear. Recognized heading
  keywords include: utility/tree, architecture/component/data-flow,
  deployment/infrastructure, sequence, erd/entity/schema/model. For other
  diagram types, prefix filenames `00_`, `01_`, ... in document order as a
  fallback.
- This works for **any number of diagrams**, not just two — add one `.mmd`
  per diagram and one `<div class="mermaid">` per diagram in the HTML.
- Requires Google Chrome/Chromium/Edge installed locally (the renderer
  checks the usual macOS, Linux, and Windows paths) and the `Pillow` package
  (`pip3 install pillow` if missing) for whitespace auto-cropping. The
  renderer pins a specific mermaid version, times out instead of hanging,
  and **errors loudly on a blank render** rather than writing an empty PNG.
- Verify each PNG visually with the `view` tool before moving on — if a
  diagram is cut off or empty, the Mermaid syntax likely has an error; fix
  the `.mmd` source and re-render rather than shipping a bad image.

### 6. Build branded, paginated PDFs
Use the bundled generic PDF builder (`reportlab`/`python-docx`/`pypdf`;
`pip3 install reportlab python-docx pypdf pillow` if any are missing — these
are small, safe, common packages). It strips HTML/Markdown and re-flows the
content into a plain academic layout: repeating header block (brand line /
level line / document line / page number), "Prepared by" byline on the
title page, real `reportlab.Table` objects for every markdown/HTML table,
and the rendered Mermaid PNGs embedded at the right place (never a text/tree
fallback unless Chrome is truly unavailable).

```
python3 scripts/build_branded_pdf.py \
  --input-html Solution.html --output Solution.pdf \
  --title "<Org/Case Title>" \
  --subtitle "<One-line recommendation subtitle>" \
  --doc-label "Architecture Recommendation — full TF1 report" \
  --level-line "<2nd header line, e.g. matching the source doc's own 'Level 1 case'>" \
  --doc-line "<3rd header line, e.g. 'Case Name • Architecture Recommendation'>" \
  --author-name "<name from the user>" --author-role "<role from the user>" \
  --diagrams-dir ./diagrams

python3 scripts/build_branded_pdf.py \
  --input-md Workbook_Filled.md --output Workbook_Filled.pdf \
  --title "<Org/Case Title>" --subtitle "<subtitle>" \
  --doc-label "Participant Workbook (completed)" \
  --level-line "Level 1 participant workbook" \
  --doc-line "<Case Name> - Participant workbook (completed)" \
  --author-name "<name>" --author-role "<role>"

python3 scripts/build_branded_pdf.py \
  --input-md validation-checklist.md --output validation-checklist.pdf \
  --title "<Org/Case Title>" --subtitle "<subtitle>" \
  --doc-label "Validation & Citation Record" \
  --level-line "Level 1 case" \
  --doc-line "<Case Name> • Validation & Citation Record" \
  --author-name "<name>" --author-role "<role>"
```

- If the source material had its own exact header pattern (brand name /
  level line / doc line, as academic case PDFs usually do), extract it with
  `pypdf` first and reuse the *same wording* in `--level-line`/`--doc-line`
  so the output visually matches the original documents, not just a generic
  template.
- `--title`/`--subtitle`/`--doc-label`/`--level-line`/`--doc-line`/
  `--author-name`/`--author-role` are all free text — there is nothing
  case-specific hardcoded in the script; every prior scenario's wording was
  passed in exactly like this.

### 7. Verify before declaring done
- Run the skill's own regression self-test first — it exercises the diagram
  matching, code-preservation, italic, table and unicode paths against tiny
  fixtures and must exit 0:
  ```
  python3 scripts/selftest.py
  ```
- Re-open each PDF's page count and first/last page text with `pypdf` to
  confirm non-empty, correctly ordered content.
- Render at least the diagram pages to PNG with PyMuPDF
  (`pip3 install pymupdf`; `import pymupdf; pymupdf.open(pdf)[i].get_pixmap(dpi=120).save(...)`
  — the old `import fitz` alias still works but is deprecated) and view them —
  confirm diagrams are present, legible, and not cut off.
  (Headless Chrome's own `--print-to-pdf`/`--screenshot` do not reliably
  render local PDFs in this environment — use PyMuPDF for QA screenshots,
  not Chrome.)
- **Check each diagram is under the right heading** — don't just confirm "a
  diagram is present." Extract the caption line (`Diagram: <heading>`) above
  each embedded image and confirm it matches the intended diagram (e.g. the
  Utility Tree image sits under the Utility Tree section, not the
  architecture one). This catches the image-to-section mismatch that a
  bare "diagrams present" check would miss.
- Confirm no fenced code content silently vanished: the PDF builder only
  swaps a code block for a diagram image when the block is genuine ASCII-art
  (or a `mermaid`/`diagram` fence) under a diagram heading — real code (SQL,
  YAML, etc.) is kept verbatim. Spot-check any case that embeds code.
- `open <file>.pdf` / `open <file>.html` at the end so the user can review
  immediately.

### 8. Adversarial content self-review (catch the silent credibility-killers)
Steps 1-7 prove the documents *build and render*; this step proves they are
*correct and defensible*. A deliverable that stakes its credibility on "every
claim traces to the brief" is destroyed by one dangling citation or one
invented number.

**Run order matters.** The *text-based* checks below need no PDF — run them on
the HTML/Markdown sources right after step 4 (see the note there) so fixes
cost one text edit, not a diagram + 3-PDF rebuild. Only the *render-dependent*
checks (diagram under the right heading, caption matches image — already in
step 7) wait until after step 6. For a thorough pass, also dispatch a
**fresh, independent review agent** (it catches what the author rationalizes
away) with the brief + deliverables and ask it to find breaking points.

**Mechanize what you can; reserve judgment for the rest.** Run the bundled
checker first — it automates the purely structural checks so your attention
(and the review agent's) goes to the judgment calls:

```
python3 scripts/review_report.py --manifest validation-checklist.md \
    --report Solution.html --also Workbook_Filled.md
```

It exits non-zero (gate-style, like `selftest.py`) on: a citation not defined
in the facts manifest, a second/dangling citation namespace, a discovery
question referenced but never defined, and (heuristically) a spelled count
that disagrees with the parenthesised list it introduces. Unused manifest
facts and cross-file id gaps are WARNings, not failures (a fact can be
legitimately cited in only one deliverable). What the script **cannot** judge —
and you/the agent still must — is everything below marked *(judgment)*.

- **[mechanized] Citation integrity — every id resolves both ways.** Every
  `[XX-Fxx]` in the report must be defined in the facts manifest; never
  introduce a second citation namespace you then never define (carry open
  items as the numbered discovery questions `Q1..Qn`). The checker's id
  regex is namespace-agnostic (`[A-Z0-9]+-[A-Za-z0-9]+`), so it works for any
  case's tag scheme, not just `-F`.
- **[judgment] Cited fact actually says it.** Spot-check that each citation's
  manifest quote genuinely supports the sentence it is attached to. A
  plausible-but-wrong id (right topic, wrong fact) is a common self-inflicted
  error the script cannot catch. If the supporting fact is not yet in the
  manifest, *add it* — don't borrow a near-neighbour id.
- **[mechanized + judgment] No numeric self-contradiction.** The checker flags
  obvious "the two X (a, b, c)" count/list mismatches; you still re-read every
  other count/number in prose against the source table and against other
  sentences in the same document. Internal arithmetic must agree with the
  brief's own figures.
- **[judgment] Trade-offs are genuine, in-bounds tensions.** Each trade-off's
  Option B must be something the brief actually *permits*. Comparing the
  recommendation against an option the brief explicitly *prohibits* is a
  strawman. If the only alternative is prohibited, **replace** that trade-off
  with a real tension (e.g. how far an allowed capability may reach) rather
  than deleting it — you must still meet the stated minimum (usually >=3).
- **[judgment] Every trade-off carries reversibility + a review trigger.** For
  each decision, state whether it is easily reversible or a one-way door, and
  the signal/date that should trigger revisiting it. A trade-off with no
  "when would we change our mind?" reads as an opinion, not an architecture
  decision.
- **[judgment] Every six-part scenario is fully populated and measurable.**
  For each quality-attribute scenario, confirm all six parts are present
  (source, stimulus, environment, artifact, response, **response measure**)
  and that the response measure is *measurable* — a number, threshold, or an
  explicitly-labelled design acceptance criterion with a verification method,
  never a vague "system performs well."
- **[judgment] Every named pain point maps to a requirement — or is
  explicitly deferred.** List the problems the brief explicitly names; confirm
  each is either carried into a functional requirement/ASR/scenario, or
  *explicitly listed as out of scope/deferred with a reason*. A pain point
  that is silently absent (neither modelled nor deferred) is the completeness
  gap a rubric catches; one that is deliberately deferred is fine.
- **[judgment] Impact ratings reflect capability importance, not
  deferability.** Don't rate a foundational precondition (e.g. "can we ingest
  anything at all from the sources") as low/medium business impact just
  because a *specific technique* for it is being deferred. Separate "we can
  defer technique X" (a scope choice) from "this capability's business impact"
  (often high).
- **[judgment] Design decisions verified as labelled, not asserted.** Anything
  the brief didn't state (nightly batch, deterministic matching, an SLA, an
  acceptance criterion) must be labelled an assumption or acceptance criterion
  tied to a source fact + review trigger — never phrased as an established
  client fact. This is the verification half of the step-4 rule: step 4
  *writes* the source-vs-design distinction into the checklist; here you
  *confirm* nothing slipped through into the report as a fake client fact.
- **[judgment] Rubric self-check is honest.** If you assert coverage of a
  rubric/assessment area, confirm the deliverable genuinely addresses it at
  the stated weight — don't claim a dimension you only gestured at. An
  inflated self-assessment is worse than an honest gap note.
- **[mechanized + judgment] Cross-file consistency.** If you produced HTML +
  workbook + checklist, the same fact must carry the same citation id, the
  same ASR/trade-off numbers, and the same included-vs-deferred scope in all
  three. The checker WARNs on citation ids that appear in some deliverables
  but not others; you still eyeball shared numbers and renumbered trade-offs.
- **[judgment] Self-containment (nice-to-have).** Ideally the canonical
  HTML/PDF lets a reader resolve citations without opening a second file —
  include at least the cited subset of the facts manifest as an appendix, or
  a visible pointer to it.

When the independent agent returns findings, verify each against the brief
yourself before acting (reviewers over-flag too), fix the real ones, then —
if the fix touched rendered content — **rebuild and re-verify** (steps 5-7);
a content edit can change page counts, diagram labels, and cross-references.
Text-only fixes made before step 6 need no rebuild.

## Known environment gotchas (save yourself a retry loop)
- `npm`/`npx` may be pinned to a private/corporate registry with a stale
  auth token (`npm config get registry` to check) — don't fight it; use the
  bundled Chrome-based Mermaid renderer instead of `@mermaid-js/mermaid-cli`.
- `weasyprint`, `wkhtmltopdf`, and `pandoc` are typically not installed and
  not worth installing — the bundled `reportlab`-based pipeline covers the
  whole PDF need without a system-level HTML renderer.
- `pdf2image` needs poppler and is unreliable here; prefer `pymupdf`
  (`fitz`) for any PDF->image QA step.
- Always install missing small pip packages directly
  (`pip3 install reportlab python-docx pypdf pillow pymupdf`) rather than
  asking the user to do it — these are safe, common, and already proven to
  work in this environment.

## Files in this skill
- `scripts/render_mermaid.py` — Mermaid source -> cropped PNG via headless
  Chrome (no npm/mermaid-cli dependency).
- `scripts/review_report.py` — mechanized slice of the step-8 content
  self-review: citation two-way resolution against the facts manifest,
  dangling-namespace and undefined discovery-question detection, a numeric
  count/list heuristic, and cross-file citation consistency. Namespace-
  agnostic; gate-style non-zero exit on real defects.
- `scripts/build_branded_pdf.py` — generic HTML-or-Markdown -> branded,
  paginated PDF CLI (repeating header/footer, tables, embedded diagram
  images, author byline). Fully parameterized; nothing case-specific is
  hardcoded.
- `templates/report_style.css` — the shared visual CSS for the HTML report
  (navy/blue header, sticky nav, card sections, decision/trade-off boxes,
  tables) — reuse verbatim for visual consistency across cases.
- `templates/report_skeleton.html` — section-by-section starting structure
  for a new HTML report; replace placeholders with real content.
