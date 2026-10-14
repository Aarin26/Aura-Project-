#!/usr/bin/env python3
"""
Phase 1 — check_environment.py
Records OS, CPU, RAM, GPU, CUDA, disk space and installed tool versions.
Run this before your first baseline Meshroom/COLMAP job.
"""

import platform
import shutil
import subprocess
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "outputs" / "phase_1_baseline" / "environment_setup.md"


def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"ERROR: {e}"


def get_tool_version(tool, flag="--version"):
    path = shutil.which(tool)
    if not path:
        return "NOT FOUND"
    return run_cmd([tool, flag])


def get_disk_free_gb(path="."):
    total, used, free = shutil.disk_usage(path)
    return round(free / (1024 ** 3), 2)


def main():
    info = {}

    # OS / Platform
    info["os"] = platform.platform()
    info["python"] = sys.version.split("\n")[0]

    # CPU
    info["cpu"] = platform.processor() or "unknown"
    try:
        import psutil
        info["ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 2)
    except ImportError:
        info["ram_gb"] = "psutil not installed — install with: pip install psutil"

    # Disk
    info["disk_free_gb"] = get_disk_free_gb(str(BASE_DIR))

    # GPU / CUDA
    info["nvidia_smi"] = run_cmd(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"])
    info["nvcc_version"] = get_tool_version("nvcc", "--version")

    # Tool versions
    info["colmap"] = get_tool_version("colmap", "-h")[:80] if shutil.which("colmap") else "NOT FOUND"
    info["python_packages"] = run_cmd([sys.executable, "-m", "pip", "show", "open3d", "Pillow", "numpy"])

    # Write Markdown report
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# Environment Setup Guide — Phase 1\n\n")
        f.write(f"## OS\n`{info['os']}`\n\n")
        f.write(f"## CPU\n`{info['cpu']}`\n\n")
        f.write(f"## RAM\n`{info['ram_gb']} GB`\n\n")
        f.write(f"## Disk Free (project drive)\n`{info['disk_free_gb']} GB`\n\n")
        f.write(f"## GPU / CUDA\n```\n{info['nvidia_smi']}\nnvcc: {info['nvcc_version']}\n```\n\n")
        f.write(f"## Python\n`{info['python']}`\n\n")
        f.write(f"## Key Python Packages\n```\n{info['python_packages']}\n```\n\n")
        f.write(f"## COLMAP\n```\n{info['colmap']}\n```\n\n")
        f.write("\n## Tool Version Table\n\n")
        f.write("| Tool | Version | Notes |\n| :--- | :--- | :--- |\n")
        f.write("| Meshroom | *(fill in)* | *(installation path)* |\n")
        f.write("| COLMAP | *(fill in)* | *(installation path)* |\n")
        f.write("| OpenMVS | *(fill in)* | *(optional)* |\n")
        f.write("| MeshLab | *(fill in)* | *(installation path)* |\n")
        f.write("| Blender | *(fill in)* | *(installation path)* |\n\n")
        f.write("## Test Run Checklist\n\n")
        f.write("- [ ] Loaded 5–10 test images from `data/01_reconstruction/` into Meshroom\n")
        f.write("- [ ] Feature extraction completed without crash\n")
        f.write("- [ ] GPU/CUDA is recognized (not falling back to CPU)\n")
        f.write("- [ ] Estimated runtime for full image set: *(fill in)* minutes\n")
        f.write("- [ ] Peak RAM during test run: *(fill in)* GB\n\n")
        f.write("## Notes\n\n*(Any deviations, workarounds, or environment-specific issues)*\n")

    print(f"Environment report written to: {OUTPUT_FILE}")
    print(json.dumps({k: v for k, v in info.items() if k != "python_packages"}, indent=2))


if __name__ == "__main__":
    main()

