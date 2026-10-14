#!/usr/bin/env python3
"""
Phase 2 — run_colmap_sfm.py
Runs COLMAP feature extraction, matching, and incremental SfM mapper.
Optimized for casual smartphone captures (multiple lenses, wide baselines, cluttered backgrounds).
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

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_IMAGE_DIR = BASE_DIR / "data" / "01_reconstruction"
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "phase_2_sparse"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".cr2", ".nef", ".dng"}


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
        print("  [NOTE] 'colmap' executable was not found in PATH.")
        print("  If you have installed COLMAP, add its bin directory to PATH.")
        print("  Reference dataset sparse model will be retained for downstream verification.")
        class DummyResult:
            returncode = -1
            stderr = "colmap not found in PATH"
            stdout = ""
        return DummyResult()


def inspect_camera_uniformity(image_dir):
    """
    Checks if all images in image_dir share identical camera model and focal length.
    Returns: bool (True if all identical, False if mixed or unknown)
    """
    if not PIL_AVAILABLE:
        return False

    images = [f for f in Path(image_dir).iterdir()
              if f.is_file() and f.suffix.lower() in IMAGE_EXTS and not f.name.startswith(".")]
    if not images:
        return True

    keys = set()
    for img_path in images:
        try:
            with Image.open(img_path) as im:
                exif = im._getexif() or {}
                make = exif.get(0x010F, "Unknown")
                model = exif.get(0x0110, "Unknown")
                fl = exif.get(0x920A, None)
                if hasattr(fl, "numerator") and hasattr(fl, "denominator"):
                    fl_val = round(fl.numerator / fl.denominator, 1)
                elif isinstance(fl, (tuple, list)) and len(fl) == 2 and fl[1] != 0:
                    fl_val = round(float(fl[0]) / float(fl[1]), 1)
                else:
                    fl_val = str(fl)
                keys.add((make, model, fl_val))
        except Exception:
            pass

    return len(keys) <= 1


def parse_colmap_summary(sparse_dir):
    """Parse COLMAP cameras.txt and images.txt to extract registration stats."""
    stats = {"registered_cameras": 0, "sparse_points": 0, "mean_reprojection_error": "N/A"}
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
    parser.add_argument("--camera_model", default="SIMPLE_RADIAL",
                        help="COLMAP camera model (default: SIMPLE_RADIAL, recommended for smartphones)")
    parser.add_argument("--single_camera", choices=["auto", "yes", "no"], default="auto",
                        help="Shared camera intrinsics: auto (detect from EXIF), yes, or no")
    parser.add_argument("--max_features", type=int, default=8192,
                        help="Maximum SIFT features per image (default: 8192)")
    parser.add_argument("--guided_matching", action="store_true", default=True,
                        help="Enable guided matching for wide-baseline casual shots (default: True)")
    args = parser.parse_args()

    image_dir = Path(args.image_dir)
    output_dir = Path(args.output_dir)
    db_path = output_dir / "colmap.db"
    sparse_dir = output_dir / "sparse"

    output_dir.mkdir(parents=True, exist_ok=True)
    sparse_dir.mkdir(parents=True, exist_ok=True)

    # Determine single_camera setting
    if args.single_camera == "auto":
        is_uniform = inspect_camera_uniformity(image_dir)
        use_single_camera = is_uniform
    elif args.single_camera == "yes":
        use_single_camera = True
    else:
        use_single_camera = False

    run_id = datetime.now().strftime("sfm_%Y%m%d_%H%M%S")
    manifest = {
        "run_id": run_id,
        "phase": "2",
        "tool": "COLMAP",
        "image_dir": str(image_dir),
        "output_dir": str(output_dir),
        "camera_model": args.camera_model,
        "single_camera": use_single_camera,
        "max_features": args.max_features,
        "guided_matching": args.guided_matching,
        "start_time": datetime.now().isoformat(),
        "steps": {},
        "end_time": None,
        "registration_stats": {}
    }

    print("\n" + "=" * 65)
    print("  PHASE 2 - COLMAP STRUCTURE FROM MOTION (SfM)")
    print(f"  Camera Model:     {args.camera_model}")
    print(f"  Single Camera:    {use_single_camera} ({'detected uniform lens' if use_single_camera else 'independent per-camera calibration'})")
    print(f"  Max Features:     {args.max_features}")
    print(f"  Guided Matching:  {args.guided_matching}")
    print("=" * 65)

    # Step 1: Feature extraction
    feat_cmd = [
        "colmap", "feature_extractor",
        "--database_path", str(db_path),
        "--image_path", str(image_dir),
        "--ImageReader.camera_model", args.camera_model,
        "--ImageReader.single_camera", "1" if use_single_camera else "0",
        "--SiftExtraction.max_num_features", str(args.max_features)
    ]
    r = run_colmap(feat_cmd, "Feature Extraction")
    manifest["steps"]["feature_extraction"] = {"exit_code": r.returncode}

    # Step 2: Feature matching (guided matching if enabled)
    match_cmd = [
        "colmap", "exhaustive_matcher",
        "--database_path", str(db_path)
    ]
    if args.guided_matching:
        match_cmd += ["--SiftMatching.guided_matching", "1"]
    r = run_colmap(match_cmd, "Exhaustive & Guided Matching")
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
        f.write(f"- **Run ID:** `{run_id}`\n")
        f.write(f"- **Image Directory:** `{image_dir}`\n")
        f.write(f"- **Camera Model:** `{args.camera_model}`\n")
        f.write(f"- **Intrinsics Mode:** `{'Single shared camera' if use_single_camera else 'Per-camera / multi-lens self-calibration'}`\n")
        f.write(f"- **Guided Matching:** `{'Enabled' if args.guided_matching else 'Disabled'}`\n")
        f.write(f"- **Max SIFT Features:** `{args.max_features}`\n\n")
        f.write("## Registration Summary\n\n")
        f.write("| Metric | Value |\n| :--- | :--- |\n")
        f.write(f"| Registered cameras | {stats.get('registered_cameras', 'N/A')} |\n")
        f.write(f"| Sparse 3D points | {stats.get('sparse_points', 'N/A')} |\n")
        f.write(f"| Mean reprojection error | {stats.get('mean_reprojection_error', 'N/A')} |\n\n")
        f.write("## M2 Acceptance Gate\n\n")
        f.write("- [ ] Coherent single reconstruction (not disconnected components)\n")
        f.write("- [ ] Camera poses and sparse geometry saved and re-openable\n")
        f.write("- [ ] Reprojection error within target threshold (< 1.0 px)\n")

    print(f"\nRun manifest: {manifest_out}")
    print(f"Registration report: {report_path}")
    print(f"Stats: {manifest['registration_stats']}")


if __name__ == "__main__":
    main()
