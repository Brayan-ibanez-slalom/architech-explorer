#!/usr/bin/env python3
"""Confirm that author-supplied source files really are what they claim to be.

The problem this exists to solve
--------------------------------
A generated report added a PDF it had written itself to knowledge-base/, and the
manifest verifier then checked that report's quotes against it. The author
supplied the document its own quotes were verified against. That is a loop, not
verification, and a loop will certify anything.

Scoping sources per scenario (see verify_manifest.py) stops one scenario's file
from vouching for another's. It does not stop a scenario's own file from being
fabricated. This check closes that: for any scenario whose facts come from a
GitHub issue, the committed capture is hashed, the hash is pinned in
knowledge-base/provenance.lock, and the live issue is re-fetched and compared.

Exit codes
----------
0  every pinned source matched the live upstream
1  a source has drifted from upstream, or the lock file disagrees with the file
2  indeterminate - could not check (no network, no gh, no token). NEVER 0.
   "Could not verify" must not read the same as "verified".
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
KB = os.path.join(REPO, "knowledge-base")
MANIFEST = os.path.join(KB, "scenario-facts.yml")
LOCK = os.path.join(KB, "provenance.lock")
REPO_SLUG = "Brayan-ibanez-slalom/architech-explorer"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def gh_json(path):
    """Return parsed JSON from the GitHub API, or None if unavailable."""
    env = dict(os.environ)
    env.setdefault("GH_HOST", "github.com")
    try:
        res = subprocess.run(["gh", "api", path], capture_output=True,
                             text=True, env=env, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if res.returncode != 0:
        return None
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return None


def rebuild_from_github(issue_no, comment_ids):
    issue = gh_json(f"repos/{REPO_SLUG}/issues/{issue_no}")
    if issue is None:
        return None
    parts = [f"### SOURCE: issue #{issue_no} — {issue['title']}\n", issue["body"]]
    for cid in comment_ids:
        c = gh_json(f"repos/{REPO_SLUG}/issues/comments/{cid}")
        if c is None:
            return None
        parts.append(f"\n### SOURCE: comment {cid}\n")
        parts.append(c["body"])
    return "\n".join(parts)


def main():
    try:
        import yaml
    except ImportError:
        print("PyYAML not installed - cannot read the manifest.")
        print("Exiting 2 (indeterminate). 'Could not check' is not 'checks passed'.")
        sys.exit(2)

    with open(MANIFEST, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)

    tracked = [s for s in doc.get("scenarios", []) if s.get("source_issue")]
    if not tracked:
        print("No GitHub-sourced scenarios to check.")
        return 0

    if not os.path.exists(LOCK):
        print(f"ERROR: {LOCK} is missing, so pinned hashes cannot be compared.",
              file=sys.stderr)
        sys.exit(1)
    with open(LOCK, encoding="utf-8") as fh:
        lock = yaml.safe_load(fh) or {}

    failures, unchecked = [], []

    for scen in tracked:
        sid = scen["id"]
        files = scen.get("source_files") or []
        if len(files) != 1:
            failures.append(f"{sid}: expected exactly one source_files entry")
            continue
        path = os.path.join(KB, files[0])
        if not os.path.exists(path):
            failures.append(f"{sid}: source file missing ({files[0]})")
            continue
        on_disk = open(path, encoding="utf-8").read()
        disk_hash = sha(on_disk)

        pinned = (lock.get(sid) or {}).get("sha256")
        if pinned is None:
            failures.append(f"{sid}: no pinned hash in provenance.lock")
            continue
        if pinned != disk_hash:
            failures.append(
                f"{sid}: committed source does not match its pinned hash "
                f"(file {disk_hash[:12]}, lock {pinned[:12]}). Someone edited the "
                f"captured source without updating the lock.")
            continue

        live = rebuild_from_github(scen["source_issue"],
                                   scen.get("source_comments") or [])
        if live is None:
            unchecked.append(sid)
            continue
        if sha(live) != disk_hash:
            failures.append(
                f"{sid}: committed source has DRIFTED from GitHub issue "
                f"#{scen['source_issue']}. The facts were verified against text "
                f"that upstream no longer says.")
            continue
        print(f"  ok  {sid}: capture matches issue #{scen['source_issue']} "
              f"and its pinned hash")

    for msg in failures:
        print(f"  ✗ {msg}", file=sys.stderr)

    if failures:
        print("PROVENANCE CHECK FAILED.", file=sys.stderr)
        return 1
    if unchecked:
        print(f"Could not reach GitHub for: {', '.join(unchecked)}")
        print("The pinned hash matched the committed file, but upstream was NOT "
              "re-checked.")
        print("Exiting 2 (indeterminate) rather than 0.")
        return 2
    print("PROVENANCE CHECK PASSED — captured sources match upstream, not just "
          "themselves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
