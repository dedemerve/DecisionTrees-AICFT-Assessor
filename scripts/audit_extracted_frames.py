#!/usr/bin/env python3
"""Comprehensive frame extraction audit.

Checks every student subdirectory under --audio-root for:
  1. File-system integrity   — missing paths, zero-byte files, permission errors
  2. Pixel-level corruption  — cv2.imread decode failures
  3. Aspect-ratio invariance — frame dimensions vs. manifest video_profile
  4. Manifest consistency    — frame list in JSON matches files on disk

Prints a markdown table to STDOUT and writes a machine-readable JSON report
to logs/audit_<date>.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR  = REPO_ROOT / "logs"

LOGGER = logging.getLogger("audit_frames")

# Aspect-ratio tolerance: allow ±0.5% to absorb JPEG rescaling rounding
AR_TOLERANCE = 0.005


# Keys that exist only in the legacy nested schema. Any record containing one
# of these is old-format and must NOT be reported as having null flat fields.
_OLD_SCHEMA_KEYS = frozenset({"screen_state", "behavioral_classification", "cognitive_indicators"})

# Required top-level keys in the current flat schema.
_REQUIRED_FLAT_KEYS = frozenset({
    "frame_id", "screen_context", "primary_behavior", "analysis_confidence",
})


@dataclass
class FrameIssue:
    frame_id: str
    file_path: str
    issue_type: str   # missing | zero_byte | permission | corrupt | ar_mismatch | format_mismatch | null_field
    detail: str


@dataclass
class JsonlIssue:
    frame_id: str
    issue_type: str   # format_mismatch | null_field
    detail: str


@dataclass
class StudentReport:
    student_id: str
    manifest_frame_count: int = 0
    disk_file_count: int      = 0
    missing_count: int        = 0
    zero_byte_count: int      = 0
    permission_count: int     = 0
    corrupt_count: int        = 0
    ar_mismatch_count: int    = 0
    jsonl_format_mismatch_count: int = 0
    jsonl_null_field_count: int      = 0
    issues: list[FrameIssue]  = field(default_factory=list)
    jsonl_issues: list[JsonlIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.missing_count              == 0
            and self.zero_byte_count        == 0
            and self.permission_count       == 0
            and self.corrupt_count          == 0
            and self.ar_mismatch_count      == 0
            and self.jsonl_format_mismatch_count == 0
            and self.jsonl_null_field_count == 0
        )

    @property
    def total_issues(self) -> int:
        return (
            self.missing_count
            + self.zero_byte_count
            + self.permission_count
            + self.corrupt_count
            + self.ar_mismatch_count
            + self.jsonl_format_mismatch_count
            + self.jsonl_null_field_count
        )


def _load_manifest(student_dir: Path, student_id: str) -> dict[str, Any] | None:
    path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        LOGGER.error("[%s] Cannot read manifest: %s", student_id, exc)
        return None


def _expected_ar(manifest: dict[str, Any]) -> float | None:
    profile = manifest.get("video_profile") or {}
    ar = profile.get("aspect_ratio")
    if ar:
        return float(ar)
    res = profile.get("native_resolution") or profile.get("extract_resolution")
    if res and len(res) == 2 and res[1]:
        return res[0] / res[1]
    return None


def _frame_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    # manifests may use "frames" or "segments"
    return manifest.get("frames") or manifest.get("segments") or []


def _resolve_frame_path(entry: dict[str, Any], student_dir: Path) -> Path:
    stored = entry.get("file_path") or ""
    if stored:
        candidate = REPO_ROOT / stored
        if candidate.is_file():
            return candidate
    frame_id = entry["frame_id"]
    return student_dir / f"{student_id_from_dir(student_dir)}_frames" / f"{frame_id}.jpg"


def student_id_from_dir(student_dir: Path) -> str:
    return student_dir.name


def _audit_jsonl_content(student_dir: Path, student_id: str, report: StudentReport) -> None:
    """Check JSONL analysis file for schema format issues.

    - format_mismatch: record uses old nested keys (screen_state etc.) and has not been migrated
    - null_field: record is new-format but is missing a required flat key
    """
    jsonl_path = student_dir / f"{student_id}_codap_frame_analyses.jsonl"
    if not jsonl_path.is_file():
        return

    seen_ids: dict[str, dict] = {}
    try:
        for raw in jsonl_path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            record = json.loads(raw)
            if not isinstance(record, dict):
                continue
            fid = str(record.get("frame_id") or record.get("frame_number") or "unknown")
            seen_ids[fid] = record  # last occurrence wins (mirrors dedupe)
    except Exception as exc:
        LOGGER.error("[%s] Cannot read JSONL %s: %s", student_id, jsonl_path.name, exc)
        return

    for fid, record in seen_ids.items():
        if _OLD_SCHEMA_KEYS & record.keys():
            report.jsonl_format_mismatch_count += 1
            old_keys = sorted(_OLD_SCHEMA_KEYS & record.keys())
            report.jsonl_issues.append(JsonlIssue(
                frame_id=fid,
                issue_type="format_mismatch",
                detail=f"Old nested schema keys present: {old_keys}. Run migration or re-analyze.",
            ))
        else:
            missing = sorted(_REQUIRED_FLAT_KEYS - record.keys())
            if missing:
                report.jsonl_null_field_count += 1
                report.jsonl_issues.append(JsonlIssue(
                    frame_id=fid,
                    issue_type="null_field",
                    detail=f"Required flat-schema fields missing: {missing}",
                ))


def audit_student(student_dir: Path, *, cv2_available: bool) -> StudentReport:
    student_id = student_id_from_dir(student_dir)
    report = StudentReport(student_id=student_id)

    manifest = _load_manifest(student_dir, student_id)
    if manifest is None:
        LOGGER.warning("[%s] No manifest found — skipping", student_id)
        return report

    entries = _frame_entries(manifest)
    report.manifest_frame_count = len(entries)

    frames_dir = student_dir / f"{student_id}_frames"
    if frames_dir.is_dir():
        report.disk_file_count = sum(1 for p in frames_dir.iterdir() if p.suffix.lower() == ".jpg")

    expected_ar = _expected_ar(manifest)

    for entry in entries:
        frame_id   = entry.get("frame_id", "unknown")
        frame_path = _resolve_frame_path(entry, student_dir)
        path_str   = str(frame_path)

        # 1. Missing
        if not frame_path.exists():
            report.missing_count += 1
            report.issues.append(FrameIssue(frame_id, path_str, "missing", "File does not exist on disk"))
            continue

        # 2. Permission
        if not os.access(frame_path, os.R_OK):
            report.permission_count += 1
            report.issues.append(FrameIssue(frame_id, path_str, "permission", "No read permission"))
            continue

        # 3. Zero-byte
        try:
            size = frame_path.stat().st_size
        except OSError as exc:
            report.permission_count += 1
            report.issues.append(FrameIssue(frame_id, path_str, "permission", str(exc)))
            continue

        if size == 0:
            report.zero_byte_count += 1
            report.issues.append(FrameIssue(frame_id, path_str, "zero_byte", "File is 0 bytes"))
            continue

        # 4 & 5. Pixel decode + aspect ratio
        if cv2_available:
            import cv2
            try:
                img = cv2.imread(str(frame_path))
            except Exception as exc:
                report.corrupt_count += 1
                report.issues.append(FrameIssue(frame_id, path_str, "corrupt", f"cv2 exception: {exc}"))
                continue

            if img is None:
                report.corrupt_count += 1
                report.issues.append(FrameIssue(frame_id, path_str, "corrupt", "cv2.imread returned None"))
                continue

            if expected_ar is not None:
                h, w = img.shape[:2]
                if h == 0:
                    report.ar_mismatch_count += 1
                    report.issues.append(FrameIssue(frame_id, path_str, "ar_mismatch", "Height is 0"))
                else:
                    actual_ar = w / h
                    delta = abs(actual_ar - expected_ar) / expected_ar
                    if delta > AR_TOLERANCE:
                        report.ar_mismatch_count += 1
                        report.issues.append(FrameIssue(
                            frame_id, path_str, "ar_mismatch",
                            f"expected AR={expected_ar:.4f} actual AR={actual_ar:.4f} ({w}x{h}) delta={delta:.4f}"
                        ))

    _audit_jsonl_content(student_dir, student_id, report)

    return report


def _markdown_table(reports: list[StudentReport]) -> str:
    header = (
        "| Student | Manifest | On Disk | Missing | ZeroByte | Permission | "
        "Corrupt | AR Mismatch | FmtMismatch | NullField | Status |"
    )
    sep = "|" + "|".join(["-" * len(c) for c in header.split("|")[1:-1]]) + "|"
    rows = [header, sep]
    for r in reports:
        status = "PASS" if r.passed else "FAIL"
        rows.append(
            f"| {r.student_id:<12} | {r.manifest_frame_count:>8} | {r.disk_file_count:>7} "
            f"| {r.missing_count:>7} | {r.zero_byte_count:>8} | {r.permission_count:>10} "
            f"| {r.corrupt_count:>7} | {r.ar_mismatch_count:>11} "
            f"| {r.jsonl_format_mismatch_count:>11} | {r.jsonl_null_field_count:>9} | {status} |"
        )
    passed = sum(1 for r in reports if r.passed)
    rows.append(f"\n**{passed}/{len(reports)} students passed**")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit extracted frames for integrity")
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--students", nargs="*", help="Limit to specific student IDs")
    parser.add_argument("--no-cv2", action="store_true", help="Skip pixel-level decode checks")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    audio_root = args.audio_root.resolve()
    if not audio_root.is_dir():
        LOGGER.error("audio-root not found: %s", audio_root)
        return 1

    cv2_available = False
    if not args.no_cv2:
        try:
            import cv2  # noqa: F401
            cv2_available = True
            LOGGER.info("OpenCV available — pixel decode checks enabled")
        except ImportError:
            LOGGER.warning("cv2 not installed — pixel decode checks disabled (pip install opencv-python-headless)")

    student_dirs = sorted(
        d for d in audio_root.iterdir()
        if d.is_dir() and (args.students is None or d.name in args.students)
    )

    if not student_dirs:
        LOGGER.error("No student directories found under %s", audio_root)
        return 1

    reports: list[StudentReport] = []
    for student_dir in student_dirs:
        LOGGER.info("Auditing %s ...", student_dir.name)
        report = audit_student(student_dir, cv2_available=cv2_available)
        reports.append(report)
        if report.issues and args.verbose:
            for issue in report.issues:
                LOGGER.debug("  [%s] %s — %s: %s", issue.frame_id, issue.issue_type, Path(issue.file_path).name, issue.detail)

    print("\n" + _markdown_table(reports) + "\n")

    # Write JSON report
    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    report_path = LOGS_DIR / f"audit_{ts}.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audio_root": str(audio_root),
        "cv2_checks": cv2_available,
        "students": [asdict(r) for r in reports],
        "summary": {
            "total_students": len(reports),
            "passed": sum(1 for r in reports if r.passed),
            "failed": sum(1 for r in reports if not r.passed),
            "total_issues": sum(r.total_issues for r in reports),
        },
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Full report saved: %s", report_path.relative_to(REPO_ROOT))

    failed = [r for r in reports if not r.passed]
    if failed:
        LOGGER.error("%d student(s) failed audit: %s", len(failed), [r.student_id for r in failed])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
