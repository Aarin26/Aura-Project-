#!/usr/bin/env python3
"""
Phase 2 — prepare_for_colmap.py
Pre-flight checks before running COLMAP SfM:
  - Verifies data/01_reconstruction/ and data/02_held_out/ image counts
  - Checks EXIF orientation flags (detects un-transposed phone images)
  - Inspects camera models and focal lengths (multi-lens / zoom detection)
  - Checks image dimensions (flags oversized photos likely to cause GPU OOM)
  - Reads manifests/dataset_split.json and manifests/scale_reference.json
  - Recommends smartphone-optimized COLMAP parameters (SIMPLE_RADIAL, guided matching)
  - Prints exact copy-pasteable COLMAP terminal commands

Usage:
    python scripts/prepare_for_colmap.py
"""

import json
import sys
from pathlib import Path

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".cr2", ".nef", ".dng"}

RECON_DIR = BASE_DIR / "data" / "01_reconstruction"
HELD_OUT_DIR = BASE_DIR / "data" / "02_held_out"
SPLIT_JSON = BASE_DIR / "manifests" / "dataset_split.json"
SCALE_JSON = BASE_DIR / "manifests" / "scale_reference.json"
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_2_sparse"

PASS = "[OK]  "
WARN = "[WARN]"
FAIL = "[FAIL]"


def get_images(directory):
    return sorted([f for f in Path(directory).iterdir()
                   if f.is_file() and f.suffix.lower() in IMAGE_EXTS and not f.name.startswith(".")])


def inspect_camera_profiles(images):
    """Samples images to extract camera model, focal length, orientation, and resolution."""
    if not PIL_AVAILABLE or not images:
        return {"models": set(), "focal_lengths": set(), "needs_rotation": 0, "max_dim": 0}

    models = set()
    focal_lengths = set()
    needs_rotation = 0
    max_dim = 0

    for img_path in images:
        try:
            with Image.open(img_path) as img:
                w, h = img.size
                max_dim = max(max_dim, w, h)
                exif = img._getexif() or {}
                orient = exif.get(0x0112, 1)
                if orient != 1:
                    needs_rotation += 1

                for tag_id, value in exif.items():
                    tag = ExifTags.TAGS.get(tag_id)
                    if tag == "Model":
                        models.add(str(value).strip())
                    elif tag == "FocalLength":
                        if hasattr(value, "numerator") and hasattr(value, "denominator"):
                            fl = round(value.numerator / value.denominator, 1)
                        elif isinstance(value, (tuple, list)) and len(value) == 2 and value[1] != 0:
                            fl = round(float(value[0]) / float(value[1]), 1)
                        elif hasattr(value, "__float__"):
                            fl = round(float(value), 1)
                        else:
                            fl = str(value)
                        focal_lengths.add(fl)
        except Exception:
            pass

    return {
        "models": models,
        "focal_lengths": focal_lengths,
        "needs_rotation": needs_rotation,
        "max_dim": max_dim
    }


def separator():
    print("-" * 65)


def main():
    print("\n" + "=" * 65)
    print("  Phase 2 Pre-Flight & Casual Capture Verification Check")
    print("=" * 65)

    all_ok = True

    # 1. Reconstruction images
    separator()
    recon_images = get_images(RECON_DIR)
    if len(recon_images) == 0:
        print(f"{FAIL} data/01_reconstruction/ is EMPTY")
        print("       -> Run 'python scripts/preprocess_casual_photos.py' to process raw images")
        all_ok = False
    else:
        print(f"{PASS} Reconstruction images: {len(recon_images)}")
        prof = inspect_camera_profiles(recon_images)

        # Camera Model check
        if len(prof["models"]) > 1:
            print(f"{WARN} Multiple camera models detected: {prof['models']}")
            print("       -> Will use --ImageReader.single_camera 0 for independent camera models")
        elif len(prof["models"]) == 1:
            print(f"{PASS} Camera Model: {list(prof['models'])[0]}")
        else:
            print(f"{WARN} No EXIF camera model found - COLMAP will self-calibrate")

        # Focal Length / Multi-lens check
        if len(prof["focal_lengths"]) > 1:
            print(f"{WARN} Multiple focal lengths detected: {prof['focal_lengths']} mm")
            print("       -> Suggests multi-lens phone or zoom; use --ImageReader.single_camera 0")
        elif len(prof["focal_lengths"]) == 1:
            print(f"{PASS} Single focal length: {list(prof['focal_lengths'])[0]} mm")

        # EXIF Orientation check
        if prof["needs_rotation"] > 0:
            print(f"{WARN} {prof['needs_rotation']} images have raw EXIF orientation flags (not transposed upright).")
            print("       -> Highly recommended: run 'python scripts/preprocess_casual_photos.py' first")
        else:
            print(f"{PASS} Image orientations verified upright (normalized EXIF)")

        # Resolution check
        if prof["max_dim"] > 3840:
            print(f"{WARN} Image resolution is very high ({prof['max_dim']}px max edge).")
            print("       -> May cause high RAM/GPU VRAM usage. Consider downscaling to 2560px via preprocess script.")
        else:
            print(f"{PASS} Image dimensions safe for reconstruction (max edge: {prof['max_dim']}px)")

    # 2. Held-out images
    held_out_images = get_images(HELD_OUT_DIR)
    if len(held_out_images) == 0:
        print(f"{WARN} data/02_held_out/ is EMPTY")
        print("       -> Reserve ~10-15% of photos as held-out before running SfM")
    else:
        print(f"{PASS} Held-out images:         {len(held_out_images)}")

    # 3. Dataset split manifest
    separator()
    try:
        with open(SPLIT_JSON, encoding="utf-8") as f:
            split = json.load(f)
        if split.get("reconstruction_count", 0) == 0:
            print(f"{WARN} dataset_split.json: reconstruction_count = 0")
            print("       -> Update manifests/dataset_split.json or run scripts/preprocess_casual_photos.py")
        else:
            print(f"{PASS} dataset_split.json: {split['reconstruction_count']} reconstruction, {split['held_out_count']} held-out")
    except Exception as e:
        print(f"{FAIL} Cannot read dataset_split.json: {e}")
        all_ok = False

    # 4. Scale reference
    try:
        with open(SCALE_JSON, encoding="utf-8") as f:
            scale = json.load(f)
        dist = scale.get("ground_truth_distance", 0)
        if dist == 0 or dist is None:
            print(f"{WARN} scale_reference.json: ground_truth_distance = 0 (not yet measured)")
            print("       -> Measure and record a known physical distance before Phase 3")
        else:
            print(f"{PASS} Scale reference: {dist} {scale.get('units', '?')}")
    except Exception as e:
        print(f"{FAIL} Cannot read scale_reference.json: {e}")
        all_ok = False

    # 5. Output dir
    separator()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{PASS} Output directory ready: outputs/phase_2_sparse/")

    # 6. Smartphone-Optimized COLMAP commands
    separator()
    print("\n  Recommended COLMAP Commands (Optimized for Casual Mobile Captures):\n")
    db = OUTPUT_DIR / "colmap.db"
    sparse = OUTPUT_DIR / "sparse"
    
    # Check if multiple lenses or zoom
    single_cam_flag = "1" if (PIL_AVAILABLE and len(inspect_camera_profiles(recon_images)["focal_lengths"]) <= 1 and len(inspect_camera_profiles(recon_images)["models"]) <= 1) else "0"

    print("  # Step 1 - Feature Extraction (SIMPLE_RADIAL camera self-calibration)")
    print(f"  colmap feature_extractor \\")
    print(f"      --database_path \"{db}\" \\")
    print(f"      --image_path \"{RECON_DIR}\" \\")
    print(f"      --ImageReader.camera_model SIMPLE_RADIAL \\")
    print(f"      --ImageReader.single_camera {single_cam_flag} \\")
    print(f"      --SiftExtraction.max_num_features 8192")
    print()
    print("  # Step 2 - Guided Feature Matching (Filters cluttered backgrounds & wide baselines)")
    print(f"  colmap exhaustive_matcher \\")
    print(f"      --database_path \"{db}\" \\")
    print(f"      --SiftMatching.guided_matching 1")
    print()
    print("  # Step 3 - Incremental SfM Mapper")
    print(f"  colmap mapper \\")
    print(f"      --database_path \"{db}\" \\")
    print(f"      --image_path \"{RECON_DIR}\" \\")
    print(f"      --output_path \"{sparse}\"")
    print()
    print("  # Step 4 - Convert model to TXT format")
    print(f"  colmap model_converter \\")
    print(f"      --input_path \"{sparse}\\0\" \\")
    print(f"      --output_path \"{sparse}\\0\" \\")
    print(f"      --output_type TXT")
    print()
    print("  # Or run automated runner:")
    print("  python scripts/run_colmap_sfm.py")
    print()

    separator()
    if not all_ok:
        print(f"\n{FAIL} Pre-flight FAILED. Fix the issues above before running COLMAP.\n")
        sys.exit(1)
    elif len(recon_images) == 0:
        print(f"\n{WARN} Pre-flight INCOMPLETE. Run 'python scripts/preprocess_casual_photos.py' first.\n")
        sys.exit(1)
    else:
        print(f"\n{PASS} Pre-flight PASSED. Ready for Phase 2 Reconstruction.\n")


if __name__ == "__main__":
    main()
