"""Read final-homework notebooks and the stored inspection records.

Does not execute notebook code, and does not modify notebooks, extraction
JSON, or scoring files. Writes a derived file the findings page can load.

    python scripts/extract_notebook_evidence.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data_sources_2026" / "Final Ödevi Dokümanları"
PUB = ROOT / "mmla_explorer" / "site" / "downloads" / "notebooks" / "final"
EXT = ROOT / "worksheets" / "FINAL_LIZARD"
OUT = ROOT / "mmla_explorer" / "site" / "data" / "notebook_evidence.js"

STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel", "Marco", "Marcus",
    "Melinda", "Nadia", "Serena", "Shana", "Sheila", "Ulysses", "Zara",
]

CODE_MARKERS = [
    ("read_csv", "read_csv"),
    ("decision_tree", "DecisionTreeClassifier"),
    ("fit", ".fit("),
    ("predict", ".predict("),
    ("accuracy", "accuracy_score"),
    ("split", "train_test_split"),
    ("get_dummies", "get_dummies"),
    ("plot_tree", "plot_tree"),
    ("max_depth", "max_depth"),
    ("value_counts", "value_counts"),
    ("describe", ".describe("),
]

TASKS = [
    ("load", "Lizard table loaded"),
    ("explore", "Table summary stored"),
    ("notes", "Written notes on the table"),
    ("target", "Target column recorded"),
    ("question", "Written question stored"),
    ("split", "Train/test split recorded"),
    ("fitted", "Tree fitted"),
    ("depth_table", "Depth-search table stored"),
    ("drawing", "Tree drawing recorded"),
    ("reflection", "Written reflection stored"),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cell_source(cell: dict) -> str:
    src = cell.get("source") or []
    return src if isinstance(src, str) else "".join(src)


def tri_bool(value):
    if value is True:
        return "found"
    if value is False:
        return "not_found"
    return "undetermined"


def any_status(values):
    if any(v is True for v in values):
        return "found"
    if values and all(v is False for v in values):
        return "not_found"
    if values and all(v is None for v in values):
        return "undetermined"
    return "undetermined"


def text_present(value) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        raw = value.get("raw_text") or value.get("text")
        return isinstance(raw, str) and bool(raw.strip())
    return False


def text_status(values):
    if any(text_present(v) for v in values):
        return "found"
    return "not_found"


def structure_of(path: Path) -> dict:
    nb = load_json(path)
    cells = nb.get("cells") or []
    code = [c for c in cells if c.get("cell_type") == "code"]
    md = [c for c in cells if c.get("cell_type") == "markdown"]
    counts = [c.get("execution_count") for c in code]
    ran = [c for c in counts if c is not None]
    reversals = sum(1 for a, b in zip(ran, ran[1:]) if b < a)
    repeated = sorted({c for c in ran if ran.count(c) > 1})
    errors = []
    upload = False
    with_output = 0
    for cell in code:
        outputs = cell.get("outputs") or []
        if outputs:
            with_output += 1
        src = cell_source(cell)
        for output in outputs:
            if output.get("output_type") == "error":
                errors.append(output.get("ename") or "error")
                if "files.upload" in src or "drive.mount" in src:
                    upload = True
    blob = "\n".join(cell_source(c) for c in code)
    return {
        "code_cells": len(code),
        "markdown_cells": len(md),
        "total_cells": len(cells),
        "executed_code_cells": len(ran),
        "code_without_execution_count": len(code) - len(ran),
        "order_reversals": reversals,
        "repeated_execution_counts": len(repeated),
        "cells_with_output": with_output,
        "cells_with_image": sum(
            1 for cell in code
            if any("image/png" in (o.get("data") or {}) for o in (cell.get("outputs") or []))
        ),
        "cells_with_error": len(errors),
        "error_types": sorted(set(errors)),
        "upload_interrupt": upload,
        "code_present": {key: marker in blob for key, marker in CODE_MARKERS},
    }


def tasks_of(doc: dict) -> dict:
    step1 = doc.get("step1_data_exploration") or {}
    questions = doc.get("formulated_research_questions") or []
    split = doc.get("step3_split_global") or {}
    experiments = doc.get("dt_experiments") or []
    reflection = doc.get("step6_written_reflection") or {}
    fitted = [(e.get("code_evidence") or {}).get("model_fitted") for e in experiments]
    drawn = [(e.get("code_evidence") or {}).get("tree_visualized") for e in experiments]
    tables = [bool((e.get("depth_search") or {}).get("mcr_table")) for e in experiments]
    note_fields = [
        step1.get("q_lizard_count"),
        step1.get("q_habitat_most_frequent"),
        step1.get("q_habitat_least_frequent"),
        step1.get("q_imbalance_effect_reasoning"),
        step1.get("q_mass_by_species_reasoning"),
    ]
    return {
        "load": tri_bool(step1.get("data_loaded")),
        "explore": any_status([step1.get("value_counts_called"), step1.get("describe_called")]),
        "notes": text_status(note_fields),
        "target": "found" if questions else "not_found",
        "question": "found" if any(text_present(q.get("formulated_question")) for q in questions) else "not_found",
        "split": "found" if split.get("test_size") is not None else "not_found",
        "fitted": any_status(fitted) if experiments else "undetermined",
        "depth_table": ("found" if any(tables) else "not_found") if experiments else "undetermined",
        "drawing": any_status(drawn) if experiments else "undetermined",
        "reflection": text_status(list(reflection.values())) if reflection else "undetermined",
    }


def tri_from_bool(value):
    return tri_bool(value)


def reflection_text(block) -> bool:
    if not isinstance(block, dict):
        return text_present(block)
    return text_present(block.get("raw_text"))


def dimension_checks(doc: dict) -> dict:
    """Evidence status for the four rubric dimensions on page 8 of the assignment.

    found: the inspection stored the evidence.
    not_found: the inspection recorded that the evidence was absent.
    undetermined: the inspection did not record a yes or no.
    """
    step1 = doc.get("step1_data_exploration") or {}
    split = doc.get("step3_split_global") or {}
    experiments = doc.get("dt_experiments") or []
    reflection = doc.get("step6_written_reflection") or {}
    note_fields = [
        step1.get("q_lizard_count"),
        step1.get("q_habitat_most_frequent"),
        step1.get("q_imbalance_effect_reasoning"),
        step1.get("q_mass_by_species_reasoning"),
    ]
    dummies = [(e.get("code_evidence") or {}).get("used_get_dummies") for e in experiments]
    curves = [
        (e.get("code_evidence") or {}).get("train_curve_in_plot") is True
        and (e.get("code_evidence") or {}).get("test_curve_in_plot") is True
        for e in experiments
    ]
    comments = [
        any(text_present(v) for v in (e.get("step4_markdown_analysis") or {}).values())
        for e in experiments
    ]
    rows = []
    drawings = 0
    root_written = 0
    root_plot = 0
    decision_notes = 0
    codap_notes = 0
    test_mcr_n = 0
    tables = 0
    for exp in experiments:
        ce = exp.get("code_evidence") or {}
        search = exp.get("depth_search") or {}
        final = exp.get("step5_final_tree") or {}
        if ce.get("tree_visualized") is True:
            drawings += 1
        if text_present(final.get("q_root_node_reasoning")):
            root_written += 1
        if final.get("root_node_feature_source") == "plot_label":
            root_plot += 1
        if text_present(final.get("q_decisions_to_classify")):
            decision_notes += 1
        if text_present(final.get("q_codap_comparison")):
            codap_notes += 1
        if final.get("test_mcr_achieved") is not None:
            test_mcr_n += 1
        if search.get("mcr_table"):
            tables += 1
        mcr = final.get("test_mcr_achieved")
        rows.append({
            "target": exp.get("target_variable"),
            "chosen_depth": final.get("chosen_optimal_depth"),
            "test_mcr": mcr if isinstance(mcr, (int, float)) and 0 <= mcr <= 1 else None,
            "test_mcr_stored": final.get("test_mcr_achieved") is not None,
            "table": bool(search.get("mcr_table")),
            "both_curves": ce.get("train_curve_in_plot") is True and ce.get("test_curve_in_plot") is True,
            "drawing": ce.get("tree_visualized") is True,
        })
    q1 = reflection.get("q1_learning_journey") or {}
    q2 = reflection.get("q2_data_understanding") or {}
    q3 = reflection.get("q3_model_performance") or {}
    q4 = reflection.get("q4_dt_limitations") or {}
    envs = q1.get("environments_mentioned") if isinstance(q1, dict) else []
    if not isinstance(envs, list):
        envs = []
    n = len(experiments)

    def any_found(flags):
        if any(v is True for v in flags):
            return "found"
        if n and all(v is False for v in flags):
            return "not_found"
        if not n:
            return "undetermined"
        return "undetermined"

    return {
        "loaded": tri_from_bool(step1.get("data_loaded")),
        "value_counts": tri_from_bool(step1.get("value_counts_called")),
        "describe": tri_from_bool(step1.get("describe_called")),
        "table_notes": "found" if any(text_present(v) for v in note_fields) else "not_found",
        "table_notes_n": sum(1 for v in note_fields if text_present(v)),
        "encoding": any_found(dummies),
        "test_size": split.get("test_size"),
        "random_state": split.get("random_state"),
        "stratify": "found" if split.get("stratify_used") is True else "not_found" if split.get("stratify_used") is False else "undetermined",
        "stratify_note": "found" if text_present(split.get("q_stratify_removal_effect")) else "not_found",
        "random_note": "found" if text_present(split.get("q_random_state_change_effect")) else "not_found",
        "depth_tables": tables,
        "depth_records": n,
        "both_curves": sum(1 for v in curves if v),
        "depth_comments": sum(1 for v in comments if v),
        "test_mcr_n": test_mcr_n,
        "drawings": drawings,
        "root_written": root_written,
        "root_from_plot": root_plot,
        "decision_notes": decision_notes,
        "codap_notes": codap_notes,
        "reflection": {
            "settings": "found" if reflection_text(q1) else "not_found",
            "data": "found" if reflection_text(q2) else "not_found",
            "performance": "found" if reflection_text(q3) else "not_found",
            "limits": "found" if reflection_text(q4) else "not_found",
            "environments": envs,
            "all_three": set(envs) >= {"data_cards", "codap", "python"},
        },
        "models": rows,
    }


def inspection_of(doc: dict) -> dict:
    experiments = doc.get("dt_experiments") or []
    preliminary = doc.get("preliminary_quick_models") or []
    questions = doc.get("formulated_research_questions") or []
    split = doc.get("step3_split_global") or {}
    source = doc.get("data_source") or {}
    meta = doc.get("metadata") or {}
    depths = []
    tables = 0
    for exp in experiments:
        search = exp.get("depth_search") or {}
        final = exp.get("step5_final_tree") or {}
        if search.get("mcr_table"):
            tables += 1
        depths.append({
            "target": exp.get("target_variable"),
            "min": search.get("depth_range_min"),
            "max": search.get("depth_range_max"),
            "chosen": final.get("chosen_optimal_depth"),
            "table": bool(search.get("mcr_table")),
        })
    return {
        "stored_model_count": meta.get("total_models_created"),
        "inspection_code_cells": meta.get("code_cells"),
        "inspection_markdown_cells": meta.get("markdown_cells"),
        "targets": [q.get("target_variable") for q in questions],
        "questions_written": sum(1 for q in questions if text_present(q.get("formulated_question"))),
        "depth_search_records": len(experiments),
        "preliminary_models": len(preliminary) if isinstance(preliminary, list) else 0,
        "depth_tables": tables,
        "depths": depths,
        "test_size": split.get("test_size"),
        "stratify": split.get("stratify_used"),
        "row_count": source.get("row_count_in_output"),
        "synthetic": source.get("synthetic_data_used"),
        "tasks": tasks_of(doc),
        "checks": dimension_checks(doc),
    }


def main() -> None:
    rows = []
    disagree = []
    for name in STUDENTS:
        doc = load_json(EXT / f"example_extracted_{name}.json")
        rec = {"student": name, "inspection": inspection_of(doc)}
        src = SRC / f"{name}.ipynb"
        pub = PUB / f"{name}.ipynb"
        if src.exists():
            file_rec = structure_of(src)
            if pub.exists():
                pub_rec = structure_of(pub)
                file_rec["public_copy_matches"] = (
                    pub_rec["code_cells"] == file_rec["code_cells"]
                    and pub_rec["markdown_cells"] == file_rec["markdown_cells"]
                    and pub_rec["cells_with_error"] == file_rec["cells_with_error"]
                )
            ins = rec["inspection"]
            file_rec["cell_count_matches_inspection"] = (
                file_rec["code_cells"] == ins["inspection_code_cells"]
                and file_rec["markdown_cells"] == ins["inspection_markdown_cells"]
            )
            if not file_rec["cell_count_matches_inspection"]:
                disagree.append(name)
            rec["kind"] = "notebook"
            rec["file"] = file_rec
        else:
            rec["kind"] = "report"
            rec["file"] = None
        rows.append(rec)

    payload = {
        "tasks": [{"id": i, "label": label} for i, label in TASKS],
        "cell_count_disagreements": disagree,
        "rows": rows,
    }
    OUT.write_text(
        "window.NOTEBOOK_EVIDENCE = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT.relative_to(ROOT)}")
    print("cell-count disagreements:", ", ".join(disagree) or "none")
    for rec in rows:
        ins = rec["inspection"]
        kind = rec["kind"]
        extra = ""
        if rec["file"]:
            f = rec["file"]
            extra = f" cells={f['code_cells']}/{f['markdown_cells']} rev={f['order_reversals']} err={f['error_types'] or '-'}"
        print(f"{rec['student']:8} {kind:8} models={ins['stored_model_count']} depth={ins['depth_search_records']} tables={ins['depth_tables']}{extra}")


if __name__ == "__main__":
    main()
