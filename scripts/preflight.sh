#!/usr/bin/env bash
#
# preflight.sh — Validate a report BEFORE creating a pull request.
#
# The agent MUST run this and see it pass before it is allowed to open a PR.
# If it fails, the agent iterates on the findings and re-runs. No PR is created
# until this exits 0.
#
# This is the "validate first, then propose" gate. The CI workflow
# (.github/workflows/agent-quality-review.yml) re-runs equivalent checks on the PR
# as a backstop, but the intent is that nothing reaches CI in a failing state.
#
# Usage:
#   ./scripts/preflight.sh docs/MyScenario_Solution.html [more.html ...]
#   ./scripts/preflight.sh            # auto-detects changed docs/*.html vs main

set -uo pipefail

# Secure scratch dir. Previously this script wrote to predictable /tmp/_cit.$$
# paths, which a red team flagged as a symlink/pre-creation hazard on a shared
# machine. mktemp -d is unpredictable and removed on exit.
WORK="$(mktemp -d "${TMPDIR:-/tmp}/preflight.XXXXXXXX")"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT INT TERM


RED=$'\033[0;31m'; GRN=$'\033[0;32m'; YEL=$'\033[0;33m'; BLU=$'\033[0;34m'; RST=$'\033[0m'
FAIL=0
WARN=0

fail() { echo "${RED}✗ FAIL${RST}  $*"; FAIL=$((FAIL+1)); }
pass() { echo "${GRN}✓ PASS${RST}  $*"; }
warn() { echo "${YEL}⚠ WARN${RST}  $*"; WARN=$((WARN+1)); }
head_() { echo; echo "${BLU}── $* ${RST}"; }

# ---------------------------------------------------------------------------
# Resolve target files
#
# NOTE: deliberately avoids `mapfile`/`readarray`. macOS ships bash 3.2, where
# those builtins do not exist — an earlier version silently printed
# "command not found" and then exited 0, i.e. the gate PASSED by failing.
# A gate must never pass because it broke.
# ---------------------------------------------------------------------------
FILES=()
if [ "$#" -gt 0 ]; then
  for a in "$@"; do FILES+=("$a"); done
else
  if git rev-parse --git-dir >/dev/null 2>&1; then
    if git rev-parse --verify -q main >/dev/null 2>&1; then BASE=main; else BASE=HEAD; fi
    CAND=$( { git diff --name-only "$BASE"...HEAD -- 'docs/*.html' 2>/dev/null
              git diff --name-only -- 'docs/*.html' 2>/dev/null
              git diff --name-only --cached -- 'docs/*.html' 2>/dev/null
              git ls-files -o --exclude-standard -- 'docs/*.html' 2>/dev/null
            } | grep -v '^$' | sort -u )
    while IFS= read -r line; do
      [ -n "$line" ] && FILES+=("$line")
    done <<< "$CAND"
  else
    echo "${RED}✗ Not a git repository and no files given.${RST}" >&2
    echo "Usage: $0 docs/<Scenario>_Solution.html" >&2
    exit 2
  fi
fi

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "${YEL}No changed docs/*.html detected.${RST}"
  echo "If you expected files here, pass them explicitly:"
  echo "    $0 docs/<Scenario>_Solution.html"
  echo
  echo "Exiting 2 (indeterminate) rather than 0 — 'nothing checked' is NOT 'checks passed'."
  exit 2
fi

echo "Pre-flight validation for: ${FILES[*]}"

# ---------------------------------------------------------------------------
# Manifest integrity, checked ONCE before any report is validated.
# Citations are only meaningful if the facts they point at are real. Without
# this, the manifest would be relocated self-attestation.
# ---------------------------------------------------------------------------
head_ "0. Fact manifest integrity"
if python3 "$(dirname "$0")/verify_manifest.py" >"$WORK/mf.out" 2>&1; then
  pass "$(tail -1 "$WORK/mf.out")"
else
  MF_RC=$?
  grep -E '^  ✗|^      ' "$WORK/mf.out" || cat "$WORK/mf.out"
  if [ "$MF_RC" -eq 2 ]; then
    warn "manifest could NOT be verified (see above) — treat results as unproven"
  else
    fail "fact manifest contains quote(s) not present in the source document"
  fi
fi

head_ "0-pre. Workflow files parse (a workflow that cannot parse never runs)"
if python3 "$(dirname "$0")/check_workflows.py" >"$WORK/wf.out" 2>&1; then
  pass "$(tail -1 "$WORK/wf.out")"
else
  WF_RC=$?
  cat "$WORK/wf.out"
  if [ "$WF_RC" -eq 2 ]; then
    warn "workflow files could NOT be checked"
  else
    fail "a workflow file is invalid — CI would silently stop running"
  fi
fi

head_ "0a. Source provenance (is the evidence really the evidence?)"
# A generated report once added a PDF it had authored itself, which the manifest
# verifier then accepted as the source for its own quotes. Scoping sources per
# scenario stops one file vouching for another; this step stops a file vouching
# for itself, by re-fetching the upstream GitHub issue and comparing hashes.
if python3 "$(dirname "$0")/verify_provenance.py" >"$WORK/pv.out" 2>&1; then
  pass "$(tail -1 "$WORK/pv.out")"
else
  PV_RC=$?
  cat "$WORK/pv.out"
  if [ "$PV_RC" -eq 2 ]; then
    warn "provenance could NOT be re-checked against upstream — unproven, not passed"
  else
    fail "a captured source does not match upstream or its pinned hash"
  fi
fi

head_ "0b. Adversarial regression suite"
if python3 "$(dirname "$0")/test_gate.py" >"$WORK/tg.out" 2>&1; then
  pass "$(grep -o '[0-9]*/[0-9]* cases correct' "$WORK/tg.out") — gate behaves as verified"
else
  fail "adversarial regression suite FAILED — the gate no longer blocks known attacks"
  grep -E '^  FAIL' "$WORK/tg.out" || true
fi

for f in "${FILES[@]}"; do
  [ -f "$f" ] || { fail "$f does not exist"; continue; }

  # v1 is an intentionally preserved defective baseline — never gate on it.
  case "$f" in
    docs/Customer360_Capstone_Solution.html)
      warn "$f is the archived v1 baseline (known defects, intentionally uncorrected) — skipped"
      continue ;;
  esac

  echo; echo "═══ $f ═══"
  FILEFAIL_START=$FAIL

  # Visible text only. Keyword-stuffed HTML comments and display:none blocks
  # previously satisfied every check while the prose contained no analysis.
  # Extract to a FILE, not a shell variable. Every check below used to pipe the
  # variable in with `printf '%s' "$PROSE" | grep ...`. When grep matched early it
  # exited and killed printf with SIGPIPE, and on CI that intermittently truncated
  # the stream for LATER checks in the same loop: identical commits alternated
  # between pass and fail, with sections that demonstrably exist reported missing.
  # A flaky gate is worse than no gate, because it teaches people to re-run it
  # until it goes green. grep reading a file cannot race.
  PROSE_FILE="$WORK/prose.$$.txt"
  if ! python3 "$(dirname "$0")/visible_text.py" "$f" > "$PROSE_FILE"; then
    echo "extraction failed for $f — result indeterminate, not a pass"; exit 2
  fi
  PROSE_BYTES=$(wc -c < "$PROSE_FILE" | tr -d ' ')
  if [ "$PROSE_BYTES" -lt 2000 ]; then
    echo "only $PROSE_BYTES bytes of visible text extracted from $f — too little to"
    echo "have checked anything. Treating as INDETERMINATE (exit 2), not a pass."
    exit 2
  fi

  # -------------------------------------------------------------------------
  head_ "1. Required reasoning-chain sections"
  for term in "Objectives" "Constraints" "Functional" "Quality" "ASR" \
              "Utility Tree" "Decision" "Trade-off" "Cost of Change" \
              "Open Questions" "Governance"; do
    if grep -qi "$term" "$PROSE_FILE"; then pass "section present: $term"
    else fail "missing required section: $term"; fi
  done

  # -------------------------------------------------------------------------
  head_ "2. Fabricated-precision scan (every hit must be traceable to the source)"
  # Strip <style>/<script> blocks first — CSS percentages and Mermaid config are not
  # requirements, and flagging them buries the real findings in noise.
  # Strip <style>/<script> only. Mermaid diagram bodies are DELIBERATELY included:
  # a fabricated "99%" survived a previous cleanup precisely because an earlier
  # version of this script excluded diagrams as "noise". Diagrams state requirements,
  # so they must be scanned. CSS percentages are excluded via the style strip.

  HITS=$(grep -oiE '[0-9]+(\.[0-9]+)?%|p9[059]\b|zero (downtime|disruption|data loss)|99\.[0-9]+' "$PROSE_FILE" | sort -u || true)
  if [ -z "$HITS" ]; then
    pass "no high-risk precision values in prose"
  else
    while read -r h; do
      [ -z "$h" ] && continue
      echo "        → \"$h\" — confirm this is GIVEN in the scenario, not invented"
    done <<< "$HITS"
    warn "$(printf '%s\n' "$HITS" | grep -c .) precision value(s) need source confirmation"
  fi

  # "zero X" claims are the highest-risk fabrication class, but they can also be
  # legitimate (Scenario A genuinely says "without pipeline downtime"). The script
  # cannot know which — so it requires the REPORT to declare its sourcing inline.
  # Mark with (given) / (assumption) / Open Question / "not specified".
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    if ! printf '%s' "$line" | grep -qiE '\(given\)|\(assumption\)|Open Question|not specified|was not given|removed|fabricat'; then
      fail "unmarked absolute claim — add (given) or (assumption), or move to Open Questions:"
      echo "          $(printf '%s' "$line" | sed -e 's/^ *//' | cut -c1-110)"
    fi
  done < <(sed -e 's/<[^>]*>/ /g' -e 's/&[a-z]*;/ /g' "$PROSE_FILE" \
            | tr '\n' ' ' \
            | grep -oiE '[^.!?]*zero (downtime|disruption|data loss|event loss)[^.!?]*' || true)

  # -------------------------------------------------------------------------
  head_ "3. Vendor balance (guards against single-cloud bias)"
  AWS=$(grep -oiE 'aws|amazon|kinesis|redshift' "$PROSE_FILE" | wc -l | tr -d ' ')
  AZ=$(grep -oiE 'azure|synapse|fabric' "$PROSE_FILE" | wc -l | tr -d ' ')
  GCP=$(grep -oiE 'google cloud|gcp|bigquery|dataflow' "$PROSE_FILE" | wc -l | tr -d ' ')
  OSS=$(grep -oiE 'kafka|flink|spark|airflow|dagster|iceberg|delta lake|hudi|opa|airbyte|dbt|openlineage|openmetadata' "$PROSE_FILE" | wc -l | tr -d ' ')
  echo "        AWS:$AWS  Azure:$AZ  GCP:$GCP  OSS:$OSS"

  TOTAL=$((AWS+AZ+GCP))
  if [ "$OSS" -eq 0 ]; then
    fail "no open-source / portable option offered anywhere"
  else
    pass "open-source options present ($OSS mentions)"
  fi
  # Demoted from blocking to a WARNING on the recommendation of two independent
  # reviewers, made twice. Their argument: mention-share is not evidence of
  # neutrality. A balanced count can be reached by padding a report with product
  # names nobody intends to use, while a genuinely reasoned single-cloud design
  # — correct when the client has a stated platform commitment — would fail.
  # The signal is still worth surfacing, so it is reported, not enforced.
  if [ "$TOTAL" -gt 6 ]; then
    SKEW=0
    for pair in "AWS:$AWS" "Azure:$AZ" "GCP:$GCP"; do
      n=${pair#*:}; v=${pair%%:*}
      if [ $((n*100/TOTAL)) -gt 60 ]; then
        warn "$v is $((n*100/TOTAL))% of hyperscaler mentions — check this reflects a stated platform constraint, not familiarity bias"
        SKEW=1
      fi
    done
    [ "$SKEW" -eq 0 ] && pass "no single hyperscaler exceeds 60% of mentions"
  else
    pass "too few vendor mentions to skew ($TOTAL)"
  fi

  # -------------------------------------------------------------------------
  head_ "4. Structural depth"
  SCEN=$(grep -oi "Response Measure" "$PROSE_FILE" | wc -l | tr -d ' ')
  [ "${SCEN:-0}" -ge 2 ] && pass "$SCEN quality-attribute scenarios (min 2)" \
                         || fail "only ${SCEN:-0} quality-attribute scenario(s); minimum is 2"

  grep -qi "Para qu" "$PROSE_FILE" && pass "'¿Para qué?' purpose mapping present" \
                          || fail "no '¿Para qué?' mapping — every decision must name its purpose"

  grep -qi "mermaid" "$f" && pass "diagrams present" || warn "no Mermaid diagrams found"

  # -------------------------------------------------------------------------
  head_ "5. Source citations (every value must trace to the fact manifest)"
  if python3 "$(dirname "$0")/check_citations.py" "$f" >"$WORK/cit.out" 2>&1; then
    pass "$(grep -o 'cited: [0-9]*' "$WORK/cit.out" | head -1) — all values traced"
  else
    grep -E '^  ✗|^      (values|text):' "$WORK/cit.out" || true
    fail "uncited requirement values — see above"
  fi
  
  head_ "5b. Decision quality (is the decision reviewable, not just sourced?)"
  if python3 "$(dirname "$0")/check_decisions.py" "$f" >"$WORK/dec.out" 2>&1; then
    pass "all 7 decision fields present, substantive and non-negated (does NOT prove the reasoning is correct)"
  else
    fail "one or more decisions are not reviewable"
    grep -E '^  FAIL|^         ' "$WORK/dec.out" || true
  fi

  head_ "6. HTML well-formedness"
  python3 - "$f" <<'PY'
import sys
from html.parser import HTMLParser
VOID={'meta','br','hr','img','link','input','source','area','base','col','embed','track','wbr'}
class P(HTMLParser):
    def __init__(s): super().__init__(); s.st=[]
    def handle_starttag(s,t,a):
        if t not in VOID: s.st.append(t)
    def handle_endtag(s,t):
        if s.st and s.st[-1]==t: s.st.pop()
        elif t in s.st:
            while s.st and s.st.pop()!=t: pass
p=P(); p.feed(open(sys.argv[1],encoding='utf-8').read())
if p.st: print("UNCLOSED:"+",".join(p.st)); sys.exit(1)
sys.exit(0)
PY
  [ $? -eq 0 ] && pass "HTML well-formed" || fail "unclosed HTML tags"
done

# ---------------------------------------------------------------------------
echo
echo "════════════════════════════════════════════════"
if [ "$FAIL" -gt 0 ]; then
  echo "${RED}PRE-FLIGHT FAILED — $FAIL blocking issue(s), $WARN warning(s)${RST}"
  echo
  echo "DO NOT open a pull request."
  echo "Report these findings to the requester, iterate on the report, and re-run:"
  echo "    ./scripts/preflight.sh ${FILES[*]}"
  exit 1
fi
echo "${GRN}PRE-FLIGHT PASSED${RST} — $WARN warning(s) to review manually."
echo
echo "Warnings are not auto-blocking, but every flagged precision value must be"
echo "confirmed against the source scenario before you proceed."
echo
echo "Next required step: obtain an INDEPENDENT agent review verdict, then open the PR"
echo "with the verdict block pasted into the description."
exit 0
