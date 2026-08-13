#!/usr/bin/env python3
"""
rebuild_portfolios.py — WS5/WS6/WS7 düzeltmelerinden sonra portfolio + evidence_units yeniden inşa et.
API çağrısı yok — tamamen deterministic.

KULLANIM:
    cd ~/Desktop/DecisionTrees-AICFT-Assessor
    python3 rebuild_portfolios.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

STUDENTS_DIR = Path(__file__).parent / "students"

ALL_STUDENTS = [
    "Amy", "Bruno", "Helena", "Isabel", "Irma", "Iris",
    "Marco", "Marcus", "Melinda", "Nadia", "Serena",
    "Sheila", "Shana", "Ulysses", "Zara",
]

def main():
    # Portfolio builder
    try:
        from portfolio_builder import build_and_save_portfolio
        print("=== Portfolio rebuild ===")
        for student in ALL_STUDENTS:
            if not (STUDENTS_DIR / student).is_dir():
                print(f"  {student:<12} SKIP (no student dir)")
                continue
            try:
                r = build_and_save_portfolio(student)
                ws = r.get("worksheets_scored", [])
                lo_count = len(r.get("evidence_by_lo", {}))
                print(f"  {student:<12} OK — {len(ws)} WS scored, {lo_count} LOs with evidence")
            except Exception as e:
                print(f"  {student:<12} ERROR: {e}")
    except ImportError as e:
        print(f"portfolio_builder import failed: {e}")

    # Evidence units
    try:
        from evidence_unit_runtime import build_and_save_evidence_units
        print("\n=== Evidence units rebuild ===")
        for student in ALL_STUDENTS:
            if not (STUDENTS_DIR / student).is_dir():
                continue
            try:
                build_and_save_evidence_units(student)
                print(f"  {student:<12} OK")
            except Exception as e:
                print(f"  {student:<12} ERROR: {e}")
    except ImportError:
        pass  # evidence_unit_runtime may not exist

    print("\nDone. Portfolio + evidence_units updated for all students.")

if __name__ == "__main__":
    main()
