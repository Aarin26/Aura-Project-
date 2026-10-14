#!/usr/bin/env python3
"""
scripts/download_syncom_dataset.py
Downloads the SynCom bottle multi-view dataset from Hugging Face:
Repo: yGaoJiany/SynCom
Subfolder: object/bottle/test/images/

Downloads the multi-view images into a new folder in data/, e.g., data/syncom_bottle/

Usage:
    python scripts/download_syncom_dataset.py
    python scripts/download_syncom_dataset.py --dest_dir data/syncom_bottle --include_exr
"""

import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DEST = BASE_DIR / "data" / "syncom_bottle"
REPO_ID = "yGaoJiany/SynCom"
SUBFOLDER = "object/bottle/test/images"
TREE_API_URL = f"https://huggingface.co/api/datasets/{REPO_ID}/tree/main/{SUBFOLDER}"
RAW_BASE_URL = f"https://huggingface.co/datasets/{REPO_ID}/resolve/main/{SUBFOLDER}"


def fetch_file_list(include_exr=False):
    """Fetches list of file objects from Hugging Face dataset tree API."""
    req = urllib.request.Request(
        TREE_API_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            files = []
            for item in data:
                if item.get("type") == "file":
                    p = item.get("path", "")
                    name = Path(p).name
                    ext = Path(p).suffix.lower()
                    if ext == ".png" or (include_exr and ext == ".exr"):
                        files.append({
                            "name": name,
                            "path": p,
                            "size": item.get("size", 0),
                            "url": f"{RAW_BASE_URL}/{name}"
                        })
            return files
    except Exception as e:
        print(f"[WARN] Failed to fetch tree API ({e}). Falling back to standard index range (0000.png - 0099.png).")
        # Fallback to generating 0000.png through 0099.png (100 test views)
        files = []
        for i in range(100):
            fname = f"{i:04d}.png"
            files.append({
                "name": fname,
                "path": f"{SUBFOLDER}/{fname}",
                "size": 0,
                "url": f"{RAW_BASE_URL}/{fname}"
            })
            if include_exr:
                exr_name = f"{i:04d}.exr"
                files.append({
                    "name": exr_name,
                    "path": f"{SUBFOLDER}/{exr_name}",
                    "size": 0,
                    "url": f"{RAW_BASE_URL}/{exr_name}"
                })
        return files


def download_single_file(file_info, dest_dir):
    """Downloads one file from Hugging Face if not already present or incomplete."""
    out_path = Path(dest_dir) / file_info["name"]
    expected_size = file_info.get("size", 0)

    if out_path.exists():
        if expected_size > 0 and out_path.stat().st_size == expected_size:
            return file_info["name"], True, "Already exists"
        elif expected_size == 0 and out_path.stat().st_size > 10000:
            return file_info["name"], True, "Already exists"

    url = file_info["url"]
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp, open(out_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            return file_info["name"], True, "Downloaded"
        except Exception as e:
            if attempt == max_retries - 1:
                return file_info["name"], False, str(e)
            time.sleep(1.0)


def main():
    parser = argparse.ArgumentParser(description="Download SynCom bottle dataset from Hugging Face")
    parser.add_argument("--dest_dir", default=str(DEFAULT_DEST),
                        help="Target directory in data/ to store images (default: data/syncom_bottle)")
    parser.add_argument("--include_exr", action="store_true",
                        help="Also download high-dynamic range EXR files (~740MB) in addition to PNGs")
    parser.add_argument("--workers", type=int, default=8,
                        help="Number of concurrent download threads (default: 8)")
    args = parser.parse_args()

    dest = Path(args.dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print("  HUGGING FACE DATASET DOWNLOADER: SynCom Bottle")
    print(f"  Source:      https://huggingface.co/datasets/{REPO_ID}")
    print(f"  Folder:      {SUBFOLDER}")
    print(f"  Destination: {dest}")
    print(f"  Format:      PNG images {'+ EXR files' if args.include_exr else '(RGB renders)'}")
    print("=" * 65)

    print("\n[1/3] Querying Hugging Face file manifest...")
    files = fetch_file_list(include_exr=args.include_exr)
    print(f"  Found {len(files)} target files to download.")

    total_bytes = sum(f.get("size", 0) for f in files)
    if total_bytes > 0:
        print(f"  Total estimated size: {total_bytes / (1024*1024):.1f} MB")

    print(f"\n[2/3] Downloading {len(files)} files using {args.workers} concurrent threads...")
    t0 = time.time()
    success_count = 0
    failed_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_single_file, f, dest): f for f in files}
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            name, ok, msg = future.result()
            if ok:
                success_count += 1
            else:
                failed_count += 1
                print(f"  [ERROR] {name}: {msg}")

            if completed % 10 == 0 or completed == len(files):
                pct = (completed / len(files)) * 100
                print(f"  Progress: {completed:3d}/{len(files)} ({pct:5.1f}%) | {success_count} OK, {failed_count} Errors")

    dt = time.time() - t0
    print("\n" + "=" * 65)
    print(f"  [3/3] DOWNLOAD COMPLETE in {dt:.1f}s")
    print(f"  Saved {success_count} files to: {dest}")
    if failed_count > 0:
        print(f"  Warning: {failed_count} files failed to download.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()

