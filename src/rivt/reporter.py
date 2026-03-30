from __future__ import annotations

from rivt.models import Violation


def format_violations(violations: list[Violation]) -> str:
    if not violations:
        return ""

    lines = [f"{v.path}:{v.line}:{v.col}  {v.rule_id}  {v.message}" for v in violations]

    file_count = len({v.path for v in violations})
    viol_count = len(violations)
    lines.append("")
    lines.append(
        f"Found {viol_count} violation{'s' if viol_count != 1 else ''} "
        f"in {file_count} file{'s' if file_count != 1 else ''}."
    )
    return "\n".join(lines)
