#!/usr/bin/env python3
"""Align 2025 motion frames to Analysis.docx observations with behavior codes.

Offline, deterministic pipeline (no Vision API):
  1. Load observation steps + expert screenshots under training_datasets/2025/
  2. Multi-label CODAP/Arbor behavior coding from Turkish expert text
  3. Aspect-band dHash match + monotonic DP: docx shot → video keyframe
  4. Emit coded training pairs + screen-change transition timelines

Output per student (under training_datasets/2025/<id>/):
  - <id>_behavior_coded_alignments.json / .jsonl
  - <id>_screen_change_timeline.json

Cohort rollup:
  - training_datasets/2025/cohort_behavior_alignment_summary.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
OUT_ROOT = REPO_ROOT / "training_datasets" / "2025"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

LOGGER = logging.getLogger("align_2025_behaviors")

DHASH_HIGH = 8
DHASH_MED = 12
DHASH_LOW = 18
BAND_STEPS = 6  # vertical band samples per frame (speed/quality tradeoff)
HASH_SIZE = (128, 64)


# ─────────────────────────────────────────────────────────────
# Behavior codebook — atomic CODAP/Arbor UI acts
# ─────────────────────────────────────────────────────────────

BEHAVIOR_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("LOAD_DATASET", re.compile(r"dataset yüklen|Food Data|Food_Dataset|veri seti yüklen", re.I),
     "Dataset is loaded into CODAP/Arbor."),
    ("OPEN_ARBOR", re.compile(
        r"CODAP Arbor aç|yeni bir CODAP Arbor|Arbor’a|Arbor’a"
        r"|ekran kaydı.*(?:başlatılır|başlar)|CODAP arbor uzantısı ile başlar"
        r"|(?:önceki videodan|önceki videoda).*devam",
        re.I),
     "Arbor / CODAP workspace is opened or restarted."),
    ("TRAIN_TEST_SPLIT", re.compile(
        r"Choosy|training ve test|train(?:ing)?\s+ve\s+test|eğitim.*test"
        r"|[Tt]est dataseti.*geçilir|test data.*incelenir|training.*test.*data",
        re.I),
     "Train/test split is configured (often via Choosy)."),
    ("SET_TARGET_ATTRIBUTE", re.compile(r"Target attribute|Predict value olarak|hedef (?:değişken|attribute)", re.I),
     "Target / predict attribute is set on the tree."),
    ("CREATE_GRAPH", re.compile(r"Grafik oluşturulur|grafik oluşturul|bir grafik oluştur|Table.*mosaic|mosaic.*networks", re.I),
     "A CODAP graph panel is created."),
    ("CLOSE_GRAPH", re.compile(r"Grafik kapatılır", re.I),
     "Graph panel is closed."),
    ("SET_AXIS", re.compile(
        r"[xy]-eksenine|x-eksen|y-eksen"
        r"|[Gg]rafiğin üzer(?:ine|indeki)[^\n]{0,60}bırakılır",
        re.I),
     "Graph axis attribute is assigned or changed."),
    ("SWAP_AXES", re.compile(r"ekseni ile y-ekseni yer|eksenlerinin yeri|yer değiştirilir", re.I),
     "Graph axes are swapped."),
    ("ADD_MOVABLE_VALUE", re.compile(r"Movable value eklenir|movable line oluşturulur|Movable line", re.I),
     "Movable value / reference line is added on the graph."),
    ("UPDATE_MOVABLE_VALUE", re.compile(
        r"Movable value\s+[\d.]+\s+yerine|Movable value\s+[\d.]+\s+olarak|Movable value .*güncellenir", re.I),
     "Movable value position is updated (visual threshold probe on graph)."),
    ("DRAG_SPLIT_ATTRIBUTE", re.compile(
        r"(?:Depth\s*\d+|DT[‘’]?(?:nin|de|deki)?|sol node|sağ node)[^\n]{0,120}sürüklenir|"
        r"sürüklenir[^\n]{0,40}(?:Depth|node)|predictor olarak"
        r"|(?:training veri seti|yalnızca training) ile DT oluşturulur", re.I),
     "A predictor attribute is dragged onto a tree depth/node."),
    ("UPDATE_THRESHOLD", re.compile(r"Threshold value|threshold değeri|threshold value", re.I),
     "Numeric split threshold on the tree is changed."),
    ("ASSIGN_LEAF_LABEL", re.compile(r"nerenin recommendable|recommendable or not|nor recommendable", re.I),
     "Leaf / side of a split is labeled recommendable vs not."),
    ("EMIT_TREE", re.compile(r"Emit function", re.I),
     "Emit function writes the current tree into Classification Tree Records."),
    ("DELETE_TREE_OR_CTR_ROW", re.compile(
        r"karar ağacı silinir|Classification Tree Records.*(silinir|temizlenir)|satır silinir|satırı temizlenir"
        r"|\bDT temizlenir\b",
        re.I),
     "Tree is cleared or a CTR row is deleted."),
    ("SELECT_CTR_ROW", re.compile(
        r"Classification Tree Records.*(seçilir|gösterir|açılır|geçilir)|\bCTR\b"
        r"|Classification Tree Records.*\d+\.\s*(?:DT|satır)"
        r"|\d+\.\s*[Ss]atırdaki\s+DT",
        re.I),
     "A saved tree row in Classification Tree Records is selected/inspected."),
    ("INTERPRET_METRICS", re.compile(
        r"\bMCR\b|sensitivity|accuracy|misclassification|Confusion Matrix"
        r"|doğru sınıflandırma oranı",
        re.I),
     "Performance metrics are referenced or compared."),
    ("COMPARE_MODELS", re.compile(r"daha iyi|en iyi sonuç|hangisinin|karşılaştır|modeli seç", re.I),
     "Student compares alternative models / trees."),
    ("SEEK_HELP_OR_DIALOGUE", re.compile(
        r"Öğrenci “|Oğuz Hoca|Merve “|Hocam"
        r"|\" der (?:ve )?(?:arkadaşı|öğrenci|hoca)",
        re.I),
     "Verbal help-seeking or teacher–student dialogue is recorded."),
    ("COLOR_OR_STYLE_GRAPH", re.compile(r"renkleri düzenlenir|renkleri değiştirilir", re.I),
     "Graph colors / visual styling are adjusted."),
    ("IMPORT_TREE", re.compile(
        r"URL kullanılarak DT import|DT import edilir|tree import|ağaç import",
        re.I),
     "Student attempts to import a saved tree via URL (may succeed or error)."),
    ("ERROR_SCREEN", re.compile(
        r"hatası alınır|IP adresi bulunamadı|404 hatası|bağlantı hatası|sunucu.*bulunamadı",
        re.I),
     "An error message or failed network request appears on screen."),
]

COGNITIVE_FROM_BEHAVIOR: dict[str, str] = {
    "LOAD_DATASET": "EXPLORE", "OPEN_ARBOR": "EXPLORE", "TRAIN_TEST_SPLIT": "EXPLORE",
    "CREATE_GRAPH": "EXPLORE", "SET_AXIS": "EXPLORE", "SWAP_AXES": "EXPLORE", "CLOSE_GRAPH": "EXPLORE",
    "COLOR_OR_STYLE_GRAPH": "EXPLORE",
    "ADD_MOVABLE_VALUE": "TUNE", "UPDATE_MOVABLE_VALUE": "TUNE", "DRAG_SPLIT_ATTRIBUTE": "TUNE",
    "UPDATE_THRESHOLD": "TUNE", "ASSIGN_LEAF_LABEL": "TUNE", "SET_TARGET_ATTRIBUTE": "TUNE",
    "DELETE_TREE_OR_CTR_ROW": "TUNE",
    "EMIT_TREE": "EVALUATE", "SELECT_CTR_ROW": "EVALUATE", "INTERPRET_METRICS": "EVALUATE",
    "COMPARE_MODELS": "EVALUATE", "SEEK_HELP_OR_DIALOGUE": "EVALUATE",
    "IMPORT_TREE": "EVALUATE",
    "ERROR_SCREEN": "EXPLORE",
}

SCREEN_CHANGE_HINTS: dict[str, str] = {
    "LOAD_DATASET": "Table/case-card region populates with Food Data attributes and rows.",
    "OPEN_ARBOR": "Arbor tree canvas appears empty/reset; plugin chrome becomes visible.",
    "TRAIN_TEST_SPLIT": "Case tags / Choosy UI for train vs test becomes visible.",
    "SET_TARGET_ATTRIBUTE": "Tree root shows selected dependent variable name.",
    "CREATE_GRAPH": "New CODAP graph panel opens (often beside Arbor).",
    "SET_AXIS": "Graph marks/points reconfigure to the assigned X/Y attribute.",
    "SWAP_AXES": "Graph orientation flips; clusters rearrange.",
    "ADD_MOVABLE_VALUE": "A movable reference line appears on the graph.",
    "UPDATE_MOVABLE_VALUE": "Movable line shifts; case partitions on either side change.",
    "DRAG_SPLIT_ATTRIBUTE": "Tree node gains a split attribute and child branches appear/update.",
    "UPDATE_THRESHOLD": "Split cut-point text/value on the node changes; leaf purity may change.",
    "ASSIGN_LEAF_LABEL": "Leaf badges show recommendable / not recommendable.",
    "EMIT_TREE": "Classification Tree Records gains/updates a row with metrics.",
    "DELETE_TREE_OR_CTR_ROW": "Tree canvas clears or a CTR row disappears.",
    "SELECT_CTR_ROW": "CTR highlight changes; reconstructed tree may reload on canvas.",
    "INTERPRET_METRICS": "Attention is on MCR/sensitivity/accuracy numerals in CTR or plugins.",
    "COMPARE_MODELS": "Multiple CTR rows / trees are inspected in sequence.",
    "SEEK_HELP_OR_DIALOGUE": "Screen may be static while conversation occurs.",
    "COLOR_OR_STYLE_GRAPH": "Point colors/legends on the graph change.",
    "CLOSE_GRAPH": "Graph panel disappears from the workspace.",
    "IMPORT_TREE": "URL import dialog or loading state visible; may show success or error.",
    "ERROR_SCREEN": "Browser error overlay, 404 page, or CODAP connection-failed message visible.",
}


def code_behaviors(text: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for code, pat, gloss in BEHAVIOR_RULES:
        if code in seen:
            continue
        if pat.search(text):
            seen.add(code)
            found.append({
                "code": code,
                "gloss": gloss,
                "screen_change": SCREEN_CHANGE_HINTS.get(code, ""),
            })
    return found


def cognitive_from_codes(codes: list[str], fallback: str) -> str:
    ranks = {"MISCONCEPTION": 4, "EVALUATE": 3, "TUNE": 2, "EXPLORE": 1}
    best, best_r = fallback, ranks.get(fallback, 0)
    for c in codes:
        mapped = COGNITIVE_FROM_BEHAVIOR.get(c)
        if mapped and ranks.get(mapped, 0) > best_r:
            best, best_r = mapped, ranks[mapped]
    return best


def strategy_from_text(text: str, codes: list[str]) -> str:
    if re.search(r"rastgele|sırayla arttır|sırayla azalt|arttırılıp azalt|deneme", text, re.I):
        return "Trial-and-error"
    if re.search(r"karar veremedim|hangisinin daha iyi|bilmiyorum", text, re.I):
        return "Random guessing"
    if "UPDATE_MOVABLE_VALUE" in codes or "UPDATE_THRESHOLD" in codes:
        if re.search(r"Energy|Salt|Fat|Sugar|Protein|Carbohydrate|Tuz|Enerji", text, re.I):
            return "Domain-knowledge driven"
        return "Trial-and-error"
    return "Domain-knowledge driven"


def lo_from_text(text: str, codes: list[str]) -> str:
    if re.search(r"MCR.*sensitivity|neden.*seç|gerekçe|daha iyi.*model", text, re.I):
        return "Deepen"
    if "INTERPRET_METRICS" in codes and "COMPARE_MODELS" in codes:
        return "Deepen"
    if re.search(r"yeni bir karar ağacı|bağımsız", text, re.I):
        return "Create"
    if codes:
        return "Acquire"
    return "None"


# ─────────────────────────────────────────────────────────────
# Image similarity
# ─────────────────────────────────────────────────────────────

def _open_rgb(path: Path):
    from PIL import Image
    return Image.open(path).convert("RGB")


def _dhash(im) -> Any:
    import imagehash
    return imagehash.dhash(im.resize(HASH_SIZE))


def band_min_distance(shot_im, frame_im, *, steps: int = BAND_STEPS) -> tuple[int, int, int]:
    sw, sh = shot_im.size
    fw, fh = frame_im.size
    aspect = max(sw / max(sh, 1), 1e-6)
    band_h = int(round(fw / aspect))
    if band_h >= fh:
        band_h = fh
        ys = [0]
    else:
        ys = [int(i * (fh - band_h) / max(steps - 1, 1)) for i in range(steps)]
    shot_hash = _dhash(shot_im)
    best_d, best_y = 10**9, 0
    for y in ys:
        crop = frame_im.crop((0, y, fw, y + band_h))
        d = int(shot_hash - _dhash(crop))
        if d < best_d:
            best_d, best_y = d, y
    return best_d, best_y, band_h


def build_frame_index(frames_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not frames_dir.is_dir():
        return items
    for path in sorted(frames_dir.glob("frame_*.jpg")):
        m = re.search(r"(\d+)$", path.stem)
        items.append({
            "frame_id": path.stem,
            "frame_number": int(m.group(1)) if m else None,
            "path": path.name,
            "abs_path": path,
        })
    return items


def confidence_from_dhash(d: int | None) -> str:
    if d is None:
        return "none"
    if d <= DHASH_HIGH:
        return "high"
    if d <= DHASH_MED:
        return "medium"
    if d <= DHASH_LOW:
        return "low"
    return "weak"


def cost_matrix(shot_paths: list[Path | None], frame_index: list[dict[str, Any]]) -> list[list[int]]:
    n, m = len(shot_paths), len(frame_index)
    if n == 0 or m == 0:
        return [[] for _ in range(n)]
    frames_img: list[Any] = []
    for fr in frame_index:
        try:
            frames_img.append(_open_rgb(fr["abs_path"]))
        except Exception:
            frames_img.append(None)
    costs: list[list[int]] = []
    for si, shot_path in enumerate(shot_paths):
        row = [10**6] * m
        if shot_path is not None and shot_path.is_file():
            try:
                shot_im = _open_rgb(shot_path)
                for j, fim in enumerate(frames_img):
                    if fim is None:
                        continue
                    d, _, _ = band_min_distance(shot_im, fim)
                    row[j] = d
            except Exception as exc:
                LOGGER.warning("shot cost failed %s: %s", shot_path, exc)
        costs.append(row)
        if (si + 1) % 10 == 0 or si + 1 == n:
            LOGGER.info("  cost matrix shot %d/%d", si + 1, n)
    return costs


def monotonic_assign(costs: list[list[int]]) -> list[int | None]:
    n = len(costs)
    if n == 0:
        return []
    m = len(costs[0]) if costs[0] else 0
    if m == 0:
        return [None] * n
    INF = 10**12
    dp = [[INF] * m for _ in range(n)]
    prev: list[list[int | None]] = [[None] * m for _ in range(n)]
    for j in range(m):
        dp[0][j] = costs[0][j]
    for i in range(1, n):
        run_min, run_arg = INF, None
        for j in range(m):
            if dp[i - 1][j] < run_min:
                run_min, run_arg = dp[i - 1][j], j
            dp[i][j] = costs[i][j] + run_min
            prev[i][j] = run_arg
    end_j = min(range(m), key=lambda j: dp[n - 1][j])
    assign: list[int | None] = [None] * n
    j: int | None = end_j
    for i in range(n - 1, -1, -1):
        assign[i] = j
        if i == 0 or j is None:
            break
        j = prev[i][j]
    return assign


def regularize_costs_temporal(
    base_costs: list[list[int]],
    *,
    temporal_weight: float = 10.0,
) -> list[list[float]]:
    """Blend visual dHash with expected timeline position."""
    n = len(base_costs)
    if n == 0:
        return []
    m = len(base_costs[0]) if base_costs[0] else 0
    out: list[list[float]] = []
    for i in range(n):
        expected = (i + 0.5) / n * max(m - 1, 0)
        out.append([
            float(base_costs[i][j]) + temporal_weight * abs(j - expected)
            for j in range(m)
        ])
    return out


def monotonic_unique_assign(
    costs: list[list[float]] | list[list[int]],
    *,
    prefer_unique: bool = True,
    inactive_threshold: float = 1e5,
    reuse_penalty: float = 6.0,
) -> list[int | None]:
    """Forward assign for *active* (screenshot) rows only.

    - Text-only / missing-shot rows (all costs ≥ inactive_threshold) → None
      so they do not steal timeline slots from gold pairs.
    - Soft uniqueness: reuse is allowed but penalized (hard unique hurt visual
      fidelity when screenshots cluster in one phase of the session).
    - Non-decreasing in time among active rows (plateau = same frame allowed).
    """
    n = len(costs)
    if n == 0:
        return []
    m = len(costs[0]) if costs[0] else 0
    if m == 0:
        return [None] * n

    active = [
        i for i in range(n)
        if costs[i] and min(float(c) for c in costs[i]) < inactive_threshold
    ]
    assign: list[int | None] = [None] * n
    if not active:
        return assign

    used: set[int] = set()
    prev = -1
    big = 1e18

    for i in active:
        best_j = None
        best_c = big
        lo = max(prev, 0)
        for j in range(lo, m):
            c = float(costs[i][j])
            if prefer_unique and j in used:
                c += reuse_penalty
            if c < best_c:
                best_c = c
                best_j = j
        if best_j is None:
            # No feasible forward frame — rare; search full row by raw cost
            best_j = min(range(m), key=lambda jj: float(costs[i][jj]))
            best_c = float(costs[i][best_j])
        # Reject inactive matches (no real visual candidate)
        if best_c >= inactive_threshold and float(costs[i][best_j]) >= inactive_threshold:
            assign[i] = None
            continue
        assign[i] = best_j
        used.add(best_j)
        prev = best_j
    return assign


def seed_lock_assign(
    raw_costs: list[list[int]],
    reg_costs: list[list[float]] | list[list[int]],
    *,
    lock_hamming: int = 12,
    inactive_threshold: float = 1e5,
    reuse_penalty: float = 6.0,
) -> list[int | None]:
    """Preserve strong visual matches, then fill residual steps temporally.

    Pass 1 — lock any screenshot whose unconstrained best band-dHash ≤ lock_hamming
    (high/medium visual fidelity must not be sacrificed for timeline smoothness).

    Pass 2 — fill unlocked active steps with soft-unique forward assign on
    regularized costs, preferring frames not already locked.
    """
    n = len(raw_costs)
    if n == 0:
        return []
    m = len(raw_costs[0]) if raw_costs[0] else 0
    if m == 0:
        return [None] * n

    assign: list[int | None] = [None] * n
    locked_frames: set[int] = set()
    unlocked: list[int] = []

    for i in range(n):
        row = raw_costs[i]
        if not row:
            continue
        best_j = min(range(m), key=lambda j: row[j])
        ham = int(row[best_j])
        if ham >= inactive_threshold:
            continue
        if ham <= lock_hamming:
            assign[i] = best_j
            locked_frames.add(best_j)
        else:
            unlocked.append(i)

    if not unlocked:
        return assign

    # Build a cost view for unlocked fill: heavily penalize locked frames
    fill_costs: list[list[float]] = []
    fill_index_map: list[int] = []
    for i in unlocked:
        fill_index_map.append(i)
        row = []
        for j in range(m):
            c = float(reg_costs[i][j]) if reg_costs[i] else float(raw_costs[i][j])
            if j in locked_frames:
                c += 40.0  # strong preference not to steal locked high-quality frames
            row.append(c)
        fill_costs.append(row)

    fill_assign = monotonic_unique_assign(
        fill_costs,
        prefer_unique=True,
        inactive_threshold=inactive_threshold,
        reuse_penalty=reuse_penalty,
    )
    for k, i in enumerate(fill_index_map):
        assign[i] = fill_assign[k]
    return assign


def detect_frozen_frame_index(frame_index: list[dict[str, Any]]) -> bool:
    """True when keyframes are essentially one still (e.g. Edgar)."""
    if len(frame_index) <= 1:
        return len(frame_index) == 1
    try:
        from PIL import Image
        import imagehash

        samples = [frame_index[0], frame_index[len(frame_index) // 2], frame_index[-1]]
        hashes = []
        for fr in samples:
            with Image.open(fr["abs_path"]) as im:
                hashes.append(imagehash.dhash(im.convert("RGB").resize((128, 64))))
        return all((hashes[a] - hashes[b]) <= 2 for a in range(3) for b in range(a + 1, 3))
    except Exception:
        return False


def match_result_for(
    frame_index: list[dict[str, Any]],
    frame_j: int | None,
    cost: int | None,
) -> dict[str, Any]:
    if frame_j is None or not frame_index or cost is None or cost >= 10**5:
        return {
            "matched": False,
            "reason": "unassigned_or_missing",
            "best_frame_id": None,
            "best_frame_file": None,
            "frame_number": None,
            "hamming": None,
            "confidence": "none",
            "method": "aspect_band_dhash+monotonic_dp",
        }
    fr = frame_index[frame_j]
    conf = confidence_from_dhash(int(cost))
    return {
        "matched": conf in {"high", "medium", "low"},
        "reason": "aspect_band_dhash_monotonic",
        "best_frame_id": fr["frame_id"],
        "best_frame_file": fr["path"],
        "frame_number": fr["frame_number"],
        "hamming": int(cost),
        "confidence": conf,
        "method": "aspect_band_dhash+monotonic_dp",
        "frame_index": frame_j,
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def timestamp_for_frame(manifest: dict[str, Any] | None, frame_id: str | None) -> float | None:
    if not manifest or not frame_id:
        return None
    for fr in manifest.get("frames") or []:
        if fr.get("frame_id") == frame_id:
            return float(fr.get("source_timestamp_seconds"))
    return None


def build_timeline(alignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    prev_codes: list[str] = []
    for row in alignments:
        codes = [b["code"] for b in row["behavior_codes"]]
        added = [c for c in codes if c not in prev_codes]
        events.append({
            "step_index": row["metadata"]["observation_step_index"],
            "behavior_codes": codes,
            "new_behaviors_vs_prev_step": added,
            "screen_change_notes": [b["screen_change"] for b in row["behavior_codes"]],
            "expert_screenshot": row["metadata"].get("expert_screenshot"),
            "matched_video_frame": row["metadata"].get("matched_frame_id"),
            "match_confidence": row["alignment"].get("confidence"),
            "hamming": row["alignment"].get("hamming"),
            "uzman_nitel_gözlemi": row["ground_truth_labels"]["uzman_nitel_gözlemi"],
        })
        prev_codes = codes
    return events


def process_student(student_id: str) -> dict[str, Any]:
    out_dir = OUT_ROOT / student_id
    steps_path = out_dir / f"{student_id}_observation_steps.json"
    if not steps_path.is_file():
        from build_2025_mmla_training_dataset import process_student as rebuild
        rebuild(student_id)
    if not steps_path.is_file():
        return {"student_id": student_id, "status": "skipped", "reason": "missing_observation_steps"}

    steps_doc = load_json(steps_path)
    steps = steps_doc.get("observation_steps") or []
    docx_shots = {
        int(s["shot_index"]): s
        for s in (steps_doc.get("docx_screenshots") or [])
        if "shot_index" in s
    }

    manifest_path = out_dir / f"{student_id}_video_extraction_manifest.json"
    manifest = load_json(manifest_path) if manifest_path.is_file() else None
    frame_index = build_frame_index(out_dir / f"{student_id}_frames")
    LOGGER.info("[%s] %d steps × %d frames — building cost matrix", student_id, len(steps), len(frame_index))

    shot_paths: list[Path | None] = []
    for step in steps:
        shot_i = step.get("docx_shot_index")
        shot_meta = docx_shots.get(shot_i) if isinstance(shot_i, int) else None
        shot_paths.append(out_dir / shot_meta["path"] if shot_meta else None)

    costs = cost_matrix(shot_paths, frame_index)
    assign = monotonic_assign(costs) if frame_index else [None] * len(steps)

    alignments: list[dict[str, Any]] = []
    conf_hist: Counter[str] = Counter()
    behavior_hist: Counter[str] = Counter()

    for i, step in enumerate(steps):
        text = step["uzman_nitel_gözlemi"]
        behaviors = code_behaviors(text)
        codes = [b["code"] for b in behaviors]
        for c in codes:
            behavior_hist[c] += 1

        cognitive = cognitive_from_codes(
            codes, step.get("labels", {}).get("bilişsel_davranış_kategorisi", "EXPLORE")
        )
        strategy = strategy_from_text(text, codes)
        lo = lo_from_text(text, codes)

        shot_i = step.get("docx_shot_index")
        shot_meta = docx_shots.get(shot_i) if isinstance(shot_i, int) else None
        shot_rel = shot_meta["path"] if shot_meta else None

        fj = assign[i] if i < len(assign) else None
        cost = costs[i][fj] if fj is not None and costs and costs[i] else None
        match = match_result_for(frame_index, fj, cost) if shot_rel else {
            "matched": False,
            "reason": "no_docx_shot",
            "best_frame_id": None,
            "best_frame_file": None,
            "frame_number": None,
            "hamming": None,
            "confidence": "none",
            "method": "aspect_band_dhash+monotonic_dp",
        }
        conf_hist[match.get("confidence") or "none"] += 1

        frame_id = match.get("best_frame_id")
        ts = timestamp_for_frame(manifest, frame_id)
        frame_image = f"{student_id}_frames/{frame_id}.jpg" if frame_id else None

        justification = (
            f"Uzman metni davranış kodları {codes or ['(none)']} ile etiketlendi. "
            f"Görsel GT: Word ekranı ({shot_rel}). "
            f"Video eşlemesi: aspect-band dHash hamming={match.get('hamming')} "
            f"confidence={match.get('confidence')} → {frame_id} (monotonic DP)."
        )
        for b in behaviors:
            if b["screen_change"]:
                justification += f" Ekran değişimi ({b['code']}): {b['screen_change']}"

        alignments.append({
            "training_sample_id": f"2025_{student_id}_beh_{step['step_index']:04d}",
            "metadata": {
                "cohort_year": 2025,
                "student_id": student_id,
                "observation_step_index": step["step_index"],
                "expert_screenshot": shot_rel,
                "matched_frame_id": frame_id,
                "matched_frame_image": frame_image,
                "timestamp_ms": int(round(ts * 1000)) if ts is not None else None,
                "alignment_method": "docx_aspect_band_dhash_monotonic_dp",
            },
            "alignment": match,
            "behavior_codes": behaviors,
            "behavior_code_list": codes,
            "multimodal_inputs": {
                "görsel_ekran_durumu": {
                    "expert_screenshot": shot_rel,
                    "matched_video_frame": frame_image,
                    "match_confidence": match.get("confidence"),
                    "active_behaviors": codes,
                },
                "sistem_logu": {
                    "last_action": codes[-1] if codes else None,
                    "action_sequence_step": codes,
                    "note": "2025 CSV log yok; eylemler uzman gözlem + davranış kodundan türetilir.",
                },
            },
            "ground_truth_labels": {
                "uzman_nitel_gözlemi": text,
                "bilişsel_davranış_kategorisi": cognitive,
                "pedagojik_strateji": strategy,
                "unesco_ai_cft_level": lo,
                "ai_cft_evidence_justification": justification,
                "sequence_pattern": step.get("sequence_pattern"),
            },
            "screen_change_learning": {
                "expected_visual_effects": [b["screen_change"] for b in behaviors if b["screen_change"]],
                "primary_behavior": codes[0] if codes else None,
            },
        })

    timeline = build_timeline(alignments)
    payload = {
        "student_id": student_id,
        "cohort_year": 2025,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": {
            "behavior_coding": "rule_based_turkish_observation_codebook_v1",
            "visual_alignment": "aspect_band_dhash+monotonic_dp",
            "dhash_bands": {"high": DHASH_HIGH, "medium": DHASH_MED, "low": DHASH_LOW},
        },
        "frame_index_size": len(frame_index),
        "step_count": len(alignments),
        "match_confidence_histogram": dict(conf_hist),
        "behavior_histogram": dict(behavior_hist),
        "alignments": alignments,
    }
    write_json(out_dir / f"{student_id}_behavior_coded_alignments.json", payload)
    write_jsonl(out_dir / f"{student_id}_behavior_coded_alignments.jsonl", alignments)
    write_json(
        out_dir / f"{student_id}_screen_change_timeline.json",
        {
            "student_id": student_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "events": timeline,
        },
    )

    summary = {
        "student_id": student_id,
        "status": "ok",
        "steps": len(alignments),
        "frames_indexed": len(frame_index),
        "match_confidence_histogram": dict(conf_hist),
        "top_behaviors": behavior_hist.most_common(8),
        "high_or_medium_matches": conf_hist.get("high", 0) + conf_hist.get("medium", 0),
    }
    LOGGER.info(
        "[%s] %d steps; matches high=%d med=%d low=%d weak=%d",
        student_id,
        len(alignments),
        conf_hist.get("high", 0),
        conf_hist.get("medium", 0),
        conf_hist.get("low", 0),
        conf_hist.get("weak", 0) + conf_hist.get("none", 0),
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Code 2025 behaviors and align docx shots to frames")
    ap.add_argument("students", nargs="*")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.students:
        targets = args.students
    else:
        targets = [
            p.name for p in sorted(OUT_ROOT.iterdir())
            if p.is_dir() and not p.name.startswith(".")
            and ((p / f"{p.name}_observation_steps.json").exists() or (p / f"{p.name}_frames").is_dir())
        ]

    results = []
    for sid in targets:
        try:
            results.append(process_student(sid))
        except Exception as exc:
            LOGGER.exception("[%s] failed", sid)
            results.append({"student_id": sid, "status": "error", "error": str(exc)})

    write_json(OUT_ROOT / "cohort_behavior_alignment_summary.json", {
        "cohort_year": 2025,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "students": results,
        "codebook_size": len(BEHAVIOR_RULES),
        "behavior_codes": [c for c, _, _ in BEHAVIOR_RULES],
    })
    ok = sum(1 for r in results if r.get("status") == "ok")
    LOGGER.info("Done: %d/%d", ok, len(results))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
