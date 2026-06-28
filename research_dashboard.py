"""
research_dashboard.py — Human-readable portfolio report for researchers.

Consumes portfolio.json + worksheet summaries; does not re-score.
"""

from __future__ import annotations

from typing import Any

from student_bundle import artifact_payload, load_artifact, load_portfolio, list_worksheets


STRENGTH_ICON = {
    "strong": "■■■",
    "moderate": "■■□",
    "weak": "■□□",
    "none": "□□□",
}


def render_portfolio_report(student_id: str) -> str:
    portfolio = load_portfolio(student_id)
    lines: list[str] = []

    proposal = portfolio.get("ai_cft_proposal", {})
    level = proposal.get("Aspect3", "—")
    lines.append(f"# AI-CFT Portfolio Report — {student_id}")
    lines.append("")
    lines.append(f"**Framework:** {portfolio.get('framework', '')}")
    lines.append(f"**Aspect:** {portfolio.get('aspect', '')}")
    lines.append(f"**Proposed level (provisional):** {level}")
    lines.append("")
    lines.append(f"> {proposal.get('rationale', '')}")
    lines.append("")

    level_sum = portfolio.get("competency_level_summary", {})
    if level_sum:
        lines.append("## Competency level diagnostics")
        lines.append("")
        lines.append("| Level | Status |")
        lines.append("|-------|--------|")
        for lv in ("Acquire", "Deepen", "Create"):
            lines.append(f"| {lv} | {level_sum.get(lv, '—')} |")
        lines.append("")

    lines.append("## Learning object evidence (aggregated)")
    lines.append("")
    lines.append("| LO | Expected | Peak | Worksheets | Items | Mean conf. |")
    lines.append("|----|----------|------|------------|-------|------------|")
    for lo, data in sorted(portfolio.get("learning_objects", {}).items()):
        peak = data.get("peak_strength", "none")
        icon = STRENGTH_ICON.get(peak, peak)
        ws = ", ".join(data.get("contributing_worksheets", [])) or "—"
        conf = data.get("mean_confidence")
        conf_s = f"{conf:.2f}" if conf is not None else "—"
        lines.append(
            f"| {lo} | {data.get('expected_level', '')} | {icon} {peak} | "
            f"{ws} | {data.get('evidence_items', 0)} | {conf_s} |"
        )
    lines.append("")

    lines.append("## Worksheet scorecard")
    lines.append("")
    lines.append("| Worksheet | Score | Review items | Blocked |")
    lines.append("|-----------|-------|--------------|---------|")
    for ws in list_worksheets(student_id):
        summary = artifact_payload(load_artifact(student_id, ws, "summary"))
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
    baseline = portfolio.get("baseline_evidence", [])
    if baseline:
        lines.append("## Baseline / diagnostic evidence (excluded from LO peaks)")
        lines.append("")
        lines.append("| Worksheet | Item | LO | Strength | Type |")
        lines.append("|-----------|------|----|----------|------|")
        for rec in baseline[:12]:
            lines.append(
                f"| {rec['worksheet']} | {rec['item']} | {rec['lo']} | "
                f"{rec['strength']} | {rec['evidence_type']} |"
            )
        if len(baseline) > 12:
            lines.append(f"| … | +{len(baseline) - 12} more | | | |")
        lines.append("")

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
    lines.append(
        "*Final AI-CFT level is assigned by the researcher (`ai_cft_proposal.is_final` remains false).*"
    )
    return "\n".join(lines)
