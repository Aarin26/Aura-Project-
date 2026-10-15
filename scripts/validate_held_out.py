#!/usr/bin/env python3
"""Compare held-out bottle silhouettes using the dataset's recorded cameras.

This intentionally reports silhouette-envelope IoU only. It does not claim a
photometric/SSIM score because a faithful material renderer is not part of this
pipeline.
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import ConvexHull, QhullError

try:
    import trimesh
except ImportError:
    print("[ERROR] trimesh is required.")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MESH = BASE_DIR / "outputs" / "phase_7_export" / "asset.obj"
DEFAULT_HELD_OUT = BASE_DIR / "data" / "02_held_out"
DEFAULT_CAMERAS = BASE_DIR / "data" / "syncom_bottle" / "cameras.json"
DEFAULT_OUTPUT = BASE_DIR / "outputs" / "phase_6_validation"
DEFAULT_SPLIT = BASE_DIR / "manifests" / "dataset_split.json"
DEFAULT_SCALE = BASE_DIR / "manifests" / "scale_reference.json"
DEFAULT_ALIGNMENT = BASE_DIR / "outputs" / "phase_7_export" / "camera_alignment.json"


def load_mask(path):
    image = Image.open(path)
    if "A" in image.getbands():
        return np.asarray(image.getchannel("A")) > 20
    rgb = np.asarray(image.convert("RGB"))
    # The benchmark images have a textured background. Use its alpha whenever
    # available; RGB-only images need a border-color distance estimate.
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)
    return np.linalg.norm(rgb.astype(float) - bg, axis=2) > 18.0


def render_silhouette_envelope(mesh, camera, width, height, alignment):
    """Project the mesh into a dataset camera and rasterize its 2D convex hull."""
    # The reconstruction export maps source Z-up to engine Y-up: (x,y,z)->(x,z,-y).
    scale = float(alignment["scale_factor"])
    source_z_min = float(alignment["source_z_min"])
    v = np.asarray(mesh.vertices, dtype=np.float64)
    source = np.column_stack([v[:, 0] / scale, -v[:, 2] / scale, v[:, 1] / scale + source_z_min])

    c2w = np.asarray(camera["extr"], dtype=np.float64).reshape(4, 4)
    gl_to_cv = np.diag([1.0, -1.0, -1.0, 1.0])
    w2c = np.linalg.inv(c2w @ gl_to_cv)
    cam = (w2c @ np.column_stack([source, np.ones(len(source))]).T).T[:, :3]
    fx, fy, cx, cy = camera["intr"]
    visible = cam[:, 2] > 1e-5
    xy = np.empty((np.count_nonzero(visible), 2), dtype=np.float64)
    xyz = cam[visible]
    xy[:, 0] = fx * xyz[:, 0] / xyz[:, 2] + cx
    xy[:, 1] = fy * xyz[:, 1] / xyz[:, 2] + cy
    xy = xy[np.isfinite(xy).all(axis=1)]

    mask = Image.new("L", (width, height), 0)
    if len(xy) < 3:
        return np.asarray(mask) > 0
    try:
        hull = ConvexHull(xy)
    except QhullError:
        return np.asarray(mask) > 0
    polygon = [(float(x), float(y)) for x, y in xy[hull.vertices]]
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    return np.asarray(mask) > 0


def comparison_board(real_image, real_mask, predicted, image_name, iou, output_path):
    real = real_image.convert("RGB")
    pred = Image.fromarray((predicted * 255).astype(np.uint8)).convert("RGB")
    mismatch = np.logical_xor(real_mask, predicted)
    overlay = np.zeros((*mismatch.shape, 3), dtype=np.uint8)
    overlay[real_mask & predicted] = [40, 180, 80]
    overlay[real_mask & ~predicted] = [240, 50, 50]
    overlay[~real_mask & predicted] = [40, 120, 255]
    diff = Image.fromarray(overlay, "RGB")
    w, h = real.size
    board = Image.new("RGB", (w * 3, h + 55), (30, 32, 36))
    draw = ImageDraw.Draw(board)
    draw.text((15, 15), f"{image_name} | silhouette-envelope IoU {iou:.4f}", fill="white")
    board.paste(real, (0, 55))
    board.paste(pred, (w, 55))
    board.paste(diff, (2 * w, 55))
    draw.text((12, 38), "Held-out image", fill="white")
    draw.text((w + 12, 38), "Camera-matched projected hull", fill="white")
    draw.text((2 * w + 12, 38), "Green overlap / red miss / blue extra", fill="white")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(output_path)


def main():
    parser = argparse.ArgumentParser(description="Held-out silhouette validation using supplied camera poses")
    parser.add_argument("--mesh", default=str(DEFAULT_MESH))
    parser.add_argument("--held_out_dir", default=str(DEFAULT_HELD_OUT))
    parser.add_argument("--camera_file", default=str(DEFAULT_CAMERAS))
    parser.add_argument("--output_dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dataset_split", default=str(DEFAULT_SPLIT))
    parser.add_argument("--scale_reference", default=str(DEFAULT_SCALE))
    parser.add_argument("--alignment_file", default=str(DEFAULT_ALIGNMENT))
    args = parser.parse_args()

    mesh_path = Path(args.mesh)
    if not mesh_path.exists():
        raise FileNotFoundError(f"Candidate mesh not found: {mesh_path}")
    loaded = trimesh.load(mesh_path, process=False)
    if isinstance(loaded, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)))
    else:
        mesh = loaded

    split = json.loads(Path(args.dataset_split).read_text(encoding="utf-8"))
    cameras = json.loads(Path(args.camera_file).read_text(encoding="utf-8"))["cameras"]
    scale_ref = json.loads(Path(args.scale_reference).read_text(encoding="utf-8"))
    target_height = float(scale_ref["ground_truth_distance"])
    alignment_path = Path(args.alignment_file)
    if not alignment_path.exists():
        raise FileNotFoundError(f"Reconstruction alignment metadata is required: {alignment_path}")
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    if abs(float(alignment["target_height_m"]) - target_height) > 1e-6:
        raise ValueError("The candidate mesh alignment metadata and scale reference do not match")
    held_out = split["held_out_images"]
    held_dir = Path(args.held_out_dir)
    output_dir = Path(args.output_dir)
    renders_dir = output_dir / "renders"
    rows = []

    for filename in held_out:
        image_path = held_dir / filename
        if not image_path.exists():
            raise FileNotFoundError(f"Held-out image is missing: {image_path}")
        key = Path(filename).stem
        if key not in cameras:
            raise KeyError(f"No recorded camera pose for held-out image {filename}")
        image = Image.open(image_path)
        real_mask = load_mask(image_path)
        predicted = render_silhouette_envelope(mesh, cameras[key], image.width, image.height, alignment)
        union = np.count_nonzero(real_mask | predicted)
        iou = float(np.count_nonzero(real_mask & predicted) / union) if union else 1.0
        board = renders_dir / f"comparison_{key}.png"
        comparison_board(image, real_mask, predicted, filename, iou, board)
        rows.append({
            "image": filename,
            "silhouette_envelope_iou": f"{iou:.5f}",
            "status": "EVALUATED",
            "comparison_board": f"renders/{board.name}",
        })
        print(f"{filename}: silhouette-envelope IoU={iou:.4f}")

    mean_iou = float(np.mean([float(r["silhouette_envelope_iou"]) for r in rows])) if rows else 0.0
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "per_view_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "silhouette_envelope_iou", "status", "comparison_board"])
        writer.writeheader()
        writer.writerows(rows)
    with (output_dir / "validation_report.md").open("w", encoding="utf-8") as f:
        f.write("# Held-Out Validation Report\n\n")
        f.write(f"- Validation date: {datetime.now().isoformat()}\n")
        f.write(f"- Candidate: `{mesh_path}` ({len(mesh.vertices):,} vertices, {len(mesh.faces):,} triangles)\n")
        f.write(f"- Held-out views evaluated with supplied camera intrinsics/extrinsics: {len(rows)}\n")
        f.write(f"- Mean silhouette-envelope IoU: **{mean_iou:.4f}**\n\n")
        f.write("The predicted mask is the 2D convex hull of projected mesh vertices. This measures overall silhouette coverage only; it does not score color, concavities, occlusion detail, or unseen surfaces. No SSIM or appearance pass is claimed.\n\n")
        f.write("| Image | Silhouette-envelope IoU | Comparison |\n|---|---:|---|\n")
        for row in rows:
            f.write(f"| {row['image']} | {row['silhouette_envelope_iou']} | [{Path(row['comparison_board']).name}]({row['comparison_board']}) |\n")
    print(f"Mean silhouette-envelope IoU: {mean_iou:.4f}")


if __name__ == "__main__":
    main()
