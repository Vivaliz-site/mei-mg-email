#!/usr/bin/env python3
"""Prevent blanket human PR-review requests while retaining owner-only grants.

This deliberately does not remove security, CI, or branch protections. It only
checks repository files and fails closed when someone would re-add the owner as
a default reviewer for unrelated changes.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

HUMAN = '@shopvivaliz-human'
SECURITY_OWNERS = {
    '/security/owner-approvals/',
    '/docs/knowledge/security-approval-via-pr.md',
    '/scripts/validate-owner-pr-grant.py',
}
LOCATIONS = ('.github/CODEOWNERS', 'CODEOWNERS', 'docs/CODEOWNERS')
AUTO_REVIEW = re.compile(r'request[_-]reviewers|--add-reviewer|\breviewers\s*:', re.I)


def violations(root: Path) -> list[str]:
    errors: list[str] = []
    grant_covered = False
    for relative in LOCATIONS:
        path = root / relative
        if not path.is_file():
            continue
        for number, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            parts = raw.partition('#')[0].split()
            if len(parts) < 2 or HUMAN not in parts[1:]:
                continue
            if parts[0] not in SECURITY_OWNERS:
                errors.append(f'{relative}:{number}: human reviewer must not own {parts[0]!r}')
            if relative == '.github/CODEOWNERS' and parts[0] == '/security/owner-approvals/':
                grant_covered = True
    if not grant_covered:
        errors.append('.github/CODEOWNERS: security/owner-approvals/ needs human owner')
    for path in sorted((root / '.github/workflows').glob('*.yml')) + sorted((root / '.github/workflows').glob('*.yaml')):
        content = path.read_text(encoding='utf-8')
        if HUMAN.lstrip("@") in content and AUTO_REVIEW.search(content):
            errors.append(f'{path.relative_to(root)}: automated broad human review is forbidden; request review on a specific protected PR')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    args = parser.parse_args()
    found = violations(args.root)
    for message in found:
        print('OWNER_REVIEW_ROUTING=FAIL:', message)
    if found:
        return 1
    print('OWNER_REVIEW_ROUTING=PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
