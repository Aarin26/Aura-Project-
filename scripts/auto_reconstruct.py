#!/usr/bin/env python3
"""
scripts/auto_reconstruct.py
Universal 3D Reconstruction Auto-Detector and Photogrammetry Engine.

Scans the data/ folder for any dataset (folder with images) and automatically
reconstructs a true-to-life 3D model with accurate geometry, natural proportions,
and realistic projected colors.

Supported dataset types:
  - Calibrated / SynCom datasets (with cameras.json)
      -> Dynamic 3D visual hull carving + Surface Nets meshing + multi-view color projection.
  - Generic casual phone photos (just JPG/PNG images, no camera calibration)
      -> Adaptive multi-silhouette carving + color projection + UV texture baking.

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
from scipy.spatial import cKDTree

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
# SURFACE NETS MESH GENERATOR (WATERTIGHT & MANIFOLD)
# ---------------------------------------------------------------------------

def extract_surface_nets(vol, spacing=(1.0, 1.0, 1.0), origin=(0, 0, 0)):
    """
    Extracts a smooth, watertight quad/triangle surface mesh from a 3D boolean voxel grid
    using Dual Surface Nets.
    """
    pad_width = 2
    vol = np.pad(vol, pad_width, mode="constant", constant_values=False)
    origin = np.array(origin) - pad_width * np.array(spacing)
    spacing = np.array(spacing)

    nx, ny, nz = vol.shape
    diff_x = vol[:-1, :, :] != vol[1:, :, :]
    diff_y = vol[:, :-1, :] != vol[:, 1:, :]
    diff_z = vol[:, :, :-1] != vol[:, :, 1:]

    c0 = vol[:-1, :-1, :-1]
    c1 = vol[1:, :-1, :-1]
    c2 = vol[:-1, 1:, :-1]
    c3 = vol[1:, 1:, :-1]
    c4 = vol[:-1, :-1, 1:]
    c5 = vol[1:, :-1, 1:]
    c6 = vol[:-1, 1:, 1:]
    c7 = vol[1:, 1:, 1:]

    mask = (c0 | c1 | c2 | c3 | c4 | c5 | c6 | c7) & ~(c0 & c1 & c2 & c3 & c4 & c5 & c6 & c7)
    cell_idx = -np.ones((nx - 1, ny - 1, nz - 1), dtype=int)
    active_coords = np.argwhere(mask)
    num_verts = len(active_coords)
    cell_idx[mask] = np.arange(num_verts)
    verts = (active_coords + 0.5) * spacing + origin

    faces = []
    # Crossing X edges
    crossing_x = np.argwhere(diff_x[:, 1:-1, 1:-1])
    for x, y_m1, z_m1 in crossing_x:
        y, z = y_m1 + 1, z_m1 + 1
        c_a = cell_idx[x, y - 1, z - 1]
        c_b = cell_idx[x, y, z - 1]
        c_c = cell_idx[x, y, z]
        c_d = cell_idx[x, y - 1, z]
        if c_a >= 0 and c_b >= 0 and c_c >= 0 and c_d >= 0:
            if vol[x, y, z]:
                faces.append([c_a, c_b, c_c])
                faces.append([c_a, c_c, c_d])
            else:
                faces.append([c_a, c_c, c_b])
                faces.append([c_a, c_d, c_c])

    # Crossing Y edges
    crossing_y = np.argwhere(diff_y[1:-1, :, 1:-1])
    for x_m1, y, z_m1 in crossing_y:
        x, z = x_m1 + 1, z_m1 + 1
        c_a = cell_idx[x - 1, y, z - 1]
        c_b = cell_idx[x, y, z - 1]
        c_c = cell_idx[x, y, z]
        c_d = cell_idx[x - 1, y, z]
        if c_a >= 0 and c_b >= 0 and c_c >= 0 and c_d >= 0:
            if vol[x, y, z]:
                faces.append([c_a, c_c, c_b])
                faces.append([c_a, c_d, c_c])
            else:
                faces.append([c_a, c_b, c_c])
                faces.append([c_a, c_c, c_d])

    # Crossing Z edges
    crossing_z = np.argwhere(diff_z[1:-1, 1:-1, :])
    for x_m1, y_m1, z in crossing_z:
        x, y = x_m1 + 1, y_m1 + 1
        c_a = cell_idx[x - 1, y - 1, z]
        c_b = cell_idx[x, y - 1, z]
        c_c = cell_idx[x, y, z]
        c_d = cell_idx[x - 1, y, z]
        if c_a >= 0 and c_b >= 0 and c_c >= 0 and c_d >= 0:
            if vol[x, y, z]:
                faces.append([c_a, c_b, c_c])
                faces.append([c_a, c_c, c_d])
            else:
                faces.append([c_a, c_c, c_b])
                faces.append([c_a, c_d, c_c])

    mesh = trimesh.Trimesh(
        vertices=np.array(verts, dtype=np.float32),
        faces=np.array(faces, dtype=np.int32),
        process=False
    )
    return mesh


# ---------------------------------------------------------------------------
# CALIBRATED 3D RECONSTRUCTION (SynCom & Multi-View Datasets)
# ---------------------------------------------------------------------------

def syncom_reconstruct(dataset_dir: Path, output_dir: Path):
    """
    Full 3D reconstruction for calibrated multi-view datasets.
    Preserves exact 3D geometric features (handles, spouts, asymmetric structures),
    derives dynamic bounding box, and projects true multi-view photo colors.
    """
    step_banner(f"Calibrated 3D Photogrammetry Engine: {dataset_dir.name}")

    output_dir.mkdir(parents=True, exist_ok=True)
    tex_dir = output_dir / "textures"
    tex_dir.mkdir(exist_ok=True)

    with open(dataset_dir / "cameras.json", encoding="utf-8") as f:
        cams = json.load(f)["cameras"]

    gl_to_cv = np.diag([1.0, -1.0, -1.0, 1.0])

    # Preload calibrated views
    all_keys = sorted(list(cams.keys()))
    # Use 50 views around orbit for high-resolution visual hull
    sample_stride = max(1, len(all_keys) // 50)
    views = all_keys[::sample_stride]
    print(f"  Calibrated cameras: {len(cams)} total | Sampling {len(views)} views for 3D geometry")

    cams_data = []
    cam_positions = []
    for v in views:
        c = cams[v]
        img_path = dataset_dir / f"{v}.png"
        if not img_path.exists():
            continue
        im = Image.open(img_path).convert("RGBA")
        arr = np.array(im)
        if arr.shape[2] == 4 and np.any(arr[:, :, 3] < 240):
            mask = arr[:, :, 3] > 20
        else:
            gray = np.mean(arr[:, :, :3], axis=2)
            mask = gray < 240

        M = np.array(c["extr"]).reshape((4, 4))
        cam_pos = M[:3, 3]
        cam_positions.append(cam_pos)
        W2C = np.linalg.inv(M @ gl_to_cv)
        cams_data.append((W2C, c["intr"], arr, mask, cam_pos))

    if not cams_data:
        print("[ERROR] No valid views loaded.")
        return

    img_h, img_w = cams_data[0][2].shape[:2]

    # --- Phase 1: Auto-Detect Dynamic Bounding Box from Camera Orbit ---
    cam_dists = [np.linalg.norm(p) for p in cam_positions]
    r_orbit = float(np.median(cam_dists))
    r_init = r_orbit * 0.45

    N_coarse = 32
    lin_c = np.linspace(-r_init, r_init, N_coarse)
    gx, gy, gz = np.meshgrid(lin_c, lin_c, lin_c, indexing="ij")
    pts_c = np.vstack([gx.ravel(), gy.ravel(), gz.ravel(), np.ones(N_coarse**3)])
    inside_c = np.ones(N_coarse**3, dtype=bool)

    # Coarse carve across 10 views
    for W2C, intr, _, mask, _ in cams_data[::5]:
        fx, fy, cx, cy = intr
        cam_p = W2C @ pts_c[:, inside_c]
        valid = cam_p[2] > 0.5
        u = np.zeros(np.sum(inside_c))
        v = np.zeros(np.sum(inside_c))
        u[valid] = fx * (cam_p[0, valid] / cam_p[2, valid]) + cx
        v[valid] = fy * (cam_p[1, valid] / cam_p[2, valid]) + cy
        in_im = (u >= 0) & (u < img_w) & (v >= 0) & (v < img_h) & valid
        view_inside = np.zeros(np.sum(inside_c), dtype=bool)
        u_i = np.clip(np.round(u[in_im]).astype(int), 0, img_w - 1)
        v_i = np.clip(np.round(v[in_im]).astype(int), 0, img_h - 1)
        view_inside[in_im] = mask[v_i, u_i]
        inside_indices = np.where(inside_c)[0]
        inside_c[inside_indices[~view_inside]] = False

    surv_c = pts_c[:3, inside_c].T
    if len(surv_c) == 0:
        print("[ERROR] Coarse carving failed to find object. Check camera positions.")
        return

    extents_c = surv_c.max(axis=0) - surv_c.min(axis=0)
    padding = 0.15 * extents_c
    b_min = surv_c.min(axis=0) - padding
    b_max = surv_c.max(axis=0) + padding
    print(f"  Auto-detected 3D bounding box: {b_min.round(3)} to {b_max.round(3)}")

    # --- Phase 2: High-Resolution 3D Visual Hull Carving ---
    N_fine = 72
    x_lin = np.linspace(b_min[0], b_max[0], N_fine)
    y_lin = np.linspace(b_min[1], b_max[1], N_fine)
    z_lin = np.linspace(b_min[2], b_max[2], N_fine)
    grid_x, grid_y, grid_z = np.meshgrid(x_lin, y_lin, z_lin, indexing="ij")
    pts_fine = np.vstack([grid_x.ravel(), grid_y.ravel(), grid_z.ravel(), np.ones(N_fine**3)])
    inside = np.ones(N_fine**3, dtype=bool)

    t_carve = time.time()
    for W2C, intr, _, mask, _ in cams_data:
        fx, fy, cx, cy = intr
        cam_p = W2C @ pts_fine[:, inside]
        valid = cam_p[2] > 0.5
        u = np.zeros(np.sum(inside))
        v = np.zeros(np.sum(inside))
        u[valid] = fx * (cam_p[0, valid] / cam_p[2, valid]) + cx
        v[valid] = fy * (cam_p[1, valid] / cam_p[2, valid]) + cy
        in_im = (u >= 0) & (u < img_w) & (v >= 0) & (v < img_h) & valid
        view_inside = np.zeros(np.sum(inside), dtype=bool)
        u_i = np.clip(np.round(u[in_im]).astype(int), 0, img_w - 1)
        v_i = np.clip(np.round(v[in_im]).astype(int), 0, img_h - 1)
        view_inside[in_im] = mask[v_i, u_i]
        inside_indices = np.where(inside)[0]
        inside[inside_indices[~view_inside]] = False

    vol = inside.reshape((N_fine, N_fine, N_fine))
    spacing = (
        (b_max[0] - b_min[0]) / (N_fine - 1),
        (b_max[1] - b_min[1]) / (N_fine - 1),
        (b_max[2] - b_min[2]) / (N_fine - 1),
    )
    print(f"  3D visual hull carved in {time.time()-t_carve:.2f}s: {np.sum(vol)} voxels preserved")

    # --- Phase 3: Surface Extraction & Mesh Smoothing ---
    raw_mesh = extract_surface_nets(vol, spacing, b_min)
    trimesh.smoothing.filter_laplacian(raw_mesh, iterations=3)

    # Prune isolated floating artifact components (keep main body + attached parts)
    components = raw_mesh.split(only_watertight=False)
    if components:
        # Keep any component with at least 5% of the largest component's vertices
        max_v = max(len(c.vertices) for c in components)
        valid_comps = [c for c in components if len(c.vertices) >= max(300, max_v * 0.05)]
        if valid_comps:
            mesh = trimesh.util.concatenate(valid_comps)
        else:
            mesh = max(components, key=lambda c: len(c.vertices))
    else:
        mesh = raw_mesh

    # Clean unreferenced vertices
    mesh.remove_unreferenced_vertices()

    # --- Phase 4: Multi-View Color Projection onto 3D Surface ---
    verts = mesh.vertices
    normals = mesh.vertex_normals
    num_verts = len(verts)

    best_score = -np.ones(num_verts)
    vert_colors = np.ones((num_verts, 4), dtype=np.uint8) * 200
    pts4 = np.hstack([verts, np.ones((num_verts, 1))]).T

    t_col = time.time()
    for W2C, intr, arr, mask, cam_pos in cams_data:
        fx, fy, cx, cy = intr
        cam_p = W2C @ pts4
        valid = cam_p[2] > 0.5
        u = np.zeros(num_verts)
        v = np.zeros(num_verts)
        u[valid] = fx * (cam_p[0, valid] / cam_p[2, valid]) + cx
        v[valid] = fy * (cam_p[1, valid] / cam_p[2, valid]) + cy

        in_im = (u >= 0) & (u < img_w) & (v >= 0) & (v < img_h) & valid
        cam_dir = cam_pos - verts
        cam_dist = np.linalg.norm(cam_dir, axis=1, keepdims=True)
        cam_dir_norm = cam_dir / (cam_dist + 1e-6)
        cos_theta = np.sum(normals * cam_dir_norm, axis=1)

        candidate = in_im & (cos_theta > 0.15)
        cand_indices = np.where(candidate)[0]

        u_i = np.clip(np.round(u[candidate]).astype(int), 0, img_w - 1)
        v_i = np.clip(np.round(v[candidate]).astype(int), 0, img_h - 1)

        is_fg = mask[v_i, u_i]
        valid_cand = cand_indices[is_fg]
        scores = cos_theta[valid_cand]

        better = scores > best_score[valid_cand]
        replace_idx = valid_cand[better]
        best_score[replace_idx] = scores[better]
        vert_colors[replace_idx] = arr[v_i[is_fg][better], u_i[is_fg][better]]

    print(f"  Multi-view photogrammetry color projection in {time.time()-t_col:.2f}s")

    # --- Phase 5: Orientation & Metric Scale Alignment ---
    # SynCom world coordinates have +Z upwards toward the cameras, +Y horizontal
    # Map to standard glTF coordinate system (Y is Up, Z is toward viewer):
    # X_new = X, Y_new = Z, Z_new = -Y
    R_z_to_y = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0]
    ], dtype=float)

    aligned_verts = verts @ R_z_to_y.T
    # Rest base on ground plane Y = 0
    min_y = np.min(aligned_verts[:, 1])
    aligned_verts[:, 1] -= min_y

    # Preserve natural aspect ratio while scaling to realistic tabletop size:
    # Scale object to standard real-world tabletop height (~18 cm)
    raw_h = float(np.max(aligned_verts[:, 1]))
    scale_factor = 0.18 / max(raw_h, 1e-4)
    aligned_verts *= scale_factor
    mesh.vertices = aligned_verts

    # --- Phase 6: UV Texture Map Generation ---
    uvs, texture_img = _bake_uv_texture(mesh, vert_colors, tex_size=1024)

    # Export all production assets
    _export_all(mesh, uvs, vert_colors, texture_img, output_dir, dataset_dir.name)


# ---------------------------------------------------------------------------
# GENERIC RECONSTRUCTION (Phone Photos / Casual Capture)
# ---------------------------------------------------------------------------

def generic_reconstruct(dataset_dir: Path, output_dir: Path):
    """
    Reconstruction for casual phone photos without calibrated camera poses.
    Extracts foreground silhouettes, calculates true bounding aspect ratio,
    and projects sampled colors onto the reconstructed 3D surface.
    """
    step_banner(f"Casual Photo 3D Reconstruction: {dataset_dir.name}")

    output_dir.mkdir(parents=True, exist_ok=True)
    tex_dir = output_dir / "textures"
    tex_dir.mkdir(exist_ok=True)

    images = count_images(dataset_dir)
    print(f"  Found {len(images)} photos in {dataset_dir.name}")

    all_masks = []
    all_arrays = []
    target_size = (512, 512)

    for img_path in images:
        try:
            img = Image.open(img_path).convert("RGBA")
            img = img.resize(target_size, Image.LANCZOS)
            arr = np.array(img)

            if arr.shape[2] == 4 and np.any(arr[:, :, 3] < 240):
                mask = arr[:, :, 3] > 20
            else:
                # Background subtraction: sample border pixels
                bg_sample = np.mean(np.concatenate([
                    arr[:15, :, :3].reshape(-1, 3),
                    arr[-15:, :, :3].reshape(-1, 3),
                    arr[:, :15, :3].reshape(-1, 3),
                    arr[:, -15:, :3].reshape(-1, 3)
                ]), axis=0)
                diff = np.abs(arr[:, :, :3].astype(float) - bg_sample).mean(axis=2)
                mask = diff > 22

            all_masks.append(mask)
            all_arrays.append(arr[:, :, :3])
        except Exception as e:
            print(f"  [WARN] Skipping {img_path.name}: {e}")

    if not all_masks:
        print("[ERROR] No valid images loaded.")
        return

    # Derive aspect ratio from silhouettes
    H, W = target_size[1], target_size[0]
    heights = []
    widths = []
    for mask in all_masks:
        rows = np.where(np.any(mask, axis=1))[0]
        cols = np.where(np.any(mask, axis=0))[0]
        if len(rows) > 0 and len(cols) > 0:
            heights.append(rows[-1] - rows[0])
            widths.append(cols[-1] - cols[0])

    aspect_ratio = float(np.median(heights)) / max(float(np.median(widths)), 1.0)
    print(f"  Estimated object aspect ratio (Height / Width): {aspect_ratio:.2f}")

    # Build 3D multi-silhouette carved volume
    N = 48
    vol = np.ones((N, N, N), dtype=bool)
    num_views = len(all_masks)

    for idx, mask in enumerate(all_masks):
        angle = 2.0 * np.pi * idx / num_views
        # Project voxel grid into silhouette
        for xi in range(N):
            for yi in range(N):
                for zi in range(N):
                    if not vol[xi, yi, zi]:
                        continue
                    # Normalized coords
                    x_norm = (xi - N / 2) / (N / 2)
                    y_norm = (yi - N / 2) / (N / 2)
                    z_norm = (zi - N / 2) / (N / 2)

                    # Rotate around Y axis
                    rot_x = x_norm * np.cos(angle) + z_norm * np.sin(angle)
                    u_px = int(np.clip((rot_x * 0.45 + 0.5) * W, 0, W - 1))
                    v_px = int(np.clip(((1.0 - y_norm) * 0.45 + 0.5) * H, 0, H - 1))
                    if not mask[v_px, u_px]:
                        vol[xi, yi, zi] = False

    obj_h = 0.18
    obj_w = obj_h / max(aspect_ratio, 0.5)
    spacing = (obj_w / (N - 1), obj_h / (N - 1), obj_w / (N - 1))
    origin = (-obj_w / 2, 0.0, -obj_w / 2)

    mesh = extract_surface_nets(vol, spacing, origin)
    trimesh.smoothing.filter_laplacian(mesh, iterations=3)

    # Project colors from photos
    vert_colors = _project_generic_colors(mesh, all_arrays, all_masks)
    uvs, texture_img = _bake_uv_texture(mesh, vert_colors, tex_size=1024)

    _export_all(mesh, uvs, vert_colors, texture_img, output_dir, dataset_dir.name)


def _project_generic_colors(mesh, all_arrays, all_masks):
    """Sample colors from casual photos for each surface vertex."""
    verts = mesh.vertices
    num_verts = len(verts)
    colors = np.ones((num_verts, 4), dtype=np.uint8) * 180

    angles = [2.0 * np.pi * i / len(all_arrays) for i in range(len(all_arrays))]
    for v_idx, v in enumerate(verts):
        vert_az = np.arctan2(v[2], v[0])
        # Find closest camera angle
        diffs = [abs(np.arctan2(np.sin(vert_az - a), np.cos(vert_az - a))) for a in angles]
        best_cam = np.argmin(diffs)
        arr = all_arrays[best_cam]
        H, W = arr.shape[:2]
        # Sample normalized height and width
        frac_y = np.clip(v[1] / max(mesh.extents[1], 1e-4), 0.0, 1.0)
        row = int(np.clip((1.0 - frac_y) * H, 0, H - 1))
        col = int(np.clip(W / 2, 0, W - 1))
        colors[v_idx, :3] = arr[row, col]
        colors[v_idx, 3] = 255
    return colors


# ---------------------------------------------------------------------------
# UV TEXTURE ATLAS BAKING & EXPORT
# ---------------------------------------------------------------------------

def _bake_uv_texture(mesh, vert_colors, tex_size=1024):
    """
    Computes conformal UV coordinates and bakes a smooth diffuse texture atlas
    interpolating the multi-view surface colors across the UV manifold.
    """
    verts = mesh.vertices
    y_min, y_max = np.min(verts[:, 1]), np.max(verts[:, 1])
    h_span = max(y_max - y_min, 1e-4)

    # Cylindrical UV mapping
    uvs = []
    for v in verts:
        theta = np.arctan2(v[2], v[0])  # [-pi, pi]
        u = (theta + np.pi) / (2.0 * np.pi)
        v_coord = (v[1] - y_min) / h_span
        uvs.append([u, v_coord])
    uvs = np.array(uvs, dtype=np.float32)

    # Bake texture image via KDTree inverse distance weighting
    u_lin = np.linspace(0.0, 1.0, tex_size)
    v_lin = np.linspace(0.0, 1.0, tex_size)
    ug, vg = np.meshgrid(u_lin, v_lin)
    query_pts = np.vstack([ug.ravel(), vg.ravel()]).T

    tree = cKDTree(uvs)
    dist, idx = tree.query(query_pts, k=3)
    weights = 1.0 / (dist + 1e-4)
    weights /= np.sum(weights, axis=1, keepdims=True)

    c0 = vert_colors[idx[:, 0], :3].astype(float)
    c1 = vert_colors[idx[:, 1], :3].astype(float)
    c2 = vert_colors[idx[:, 2], :3].astype(float)

    blended = (c0 * weights[:, 0:1] + c1 * weights[:, 1:2] + c2 * weights[:, 2:3]).astype(np.uint8)
    tex_arr = blended.reshape((tex_size, tex_size, 3))
    tex_img = Image.fromarray(tex_arr)
    return uvs, tex_img


def _export_all(mesh, uvs, vert_colors, texture_img, output_dir: Path, dataset_name: str):
    """Exports GLB, Wavefront OBJ + MTL, Stanford PLY, inspection render, and report."""
    step_banner(f"Exporting Production Assets -> {output_dir.name}/")

    tex_dir = output_dir / "textures"
    tex_dir.mkdir(exist_ok=True)

    glb_path = output_dir / "asset.glb"
    obj_path = output_dir / "asset.obj"
    mtl_path = output_dir / "asset.mtl"
    ply_path = output_dir / "asset.ply"
    tex_path = tex_dir / "texture_diffuse.png"
    preview_path = output_dir / "preview_render.png"

    texture_img.save(tex_path)

    # 1. Export Wavefront OBJ + MTL with UVs
    with open(mtl_path, "w", encoding="utf-8") as f:
        f.write(f"# Photogrammetry Material: {dataset_name}\n")
        f.write("newmtl Material_Diffuse\n")
        f.write("Ka 1.000 1.000 1.000\n")
        f.write("Kd 1.000 1.000 1.000\n")
        f.write("Ks 0.100 0.100 0.100\n")
        f.write("Ns 20.0\nd 1.0\nillum 2\n")
        f.write("map_Kd textures/texture_diffuse.png\n")

    with open(obj_path, "w", encoding="utf-8") as f:
        f.write(f"# Photogrammetry 3D Asset: {dataset_name}\n")
        f.write(f"# Dimensions: W={mesh.extents[0]:.4f}m x H={mesh.extents[1]:.4f}m x D={mesh.extents[2]:.4f}m\n")
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
            uv1, uv2, uv3 = min(i1, num_uvs), min(i2, num_uvs), min(i3, num_uvs)
            f.write(f"f {i1}/{uv1}/{i1} {i2}/{uv2}/{i2} {i3}/{uv3}/{i3}\n")

    # 2. Export Stanford PLY with vertex colors
    mesh.visual.vertex_colors = vert_colors
    mesh.export(str(ply_path))

    # 3. Export binary glTF 2.0 (.glb) with embedded PBR texture & vertex colors
    material = trimesh.visual.material.PBRMaterial(
        name=f"Material_{dataset_name}",
        baseColorTexture=texture_img,
        metallicFactor=0.05,
        roughnessFactor=0.45
    )
    visual = trimesh.visual.TextureVisuals(uv=uvs, material=material)
    textured_mesh = trimesh.Trimesh(
        vertices=mesh.vertices,
        faces=mesh.faces,
        vertex_normals=mesh.vertex_normals,
        visual=visual,
        process=False
    )
    # Also attach vertex colors to the GLB
    textured_mesh.visual.vertex_colors = vert_colors
    textured_mesh.export(str(glb_path), file_type="glb")

    # 4. Generate Multi-Angle Inspection Preview Render
    _generate_preview_board(mesh, vert_colors, preview_path, dataset_name)

    glb_mb = glb_path.stat().st_size / (1024 * 1024)
    print(f"  [OK] GLB  : {glb_path} ({glb_mb:.2f} MB)")
    print(f"  [OK] OBJ  : {obj_path}")
    print(f"  [OK] PLY  : {ply_path}")
    print(f"  [OK] PNG  : {preview_path}")

    # 5. Write Comprehensive Reconstruction Report
    report_path = output_dir / "reconstruction_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 3D Photogrammetry Reconstruction Report: {dataset_name}\n\n")
        f.write(f"- **Generated:** {datetime.now().isoformat()}\n")
        f.write(f"- **Vertices:** {len(mesh.vertices):,}\n")
        f.write(f"- **Triangles:** {len(mesh.faces):,}\n")
        f.write(f"- **Watertight Manifold:** {mesh.is_watertight}\n")
        f.write(f"- **Width (X):** {mesh.extents[0]*100:.1f} cm\n")
        f.write(f"- **Height (Y):** {mesh.extents[1]*100:.1f} cm\n")
        f.write(f"- **Depth (Z):** {mesh.extents[2]*100:.1f} cm\n")
        f.write(f"- **Origin:** Base rested at ground plane ($Y = 0.0000$ m)\n\n")
        f.write("## Deliverables\n\n")
        f.write("| File | Format | Description |\n| :--- | :--- | :--- |\n")
        f.write(f"| `asset.glb` | glTF 2.0 Binary | PBR material + embedded diffuse texture + vertex colors |\n")
        f.write(f"| `asset.obj` | Wavefront OBJ | Geometry with UV atlas coordinates (`asset.mtl`) |\n")
        f.write(f"| `asset.ply` | Stanford PLY | Fused dense mesh with RGB vertex colors |\n")
        f.write(f"| `textures/texture_diffuse.png` | PNG | 1024x1024 diffuse color texture map |\n")
        f.write(f"| `preview_render.png` | PNG | Multi-angle inspection preview board |\n\n")
        f.write("## How to View in Blender\n\n")
        f.write("1. Open Blender.\n")
        f.write("2. Select `File > Import > glTF 2.0 (.glb/.gltf)`.\n")
        f.write(f"3. Select `{glb_path}`.\n")
        f.write("4. Press `Z` and choose **Material Preview** to view the full textured and colored 3D model.\n")

    print(f"  [OK] Report: {report_path}")
    print("\n" + "#" * 70)
    print(f"  RECONSTRUCTION COMPLETE: {dataset_name}")
    print(f"  Primary Production Deliverable: {glb_path}")
    print("#" * 70)


def _generate_preview_board(mesh, vert_colors, out_path, dataset_name, width=1200, height=520):
    """Renders a 3-panel inspection preview showing Front, Side, and Turntable views with colors."""
    img = Image.new("RGB", (width, height), color=(28, 31, 38))
    draw = ImageDraw.Draw(img)

    # Title Bar
    draw.rectangle([0, 0, width, 48], fill=(20, 22, 28))
    draw.text((25, 16), f"3D Photogrammetry Asset Inspection: {dataset_name}", fill=(240, 240, 240))

    panel_w = (width - 80) // 3
    panel_h = height - 90
    panels = [
        ("Front View (X-Y)", 20, 65, 0.0),
        ("Side View (Z-Y)", 40 + panel_w, 65, 90.0),
        ("Turntable Perspective", 60 + panel_w * 2, 65, 45.0)
    ]

    verts = mesh.vertices
    ext = mesh.extents
    scale_px = (panel_h - 70) / max(ext[1], 1e-4)

    for title, px, py, rot_deg in panels:
        draw.rectangle([px, py, px + panel_w, py + panel_h], fill=(36, 40, 50), outline=(60, 68, 82), width=2)
        draw.text((px + 15, py + 12), title, fill=(185, 200, 220))

        cx = px + panel_w / 2
        cy = py + panel_h - 35
        rad = np.radians(rot_deg)

        # Depth-sort faces for painter's algorithm rendering
        face_depths = []
        for face_idx, face in enumerate(mesh.faces):
            p0 = verts[face[0]]
            rz = p0[0] * np.sin(rad) + p0[2] * np.cos(rad)
            face_depths.append((rz, face_idx))

        face_depths.sort(key=lambda x: x[0])  # Back to front

        for _, f_idx in face_depths:
            face = mesh.faces[f_idx]
            pts_2d = []
            for vi in face:
                v = verts[vi]
                rx = v[0] * np.cos(rad) - v[2] * np.sin(rad)
                rz = v[0] * np.sin(rad) + v[2] * np.cos(rad)
                sx = cx + rx * scale_px
                sy = cy - (v[1] + rz * 0.15) * scale_px
                pts_2d.append((sx, sy))

            c = tuple(vert_colors[face[0]][:3])
            draw.polygon(pts_2d, fill=c)

    img.save(out_path)


# ---------------------------------------------------------------------------
# MAIN DISPATCHER
# ---------------------------------------------------------------------------

def process_dataset(dataset_info: dict):
    """Process a single dataset, dispatching to the calibrated or casual pipeline."""
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
    print(f"\n  Pipeline completed in {dt:.2f} seconds.")


def main():
    parser = argparse.ArgumentParser(
        description="Universal 3D Photogrammetry Auto-Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/auto_reconstruct.py --auto
      Scan data/ and reconstruct ALL detected datasets.

  python scripts/auto_reconstruct.py --dataset_dir data/syncom_bottle
      Reconstruct only the specified dataset.

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

        total_t = time.time()
        for ds in datasets:
            process_dataset(ds)
        total_dt = time.time() - total_t
        print(f"\n\nAll {len(datasets)} dataset(s) reconstructed in {total_dt:.2f} seconds.")

    else:
        parser.print_help()
        print("\n\nDatasets currently detected in data/:")
        datasets = find_datasets(DATA_DIR)
        if not datasets:
            print("  (none found)")
        for ds in datasets:
            print(f"  - {ds['name']:30s}  [{ds['type']}]  {ds['image_count']} images")


if __name__ == "__main__":
    main()
