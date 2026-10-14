#!/usr/bin/env python3
"""
Phase 2 — preprocess_casual_photos.py
Automated Preprocessing & Normalization Engine for Casual Smartphone Photographs.

Designed for real-world, unconstrained handheld captures (without professional studio equipment):
  1. Auto-Orientation: Detects EXIF rotation tags (portrait, landscape, upside-down)
     and transposes pixel buffers to be physically upright using PIL ImageOps.
  2. Sharpness & Blur Filtering: Calculates the variance of the 2D Laplacian operator
     to quantify optical and motion sharpness. Flags or excludes blurry images.
  3. Safe Megapixel Downscaling: Resizes oversized phone photos (e.g. 48MP, 108MP)
     to a safe maximum dimension (default: 2560px) with high-fidelity Lanczos filtering,
     preventing Out-Of-Memory (OOM) crashes during feature extraction and MVS.
  4. Multi-Lens / Multi-Camera Detection: Identifies distinct focal lengths and sensor
     configurations across modern multi-camera smartphones (ultra-wide, wide, telephoto).
  5. Automated Dataset Splitting: Partitions cleaned, verified images into Reconstruction (85%)
     and Held-Out Validation (15%) subsets with uniform angular coverage.
  6. Phase 2 Audit Report: Generates a detailed audit of sharpness, rotations, and camera profiles.

Usage:
    python scripts/preprocess_casual_photos.py
    python scripts/preprocess_casual_photos.py --blur_threshold 50.0 --max_dim 2560
"""

import argparse
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageOps, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[ERROR] Pillow is required for preprocessing. Run: pip install Pillow")

try:
    import numpy as np
    import scipy.ndimage as ndimage
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("[ERROR] NumPy and SciPy are required for blur detection. Run: pip install numpy scipy")

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".cr2", ".nef", ".dng"}

DEFAULT_SOURCE_DIR = BASE_DIR / "data" / "00_raw_master"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "03_preprocessed"
DEFAULT_RECON_DIR = BASE_DIR / "data" / "01_reconstruction"
DEFAULT_HELD_OUT_DIR = BASE_DIR / "data" / "02_held_out"
DEFAULT_SPLIT_JSON = BASE_DIR / "manifests" / "dataset_split.json"
DEFAULT_REPORT_MD = BASE_DIR / "reports" / "phase_2_preprocessing_report.md"


def compute_laplacian_blur_score(pil_img):
    """
    Computes image sharpness using Pech-Pacheco's Laplacian variance method.
    Returns: float score (higher = sharper, typically > 80 is very sharp, < 30 is blurry).
    """
    if not SCIPY_AVAILABLE:
        return 100.0  # fallback if scipy not available

    # Convert to grayscale
    gray_img = pil_img.convert("L")
    arr = np.array(gray_img, dtype=np.float64)

    # Compute discrete Laplacian using 3x3 convolution
    lap = ndimage.laplace(arr)
    var_score = float(np.var(lap))
    return var_score


def get_image_metadata(img_path):
    """Extracts resolution, EXIF orientation, camera model, and focal length."""
    info = {
        "width": 0,
        "height": 0,
        "orientation_tag": 1,
        "rotation_needed_deg": 0,
        "make": "Unknown",
        "model": "Unknown",
        "focal_length_mm": None,
        "iso": None,
        "exposure_time": None
    }
    if not PIL_AVAILABLE:
        return info

    try:
        with Image.open(img_path) as im:
            info["width"], info["height"] = im.size
            exif = im._getexif() or {}
            orient = exif.get(0x0112, 1)
            info["orientation_tag"] = orient

            # Map EXIF orientation tag to approximate rotation
            orient_map = {1: 0, 3: 180, 6: 90, 8: 270}
            info["rotation_needed_deg"] = orient_map.get(orient, 0)

            for tag_id, val in exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                if tag_name == "Make":
                    info["make"] = str(val).strip()
                elif tag_name == "Model":
                    info["model"] = str(val).strip()
                elif tag_name == "FocalLength":
                    if hasattr(val, "numerator") and hasattr(val, "denominator"):
                        info["focal_length_mm"] = round(val.numerator / val.denominator, 1)
                    elif isinstance(val, (tuple, list)) and len(val) == 2 and val[1] != 0:
                        info["focal_length_mm"] = round(float(val[0]) / float(val[1]), 1)
                    elif hasattr(val, "__float__"):
                        info["focal_length_mm"] = round(float(val), 1)
                    else:
                        info["focal_length_mm"] = str(val)
                elif tag_name == "ISOSpeedRatings":
                    info["iso"] = str(val)
                elif tag_name == "ExposureTime":
                    info["exposure_time"] = str(val)
    except Exception as e:
        info["read_error"] = str(e)

    return info


def normalize_image(input_path, output_path, max_dim=2560):
    """
    1. Transposes EXIF orientation to standard upright.
    2. Resizes if max dimension exceeds max_dim (preserving aspect ratio).
    3. Normalizes EXIF orientation tag to 1 (normal).
    Returns: (processed_pil_image, was_rotated, was_resized, original_size, new_size)
    """
    with Image.open(input_path) as im:
        orig_size = im.size
        # Step 1: Physical upright orientation
        transposed = ImageOps.exif_transpose(im)
        was_rotated = (transposed.size != orig_size) or (im._getexif() or {}).get(0x0112, 1) != 1

        # Step 2: Safe Downscaling if requested
        cur_w, cur_h = transposed.size
        max_edge = max(cur_w, cur_h)
        was_resized = False

        if max_dim > 0 and max_edge > max_dim:
            scale = max_dim / float(max_edge)
            new_w = int(round(cur_w * scale))
            new_h = int(round(cur_h * scale))
            # Use high-quality Lanczos resampling
            resample_filter = getattr(Image.Resampling, "LANCZOS", Image.LANCZOS)
            final_img = transposed.resize((new_w, new_h), resample=resample_filter)
            was_resized = True
        else:
            final_img = transposed

        new_size = final_img.size

        # Step 3: Save with normalized orientation tag
        output_path.parent.mkdir(parents=True, exist_ok=True)
        exif = transposed.getexif()
        exif[0x0112] = 1  # Reset to standard upright orientation
        
        # Save image (convert RGBA to RGB with white background if saving to JPEG)
        if output_path.suffix.lower() in [".jpg", ".jpeg"]:
            if final_img.mode in ("RGBA", "LA", "P"):
                rgb_bg = Image.new("RGB", final_img.size, (255, 255, 255))
                if final_img.mode == "P":
                    final_img = final_img.convert("RGBA")
                alpha = final_img.split()[3] if len(final_img.split()) == 4 else None
                rgb_bg.paste(final_img, mask=alpha)
                save_img = rgb_bg
            else:
                save_img = final_img
            save_img.save(output_path, quality=95, exif=exif, subsampling=0)
        else:
            final_img.save(output_path)

        return final_img, was_rotated, was_resized, orig_size, new_size


def preprocess_dataset(
    source_dir,
    output_dir,
    recon_dir,
    held_out_dir,
    split_json,
    report_md,
    max_dim=2560,
    blur_threshold=50.0,
    exclude_blurry=True,
    held_out_ratio=0.15,
    auto_split=True
):
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    recon_path = Path(recon_dir)
    held_out_path = Path(held_out_dir)
    excluded_blurry_dir = output_path / "excluded_blurry"

    output_path.mkdir(parents=True, exist_ok=True)
    excluded_blurry_dir.mkdir(parents=True, exist_ok=True)

    files = sorted([f for f in source_path.iterdir()
                    if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS and not f.name.startswith(".")])

    print("\n" + "=" * 70)
    print("  CASUAL SMARTPHONE PHOTO PREPROCESSING ENGINE (PHASE 2)")
    print(f"  Source Directory: {source_path}")
    print(f"  Output Clean Dir: {output_path}")
    print(f"  Found Images:     {len(files)}")
    print(f"  Max Dimension:    {max_dim} px (0 = no downscale)")
    print(f"  Blur Threshold:   {blur_threshold:.1f} (Laplacian variance)")
    print("=" * 70)

    if not files:
        print("[WARNING] No source images found. Please add photos to data/00_raw_master/ and rerun.")
        return False

    records = []
    camera_profiles = set()

    for idx, f in enumerate(files, start=1):
        meta = get_image_metadata(f)
        cam_key = f"{meta['make']} {meta['model']} ({meta['focal_length_mm']}mm)"
        camera_profiles.add(cam_key)

        clean_file = output_path / f.name
        processed_img, was_rotated, was_resized, orig_size, new_size = normalize_image(
            f, clean_file, max_dim=max_dim
        )

        blur_score = compute_laplacian_blur_score(processed_img)
        is_blurry = blur_score < blur_threshold

        status = "Sharp"
        if is_blurry:
            status = "BLURRY"
            if exclude_blurry:
                # Move to excluded folder
                blurry_dest = excluded_blurry_dir / f.name
                shutil.move(str(clean_file), str(blurry_dest))
                status = "EXCLUDED (BLUR)"

        record = {
            "filename": f.name,
            "orig_size": f"{orig_size[0]}x{orig_size[1]}",
            "new_size": f"{new_size[0]}x{new_size[1]}",
            "exif_orient": meta["orientation_tag"],
            "was_rotated": was_rotated,
            "was_resized": was_resized,
            "blur_score": blur_score,
            "status": status,
            "is_excluded": is_blurry and exclude_blurry,
            "camera_profile": cam_key,
            "focal_length_mm": meta["focal_length_mm"],
            "clean_path": clean_file if not (is_blurry and exclude_blurry) else (excluded_blurry_dir / f.name)
        }
        records.append(record)

        rot_str = f"Rotated {meta['rotation_needed_deg']}deg" if was_rotated else "Upright"
        res_str = f"Resized -> {record['new_size']}" if was_resized else "Original size"
        blur_str = f"Sharpness: {blur_score:6.1f} [{status}]"
        print(f"  [{idx:02d}/{len(files):02d}] {f.name:15s} | {rot_str:15s} | {res_str:20s} | {blur_str}")

    # Camera groupings check
    print("-" * 70)
    print(f"  Detected Camera / Lens Profiles: {len(camera_profiles)}")
    for cp in sorted(camera_profiles):
        print(f"    * {cp}")

    usable_records = [r for r in records if not r["is_excluded"]]
    excluded_records = [r for r in records if r["is_excluded"]]

    print(f"\n  Summary: {len(usable_records)} usable images, {len(excluded_records)} blurry/excluded.")

    # Smart Split Partitioning
    if auto_split and usable_records:
        recon_path.mkdir(parents=True, exist_ok=True)
        held_out_path.mkdir(parents=True, exist_ok=True)

        # Clear existing images to prevent stale files from previous runs
        for old_img in list(recon_path.iterdir()):
            if old_img.is_file() and old_img.suffix.lower() in IMAGE_EXTENSIONS:
                try:
                    old_img.unlink()
                except Exception:
                    pass
        for old_img in list(held_out_path.iterdir()):
            if old_img.is_file() and old_img.suffix.lower() in IMAGE_EXTENSIONS:
                try:
                    old_img.unlink()
                except Exception:
                    pass

        num_usable = len(usable_records)
        num_held_out = max(1, int(round(num_usable * held_out_ratio))) if num_usable >= 6 else 0
        
        # Pick held-out photos evenly spaced across the sequence to ensure angle diversity
        held_out_indices = set()
        if num_held_out > 0:
            step = num_usable / float(num_held_out)
            for i in range(num_held_out):
                idx = int(round((i + 0.5) * step))
                idx = min(idx, num_usable - 1)
                held_out_indices.add(idx)

        recon_files = []
        held_out_files = []

        for idx, r in enumerate(usable_records):
            src_file = r["clean_path"]
            if idx in held_out_indices:
                dst_file = held_out_path / r["filename"]
                r["split"] = "Held-Out"
                held_out_files.append(r["filename"])
            else:
                dst_file = recon_path / r["filename"]
                r["split"] = "Reconstruction"
                recon_files.append(r["filename"])
            shutil.copy2(str(src_file), str(dst_file))

        for r in excluded_records:
            r["split"] = "Excluded"

        # Update dataset_split.json
        split_data = {
            "total_images": len(files),
            "reconstruction_count": len(recon_files),
            "held_out_count": len(held_out_files),
            "excluded_count": len(excluded_records),
            "reconstruction_images": recon_files,
            "held_out_images": held_out_files,
            "excluded_images": [r["filename"] for r in excluded_records],
            "timestamp": datetime.now().isoformat()
        }
        with open(split_json, "w", encoding="utf-8") as f:
            json.dump(split_data, f, indent=2)
        print(f"  [OK] Updated dataset split: {split_json}")
        print(f"       -> {len(recon_files)} in data/01_reconstruction/")
        print(f"       -> {len(held_out_files)} in data/02_held_out/")

    # Generate Preprocessing Audit Report
    write_preprocessing_report(report_md, records, camera_profiles, max_dim, blur_threshold)
    print(f"  [OK] Saved report: {report_md}")
    print("=" * 70 + "\n")
    return True


def write_preprocessing_report(report_path, records, camera_profiles, max_dim, blur_threshold):
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Phase 2: Casual Photo Preprocessing & Normalization Report\n\n")
        f.write(f"- **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Total Source Images:** {len(records)}\n")
        f.write(f"- **Max Allowed Dimension:** {max_dim} px\n")
        f.write(f"- **Sharpness / Blur Threshold:** {blur_threshold:.1f} (Laplacian variance)\n\n")

        f.write("## Camera & Lens Profiles Detected\n\n")
        if len(camera_profiles) > 1:
            f.write("> [!IMPORTANT]\n")
            f.write(f"> **Multiple camera / lens profiles detected ({len(camera_profiles)}).**\n")
            f.write("> When running COLMAP SfM, do **not** force a single shared camera model.\n")
            f.write("> The pipeline will automatically supply `--ImageReader.single_camera 0`\n")
            f.write("> and `--ImageReader.camera_model SIMPLE_RADIAL` for independent self-calibration.\n\n")
        else:
            f.write(f"- Single lens profile: `{list(camera_profiles)[0] if camera_profiles else 'None'}`\n\n")

        for cp in sorted(camera_profiles):
            count = sum(1 for r in records if r["camera_profile"] == cp)
            f.write(f"- `{cp}`: {count} images\n")
        f.write("\n")

        f.write("## Image Inspection & Normalization Table\n\n")
        f.write("| Filename | Original Size | Clean Size | Auto-Orientation | Sharpness Score | Status | Split |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in records:
            rot = "Rotated upright" if r["was_rotated"] else "Already upright"
            f.write(f"| `{r['filename']}` | {r['orig_size']} | {r['new_size']} | {rot} | {r['blur_score']:.1f} | {r['status']} | {r.get('split', 'N/A')} |\n")
        f.write("\n")

        f.write("## Recommended Next Steps\n\n")
        f.write("1. Check any images marked `BLURRY` or `EXCLUDED (BLUR)`.\n")
        f.write("2. If important surfaces were excluded, take 1-2 steady replacement shots.\n")
        f.write("3. Run Phase 2 SfM via `python scripts/run_colmap_sfm.py` or master `python scripts/run_pipeline.py`.\n")


def main():
    parser = argparse.ArgumentParser(description="Preprocess and normalize casual handheld smartphone photos")
    parser.add_argument("--source_dir", default=str(DEFAULT_SOURCE_DIR), help="Source directory containing raw images")
    parser.add_argument("--output_dir", default=str(DEFAULT_OUTPUT_DIR), help="Destination for normalized images")
    parser.add_argument("--recon_dir", default=str(DEFAULT_RECON_DIR), help="Destination for reconstruction subset")
    parser.add_argument("--held_out_dir", default=str(DEFAULT_HELD_OUT_DIR), help="Destination for held-out subset")
    parser.add_argument("--split_json", default=str(DEFAULT_SPLIT_JSON), help="Path to dataset_split.json")
    parser.add_argument("--report_md", default=str(DEFAULT_REPORT_MD), help="Path to preprocessing report markdown")
    parser.add_argument("--max_dim", type=int, default=2560, help="Max width/height (px) to prevent OOM (0=keep full)")
    parser.add_argument("--blur_threshold", type=float, default=50.0, help="Laplacian variance threshold for sharpness")
    parser.add_argument("--no_exclude_blurry", action="store_true", help="Keep blurry images in reconstruction anyway")
    parser.add_argument("--held_out_ratio", type=float, default=0.15, help="Ratio of photos reserved for held-out validation")
    parser.add_argument("--no_auto_split", action="store_true", help="Do not automatically populate reconstruction/held_out folders")

    args = parser.parse_args()

    preprocess_dataset(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        recon_dir=args.recon_dir,
        held_out_dir=args.held_out_dir,
        split_json=args.split_json,
        report_md=args.report_md,
        max_dim=args.max_dim,
        blur_threshold=args.blur_threshold,
        exclude_blurry=not args.no_exclude_blurry,
        held_out_ratio=args.held_out_ratio,
        auto_split=not args.no_auto_split
    )


if __name__ == "__main__":
    main()
