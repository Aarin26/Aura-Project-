#!/usr/bin/env python3
"""
Phase 0 — audit_dataset.py
Computes SHA-256 checksums, dimensions, file sizes, EXIF metadata, orientation tags,
and optical/motion sharpness (Laplacian variance).
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

try:
    import numpy as np
    import scipy.ndimage as ndimage
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".cr2", ".nef", ".dng"}


def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def compute_sharpness(pil_img):
    if not SCIPY_AVAILABLE:
        return 100.0
    try:
        gray = pil_img.convert("L")
        arr = np.array(gray, dtype=np.float64)
        lap = ndimage.laplace(arr)
        return round(float(np.var(lap)), 1)
    except Exception:
        return 0.0


def get_exif_metadata(image_path):
    meta = {
        "width": None,
        "height": None,
        "make": None,
        "model": None,
        "focal_length": None,
        "iso": None,
        "exposure_time": None,
        "orientation": 1,
        "blur_score": 0.0,
        "sharpness": "Unknown"
    }
    if not PIL_AVAILABLE:
        return meta
    try:
        with Image.open(image_path) as img:
            meta["width"], meta["height"] = img.size
            meta["blur_score"] = compute_sharpness(img)
            if meta["blur_score"] >= 80.0:
                meta["sharpness"] = "Sharp"
            elif meta["blur_score"] >= 40.0:
                meta["sharpness"] = "Acceptable"
            else:
                meta["sharpness"] = "Blurry"

            raw_exif = img._getexif()
            if raw_exif:
                meta["orientation"] = raw_exif.get(0x0112, 1)
                for tag_id, value in raw_exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == "Make":
                        meta["make"] = str(value).strip()
                    elif tag == "Model":
                        meta["model"] = str(value).strip()
                    elif tag == "FocalLength":
                        if hasattr(value, "numerator") and hasattr(value, "denominator"):
                            meta["focal_length"] = round(value.numerator / value.denominator, 1)
                        elif isinstance(value, (tuple, list)) and len(value) == 2 and value[1] != 0:
                            meta["focal_length"] = round(float(value[0]) / float(value[1]), 1)
                        elif hasattr(value, "__float__"):
                            meta["focal_length"] = round(float(value), 1)
                        else:
                            meta["focal_length"] = str(value)
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
                    if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS and not f.name.startswith(".")])

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
            "orientation": meta.get("orientation", 1),
            "blur_score": meta.get("blur_score", 0.0),
            "sharpness": meta.get("sharpness", "Unknown"),
            "sha256": sha256
        })

    fieldnames = [
        "filename", "size_bytes", "width", "height", "make", "model",
        "focal_length", "iso", "exposure_time", "orientation",
        "blur_score", "sharpness", "sha256"
    ]
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
            focals = {str(r['focal_length']) for r in records if r.get('focal_length') is not None}
            blurry_count = sum(1 for r in records if r.get('sharpness') == 'Blurry')
            non_upright = sum(1 for r in records if r.get('orientation', 1) != 1)
            total_mb = sum(r['size_bytes'] for r in records) / (1024 * 1024)

            rep.write("## Inventory Summary\n\n")
            rep.write(f"- **Camera Models Detected**: {', '.join(models) if models else 'None / EXIF stripped'}\n")
            rep.write(f"- **Focal Lengths**: {', '.join(focals) if focals else 'Unknown'} mm\n")
            rep.write(f"- **Total Disk Footprint**: {total_mb:.2f} MB\n")
            rep.write(f"- **Blurry / Out-of-Focus Images**: {blurry_count}\n")
            rep.write(f"- **Un-transposed EXIF Orientations**: {non_upright}\n\n")

            if blurry_count > 0 or non_upright > 0:
                rep.write("> [!TIP]\n")
                rep.write("> Casual smartphone captures with non-upright rotation or blur detected.\n")
                rep.write("> Run `python scripts/preprocess_casual_photos.py` to auto-orient and clean the dataset.\n\n")

            rep.write("### Image Quality & Metadata List\n\n")
            rep.write("| Filename | Dimensions | Camera | Focal (mm) | Sharpness | Status | Orient | SHA-256 (first 8) |\n")
            rep.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for r in records:
                dim = f"{r['width']}x{r['height']}" if r['width'] else "N/A"
                cam = f"{r.get('make') or ''} {r.get('model') or ''}".strip() or "N/A"
                fl = str(r['focal_length']) if r.get('focal_length') else "N/A"
                rep.write(f"| `{r['filename']}` | {dim} | {cam} | {fl} | {r['blur_score']} | {r['sharpness']} | {r['orientation']} | {r['sha256'][:8]}... |\n")
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
        print(f"[WARNING] Multiple camera models detected: {cameras} - will use multi-camera mode in Phase 2.")
    elif not cameras:
        print("[WARNING] No camera EXIF detected - COLMAP will use self-calibration.")
    else:
        print(f"[OK] Single camera model: {list(cameras)[0]}")

    print("\nNext steps for Casual Smartphone Photos:")
    print("  1. Run 'python scripts/preprocess_casual_photos.py' to auto-orient and normalize")
    print("  2. Measure reference distance and update 'manifests/scale_reference.json'")
    print("  3. Run 'python scripts/run_pipeline.py' for full end-to-end reconstruction")


if __name__ == "__main__":
    main()
