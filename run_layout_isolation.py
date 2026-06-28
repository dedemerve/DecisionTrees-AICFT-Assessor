#!/usr/bin/env python3
"""
run_layout_isolation.py — CLI for Phase 1 layout parsing (project-aware).

Examples:
  python run_layout_isolation.py --student Sample_Student
  python run_layout_isolation.py --student Sample_Student --worksheet WS10 --debug
  python run_layout_isolation.py WS10 ocr_output/_images/_slot31_check/page_2.jpg Sample_Student
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from layout_isolator import LayoutIsolator
from pipeline_schema import REPO_ROOT, worksheet_page_image


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 1: ProDaBi layout RoI isolation")
    parser.add_argument("worksheet", nargs="?", help="WS5, WS10, or WS6")
    parser.add_argument("image", nargs="?", help="Explicit page image path")
    parser.add_argument("student_id", nargs="?", help="Student pseudonym or slot label")
    parser.add_argument("--student", help="Process student via pipeline_schema page map")
    parser.add_argument("--worksheet", dest="ws_flag", help="Single worksheet with --student")
    parser.add_argument("--bundle", action="store_true", help="All LAYOUT_ISOLATION_WORKSHEETS")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "layout_rois")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    isolator = LayoutIsolator(output_dir=args.output_dir, debug=args.debug)

    if args.student:
        student_id = args.student
        if args.bundle:
            results = isolator.process_student_bundle(student_id)
            failed = 0
            for ws, result in results.items():
                print(f"{ws}: {result.status} ({result.zone_count} zones) -> {result.save()}")
                if result.status == "error":
                    failed += 1
                if args.json:
                    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            return 1 if failed == len(results) else 0

        ws = (args.ws_flag or args.worksheet or "WS10").upper()
        result = isolator.process_student_worksheet(
            student_id, ws,
            image_path=args.image,
        )
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"Status: {result.status}")
            print(f"Page: {result.page_index} | Zones: {len(result.zones)}")
            print(f"Manifest: {result.save()}")
            if result.message:
                print(f"Note: {result.message}")
            resolved = worksheet_page_image(student_id, ws)
            if resolved:
                print(f"Source: {resolved}")
        return 0 if result.status != "error" else 1

    if not args.worksheet or not args.student_id:
        parser.error("Provide --student, or worksheet image student_id")

    image = args.image or worksheet_page_image(args.student_id, args.worksheet.upper())
    if image is None:
        print(f"No image for {args.worksheet}; pass explicit image path.", file=sys.stderr)
        return 1

    result = isolator.process_worksheet_page(image, args.student_id, args.worksheet.upper())
    result.save(args.output_dir / args.student_id)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Status: {result.status} | Zones: {len(result.zones)}")
        print(f"Manifest: {result.save()}")
        if result.message:
            print(f"Note: {result.message}")

    return 0 if result.status != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
