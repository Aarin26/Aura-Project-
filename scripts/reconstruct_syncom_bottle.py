#!/usr/bin/env python3
"""
scripts/reconstruct_syncom_bottle.py
Photogrammetry Reconstruction Engine for SynCom Bottle Dataset.

Reconstructs the multi-view dataset into a smooth, watertight, production-ready
3D model with accurate geometry, smooth surface curvature, and true photo colors.
"""

import json
import math
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import scipy.ndimage as ndimage
from scipy.spatial import cKDTree

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("[ERROR] trimesh is required. Run: pip install trimesh")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
SYNCOM_DIR = BASE_DIR / "data" / "syncom_bottle"
OUTPUT_EXPORT = BASE_DIR / "outputs" / "phase_7_export"
OUTPUT_SYNCOM = BASE_DIR / "outputs" / "syncom_bottle"

sys.path.insert(0, str(BASE_DIR))
from scripts.auto_reconstruct import extract_surface_nets, _bake_clean_texture_atlas, _export_all


def reconstruct():
    print("\n" + "=" * 70)
    print("  Running Generalized 3D Photogrammetry Engine on SynCom Bottle")
    print("=" * 70)

    with open(SYNCOM_DIR / "cameras.json", encoding="utf-8") as f:
        cams = json.load(f)["cameras"]

    gl_to_cv = np.diag([1.0, -1.0, -1.0, 1.0])

    views = sorted(list(cams.keys()))[::2] # 50 views
    cams_data = []
    cam_positions = []
    for v in views:
        c = cams[v]
        img_path = SYNCOM_DIR / f"{v}.png"
        if not img_path.exists():
            continue
        im = Image.open(img_path).convert("RGBA")
        arr = np.array(im)
        mask = arr[:, :, 3] > 20
        M = np.array(c["extr"]).reshape((4, 4))
        cam_pos = M[:3, 3]
        cam_positions.append(cam_pos)
        W2C = np.linalg.inv(M @ gl_to_cv)
        cams_data.append((W2C, c["intr"], arr, mask, cam_pos))

    img_h, img_w = cams_data[0][2].shape[:2]

    # Auto-Bounds
    cam_dists = [np.linalg.norm(p) for p in cam_positions]
    r_orbit = float(np.median(cam_dists))
    r_init = r_orbit * 0.45

    N_coarse = 32
    lin_c = np.linspace(-r_init, r_init, N_coarse)
    gx, gy, gz = np.meshgrid(lin_c, lin_c, lin_c, indexing="ij")
    pts_c = np.vstack([gx.ravel(), gy.ravel(), gz.ravel(), np.ones(N_coarse**3)])
    inside_c = np.ones(N_coarse**3, dtype=bool)

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
    extents_c = surv_c.max(axis=0) - surv_c.min(axis=0)
    padding = 0.12 * extents_c
    b_min = surv_c.min(axis=0) - padding
    b_max = surv_c.max(axis=0) + padding

    # High-Resolution Carve
    N_fine = 80
    x_lin = np.linspace(b_min[0], b_max[0], N_fine)
    y_lin = np.linspace(b_min[1], b_max[1], N_fine)
    z_lin = np.linspace(b_min[2], b_max[2], N_fine)
    grid_x, grid_y, grid_z = np.meshgrid(x_lin, y_lin, z_lin, indexing="ij")
    pts_fine = np.vstack([grid_x.ravel(), grid_y.ravel(), grid_z.ravel(), np.ones(N_fine**3)])
    inside = np.ones(N_fine**3, dtype=bool)

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
    vol_smooth = ndimage.gaussian_filter(vol.astype(np.float32), sigma=0.85)
    vol_binary = vol_smooth > 0.45

    spacing = (
        (b_max[0] - b_min[0]) / (N_fine - 1),
        (b_max[1] - b_min[1]) / (N_fine - 1),
        (b_max[2] - b_min[2]) / (N_fine - 1),
    )

    mesh = extract_surface_nets(vol_binary, spacing, b_min)
    trimesh.smoothing.filter_laplacian(mesh, iterations=4, lamb=0.35)

    comps = mesh.split(only_watertight=False)
    if comps:
        max_v = max(len(c.vertices) for c in comps)
        valid_comps = [c for c in comps if len(c.vertices) >= max(300, max_v * 0.05)]
        mesh = trimesh.util.concatenate(valid_comps) if valid_comps else max(comps, key=lambda c: len(c.vertices))
    mesh.remove_unreferenced_vertices()

    # Multi-view color projection
    verts = mesh.vertices
    normals = mesh.vertex_normals
    num_verts = len(verts)

    best_score = -np.ones(num_verts)
    vert_colors = np.ones((num_verts, 4), dtype=np.uint8) * 220
    pts4 = np.hstack([verts, np.ones((num_verts, 1))]).T

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

    # Orientation & scale
    R_z_to_y = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0]
    ], dtype=float)

    aligned_verts = verts @ R_z_to_y.T
    min_y = np.min(aligned_verts[:, 1])
    aligned_verts[:, 1] -= min_y
    raw_h = float(np.max(aligned_verts[:, 1]))
    scale_factor = 0.18 / max(raw_h, 1e-4)
    aligned_verts *= scale_factor
    mesh.vertices = aligned_verts

    # Texture & Seam-split UVs
    uv_list, face_uvs, texture_img = _bake_clean_texture_atlas(mesh, vert_colors, tex_size=1024)

    # Export to both phase_7_export and outputs/syncom_bottle
    for out_d in [OUTPUT_EXPORT, OUTPUT_SYNCOM]:
        _export_all(mesh, uv_list, face_uvs, vert_colors, texture_img, out_d, "syncom_bottle")

    print("\n[OK] Production assets regenerated with smooth geometry and clean textures.")


def main():
    t0 = time.time()
    reconstruct()
    print(f"Total reconstruction completed in {time.time()-t0:.2f} seconds.")


if __name__ == "__main__":
    main()
