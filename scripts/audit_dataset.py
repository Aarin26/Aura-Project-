#!/usr/bin/env python3
"""
Phase 0 — audit_dataset.py
Computes SHA-256 checksums, dimensions, file sizes, and EXIF metadata.
Generates source manifest CSV and Phase 0 summary report.

Usage:
    python scripts/audit_dataset.py
    (or)
    python scripts/audit_dataset.py --source_dir data/00_raw_master
"""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[WARNING] Pillow not installed. Install with: pip install Pillow")

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".cr2", ".nef", ".dng"}


def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def get_exif_metadata(image_path):
    meta = {"width": None, "height": None, "make": None, "model": None,
            "focal_length": None, "iso": None, "exposure_time": None}
    if not PIL_AVAILABLE:
        return meta
    try:
        with Image.open(image_path) as img:
            meta["width"], meta["height"] = img.size
            raw_exif = img._getexif()
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == "Make":
                        meta["make"] = str(value).strip()
                    elif tag == "Model":
                        meta["model"] = str(value).strip()
                    elif tag == "FocalLength":
                        meta["focal_length"] = float(value) if hasattr(value, "__float__") else str(value)
                    elif tag == "ISOSpeedRatings":
                        meta["iso"] = str(value)
                    elif tag == "ExposureTime":
                        meta["exposure_time"] = str(value)
    except Exception as e:
        meta["error"] = str(e)
    return meta


def audit_directory(source_dir, output_manifest_csv, output_report_md):
    source_path = Path(source_dir)
    files = sorted([f for f in source_path.iterdir()
                    if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS])

    records = []
    print(f"Auditing {len(files)} images in '{source_dir}'...")

    for f in files:
        sha256 = calculate_sha256(f)
        size_bytes = f.stat().st_size
        meta = get_exif_metadata(f)
        records.append({
            "filename": f.name,
            "size_bytes": size_bytes,
            "width": meta.get("width"),
            "height": meta.get("height"),
            "make": meta.get("make"),
            "model": meta.get("model"),
            "focal_length": meta.get("focal_length"),
            "iso": meta.get("iso"),
            "exposure_time": meta.get("exposure_time"),
            "sha256": sha256
        })

    fieldnames = ["filename", "size_bytes", "width", "height", "make", "model",
                  "focal_length", "iso", "exposure_time", "sha256"]
    with open(output_manifest_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"[OK] Saved source manifest: {output_manifest_csv}")

    with open(output_report_md, "w", encoding="utf-8") as rep:
        rep.write("# Phase 0: Dataset Audit Report\n\n")
        rep.write(f"- **Total source images identified**: {len(records)}\n")
        rep.write(f"- **Source path**: `{source_dir}`\n\n")
        if records:
            models = {r['model'] for r in records if r.get('model')}
            total_mb = sum(r['size_bytes'] for r in records) / (1024 * 1024)
            rep.write("## Inventory Summary\n\n")
            rep.write(f"- **Camera Models Detected**: {', '.join(models) if models else 'None / EXIF stripped'}\n")
            rep.write(f"- **Total Disk Footprint**: {total_mb:.2f} MB\n\n")
            rep.write("### Image List\n\n")
            rep.write("| Filename | Dimensions | Camera | Size (KB) | SHA-256 (first 8) |\n")
            rep.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for r in records:
                dim = f"{r['width']}x{r['height']}" if r['width'] else "N/A"
                cam = f"{r.get('make') or ''} {r.get('model') or ''}".strip() or "N/A"
                rep.write(f"| {r['filename']} | {dim} | {cam} | {r['size_bytes']//1024} | {r['sha256'][:8]}... |\n")
        else:
            rep.write("> [!WARNING]\n")
            rep.write("> No images found in the raw master folder.\n")
            rep.write("> Please copy your photographs into `data/00_raw_master/` before running this script.\n")
    print(f"[OK] Saved audit report: {output_report_md}")
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_dir", default=str(BASE_DIR / "data" / "00_raw_master"))
    args = parser.parse_args()

    manifest_file = BASE_DIR / "manifests" / "source_manifest.csv"
    report_file = BASE_DIR / "reports" / "phase_0_dataset_audit.md"

    records = audit_directory(args.source_dir, manifest_file, report_file)

    if not records:
        print("\n[!] No images found. Add photos to data/00_raw_master/ and rerun.")
        return

    print(f"\nSummary: {len(records)} images audited.")
    cameras = {r['model'] for r in records if r.get('model')}
    if len(cameras) > 1:
        print(f"[WARNING] Multiple camera models detected: {cameras} — verify COLMAP intrinsic grouping in Phase 2.")
    elif not cameras:
        print("[WARNING] No camera EXIF detected — COLMAP will use self-calibration.")
    else:
        print(f"[OK] Single camera model: {list(cameras)[0]}")

    print("\nNext steps:")
    print("  1. Review reports/phase_0_dataset_audit.md for coverage and quality issues")
    print("  2. Fill in manifests/scale_reference.json with your ground truth measurement")
    print("  3. Copy reconstruction images to data/01_reconstruction/")
    print("  4. Copy held-out images to data/02_held_out/")
    print("  5. Update manifests/dataset_split.json with the split")


if __name__ == "__main__":
    main()
