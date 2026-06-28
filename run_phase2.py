#!/usr/bin/env python3
"""run_phase2.py — Phase 1 layout + Phase 2 HTR + OCR integration."""

from __future__ import annotations

import argparse
import json
import sys

from pipeline_integration import integrate_student


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run layout + HTR integration")
    parser.add_argument("student_id", help="e.g. Sample_Student")
    parser.add_argument("--no-ws6-pdf", action="store_true", help="Skip Worksheet 6.pdf layout")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = integrate_student(args.student_id, ws6_pdf=not args.no_ws6_pdf)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Student: {args.student_id}")
        print(f"Layout: {report.get('layout')}")
        ws10 = report.get("htr", {}).get("WS10", {})
        print(f"WS10 HTR: {ws10.get('htr_status')} blocked={ws10.get('blocked')}")
        if report.get("ws6"):
            print(f"WS6 PDF layout: {report['ws6'].get('status')}")

    blocked = report.get("htr", {}).get("WS10", {}).get("blocked", True)
    return 0 if not blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
