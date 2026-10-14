#!/usr/bin/env python3
"""
scripts/auto_reconstruct.py
Universal 3D Reconstruction Auto-Detector and Dispatcher.

Scans the data/ folder for any dataset (folder with images) and automatically
reconstructs a 3D model for each one.

Supported dataset types:
  - SynCom-style (has cameras.json + calibrated PNG views)
      -> Uses visual hull surface-of-revolution reconstruction.
  - Generic / Casual phone photos (just JPG/PNG images, no cameras.json)
      -> Uses silhouette-based convex hull + gradient texture baking.

Usage:
    # Auto-scan all datasets in data/ folder:
    python scripts/auto_reconstruct.py --auto

    # Process one specific dataset:
    python scripts/auto_reconstruct.py --dataset_dir data/syncom_bottle

    # List all detected datasets and exit:
    python scripts/auto_reconstruct.py --list
"""

import argparse
import json
import math
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("[ERROR] trimesh is required. Run: pip install trimesh")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MANIFESTS_DIR = BASE_DIR / "manifests"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
MIN_IMAGES = 5  # minimum images to consider a folder a dataset


# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

def step_banner(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def detect_dataset_type(dataset_dir: Path) -> str:
    """
    Returns:
        'syncom'  - has cameras.json (calibrated multi-view dataset)
        'generic' - just images, no pose info
        'empty'   - not enough images
    """
    images = [f for f in dataset_dir.iterdir()
              if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
    if len(images) < MIN_IMAGES:
        return "empty"
    if (dataset_dir / "cameras.json").exists():
        return "syncom"
    return "generic"


def find_datasets(data_dir: Path) -> list:
    """Scan data_dir for sub-folders that look like datasets."""
    datasets = []
    for d in sorted(data_dir.iterdir()):
        if not d.is_dir():
            continue
        # Skip the internal split folders that are children of the workflow
        if d.name in {"00_raw_master", "01_reconstruction", "02_held_out", "03_preprocessed"}:
            continue
        dtype = detect_dataset_type(d)
        if dtype != "empty":
            images = [f for f in d.iterdir()
                      if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
            datasets.append({
                "path": d,
                "name": d.name,
                "type": dtype,
                "image_count": len(images),
            })
    return datasets


def count_images(dataset_dir: Path) -> list:
    return sorted([f for f in dataset_dir.iterdir()
                   if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS])


# ---------------------------------------------------------------------------
# SYNCOM-STYLE RECONSTRUCTION (calibrated cameras.json)
# ---------------------------------------------------------------------------

def syncom_reconstruct(dataset_dir: Path, output_dir: Path):
    """Full visual hull reconstruction for SynCom-style calibrated datasets."""
    step_banner(f"SynCom Reconstruction: {dataset_dir.name}")

    output_dir.mkdir(parents=True, exist_ok=True)
    tex_dir = output_dir / "textures"
    tex_dir.mkdir(exist_ok=True)

    # --- Load camera data ---
    with open(dataset_dir / "cameras.json", encoding="utf-8") as f:
        cams = json.load(f)["cameras"]

    gl_to_cv = np.diag([1.0, -1.0, -1.0, 1.0])

    # Detect image size from first image
    first_img = count_images(dataset_dir)[0]
    with Image.open(first_img) as im:
        img_w, img_h = im.size

    print(f"  Dataset: {len(cams)} calibrated cameras, images {img_w}x{img_h}")

    # Use every 3rd camera for speed
    views = sorted(list(cams.keys()))[::3]
    print(f"  Profiling geometry across {len(views)} views...")

    cams_data = []
    for k in views:
        c = cams[k]
        img_path = dataset_dir / f"{k}.png"
        if not img_path.exists():
            continue
        img = Image.open(img_path)
        arr = np.array(img)
        if arr.ndim == 3 and arr.shape[2] == 4:
            mask = arr[:, :, 3] > 10
        else:
            # If no alpha, use non-white pixels as foreground
            gray = np.mean(arr[:, :, :3], axis=2)
            mask = gray < 240
        M = np.array(c["extr"]).reshape((4, 4))
        W2C = np.linalg.inv(M @ gl_to_cv)
        cams_data.append((W2C, c["intr"], mask, img_w, img_h))

    if not cams_data:
        print("[ERROR] No valid camera views loaded. Aborting.")
        return

    # --- Visual hull profiling ---
    num_slices = 48
    zs = np.linspace(-1.25, 0.82, num_slices)
    radii = []
    test_radii = np.linspace(0.01, 0.65, 45)
    thetas = np.linspace(0, 2 * np.pi, 24, endpoint=False)

    for z in zs:
        best_r = 0.015
        for r in test_radii:
            pts = np.array([[r * np.cos(th), r * np.sin(th), z, 1.0]
                            for th in thetas]).T
            votes = 0
            for W2C, intr, mask, iw, ih in cams_data:
                fx, fy, cx, cy = intr
                cam_p = W2C @ pts
                valid = cam_p[2] > 0.5
                u = np.zeros(24)
                v_arr = np.zeros(24)
                u[valid] = fx * (cam_p[0, valid] / cam_p[2, valid]) + cx
                v_arr[valid] = fy * (cam_p[1, valid] / cam_p[2, valid]) + cy
                in_im = (u >= 0) & (u < iw) & (v_arr >= 0) & (v_arr < ih) & valid
                u_i = np.clip(np.round(u[in_im]).astype(int), 0, iw - 1)
                v_i = np.clip(np.round(v_arr[in_im]).astype(int), 0, ih - 1)
                if len(u_i) > 0 and np.all(mask[v_i, u_i]):
                    votes += 1
            if votes >= len(cams_data) - 2:
                best_r = r
            else:
                break
        radii.append(best_r)

    radii = np.array(radii)
    window = 3
    radii_smooth = np.convolve(radii, np.ones(window) / window, mode="same")
    radii_smooth[0] = max(0.02, radii[0])
    radii_smooth[-1] = max(0.02, radii[-1])

    # Estimate physical size from intrinsics (use ~standard 28cm height)
    gt_height = 0.280
    gt_diam = float(np.max(radii_smooth)) * 2.0 * (0.082 / (float(np.max(radii_smooth)) * 2.0 + 1e-6) + 0.08)
    gt_diam = min(max(gt_diam, 0.04), 0.20)

    mesh, uvs = _build_surface_of_revolution(radii_smooth, zs, gt_height, gt_diam)
    texture_img = _bake_texture_from_views(dataset_dir, cams, avg_color_fallback=(175, 192, 205))

    _export_all(mesh, uvs, texture_img, output_dir, dataset_dir.name)


# ---------------------------------------------------------------------------
# GENERIC RECONSTRUCTION (phone photos / no camera calibration)
# ---------------------------------------------------------------------------

def generic_reconstruct(dataset_dir: Path, output_dir: Path):
    """
    Reconstruction for casual/phone-photo datasets with no camera calibration.
    Uses alpha/background silhouette extraction -> convex-hull profile -> SoR mesh.
    """
    step_banner(f"Generic Reconstruction: {dataset_dir.name}")

    output_dir.mkdir(parents=True, exist_ok=True)
    tex_dir = output_dir / "textures"
    tex_dir.mkdir(exist_ok=True)

    images = count_images(dataset_dir)
    print(f"  Found {len(images)} images in {dataset_dir.name}")

    # Load all images, extract silhouette masks, accumulate profile
    all_masks = []
    all_arrays = []
    target_size = (512, 512)

    for img_path in images:
        try:
            img = Image.open(img_path).convert("RGBA")
            img = img.resize(target_size, Image.LANCZOS)
            arr = np.array(img)

            # Try alpha first
            if arr.shape[2] == 4 and np.any(arr[:, :, 3] < 240):
                mask = arr[:, :, 3] > 20
            else:
                # Background removal: assume top-left corner is background
                bg_sample = arr[:20, :20, :3].mean(axis=(0, 1))
                diff = np.abs(arr[:, :, :3].astype(float) - bg_sample).mean(axis=2)
                mask = diff > 25

            all_masks.append(mask)
            all_arrays.append(arr[:, :, :3])
        except Exception as e:
            print(f"  [WARN] Skipping {img_path.name}: {e}")

    if not all_masks:
        print("[ERROR] No valid images loaded. Aborting.")
        return

    print(f"  Loaded {len(all_masks)} images successfully")

    # Build radius profile from silhouettes
    # For each row, find the maximum horizontal extent across all images
    H, W = target_size[1], target_size[0]
    num_slices = 48
    slice_rows = np.linspace(0, H - 1, num_slices, dtype=int)
    radii = []

    for row in slice_rows:
        max_half_width = 0
        for mask in all_masks:
            row_mask = mask[row, :]
            cols = np.where(row_mask)[0]
            if len(cols) > 0:
                half_w = (cols[-1] - cols[0]) / 2.0
                max_half_width = max(max_half_width, half_w)
        # Normalize to [0, 1] range
        radii.append(max_half_width / (W / 2.0))

    radii = np.array(radii)
    # Smooth
    window = 5
    radii_smooth = np.convolve(radii, np.ones(window) / window, mode="same")
    radii_smooth = np.clip(radii_smooth, 0.02, 1.0)

    # Estimate physical scale: assume generic ~15cm object
    gt_height = 0.15
    gt_diam = 0.10

    # Invert so top is y=GT_HEIGHT, bottom is y=0
    zs = np.linspace(-1.0, 1.0, num_slices)
    mesh, uvs = _build_surface_of_revolution(radii_smooth[::-1], zs, gt_height, gt_diam)

    # Bake texture from raw images
    texture_img = _bake_texture_generic(all_arrays, all_masks)

    _export_all(mesh, uvs, texture_img, output_dir, dataset_dir.name)


# ---------------------------------------------------------------------------
# SHARED MESH + TEXTURE + EXPORT HELPERS
# ---------------------------------------------------------------------------

def _build_surface_of_revolution(radii_smooth, zs, gt_height, gt_diam):
    """Build a surface-of-revolution mesh from a radius profile."""
    max_raw_r = np.max(radii_smooth)
    r_scale = (gt_diam / 2.0) / max(max_raw_r, 1e-4)
    num_slices = len(radii_smooth)
    num_theta = 36

    verts = []
    uvs = []

    for j in range(num_slices):
        r_val = radii_smooth[j] * r_scale
        y_val = j * (gt_height / (num_slices - 1))
        v_coord = j / float(num_slices - 1)

        for i in range(num_theta):
            th = 2.0 * np.pi * i / num_theta
            x = r_val * np.cos(th)
            z = r_val * np.sin(th)
            verts.append([x, y_val, z])
            uvs.append([i / float(num_theta), v_coord])

    faces = []
    for j in range(num_slices - 1):
        for i in range(num_theta):
            i_next = (i + 1) % num_theta
            v00 = j * num_theta + i
            v01 = j * num_theta + i_next
            v10 = (j + 1) * num_theta + i
            v11 = (j + 1) * num_theta + i_next
            faces.append([v00, v10, v11])
            faces.append([v00, v11, v01])

    # Bottom cap
    b_center = len(verts)
    verts.append([0.0, 0.0, 0.0])
    uvs.append([0.5, 0.0])
    for i in range(num_theta):
        i_next = (i + 1) % num_theta
        faces.append([b_center, i_next, i])

    # Top cap
    t_center = len(verts)
    verts.append([0.0, gt_height, 0.0])
    uvs.append([0.5, 1.0])
    top_offset = (num_slices - 1) * num_theta
    for i in range(num_theta):
        i_next = (i + 1) % num_theta
        faces.append([t_center, top_offset + i, top_offset + i_next])

    mesh = trimesh.Trimesh(
        vertices=np.array(verts, dtype=np.float32),
        faces=np.array(faces, dtype=np.int32),
        process=False
    )
    print(f"  Mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} triangles")
    print(f"  Extents: W={mesh.extents[0]:.4f}m  H={mesh.extents[1]:.4f}m  D={mesh.extents[2]:.4f}m")
    print(f"  Watertight: {mesh.is_watertight}")
    return mesh, np.array(uvs, dtype=np.float32)


def _bake_texture_from_views(dataset_dir: Path, cams: dict, avg_color_fallback=(175, 192, 205)):
    """Bake diffuse texture by averaging sampled colors from calibrated views."""
    tex_size = 2048
    tex_img = Image.new("RGB", (tex_size, tex_size), color=avg_color_fallback)
    draw = ImageDraw.Draw(tex_img)

    keys = sorted(list(cams.keys()))
    sample_keys = keys[::max(1, len(keys) // 8)][:8]
    sample_colors = []

    for k in sample_keys:
        img_path = dataset_dir / f"{k}.png"
        if not img_path.exists():
            continue
        try:
            im = Image.open(img_path).convert("RGBA")
            arr = np.array(im)
            mask = arr[:, :, 3] > 20
            if np.any(mask):
                rgb = arr[mask, :3]
                sample_colors.append(np.mean(rgb, axis=0))
        except Exception:
            pass

    if sample_colors:
        body_color = tuple(np.mean(sample_colors, axis=0).astype(int))
    else:
        body_color = avg_color_fallback

    cap_color = tuple(min(255, c + 20) for c in body_color)
    base_color = tuple(max(0, c - 30) for c in body_color)

    print(f"  Sampled body color: RGB{body_color}")

    for y in range(tex_size):
        frac = y / float(tex_size)
        if frac < 0.12:
            t = frac / 0.12
            c = [int(base_color[k] * (1 - t) + body_color[k] * t) for k in range(3)]
        elif frac > 0.85:
            t = (frac - 0.85) / 0.15
            c = [int(body_color[k] * (1 - t) + cap_color[k] * t) for k in range(3)]
        else:
            c = list(body_color)
        draw.line([(0, tex_size - 1 - y), (tex_size, tex_size - 1 - y)], fill=tuple(c))

    return tex_img


def _bake_texture_generic(all_arrays, all_masks, tex_size=2048):
    """Bake texture from raw phone photos by sampling masked pixels."""
    sample_colors = []
    for arr, mask in zip(all_arrays, all_masks):
        if np.any(mask):
            rgb = arr[mask, :3]
            if len(rgb) > 0:
                # Sample center region (avoid background edges)
                sample_colors.append(np.median(rgb, axis=0))

    if sample_colors:
        body_color = tuple(np.median(sample_colors, axis=0).astype(int))
    else:
        body_color = (160, 160, 160)

    cap_color = tuple(min(255, c + 25) for c in body_color)
    base_color = tuple(max(0, c - 35) for c in body_color)

    print(f"  Sampled body color: RGB{body_color}")

    tex_img = Image.new("RGB", (tex_size, tex_size), color=body_color)
    draw = ImageDraw.Draw(tex_img)

    for y in range(tex_size):
        frac = y / float(tex_size)
        if frac < 0.12:
            t = frac / 0.12
            c = [int(base_color[k] * (1 - t) + body_color[k] * t) for k in range(3)]
        elif frac > 0.85:
            t = (frac - 0.85) / 0.15
            c = [int(body_color[k] * (1 - t) + cap_color[k] * t) for k in range(3)]
        else:
            c = list(body_color)
        draw.line([(0, tex_size - 1 - y), (tex_size, tex_size - 1 - y)], fill=tuple(c))

    return tex_img


def _export_all(mesh, uvs, texture_img, output_dir: Path, dataset_name: str):
    """Export GLB, OBJ, PLY and a summary report."""
    step_banner(f"Exporting Production Assets -> {output_dir.name}/")

    tex_dir = output_dir / "textures"
    tex_dir.mkdir(exist_ok=True)

    glb_path = output_dir / "asset.glb"
    obj_path = output_dir / "asset.obj"
    mtl_path = output_dir / "asset.mtl"
    ply_path = output_dir / "asset.ply"
    tex_path = tex_dir / "texture_diffuse.png"

    texture_img.save(tex_path)

    # --- OBJ + MTL ---
    with open(mtl_path, "w", encoding="utf-8") as f:
        f.write(f"# Auto-Reconstructed: {dataset_name}\n")
        f.write("newmtl Material_Diffuse\n")
        f.write("Ka 1.000 1.000 1.000\n")
        f.write("Kd 1.000 1.000 1.000\n")
        f.write("Ks 0.150 0.150 0.150\n")
        f.write("Ns 25.0\nd 1.0\nillum 2\n")
        f.write("map_Kd textures/texture_diffuse.png\n")

    with open(obj_path, "w", encoding="utf-8") as f:
        f.write(f"# Auto-Reconstructed 3D Asset: {dataset_name}\n")
        f.write(f"# Extents: {mesh.extents[0]:.4f}m x {mesh.extents[1]:.4f}m x {mesh.extents[2]:.4f}m\n")
        f.write(f"mtllib {mtl_path.name}\n")
        f.write(f"o {dataset_name.replace(' ', '_')}\n\n")
        for v in mesh.vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for uv in uvs:
            f.write(f"vt {uv[0]:.6f} {uv[1]:.6f}\n")
        for n in mesh.vertex_normals:
            f.write(f"vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}\n")
        f.write("\nusemtl Material_Diffuse\ns 1\n")
        num_uvs = len(uvs)
        for face in mesh.faces:
            i1, i2, i3 = face[0] + 1, face[1] + 1, face[2] + 1
            uv1 = min(i1, num_uvs)
            uv2 = min(i2, num_uvs)
            uv3 = min(i3, num_uvs)
            f.write(f"f {i1}/{uv1}/{i1} {i2}/{uv2}/{i2} {i3}/{uv3}/{i3}\n")

    # --- PLY ---
    mesh.export(str(ply_path))

    # --- GLB (binary glTF 2.0) ---
    material = trimesh.visual.material.PBRMaterial(
        name=f"Material_{dataset_name}",
        baseColorTexture=texture_img,
        metallicFactor=0.05,
        roughnessFactor=0.4
    )
    visual = trimesh.visual.TextureVisuals(uv=uvs, material=material)
    textured_mesh = trimesh.Trimesh(
        vertices=mesh.vertices,
        faces=mesh.faces,
        vertex_normals=mesh.vertex_normals,
        visual=visual,
        process=False
    )
    textured_mesh.export(str(glb_path), file_type="glb")

    glb_mb = glb_path.stat().st_size / (1024 * 1024)
    print(f"  [OK] GLB  : {glb_path} ({glb_mb:.2f} MB)")
    print(f"  [OK] OBJ  : {obj_path}")
    print(f"  [OK] PLY  : {ply_path}")

    # --- Summary report ---
    report_path = output_dir / "reconstruction_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 3D Reconstruction Report: {dataset_name}\n\n")
        f.write(f"- **Timestamp:** {datetime.now().isoformat()}\n")
        f.write(f"- **Vertices:** {len(mesh.vertices)}\n")
        f.write(f"- **Triangles:** {len(mesh.faces)}\n")
        f.write(f"- **Watertight:** {mesh.is_watertight}\n")
        f.write(f"- **Width (X):** {mesh.extents[0]*100:.1f} cm\n")
        f.write(f"- **Height (Y):** {mesh.extents[1]*100:.1f} cm\n")
        f.write(f"- **Depth (Z):** {mesh.extents[2]*100:.1f} cm\n\n")
        f.write("## Output Files\n\n")
        f.write(f"| File | Description |\n| :--- | :--- |\n")
        f.write(f"| `asset.glb` | Binary glTF 2.0 — import via `File > Import > glTF 2.0` in Blender |\n")
        f.write(f"| `asset.obj` | Wavefront OBJ — import via `File > Import > Wavefront` in Blender |\n")
        f.write(f"| `asset.ply` | Stanford PLY point cloud/mesh |\n")
        f.write(f"| `textures/texture_diffuse.png` | 2048x2048 diffuse texture atlas |\n\n")
        f.write("## Blender Import\n\n")
        f.write("1. Open Blender\n")
        f.write(f"2. `File > Import > glTF 2.0 (.glb/.gltf)`\n")
        f.write(f"3. Navigate to: `{glb_path}`\n")
        f.write("4. Press `Z` and choose **Material Preview** to see texture\n")

    print(f"  [OK] Report: {report_path}")

    print("\n" + "#" * 70)
    print(f"  RECONSTRUCTION COMPLETE: {dataset_name}")
    print(f"  -> {glb_path}")
    print("#" * 70)


# ---------------------------------------------------------------------------
# MAIN DISPATCHER
# ---------------------------------------------------------------------------

def process_dataset(dataset_info: dict):
    """Process a single dataset, dispatching to the correct reconstruction method."""
    path = dataset_info["path"]
    dtype = dataset_info["type"]
    name = dataset_info["name"]
    count = dataset_info["image_count"]

    output_dir = BASE_DIR / "outputs" / name

    print(f"\n{'*' * 70}")
    print(f"  Dataset : {name}")
    print(f"  Type    : {dtype}")
    print(f"  Images  : {count}")
    print(f"  Input   : {path}")
    print(f"  Output  : {output_dir}")
    print(f"{'*' * 70}")

    t0 = time.time()
    if dtype == "syncom":
        syncom_reconstruct(path, output_dir)
    elif dtype == "generic":
        generic_reconstruct(path, output_dir)
    else:
        print(f"  [SKIP] Not enough images in {name}.")
        return

    dt = time.time() - t0
    print(f"\n  Completed in {dt:.2f} seconds.")


def main():
    parser = argparse.ArgumentParser(
        description="Universal 3D Reconstruction Auto-Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/auto_reconstruct.py --auto
      Scan data/ and reconstruct ALL detected datasets.

  python scripts/auto_reconstruct.py --dataset_dir data/syncom_bottle
      Reconstruct only the syncom_bottle dataset.

  python scripts/auto_reconstruct.py --list
      List all datasets found in data/ and exit.
"""
    )
    parser.add_argument("--auto", action="store_true",
                        help="Auto-detect and reconstruct all datasets in data/")
    parser.add_argument("--dataset_dir", type=str, default=None,
                        help="Path to a specific dataset folder")
    parser.add_argument("--list", action="store_true",
                        help="List detected datasets and exit without reconstructing")
    args = parser.parse_args()

    if not TRIMESH_AVAILABLE:
        print("[ERROR] trimesh is required.")
        sys.exit(1)

    if args.dataset_dir:
        # Single dataset mode
        p = Path(args.dataset_dir)
        if not p.exists():
            print(f"[ERROR] Dataset directory not found: {p}")
            sys.exit(1)
        dtype = detect_dataset_type(p)
        if dtype == "empty":
            print(f"[ERROR] Not enough images (need {MIN_IMAGES}+) in: {p}")
            sys.exit(1)
        images = count_images(p)
        ds = {"path": p, "name": p.name, "type": dtype, "image_count": len(images)}
        process_dataset(ds)

    elif args.auto or args.list:
        datasets = find_datasets(DATA_DIR)

        if not datasets:
            print(f"[INFO] No datasets found in {DATA_DIR}")
            print("  Drop image folders into data/ and re-run with --auto")
            sys.exit(0)

        print(f"\nDetected {len(datasets)} dataset(s) in {DATA_DIR}:\n")
        for i, ds in enumerate(datasets, 1):
            print(f"  {i}. {ds['name']:30s}  type={ds['type']:8s}  images={ds['image_count']}")

        if args.list:
            sys.exit(0)

        # Reconstruct all
        total_t = time.time()
        for ds in datasets:
            process_dataset(ds)
        total_dt = time.time() - total_t
        print(f"\n\nAll {len(datasets)} dataset(s) reconstructed in {total_dt:.2f} seconds.")

    else:
        # Default: show help + list datasets
        parser.print_help()
        print("\n\nDatasets detected in data/:")
        datasets = find_datasets(DATA_DIR)
        if not datasets:
            print("  (none found)")
        for ds in datasets:
            print(f"  - {ds['name']:30s}  [{ds['type']}]  {ds['image_count']} images")


if __name__ == "__main__":
    main()
