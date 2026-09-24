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
if python3 "$(dirname "$0")/verify_manifest.py" >/tmp/_mf.$$ 2>&1; then
  pass "$(tail -1 /tmp/_mf.$$)"
else
  MF_RC=$?
  grep -E '^  ✗|^      ' /tmp/_mf.$$ || cat /tmp/_mf.$$
  if [ "$MF_RC" -eq 2 ]; then
    warn "manifest could NOT be verified (see above) — treat results as unproven"
  else
    fail "fact manifest contains quote(s) not present in the source document"
  fi
fi
rm -f /tmp/_mf.$$

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
  PROSE=$(python3 "$(dirname "$0")/visible_text.py" "$f")

  # -------------------------------------------------------------------------
  head_ "1. Required reasoning-chain sections"
  for term in "Objectives" "Constraints" "Functional" "Quality" "ASR" \
              "Utility Tree" "Decision" "Trade-off" "Cost of Change" \
              "Open Questions" "Governance"; do
    if printf '%s' "$PROSE" | grep -qi "$term"; then pass "section present: $term"
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

  HITS=$(printf '%s' "$PROSE" | grep -oiE '[0-9]+(\.[0-9]+)?%|p9[059]\b|zero (downtime|disruption|data loss)|99\.[0-9]+' | sort -u || true)
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
  done < <(printf '%s' "$PROSE" \
            | sed -e 's/<[^>]*>/ /g' -e 's/&[a-z]*;/ /g' \
            | tr '\n' ' ' \
            | grep -oiE '[^.!?]*zero (downtime|disruption|data loss|event loss)[^.!?]*' || true)

  # -------------------------------------------------------------------------
  head_ "3. Vendor balance (guards against single-cloud bias)"
  AWS=$(printf '%s' "$PROSE" | grep -oiE 'aws|amazon|kinesis|redshift' | wc -l | tr -d ' ')
  AZ=$(printf '%s' "$PROSE" | grep -oiE 'azure|synapse|fabric' | wc -l | tr -d ' ')
  GCP=$(printf '%s' "$PROSE" | grep -oiE 'google cloud|gcp|bigquery|dataflow' | wc -l | tr -d ' ')
  OSS=$(printf '%s' "$PROSE" | grep -oiE 'kafka|flink|spark|airflow|dagster|iceberg|delta lake|hudi|opa|airbyte|dbt|openlineage|openmetadata' | wc -l | tr -d ' ')
  echo "        AWS:$AWS  Azure:$AZ  GCP:$GCP  OSS:$OSS"

  TOTAL=$((AWS+AZ+GCP))
  if [ "$OSS" -eq 0 ]; then
    fail "no open-source / portable option offered anywhere"
  else
    pass "open-source options present ($OSS mentions)"
  fi
  if [ "$TOTAL" -gt 6 ]; then
    for pair in "AWS:$AWS" "Azure:$AZ" "GCP:$GCP"; do
      n=${pair#*:}; v=${pair%%:*}
      if [ $((n*100/TOTAL)) -gt 60 ]; then
        fail "$v is $((n*100/TOTAL))% of hyperscaler mentions (limit 60%) — rebalance"
      fi
    done
    # Compare against this file's starting count, not the global one — otherwise a
    # failure in an earlier file suppresses this file's pass message.
    [ "$FAIL" -eq "$FILEFAIL_START" ] && pass "no single hyperscaler exceeds 60% of mentions"
  else
    pass "too few vendor mentions to skew ($TOTAL)"
  fi

  # -------------------------------------------------------------------------
  head_ "4. Structural depth"
  SCEN=$(printf '%s' "$PROSE" | grep -oi "Response Measure" | wc -l | tr -d ' ')
  [ "${SCEN:-0}" -ge 2 ] && pass "$SCEN quality-attribute scenarios (min 2)" \
                         || fail "only ${SCEN:-0} quality-attribute scenario(s); minimum is 2"

  printf '%s' "$PROSE" | grep -qi "Para qu" && pass "'¿Para qué?' purpose mapping present" \
                          || fail "no '¿Para qué?' mapping — every decision must name its purpose"

  grep -qi "mermaid" "$f" && pass "diagrams present" || warn "no Mermaid diagrams found"

  # -------------------------------------------------------------------------
  head_ "5. Source citations (every value must trace to the fact manifest)"
  if python3 "$(dirname "$0")/check_citations.py" "$f" >/tmp/_cit.$$ 2>&1; then
    pass "$(grep -o 'cited: [0-9]*' /tmp/_cit.$$ | head -1) — all values traced"
  else
    grep -E '^  ✗|^      (values|text):' /tmp/_cit.$$ || true
    fail "uncited requirement values — see above"
  fi
  rm -f /tmp/_cit.$$

  head_ "5. HTML well-formedness"
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
