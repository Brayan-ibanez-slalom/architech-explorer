#!/usr/bin/env python3
"""Catch broken workflow files locally, before GitHub silently stops running them.

A single stray quote (`!= '''` instead of `!= ''`) made a workflow unparseable.
PyYAML accepted it, so a local "workflow YAML valid" check passed. GitHub did
not: it refused to run the workflow and reported the failure under the file's
PATH instead of its name, which reads at a glance like an unrelated failure.

The dangerous part is not the typo. It is that a workflow which cannot be parsed
does not run, and a check that does not run looks exactly like a check that had
nothing to complain about.

Exit codes: 0 valid, 1 a workflow is invalid, 2 could not check.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.join(os.path.dirname(HERE), ".github", "workflows")

REQUIRED_TOP = ("jobs",)


def main():
    try:
        import yaml
    except ImportError:
        print("PyYAML not installed — cannot check workflows. Exiting 2.")
        return 2
    if not os.path.isdir(WF):
        print(f"No workflow directory at {WF}. Exiting 2.")
        return 2

    files = sorted(f for f in os.listdir(WF) if f.endswith((".yml", ".yaml")))
    if not files:
        print("No workflow files found. Exiting 2 — 'nothing checked' is not a pass.")
        return 2

    bad = []
    for name in files:
        path = os.path.join(WF, name)
        try:
            doc = yaml.safe_load(open(path, encoding="utf-8"))
        except yaml.YAMLError as exc:
            bad.append(f"{name}: unparseable — {str(exc).splitlines()[0]}")
            continue
        if not isinstance(doc, dict):
            bad.append(f"{name}: does not parse to a mapping")
            continue
        for key in REQUIRED_TOP:
            if key not in doc:
                bad.append(f"{name}: missing top-level '{key}'")
        # `on:` is parsed by PyYAML as the boolean True (YAML 1.1). Its absence
        # in EITHER form means the workflow has no triggers and will never run.
        if "on" not in doc and True not in doc:
            bad.append(f"{name}: no triggers — this workflow would never run")
        for jid, job in (doc.get("jobs") or {}).items():
            if not isinstance(job, dict):
                bad.append(f"{name}: job '{jid}' is not a mapping")
                continue
            if "runs-on" not in job and "uses" not in job:
                bad.append(f"{name}: job '{jid}' has neither runs-on nor uses")
            for i, step in enumerate(job.get("steps") or []):
                cond = step.get("if")
                # A stray quote turns a condition into a string GitHub rejects
                # while PyYAML happily absorbs it.
                if isinstance(cond, str) and cond.count("'") % 2:
                    bad.append(f"{name}: job '{jid}' step {i + 1} has an unbalanced "
                               f"quote in its `if:` — {cond!r}")

    for msg in bad:
        print(f"  ✗ {msg}", file=sys.stderr)
    if bad:
        print("WORKFLOW CHECK FAILED — a workflow that cannot parse does not run,"
              " and a check that does not run looks like a check that passed.",
              file=sys.stderr)
        return 1
    print(f"WORKFLOW CHECK PASSED — {len(files)} workflow file(s) parse, have "
          f"triggers, and have balanced quotes in `if:` conditions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
