#!/usr/bin/env python3
"""
Phase 6 — validate_held_out.py
For each held-out image:
  1. Localize it against the COLMAP reconstruction (image registrator).
  2. Render the candidate mesh from the estimated viewpoint using Open3D.
  3. Compute SSIM between the render and the real photograph.
  4. Save comparison images and a per-view results CSV.

Usage:
    python scripts/validate_held_out.py \
        --mesh outputs/phase_5_textured/mesh_textured.obj \
        --sparse_dir outputs/phase_3_scaled \
        --held_out_dir data/02_held_out \
        --output_dir outputs/phase_6_validation
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent


def check_imports():
    missing = []
    try:
        import open3d
    except ImportError:
        missing.append("open3d")
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    if missing:
        print(f"[ERROR] Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        sys.exit(1)


def load_held_out_list(dataset_split_path):
    with open(dataset_split_path, encoding="utf-8") as f:
        split = json.load(f)
    return split.get("held_out_images", [])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", default=str(BASE_DIR / "outputs" / "phase_5_textured" / "mesh_textured.obj"))
    parser.add_argument("--sparse_dir", default=str(BASE_DIR / "outputs" / "phase_3_scaled"))
    parser.add_argument("--held_out_dir", default=str(BASE_DIR / "data" / "02_held_out"))
    parser.add_argument("--output_dir", default=str(BASE_DIR / "outputs" / "phase_6_validation"))
    parser.add_argument("--dataset_split", default=str(BASE_DIR / "manifests" / "dataset_split.json"))
    args = parser.parse_args()

    check_imports()
    import open3d as o3d
    import numpy as np
    from PIL import Image

    output_dir = Path(args.output_dir)
    renders_dir = output_dir / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)

    held_out_dir = Path(args.held_out_dir)
    held_out_images = load_held_out_list(args.dataset_split)

    if not held_out_images:
        image_exts = {".jpg", ".jpeg", ".png"}
        held_out_images = [f.name for f in held_out_dir.iterdir()
                           if f.suffix.lower() in image_exts]

    print(f"Found {len(held_out_images)} held-out images")

    results = []

    for img_name in held_out_images:
        img_path = held_out_dir / img_name
        if not img_path.exists():
            results.append({"image": img_name, "status": "FILE_NOT_FOUND", "ssim": None, "notes": ""})
            continue

        # Placeholder: COLMAP image_registrator would go here
        # For now, record as pending localization
        results.append({
            "image": img_name,
            "status": "PENDING_LOCALIZATION",
            "ssim": None,
            "notes": "Run COLMAP image_registrator to estimate camera pose, then rerun this script."
        })

    # Write CSV results
    csv_path = output_dir / "per_view_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "status", "ssim", "notes"])
        writer.writeheader()
        writer.writerows(results)

    # Write validation report
    report_path = output_dir / "validation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Phase 6: Held-Out Validation Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write(f"**Mesh:** `{args.mesh}`\n\n")
        f.write(f"**Held-out images:** {len(held_out_images)}\n\n")
        f.write("## Per-View Results\n\n")
        f.write("| Image | Status | SSIM | Notes |\n| :--- | :--- | :--- | :--- |\n")
        for r in results:
            f.write(f"| {r['image']} | {r['status']} | {r['ssim'] or 'N/A'} | {r['notes']} |\n")
        f.write("\n## M6 Acceptance Gate\n\n")
        f.write("- [ ] Every held-out image has a recorded result (localized or marked unscorable with reason)\n")
        f.write("- [ ] Rendered-vs-real comparisons saved for representative views\n")
        f.write("- [ ] Known physical dimensions checked against ground truth\n")
        f.write("- [ ] Project owner accepts documented quality, or asset returns to responsible phase\n")
        f.write("- [ ] Report distinguishes measured evidence from subjective visual review\n")

    print(f"Results CSV: {csv_path}")
    print(f"Validation report: {report_path}")


if __name__ == "__main__":
    main()

