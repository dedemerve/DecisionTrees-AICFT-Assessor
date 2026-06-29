"""
research_dashboard.py — Human-readable portfolio report for researchers.

Consumes portfolio.json (simple LO rubric layout); does not assign competency levels.
"""

from __future__ import annotations

from student_bundle import list_worksheets, load_portfolio, load_worksheet_summary_view


def render_portfolio_report(student_id: str) -> str:
    portfolio = load_portfolio(student_id)
    lines: list[str] = []

    lines.append(f"# Portfolio Review — {student_id}")
    lines.append("")
    lines.append(f"**Framework:** {portfolio.get('framework', '')}")
    lines.append(f"**Aspect:** {portfolio.get('aspect', '')}")
    lines.append(f"**Review mode:** {portfolio.get('methodology', {}).get('approach', 'simple_lo_rubric')}")
    lines.append("")
    lines.append(
        "> Competency levels are **not** auto-assigned. Use `lo_review_packets` and record "
        "`researcher_rubric_decisions` after reading the evidence."
    )
    lines.append("")

    decisions = portfolio.get("researcher_rubric_decisions", [])
    lines.append(f"## Researcher decisions recorded: {len(decisions)}")
    lines.append("")

    lines.append("## LO review packets (preview)")
    lines.append("")
    for lo in sorted(portfolio.get("lo_review_packets", {}))[:3]:
        packet = portfolio["lo_review_packets"][lo]
        preview = packet.splitlines()[:6]
        lines.append(f"### {lo}")
        lines.extend(preview)
        if len(packet.splitlines()) > 6:
            lines.append("…")
        lines.append("")

    lines.append("## Worksheet scorecard")
    lines.append("")
    lines.append("| Worksheet | Score | Review items | Blocked |")
    lines.append("|-----------|-------|--------------|---------|")
    for ws in list_worksheets(student_id):
        summary = load_worksheet_summary_view(student_id, ws)
        if not summary:
            continue
        total = summary.get("total_score")
        max_s = summary.get("max_score")
        score_s = f"{total}/{max_s}" if total is not None and max_s else "—"
        reviews = len(summary.get("review_items") or [])
        blocked = "yes" if summary.get("blocked") else "no"
        lines.append(f"| {ws} | {score_s} | {reviews} | {blocked} |")
    lines.append("")

    gaps = portfolio.get("data_gaps", [])
    if gaps:
        lines.append("## Data gaps (priority order)")
        lines.append("")
        for gap in gaps:
            items = gap.get("items", [])
            preview = ", ".join(items[:6])
            if len(items) > 6:
                preview += f", … (+{len(items) - 6})"
            lines.append(f"### P{gap.get('priority', '?')} — {gap['worksheet']}")
            lines.append(f"- **Why:** {gap.get('why', '')}")
            lines.append(f"- **Items:** {preview or '—'}")
            lines.append("")

    lines.append("---")
    lines.append("*Record final LO judgements in `researcher_rubric_decisions`.*")
    return "\n".join(lines)
