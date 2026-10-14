#!/usr/bin/env python3
"""
Phase 2 — prepare_for_colmap.py
Pre-flight checks before running COLMAP SfM:
  - Verifies that data/01_reconstruction/ has images
  - Verifies that data/02_held_out/ has images
  - Reads manifests/dataset_split.json to confirm the split is recorded
  - Verifies manifests/scale_reference.json has a non-zero ground truth distance
  - Counts images, lists camera models from EXIF, warns about mixed cameras
  - Prints exact COLMAP commands to run for this project

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
                   if f.is_file() and f.suffix.lower() in IMAGE_EXTS])


def get_camera_models(images):
    if not PIL_AVAILABLE:
        return set()
    models = set()
    for img_path in images[:20]:  # sample first 20
        try:
            with Image.open(img_path) as img:
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        if ExifTags.TAGS.get(tag_id) == "Model":
                            models.add(str(value).strip())
        except Exception:
            pass
    return models


def separator():
    print("-" * 60)


def main():
    print("\n" + "=" * 60)
    print("  Phase 2 Pre-Flight Check")
    print("=" * 60)

    all_ok = True

    # 1. Reconstruction images
    separator()
    recon_images = get_images(RECON_DIR)
    if len(recon_images) == 0:
        print(f"{FAIL} data/01_reconstruction/ is EMPTY")
        print(f"       -> Copy your reconstruction photos here before running COLMAP")
        all_ok = False
    else:
        print(f"{PASS} Reconstruction images: {len(recon_images)}")
        cameras = get_camera_models(recon_images)
        if len(cameras) > 1:
            print(f"{WARN} Multiple camera models: {cameras}")
            print(f"       -> Use --ImageReader.camera_model SIMPLE_RADIAL and review per-camera grouping")
        elif len(cameras) == 1:
            print(f"{PASS} Single camera model: {list(cameras)[0]}")
        else:
            print(f"{WARN} No EXIF camera model found — COLMAP will self-calibrate")

    # 2. Held-out images
    held_out_images = get_images(HELD_OUT_DIR)
    if len(held_out_images) == 0:
        print(f"{WARN} data/02_held_out/ is EMPTY")
        print(f"       -> Reserve ~10-15% of photos as held-out before running SfM")
    else:
        print(f"{PASS} Held-out images:         {len(held_out_images)}")

    # 3. Dataset split manifest
    separator()
    try:
        with open(SPLIT_JSON, encoding="utf-8") as f:
            split = json.load(f)
        if split.get("reconstruction_count", 0) == 0:
            print(f"{WARN} dataset_split.json: reconstruction_count = 0 (not yet filled in)")
            print(f"       -> Update manifests/dataset_split.json after you finalize the split")
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
            print(f"       -> Measure and record a known physical distance before Phase 3")
        else:
            print(f"{PASS} Scale reference: {dist} {scale.get('units', '?')}")
    except Exception as e:
        print(f"{FAIL} Cannot read scale_reference.json: {e}")
        all_ok = False

    # 5. Output dir
    separator()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{PASS} Output directory ready: outputs/phase_2_sparse/")

    # 6. COLMAP commands
    separator()
    print("\n  COLMAP Commands to Run (copy-paste into your terminal):\n")
    db = OUTPUT_DIR / "colmap.db"
    sparse = OUTPUT_DIR / "sparse"
    print(f"  # Step 1 - Feature Extraction")
    print(f"  colmap feature_extractor \\")
    print(f"      --database_path \"{db}\" \\")
    print(f"      --image_path \"{RECON_DIR}\" \\")
    print(f"      --ImageReader.camera_model RADIAL")
    print()
    print(f"  # Step 2 - Exhaustive Feature Matching")
    print(f"  colmap exhaustive_matcher \\")
    print(f"      --database_path \"{db}\"")
    print()
    print(f"  # Step 3 - Incremental SfM Mapper")
    print(f"  colmap mapper \\")
    print(f"      --database_path \"{db}\" \\")
    print(f"      --image_path \"{RECON_DIR}\" \\")
    print(f"      --output_path \"{sparse}\"")
    print()
    print(f"  # Step 4 - Convert model to TXT for inspection")
    print(f"  colmap model_converter \\")
    print(f"      --input_path \"{sparse}\\0\" \\")
    print(f"      --output_path \"{sparse}\\0\" \\")
    print(f"      --output_type TXT")
    print()
    print(f"  # Or run all at once via the pipeline script:")
    print(f"  python scripts/run_colmap_sfm.py")
    print()

    separator()
    if not all_ok:
        print(f"\n{FAIL} Pre-flight FAILED. Fix the issues above before running COLMAP.\n")
        sys.exit(1)
    elif len(recon_images) == 0:
        print(f"\n{WARN} Pre-flight INCOMPLETE. Add images to data/01_reconstruction/ first.\n")
        sys.exit(1)
    else:
        print(f"\n{PASS} Pre-flight PASSED. You can now run COLMAP for Phase 2.\n")


if __name__ == "__main__":
    main()
