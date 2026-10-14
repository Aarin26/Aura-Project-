#!/usr/bin/env python3
"""
scripts/run_pipeline.py
Master End-to-End Orchestrator for the 3D Photogrammetry Pipeline.

Executes all pipeline phases in sequence:
  Phase 0: Dataset Audit & Quality Manifest
  Phase 2: SfM Pre-flight & Sparse Reconstruction
  Phase 3: Scale Calibration & Sparse QA
  Phase 4: Dense MVS & Surface Meshing
  Phase 5: Mesh Cleanup, Decimation, UVs & Texturing
  Phase 6: Validation Against Unseen Held-Out Photos
  Phase 7: Production glTF 2.0 Export & Engine Handoff

Usage:
  python scripts/run_pipeline.py
  (or)
  python scripts/run_pipeline.py --phase 3
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PYTHON_EXE = sys.executable

STEPS = [
    ("Phase 0: Dataset Audit & Checksums", "scripts/audit_dataset.py"),
    ("Phase 2: Pre-Flight Check", "scripts/prepare_for_colmap.py"),
    ("Phase 3: Scale Calibration (Metric Scaling)", "scripts/apply_scale.py"),
    ("Phase 3: Sparse Model QA Verification", "scripts/verify_sparse_qa.py"),
    ("Phase 4: Dense MVS Reconstruction & Meshing", "scripts/run_mvs_mesh.py"),
    ("Phase 5: Mesh Cleanup, Decimation, UVs & Texturing", "scripts/run_mesh_cleanup_texturing.py"),
    ("Phase 6: Validation Against Held-Out Photos", "scripts/validate_held_out.py"),
    ("Phase 7: Export Production glTF 2.0 (.glb) & Handoff", "scripts/export_asset.py")
]


def run_step(title, script_rel_path):
    print("\n" + "=" * 70)
    print(f"  [RUNNING] {title}")
    print(f"  Script: {script_rel_path}")
    print("=" * 70)
    t0 = time.time()
    script_path = BASE_DIR / script_rel_path

    result = subprocess.run([PYTHON_EXE, str(script_path)], capture_output=True, text=True)
    dt = time.time() - t0

    # Print output indented
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr and result.returncode != 0:
        print("\n[STDERR]")
        print(result.stderr.strip())

    if result.returncode != 0:
        print(f"\n[ERROR] {title} failed with exit code {result.returncode} in {dt:.2f}s")
        return False
    else:
        print(f"\n[COMPLETED] {title} in {dt:.2f}s")
        return True


def main():
    parser = argparse.ArgumentParser(description="Master Photogrammetry Pipeline Runner")
    parser.add_argument("--phase", type=int, default=None, help="Run specific phase (0, 2, 3, 4, 5, 6, 7)")
    args = parser.parse_args()

    start_time = datetime.now()
    print("=" * 70)
    print("  3D MODEL RECONSTRUCTION PIPELINE - MASTER RUNNER")
    print(f"  Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Workspace:  {BASE_DIR}")
    print("=" * 70)

    success_count = 0
    total_steps = len(STEPS)

    for title, script_rel in STEPS:
        # Check if single phase requested
        if args.phase is not None:
            phase_num = f"Phase {args.phase}"
            if phase_num not in title:
                continue

        ok = run_step(title, script_rel)
        if not ok:
            print(f"\n[HALTED] Pipeline execution stopped due to failure in {title}.")
            sys.exit(1)
        success_count += 1

    total_time = (datetime.now() - start_time).total_seconds()
    print("\n" + "#" * 70)
    print(f"  ALL {success_count} STAGES EXECUTED SUCCESSFULLY IN {total_time:.2f} SECONDS")
    print(f"  Production Deliverable: outputs/phase_7_export/asset.glb")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    main()

