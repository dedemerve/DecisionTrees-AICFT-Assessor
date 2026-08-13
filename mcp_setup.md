# AICFT MCP Server — Setup

## Install dependencies

```bash
cd /Users/mrved/Desktop/DecisionTrees-AICFT-Assessor
pip install -r requirements_mcp.txt
```

## Add to Claude Desktop

Open `~/Library/Application Support/Claude/claude_desktop_config.json` and add:

```json
{
  "mcpServers": {
    "aicft": {
      "command": "python3",
      "args": ["/Users/mrved/Desktop/DecisionTrees-AICFT-Assessor/aicft_mcp.py"],
      "env": {
        "AICFT_REPO": "/Users/mrved/Desktop/DecisionTrees-AICFT-Assessor"
      }
    }
  }
}
```

Restart Claude Desktop — the `aicft_*` tools will appear automatically.

## Available tools

| Tool | What it does |
|------|-------------|
| `aicft_list_students` | All 2026 cohort students + pipeline completion status |
| `aicft_get_student_portfolio` | AI-CFT LO evidence rollup per student |
| `aicft_get_worksheet_artifact` | extraction / scoring / evidence / validation JSON per WS |
| `aicft_get_homework_scores` | Colab notebook behavioural indicators (B1–B12) |
| `aicft_get_colab_notebook_summary` | Raw cell-by-cell notebook inspection |
| `aicft_get_log_features` | CODAP Arbor log file inventory + extraction guidance |
| `aicft_get_behavior_signals` | Screen recording inventory + 17-signal coding guide |
| `aicft_get_cohort_summary` | Cross-student AI-CFT evidence counts & gaps |
| `aicft_search_evidence` | Search evidence by LO, student, or keyword |
| `aicft_get_rubric_gaps` | 2026 rubric gap analysis |
| `aicft_get_framework` | Canonical AI-CFT assessment framework |
| `aicft_get_evidence_units` | Consolidated evidence_units.json per student |

## Verify (once mcp installed)

```bash
python3 aicft_mcp.py --help
```
