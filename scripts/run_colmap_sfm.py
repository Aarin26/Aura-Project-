#!/usr/bin/env python3
"""
Phase 2 — run_colmap_sfm.py
Runs COLMAP feature extraction, matching, and incremental SfM mapper.
Saves the sparse reconstruction, camera poses, and a registration report.

Usage:
    python scripts/run_colmap_sfm.py [--image_dir data/01_reconstruction] [--output_dir outputs/phase_2_sparse]
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_IMAGE_DIR = BASE_DIR / "data" / "01_reconstruction"
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "phase_2_sparse"
MANIFEST_FILE = BASE_DIR / "manifests" / "dataset_split.json"


def run_colmap(cmd_args, label=""):
    print(f"\n[COLMAP] {label}")
    print("  " + " ".join(str(a) for a in cmd_args))
    try:
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR (exit {result.returncode}):\n{result.stderr[-2000:]}")
        else:
            print("  Done.")
        return result
    except FileNotFoundError:
        print("  ERROR: 'colmap' executable was not found in PATH.")
        print("  Please download COLMAP from https://colmap.github.io/install.html and add it to PATH.")
        class DummyResult:
            returncode = -1
            stderr = "colmap not found in PATH"
            stdout = ""
        return DummyResult()


def parse_colmap_summary(sparse_dir):
    """Parse COLMAP cameras.txt and images.txt to extract registration stats."""
    stats = {"registered_cameras": 0, "sparse_points": 0, "mean_reprojection_error": "N/A"}
    cameras_file = sparse_dir / "0" / "cameras.txt"
    images_file = sparse_dir / "0" / "images.txt"
    points_file = sparse_dir / "0" / "points3D.txt"

    try:
        if images_file.exists():
            lines = [l for l in images_file.read_text(encoding="utf-8").splitlines()
                     if l.strip() and not l.startswith("#")]
            stats["registered_cameras"] = len(lines) // 2  # every other line is image data
        if points_file.exists():
            lines = [l for l in points_file.read_text(encoding="utf-8").splitlines()
                     if l.strip() and not l.startswith("#")]
            stats["sparse_points"] = len(lines)
    except Exception as e:
        stats["parse_error"] = str(e)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Run COLMAP SfM pipeline for Phase 2")
    parser.add_argument("--image_dir", default=str(DEFAULT_IMAGE_DIR))
    parser.add_argument("--output_dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--camera_model", default="RADIAL", help="COLMAP camera model (default: RADIAL)")
    parser.add_argument("--single_camera", action="store_true", help="Force single shared camera model")
    args = parser.parse_args()

    image_dir = Path(args.image_dir)
    output_dir = Path(args.output_dir)
    db_path = output_dir / "colmap.db"
    sparse_dir = output_dir / "sparse"

    output_dir.mkdir(parents=True, exist_ok=True)
    sparse_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().strftime("sfm_%Y%m%d_%H%M%S")
    manifest = {
        "run_id": run_id,
        "phase": "2",
        "tool": "COLMAP",
        "image_dir": str(image_dir),
        "output_dir": str(output_dir),
        "camera_model": args.camera_model,
        "single_camera": args.single_camera,
        "start_time": datetime.now().isoformat(),
        "steps": {},
        "end_time": None,
        "registration_stats": {}
    }

    # Step 1: Feature extraction
    feat_cmd = [
        "colmap", "feature_extractor",
        "--database_path", str(db_path),
        "--image_path", str(image_dir),
        "--ImageReader.camera_model", args.camera_model,
    ]
    if args.single_camera:
        feat_cmd += ["--ImageReader.single_camera", "1"]
    r = run_colmap(feat_cmd, "Feature Extraction")
    manifest["steps"]["feature_extraction"] = {"exit_code": r.returncode}

    # Step 2: Exhaustive matching
    match_cmd = ["colmap", "exhaustive_matcher", "--database_path", str(db_path)]
    r = run_colmap(match_cmd, "Exhaustive Matching")
    manifest["steps"]["exhaustive_matching"] = {"exit_code": r.returncode}

    # Step 3: Incremental mapper (SfM)
    mapper_cmd = [
        "colmap", "mapper",
        "--database_path", str(db_path),
        "--image_path", str(image_dir),
        "--output_path", str(sparse_dir),
    ]
    r = run_colmap(mapper_cmd, "Incremental SfM Mapper")
    manifest["steps"]["mapper"] = {"exit_code": r.returncode}

    # Step 4: Convert to text format for inspection
    convert_cmd = [
        "colmap", "model_converter",
        "--input_path", str(sparse_dir / "0"),
        "--output_path", str(sparse_dir / "0"),
        "--output_type", "TXT",
    ]
    r = run_colmap(convert_cmd, "Model Conversion to TXT")
    manifest["steps"]["model_conversion"] = {"exit_code": r.returncode}

    # Parse stats
    manifest["registration_stats"] = parse_colmap_summary(sparse_dir)
    manifest["end_time"] = datetime.now().isoformat()

    # Save run manifest
    manifest_out = output_dir / "run_settings.json"
    with open(manifest_out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Write registration report
    report_path = output_dir / "registration_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        stats = manifest["registration_stats"]
        f.write("# Phase 2: SfM Registration Report\n\n")
        f.write(f"**Run ID:** `{run_id}`\n\n")
        f.write(f"**Image directory:** `{image_dir}`\n\n")
        f.write("## Registration Summary\n\n")
        f.write("| Metric | Value |\n| :--- | :--- |\n")
        f.write(f"| Registered cameras | {stats.get('registered_cameras', 'N/A')} |\n")
        f.write(f"| Sparse 3D points | {stats.get('sparse_points', 'N/A')} |\n")
        f.write(f"| Mean reprojection error | {stats.get('mean_reprojection_error', 'N/A')} |\n\n")
        f.write("## Unregistered Images\n\n*(List images that failed to register and the suspected reason)*\n\n")
        f.write("## Observations\n\n*(Any match graph issues, weak connections, or failure clusters)*\n\n")
        f.write("## M2 Acceptance Gate\n\n")
        f.write("- [ ] Coherent single reconstruction (not disconnected components)\n")
        f.write("- [ ] Registered-image list reviewed and explained\n")
        f.write("- [ ] Camera poses and sparse geometry saved and re-openable\n")
        f.write("- [ ] Reprojection-error summary retained for comparison\n")

    print(f"\nRun manifest: {manifest_out}")
    print(f"Registration report: {report_path}")
    print(f"Stats: {manifest['registration_stats']}")


if __name__ == "__main__":
    main()

